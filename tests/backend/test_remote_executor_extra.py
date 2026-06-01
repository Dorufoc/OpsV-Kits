from unittest.mock import MagicMock, patch

import pytest

from app.models.ssh_account import SSHAccount


def _make_account(alias="test"):
    return SSHAccount(
        alias=alias, host="192.168.1.1", port=22,
        username="root", auth_type="password", password="secret",
    )


@pytest.fixture
def mock_pool():
    with patch("app.core.remote_executor.ssh_account_service") as mock_svc:
        account = _make_account()
        mock_svc.get_account.return_value = account
        mock_svc.pool = MagicMock()
        yield mock_svc, account


class TestExecWithPtyBytesOutput:
    def test_exec_with_pty_bytes_stdout(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_with_pty.return_value = (0, b"bytes output", "str stderr")
        mock_svc.pool.get_connection.return_value = mock_conn

        result = executor.exec_with_pty("cmd")
        assert result.stdout == "bytes output"
        assert result.stderr == "str stderr"

    def test_exec_with_pty_bytes_stderr(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_with_pty.return_value = (0, "str output", b"bytes stderr")
        mock_svc.pool.get_connection.return_value = mock_conn

        result = executor.exec_with_pty("cmd")
        assert result.stdout == "str output"
        assert result.stderr == "bytes stderr"


class TestExecCommandStreamWithData:
    def test_stream_recv_ready_data(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()

        exit_call = [0]
        def exit_ready():
            exit_call[0] += 1
            return exit_call[0] > 1

        recv_call = [0]
        def recv_ready():
            recv_call[0] += 1
            if recv_call[0] == 1:
                return True
            return False

        mock_chan.exit_status_ready.side_effect = exit_ready
        mock_chan.recv_ready.side_effect = recv_ready
        mock_chan.recv.return_value = b"stdout data"
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.recv_exit_status.return_value = 0
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        outputs = []
        exit_code = executor.exec_command_stream("cmd", output_callback=outputs.append)
        assert exit_code == 0
        assert "stdout data" in outputs

    def test_stream_recv_stderr_ready_data(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()

        exit_call = [0]
        def exit_ready():
            exit_call[0] += 1
            return exit_call[0] > 1

        stderr_call = [0]
        def stderr_ready():
            stderr_call[0] += 1
            if stderr_call[0] == 1:
                return True
            return False

        mock_chan.exit_status_ready.side_effect = exit_ready
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.side_effect = stderr_ready
        mock_chan.recv_stderr.return_value = b"stderr data"
        mock_chan.recv_exit_status.return_value = 1
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        outputs = []
        exit_code = executor.exec_command_stream("cmd", output_callback=outputs.append)
        assert exit_code == 1
        assert "stderr data" in outputs

    def test_stream_post_exit_recv_ready(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()

        mock_chan.exit_status_ready.return_value = True
        recv_ready_calls = [True, True, False]
        mock_chan.recv_ready.side_effect = recv_ready_calls
        mock_chan.recv.side_effect = [b"remaining stdout", b""]
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.recv_exit_status.return_value = 0
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        outputs = []
        exit_code = executor.exec_command_stream("cmd", output_callback=outputs.append)
        assert exit_code == 0
        assert "remaining stdout" in outputs

    def test_stream_post_exit_recv_stderr_ready(self, mock_pool):
        mock_svc, _ = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()

        mock_chan.exit_status_ready.return_value = True
        mock_chan.recv_ready.return_value = False
        stderr_ready_calls = [True, True, False]
        mock_chan.recv_stderr_ready.side_effect = stderr_ready_calls
        mock_chan.recv_stderr.side_effect = [b"remaining stderr", b""]
        mock_chan.recv_exit_status.return_value = 0
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        outputs = []
        exit_code = executor.exec_command_stream("cmd", output_callback=outputs.append)
        assert exit_code == 0
        assert "remaining stderr" in outputs
