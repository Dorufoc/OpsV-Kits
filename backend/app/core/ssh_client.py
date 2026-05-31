from __future__ import annotations

import io
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

import paramiko

from app.models.ssh_account import SSHAccount

HOST_KEY_POLICY_AUTO = "auto"
HOST_KEY_POLICY_ADD = "add"
HOST_KEY_POLICY_ACCEPT = "accept"

_KNOWN_HOSTS_PATH = Path.home() / ".ssh" / "known_hosts"


class SSHClientManager:
    def __init__(self, account: SSHAccount, keepalive_interval: int = 30):
        self._account = account
        self._keepalive_interval = keepalive_interval
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._transport: Optional[paramiko.Transport] = None
        self._lock = threading.RLock()
        self._connected = False
        self._closed = False
        self._encoding: Optional[str] = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def encoding(self) -> Optional[str]:
        return self._encoding

    @property
    def transport(self) -> Optional[paramiko.Transport]:
        return self._transport

    @property
    def client(self) -> Optional[paramiko.SSHClient]:
        return self._client

    def connect(self, timeout: float = 15.0) -> None:
        with self._lock:
            if self._connected:
                return
            self._client = paramiko.SSHClient()
            self._apply_host_key_policy()
            client = self._client
            client.connect(
                hostname=self._account.host,
                port=self._account.port,
                username=self._account.username,
                password=self._resolve_password(),
                pkey=self._load_private_key(),
                look_for_keys=False,
                allow_agent=(self._account.auth_type == "agent"),
                timeout=timeout,
                compress=True,
            )
            self._transport = client.get_transport()
            if self._transport is not None:
                self._transport.set_keepalive(self._keepalive_interval)
            self._detect_encoding()
            self._connected = True
            self._closed = False
            self._start_keepalive()

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
            client.set_missing_host_key_policy(paramiko.WarningPolicy())

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

    def _start_keepalive(self) -> None:
        def _ping():
            while self._connected and not self._closed:
                time.sleep(self._keepalive_interval)
                try:
                    self._client.exec_command("echo keepalive", timeout=10.0)
                except Exception:
                    self._connected = False
                    break

        t = threading.Thread(target=_ping, daemon=True)
        t.start()

    def exec_command(
        self,
        command: str,
        timeout: float = 30.0,
        environment: Optional[dict[str, str]] = None,
    ) -> tuple[int, str, str]:
        if not self._connected or self._client is None:
            raise RuntimeError("SSH 未连接")
        with self._lock:
            chan = self._client.get_transport().open_session(timeout=timeout)
            if environment:
                for k, v in environment.items():
                    chan.set_environment_variable(k, v)
            chan.exec_command(command)
            exit_code = chan.recv_exit_status()
            stdout_data = _read_channel(chan.makefile("r", -1))
            stderr_data = _read_channel(chan.makefile_stderr("r", -1))
            chan.close()
        return exit_code, stdout_data, stderr_data

    def exec_with_pty(
        self,
        command: str,
        timeout: float = 30.0,
        term: str = "xterm",
        environment: Optional[dict[str, str]] = None,
    ) -> tuple[int, str, str]:
        if not self._connected or self._client is None:
            raise RuntimeError("SSH 未连接")
        with self._lock:
            chan = self._transport.open_session(timeout=timeout)
            if environment:
                for k, v in environment.items():
                    chan.set_environment_variable(k, v)
            chan.get_pty(term=term)
            chan.exec_command(command)
            exit_code = chan.recv_exit_status()
            stdout_data = _read_channel(chan.makefile("r", -1))
            stderr_data = _read_channel(chan.makefile_stderr("r", -1))
            chan.close()
        return exit_code, stdout_data, stderr_data

    def open_sftp(self) -> paramiko.SFTPClient:
        if not self._connected or self._client is None:
            raise RuntimeError("SSH 未连接")
        if self._sftp is None or self._sftp.sock.closed:
            self._sftp = self._client.open_sftp()
        return self._sftp

    def close_sftp(self) -> None:
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._connected = False
            self.close_sftp()
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

    def test_connection(self, timeout: float = 10.0) -> tuple[bool, str]:
        try:
            test_client = paramiko.SSHClient()
            test_client.load_system_host_keys(str(_KNOWN_HOSTS_PATH))
            test_client.set_missing_host_key_policy(paramiko.RejectPolicy())
            password = self._resolve_password()
            pkey = self._load_private_key()
            test_client.connect(
                hostname=self._account.host,
                port=self._account.port,
                username=self._account.username,
                password=password,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=(self._account.auth_type == "agent"),
                timeout=timeout,
            )
            test_client.close()
            return True, "连接成功"
        except paramiko.AuthenticationException as e:
            return False, f"身份认证失败: {e}"
        except paramiko.SSHException as e:
            err_msg = str(e)
            if "not found in known_hosts" in err_msg.lower() or "host key" in err_msg.lower():
                return False, "主机密钥验证失败：该主机不在 known_hosts 中。请先在系统 known_hosts 中添加主机密钥，或将主机密钥策略设置为 'auto'。"
            return False, f"SSH 错误: {e}"
        except socket.timeout:
            return False, "连接超时"
        except socket.gaierror:
            return False, "主机地址无法解析"
        except OSError as e:
            return False, f"网络错误: {e}"
        except Exception as e:
            return False, f"连接失败: {e}"


def verify_totp(totp_secret: str, code: str) -> bool:
    raise NotImplementedError(
        "TOTP 验证需要 pyotp 库。"
        "请安装: pip install pyotp"
    )


def _read_channel(stream: io.IOBase) -> str:
    try:
        return stream.read()
    except Exception:
        return ""


def _ensure_known_hosts_dir() -> None:
    _KNOWN_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _KNOWN_HOSTS_PATH.exists():
        _KNOWN_HOSTS_PATH.touch(exist_ok=True)
    if os.name == "nt":
        import stat
        os.chmod(str(_KNOWN_HOSTS_PATH), stat.S_IRUSR | stat.S_IWUSR)
    else:
        os.chmod(str(_KNOWN_HOSTS_PATH), 0o600)
