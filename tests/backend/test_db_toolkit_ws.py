from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
def redis_conn():
    return RedisConnectionParams(
        host="10.0.0.2", port=6379, password="redis_pass", db=2
    )


@pytest.fixture
def redis_conn_no_password():
    return RedisConnectionParams(
        host="10.0.0.2", port=6379, password="", db=0
    )


def _make_ssh_mock(chan=None, transport=None):
    mock_account = MagicMock()
    mock_conn = MagicMock()
    if transport is None and chan is not None:
        mock_transport = MagicMock()
        mock_transport.open_session.return_value = chan
        mock_conn.manager._transport = mock_transport
    elif transport is not None:
        mock_conn.manager._transport = transport
    else:
        mock_conn.manager._transport = None
    return mock_account, mock_conn


class TestHandleCliDirectMysqlNoPassword:
    @pytest.mark.asyncio
    async def test_mysql_direct_no_password(self, handler, mock_ws):
        conn = MySqlConnectionParams(host="10.0.0.1", port=3306, user="root", password="", database="mydb")
        with patch.object(handler, "_handle_cli_after_accept", new_callable=AsyncMock) as mock_after:
            await handler._handle_cli_direct(mock_ws, "srv1", None, conn, "mysql")
            cli_command = mock_after.call_args[0][3]
            safe_command = mock_after.call_args[0][4]
            assert "-p" not in cli_command
            assert "-p" not in safe_command
            assert "mydb" in cli_command

    @pytest.mark.asyncio
    async def test_mysql_direct_no_database(self, handler, mock_ws):
        conn = MySqlConnectionParams(host="10.0.0.1", port=3306, user="root", password="pw", database="")
        with patch.object(handler, "_handle_cli_after_accept", new_callable=AsyncMock) as mock_after:
            await handler._handle_cli_direct(mock_ws, "srv1", None, conn, "mysql")
            cli_command = mock_after.call_args[0][3]
            assert cli_command.endswith("-ppw")

    @pytest.mark.asyncio
    async def test_redis_direct_no_password(self, handler, mock_ws, redis_conn_no_password):
        with patch.object(handler, "_handle_cli_after_accept", new_callable=AsyncMock) as mock_after:
            await handler._handle_cli_direct(mock_ws, "srv1", None, redis_conn_no_password, "redis")
            cli_command = mock_after.call_args[0][3]
            safe_command = mock_after.call_args[0][4]
            assert "-a" not in cli_command
            assert "-a" not in safe_command


class TestHandleCliAfterAcceptReaderOutput:
    @pytest.mark.asyncio
    async def test_reader_thread_created(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("threading.Thread") as mock_thread_cls:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_thread_cls.assert_called_once()
            assert mock_thread_cls.call_args[1]["daemon"] is True
            mock_thread.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_reader_logic_data_flow(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.side_effect = [True, False, False]
        mock_chan.recv.return_value = b"hello"
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, False, True]

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("app.core.db_toolkit_ws._safe_ws_send") as mock_send, \
             patch("threading.Thread") as mock_thread_cls, \
             patch("app.core.db_toolkit_ws.threading.Event", return_value=stop_event):
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            target_fn = mock_thread_cls.call_args[1]["target"]
            target_fn()
            data_calls = [
                c for c in mock_send.call_args_list
                if len(c[0]) >= 2 and c[0][1].get("type") == "data"
            ]
            assert len(data_calls) >= 1
            assert data_calls[0][0][1]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_reader_logic_empty_recv(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.side_effect = [True, False]
        mock_chan.recv.return_value = b""
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("app.core.db_toolkit_ws._safe_ws_send") as mock_send, \
             patch("threading.Thread") as mock_thread_cls, \
             patch("app.core.db_toolkit_ws.threading.Event", return_value=stop_event):
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            target_fn = mock_thread_cls.call_args[1]["target"]
            target_fn()
            disconnected_calls = [
                c for c in mock_send.call_args_list
                if len(c[0]) >= 2 and c[0][1].get("type") == "disconnected"
            ]
            assert len(disconnected_calls) >= 1

    @pytest.mark.asyncio
    async def test_reader_logic_exit_with_remaining(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.side_effect = [False, True, False]
        mock_chan.exit_status_ready.side_effect = [True, False]
        mock_chan.recv.return_value = b"remaining"
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("app.core.db_toolkit_ws._safe_ws_send") as mock_send, \
             patch("threading.Thread") as mock_thread_cls, \
             patch("app.core.db_toolkit_ws.threading.Event", return_value=stop_event):
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            target_fn = mock_thread_cls.call_args[1]["target"]
            target_fn()
            data_calls = [
                c for c in mock_send.call_args_list
                if len(c[0]) >= 2 and c[0][1].get("type") == "data"
            ]
            assert len(data_calls) >= 1

    @pytest.mark.asyncio
    async def test_reader_logic_exception(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.side_effect = [True]
        mock_chan.recv.side_effect = Exception("channel error")
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        stop_event = MagicMock()
        stop_event.is_set.side_effect = [False, True]

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("app.core.db_toolkit_ws._safe_ws_send") as mock_send, \
             patch("threading.Thread") as mock_thread_cls, \
             patch("app.core.db_toolkit_ws.threading.Event", return_value=stop_event):
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            target_fn = mock_thread_cls.call_args[1]["target"]
            target_fn()
            error_calls = [
                c for c in mock_send.call_args_list
                if len(c[0]) >= 2 and c[0][1].get("type") == "error"
            ]
            assert len(error_calls) >= 1


class TestHandleCliAfterAcceptInputHandling:
    @pytest.mark.asyncio
    async def test_input_when_exit_status_ready(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "input", "data": "SELECT 1;"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_chan.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_input_with_no_data_key(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = False
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        call_count = 0
        original_send = mock_chan.send

        def send_side_effect(data):
            nonlocal call_count
            call_count += 1

        mock_chan.send.side_effect = send_side_effect

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh, \
             patch("threading.Thread"):
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "input"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            assert call_count >= 1

    @pytest.mark.asyncio
    async def test_resize_with_no_width_height(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "resize"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_chan.resize_pty.assert_called_with(width=80, height=24)

    @pytest.mark.asyncio
    async def test_unknown_message_type(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "unknown_type"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )

    @pytest.mark.asyncio
    async def test_receive_text_exception(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                "invalid json{",
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )

    @pytest.mark.asyncio
    async def test_disconnect_message_breaks_loop(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_chan.close.assert_called()


class TestHandleCliAfterAcceptConnectionError:
    @pytest.mark.asyncio
    async def test_ssh_connection_exception(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_chan_close_exception_in_finally(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_chan.close.side_effect = Exception("close error")
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )

    @pytest.mark.asyncio
    async def test_send_json_exception_on_error(self, handler, mock_ws):
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.send_json.side_effect = Exception("ws closed")
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleCliFullFlow:
    @pytest.mark.asyncio
    async def test_handle_cli_successful_connection(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_ws.accept.assert_called_once()
            info_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "info"
            ]
            assert len(info_calls) >= 1

    @pytest.mark.asyncio
    async def test_handle_cli_account_lookup_exception(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.side_effect = Exception("connection error")
            await handler._handle_cli(
                mock_ws, "bad_alias", None, "mysql -h x", "mysql -h x"
            )
            mock_ws.accept.assert_called_once()
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) >= 1
            mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cli_transport_none(self, handler, mock_ws):
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) >= 1

    @pytest.mark.asyncio
    async def test_handle_cli_with_container(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli(
                mock_ws, "srv1", "container123", "mysql -h x", "mysql -h x"
            )
            exec_cmd = mock_chan.exec_command.call_args[0][0]
            assert "docker exec -i container123" in exec_cmd

    @pytest.mark.asyncio
    async def test_handle_cli_ping_pong(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "ping"}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            pong_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "pong"
            ]
            assert len(pong_calls) >= 1

    @pytest.mark.asyncio
    async def test_handle_cli_connection_released(self, handler, mock_ws):
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)


class TestSafeWsSendExtra:
    def test_safe_ws_send_runtime_error_fallback_exception(self):
        ws = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = RuntimeError("no loop")
            with patch("concurrent.futures.ThreadPoolExecutor") as mock_pool_cls:
                mock_pool = MagicMock()
                mock_pool_cls.return_value.__enter__ = MagicMock(return_value=mock_pool)
                mock_pool_cls.return_value.__exit__ = MagicMock(return_value=False)
                mock_future = MagicMock()
                mock_future.result.side_effect = Exception("timeout")
                mock_pool.submit.return_value = mock_future
                _safe_ws_send(ws, {"type": "data"})
