from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Optional

import paramiko
from webssh.handler import SSHClient as WebSSHClient, PrivateKey
from webssh.policy import AutoAddPolicy
from webssh.utils import to_str

logger = logging.getLogger(__name__)

BUF_SIZE = 32 * 1024


def create_webssh_client(
    host: str,
    port: int,
    username: str,
    password: Optional[str] = None,
    private_key: Optional[str] = None,
    key_passphrase: Optional[str] = None,
    totp: Optional[str] = None,
    timeout: float = 15.0,
) -> tuple[paramiko.SSHClient, paramiko.Channel, str]:
    ssh = WebSSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.load_system_host_keys()

    pkey = None
    if private_key:
        pk = PrivateKey(private_key, key_passphrase)
        pkey = pk.get_pkey_obj()

    ssh.totp = totp or ""
    args = (host, port, username, password, pkey)
    ssh.connect(*args, timeout=timeout)

    encoding = _detect_encoding(ssh)
    chan = ssh.invoke_shell(term="xterm-256color")
    chan.setblocking(0)
    return ssh, chan, encoding


def _detect_encoding(ssh: paramiko.SSHClient) -> str:
    commands = [
        '$SHELL -ilc "locale charmap"',
        '$SHELL -ic "locale charmap"',
    ]
    for cmd in commands:
        try:
            _, stdout, _ = ssh.exec_command(cmd, get_pty=True, timeout=1)
            data = stdout.read()
            if data:
                encoding = to_str(data.strip(), "ascii")
                if encoding:
                    try:
                        "test".encode(encoding)
                        return encoding
                    except (LookupError, ValueError):
                        pass
        except Exception:
            continue
    return "utf-8"


class WebSSHSession:
    def __init__(
        self,
        session_id: str,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_passphrase: Optional[str] = None,
        totp: Optional[str] = None,
    ):
        self.session_id = session_id
        self.host = host
        self.port = port
        self.username = username
        self._password = password
        self._private_key = private_key
        self._key_passphrase = key_passphrase
        self._totp = totp
        self._ssh: Optional[paramiko.SSHClient] = None
        self._chan: Optional[paramiko.Channel] = None
        self.encoding: str = "utf-8"
        self._connected = False
        self._closed = False
        self._output_callback: Optional[Callable[[bytes], None]] = None
        self._reader_thread: Optional[threading.Thread] = None

    def connect(self, timeout: float = 15.0) -> None:
        logger.info(f"[{self.session_id}] connecting to {self.host}:{self.port} as {self.username}")
        ssh = WebSSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.load_system_host_keys()

        pkey = None
        if self._private_key:
            pk = PrivateKey(self._private_key, self._key_passphrase)
            pkey = pk.get_pkey_obj()

        ssh.totp = self._totp or ""

        args = (self.host, self.port, self.username, self._password, pkey)
        ssh.connect(*args, timeout=timeout)
        logger.info(f"[{self.session_id}] SSH connected successfully")

        self.encoding = _detect_encoding(ssh)
        logger.info(f"[{self.session_id}] detected encoding: {self.encoding}")
        chan = ssh.invoke_shell(term="xterm-256color")
        chan.setblocking(0)
        logger.info(f"[{self.session_id}] shell channel opened")

        self._ssh = ssh
        self._chan = chan
        self._connected = True

    def start_reader(self, callback: Callable[[bytes], None]) -> None:
        self._output_callback = callback
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True,
            name=f"webssh-reader-{self.session_id}"
        )
        self._reader_thread.start()
        logger.info(f"[{self.session_id}] reader thread started")

    def _reader_loop(self) -> None:
        chan = self._chan
        if chan is None:
            logger.warning(f"[{self.session_id}] reader loop: chan is None, exiting")
            return
        try:
            while self._connected and not self._closed:
                if chan.recv_ready():
                    data = chan.recv(BUF_SIZE)
                    if data:
                        logger.debug(f"[{self.session_id}] received {len(data)} bytes from SSH")
                        if self._output_callback:
                            self._output_callback(data)
                    else:
                        logger.info(f"[{self.session_id}] chan.recv returned empty, breaking")
                        break
                elif chan.exit_status_ready():
                    logger.info(f"[{self.session_id}] SSH channel exit_status_ready")
                    break
                else:
                    time.sleep(0.01)
        except Exception as e:
            logger.error(f"[{self.session_id}] reader loop error: {e}")
        finally:
            self._connected = False
            if self._output_callback:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self._output_callback(b"__SSH_DISCONNECTED__"),
                            loop,
                        )
                except (RuntimeError, Exception):
                    pass

    def write(self, data: bytes) -> None:
        if not self._connected or self._closed or self._chan is None:
            logger.warning(f"[{self.session_id}] write called but not connected")
            return
        try:
            sent = self._chan.send(data)
            logger.debug(f"[{self.session_id}] sent {sent} bytes to SSH")
        except Exception as e:
            logger.error(f"[{self.session_id}] write error: {e}")
            pass

    def resize_pty(self, width: int, height: int) -> None:
        if not self._connected or self._closed or self._chan is None:
            return
        try:
            self._chan.resize_pty(width=width, height=height)
            logger.debug(f"[{self.session_id}] resized pty to {width}x{height}")
        except Exception:
            pass

    def close(self) -> None:
        logger.info(f"[{self.session_id}] closing session")
        self._closed = True
        self._connected = False
        if self._output_callback:
            try:
                self._output_callback(b"__SSH_DISCONNECTED__")
            except Exception:
                pass
        if self._chan:
            try:
                self._chan.close()
            except Exception:
                pass
            self._chan = None
        if self._ssh:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None

    def check_health(self) -> bool:
        if self._closed or not self._connected:
            return False
        if self._ssh is None or self._chan is None:
            return False
        try:
            t = self._ssh.get_transport()
            return t is not None and t.is_active()
        except Exception:
            return False
