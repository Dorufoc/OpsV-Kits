from __future__ import annotations

import time
from typing import Callable, Optional

from app.services.ssh_account_service import ssh_account_service
from app.core.ssh_pool import SSHConnectionPool
from app.core.ssh_utils import resolve_remote_path


class RemoteExecutorError(Exception):
    pass


class CommandResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def __repr__(self) -> str:
        return (
            f"CommandResult(exit_code={self.exit_code}, "
            f"stdout={self.stdout[:80]!r}..., "
            f"stderr={self.stderr[:80]!r}...)"
        )


class RemoteExecutor:
    def __init__(self, account_alias: str):
        self._account_alias = account_alias
        self._account = ssh_account_service.get_account(account_alias)
        if self._account is None:
            raise RemoteExecutorError(f"SSH 账户 '{account_alias}' 不存在")
        self._pool = ssh_account_service.pool

    @property
    def account_alias(self) -> str:
        return self._account_alias

    def resolve_path(self, path: str) -> str:
        if not path.startswith("~"):
            return path
        conn = None
        try:
            conn = self._pool.get_connection(self._account, timeout=10.0)
            return resolve_remote_path(
                conn.manager.client, path, self._account.username
            )
        except Exception:
            fallback = f"/home/{self._account.username}" if self._account.username != "root" else "/root"
            return path.replace("~", fallback, 1)
        finally:
            if conn:
                self._pool.release_connection(conn)

    def exec_command(
        self,
        command: str,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        if timeout is None:
            timeout = 30.0
        conn = None
        try:
            conn = self._pool.get_connection(self._account, timeout=timeout)
            exit_code, stdout, stderr = conn.manager.exec_command(
                command, timeout=timeout
            )
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return CommandResult(
                exit_code=exit_code,
                stdout=stdout.strip(),
                stderr=stderr.strip(),
            )
        except Exception as e:
            raise RemoteExecutorError(
                f"命令执行失败: {command[:80]!r}: {e}"
            ) from e
        finally:
            if conn is not None:
                self._pool.release_connection(conn)

    def exec_commands(
        self,
        commands: list[str],
        command_timeout: Optional[float] = None,
    ) -> list[CommandResult]:
        results: list[CommandResult] = []
        for cmd in commands:
            result = self.exec_command(cmd, timeout=command_timeout)
            results.append(result)
        return results

    def exec_with_pty(
        self,
        command: str,
        timeout: Optional[float] = None,
        term: str = "xterm",
    ) -> CommandResult:
        if timeout is None:
            timeout = 60.0
        conn = None
        try:
            conn = self._pool.get_connection(self._account, timeout=timeout)
            exit_code, stdout, stderr = conn.manager.exec_with_pty(
                command, timeout=timeout, term=term
            )
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return CommandResult(
                exit_code=exit_code,
                stdout=stdout.strip(),
                stderr=stderr.strip(),
            )
        except Exception as e:
            raise RemoteExecutorError(
                f"PTY 命令执行失败: {command[:80]!r}: {e}"
            ) from e
        finally:
            if conn is not None:
                self._pool.release_connection(conn)

    def exec_command_stream(
        self,
        command: str,
        output_callback: Callable[[str], None],
        timeout: float = 300.0,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> int:
        conn = None
        try:
            conn = self._pool.get_connection(self._account, timeout=15.0)
            encoding = conn.manager.encoding or "utf-8"
            transport = conn.manager.transport
            if transport is None:
                raise RemoteExecutorError("SSH 传输通道未建立")

            chan = transport.open_session(timeout=timeout)
            chan.exec_command(command)

            while not chan.exit_status_ready():
                if stop_check and stop_check():
                    chan.close()
                    return -1

                if chan.recv_ready():
                    data = chan.recv(4096)
                    if data:
                        output_callback(data.decode(encoding, errors="replace"))

                if chan.recv_stderr_ready():
                    data = chan.recv_stderr(4096)
                    if data:
                        output_callback(data.decode(encoding, errors="replace"))

                time.sleep(0.05)

            while chan.recv_ready():
                data = chan.recv(4096)
                if data:
                    output_callback(data.decode(encoding, errors="replace"))

            while chan.recv_stderr_ready():
                data = chan.recv_stderr(4096)
                if data:
                    output_callback(data.decode(encoding, errors="replace"))

            exit_code = chan.recv_exit_status()
            chan.close()
            return exit_code
        except Exception as e:
            raise RemoteExecutorError(
                f"流式命令执行失败: {command[:80]!r}: {e}"
            ) from e
        finally:
            if conn is not None:
                self._pool.release_connection(conn)

    def test_connection(self, timeout: float = 10.0) -> tuple[bool, str]:
        from app.core.ssh_client import SSHClientManager

        manager = SSHClientManager(self._account)
        return manager.test_connection(timeout)
