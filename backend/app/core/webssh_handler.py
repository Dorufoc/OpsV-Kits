from __future__ import annotations

import asyncio
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

import paramiko

from app.models.ssh_account import SSHAccount

_KNOWN_HOSTS_PATH = Path.home() / ".ssh" / "known_hosts"

_READ_BUFFER_SIZE = 1024 * 32
_CHANNEL_READ_TIMEOUT = 0.05
_HEALTHCHECK_INTERVAL = 15.0
_HEALTHCHECK_TIMEOUT = 5.0


class WebSSHHandler:
    def __init__(
        self,
        session_id: str,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_passphrase: Optional[str] = None,
        auth_type: str = "password",
        keepalive_interval: int = 30,
    ):
        self.session_id = session_id
        self.host = host
        self.port = port
        self.username = username
        self._password = password
        self._private_key_path = private_key
        self._key_passphrase = key_passphrase
        self._auth_type = auth_type
        self._keepalive_interval = keepalive_interval

        self._client: Optional[paramiko.SSHClient] = None
        self._channel: Optional[paramiko.Channel] = None
        self._transport: Optional[paramiko.Transport] = None
        self._lock = threading.RLock()
        self._connected = False
        self._closed = False
        self._encoding: str = "utf-8"

        self._reader_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None

        self._output_queue: Optional[asyncio.Queue[bytes]] = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def encoding(self) -> str:
        return self._encoding

    def connect(self, timeout: float = 15.0) -> None:
        with self._lock:
            if self._connected:
                return

            self._client = paramiko.SSHClient()
            self._apply_host_key_policy()

            client = self._client
            pkey = self._load_private_key() if self._auth_type == "key" else None
            password = self._password if self._auth_type == "password" else None

            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=password,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=(self._auth_type == "agent"),
                timeout=timeout,
                compress=True,
            )

            self._transport = client.get_transport()
            if self._transport is not None:
                self._transport.set_keepalive(self._keepalive_interval)

            self._channel = client.invoke_shell(term="xterm-256color")
            self._channel.settimeout(_CHANNEL_READ_TIMEOUT)

            self._detect_encoding()
            self._connected = True
            self._closed = False

    def _apply_host_key_policy(self) -> None:
        client = self._client
        if client is None:
            return
        _ensure_known_hosts_dir()
        if self._auth_type == "accept":
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.load_system_host_keys(str(_KNOWN_HOSTS_PATH))
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _load_private_key(self) -> Optional[paramiko.PKey]:
        key_path = self._private_key_path
        if not key_path:
            return None
        key_path = os.path.expanduser(key_path)
        if not os.path.isfile(key_path):
            return None
        passphrase = self._key_passphrase or None
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
        client = self._client
        if client is None:
            self._encoding = "utf-8"
            return
        try:
            _, stdout, _ = client.exec_command("locale charmap", timeout=5.0)
            raw = stdout.read().strip()
            if raw:
                detected = raw.decode("ascii", errors="replace")
                if detected:
                    self._encoding = detected
                    return
        except Exception:
            pass
        try:
            _, stdout, _ = client.exec_command("echo $LANG", timeout=5.0)
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

    def start_reader(self, output_queue: asyncio.Queue[bytes]) -> None:
        self._output_queue = output_queue

        def _read():
            channel = self._channel
            if channel is None:
                return
            try:
                while self._connected and not self._closed:
                    if channel.recv_ready():
                        data = channel.recv(_READ_BUFFER_SIZE)
                        if data:
                            try:
                                future = asyncio.run_coroutine_threadsafe(
                                    output_queue.put(data),
                                    asyncio.get_event_loop(),
                                )
                                future.result(timeout=5.0)
                            except Exception:
                                pass
                        else:
                            break
                    elif channel.closed:
                        break
                    else:
                        time.sleep(_CHANNEL_READ_TIMEOUT)
            except Exception:
                pass
            finally:
                self._connected = False
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        output_queue.put(b"__SSH_DISCONNECTED__"),
                        asyncio.get_event_loop(),
                    )
                    future.result(timeout=5.0)
                except Exception:
                    pass

        self._reader_thread = threading.Thread(target=_read, daemon=True, name=f"ssh-reader-{self.session_id}")
        self._reader_thread.start()
        self._start_keepalive()

    def _start_keepalive(self) -> None:
        def _ping():
            while self._connected and not self._closed:
                time.sleep(self._keepalive_interval)
                try:
                    transport = self._transport
                    if transport is None or not transport.is_active():
                        self._connected = False
                        break
                    transport.send_ignore()
                except Exception:
                    self._connected = False
                    break

        self._keepalive_thread = threading.Thread(
            target=_ping, daemon=True, name=f"ssh-keepalive-{self.session_id}"
        )
        self._keepalive_thread.start()

    def write(self, data: bytes) -> None:
        if not self._connected or self._channel is None:
            return
        with self._lock:
            try:
                self._channel.send(data)
            except Exception:
                self._connected = False

    def resize_pty(self, width: int, height: int) -> None:
        if not self._connected or self._channel is None:
            return
        with self._lock:
            try:
                self._channel.resize_pty(width=width, height=height)
            except Exception:
                pass

    def check_health(self) -> bool:
        if self._closed:
            return False
        if not self._connected:
            return False
        try:
            transport = self._transport
            if transport is None or not transport.is_active():
                self._connected = False
                return False
            return True
        except Exception:
            self._connected = False
            return False

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._connected = False
            if self._channel is not None:
                try:
                    self._channel.close()
                except Exception:
                    pass
                self._channel = None
            if self._transport is not None:
                try:
                    self._transport.close()
                except Exception:
                    pass
                self._transport = None
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None

    @classmethod
    def from_account(cls, session_id: str, account: SSHAccount) -> WebSSHHandler:
        return cls(
            session_id=session_id,
            host=account.host,
            port=account.port,
            username=account.username,
            password=account.password if account.auth_type == "password" else None,
            private_key=account.private_key if account.auth_type == "key" else None,
            key_passphrase=account.key_passphrase,
            auth_type=account.auth_type,
        )


def _ensure_known_hosts_dir() -> None:
    _KNOWN_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
