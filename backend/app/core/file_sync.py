from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Callable, Optional

import paramiko

from app.core.gitignore_parser import GitignoreParser

SyncProgressCallback = Callable[[str, float, str], None]


class SyncActionType(Enum):
    UPLOAD = "upload"
    DELETE = "delete"
    SKIP = "skip"


class SyncFileInfo:
    def __init__(self, mtime: float, size: int):
        self.mtime = mtime
        self.size = size

    def to_dict(self) -> dict:
        return {"mtime": self.mtime, "size": self.size}

    @classmethod
    def from_dict(cls, data: dict) -> SyncFileInfo:
        return cls(mtime=data["mtime"], size=data["size"])


class SyncAction:
    def __init__(self, action_type: SyncActionType, relative_path: str):
        self.action_type = action_type
        self.relative_path = relative_path


class FileSyncEngine:
    SYNC_STATE_FILE = ".opsv-sync-state.json"
    SYNC_STATE_VERSION = 1

    def __init__(
        self,
        local_path: str,
        remote_path: str,
        sftp: paramiko.SFTPClient,
        gitignore_parser: GitignoreParser,
        progress_callback: Optional[SyncProgressCallback] = None,
    ):
        self._local_path = os.path.abspath(local_path)
        self._remote_path = remote_path.rstrip("/")
        self._sftp = sftp
        self._gitignore_parser = gitignore_parser
        self._progress_callback = progress_callback
        self._lock = RLock()
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        self._stopped = True

    def full_sync(self, force: bool = False) -> None:
        self._report_progress("scan", 0.0, "开始扫描本地文件...")
        local_files = self._scan_local_files()
        total_local = len(local_files)
        self._report_progress("scan", 1.0, f"本地扫描完成，共 {total_local} 个文件")

        if self._stopped:
            return

        if force:
            remote_state = None
        else:
            self._report_progress("load_state", 0.0, "加载远程同步状态...")
            remote_state = self._load_remote_state()

        self._report_progress("diff", 0.0, "计算差异...")
        actions = self._compute_actions(local_files, remote_state)
        total_actions = sum(
            1 for a in actions if a.action_type != SyncActionType.SKIP
        )
        self._report_progress(
            "diff", 1.0, f"差异计算完成，待处理 {total_actions} 个操作"
        )

        if self._stopped:
            return

        self._execute_actions(actions)

        if self._stopped:
            return

        self._report_progress("save_state", 0.95, "保存同步状态...")
        self._save_remote_state(local_files)

        self._report_progress("complete", 1.0, "同步完成")

    def _report_progress(self, phase: str, progress: float, message: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, progress, message)

    def _scan_local_files(self) -> dict[str, SyncFileInfo]:
        files: dict[str, SyncFileInfo] = {}
        for dirpath, dirnames, filenames in os.walk(self._local_path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            rel_dir = os.path.relpath(dirpath, self._local_path)
            if rel_dir == ".":
                rel_dir = ""

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                if rel_dir:
                    rel_path = rel_dir.replace("\\", "/") + "/" + filename
                else:
                    rel_path = filename

                if rel_path == self.SYNC_STATE_FILE:
                    continue

                if self._gitignore_parser.is_ignored(rel_path, is_dir=False):
                    continue

                try:
                    stat = os.stat(full_path)
                    files[rel_path] = SyncFileInfo(
                        mtime=stat.st_mtime, size=stat.st_size
                    )
                except OSError:
                    continue
        return files

    def _load_remote_state(self) -> Optional[dict[str, SyncFileInfo]]:
        remote_state_path = self._remote_path + "/" + self.SYNC_STATE_FILE
        try:
            with self._sftp.open(remote_state_path, "r") as f:
                raw = f.read().decode("utf-8")
            data = json.loads(raw)
            if data.get("version") != self.SYNC_STATE_VERSION:
                return None
            return {
                path: SyncFileInfo.from_dict(info)
                for path, info in data.get("files", {}).items()
            }
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def _save_remote_state(self, local_files: dict[str, SyncFileInfo]) -> None:
        remote_state_path = self._remote_path + "/" + self.SYNC_STATE_FILE
        data = {
            "version": self.SYNC_STATE_VERSION,
            "files": {
                path: info.to_dict() for path, info in local_files.items()
            },
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }
        import tempfile

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        try:
            json.dump(data, tmp, indent=2)
            tmp.close()
            self._sftp.put(tmp.name, remote_state_path)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _compute_actions(
        self,
        local_files: dict[str, SyncFileInfo],
        remote_state: Optional[dict[str, SyncFileInfo]],
    ) -> list[SyncAction]:
        actions: list[SyncAction] = []
        local_set = set(local_files.keys())
        remote_set = set(remote_state.keys()) if remote_state else set()

        for path in sorted(local_set):
            if path not in remote_set:
                actions.append(SyncAction(SyncActionType.UPLOAD, path))
            else:
                local_info = local_files[path]
                remote_info = remote_state[path]
                if local_info.mtime != remote_info.mtime or local_info.size != remote_info.size:
                    actions.append(SyncAction(SyncActionType.UPLOAD, path))
                else:
                    actions.append(SyncAction(SyncActionType.SKIP, path))

        for path in sorted(remote_set - local_set):
            actions.append(SyncAction(SyncActionType.DELETE, path))

        return actions

    def _execute_actions(self, actions: list[SyncAction]) -> None:
        uploads = [a for a in actions if a.action_type == SyncActionType.UPLOAD]
        deletes = [a for a in actions if a.action_type == SyncActionType.DELETE]
        total_ops = len(uploads) + len(deletes)

        if total_ops == 0:
            self._report_progress("idle", 1.0, "所有文件已是最新，无需同步")
            return

        completed = 0
        for action in uploads:
            if self._stopped:
                return
            self._upload_file(action.relative_path)
            completed += 1
            progress = 0.1 + (completed / total_ops) * 0.8
            self._report_progress(
                "upload",
                min(progress, 0.9),
                f"上传: {action.relative_path} ({completed}/{total_ops})",
            )

        for action in deletes:
            if self._stopped:
                return
            self._delete_remote_file(action.relative_path)
            completed += 1
            progress = 0.1 + (completed / total_ops) * 0.8
            self._report_progress(
                "delete",
                min(progress, 0.9),
                f"删除: {action.relative_path} ({completed}/{total_ops})",
            )

    def _ensure_remote_dir(self, remote_file_path: str) -> None:
        dir_path = os.path.dirname(remote_file_path).replace("\\", "/")
        if not dir_path:
            return
        parts = dir_path.split("/")
        current = ""
        for part in parts:
            if not part:
                continue
            current += "/" + part
            try:
                self._sftp.stat(current)
            except FileNotFoundError:
                try:
                    self._sftp.mkdir(current)
                except OSError:
                    pass

    def _upload_file(self, relative_path: str) -> None:
        local_file = os.path.join(self._local_path, relative_path).replace(
            "\\", "/"
        )
        remote_file = self._remote_path + "/" + relative_path.replace("\\", "/")
        self._ensure_remote_dir(remote_file)
        try:
            self._sftp.put(local_file, remote_file)
        except Exception as e:
            raise RuntimeError(
                f"上传文件失败 {relative_path}: {e}"
            ) from e

    def _delete_remote_file(self, relative_path: str) -> None:
        remote_file = self._remote_path + "/" + relative_path.replace("\\", "/")
        try:
            try:
                attr = self._sftp.stat(remote_file)
                if attr.st_mode is not None:
                    import stat as stat_module
                    if stat_module.S_ISDIR(attr.st_mode):
                        self._sftp.rmdir(remote_file)
                        return
            except Exception:
                pass
            self._sftp.remove(remote_file)
        except FileNotFoundError:
            pass
        except Exception as e:
            raise RuntimeError(
                f"删除远程文件失败 {relative_path}: {e}"
            ) from e
