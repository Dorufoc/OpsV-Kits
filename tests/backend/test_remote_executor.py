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


class TestRemoteExecutorInit:
    def test_init_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        assert executor.account_alias == "test"

    def test_init_nonexistent_account(self, mock_pool):
        mock_svc, _ = mock_pool
        mock_svc.get_account.return_value = None
        from app.core.remote_executor import RemoteExecutor, RemoteExecutorError

        with pytest.raises(RemoteExecutorError, match="不存在"):
            RemoteExecutor("nonexistent")


class TestCommandResult:
    def test_success_property(self):
        from app.core.remote_executor import CommandResult

        result = CommandResult(exit_code=0, stdout="ok", stderr="")
        assert result.success is True

    def test_failure_property(self):
        from app.core.remote_executor import CommandResult

        result = CommandResult(exit_code=1, stdout="", stderr="error")
        assert result.success is False

    def test_repr(self):
        from app.core.remote_executor import CommandResult

        result = CommandResult(exit_code=0, stdout="ok", stderr="")
        r = repr(result)
        assert "CommandResult" in r


class TestRemoteExecutorExecCommand:
    def test_exec_command_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        result = executor.exec_command("ls")
        assert result.success is True
        assert result.stdout == "output"
        mock_svc.pool.release_connection.assert_called_once()

    def test_exec_command_bytes_output(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, b"output", b"err")
        mock_svc.pool.get_connection.return_value = mock_conn

        result = executor.exec_command("ls")
        assert result.stdout == "output"

    def test_exec_command_failure(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor, RemoteExecutorError

        executor = RemoteExecutor("test")
        mock_svc.pool.get_connection.side_effect = Exception("conn fail")

        with pytest.raises(RemoteExecutorError, match="命令执行失败"):
            executor.exec_command("ls")

    def test_exec_command_default_timeout(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "ok", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor.exec_command("ls")
        mock_conn.manager.exec_command.assert_called_with("ls", timeout=30.0)


class TestRemoteExecutorExecCommands:
    def test_exec_commands_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "ok", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        results = executor.exec_commands(["ls", "pwd"])
        assert len(results) == 2


class TestRemoteExecutorExecWithPty:
    def test_exec_with_pty_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.exec_with_pty.return_value = (0, "output", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        result = executor.exec_with_pty("top")
        assert result.success is True

    def test_exec_with_pty_failure(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor, RemoteExecutorError

        executor = RemoteExecutor("test")
        mock_svc.pool.get_connection.side_effect = Exception("fail")

        with pytest.raises(RemoteExecutorError, match="PTY 命令执行失败"):
            executor.exec_with_pty("top")


class TestRemoteExecutorExecCommandStream:
    def test_exec_command_stream_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()

        call_count = [0]

        def mock_exit_ready():
            call_count[0] += 1
            return call_count[0] > 1

        mock_chan.exit_status_ready.side_effect = mock_exit_ready
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.recv_exit_status.return_value = 0
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        outputs = []
        exit_code = executor.exec_command_stream("ls", output_callback=outputs.append)
        assert exit_code == 0

    def test_exec_command_stream_no_transport(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor, RemoteExecutorError

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.transport = None
        mock_conn.manager.encoding = "utf-8"
        mock_svc.pool.get_connection.return_value = mock_conn

        with pytest.raises(RemoteExecutorError, match="SSH 传输通道未建立"):
            executor.exec_command_stream("ls", output_callback=lambda x: None)

    def test_exec_command_stream_with_stop_check(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.encoding = "utf-8"
        mock_transport = MagicMock()
        mock_conn.manager.transport = mock_transport
        mock_chan = MagicMock()
        mock_chan.exit_status_ready.return_value = False
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_transport.open_session.return_value = mock_chan
        mock_svc.pool.get_connection.return_value = mock_conn

        exit_code = executor.exec_command_stream(
            "ls", output_callback=lambda x: None,
            stop_check=lambda: True,
        )
        assert exit_code == -1


class TestRemoteExecutorResolvePath:
    def test_resolve_path_non_tilde(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        assert executor.resolve_path("/absolute/path") == "/absolute/path"

    def test_resolve_path_tilde_success(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_conn = MagicMock()
        mock_conn.manager.client = MagicMock()
        mock_svc.pool.get_connection.return_value = mock_conn

        with patch("app.core.remote_executor.resolve_remote_path", return_value="/home/root/path"):
            result = executor.resolve_path("~/path")
            assert result == "/home/root/path"

    def test_resolve_path_tilde_fallback(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        mock_svc.pool.get_connection.side_effect = Exception("fail")

        result = executor.resolve_path("~/path")
        assert result == "/root/path"


class TestRemoteExecutorTestConnection:
    def test_test_connection(self, mock_pool):
        mock_svc, account = mock_pool
        from app.core.remote_executor import RemoteExecutor

        executor = RemoteExecutor("test")
        with patch("app.core.ssh_client.SSHClientManager") as mock_cls:
            mock_mgr = MagicMock()
            mock_mgr.test_connection.return_value = (True, "ok")
            mock_cls.return_value = mock_mgr
            success, msg = executor.test_connection()
            assert success is True
