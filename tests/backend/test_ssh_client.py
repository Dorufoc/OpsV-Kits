import socket
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import paramiko
import pytest

from app.models.ssh_account import SSHAccount


def _make_account(**kwargs):
    defaults = {
        "alias": "test",
        "host": "192.168.1.1",
        "port": 22,
        "username": "root",
        "auth_type": "password",
        "password": "secret",
    }
    defaults.update(kwargs)
    return SSHAccount(**defaults)


@pytest.fixture
def account():
    return _make_account()


@pytest.fixture
def manager(account):
    from app.core.ssh_client import SSHClientManager

    return SSHClientManager(account)


class TestSSHClientManagerInit:
    def test_initial_state(self, manager):
        assert manager.connected is False
        assert manager.closed is False
        assert manager.encoding is None
        assert manager.transport is None
        assert manager.client is None


class TestSSHClientManagerConnect:
    @patch("app.core.ssh_client.paramiko.SSHClient")
    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_connect_success(self, mock_ensure, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client
        mock_transport = MagicMock()
        mock_client.get_transport.return_value = mock_transport

        stdout = MagicMock()
        stdout.read.return_value = b"UTF-8\n"
        mock_client.exec_command.return_value = (None, stdout, None)

        manager.connect(timeout=10.0)
        assert manager.connected is True
        assert manager.closed is False
        mock_client.connect.assert_called_once()

    @patch("app.core.ssh_client.paramiko.SSHClient")
    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_connect_already_connected(self, mock_ensure, mock_ssh_cls, manager):
        manager._connected = True
        manager.connect()
        mock_ssh_cls.assert_not_called()


class TestSSHClientManagerHostKeyPolicy:
    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_auto_policy(self, mock_ensure, account):
        from app.core.ssh_client import SSHClientManager

        mgr = SSHClientManager(_make_account(auth_type="auto"))
        mgr._client = MagicMock()
        mgr._apply_host_key_policy()
        mgr._client.set_missing_host_key_policy.assert_called()

    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_accept_policy(self, mock_ensure, account):
        from app.core.ssh_client import SSHClientManager

        mgr = SSHClientManager(_make_account(auth_type="accept"))
        mgr._client = MagicMock()
        mgr._apply_host_key_policy()
        mgr._client.load_system_host_keys.assert_called()
        mgr._client.set_missing_host_key_policy.assert_called()

    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_add_policy(self, mock_ensure, account):
        from app.core.ssh_client import SSHClientManager

        mgr = SSHClientManager(_make_account(auth_type="add"))
        mgr._client = MagicMock()
        mgr._apply_host_key_policy()
        mgr._client.load_system_host_keys.assert_called()

    def test_apply_policy_no_client(self, manager):
        manager._apply_host_key_policy()


class TestSSHClientManagerResolvePassword:
    def test_password_auth(self, account):
        from app.core.ssh_client import SSHClientManager

        mgr = SSHClientManager(account)
        assert mgr._resolve_password() == "secret"

    def test_key_auth(self):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", password=None)
        mgr = SSHClientManager(acc)
        assert mgr._resolve_password() is None

    def test_password_auth_no_password(self):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="password", password=None)
        mgr = SSHClientManager(acc)
        assert mgr._resolve_password() is None


class TestSSHClientManagerLoadPrivateKey:
    def test_non_key_auth_returns_none(self, manager):
        assert manager._load_private_key() is None

    def test_key_auth_no_path(self):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key=None)
        mgr = SSHClientManager(acc)
        assert mgr._load_private_key() is None

    def test_key_auth_nonexistent_path(self):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key="/nonexistent/key")
        mgr = SSHClientManager(acc)
        assert mgr._load_private_key() is None

    @patch("app.core.ssh_client.os.path.isfile", return_value=True)
    @patch("app.core.ssh_client.os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_key_auth_loads_rsa(self, mock_expand, mock_isfile):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key="~/.ssh/id_rsa")
        mgr = SSHClientManager(acc)
        with patch.object(paramiko.RSAKey, "from_private_key_file", return_value=MagicMock()) as mock_load:
            result = mgr._load_private_key()
            assert result is not None

    @patch("app.core.ssh_client.os.path.isfile", return_value=True)
    @patch("app.core.ssh_client.os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_key_auth_fallback_to_ed25519(self, mock_expand, mock_isfile):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key="~/.ssh/id_rsa")
        mgr = SSHClientManager(acc)
        with patch.object(paramiko.RSAKey, "from_private_key_file", side_effect=paramiko.SSHException), \
             patch.object(paramiko.Ed25519Key, "from_private_key_file", return_value=MagicMock()):
            result = mgr._load_private_key()
            assert result is not None

    @patch("app.core.ssh_client.os.path.isfile", return_value=True)
    @patch("app.core.ssh_client.os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_key_auth_all_fail(self, mock_expand, mock_isfile):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key="~/.ssh/id_rsa")
        mgr = SSHClientManager(acc)
        with patch.object(paramiko.RSAKey, "from_private_key_file", side_effect=paramiko.SSHException), \
             patch.object(paramiko.Ed25519Key, "from_private_key_file", side_effect=paramiko.SSHException), \
             patch.object(paramiko.ECDSAKey, "from_private_key_file", side_effect=paramiko.SSHException):
            result = mgr._load_private_key()
            assert result is None

    @patch("app.core.ssh_client.os.path.isfile", return_value=True)
    @patch("app.core.ssh_client.os.path.expanduser", return_value="/home/user/.ssh/id_rsa")
    def test_key_auth_with_passphrase(self, mock_expand, mock_isfile):
        from app.core.ssh_client import SSHClientManager

        acc = _make_account(auth_type="key", private_key="~/.ssh/id_rsa", key_passphrase="mypass")
        mgr = SSHClientManager(acc)
        with patch.object(paramiko.RSAKey, "from_private_key_file", return_value=MagicMock()) as mock_load:
            result = mgr._load_private_key()
            mock_load.assert_called_once()
            assert mock_load.call_args[1].get("password") == "mypass" or mock_load.call_args[0][-1] == "mypass"


class TestSSHClientManagerDetectEncoding:
    def test_detect_encoding_no_transport(self, manager):
        manager._transport = None
        manager._detect_encoding()
        assert manager.encoding == "utf-8"

    def test_detect_encoding_locale_charmap(self, manager):
        manager._transport = MagicMock()
        manager._client = MagicMock()
        stdout = MagicMock()
        stdout.read.return_value = b"UTF-8\n"
        manager._client.exec_command.return_value = (None, stdout, None)
        manager._detect_encoding()
        assert manager.encoding == "UTF-8"

    def test_detect_encoding_lang_fallback(self, manager):
        manager._transport = MagicMock()
        manager._client = MagicMock()

        call_count = [0]

        def mock_exec(cmd, timeout=5.0):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("fail")
            stdout = MagicMock()
            stdout.read.return_value = b"en_US.UTF-8\n"
            return (None, stdout, None)

        manager._client.exec_command = mock_exec
        manager._detect_encoding()
        assert manager.encoding == "UTF-8"

    def test_detect_encoding_all_fail(self, manager):
        manager._transport = MagicMock()
        manager._client = MagicMock()
        manager._client.exec_command = MagicMock(side_effect=Exception("fail"))
        manager._detect_encoding()
        assert manager.encoding == "utf-8"


class TestSSHClientManagerExecCommand:
    def test_exec_not_connected_raises(self, manager):
        with pytest.raises(RuntimeError, match="未连接"):
            manager.exec_command("ls")

    def test_exec_command_success(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        mock_transport = MagicMock()
        mock_transport.open_session.return_value = mock_chan
        manager._client.get_transport.return_value = mock_transport

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_command("ls", environment={"FOO": "bar"})
            assert code == 0
            mock_chan.set_environment_variable.assert_called_with("FOO", "bar")


class TestSSHClientManagerExecWithPty:
    def test_exec_with_pty_not_connected_raises(self, manager):
        with pytest.raises(RuntimeError, match="未连接"):
            manager.exec_with_pty("top")

    def test_exec_with_pty_success(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        manager._transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        manager._transport.open_session.return_value = mock_chan

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_with_pty("top", term="xterm-256color")
            assert code == 0
            mock_chan.get_pty.assert_called_with(term="xterm-256color")


class TestSSHClientManagerSftp:
    def test_open_sftp_not_connected_raises(self, manager):
        with pytest.raises(RuntimeError, match="未连接"):
            manager.open_sftp()

    def test_open_sftp_new(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        manager._sftp = None
        mock_sftp = MagicMock()
        mock_sftp.sock.closed = False
        manager._client.open_sftp.return_value = mock_sftp
        result = manager.open_sftp()
        assert result == mock_sftp

    def test_open_sftp_reuse(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        mock_sftp = MagicMock()
        mock_sftp.sock.closed = False
        manager._sftp = mock_sftp
        result = manager.open_sftp()
        assert result == mock_sftp

    def test_open_sftp_reopen_closed(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        mock_sftp = MagicMock()
        mock_sftp.sock.closed = True
        manager._sftp = mock_sftp
        new_sftp = MagicMock()
        new_sftp.sock.closed = False
        manager._client.open_sftp.return_value = new_sftp
        result = manager.open_sftp()
        assert result == new_sftp

    def test_close_sftp(self, manager):
        mock_sftp = MagicMock()
        manager._sftp = mock_sftp
        manager.close_sftp()
        mock_sftp.close.assert_called()
        assert manager._sftp is None

    def test_close_sftp_none(self, manager):
        manager._sftp = None
        manager.close_sftp()


class TestSSHClientManagerClose:
    def test_close_connected(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        manager._transport = MagicMock()
        manager._sftp = MagicMock()
        manager.close()
        assert manager.connected is False
        assert manager.closed is True
        assert manager._client is None
        assert manager._transport is None

    def test_close_already_closed(self, manager):
        manager._closed = True
        manager._connected = False
        manager.close()


class TestSSHClientManagerTestConnection:
    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_success(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is True
        assert "成功" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_auth_fail(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = paramiko.AuthenticationException("bad creds")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "认证失败" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_host_key_fail(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = paramiko.SSHException("not found in known_hosts")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "主机密钥" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_ssh_error(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = paramiko.SSHException("some error")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "SSH 错误" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_timeout(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = socket.timeout()
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "超时" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_gaierror(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = socket.gaierror("bad host")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "无法解析" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_oserror(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = OSError("network error")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "网络错误" in msg

    @patch("app.core.ssh_client.paramiko.SSHClient")
    def test_test_connection_generic_error(self, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_client.connect.side_effect = RuntimeError("unknown")
        mock_ssh_cls.return_value = mock_client
        success, msg = manager.test_connection()
        assert success is False
        assert "连接失败" in msg


class TestVerifyTotp:
    def test_verify_totp_not_implemented(self):
        from app.core.ssh_client import verify_totp

        with pytest.raises(NotImplementedError):
            verify_totp("secret", "123456")


class TestReadChannel:
    def test_read_channel_success(self):
        from app.core.ssh_client import _read_channel

        stream = MagicMock()
        stream.read.return_value = "data"
        assert _read_channel(stream) == "data"

    def test_read_channel_exception(self):
        from app.core.ssh_client import _read_channel

        stream = MagicMock()
        stream.read.side_effect = Exception("fail")
        assert _read_channel(stream) == ""


class TestEnsureKnownHostsDir:
    def test_ensure_creates_dir_and_file(self):
        from app.core.ssh_client import _ensure_known_hosts_dir

        with patch("app.core.ssh_client._KNOWN_HOSTS_PATH", Path("dummy")), \
             patch.object(Path, "mkdir"), \
             patch.object(Path, "exists", return_value=True), \
             patch("app.core.ssh_client.os.chmod"):
            _ensure_known_hosts_dir()
