from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Optional

from app.core.ssh_client import SSHClientManager


@dataclass
class UserInfo:
    username: str
    uid: int
    gid: int
    groups: list[dict] = field(default_factory=list)
    home: str = ""
    shell: str = ""
    is_root: bool = False


@dataclass
class FilePermissions:
    path: str
    exists: bool
    readable: bool
    writable: bool
    executable: bool
    permission_str: str
    permission_mode: int
    owner: str
    group: str
    current_user: str


class PermissionChecker:
    def __init__(self, manager: SSHClientManager):
        self._manager = manager

    def _exec(self, command: str, timeout: float = 15.0) -> tuple[int, str, str]:
        code, stdout, stderr = self._manager.exec_command(command, timeout=timeout)
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return code, stdout, stderr

    @staticmethod
    def _shell_path(path: str) -> str:
        if path.startswith("~"):
            remainder = path[1:]
            if remainder:
                return f"$HOME{shlex.quote(remainder)}"
            return "$HOME"
        return shlex.quote(path)

    def check_read_access(self, path: str) -> bool:
        code, _, _ = self._exec(f"test -r {self._shell_path(path)}")
        return code == 0

    def check_exists(self, path: str) -> bool:
        code, _, _ = self._exec(f"test -e {self._shell_path(path)}")
        return code == 0

    def check_write_access(self, path: str) -> bool:
        code, _, _ = self._exec(f"test -w {self._shell_path(path)}")
        return code == 0

    def check_execute_access(self, path: str) -> bool:
        code, _, _ = self._exec(f"test -x {self._shell_path(path)}")
        return code == 0

    def check_sudo_access(self) -> bool:
        code, _, _ = self._exec("sudo -n true 2>/dev/null")
        return code == 0

    def get_current_user(self) -> UserInfo:
        code, stdout, stderr = self._exec("id 2>/dev/null")
        if code != 0:
            code, stdout, stderr = self._exec("whoami")
            username = stdout.strip() or "unknown"
            return UserInfo(username=username, uid=0, gid=0, is_root=(username == "root"))

        info = self._parse_id_output(stdout.strip())

        _, stdout2, _ = self._exec("echo $HOME")
        info.home = stdout2.strip() or f"/home/{info.username}"

        _, stdout3, _ = self._exec("echo $SHELL")
        info.shell = stdout3.strip() or "/bin/bash"

        return info

    def get_file_permissions(self, path: str) -> FilePermissions:
        exists = False

        code, _, _ = self._exec(f"test -e {self._shell_path(path)}")
        exists = code == 0

        readable = False
        writable = False
        executable = False

        if exists:
            code, _, _ = self._exec(f"test -r {self._shell_path(path)}")
            readable = code == 0

            code, _, _ = self._exec(f"test -w {self._shell_path(path)}")
            writable = code == 0

            code, _, _ = self._exec(f"test -x {self._shell_path(path)}")
            executable = code == 0

        perm_str = ""
        perm_mode = 0
        owner = ""
        group = ""
        current_user = ""

        if exists:
            code, stdout, _ = self._exec(
                f"stat -c '%a %A %U %G' {self._shell_path(path)} 2>/dev/null || "
                f"stat -f '%Sp %u %g' {self._shell_path(path)} 2>/dev/null"
            )
            if code == 0:
                parts = stdout.strip().split()
                if len(parts) >= 4:
                    perm_mode = int(parts[0], 8) if parts[0].isdigit() else 0
                    perm_str = parts[1] if len(parts) > 1 else ""
                    owner = parts[2] if len(parts) > 2 else ""
                    group = parts[3] if len(parts) > 3 else ""
                elif len(parts) >= 3:
                    perm_str = parts[0]
                    owner = parts[1]
                    group = parts[2]
            else:
                code, stdout, _ = self._exec(f"ls -la -d {self._shell_path(path)} 2>/dev/null")
                if code == 0 and stdout.strip():
                    parts = stdout.strip().split()
                    if len(parts) >= 8:
                        perm_str = parts[0]
                        owner = parts[2]
                        group = parts[3]

        code, stdout, _ = self._exec("whoami")
        current_user = stdout.strip()

        return FilePermissions(
            path=path,
            exists=exists,
            readable=readable,
            writable=writable,
            executable=executable,
            permission_str=perm_str,
            permission_mode=perm_mode,
            owner=owner,
            group=group,
            current_user=current_user,
        )

    def _parse_id_output(self, output: str) -> UserInfo:
        username = "unknown"
        uid = 0
        gid = 0
        groups: list[dict] = []
        is_root = False

        m = re.match(r"uid=(\d+)\((\S+)\)\s+gid=(\d+)\((\S+)\)\s+(.*)", output)
        if m:
            uid = int(m.group(1))
            username = m.group(2)
            gid = int(m.group(3))
            groups_str = m.group(5)
            for g in re.finditer(r"(\d+)\((\S+)\)", groups_str):
                groups.append({"gid": int(g.group(1)), "name": g.group(2)})
        else:
            username = output.strip()

        is_root = username == "root" or uid == 0

        return UserInfo(
            username=username,
            uid=uid,
            gid=gid,
            groups=groups,
            is_root=is_root,
        )
