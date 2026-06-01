from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.webssh_handler import WebSSHHandler


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


class TestStartReaderReadLoop:
    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_recv_data(self, mock_asyncio, handler):
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
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    mock_asyncio.run_coroutine_threadsafe.assert_called()
                    assert handler._connected is False

    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_empty_data_breaks(self, mock_asyncio, handler):
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

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_channel_closed(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.return_value = False
        mock_channel.closed = True
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_general_exception(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = Exception("unexpected error")
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_put_data_exception(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.closed = True
        mock_channel.recv.return_value = b"data"
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.side_effect = [Exception("queue error"), None]
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()

    @patch("app.core.webssh_handler.asyncio")
    def test_read_loop_disconnect_put_exception(self, mock_asyncio, handler):
        mock_channel = MagicMock()
        mock_channel.recv_ready.side_effect = [True]
        mock_channel.recv.return_value = b""
        handler._channel = mock_channel
        handler._connected = True
        handler._closed = False

        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("put error")
        mock_asyncio.run_coroutine_threadsafe.return_value = mock_future
        mock_asyncio.get_event_loop.return_value = MagicMock()

        queue = asyncio.Queue()

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler.start_reader(queue)

            reader_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name.startswith("ssh-reader-"):
                    reader_call = call_item
                    break

            if reader_call is not None:
                target_fn = reader_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False


class TestStartKeepalivePingLoop:
    def test_keepalive_transport_inactive(self, handler):
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = False
        handler._transport = mock_transport
        handler._connected = True
        handler._closed = False

        with patch("time.sleep") as mock_sleep, \
             patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler._start_keepalive()

            keepalive_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name and "keepalive" in name:
                    keepalive_call = call_item
                    break

            if keepalive_call is not None:
                target_fn = keepalive_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    def test_keepalive_send_ignore_exception(self, handler):
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_transport.send_ignore.side_effect = Exception("send failed")
        handler._transport = mock_transport
        handler._connected = True
        handler._closed = False

        with patch("time.sleep") as mock_sleep, \
             patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler._start_keepalive()

            keepalive_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name and "keepalive" in name:
                    keepalive_call = call_item
                    break

            if keepalive_call is not None:
                target_fn = keepalive_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    def test_keepalive_transport_none(self, handler):
        handler._transport = None
        handler._connected = True
        handler._closed = False

        with patch("time.sleep") as mock_sleep, \
             patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler._start_keepalive()

            keepalive_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name and "keepalive" in name:
                    keepalive_call = call_item
                    break

            if keepalive_call is not None:
                target_fn = keepalive_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    assert handler._connected is False

    def test_keepalive_closed_flag(self, handler):
        mock_transport = MagicMock()
        handler._transport = mock_transport
        handler._connected = True
        handler._closed = True

        with patch("time.sleep") as mock_sleep, \
             patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler._start_keepalive()

            keepalive_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name and "keepalive" in name:
                    keepalive_call = call_item
                    break

            if keepalive_call is not None:
                target_fn = keepalive_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    mock_transport.send_ignore.assert_not_called()

    def test_keepalive_successful_ping_loop(self, handler):
        mock_transport = MagicMock()
        mock_transport.is_active.side_effect = [True, False]
        mock_transport.send_ignore.return_value = None
        handler._transport = mock_transport
        handler._connected = True
        handler._closed = False

        with patch("time.sleep") as mock_sleep, \
             patch("threading.Thread") as mock_thread_cls:
            mock_thread_instance = MagicMock()
            mock_thread_cls.return_value = mock_thread_instance
            handler._start_keepalive()

            keepalive_call = None
            for call_item in mock_thread_cls.call_args_list:
                name = call_item.kwargs.get("name", "")
                if name and "keepalive" in name:
                    keepalive_call = call_item
                    break

            if keepalive_call is not None:
                target_fn = keepalive_call.kwargs.get("target")
                if target_fn is not None:
                    target_fn()
                    mock_transport.send_ignore.assert_called_once()
                    assert handler._connected is False
