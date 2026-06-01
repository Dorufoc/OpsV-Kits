import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestWebSSHWebSocketSessionNotFound:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_session_not_found(self, mock_service):
        mock_service.get_session.return_value = None
        with client.websocket_connect("/api/webssh/ws/nonexistent") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不存在" in data["message"]


class TestWebSSHWebSocketAdapterNotAvailable:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_adapter_none(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_service._get_entry.return_value = None
        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不可用" in data["message"]

    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_adapter_attr_none(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_entry.adapter = None
        mock_service._get_entry.return_value = mock_entry
        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不可用" in data["message"]


class TestWebSSHWebSocketInfoMessage:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_sends_info_on_connect(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            assert info["encoding"] == "utf-8"
            assert info["session_id"] == "sess1"
            ws.send_json({"type": "disconnect"})


class TestWebSSHWebSocketPingPong:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_ping_pong(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            ws.send_json({"type": "disconnect"})


class TestWebSSHWebSocketInputMessage:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_input_message_no_crash(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            ws.send_json({"type": "input", "data": "ls -la"})
            ws.send_json({"type": "disconnect"})


class TestWebSSHWebSocketResizeMessage:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_resize_message_no_crash(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            ws.send_json({"type": "resize", "width": 120, "height": 40})
            ws.send_json({"type": "disconnect"})


class TestWebSSHWebSocketDisconnectSignal:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_disconnect_signal(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        def fake_start_reader(callback):
            callback(b"__SSH_DISCONNECTED__")

        mock_adapter.start_reader.side_effect = fake_start_reader

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            msg = ws.receive_json()
            assert msg["type"] == "disconnected"


class TestWebSSHWebSocketDataSignal:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_data_signal(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        def fake_start_reader(callback):
            callback(b"hello world")
            callback(b"__SSH_DISCONNECTED__")

        mock_adapter.start_reader.side_effect = fake_start_reader

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            assert info["type"] == "info"
            data_msg = ws.receive_json()
            assert data_msg["type"] == "data"
            assert "hello world" in data_msg["content"]
            disc_msg = ws.receive_json()
            assert disc_msg["type"] == "disconnected"


class TestWebSSHWebSocketInputRecordsHistory:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_input_records_history(self, mock_service):
        import app.api.routes.webssh as webssh_module

        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()

        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        try:
            with client.websocket_connect("/api/webssh/ws/sess1") as ws:
                info = ws.receive_json()
                ws.send_json({"type": "input", "data": "ls"})
                ws.send_json({"type": "disconnect"})
            assert "sess1" in webssh_module._history_store
            assert any(
                r["command"] == "ls"
                for r in webssh_module._history_store["sess1"]
            )
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)


class TestWebSSHWebSocketInputEscapeSequence:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_input_escape_not_recorded(self, mock_service):
        import app.api.routes.webssh as webssh_module

        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()

        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        try:
            with client.websocket_connect("/api/webssh/ws/sess1") as ws:
                info = ws.receive_json()
                ws.send_json({"type": "input", "data": "\x1b[A"})
                ws.send_json({"type": "disconnect"})
            if "sess1" in webssh_module._history_store:
                for r in webssh_module._history_store["sess1"]:
                    assert r["command"] != "\x1b[A"
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)


class TestWebSSHWebSocketInvalidJSON:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_invalid_json_ignored(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            ws.send_text("not valid json{{{")
            ws.send_json({"type": "disconnect"})


class TestWebSSHWebSocketInputNonString:
    @patch("app.api.routes.webssh.webssh_service")
    def test_ws_input_non_string_data(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        mock_entry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.encoding = "utf-8"
        mock_entry.adapter = mock_adapter
        mock_service._get_entry.return_value = mock_entry
        mock_service.close_session.return_value = None

        with client.websocket_connect("/api/webssh/ws/sess1") as ws:
            info = ws.receive_json()
            ws.send_json({"type": "input", "data": 12345})
            ws.send_json({"type": "disconnect"})
            mock_adapter.write.assert_not_called()
