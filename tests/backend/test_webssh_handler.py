from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.webssh_handler import (
    _CHANNEL_READ_TIMEOUT,
    _HEALTHCHECK_INTERVAL,
    _KNOWN_HOSTS_PATH,
    _READ_BUFFER_SIZE,
    WebSSHHandler,
    _ensure_known_hosts_dir,
)
from app.models.ssh_account import SSHAccount


@pytest.fixture
def handler():
    return WebSSHHandler(
        session_id="test-session",
        host="1.2.3.4",
        port=22,
        username="root",
        password="secret",
        auth_type="password",
    )


@pytest.fixture
def handler_key():
    return WebSSHHandler(
        session_id="test-session-key",
        host="1.2.3.4",
        port=22,
        username="root",
        private_key="/home/user/.ssh/id_rsa",
        auth_type="key",
    )


@pytest.fixture
def handler_agent():
    return WebSSHHandler(
        session_id="test-session-agent",
        host="1.2.3.4",
        port=22,
        username="root",
        auth_type="agent",
    )


class TestWebSSHHandlerInit:
    def test_init_defaults(self, handler):
        assert handler.session_id == "test-session"
        assert handler.host == "1.2.3.4"
        assert handler.port == 22
        assert handler.username == "root"
        assert handler._password == "secret"
        assert handler._auth_type == "password"
        assert handler._connected is False
        assert handler._closed is False
        assert handler._encoding == "utf-8"
        assert handler._client is None
        assert handler._channel is None
        assert handler._transport is None

    def test_init_key_auth(self, handler_key):
        assert handler_key._auth_type == "key"
        assert handler_key._private_key_path == "/home/user/.ssh/id_rsa"
        assert handler_key._password is None

    def test_init_agent_auth(self, handler_agent):
        assert handler_agent._auth_type == "agent"
        assert handler_agent._private_key_path is None
        assert handler_agent._password is None

    def test_init_keepalive(self):
        h = WebSSHHandler("s1", "h", 22, "u", keepalive_interval=60)
        assert h._keepalive_interval == 60


class TestProperties:
    def test_connected_property(self, handler):
        assert handler.connected is False
        handler._connected = True
        assert handler.connected is True

    def test_closed_property(self, handler):
        assert handler.closed is False
        handler._closed = True
        assert handler.closed is True

    def test_encoding_property(self, handler):
        assert handler.encoding == "utf-8"
        handler._encoding = "gbk"
        assert handler.encoding == "gbk"


class TestConnect:
    @patch("app.core.webssh_handler.paramiko.SSHClient")
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    def test_connect_password_auth(self, mock_ensure, mock_client_cls, handler):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_transport = MagicMock()
        mock_client.get_transport.return_value = mock_transport
        mock_channel = MagicMock()
        mock_client.invoke_shell.return_value = mock_channel

        with patch.object(handler, "_detect_encoding"):
            handler.connect(timeout=10.0)

        mock_client.connect.assert_called_once_with(
            hostname="1.2.3.4",
            port=22,
            username="root",
            password="secret",
            pkey=None,
            look_for_keys=False,
            allow_agent=False,
            timeout=10.0,
            compress=True,
        )
        assert handler._connected is True
        assert handler._closed is False
        mock_transport.set_keepalive.assert_called_once_with(30)
        mock_client.invoke_shell.assert_called_once_with(term="xterm-256color")

    @patch("app.core.webssh_handler.paramiko.SSHClient")
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    def test_connect_key_auth(self, mock_ensure, mock_client_cls, handler_key):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_transport.return_value = MagicMock()
        mock_client.invoke_shell.return_value = MagicMock()

        mock_pkey = MagicMock()
        with patch.object(handler_key, "_load_private_key", return_value=mock_pkey):
            with patch.object(handler_key, "_detect_encoding"):
                handler_key.connect()

        call_kwargs = mock_client.connect.call_args
        assert call_kwargs.kwargs["pkey"] is mock_pkey
        assert call_kwargs.kwargs["password"] is None

    @patch("app.core.webssh_handler.paramiko.SSHClient")
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    def test_connect_agent_auth(self, mock_ensure, mock_client_cls, handler_agent):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_transport.return_value = MagicMock()
        mock_client.invoke_shell.return_value = MagicMock()

        with patch.object(handler_agent, "_detect_encoding"):
            handler_agent.connect()

        call_kwargs = mock_client.connect.call_args
        assert call_kwargs.kwargs["allow_agent"] is True

    @patch("app.core.webssh_handler.paramiko.SSHClient")
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    def test_connect_already_connected(self, mock_ensure, mock_client_cls, handler):
        handler._connected = True
        handler.connect()
        mock_client_cls.assert_not_called()

    @patch("app.core.webssh_handler.paramiko.SSHClient")
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    def test_connect_no_transport(self, mock_ensure, mock_client_cls, handler):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_transport.return_value = None
        mock_client.invoke_shell.return_value = MagicMock()

        with patch.object(handler, "_detect_encoding"):
            handler.connect()

        assert handler._connected is True


class TestApplyHostKeyPolicy:
    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    @patch("app.core.webssh_handler.paramiko")
    def test_accept_policy(self, mock_paramiko, mock_ensure):
        handler = WebSSHHandler("s1", "h", 22, "u", auth_type="accept")
        handler._client = MagicMock()
        handler._apply_host_key_policy()
        handler._client.load_system_host_keys.assert_called_once()
        handler._client.set_missing_host_key_policy.assert_called_once()
        mock_paramiko.RejectPolicy.assert_called_once()

    @patch("app.core.webssh_handler._ensure_known_hosts_dir")
    @patch("app.core.webssh_handler.paramiko")
    def test_auto_add_policy(self, mock_paramiko, mock_ensure):
        handler = WebSSHHandler("s1", "h", 22, "u", auth_type="password")
        handler._client = MagicMock()
        handler._apply_host_key_policy()
        handler._client.load_system_host_keys.assert_called_once()
        handler._client.set_missing_host_key_policy.assert_called_once()
        mock_paramiko.AutoAddPolicy.assert_called_once()

    def test_no_client(self):
        handler = WebSSHHandler("s1", "h", 22, "u")
        handler._apply_host_key_policy()


class TestLoadPrivateKey:
    def test_no_key_path(self, handler):
        result = handler._load_private_key()
        assert result is None

    @patch("os.path.isfile", return_value=False)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_key_file_not_found(self, mock_expand, mock_isfile, handler_key):
        result = handler_key._load_private_key()
        assert result is None

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_load_rsa_key(self, mock_expand, mock_isfile, mock_rsa, handler_key):
        mock_key = MagicMock()
        mock_rsa.from_private_key_file.return_value = mock_key
        result = handler_key._load_private_key()
        assert result is mock_key

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("app.core.webssh_handler.paramiko.Ed25519Key")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_ed25519")
    def test_load_ed25519_key_fallback(self, mock_expand, mock_isfile, mock_ed25519, mock_rsa, handler_key):
        import paramiko
        mock_rsa.from_private_key_file.side_effect = paramiko.SSHException("not RSA")
        mock_key = MagicMock()
        mock_ed25519.from_private_key_file.return_value = mock_key
        result = handler_key._load_private_key()
        assert result is mock_key

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("app.core.webssh_handler.paramiko.Ed25519Key")
    @patch("app.core.webssh_handler.paramiko.ECDSAKey")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_ecdsa")
    def test_load_ecdsa_key_fallback(self, mock_expand, mock_isfile, mock_ecdsa, mock_ed25519, mock_rsa, handler_key):
        import paramiko
        mock_rsa.from_private_key_file.side_effect = paramiko.SSHException("not RSA")
        mock_ed25519.from_private_key_file.side_effect = paramiko.SSHException("not Ed25519")
        mock_key = MagicMock()
        mock_ecdsa.from_private_key_file.return_value = mock_key
        result = handler_key._load_private_key()
        assert result is mock_key

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_load_key_with_passphrase(self, mock_expand, mock_isfile, mock_rsa, handler_key):
        handler_key._key_passphrase = "mypass"
        mock_key = MagicMock()
        mock_rsa.from_private_key_file.return_value = mock_key
        result = handler_key._load_private_key()
        mock_rsa.from_private_key_file.assert_called_once_with(
            "/home/user/.ssh/id_rsa", password="mypass"
        )
        assert result is mock_key

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("app.core.webssh_handler.paramiko.Ed25519Key")
    @patch("app.core.webssh_handler.paramiko.ECDSAKey")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_unknown")
    def test_all_key_types_fail(self, mock_expand, mock_isfile, mock_ecdsa, mock_ed25519, mock_rsa, handler_key):
        import paramiko
        mock_rsa.from_private_key_file.side_effect = paramiko.SSHException("not RSA")
        mock_ed25519.from_private_key_file.side_effect = paramiko.SSHException("not Ed25519")
        mock_ecdsa.from_private_key_file.side_effect = paramiko.SSHException("not ECDSA")
        result = handler_key._load_private_key()
        assert result is None

    @patch("app.core.webssh_handler.paramiko.RSAKey")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_file_not_found_error_breaks_loop(self, mock_expand, mock_isfile, mock_rsa, handler_key):
        mock_rsa.from_private_key_file.side_effect = FileNotFoundError("gone")
        result = handler_key._load_private_key()
        assert result is None


class TestDetectEncoding:
    def test_no_client(self, handler):
        handler._client = None
        handler._detect_encoding()
        assert handler._encoding == "utf-8"

    def test_detect_from_charmap(self, handler):
        mock_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"UTF-8\n"
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        handler._client = mock_client
        handler._detect_encoding()
        assert handler._encoding == "UTF-8"

    def test_detect_from_lang(self, handler):
        mock_client = MagicMock()
        mock_stdout_charmap = MagicMock()
        mock_stdout_charmap.read.return_value = b""
        mock_stdout_lang = MagicMock()
        mock_stdout_lang.read.return_value = b"en_US.UTF-8\n"
        mock_client.exec_command.side_effect = [
            (None, mock_stdout_charmap, None),
            (None, mock_stdout_lang, None),
        ]
        handler._client = mock_client
        handler._detect_encoding()
        assert handler._encoding == "UTF-8"

    def test_detect_fallback_utf8(self, handler):
        mock_client = MagicMock()
        mock_client.exec_command.side_effect = Exception("fail")
        handler._client = mock_client
        handler._detect_encoding()
        assert handler._encoding == "utf-8"

    def test_detect_charmap_exception_lang_fallback(self, handler):
        mock_client = MagicMock()
        first_call = MagicMock()
        first_call.read.side_effect = Exception("read fail")
        second_call = MagicMock()
        second_call.read.return_value = b"C\n"
        mock_client.exec_command.side_effect = [
            Exception("cmd fail"),
            (None, second_call, None),
        ]
        handler._client = mock_client
        handler._detect_encoding()
        assert handler._encoding == "utf-8"

    def test_detect_lang_no_dot(self, handler):
        mock_client = MagicMock()
        mock_stdout_charmap = MagicMock()
        mock_stdout_charmap.read.return_value = b""
        mock_stdout_lang = MagicMock()
        mock_stdout_lang.read.return_value = b"C\n"
        mock_client.exec_command.side_effect = [
            (None, mock_stdout_charmap, None),
            (None, mock_stdout_lang, None),
        ]
        handler._client = mock_client
        handler._detect_encoding()
        assert handler._encoding == "utf-8"


class TestStartReader:
    def test_start_reader_no_channel(self, handler):
        handler._channel = None
        handler._connected = True
        queue = asyncio.Queue()
        handler.start_reader(queue)
        assert handler._output_queue is queue

    @patch("app.core.webssh_handler.asyncio")
    def test_start_reader_reads_data(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.closed = True
        mock_channel.recv.return_value = b"hello"
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_loop = MagicMock()
        mock_asyncio.get_event_loop.return_value = mock_loop

        queue = asyncio.Queue()
        handler.start_reader(queue)

        time.sleep(0.3)
        assert handler._reader_thread is not None

    @patch("app.core.webssh_handler.asyncio")
    def test_start_reader_empty_data_disconnects(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True]
        mock_channel.recv.return_value = b""
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()
        handler.start_reader(queue)

        time.sleep(0.3)


class TestWrite:
    def test_write_not_connected(self, handler):
        handler._connected = False
        handler._channel = MagicMock()
        handler.write(b"test")
        handler._channel.send.assert_not_called()

    def test_write_no_channel(self, handler):
        handler._connected = True
        handler._channel = None
        handler.write(b"test")

    def test_write_success(self, handler):
        handler._connected = True
        handler._channel = MagicMock()
        handler.write(b"test")
        handler._channel.send.assert_called_once_with(b"test")

    def test_write_exception_sets_disconnected(self, handler):
        handler._connected = True
        handler._channel = MagicMock()
        handler._channel.send.side_effect = Exception("broken pipe")
        handler.write(b"test")
        assert handler._connected is False


class TestResizePty:
    def test_resize_not_connected(self, handler):
        handler._connected = False
        handler._channel = MagicMock()
        handler.resize_pty(80, 24)
        handler._channel.resize_pty.assert_not_called()

    def test_resize_no_channel(self, handler):
        handler._connected = True
        handler._channel = None
        handler.resize_pty(80, 24)

    def test_resize_success(self, handler):
        handler._connected = True
        handler._channel = MagicMock()
        handler.resize_pty(120, 40)
        handler._channel.resize_pty.assert_called_once_with(width=120, height=40)

    def test_resize_exception_suppressed(self, handler):
        handler._connected = True
        handler._channel = MagicMock()
        handler._channel.resize_pty.side_effect = Exception("resize fail")
        handler.resize_pty(80, 24)


class TestCheckHealth:
    def test_health_closed(self, handler):
        handler._closed = True
        assert handler.check_health() is False

    def test_health_not_connected(self, handler):
        handler._closed = False
        handler._connected = False
        assert handler.check_health() is False

    def test_health_no_transport(self, handler):
        handler._closed = False
        handler._connected = True
        handler._transport = None
        assert handler.check_health() is False
        assert handler._connected is False

    def test_health_transport_inactive(self, handler):
        handler._closed = False
        handler._connected = True
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = False
        handler._transport = mock_transport
        assert handler.check_health() is False
        assert handler._connected is False

    def test_health_healthy(self, handler):
        handler._closed = False
        handler._connected = True
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        handler._transport = mock_transport
        assert handler.check_health() is True

    def test_health_exception(self, handler):
        handler._closed = False
        handler._connected = True
        mock_transport = MagicMock()
        mock_transport.is_active.side_effect = Exception("fail")
        handler._transport = mock_transport
        assert handler.check_health() is False
        assert handler._connected is False


class TestClose:
    def test_close_cleans_up(self, handler):
        mock_channel = MagicMock()
        mock_transport = MagicMock()
        mock_client = MagicMock()
        handler._channel = mock_channel
        handler._transport = mock_transport
        handler._client = mock_client
        handler._connected = True

        handler.close()

        assert handler._closed is True
        assert handler._connected is False
        assert handler._channel is None
        assert handler._transport is None
        assert handler._client is None
        mock_channel.close.assert_called_once()
        mock_transport.close.assert_called_once()
        mock_client.close.assert_called_once()

    def test_close_channel_exception(self, handler):
        mock_channel = MagicMock()
        mock_channel.close.side_effect = Exception("close fail")
        handler._channel = mock_channel
        handler._transport = None
        handler._client = None
        handler._connected = True

        handler.close()
        assert handler._closed is True

    def test_close_transport_exception(self, handler):
        mock_transport = MagicMock()
        mock_transport.close.side_effect = Exception("close fail")
        handler._channel = None
        handler._transport = mock_transport
        handler._client = None
        handler._connected = True

        handler.close()
        assert handler._closed is True

    def test_close_client_exception(self, handler):
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("close fail")
        handler._channel = None
        handler._transport = None
        handler._client = mock_client
        handler._connected = True

        handler.close()
        assert handler._closed is True

    def test_close_no_resources(self, handler):
        handler._channel = None
        handler._transport = None
        handler._client = None
        handler.close()
        assert handler._closed is True
        assert handler._connected is False


class TestFromAccount:
    def test_from_account_password(self):
        account = SSHAccount(
            alias="prod",
            host="1.2.3.4",
            port=22,
            username="root",
            auth_type="password",
            password="secret",
        )
        h = WebSSHHandler.from_account("session-1", account)
        assert h.session_id == "session-1"
        assert h.host == "1.2.3.4"
        assert h._password == "secret"
        assert h._private_key_path is None
        assert h._auth_type == "password"

    def test_from_account_key(self):
        account = SSHAccount(
            alias="prod",
            host="1.2.3.4",
            port=2222,
            username="admin",
            auth_type="key",
            private_key="/home/user/.ssh/id_rsa",
            key_passphrase="keypass",
        )
        h = WebSSHHandler.from_account("session-2", account)
        assert h._private_key_path == "/home/user/.ssh/id_rsa"
        assert h._key_passphrase == "keypass"
        assert h._password is None
        assert h.port == 2222

    def test_from_account_agent(self):
        account = SSHAccount(
            alias="prod",
            host="1.2.3.4",
            port=22,
            username="root",
            auth_type="agent",
        )
        h = WebSSHHandler.from_account("session-3", account)
        assert h._auth_type == "agent"
        assert h._password is None
        assert h._private_key_path is None


class TestEnsureKnownHostsDir:
    @patch.object(Path, "mkdir")
    def test_ensure_known_hosts_dir(self, mock_mkdir):
        _ensure_known_hosts_dir()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
