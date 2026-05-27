from __future__ import annotations

import os
import time
from enum import Enum
from threading import RLock
from typing import Callable, Optional

import paramiko

from app.core.gitignore_parser import GitignoreParser

SyncProgressCallback = Callable[[str, float, str], None]

_CHUNK_SIZE = 128 * 1024


class FileSyncEngine:

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

    # ── 进度 ──────────────────────────────────────────────────────

    def _report(self, phase: str, progress: float, message: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, progress, message)

    # ── 镜像同步（核心） ────────────────────────────────────────────

    def full_sync(self, force: bool = False) -> None:
        self._report("scan", 0.0, "扫描本地项目...")
        local_files, local_sizes, local_dirs = self._scan_local()
        self._report("scan", 0.3, f"本地扫描完成: {len(local_files)} 个文件")

        if self._stopped:
            return

        self._report("scan", 0.4, "扫描远程目录...")
        remote_files, remote_sizes, remote_dirs = self._scan_remote()
        self._report("scan", 0.6, f"远程扫描完成: {len(remote_files)} 个文件")

        if self._stopped:
            return

        self._report("diff", 0.7, "计算差异...")
        files_to_upload = local_files - remote_files
        files_to_delete = remote_files - local_files
        files_to_check = local_files & remote_files

        needs_upload = set()
        if not force:
            checked = 0
            for rel_path in sorted(files_to_check):
                if self._stopped:
                    return
                local_size = local_sizes[rel_path] if rel_path in local_sizes else None
                remote_size = remote_sizes.get(rel_path)
                if local_size is None or remote_size is None or local_size != remote_size:
                    needs_upload.add(rel_path)
                checked += 1
                if checked % 50 == 0:
                    self._report("diff", 0.7 + (checked / max(len(files_to_check), 1)) * 0.2,
                                 f"检查更新: {checked}/{len(files_to_check)}")

        files_to_upload |= needs_upload

        self._report("diff", 0.9,
                     f"需上传 {len(files_to_upload)} 个, 需删除 {len(files_to_delete)} 个")

        if self._stopped:
            return

        if not files_to_upload and not files_to_delete:
            self._report("complete", 1.0, "已是最新，无需同步")
            return

        self._report("upload", 0.0, "创建目录结构...")
        self._create_remote_dirs(local_dirs)

        self._report("upload", 0.05, f"上传 {len(files_to_upload)} 个文件...")
        self._upload_files(files_to_upload)

        if self._stopped:
            return

        if files_to_delete:
            self._report("delete", 0.0, f"删除 {len(files_to_delete)} 个远程多余文件...")
            self._delete_files(files_to_delete)
            self._delete_empty_dirs(remote_dirs - local_dirs)

        self._report("complete", 1.0, "同步完成")

    # ── 本地扫描 ──────────────────────────────────────────────────

    def _scan_local(self) -> tuple[set[str], dict[str, int], set[str]]:
        files: set[str] = set()
        sizes: dict[str, int] = {}
        dirs: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(self._local_path):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            rel_dir = os.path.relpath(dirpath, self._local_path)
            if rel_dir == ".":
                rel_dir = ""
            
            # 记录目录
            if rel_dir:
                dirs.add(rel_dir)

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = (rel_dir.replace("\\", "/") + "/" + filename) if rel_dir else filename

                if self._gitignore_parser.is_ignored(rel_path, is_dir=False):
                    continue
                try:
                    st = os.stat(full_path)
                    files.add(rel_path)
                    sizes[rel_path] = st.st_size
                except OSError:
                    continue
        return files, sizes, dirs

    # ── 远程扫描 ──────────────────────────────────────────────────

    def _scan_remote(self) -> tuple[set[str], dict[str, int], set[str]]:
        files: set[str] = set()
        sizes: dict[str, int] = {}
        dirs: set[str] = set()

        def walk(path: str, prefix: str) -> None:
            try:
                entries = self._sftp.listdir_attr(path)
            except FileNotFoundError:
                return
            for entry in entries:
                name = entry.filename
                if name.startswith("."):
                    continue
                rel = f"{prefix}/{name}" if prefix else name
                if entry.st_mode is not None and (entry.st_mode & 0o40000):
                    if prefix:  # 不记录根目录
                        dirs.add(rel)
                    walk(f"{path}/{name}", rel)
                else:
                    files.add(rel)
                    sizes[rel] = entry.st_size

        walk(self._remote_path, "")
        return files, sizes, dirs

    # ── 创建目录 ──────────────────────────────────────────────────

    def _create_remote_dirs(self, local_dirs: set[str]) -> None:
        for rel_dir in sorted(local_dirs):
            if self._stopped:
                return
            remote_dir = f"{self._remote_path}/{rel_dir}"
            try:
                self._sftp.stat(remote_dir)
            except FileNotFoundError:
                try:
                    parent = os.path.dirname(remote_dir).replace("\\", "/")
                    if parent:
                        parts = parent.split("/")
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
                    self._sftp.mkdir(remote_dir)
                except OSError:
                    pass
            except OSError:
                pass

    # ── 上传文件 ──────────────────────────────────────────────────

    def _upload_files(self, files_to_upload: set[str]) -> None:
        total = len(files_to_upload)
        if total == 0:
            return
        uploaded = 0
        failed: list[str] = []
        for rel_path in sorted(files_to_upload):
            if self._stopped:
                return
            local_file = os.path.join(self._local_path, rel_path.replace("/", os.sep))
            remote_file = f"{self._remote_path}/{rel_path}"
            self._ensure_remote_dir(remote_file)
            ok = False
            try:
                self._sftp.put(local_file, remote_file)
                ok = True
            except FileNotFoundError:
                pass
            except Exception:
                try:
                    with open(local_file, "rb") as f:
                        self._sftp.putfo(f, remote_file)
                    ok = True
                except Exception:
                    pass

            if ok:
                uploaded += 1
                self._report("upload", uploaded / total, f"上传: {rel_path}")
            else:
                failed.append(rel_path)

        if failed:
            self._report("upload", 1.0, f"上传完成: {uploaded}/{total} 成功, {len(failed)} 个失败: {', '.join(failed[:5])}")

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

    # ── 删除文件 ──────────────────────────────────────────────────

    def _delete_files(self, files_to_delete: set[str]) -> None:
        total = len(files_to_delete)
        deleted = 0
        for rel_path in sorted(files_to_delete, reverse=True):
            if self._stopped:
                return
            remote_file = f"{self._remote_path}/{rel_path}"
            try:
                self._sftp.remove(remote_file)
            except FileNotFoundError:
                pass
            except Exception:
                pass
            deleted += 1
            self._report("delete", deleted / total, f"删除: {rel_path}")

    def _delete_empty_dirs(self, dirs_to_delete: set[str]) -> None:
        for rel_path in sorted(dirs_to_delete, reverse=True):
            if self._stopped:
                return
            remote_dir = f"{self._remote_path}/{rel_path}"
            try:
                self._sftp.rmdir(remote_dir)
            except Exception:
                pass
