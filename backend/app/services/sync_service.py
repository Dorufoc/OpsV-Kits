from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import WebSocket

from app.core.file_sync import FileSyncEngine, SyncProgressCallback
from app.core.gitignore_parser import GitignoreParser
from app.core.ssh_utils import resolve_remote_path
from app.core.ssh_pool import SSHConnectionPool
from app.models.ssh_account import SSHAccount
from app.services.ssh_account_service import ssh_account_service


class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class SyncTaskInfo:
    def __init__(
        self,
        sync_id: str,
        local_path: str,
        remote_path: str,
        account_alias: str,
        force: bool = False,
    ):
        self.sync_id = sync_id
        self.local_path = local_path
        self.remote_path = remote_path
        self.account_alias = account_alias
        self.force = force
        self.status: SyncStatus = SyncStatus.PENDING
        self.progress: float = 0.0
        self.phase: str = ""
        self.message: str = ""
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None


class SyncService:
    def __init__(self):
        self._pool = SSHConnectionPool()
        self._active_syncs: dict[str, SyncTaskInfo] = {}
        self._ws_connections: dict[str, set[WebSocket]] = {}
        self._lock = threading.RLock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def register_ws(self, sync_id: str, ws: WebSocket) -> None:
        with self._lock:
            if sync_id not in self._ws_connections:
                self._ws_connections[sync_id] = set()
            self._ws_connections[sync_id].add(ws)

    async def unregister_ws(self, sync_id: str, ws: WebSocket) -> None:
        with self._lock:
            if sync_id in self._ws_connections:
                self._ws_connections[sync_id].discard(ws)
                if not self._ws_connections[sync_id]:
                    del self._ws_connections[sync_id]

    async def start_sync(
        self,
        local_path: str,
        remote_path: str,
        account_alias: str,
        force: bool = False,
    ) -> str:
        account = ssh_account_service.get_account(account_alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{account_alias}' 不存在")

        sync_id = str(uuid4())
        task = SyncTaskInfo(
            sync_id=sync_id,
            local_path=local_path,
            remote_path=remote_path,
            account_alias=account_alias,
            force=force,
        )

        with self._lock:
            self._active_syncs[sync_id] = task

        asyncio.get_running_loop().run_in_executor(
            None, self._run_sync, sync_id, task, account
        )

        return sync_id

    def stop_sync(self, sync_id: str) -> bool:
        with self._lock:
            task = self._active_syncs.get(sync_id)
            if task is None:
                return False
            if task.status in (SyncStatus.COMPLETED, SyncStatus.FAILED, SyncStatus.STOPPED):
                return False
            task.status = SyncStatus.STOPPED
            task.message = "用户已停止同步"
        return True

    def get_status(self, sync_id: Optional[str] = None):
        with self._lock:
            if sync_id:
                task = self._active_syncs.get(sync_id)
                if task is None:
                    return None
                return self._task_to_dict(task)
            return [
                self._task_to_dict(t) for t in self._active_syncs.values()
            ]

    def get_active_syncs(self) -> list[dict]:
        with self._lock:
            return [
                self._task_to_dict(t)
                for t in self._active_syncs.values()
                if t.status in (SyncStatus.PENDING, SyncStatus.RUNNING)
            ]

    def _task_to_dict(self, task: SyncTaskInfo) -> dict:
        return {
            "sync_id": task.sync_id,
            "local_path": task.local_path,
            "remote_path": task.remote_path,
            "account_alias": task.account_alias,
            "force": task.force,
            "status": task.status.value,
            "progress": task.progress,
            "phase": task.phase,
            "message": task.message,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error": task.error,
        }

    def _run_sync(
        self, sync_id: str, task: SyncTaskInfo, account: SSHAccount
    ) -> None:
        task.status = SyncStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.progress = 0.0

        conn = None
        try:
            conn = self._pool.get_connection(account, timeout=15.0)
            task.remote_path = resolve_remote_path(
                conn.manager.client, task.remote_path, account.username
            )
            project_folder = os.path.basename(os.path.abspath(task.local_path))
            task.remote_path = task.remote_path.rstrip("/") + "/" + project_folder
            sftp = conn.manager.open_sftp()

            gitignore_parser = GitignoreParser(task.local_path)

            def progress_callback(phase: str, progress: float, message: str):
                if task.status == SyncStatus.STOPPED:
                    return
                task.phase = phase
                task.progress = progress
                task.message = message
                self._push_progress_to_ws(sync_id, {
                    "type": "progress",
                    "sync_id": sync_id,
                    "phase": phase,
                    "progress": progress,
                    "message": message,
                })

            engine = FileSyncEngine(
                local_path=task.local_path,
                remote_path=task.remote_path,
                sftp=sftp,
                gitignore_parser=gitignore_parser,
                progress_callback=progress_callback,
            )

            task.message = "开始同步..."
            self._push_progress_to_ws(sync_id, {
                "type": "start",
                "sync_id": sync_id,
                "message": "同步任务已启动",
            })

            engine.full_sync(force=task.force)

            if task.status != SyncStatus.STOPPED:
                task.status = SyncStatus.COMPLETED
                task.progress = 1.0
                task.completed_at = datetime.now(timezone.utc).isoformat()
                tree = self._get_remote_tree(conn.manager.client, task.remote_path)
                self._push_progress_to_ws(sync_id, {
                    "type": "completed",
                    "sync_id": sync_id,
                    "message": "同步完成",
                    "tree": tree,
                    "remote_path": task.remote_path,
                })

        except Exception as e:
            if task.status != SyncStatus.STOPPED:
                task.status = SyncStatus.FAILED
                task.error = str(e)
                self._push_progress_to_ws(sync_id, {
                    "type": "error",
                    "sync_id": sync_id,
                    "error": str(e),
                    "message": f"同步失败: {e}",
                })
        finally:
            if conn is not None:
                try:
                    self._pool.release_connection(conn)
                except Exception:
                    pass
            with self._lock:
                if sync_id in self._ws_connections:
                    for ws in list(self._ws_connections[sync_id]):
                        try:
                            close_msg = json.dumps({
                                "type": "closed",
                                "sync_id": sync_id,
                            })
                            asyncio.run_coroutine_threadsafe(
                                ws.close(code=1000, reason=close_msg),
                                self._get_loop(),
                            )
                        except Exception:
                            pass
                    del self._ws_connections[sync_id]

    def _push_progress_to_ws(self, sync_id: str, data: dict) -> None:
        with self._lock:
            connections = set(self._ws_connections.get(sync_id, set()))
            for ws in connections:
                try:
                    asyncio.run_coroutine_threadsafe(
                        ws.send_json(data), self._get_loop()
                    )
                except Exception:
                    pass

    def _get_remote_tree(self, ssh: paramiko.SSHClient, remote_path: str) -> str:
        try:
            _, stdout, _ = ssh.exec_command(
                f"find {remote_path} -not -path '*/.*' 2>/dev/null | sort | head -200",
                timeout=10.0,
            )
            output = stdout.read().decode("utf-8", errors="replace").strip()
            if not output:
                return remote_path
            lines = output.split("\n")
            result = []
            for line in lines:
                if line == remote_path.rstrip("/"):
                    result.append(line)
                else:
                    indent = line[len(remote_path.rstrip("/")):].count("/")
                    name = line.rsplit("/", 1)[-1]
                    prefix = "  " * indent + "└─ "
                    result.append(prefix + name)
            return "\n".join(result)
        except Exception:
            return f"(无法获取目录树: {remote_path})"

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None:
            return self._loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.new_event_loop()


sync_service = SyncService()
