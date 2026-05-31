from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.core.db_toolkit_ws import DbToolkitWebSocketHandler, _safe_ws_send
from app.models.db_toolkit import MySqlConnectionParams, RedisConnectionParams


@pytest.fixture
def handler():
    return DbToolkitWebSocketHandler()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    ws.accept = AsyncMock()
    return ws


@pytest.fixture
def mysql_conn():
    return MySqlConnectionParams(
        host="10.0.0.1", port=3306, user="root", password="secret", database="testdb"
    )


@pytest.fixture
def mysql_conn_no_password():
    return MySqlConnectionParams(
        host="10.0.0.1", port=3306, user="root", password="", database="testdb"
    )


@pytest.fixture
def mysql_conn_no_db():
    return MySqlConnectionParams(
        host="10.0.0.1", port=3306, user="root", password="secret", database=""
    )


@pytest.fixture
def redis_conn():
    return RedisConnectionParams(
        host="10.0.0.2", port=6379, password="redis_pass", db=2
    )


@pytest.fixture
def redis_conn_no_password():
    return RedisConnectionParams(
        host="10.0.0.2", port=6379, password="", db=0
    )


class TestSafeWsSend:
    def test_safe_ws_send_success(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete = MagicMock()
            _safe_ws_send(ws, {"type": "data", "content": "hello"})
            mock_loop.return_value.run_until_complete.assert_called_once()

    def test_safe_ws_send_runtime_error_fallback(self):
        ws = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = RuntimeError("no loop")
            with patch("concurrent.futures.ThreadPoolExecutor") as mock_pool_cls:
                mock_pool = MagicMock()
                mock_pool_cls.return_value.__enter__ = MagicMock(return_value=mock_pool)
                mock_pool_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_future = MagicMock()
                mock_future.result.return_value = None
                mock_pool.submit.return_value = mock_future
                _safe_ws_send(ws, {"type": "data"})
                mock_pool.submit.assert_called_once()

    def test_safe_ws_send_all_exceptions_caught(self):
        ws = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = RuntimeError("no loop")
            with patch("concurrent.futures.ThreadPoolExecutor") as mock_pool_cls:
                mock_pool_cls.return_value.__enter__ = MagicMock(side_effect=Exception("fail"))
                mock_pool_cls.return_value.__exit__ = MagicMock(return_value=False)
                _safe_ws_send(ws, {"type": "data"})

    def test_safe_ws_send_general_exception(self):
        ws = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = Exception("generic error")
            _safe_ws_send(ws, {"type": "data"})


class TestHandleMysqlCli:
    @pytest.mark.asyncio
    async def test_mysql_cli_command_with_password_and_db(self, handler, mock_ws, mysql_conn):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "server1", None, mysql_conn)
            call_args = mock_cli.call_args
            cli_command = call_args[0][3]
            safe_command = call_args[0][4]
            assert "mysql -h 10.0.0.1 -P 3306 -u root -psecret testdb" == cli_command
            assert "-p ***" in safe_command
            assert "secret" not in safe_command

    @pytest.mark.asyncio
    async def test_mysql_cli_command_no_password(self, handler, mock_ws, mysql_conn_no_password):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "server1", None, mysql_conn_no_password)
            call_args = mock_cli.call_args
            cli_command = call_args[0][3]
            safe_command = call_args[0][4]
            assert "-p" not in cli_command
            assert "-p" not in safe_command

    @pytest.mark.asyncio
    async def test_mysql_cli_command_no_db(self, handler, mock_ws, mysql_conn_no_db):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "server1", None, mysql_conn_no_db)
            call_args = mock_cli.call_args
            cli_command = call_args[0][3]
            assert cli_command.endswith("root -psecret")
            assert "testdb" not in cli_command

    @pytest.mark.asyncio
    async def test_mysql_cli_with_container(self, handler, mock_ws, mysql_conn):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "server1", "abc123", mysql_conn)
            assert mock_cli.called
            assert mock_cli.call_args[0][2] == "abc123"


class TestHandleRedisCli:
    @pytest.mark.asyncio
    async def test_redis_cli_command_with_password(self, handler, mock_ws, redis_conn):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_redis_cli(mock_ws, "server1", None, redis_conn)
            call_args = mock_cli.call_args
            cli_command = call_args[0][3]
            safe_command = call_args[0][4]
            assert "redis-cli -h 10.0.0.2 -p 6379 -a redis_pass -n 2" == cli_command
            assert "-a ***" in safe_command
            assert "redis_pass" not in safe_command

    @pytest.mark.asyncio
    async def test_redis_cli_command_no_password(self, handler, mock_ws, redis_conn_no_password):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_redis_cli(mock_ws, "server1", None, redis_conn_no_password)
            call_args = mock_cli.call_args
            cli_command = call_args[0][3]
            safe_command = call_args[0][4]
            assert "-a" not in cli_command
            assert "-a" not in safe_command

    @pytest.mark.asyncio
    async def test_redis_cli_with_container(self, handler, mock_ws, redis_conn):
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_redis_cli(mock_ws, "server1", "xyz789", redis_conn)
            assert mock_cli.called
            assert mock_cli.call_args[0][2] == "xyz789"


class TestHandleCliDirect:
    @pytest.mark.asyncio
    async def test_mysql_direct(self, handler, mock_ws, mysql_conn):
        with patch.object(handler, "_handle_cli_after_accept", new_callable=AsyncMock) as mock_after:
            await handler._handle_cli_direct(mock_ws, "server1", None, mysql_conn, "mysql")
            assert mock_after.called
            cli_command = mock_after.call_args[0][3]
            assert "mysql" in cli_command

    @pytest.mark.asyncio
    async def test_redis_direct(self, handler, mock_ws, redis_conn):
        with patch.object(handler, "_handle_cli_after_accept", new_callable=AsyncMock) as mock_after:
            await handler._handle_cli_direct(mock_ws, "server1", "container1", redis_conn, "redis")
            assert mock_after.called
            cli_command = mock_after.call_args[0][3]
            assert "redis-cli" in cli_command
            assert mock_after.call_args[0][2] == "container1"


class TestHandleCliAfterAccept:
    @pytest.mark.asyncio
    async def test_account_not_found(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            await handler._handle_cli_after_accept(
                mock_ws, "missing_alias", None, "mysql -h x", "mysql -h x"
            )
            mock_ws.send_json.assert_any_call({
                "type": "error",
                "message": "SSH 账户 'missing_alias' 不存在",
            })
            mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_account_lookup_exception(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.side_effect = Exception("connection error")
            await handler._handle_cli_after_accept(
                mock_ws, "bad_alias", None, "mysql -h x", "mysql -h x"
            )
            mock_ws.send_json.assert_any_call({
                "type": "error",
                "message": "connection error",
            })
            mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_connection_with_container(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", "container123", "mysql -h x", "mysql -h x"
            )
            mock_chan.exec_command.assert_called_once()
            exec_cmd = mock_chan.exec_command.call_args[0][0]
            assert "docker exec -i container123" in exec_cmd

    @pytest.mark.asyncio
    async def test_successful_connection_without_container(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            exec_cmd = mock_chan.exec_command.call_args[0][0]
            assert "docker exec" not in exec_cmd
            assert exec_cmd == "mysql -h x"

    @pytest.mark.asyncio
    async def test_transport_none_raises_error(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_input_message_sends_to_channel(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = False
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "input", "data": "SELECT 1;"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            mock_chan.send.assert_called_with("SELECT 1;")

    @pytest.mark.asyncio
    async def test_resize_message(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "resize", "width": 120, "height": 40}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            mock_chan.resize_pty.assert_called_with(width=120, height=40)

    @pytest.mark.asyncio
    async def test_ping_message(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "ping"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            pong_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "pong"
            ]
            assert len(pong_calls) >= 1

    @pytest.mark.asyncio
    async def test_connection_released_in_finally(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )
            mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_resize_pty_exception_swallowed(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_chan.resize_pty.side_effect = Exception("resize failed")
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager._transport = mock_transport

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "resize", "width": 120, "height": 40}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "server1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleCli:
    @pytest.mark.asyncio
    async def test_handle_cli_accepts_websocket(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            await handler._handle_cli(
                mock_ws, "missing", None, "mysql", "mysql"
            )
            mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cli_account_not_found(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            await handler._handle_cli(
                mock_ws, "missing", None, "mysql", "mysql"
            )
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) >= 1
