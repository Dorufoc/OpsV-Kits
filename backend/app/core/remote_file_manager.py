from __future__ import annotations

import os
import re
import shlex
import stat as stat_module
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

import paramiko

from app.core.ssh_client import SSHClientManager


@dataclass
class FileEntry:
    name: str
    path: str
    is_dir: bool
    size: int
    permissions: str
    permission_mode: int
    modify_time: str
    modify_timestamp: float
    owner: str
    group: str
    link_target: Optional[str] = None


@dataclass
class FileDetail:
    path: str
    is_dir: bool
    is_file: bool
    is_link: bool
    is_socket: bool
    is_fifo: bool
    is_block_device: bool
    is_char_device: bool
    size: int
    blocks: int
    permissions: str
    permission_mode: int
    modify_time: str
    modify_timestamp: float
    access_time: str
    access_timestamp: float
    change_time: str
    change_timestamp: float
    owner: str
    group: str
    link_target: Optional[str] = None


@dataclass
class FileSearchResult:
    path: str
    name: str
    is_dir: bool
    size: int
    permissions: str
    modify_time: str


_LS_LINE_RE = re.compile(
    r"^(?P<perm>[drwxlst-]{10})[.+@]?\s+"
    r"(?P<nlink>\d+)\s+"
    r"(?P<owner>\S+)\s+"
    r"(?P<group>\S+)\s+"
    r"(?P<size>\d+)\s+"
    r"(?P<date_tokens>\S+(?:\s+\S+)*?)\s+"
    r"(?P<time_or_year>\d{1,2}:\d{2}|\d{4})\s+"
    r"(?P<name>.+?)$"
)

_STAT_LINE_PATTERNS: dict[str, re.Pattern] = {
    "file": re.compile(r"^文件：(.+)$"),
    "size": re.compile(r"^大小：(\d+)\s+"),
    "blocks": re.compile(r"^Block:\s+(\d+)"),
    "device": re.compile(r"^设备：(.+)$"),
    "inode": re.compile(r"^Inode：(\d+)"),
    "links": re.compile(r"^硬链接：(\d+)"),
    "access": re.compile(r"^Access：\((\d{4})/([^\)]+)\)"),
    "uid": re.compile(r"^Uid：\s*\(\s*(\d+)\)"),
    "gid": re.compile(r"^Gid：\s*\(\s*(\d+)\)"),
    "access_time": re.compile(r"^访问时间：(.+)$"),
    "modify_time": re.compile(r"^修改时间：(.+)$"),
    "change_time": re.compile(r"^更改时间：(.+)$"),
}


def _parse_ls_line(line: str, base_path: str, is_chinese: bool = False) -> Optional[FileEntry]:
    line = line.strip()
    if not line:
        return None
    m = _LS_LINE_RE.match(line)
    if not m:
        return None
    perm_str = m.group("perm")
    nlink = int(m.group("nlink"))
    owner = m.group("owner")
    group = m.group("group")
    size = int(m.group("size"))
    date_raw = m.group("date_tokens")
    time_or_year = m.group("time_or_year")
    name = m.group("name")

    is_dir = perm_str.startswith("d")
    is_link = perm_str.startswith("l")

    link_target = None
    if is_link and " -> " in name:
        name, link_target = name.split(" -> ", 1)

    _EN_MONTH = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    _CN_MONTH = {
        "1月": 1, "2月": 2, "3月": 3, "4月": 4,
        "5月": 5, "6月": 6, "7月": 7, "8月": 8,
        "9月": 9, "10月": 10, "11月": 11, "12月": 12,
    }

    month_num = 1
    day_num = 1

    if is_chinese:
        cn_m = re.match(r"(\d+)月(\d+)日", date_raw)
        if cn_m:
            month_num = int(cn_m.group(1))
            day_num = int(cn_m.group(2))
    else:
        parts = date_raw.split()
        if len(parts) == 2:
            month_num = _EN_MONTH.get(parts[0], 1)
            day_num = int(parts[1])

    now = time.localtime()
    current_year = now.tm_year

    if ":" in time_or_year:
        hour, minute = time_or_year.split(":")
        modify_ts = time.mktime(
            (current_year, month_num, day_num, int(hour), int(minute), 0, 0, 0, -1)
        )
        if modify_ts > time.time():
            modify_ts = time.mktime(
                (current_year - 1, month_num, day_num, int(hour), int(minute), 0, 0, 0, -1)
            )
        modify_str = f"{current_year}-{month_num:02d}-{day_num:02d} {hour}:{minute}"
    else:
        modify_ts = time.mktime(
            (int(time_or_year), month_num, day_num, 0, 0, 0, 0, 0, -1)
        )
        modify_str = f"{time_or_year}-{month_num:02d}-{day_num:02d} 00:00"

    perm_mode = 0
    for i, ch in enumerate(perm_str[1:10]):
        if ch != "-":
            perm_mode |= 1 << (8 - i)

    full_path = str(PurePosixPath(base_path) / name)

    if name in (".", ".."):
        return None

    return FileEntry(
        name=name,
        path=full_path,
        is_dir=is_dir,
        size=size,
        permissions=perm_str,
        permission_mode=perm_mode,
        modify_time=modify_str,
        modify_timestamp=modify_ts,
        owner=owner,
        group=group,
        link_target=link_target,
    )


def _parse_stat_output(stdout: str, path: str) -> FileDetail:
    lines = stdout.strip().split("\n")
    result: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if line.startswith("文件："):
            result["file"] = line[3:].strip()
        elif line.startswith("大小："):
            m = re.match(r"大小：(\d+)", line)
            if m:
                result["size"] = m.group(1)
        elif line.startswith("Block:"):
            m = re.match(r"Block:\s+(\d+)", line)
            if m:
                result["blocks"] = m.group(1)
        elif line.startswith("设备："):
            result["device"] = line[3:].strip()
        elif line.startswith("Inode："):
            result["inode"] = line[6:].strip()
        elif line.startswith("硬链接："):
            result["links"] = line[4:].strip()
        elif line.startswith("Access："):
            m = re.match(r"Access：\((\d{4})/([^\)]+)\)", line)
            if m:
                result["access_mode"] = m.group(1)
                result["access_perm"] = m.group(2)
        elif line.startswith("Uid："):
            m = re.match(r"Uid：\s*\(\s*(\d+)\)\s*/\s*(\S+)", line)
            if m:
                result["uid"] = m.group(1)
                result["owner"] = m.group(2)
        elif line.startswith("Gid："):
            m = re.match(r"Gid：\s*\(\s*(\d+)\)\s*/\s*(\S+)", line)
            if m:
                result["gid"] = m.group(1)
                result["group"] = m.group(2)
        elif line.startswith("访问时间："):
            result["access_time"] = line[5:].strip()
        elif line.startswith("修改时间："):
            result["modify_time"] = line[5:].strip()
        elif line.startswith("更改时间："):
            result["change_time"] = line[5:].strip()

    size = int(result.get("size", "0"))
    blocks = int(result.get("blocks", "0"))
    owner = result.get("owner", "")
    group = result.get("group", "")
    perm_str = result.get("access_perm", "")

    is_dir = perm_str.startswith("d") if perm_str else False
    is_link = perm_str.startswith("l") if perm_str else False
    is_socket = perm_str.startswith("s") if perm_str else False
    is_fifo = perm_str.startswith("p") if perm_str else False
    is_block = perm_str.startswith("b") if perm_str else False
    is_char = perm_str.startswith("c") if perm_str else False

    perm_mode = 0
    if perm_str:
        for i, ch in enumerate(perm_str[1:10]):
            if ch != "-":
                perm_mode |= 1 << (8 - i)

    return FileDetail(
        path=path,
        is_dir=is_dir,
        is_file=not (is_dir or is_link or is_socket or is_fifo or is_block or is_char),
        is_link=is_link,
        is_socket=is_socket,
        is_fifo=is_fifo,
        is_block_device=is_block,
        is_char_device=is_char,
        size=size,
        blocks=blocks,
        permissions=perm_str,
        permission_mode=perm_mode,
        modify_time=result.get("modify_time", ""),
        modify_timestamp=0.0,
        access_time=result.get("access_time", ""),
        access_timestamp=0.0,
        change_time=result.get("change_time", ""),
        change_timestamp=0.0,
        owner=owner,
        group=group,
        link_target=None,
    )


class RemoteFileManager:
    def __init__(self, manager: SSHClientManager):
        self._manager = manager
        self._is_chinese: Optional[bool] = None

    def _detect_locale(self) -> bool:
        if self._is_chinese is not None:
            return self._is_chinese
        try:
            code, stdout, _ = self._exec("echo $LANG", timeout=5.0)
            if code == 0:
                lang = stdout.strip()
                self._is_chinese = lang.lower().startswith("zh_cn")
            else:
                self._is_chinese = False
        except Exception:
            self._is_chinese = False
        return self._is_chinese

    def _exec(self, command: str, timeout: float = 30.0) -> tuple[int, str, str]:
        code, stdout, stderr = self._manager.exec_command(command, timeout=timeout)
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return code, stdout, stderr

    def _sftp(self) -> paramiko.SFTPClient:
        return self._manager.open_sftp()

    def list_directory(self, path: str) -> list[FileEntry]:
        path = path.rstrip("/") or "/"
        cmd = f"ls -la {shlex.quote(path)}"
        code, stdout, stderr = self._exec(cmd)
        if code != 0:
            if not stderr:
                stderr = f"无法列出目录: {path}"
            raise RuntimeError(stderr.strip())
        entries: list[FileEntry] = []
        is_chinese = self._detect_locale()
        for line in stdout.split("\n"):
            entry = _parse_ls_line(line, path, is_chinese)
            if entry is not None:
                entries.append(entry)
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    def get_file_info(self, path: str) -> FileDetail:
        cmd = f"stat {shlex.quote(path)} 2>/dev/null || stat -x {shlex.quote(path)} 2>/dev/null"
        code, stdout, stderr = self._exec(cmd)
        if code != 0:
            ls_code, ls_stdout, ls_stderr = self._exec(f"ls -la {shlex.quote(path)}")
            if ls_code == 0:
                for line in ls_stdout.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("total"):
                        parts = line.split()
                        if len(parts) >= 9:
                            name = " ".join(parts[8:])
                            if name == path.split("/")[-1]:
                                is_dir = parts[0].startswith("d")
                                size = int(parts[4])
                                return FileDetail(
                                    path=path,
                                    is_dir=is_dir,
                                    is_file=not is_dir,
                                    is_link=parts[0].startswith("l"),
                                    is_socket=False,
                                    is_fifo=False,
                                    is_block_device=False,
                                    is_char_device=False,
                                    size=size,
                                    blocks=0,
                                    permissions=parts[0],
                                    permission_mode=0,
                                    modify_time=f"{parts[5]} {parts[6]}",
                                    modify_timestamp=0.0,
                                    access_time="",
                                    access_timestamp=0.0,
                                    change_time="",
                                    change_timestamp=0.0,
                                    owner=parts[2],
                                    group=parts[3],
                                    link_target=None,
                                )
            raise RuntimeError((stderr or ls_stderr or "无法获取文件信息").strip())
        return _parse_stat_output(stdout, path)

    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        code, stdout, stderr = self._exec(f"cat {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法读取文件: {path}")
        return stdout

    def write_file(self, path: str, content: str) -> None:
        sftp = self._sftp()
        try:
            with sftp.open(path, "w") as f:
                f.write(content.encode("utf-8") if isinstance(content, str) else content)
        except Exception as e:
            raise RuntimeError(f"无法写入文件: {e}")

    def create_file(self, path: str) -> None:
        code, stdout, stderr = self._exec(f"touch {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法创建文件: {path}")

    def create_directory(self, path: str) -> None:
        code, stdout, stderr = self._exec(f"mkdir -p {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法创建目录: {path}")

    def delete(self, path: str) -> None:
        code, stdout, stderr = self._exec(f"rm -rf {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法删除: {path}")

    def rename(self, src: str, dst: str) -> None:
        code, stdout, stderr = self._exec(f"mv {shlex.quote(src)} {shlex.quote(dst)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法重命名: {src} -> {dst}")

    def copy(self, src: str, dst: str) -> None:
        code, stdout, stderr = self._exec(f"cp -r {shlex.quote(src)} {shlex.quote(dst)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法复制: {src} -> {dst}")

    def chmod(self, path: str, mode: str) -> None:
        code, stdout, stderr = self._exec(f"chmod {mode} {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法修改权限: {path}")

    def chown(self, path: str, user: Optional[str] = None, group: Optional[str] = None) -> None:
        owner = f"{user or ''}:{group or ''}" if group else (user or "")
        if not owner:
            raise ValueError("必须指定 user 或 group")
        code, stdout, stderr = self._exec(f"sudo chown {owner} {shlex.quote(path)}")
        if code != 0:
            raise RuntimeError(stderr.strip() or f"无法修改所有者: {path}")

    def upload(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"本地文件不存在: {local_path}")

        remote_dir = str(PurePosixPath(remote_path).parent)
        self.create_directory(remote_dir)

        sftp = self._sftp()
        file_size = local_path.stat().st_size
        transferred = 0

        def _callback(sent: int, total: int) -> None:
            nonlocal transferred
            transferred = sent
            if progress_callback:
                progress_callback(sent, total)

        try:
            sftp.put(str(local_path), remote_path, callback=_callback)
        except Exception as e:
            raise RuntimeError(f"上传失败: {e}")

    def download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        sftp = self._sftp()
        try:
            remote_size = sftp.stat(remote_path).st_size
        except Exception:
            remote_size = 0

        transferred = 0

        def _callback(sent: int, total: int) -> None:
            nonlocal transferred
            transferred = sent
            if progress_callback:
                progress_callback(sent, total)

        try:
            sftp.get(remote_path, str(local_path), callback=_callback)
        except Exception as e:
            raise RuntimeError(f"下载失败: {e}")

    def search(
        self,
        path: str,
        pattern: str,
        max_depth: Optional[int] = None,
        file_type: Optional[str] = None,
    ) -> list[FileSearchResult]:
        depth_arg = f"-maxdepth {max_depth}" if max_depth is not None else ""
        type_arg = ""
        if file_type == "file":
            type_arg = "-type f"
        elif file_type == "directory":
            type_arg = "-type d"

        cmd = (
            f"find {shlex.quote(path)} {depth_arg} {type_arg} "
            f"-name {shlex.quote(pattern)} "
            f"-printf '%y\\t%s\\t%M\\t%TY-%Tm-%Td %TH:%TM\\t%p\\n' "
            f"2>/dev/null"
        )
        code, stdout, stderr = self._exec(cmd)
        if code != 0 and not stdout.strip():
            fallback_cmd = (
                f"find {shlex.quote(path)} {depth_arg} {type_arg} "
                f"-name {shlex.quote(pattern)} -ls 2>/dev/null"
            )
            code, stdout, stderr = self._exec(fallback_cmd)
            if code != 0:
                return []
            return self._parse_find_ls_output(stdout)

        results: list[FileSearchResult] = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 4)
            if len(parts) < 5:
                continue
            file_type_char, size, perm, modify_time, full_path = parts
            full_path = full_path.rstrip("/")
            name = full_path.split("/")[-1] or full_path
            results.append(FileSearchResult(
                path=full_path,
                name=name,
                is_dir=(file_type_char == "d"),
                size=int(size),
                permissions=perm,
                modify_time=modify_time,
            ))
        results.sort(key=lambda r: (not r.is_dir, r.name.lower()))
        return results

    def _parse_find_ls_output(self, stdout: str) -> list[FileSearchResult]:
        results: list[FileSearchResult] = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 11:
                continue
            perm = parts[2]
            nlink = parts[3]
            owner = parts[4]
            group = parts[5]
            size = parts[6]
            month = parts[7]
            day = parts[8]
            time_or_year = parts[9]
            name = " ".join(parts[10:])
            name = name.rstrip("/")
            if " -> " in name:
                name = name.split(" -> ")[0]
            path_only = name
            base_name = name.split("/")[-1] if "/" in name else name
            results.append(FileSearchResult(
                path=path_only,
                name=base_name,
                is_dir=perm.startswith("d"),
                size=int(size) if size.isdigit() else 0,
                permissions=perm,
                modify_time=f"{month} {day} {time_or_year}",
            ))
        return results

    def exec_command(self, command: str, timeout: float = 30.0) -> dict:
        code, stdout, stderr = self._exec(command, timeout=timeout)
        return {
            "exit_code": code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
        }

    def exec_batch(self, commands: list[str], timeout: float = 60.0) -> list[dict]:
        results: list[dict] = []
        joined = " && ".join(commands)
        code, stdout, stderr = self._exec(joined, timeout=timeout)
        return [
            {
                "command": cmd,
                "exit_code": code if i == len(commands) - 1 else 0,
                "stdout": stdout if i == len(commands) - 1 else "",
                "stderr": stderr if i == len(commands) - 1 else "",
            }
            for i, cmd in enumerate(commands)
        ]
