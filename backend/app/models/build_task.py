from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4


BUILD_ACTIONS = frozenset({"compile", "package", "run"})
BUILD_STATUSES = frozenset({"pending", "running", "completed", "failed", "stopped"})


class BuildTask:
    def __init__(
        self,
        task_id: str,
        account_alias: str,
        project_path: str,
        action: str,
        config: Optional[dict] = None,
    ):
        if action not in BUILD_ACTIONS:
            raise ValueError(f"无效的构建动作: {action}，可选: {BUILD_ACTIONS}")
        self.task_id = task_id
        self.account_alias = account_alias
        self.project_path = project_path
        self.action = action
        self.config = config or {}
        self.status: str = "pending"
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.log: str = ""
        self.exit_code: Optional[int] = None
        self.pid: Optional[int] = None
        self._callbacks: list[Callable[[BuildTask], None]] = []
        self._stop_requested = False

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    def request_stop(self) -> None:
        self._stop_requested = True

    def add_callback(self, cb: Callable[[BuildTask], None]) -> None:
        self._callbacks.append(cb)

    def append_log(self, text: str) -> None:
        self.log += text
        self._notify()

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception:
                pass

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "account_alias": self.account_alias,
            "project_path": self.project_path,
            "action": self.action,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "log": self.log,
            "exit_code": self.exit_code,
            "pid": self.pid,
        }


def new_build_task(
    account_alias: str,
    project_path: str,
    action: str,
    config: Optional[dict] = None,
) -> BuildTask:
    task_id = uuid4().hex[:12]
    return BuildTask(
        task_id=task_id,
        account_alias=account_alias,
        project_path=project_path,
        action=action,
        config=config,
    )
