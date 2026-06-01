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


class TestHandleCliAfterAcceptAccountErrors:
    @pytest.mark.asyncio
    async def test_account_none(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            await handler._handle_cli_after_accept(
                mock_ws, "bad_alias", None, "mysql -h x", "mysql -h x"
            )
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) >= 1
            mock_ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_account_exception(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.side_effect = Exception("db error")
            await handler._handle_cli_after_accept(
                mock_ws, "bad_alias", None, "mysql -h x", "mysql -h x"
            )
            error_calls = [
                c for c in mock_ws.send_json.call_args_list
                if c[0][0].get("type") == "error"
            ]
            assert len(error_calls) >= 1
            mock_ws.close.assert_called_once()


class TestHandleCliAfterAcceptContainerId:
    @pytest.mark.asyncio
    async def test_with_container_id(self, handler, mock_ws):
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
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", "container123", "mysql -h x", "mysql -h x"
            )
            exec_cmd = mock_chan.exec_command.call_args[0][0]
            assert "docker exec -i container123" in exec_cmd


class TestHandleCliAfterAcceptResizeException:
    @pytest.mark.asyncio
    async def test_resize_pty_exception_suppressed(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_chan.resize_pty.side_effect = Exception("resize failed")
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "resize", "width": 120, "height": 40}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli_after_accept(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleCliAccountErrors:
    @pytest.mark.asyncio
    async def test_account_none(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
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
    async def test_get_account_exception(self, handler, mock_ws):
        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.side_effect = Exception("conn error")
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


class TestHandleCliReaderLogic:
    @pytest.mark.asyncio
    async def test_reader_data_flow(self, handler, mock_ws):
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
            await handler._handle_cli(
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
    async def test_reader_exit_with_remaining(self, handler, mock_ws):
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
            await handler._handle_cli(
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
    async def test_reader_exception(self, handler, mock_ws):
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
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            target_fn = mock_thread_cls.call_args[1]["target"]
            target_fn()
            error_calls = [
                c for c in mock_send.call_args_list
                if len(c[0]) >= 2 and c[0][1].get("type") == "error"
            ]
            assert len(error_calls) >= 1


class TestHandleCliResizeException:
    @pytest.mark.asyncio
    async def test_resize_pty_exception_suppressed(self, handler, mock_ws):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = [False, True]
        mock_chan.resize_pty.side_effect = Exception("resize failed")
        mock_account, mock_conn = _make_ssh_mock(chan=mock_chan)

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = mock_account
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.receive_text.side_effect = [
                json.dumps({"type": "resize", "width": 120, "height": 40}),
                json.dumps({"type": "disconnect"}),
            ]
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleCliUnknownMessageType:
    @pytest.mark.asyncio
    async def test_unknown_type_ignored(self, handler, mock_ws):
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
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleCliChanCloseException:
    @pytest.mark.asyncio
    async def test_chan_close_exception_in_inner_finally(self, handler, mock_ws):
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
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )

    @pytest.mark.asyncio
    async def test_chan_close_exception_in_outer_finally(self, handler, mock_ws):
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )
            mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)


class TestHandleCliSendJsonExceptionOnError:
    @pytest.mark.asyncio
    async def test_send_json_exception_on_error(self, handler, mock_ws):
        mock_conn = MagicMock()
        mock_conn.manager._transport = None

        with patch("app.core.db_toolkit_ws.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            mock_ws.send_json.side_effect = Exception("ws closed")
            await handler._handle_cli(
                mock_ws, "srv1", None, "mysql -h x", "mysql -h x"
            )


class TestHandleMysqlCli:
    @pytest.mark.asyncio
    async def test_mysql_cli_with_password(self, handler, mock_ws):
        conn = MySqlConnectionParams(
            host="10.0.0.1", port=3306, user="root", password="secret", database="testdb"
        )
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "srv1", None, conn)
            cli_command = mock_cli.call_args[0][3]
            safe_command = mock_cli.call_args[0][4]
            assert "-psecret" in cli_command
            assert "-p ***" in safe_command
            assert "testdb" in cli_command

    @pytest.mark.asyncio
    async def test_mysql_cli_no_password(self, handler, mock_ws):
        conn = MySqlConnectionParams(
            host="10.0.0.1", port=3306, user="root", password="", database="mydb"
        )
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "srv1", None, conn)
            cli_command = mock_cli.call_args[0][3]
            safe_command = mock_cli.call_args[0][4]
            assert "-p" not in cli_command
            assert "-p" not in safe_command
            assert "mydb" in cli_command

    @pytest.mark.asyncio
    async def test_mysql_cli_no_database(self, handler, mock_ws):
        conn = MySqlConnectionParams(
            host="10.0.0.1", port=3306, user="root", password="pw", database=""
        )
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_mysql_cli(mock_ws, "srv1", None, conn)
            cli_command = mock_cli.call_args[0][3]
            assert cli_command.endswith("-ppw")


class TestHandleRedisCli:
    @pytest.mark.asyncio
    async def test_redis_cli_with_password(self, handler, mock_ws):
        conn = RedisConnectionParams(
            host="10.0.0.2", port=6379, password="redis_pass", db=2
        )
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_redis_cli(mock_ws, "srv1", None, conn)
            cli_command = mock_cli.call_args[0][3]
            safe_command = mock_cli.call_args[0][4]
            assert "-a redis_pass" in cli_command
            assert "-a ***" in safe_command
            assert "-n 2" in cli_command

    @pytest.mark.asyncio
    async def test_redis_cli_no_password(self, handler, mock_ws):
        conn = RedisConnectionParams(
            host="10.0.0.2", port=6379, password="", db=0
        )
        with patch.object(handler, "_handle_cli", new_callable=AsyncMock) as mock_cli:
            await handler.handle_redis_cli(mock_ws, "srv1", None, conn)
            cli_command = mock_cli.call_args[0][3]
            safe_command = mock_cli.call_args[0][4]
            assert "-a" not in cli_command
            assert "-a" not in safe_command
            assert "-n 0" in cli_command


class TestSafeWsSendGeneralException:
    def test_safe_ws_send_general_exception(self):
        ws = MagicMock()
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_until_complete.side_effect = Exception("general error")
            with patch("concurrent.futures.ThreadPoolExecutor"):
                _safe_ws_send(ws, {"type": "data"})
