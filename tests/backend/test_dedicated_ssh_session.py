from __future__ import annotations

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import paramiko
import pytest

from app.core.dedicated_ssh_session import (
    HOST_KEY_POLICY_ACCEPT,
    HOST_KEY_POLICY_ADD,
    HOST_KEY_POLICY_AUTO,
    DedicatedSSHSession,
    _ensure_known_hosts_dir,
)


@pytest.fixture
def mock_account():
    account = MagicMock()
    account.alias = "test-server"
    account.host = "192.168.1.1"
    account.port = 22
    account.username = "root"
    account.auth_type = "password"
    account.password = "secret"
    account.private_key = None
    account.key_passphrase = None
    return account


@pytest.fixture
def session(mock_account):
    return DedicatedSSHSession(mock_account)


class TestApplyHostKeyPolicy:
    def test_auto_policy(self, session, mock_account):
        mock_account.auth_type = HOST_KEY_POLICY_AUTO
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            session._client = mock_client
            with patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
                session._apply_host_key_policy()
            mock_client.set_missing_host_key_policy.assert_called_once()
            assert isinstance(
                mock_client.set_missing_host_key_policy.call_args[0][0],
                paramiko.AutoAddPolicy,
            )

    def test_accept_policy(self, session, mock_account):
        mock_account.auth_type = HOST_KEY_POLICY_ACCEPT
        mock_client = MagicMock()
        session._client = mock_client
        with patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
            session._apply_host_key_policy()
        mock_client.load_system_host_keys.assert_called_once()
        mock_client.set_missing_host_key_policy.assert_called_once()
        assert isinstance(
            mock_client.set_missing_host_key_policy.call_args[0][0],
            paramiko.RejectPolicy,
        )

    def test_add_policy(self, session, mock_account):
        mock_account.auth_type = HOST_KEY_POLICY_ADD
        mock_client = MagicMock()
        session._client = mock_client
        with patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
            session._apply_host_key_policy()
        mock_client.load_system_host_keys.assert_called_once()
        mock_client.set_missing_host_key_policy.assert_called_once()

    def test_no_client(self, session):
        session._client = None
        session._apply_host_key_policy()


class TestResolvePassword:
    def test_password_auth(self, session, mock_account):
        mock_account.auth_type = "password"
        mock_account.password = "mypassword"
        assert session._resolve_password() == "mypassword"

    def test_password_auth_none(self, session, mock_account):
        mock_account.auth_type = "password"
        mock_account.password = None
        assert session._resolve_password() is None

    def test_key_auth(self, session, mock_account):
        mock_account.auth_type = "key"
        assert session._resolve_password() is None

    def test_agent_auth(self, session, mock_account):
        mock_account.auth_type = "agent"
        assert session._resolve_password() is None


class TestLoadPrivateKey:
    def test_not_key_auth(self, session, mock_account):
        mock_account.auth_type = "password"
        assert session._load_private_key() is None

    def test_key_auth_no_path(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = None
        assert session._load_private_key() is None

    def test_key_auth_file_not_exists(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/nonexistent/key.pem"
        with patch("os.path.expanduser", return_value="/nonexistent/key.pem"):
            with patch("os.path.isfile", return_value=False):
                assert session._load_private_key() is None

    def test_key_auth_rsa_success(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_rsa"
        mock_account.key_passphrase = None
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA:
            MockRSA.from_private_key_file.return_value = MagicMock()
            result = session._load_private_key()
            assert result is not None
            MockRSA.from_private_key_file.assert_called_once_with("/home/user/.ssh/id_rsa")

    def test_key_auth_with_passphrase(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_rsa"
        mock_account.key_passphrase = "pass123"
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_rsa"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA:
            MockRSA.from_private_key_file.return_value = MagicMock()
            result = session._load_private_key()
            assert result is not None
            MockRSA.from_private_key_file.assert_called_once_with(
                "/home/user/.ssh/id_rsa", password="pass123"
            )

    def test_key_auth_fallback_ed25519(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_ed25519"
        mock_account.key_passphrase = None
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_ed25519"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA, \
             patch("app.core.dedicated_ssh_session.paramiko.Ed25519Key") as MockEd:
            MockRSA.from_private_key_file.side_effect = paramiko.SSHException("not RSA")
            MockEd.from_private_key_file.return_value = MagicMock()
            result = session._load_private_key()
            assert result is not None

    def test_key_auth_fallback_ecdsa(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_ecdsa"
        mock_account.key_passphrase = None
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_ecdsa"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA, \
             patch("app.core.dedicated_ssh_session.paramiko.Ed25519Key") as MockEd, \
             patch("app.core.dedicated_ssh_session.paramiko.ECDSAKey") as MockEC:
            MockRSA.from_private_key_file.side_effect = paramiko.SSHException("not RSA")
            MockEd.from_private_key_file.side_effect = paramiko.SSHException("not Ed25519")
            MockEC.from_private_key_file.return_value = MagicMock()
            result = session._load_private_key()
            assert result is not None

    def test_key_auth_all_fail(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_broken"
        mock_account.key_passphrase = None
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_broken"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA, \
             patch("app.core.dedicated_ssh_session.paramiko.Ed25519Key") as MockEd, \
             patch("app.core.dedicated_ssh_session.paramiko.ECDSAKey") as MockEC:
            MockRSA.from_private_key_file.side_effect = paramiko.SSHException("fail")
            MockEd.from_private_key_file.side_effect = paramiko.SSHException("fail")
            MockEC.from_private_key_file.side_effect = paramiko.SSHException("fail")
            result = session._load_private_key()
            assert result is None

    def test_key_auth_file_not_found_breaks(self, session, mock_account):
        mock_account.auth_type = "key"
        mock_account.private_key = "/home/user/.ssh/id_missing"
        mock_account.key_passphrase = None
        with patch("os.path.expanduser", return_value="/home/user/.ssh/id_missing"), \
             patch("os.path.isfile", return_value=True), \
             patch("app.core.dedicated_ssh_session.paramiko.RSAKey") as MockRSA:
            MockRSA.from_private_key_file.side_effect = FileNotFoundError()
            result = session._load_private_key()
            assert result is None


class TestDetectEncoding:
    def test_no_transport(self, session):
        session._transport = None
        session._client = MagicMock()
        session._detect_encoding()
        assert session._encoding == "utf-8"

    def test_locale_charmap_success(self, session):
        session._transport = MagicMock()
        session._client = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"UTF-8\n"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        session._client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
        session._detect_encoding()
        assert session._encoding == "UTF-8"

    def test_locale_charmap_empty(self, session):
        session._transport = MagicMock()
        session._client = MagicMock()
        mock_stdout1 = MagicMock()
        mock_stdout1.read.return_value = b""
        mock_stdout2 = MagicMock()
        mock_stdout2.read.return_value = b"en_US.UTF-8\n"
        session._client.exec_command.side_effect = [
            (MagicMock(), mock_stdout1, MagicMock()),
            (MagicMock(), mock_stdout2, MagicMock()),
        ]
        session._detect_encoding()
        assert session._encoding == "UTF-8"

    def test_lang_fallback(self, session):
        session._transport = MagicMock()
        session._client = MagicMock()
        call_count = [0]

        def mock_exec(cmd, timeout=5.0):
            call_count[0] += 1
            mock_stdout = MagicMock()
            if call_count[0] == 1:
                mock_stdout.read.return_value = b""
                raise Exception("fail")
            mock_stdout.read.return_value = b"en_US.GBK\n"
            return (MagicMock(), mock_stdout, MagicMock())

        session._client.exec_command = mock_exec
        session._detect_encoding()
        assert session._encoding == "GBK"

    def test_all_fail_default_utf8(self, session):
        session._transport = MagicMock()
        session._client = MagicMock()
        session._client.exec_command.side_effect = Exception("fail")
        session._detect_encoding()
        assert session._encoding == "utf-8"


class TestExecCommandOffline:
    @pytest.mark.asyncio
    async def test_exec_offline_device(self, session):
        session._connected = False
        session._closed = False
        session._online = False
        session._client = None
        code, stdout, stderr = await session.exec_command("ls")
        assert code == -1
        assert "离线" in stderr

    @pytest.mark.asyncio
    async def test_exec_disconnected_not_offline(self, session):
        session._connected = False
        session._closed = False
        session._online = True
        session._client = None
        code, stdout, stderr = await session.exec_command("ls")
        assert code == -1
        assert "未连接" in stderr
        assert "离线" not in stderr


class TestExecCommandNetworkError:
    @pytest.mark.asyncio
    async def test_exec_socket_error_triggers_reconnect(self, session):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)

            mock_transport.open_session.side_effect = socket.timeout("timeout")

            with patch.object(session, "_schedule_reconnect"):
                code, stdout, stderr = await session.exec_command("ls", timeout=2.0)
                assert code == -1
                assert "超时" in stderr

    @pytest.mark.asyncio
    async def test_exec_os_error_triggers_reconnect(self, session):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)

            mock_transport.open_session.side_effect = OSError("broken pipe")

            with patch.object(session, "_schedule_reconnect"):
                code, stdout, stderr = await session.exec_command("ls", timeout=2.0)
                assert code == -1
                assert "网络断开" in stderr

    @pytest.mark.asyncio
    async def test_exec_ssh_exception_triggers_reconnect(self, session):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)

            mock_transport.open_session.side_effect = paramiko.SSHException("session lost")

            with patch.object(session, "_schedule_reconnect"):
                code, stdout, stderr = await session.exec_command("ls", timeout=2.0)
                assert code == -1
                assert "网络断开" in stderr

    @pytest.mark.asyncio
    async def test_exec_generic_exception(self, session):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)

            mock_transport.open_session.side_effect = RuntimeError("unexpected")

            code, stdout, stderr = await session.exec_command("ls", timeout=2.0)
            assert code == -1
            assert "异常" in stderr


class TestExecCommandOnlineRecovery:
    @pytest.mark.asyncio
    async def test_exec_recovers_online_status(self, session):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_chan = MagicMock()
            mock_chan.recv_exit_status.return_value = 0
            mock_chan.makefile.return_value.read.return_value = b"ok"
            mock_chan.makefile_stderr.return_value.read.return_value = b""
            mock_transport.open_session.return_value = mock_chan
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)
            session._online = False

            code, stdout, stderr = await session.exec_command("ls", timeout=5.0)
            assert code == 0
            assert session._online is True
            assert session._backoff_index == 0


class TestReadChannel:
    def test_read_bytes(self, session):
        session._encoding = "utf-8"
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"hello"
        result = session._read_channel(mock_stream)
        assert result == "hello"

    def test_read_string(self, session):
        session._encoding = "utf-8"
        mock_stream = MagicMock()
        mock_stream.read.return_value = "hello"
        result = session._read_channel(mock_stream)
        assert result == "hello"

    def test_read_exception(self, session):
        session._encoding = "utf-8"
        mock_stream = MagicMock()
        mock_stream.read.side_effect = Exception("read error")
        result = session._read_channel(mock_stream)
        assert result == ""


class TestSyncExecCommand:
    def test_sync_exec_success(self, session):
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value.read.return_value = b"output"
        mock_chan.makefile_stderr.return_value.read.return_value = b"err"

        session._client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.open_session.return_value = mock_chan
        session._client.get_transport.return_value = mock_transport
        session._encoding = "utf-8"

        code, stdout, stderr = session._sync_exec_command("ls", 5.0)
        assert code == 0
        assert stdout == "output"
        assert stderr == "err"
        mock_chan.close.assert_called_once()


class TestScheduleReconnect:
    @pytest.mark.asyncio
    async def test_schedule_reconnect_creates_task(self, session):
        session._reconnect_task = None
        with patch.object(session, "_reconnect_loop", new_callable=AsyncMock) as mock_loop:
            session._schedule_reconnect()
            assert session._reconnect_task is not None
            session._reconnect_task.cancel()
            try:
                await session._reconnect_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_schedule_reconnect_existing_task(self, session):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        session._reconnect_task = mock_task
        session._schedule_reconnect()
        assert session._reconnect_task is mock_task


class TestReconnectLoop:
    @pytest.mark.asyncio
    async def test_reconnect_loop_success(self, session):
        with patch.object(session, "_do_connect_locked", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            session._closed = False
            session._connected = False
            session._backoff_index = 0

            with patch("app.core.dedicated_ssh_session.asyncio.sleep", new_callable=AsyncMock):
                task = asyncio.create_task(session._reconnect_loop())
                await asyncio.sleep(0.1)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_reconnect_loop_closed(self, session):
        session._closed = True
        session._connected = False
        await session._reconnect_loop()

    @pytest.mark.asyncio
    async def test_reconnect_loop_already_connected(self, session):
        session._closed = False
        session._connected = True
        await session._reconnect_loop()

    @pytest.mark.asyncio
    async def test_reconnect_loop_failure_increments_backoff(self, session):
        with patch.object(session, "_do_connect_locked", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False
            session._closed = False
            session._connected = False
            session._backoff_index = 0

            with patch("app.core.dedicated_ssh_session.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                with pytest.raises(asyncio.CancelledError):
                    await session._reconnect_loop()


class TestCleanupTransport:
    def test_cleanup_transport_success(self, session):
        mock_transport = MagicMock()
        session._transport = mock_transport
        session._cleanup_transport()
        mock_transport.close.assert_called_once()
        assert session._transport is None

    def test_cleanup_transport_exception(self, session):
        mock_transport = MagicMock()
        mock_transport.close.side_effect = Exception("close error")
        session._transport = mock_transport
        session._cleanup_transport()
        assert session._transport is None


class TestCleanupClient:
    def test_cleanup_client_success(self, session):
        mock_client = MagicMock()
        session._client = mock_client
        session._cleanup_client()
        mock_client.close.assert_called_once()
        assert session._client is None

    def test_cleanup_client_exception(self, session):
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("close error")
        session._client = mock_client
        session._cleanup_client()
        assert session._client is None


class TestEnsureKnownHostsDir:
    def test_ensure_known_hosts_dir(self):
        with patch("app.core.dedicated_ssh_session._KNOWN_HOSTS_PATH") as mock_path:
            mock_parent = MagicMock()
            mock_path.parent = mock_parent
            mock_path.exists.return_value = True
            _ensure_known_hosts_dir()
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_ensure_known_hosts_dir_creates_file(self):
        with patch("app.core.dedicated_ssh_session._KNOWN_HOSTS_PATH") as mock_path:
            mock_parent = MagicMock()
            mock_path.parent = mock_parent
            mock_path.exists.return_value = False
            _ensure_known_hosts_dir()
            mock_path.touch.assert_called_once_with(exist_ok=True)


class TestCloseWithReconnectTask:
    @pytest.mark.asyncio
    async def test_close_cancels_active_reconnect(self, session):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        session._reconnect_task = mock_task
        session._transport = MagicMock()
        session._client = MagicMock()
        session.close()
        mock_task.cancel.assert_called_once()
        assert session._closed is True
        assert session._connected is False
        assert session._online is False
