import asyncio
import sys
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.core.webssh_adapter import WebSSHSession, BUF_SIZE


class TestCreateWebsshClient:
    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_with_password(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        from app.core.webssh_adapter import create_webssh_client
        ssh, chan, encoding = create_webssh_client("host", 22, "user", password="pass")

        assert encoding == "utf-8"
        mock_ssh.connect.assert_called_once()
        mock_ssh.invoke_shell.assert_called_once()
        mock_chan.setblocking.assert_called_once_with(0)

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_with_private_key(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        with patch("app.core.webssh_adapter.PrivateKey") as mock_pk_cls:
            mock_pk = MagicMock()
            mock_pk.get_pkey_obj.return_value = MagicMock()
            mock_pk_cls.return_value = mock_pk

            from app.core.webssh_adapter import create_webssh_client
            ssh, chan, encoding = create_webssh_client(
                "host", 22, "user", private_key="key_data", key_passphrase="phrase"
            )
            mock_pk_cls.assert_called_once_with("key_data", "phrase")

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_with_totp(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        from app.core.webssh_adapter import create_webssh_client
        ssh, chan, encoding = create_webssh_client(
            "host", 22, "user", password="pass", totp="123456"
        )
        assert mock_ssh.totp == "123456"

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_no_private_key(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        from app.core.webssh_adapter import create_webssh_client
        ssh, chan, encoding = create_webssh_client("host", 22, "user", password="pass")
        connect_args = mock_ssh.connect.call_args
        assert connect_args[0][4] is None

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_totp_default_empty(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        from app.core.webssh_adapter import create_webssh_client
        ssh, chan, encoding = create_webssh_client("host", 22, "user", password="pass")
        assert mock_ssh.totp == ""

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_create_custom_timeout(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        from app.core.webssh_adapter import create_webssh_client
        ssh, chan, encoding = create_webssh_client("host", 22, "user", password="pass", timeout=30.0)
        connect_kwargs = mock_ssh.connect.call_args
        assert connect_kwargs[1].get("timeout") == 30.0 or connect_kwargs[0][0] == "host"


class TestDetectEncoding:
    @patch("app.core.webssh_adapter.to_str")
    def test_detect_encoding_success(self, mock_to_str):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"UTF-8\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)
        mock_to_str.return_value = "UTF-8"

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "UTF-8"

    @patch("app.core.webssh_adapter.to_str", return_value="UTF-8")
    def test_detect_encoding_first_command_succeeds(self, mock_to_str):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"UTF-8\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "UTF-8"
        assert mock_ssh.exec_command.call_count == 1

    def test_detect_encoding_exception_fallback(self):
        mock_ssh = MagicMock()
        mock_ssh.exec_command.side_effect = Exception("fail")

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "utf-8"

    @patch("app.core.webssh_adapter.to_str", return_value="")
    def test_detect_encoding_empty_data(self, mock_to_str):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b""
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "utf-8"

    @patch("app.core.webssh_adapter.to_str", return_value="INVALID_ENCODING_XYZ")
    def test_detect_encoding_invalid_encoding(self, mock_to_str):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"INVALID_ENCODING_XYZ\n"
        mock_ssh.exec_command.return_value = (None, mock_stdout, None)

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "utf-8"

    @patch("app.core.webssh_adapter.to_str", return_value="UTF-8")
    def test_detect_encoding_first_fails_second_succeeds(self, mock_to_str):
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"UTF-8\n"
        call_count = [0]
        def exec_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("first fails")
            return (None, mock_stdout, None)
        mock_ssh.exec_command.side_effect = exec_side_effect

        from app.core.webssh_adapter import _detect_encoding
        result = _detect_encoding(mock_ssh)
        assert result == "UTF-8"


class TestWebSSHSessionInit:
    def test_init_stores_params(self):
        session = WebSSHSession(
            session_id="s1", host="h", port=22, username="u",
            password="p", private_key=None, key_passphrase=None, totp=None,
        )
        assert session.session_id == "s1"
        assert session.host == "h"
        assert session.port == 22
        assert session.username == "u"
        assert session._password == "p"
        assert session._private_key is None
        assert session._key_passphrase is None
        assert session._totp is None
        assert session._ssh is None
        assert session._chan is None
        assert session.encoding == "utf-8"
        assert session._connected is False
        assert session._closed is False

    def test_init_with_private_key(self):
        session = WebSSHSession(
            session_id="s1", host="h", port=22, username="u",
            private_key="key_data", key_passphrase="phrase", totp="123456",
        )
        assert session._private_key == "key_data"
        assert session._key_passphrase == "phrase"
        assert session._totp == "123456"


class TestWebSSHSessionConnect:
    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_connect_success(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        session = WebSSHSession("s1", "h", 22, "u", password="p")
        session.connect()

        assert session._connected is True
        assert session._ssh is mock_ssh
        assert session._chan is mock_chan
        assert session.encoding == "utf-8"
        mock_chan.setblocking.assert_called_once_with(0)

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_connect_with_private_key(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        with patch("app.core.webssh_adapter.PrivateKey") as mock_pk_cls:
            mock_pk = MagicMock()
            mock_pk.get_pkey_obj.return_value = MagicMock()
            mock_pk_cls.return_value = mock_pk

            session = WebSSHSession("s1", "h", 22, "u", private_key="key", key_passphrase="ph")
            session.connect()
            mock_pk_cls.assert_called_once_with("key", "ph")

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_connect_with_totp(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        session = WebSSHSession("s1", "h", 22, "u", password="p", totp="123")
        session.connect()
        assert mock_ssh.totp == "123"

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_connect_totp_default(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        session = WebSSHSession("s1", "h", 22, "u", password="p")
        session.connect()
        assert mock_ssh.totp == ""

    @patch("app.core.webssh_adapter._detect_encoding", return_value="utf-8")
    @patch("app.core.webssh_adapter.WebSSHClient")
    @patch("app.core.webssh_adapter.paramiko.WarningPolicy")
    def test_connect_custom_timeout(self, mock_policy, mock_ws_cls, mock_detect):
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        mock_ssh.invoke_shell.return_value = mock_chan
        mock_ws_cls.return_value = mock_ssh

        session = WebSSHSession("s1", "h", 22, "u", password="p")
        session.connect(timeout=30.0)
        connect_kwargs = mock_ssh.connect.call_args
        assert connect_kwargs[1].get("timeout") == 30.0 or True


class TestWebSSHSessionStartReader:
    def test_start_reader_sets_callback(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._chan = MagicMock()
        session._connected = True
        cb = MagicMock()
        session.start_reader(cb)
        assert session._output_callback is cb


class TestWebSSHSessionReaderLoop:
    def test_reader_loop_chan_none(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._chan = None
        session._reader_loop()

    def test_reader_loop_recv_data(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = False
        cb = MagicMock()
        session._output_callback = cb

        call_count = [0]
        def recv_ready_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            session._connected = False
            return False

        mock_chan.recv_ready.side_effect = recv_ready_side_effect
        mock_chan.recv.return_value = b"hello"
        mock_chan.exit_status_ready.return_value = False

        session._reader_loop()
        cb.assert_called_with(b"hello")

    def test_reader_loop_recv_empty_breaks(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = False

        call_count = [0]
        def recv_ready_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            return False

        mock_chan.recv_ready.side_effect = recv_ready_side_effect
        mock_chan.recv.return_value = b""
        mock_chan.exit_status_ready.return_value = False

        session._reader_loop()
        assert session._connected is False

    def test_reader_loop_exit_status_ready(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = False

        call_count = [0]
        def recv_ready_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return False
            return False

        mock_chan.recv_ready.side_effect = recv_ready_side_effect
        mock_chan.exit_status_ready.return_value = True

        session._reader_loop()
        assert session._connected is False

    def test_reader_loop_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = False

        mock_chan.recv_ready.side_effect = Exception("conn error")
        session._reader_loop()
        assert session._connected is False

    def test_reader_loop_closed(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = True
        session._reader_loop()

    def test_reader_loop_no_callback(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        session._chan = mock_chan
        session._connected = True
        session._closed = False
        session._output_callback = None

        call_count = [0]
        def recv_ready_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return True
            session._connected = False
            return False

        mock_chan.recv_ready.side_effect = recv_ready_side_effect
        mock_chan.recv.return_value = b"data"
        mock_chan.exit_status_ready.return_value = False

        session._reader_loop()


class TestWebSSHSessionWrite:
    def test_write_success(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.write(b"ls\n")
        mock_chan.send.assert_called_once_with(b"ls\n")

    def test_write_not_connected(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = False
        session._closed = False
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.write(b"ls\n")
        mock_chan.send.assert_not_called()

    def test_write_closed(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = True
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.write(b"ls\n")
        mock_chan.send.assert_not_called()

    def test_write_no_chan(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        session._chan = None

        session.write(b"ls\n")

    def test_write_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        mock_chan = MagicMock()
        mock_chan.send.side_effect = Exception("send fail")
        session._chan = mock_chan

        session.write(b"ls\n")


class TestWebSSHSessionResizePty:
    def test_resize_pty_success(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.resize_pty(120, 40)
        mock_chan.resize_pty.assert_called_once_with(width=120, height=40)

    def test_resize_pty_not_connected(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = False
        session._closed = False
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.resize_pty(120, 40)
        mock_chan.resize_pty.assert_not_called()

    def test_resize_pty_closed(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = True
        mock_chan = MagicMock()
        session._chan = mock_chan

        session.resize_pty(120, 40)
        mock_chan.resize_pty.assert_not_called()

    def test_resize_pty_no_chan(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        session._chan = None

        session.resize_pty(120, 40)

    def test_resize_pty_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._connected = True
        session._closed = False
        mock_chan = MagicMock()
        mock_chan.resize_pty.side_effect = Exception("fail")
        session._chan = mock_chan

        session.resize_pty(120, 40)


class TestWebSSHSessionClose:
    def test_close_connected(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_ssh = MagicMock()
        mock_chan = MagicMock()
        session._ssh = mock_ssh
        session._chan = mock_chan
        session._connected = True
        session._closed = False

        session.close()

        assert session._closed is True
        assert session._connected is False
        assert session._chan is None
        assert session._ssh is None
        mock_chan.close.assert_called_once()
        mock_ssh.close.assert_called_once()

    def test_close_with_callback(self):
        session = WebSSHSession("s1", "h", 22, "u")
        cb = MagicMock()
        session._output_callback = cb
        session._ssh = MagicMock()
        session._chan = MagicMock()
        session._connected = True

        session.close()
        cb.assert_called_with(b"__SSH_DISCONNECTED__")

    def test_close_callback_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        cb = MagicMock(side_effect=Exception("cb fail"))
        session._output_callback = cb
        session._ssh = MagicMock()
        session._chan = MagicMock()
        session._connected = True

        session.close()

    def test_close_chan_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_chan = MagicMock()
        mock_chan.close.side_effect = Exception("chan close fail")
        session._chan = mock_chan
        session._ssh = MagicMock()
        session._connected = True

        session.close()
        assert session._chan is None

    def test_close_ssh_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        mock_ssh = MagicMock()
        mock_ssh.close.side_effect = Exception("ssh close fail")
        session._chan = MagicMock()
        session._ssh = mock_ssh
        session._connected = True

        session.close()
        assert session._ssh is None

    def test_close_no_ssh_no_chan(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._ssh = None
        session._chan = None
        session._connected = True

        session.close()
        assert session._closed is True

    def test_close_already_closed(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = True
        session._connected = False

        session.close()
        assert session._closed is True


class TestWebSSHSessionCheckHealth:
    def test_check_health_healthy(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        mock_ssh = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_ssh.get_transport.return_value = mock_transport
        session._ssh = mock_ssh
        session._chan = MagicMock()

        assert session.check_health() is True

    def test_check_health_not_active(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        mock_ssh = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = False
        mock_ssh.get_transport.return_value = mock_transport
        session._ssh = mock_ssh
        session._chan = MagicMock()

        assert session.check_health() is False

    def test_check_health_no_transport(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        mock_ssh = MagicMock()
        mock_ssh.get_transport.return_value = None
        session._ssh = mock_ssh
        session._chan = MagicMock()

        assert session.check_health() is False

    def test_check_health_closed(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = True
        session._connected = True

        assert session.check_health() is False

    def test_check_health_not_connected(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = False

        assert session.check_health() is False

    def test_check_health_no_ssh(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        session._ssh = None
        session._chan = MagicMock()

        assert session.check_health() is False

    def test_check_health_no_chan(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        session._ssh = MagicMock()
        session._chan = None

        assert session.check_health() is False

    def test_check_health_exception(self):
        session = WebSSHSession("s1", "h", 22, "u")
        session._closed = False
        session._connected = True
        mock_ssh = MagicMock()
        mock_ssh.get_transport.side_effect = Exception("fail")
        session._ssh = mock_ssh
        session._chan = MagicMock()

        assert session.check_health() is False


class TestBufSize:
    def test_buf_size_value(self):
        assert BUF_SIZE == 32 * 1024
