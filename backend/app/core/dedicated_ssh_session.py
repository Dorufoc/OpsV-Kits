from __future__ import annotations

import asyncio
import os
import socket
from pathlib import Path
from typing import Optional

import paramiko

from app.models.ssh_account import SSHAccount

HOST_KEY_POLICY_AUTO = "auto"
HOST_KEY_POLICY_ADD = "add"
HOST_KEY_POLICY_ACCEPT = "accept"

_KNOWN_HOSTS_PATH = Path.home() / ".ssh" / "known_hosts"

_BACKOFF_DELAYS = (5.0, 10.0, 20.0, 30.0)


class DedicatedSSHSession:
    def __init__(self, account: SSHAccount, keepalive_interval: int = 60):
        self._account = account
        self._keepalive_interval = keepalive_interval
        self._client: Optional[paramiko.SSHClient] = None
        self._transport: Optional[paramiko.Transport] = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._closed = False
        self._online = False
        self._encoding: Optional[str] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._backoff_index = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_online(self) -> bool:
        return self._online

    async def connect(self, timeout: float = 15.0) -> bool:
        async with self._lock:
            if self._connected or self._closed:
                return self._connected
            return await self._do_connect_locked(timeout)

    async def _do_connect_locked(self, timeout: float) -> bool:
        self._client = paramiko.SSHClient()
        self._apply_host_key_policy()
        client = self._client
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.connect(
                    hostname=self._account.host,
                    port=self._account.port,
                    username=self._account.username,
                    password=self._resolve_password(),
                    pkey=self._load_private_key(),
                    look_for_keys=False,
                    allow_agent=(self._account.auth_type == "agent"),
                    timeout=timeout,
                    compress=True,
                ),
            )
            self._transport = client.get_transport()
            if self._transport is not None:
                self._transport.set_keepalive(self._keepalive_interval)
            self._detect_encoding()
            self._connected = True
            self._online = True
            self._backoff_index = 0
            return True
        except Exception:
            self._cleanup_client()
            self._connected = False
            self._online = False
            return False

    def _apply_host_key_policy(self) -> None:
        client = self._client
        if client is None:
            return
        _ensure_known_hosts_dir()
        policy = self._account.auth_type
        if policy == HOST_KEY_POLICY_AUTO:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        elif policy == HOST_KEY_POLICY_ACCEPT:
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.load_system_host_keys(str(_KNOWN_HOSTS_PATH))
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _resolve_password(self) -> Optional[str]:
        if self._account.auth_type == "password":
            return self._account.password or None
        return None

    def _load_private_key(self) -> Optional[paramiko.PKey]:
        if self._account.auth_type != "key":
            return None
        key_path = self._account.private_key
        if not key_path:
            return None
        key_path = os.path.expanduser(key_path)
        if not os.path.isfile(key_path):
            return None
        passphrase = self._account.key_passphrase or None
        for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
            try:
                if passphrase:
                    return key_cls.from_private_key_file(key_path, password=passphrase)
                return key_cls.from_private_key_file(key_path)
            except paramiko.SSHException:
                continue
            except FileNotFoundError:
                break
        return None

    def _detect_encoding(self) -> None:
        if self._transport is None:
            self._encoding = "utf-8"
            return
        try:
            _, stdout, _ = self._client.exec_command("locale charmap", timeout=5.0)
            raw = stdout.read().strip()
            if raw:
                self._encoding = raw.decode("ascii", errors="replace")
                return
        except Exception:
            pass
        try:
            _, stdout, _ = self._client.exec_command("echo $LANG", timeout=5.0)
            raw = stdout.read().strip()
            if raw:
                lang = raw.decode("ascii", errors="replace")
                parts = lang.split(".")
                if len(parts) > 1:
                    self._encoding = parts[1]
                    return
        except Exception:
            pass
        self._encoding = "utf-8"

    async def exec_command(self, command: str, timeout: float = 5.0) -> tuple[int, str, str]:
        async with self._lock:
            if not self._connected or self._client is None:
                if not self._closed and not self._online:
                    return (-1, "", "SSH 未连接，设备离线")
                return (-1, "", "SSH 未连接")

            try:
                result = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        None, self._sync_exec_command, command, timeout
                    ),
                    timeout=timeout + 5.0,
                )
                if not self._online:
                    self._online = True
                    self._backoff_index = 0
                return result
            except asyncio.TimeoutError:
                return (-1, "", f"命令执行超时 (>{timeout}s)")
            except (socket.timeout, OSError, paramiko.SSHException) as e:
                self._connected = False
                self._online = False
                self._cleanup_transport()
                self._schedule_reconnect()
                return (-1, "", f"网络断开: {e}")
            except Exception as e:
                return (-1, "", f"命令执行异常: {e}")

    def _sync_exec_command(self, command: str, timeout: float) -> tuple[int, str, str]:
        transport = self._client.get_transport()
        chan = transport.open_session(timeout=timeout)
        try:
            chan.exec_command(command)
            exit_code = chan.recv_exit_status()
            stdout_data = self._read_channel(chan.makefile("r", -1))
            stderr_data = self._read_channel(chan.makefile_stderr("r", -1))
            return exit_code, stdout_data, stderr_data
        finally:
            chan.close()

    def _read_channel(self, stream) -> str:
        try:
            data = stream.read()
            if isinstance(data, bytes):
                return data.decode(self._encoding or "utf-8", errors="replace")
            return data
        except Exception:
            return ""

    def _schedule_reconnect(self) -> None:
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        while not self._closed and not self._connected:
            delay = _BACKOFF_DELAYS[
                min(self._backoff_index, len(_BACKOFF_DELAYS) - 1)
            ]
            await asyncio.sleep(delay)
            if self._closed or self._connected:
                break
            async with self._lock:
                if self._closed or self._connected:
                    break
                success = await self._do_connect_locked(timeout=15.0)
                if success:
                    self._online = True
                    self._backoff_index = 0
                    break
                else:
                    self._backoff_index += 1

    def close(self) -> None:
        self._closed = True
        self._connected = False
        self._online = False
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        self._cleanup_transport()
        self._cleanup_client()

    def _cleanup_transport(self) -> None:
        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None

    def _cleanup_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def _ensure_known_hosts_dir() -> None:
    _KNOWN_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _KNOWN_HOSTS_PATH.exists():
        _KNOWN_HOSTS_PATH.touch(exist_ok=True)
