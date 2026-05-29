from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from app.core.permission_checker import (
    FilePermissions,
    PermissionChecker,
    UserInfo,
)
from app.core.remote_file_manager import (
    FileDetail,
    FileEntry,
    FileSearchResult,
    RemoteFileManager,
)
from app.core.ssh_client import SSHClientManager
from app.core.ssh_pool import PooledConnection
from app.models.ssh_account import SSHAccount
from app.services.ssh_account_service import ssh_account_service


@dataclass
class Bookmark:
    alias: str
    path: str
    label: str
    created_at: str = ""


@dataclass
class OperationRecord:
    timestamp: str
    account_alias: str
    action: str
    path: str
    status: str
    detail: str = ""


@dataclass
class CommandHistoryRecord:
    timestamp: str
    account_alias: str
    command: str
    exit_code: int
    stdout: str
    stderr: str


_BOOKMARKS_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config"
    / "file_manager_bookmarks.json"
)


class FileManagerService:
    def __init__(self):
        self._operation_history: list[OperationRecord] = []
        self._command_history: list[CommandHistoryRecord] = []
        self._lock = threading.RLock()
        self._bookmarks: list[Bookmark] = []
        self._load_bookmarks()

    def _get_connection(self, alias: str) -> PooledConnection:
        account = ssh_account_service.get_account(alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{alias}' 不存在")
        account_obj = SSHAccount(
            alias=account.alias,
            host=account.host,
            port=account.port,
            username=account.username,
            auth_type=account.auth_type,
            password=account.password,
            private_key=account.private_key,
            key_passphrase=account.key_passphrase,
            totp_secret=account.totp_secret,
            is_default=account.is_default,
            group=account.group,
        )
        conn = ssh_account_service.pool.get_connection(account_obj)
        return conn

    def _release_connection(self, conn: PooledConnection) -> None:
        ssh_account_service.pool.release_connection(conn)

    def _with_manager(self, alias: str, timeout: float = 30.0) -> tuple[PooledConnection, RemoteFileManager, PermissionChecker]:
        conn = self._get_connection(alias)
        manager = conn.manager
        file_mgr = RemoteFileManager(manager)
        perm_checker = PermissionChecker(manager)
        return conn, file_mgr, perm_checker

    def _record_operation(
        self, account_alias: str, action: str, path: str, status: str, detail: str = ""
    ) -> None:
        with self._lock:
            record = OperationRecord(
                timestamp=datetime.now().isoformat(),
                account_alias=account_alias,
                action=action,
                path=path,
                status=status,
                detail=detail,
            )
            self._operation_history.append(record)
            if len(self._operation_history) > 10000:
                self._operation_history = self._operation_history[-5000:]

    def _record_command(
        self,
        account_alias: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        with self._lock:
            record = CommandHistoryRecord(
                timestamp=datetime.now().isoformat(),
                account_alias=account_alias,
                command=command,
                exit_code=exit_code,
                stdout=stdout[:500],
                stderr=stderr[:500],
            )
            self._command_history.append(record)
            if len(self._command_history) > 10000:
                self._command_history = self._command_history[-5000:]

    # ---- 文件操作 ----

    def list_directory(
        self, alias: str, path: str
    ) -> list[FileEntry]:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_execute_access(path):
                raise PermissionError(f"无执行权限: {path}")
            result = mgr.list_directory(path)
            self._record_operation(alias, "list_directory", path, "success")
            return result
        except Exception:
            self._record_operation(alias, "list_directory", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def get_file_info(self, alias: str, path: str) -> FileDetail:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_read_access(path):
                raise PermissionError(f"无读取权限: {path}")
            result = mgr.get_file_info(path)
            self._record_operation(alias, "get_file_info", path, "success")
            return result
        except Exception:
            self._record_operation(alias, "get_file_info", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def read_file(self, alias: str, path: str) -> str:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_read_access(path):
                raise PermissionError(f"无读取权限: {path}")
            result = mgr.read_file(path)
            self._record_operation(alias, "read_file", path, "success")
            return result
        except Exception:
            self._record_operation(alias, "read_file", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def write_file(self, alias: str, path: str, content: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_write_access(path):
                raise PermissionError(f"无写入权限: {path}")
            mgr.write_file(path, content)
            self._record_operation(alias, "write_file", path, "success")
        except Exception:
            self._record_operation(alias, "write_file", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def create_file(self, alias: str, path: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            parent = str(Path(path).parent).replace("\\", "/")
            if not perm.check_write_access(parent):
                raise PermissionError(f"无写入权限: {parent}")
            mgr.create_file(path)
            self._record_operation(alias, "create_file", path, "success")
        except Exception:
            self._record_operation(alias, "create_file", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def create_directory(self, alias: str, path: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            parent = str(Path(path).parent).replace("\\", "/")
            if not perm.check_write_access(parent):
                raise PermissionError(f"无写入权限: {parent}")
            mgr.create_directory(path)
            self._record_operation(alias, "create_directory", path, "success")
        except Exception:
            self._record_operation(alias, "create_directory", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def delete(self, alias: str, path: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_write_access(path):
                parent = str(Path(path).parent).replace("\\", "/")
                if not perm.check_write_access(parent):
                    raise PermissionError(f"无删除权限: {path}")
            mgr.delete(path)
            self._record_operation(alias, "delete", path, "success")
        except Exception:
            self._record_operation(alias, "delete", path, "failure")
            raise
        finally:
            self._release_connection(conn)

    def rename(self, alias: str, src: str, dst: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            src_parent = str(Path(src).parent).replace("\\", "/")
            dst_parent = str(Path(dst).parent).replace("\\", "/")
            if not perm.check_write_access(src_parent):
                raise PermissionError(f"无权重命名: {src}")
            if src_parent != dst_parent and not perm.check_write_access(dst_parent):
                raise PermissionError(f"无权写入目标: {dst}")
            mgr.rename(src, dst)
            self._record_operation(alias, "rename", f"{src} -> {dst}", "success")
        except Exception:
            self._record_operation(alias, "rename", f"{src} -> {dst}", "failure")
            raise
        finally:
            self._release_connection(conn)

    def copy(self, alias: str, src: str, dst: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_read_access(src):
                raise PermissionError(f"无读取权限: {src}")
            dst_parent = str(Path(dst).parent).replace("\\", "/")
            if not perm.check_write_access(dst_parent):
                raise PermissionError(f"无写入目标权限: {dst}")
            mgr.copy(src, dst)
            self._record_operation(alias, "copy", f"{src} -> {dst}", "success")
        except Exception:
            self._record_operation(alias, "copy", f"{src} -> {dst}", "failure")
            raise
        finally:
            self._release_connection(conn)

    def chmod(self, alias: str, path: str, mode: str) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            mgr.chmod(path, mode)
            self._record_operation(alias, "chmod", path, "success", f"mode={mode}")
        except Exception:
            self._record_operation(alias, "chmod", path, "failure", f"mode={mode}")
            raise
        finally:
            self._release_connection(conn)

    def chown(self, alias: str, path: str, user: Optional[str] = None, group: Optional[str] = None) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            sudo_ok = perm.check_sudo_access()
            if not sudo_ok:
                raise PermissionError("需要 sudo 权限来修改文件所有者")
            mgr.chown(path, user=user, group=group)
            detail = f"user={user or '-'}, group={group or '-'}"
            self._record_operation(alias, "chown", path, "success", detail)
        except Exception:
            detail = f"user={user or '-'}, group={group or '-'}"
            self._record_operation(alias, "chown", path, "failure", detail)
            raise
        finally:
            self._release_connection(conn)

    def upload(
        self,
        alias: str,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            remote_dir = str(Path(remote_path).parent).replace("\\", "/")
            if not perm.check_write_access(remote_dir):
                raise PermissionError(f"无写入权限: {remote_dir}")
            mgr.upload(local_path, remote_path, progress_callback=progress_callback)
            self._record_operation(alias, "upload", f"{local_path} -> {remote_path}", "success")
        except Exception:
            self._record_operation(alias, "upload", f"{local_path} -> {remote_path}", "failure")
            raise
        finally:
            self._release_connection(conn)

    def download(
        self,
        alias: str,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_read_access(remote_path):
                raise PermissionError(f"无读取权限: {remote_path}")
            mgr.download(remote_path, local_path, progress_callback=progress_callback)
            self._record_operation(alias, "download", f"{remote_path} -> {local_path}", "success")
        except Exception:
            self._record_operation(alias, "download", f"{remote_path} -> {local_path}", "failure")
            raise
        finally:
            self._release_connection(conn)

    def search(
        self,
        alias: str,
        path: str,
        pattern: str,
        max_depth: Optional[int] = None,
        file_type: Optional[str] = None,
    ) -> list[FileSearchResult]:
        conn, mgr, perm = self._with_manager(alias)
        try:
            if not perm.check_execute_access(path):
                raise PermissionError(f"无执行权限: {path}")
            result = mgr.search(path, pattern, max_depth=max_depth, file_type=file_type)
            self._record_operation(alias, "search", path, "success", f"pattern={pattern}")
            return result
        except Exception:
            self._record_operation(alias, "search", path, "failure", f"pattern={pattern}")
            raise
        finally:
            self._release_connection(conn)

    # ---- 命令执行 ----

    def exec_command(
        self, alias: str, command: str, timeout: float = 30.0
    ) -> dict:
        conn, mgr, _ = self._with_manager(alias, timeout=timeout)
        try:
            result = mgr.exec_command(command, timeout=timeout)
            self._record_command(
                alias, command, result["exit_code"], result["stdout"], result["stderr"]
            )
            return result
        finally:
            self._release_connection(conn)

    def exec_batch(
        self, alias: str, commands: list[str], timeout: float = 60.0
    ) -> list[dict]:
        conn, mgr, _ = self._with_manager(alias, timeout=timeout)
        try:
            results = mgr.exec_batch(commands, timeout=timeout)
            for r in results:
                self._record_command(alias, r["command"], r["exit_code"], r["stdout"], r["stderr"])
            return results
        finally:
            self._release_connection(conn)

    def get_command_history(
        self, alias: Optional[str] = None, limit: int = 100
    ) -> list[CommandHistoryRecord]:
        with self._lock:
            history = self._command_history
            if alias:
                history = [h for h in history if h.account_alias == alias]
            return history[-limit:]

    # ---- 权限检查 ----

    def check_permission(self, alias: str, path: str) -> FilePermissions:
        conn, _, perm = self._with_manager(alias)
        try:
            return perm.get_file_permissions(path)
        finally:
            self._release_connection(conn)

    def get_user_info(self, alias: str) -> UserInfo:
        conn, _, perm = self._with_manager(alias)
        try:
            return perm.get_current_user()
        finally:
            self._release_connection(conn)

    def check_sudo(self, alias: str) -> bool:
        conn, _, perm = self._with_manager(alias)
        try:
            return perm.check_sudo_access()
        finally:
            self._release_connection(conn)

    # ---- 书签管理 ----

    def list_bookmarks(self, alias: Optional[str] = None) -> list[Bookmark]:
        with self._lock:
            if alias:
                return [b for b in self._bookmarks if b.alias == alias]
            return list(self._bookmarks)

    def add_bookmark(self, alias: str, path: str, label: str) -> Bookmark:
        with self._lock:
            existing = [b for b in self._bookmarks if b.alias == alias and b.path == path]
            if existing:
                existing[0].label = label
                self._save_bookmarks()
                return existing[0]
            bookmark = Bookmark(
                alias=alias,
                path=path,
                label=label,
                created_at=datetime.now().isoformat(),
            )
            self._bookmarks.append(bookmark)
            self._save_bookmarks()
            return bookmark

    def remove_bookmark(self, alias: str, path: str) -> bool:
        with self._lock:
            before = len(self._bookmarks)
            self._bookmarks = [b for b in self._bookmarks if not (b.alias == alias and b.path == path)]
            if len(self._bookmarks) < before:
                self._save_bookmarks()
                return True
            return False

    def _load_bookmarks(self) -> None:
        try:
            if _BOOKMARKS_FILE.exists():
                data = json.loads(_BOOKMARKS_FILE.read_text(encoding="utf-8"))
                self._bookmarks = [Bookmark(**b) for b in data]
        except Exception:
            self._bookmarks = []

    def _save_bookmarks(self) -> None:
        try:
            _BOOKMARKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(b) for b in self._bookmarks]
            _BOOKMARKS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ---- 操作历史 ----

    def get_operation_history(
        self, alias: Optional[str] = None, limit: int = 100
    ) -> list[OperationRecord]:
        with self._lock:
            history = self._operation_history
            if alias:
                history = [h for h in history if h.account_alias == alias]
            return history[-limit:]

    # ---- 批量操作 ----

    def batch_delete(self, alias: str, paths: list[str]) -> list[dict]:
        results: list[dict] = []
        for path in paths:
            try:
                self.delete(alias, path)
                results.append({"path": path, "success": True, "error": None})
            except Exception as e:
                results.append({"path": path, "success": False, "error": str(e)})
        return results

    def batch_chmod(self, alias: str, paths: list[str], mode: str, recursive: bool = False) -> list[dict]:
        results: list[dict] = []
        for path in paths:
            try:
                if recursive:
                    self.chmod(alias, path, f"-R {mode}")
                else:
                    self.chmod(alias, path, mode)
                results.append({"path": path, "success": True, "error": None})
            except Exception as e:
                results.append({"path": path, "success": False, "error": str(e)})
        return results


file_manager_service = FileManagerService()
