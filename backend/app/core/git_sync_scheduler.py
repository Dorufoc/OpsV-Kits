from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SyncTask:
    def __init__(
        self,
        config_id: str,
        account_alias: str,
        repo_path: str,
        check_interval: int,
        sync_mode: str,
        auto_deploy: bool,
        deploy_pipeline_id: Optional[str],
        branch: str,
        ff_only: bool,
    ):
        self.config_id = config_id
        self.account_alias = account_alias
        self.repo_path = repo_path
        self.check_interval = check_interval
        self.sync_mode = sync_mode
        self.auto_deploy = auto_deploy
        self.deploy_pipeline_id = deploy_pipeline_id
        self.branch = branch
        self.ff_only = ff_only
        self.last_check_time: Optional[str] = None
        self.last_sync_time: Optional[str] = None
        self.last_sync_result: Optional[str] = None
        self.pending_updates: int = 0
        self.error_count: int = 0
        self.status: str = "active"
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._on_update: Optional[Callable] = None
        self._on_sync_needed: Optional[Callable] = None

    def set_callbacks(self, on_update: Optional[Callable] = None, on_sync_needed: Optional[Callable] = None):
        self._on_update = on_update
        self._on_sync_needed = on_sync_needed

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "account_alias": self.account_alias,
            "repo_path": self.repo_path,
            "check_interval": self.check_interval,
            "sync_mode": self.sync_mode,
            "auto_deploy": self.auto_deploy,
            "deploy_pipeline_id": self.deploy_pipeline_id,
            "branch": self.branch,
            "ff_only": self.ff_only,
            "last_check_time": self.last_check_time,
            "last_sync_time": self.last_sync_time,
            "last_sync_result": self.last_sync_result,
            "pending_updates": self.pending_updates,
            "error_count": self.error_count,
            "status": self.status,
        }

    def request_stop(self):
        self._stop_event.set()

    def _notify_update(self):
        if self._on_update:
            try:
                self._on_update(self.config_id, self.to_dict())
            except Exception:
                logger.exception("on_update callback error for %s", self.config_id)


def _run_git_fetch(repo_path: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "fetch", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stderr + result.stdout
    except Exception as e:
        return False, str(e)


def _run_git_rev_list(repo_path: str, branch: str) -> tuple[int, int]:
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"origin/{branch}...{branch}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return 0, 0
        parts = result.stdout.strip().split()
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
        return 0, 0
    except Exception:
        return 0, 0


def _run_git_pull(repo_path: str, branch: str, ff_only: bool) -> tuple[bool, str]:
    cmd = ["git", "pull", "origin", branch]
    if ff_only:
        cmd.append("--ff-only")
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        has_conflict = "CONFLICT" in output or "merge conflict" in output.lower()
        if has_conflict:
            return False, "conflict"
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


class GitSyncScheduler:
    def __init__(self):
        self._tasks: dict[str, SyncTask] = {}
        self._running = False
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._running

    async def start(self):
        self._running = True
        for task in self._tasks.values():
            if task._task is None or task._task.done():
                task._stop_event.clear()
                task._task = asyncio.create_task(self._run_task(task))

    async def stop(self):
        for task in self._tasks.values():
            task.request_stop()
        deadlines = []
        for task in self._tasks.values():
            if task._task is not None and not task._task.done():
                deadlines.append(task._task)
        if deadlines:
            try:
                await asyncio.wait_for(asyncio.gather(*deadlines, return_exceptions=True), timeout=10)
            except asyncio.TimeoutError:
                for t in deadlines:
                    if not t.done():
                        t.cancel()
        self._running = False

    async def add_task(self, config: dict) -> str:
        config_id = config.get("config_id") or str(uuid4())
        task = SyncTask(
            config_id=config_id,
            account_alias=config["account_alias"],
            repo_path=config["repo_path"],
            check_interval=config.get("check_interval", 300),
            sync_mode=config.get("sync_mode", "notify_only"),
            auto_deploy=config.get("auto_deploy", False),
            deploy_pipeline_id=config.get("deploy_pipeline_id"),
            branch=config.get("branch", "main"),
            ff_only=config.get("ff_only", True),
        )
        async with self._lock:
            self._tasks[config_id] = task
        if self._running:
            task._stop_event.clear()
            task._task = asyncio.create_task(self._run_task(task))
        return config_id

    async def remove_task(self, config_id: str):
        async with self._lock:
            task = self._tasks.pop(config_id, None)
        if task is None:
            return
        task.request_stop()
        if task._task is not None and not task._task.done():
            try:
                await asyncio.wait_for(task._task, timeout=10)
            except asyncio.TimeoutError:
                task._task.cancel()

    async def update_task(self, config_id: str, config: dict):
        await self.remove_task(config_id)
        config["config_id"] = config_id
        await self.add_task(config)

    async def _run_task(self, task: SyncTask):
        while not task._stop_event.is_set():
            try:
                loop = asyncio.get_running_loop()

                fetch_ok, fetch_output = await loop.run_in_executor(
                    None, _run_git_fetch, task.repo_path
                )

                if not fetch_ok:
                    raise RuntimeError(f"git fetch failed: {fetch_output}")

                ahead, behind = await loop.run_in_executor(
                    None, _run_git_rev_list, task.repo_path, task.branch
                )

                if behind > 0:
                    task.pending_updates = behind
                    task._notify_update()

                    if task.sync_mode == "auto_pull":
                        pull_ok, pull_output = await loop.run_in_executor(
                            None, _run_git_pull, task.repo_path, task.branch, task.ff_only
                        )

                        if pull_ok:
                            task.last_sync_time = datetime.now(timezone.utc).isoformat()
                            task.last_sync_result = "success"
                            task.pending_updates = 0
                            task.error_count = 0
                            task.status = "active"
                            task._notify_update()

                            if task.auto_deploy and task._on_sync_needed:
                                try:
                                    task._on_sync_needed(
                                        task.config_id,
                                        task.account_alias,
                                        task.repo_path,
                                        task.branch,
                                        behind,
                                    )
                                except Exception:
                                    logger.exception("on_sync_needed callback error for %s", task.config_id)
                        elif pull_output == "conflict":
                            task.last_sync_result = "conflict"
                            task.status = "paused"
                            task._notify_update()
                            logger.warning("Conflict detected for %s, auto-sync paused", task.config_id)
                        else:
                            task.last_sync_result = f"pull_failed: {pull_output}"
                            task.error_count += 1
                            if task.error_count >= 3:
                                task.status = "error"
                            task._notify_update()

                    elif task.sync_mode == "notify_only":
                        if task._on_sync_needed:
                            try:
                                task._on_sync_needed(
                                    task.config_id,
                                    task.account_alias,
                                    task.repo_path,
                                    task.branch,
                                    behind,
                                )
                            except Exception:
                                logger.exception("on_sync_needed callback error for %s", task.config_id)

                else:
                    task.pending_updates = 0
                    task.error_count = 0
                    task.status = "active"

                task.last_check_time = datetime.now(timezone.utc).isoformat()
                task._notify_update()

            except Exception:
                task.error_count += 1
                task.last_sync_result = "check_failed"
                if task.error_count >= 3:
                    task.status = "error"
                task._notify_update()
                logger.exception("Sync check error for %s", task.config_id)

            try:
                await asyncio.wait_for(
                    task._stop_event.wait(),
                    timeout=task.check_interval,
                )
                return
            except asyncio.TimeoutError:
                pass

    def get_task_status(self, config_id: str) -> Optional[dict]:
        task = self._tasks.get(config_id)
        if task is None:
            return None
        return task.to_dict()

    def get_all_status(self) -> list[dict]:
        return [task.to_dict() for task in self._tasks.values()]

    async def trigger_manual_pull(self, config_id: str) -> dict:
        task = self._tasks.get(config_id)
        if task is None:
            return {"success": False, "message": f"Task {config_id} not found"}
        try:
            loop = asyncio.get_running_loop()
            pull_ok, pull_output = await loop.run_in_executor(
                None, _run_git_pull, task.repo_path, task.branch, task.ff_only
            )
            if pull_ok:
                task.last_sync_time = datetime.now(timezone.utc).isoformat()
                task.last_sync_result = "success"
                task.pending_updates = 0
                task.error_count = 0
                task.status = "active"
                task._notify_update()
                return {"success": True, "message": pull_output}
            elif pull_output == "conflict":
                task.last_sync_result = "conflict"
                task.status = "paused"
                task._notify_update()
                return {"success": False, "message": "Merge conflict detected, auto-sync paused"}
            else:
                task.last_sync_result = f"pull_failed: {pull_output}"
                task.error_count += 1
                if task.error_count >= 3:
                    task.status = "error"
                task._notify_update()
                return {"success": False, "message": pull_output}
        except Exception as e:
            task.error_count += 1
            if task.error_count >= 3:
                task.status = "error"
            task._notify_update()
            return {"success": False, "message": str(e)}


git_sync_scheduler = GitSyncScheduler()
