import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestListSessions:
    @patch("app.api.routes.webssh.webssh_service")
    def test_list_sessions_success(self, mock_service):
        mock_session = MagicMock()
        mock_session.model_dump.return_value = {"session_id": "sess1", "host": "192.168.1.1"}
        mock_service.list_sessions.return_value = [mock_session]
        mock_service.list_groups.return_value = ["group1"]
        mock_service.get_session_count.return_value = {"total": 1, "active": 1}
        resp = client.get("/api/webssh/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["sessions"]) == 1
        assert "group1" in data["groups"]

    @patch("app.api.routes.webssh.webssh_service")
    def test_list_sessions_with_group(self, mock_service):
        mock_service.list_sessions.return_value = []
        mock_service.list_groups.return_value = []
        mock_service.get_session_count.return_value = {"total": 0, "active": 0}
        resp = client.get("/api/webssh/sessions?group=group1")
        assert resp.status_code == 200
        mock_service.list_sessions.assert_called_with(group="group1")

    @patch("app.api.routes.webssh.webssh_service")
    def test_list_sessions_empty(self, mock_service):
        mock_service.list_sessions.return_value = []
        mock_service.list_groups.return_value = []
        mock_service.get_session_count.return_value = {"total": 0, "active": 0}
        resp = client.get("/api/webssh/sessions")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestTestConnection:
    @patch("app.api.routes.webssh.webssh_service")
    def test_test_connection_success(self, mock_service):
        mock_session = MagicMock()
        mock_session.session_id = "sess1"
        mock_service.create_session.return_value = mock_session
        resp = client.post(
            "/api/webssh/test",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_service.close_session.assert_called_with("sess1")

    @patch("app.api.routes.webssh.webssh_service")
    def test_test_connection_value_error(self, mock_service):
        mock_service.create_session.side_effect = ValueError("invalid params")
        resp = client.post(
            "/api/webssh/test",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.webssh.webssh_service")
    def test_test_connection_runtime_error(self, mock_service):
        mock_service.create_session.side_effect = RuntimeError("connection refused")
        resp = client.post(
            "/api/webssh/test",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 502

    @patch("app.api.routes.webssh.webssh_service")
    def test_test_connection_generic_error(self, mock_service):
        mock_service.create_session.side_effect = Exception("unexpected")
        resp = client.post(
            "/api/webssh/test",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 500


class TestConnectSSH:
    @patch("app.api.routes.webssh.webssh_service")
    def test_connect_success(self, mock_service):
        mock_session = MagicMock()
        mock_session.session_id = "sess1"
        mock_session.model_dump.return_value = {"session_id": "sess1", "host": "192.168.1.1"}
        mock_service.create_session.return_value = mock_session
        resp = client.post(
            "/api/webssh/connect",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["session"]["session_id"] == "sess1"

    @patch("app.api.routes.webssh.webssh_service")
    def test_connect_value_error(self, mock_service):
        mock_service.create_session.side_effect = ValueError("bad params")
        resp = client.post(
            "/api/webssh/connect",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.webssh.webssh_service")
    def test_connect_runtime_error(self, mock_service):
        mock_service.create_session.side_effect = RuntimeError("timeout")
        resp = client.post(
            "/api/webssh/connect",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 502

    @patch("app.api.routes.webssh.webssh_service")
    def test_connect_generic_error(self, mock_service):
        mock_service.create_session.side_effect = Exception("unknown error")
        resp = client.post(
            "/api/webssh/connect",
            json={"account_alias": "srv1", "host": "192.168.1.1", "username": "root"},
        )
        assert resp.status_code == 500


class TestDisconnectSSH:
    @patch("app.api.routes.webssh.webssh_service")
    def test_disconnect_success(self, mock_service):
        mock_session = MagicMock()
        mock_service.get_session.return_value = mock_session
        resp = client.post(
            "/api/webssh/disconnect",
            json={"session_id": "sess1"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("app.api.routes.webssh.webssh_service")
    def test_disconnect_session_not_found(self, mock_service):
        mock_service.get_session.return_value = None
        resp = client.post(
            "/api/webssh/disconnect",
            json={"session_id": "nonexistent"},
        )
        assert resp.status_code == 404


class TestResizeTerminal:
    @patch("app.api.routes.webssh.webssh_service")
    def test_resize_success(self, mock_service):
        resp = client.post(
            "/api/webssh/resize",
            json={"session_id": "sess1", "width": 120, "height": 40},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("app.api.routes.webssh.webssh_service")
    def test_resize_value_error(self, mock_service):
        mock_service.resize_session.side_effect = ValueError("session not found")
        resp = client.post(
            "/api/webssh/resize",
            json={"session_id": "nonexistent", "width": 120, "height": 40},
        )
        assert resp.status_code == 404

    @patch("app.api.routes.webssh.webssh_service")
    def test_resize_generic_error(self, mock_service):
        mock_service.resize_session.side_effect = Exception("resize error")
        resp = client.post(
            "/api/webssh/resize",
            json={"session_id": "sess1", "width": 120, "height": 40},
        )
        assert resp.status_code == 500


class TestSendCommand:
    @patch("app.api.routes.webssh.webssh_service")
    def test_send_command_success(self, mock_service):
        resp = client.post(
            "/api/webssh/command",
            json={"session_id": "sess1", "command": "ls -la"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_service.write_to_session.assert_called_once()

    @patch("app.api.routes.webssh.webssh_service")
    def test_send_command_value_error(self, mock_service):
        mock_service.write_to_session.side_effect = ValueError("session not found")
        resp = client.post(
            "/api/webssh/command",
            json={"session_id": "nonexistent", "command": "ls"},
        )
        assert resp.status_code == 404

    @patch("app.api.routes.webssh.webssh_service")
    def test_send_command_generic_error(self, mock_service):
        mock_service.write_to_session.side_effect = Exception("write error")
        resp = client.post(
            "/api/webssh/command",
            json={"session_id": "sess1", "command": "ls"},
        )
        assert resp.status_code == 500


class TestSessionHistory:
    @patch("app.api.routes.webssh.webssh_service")
    def test_get_session_history(self, mock_service):
        mock_service.list_session_history.return_value = [{"session_id": "sess1"}]
        resp = client.get("/api/webssh/sessions/history")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    @patch("app.api.routes.webssh.webssh_service")
    def test_get_session_history_empty(self, mock_service):
        mock_service.list_session_history.return_value = []
        resp = client.get("/api/webssh/sessions/history")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestDeleteSessionHistory:
    @patch("app.api.routes.webssh.webssh_service")
    def test_delete_session_history(self, mock_service):
        resp = client.delete("/api/webssh/sessions/history/sess1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_service.delete_session_history.assert_called_with("sess1")


class TestCommandHistory:
    def test_get_command_history_empty(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        try:
            resp = client.get("/api/webssh/history")
            assert resp.status_code == 200
            assert resp.json()["count"] == 0
        finally:
            webssh_module._history_store.update(original)

    def test_get_command_history_with_session(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        webssh_module._history_store["sess1"] = [
            {"session_id": "sess1", "command": "ls", "timestamp": "2024-01-01T00:00:00"},
        ]
        try:
            resp = client.get("/api/webssh/history?session_id=sess1")
            assert resp.status_code == 200
            assert resp.json()["count"] == 1
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)

    def test_get_command_history_all_sessions(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        webssh_module._history_store["sess1"] = [
            {"session_id": "sess1", "command": "ls", "timestamp": "2024-01-01T00:00:00"},
        ]
        webssh_module._history_store["sess2"] = [
            {"session_id": "sess2", "command": "pwd", "timestamp": "2024-01-01T00:01:00"},
        ]
        try:
            resp = client.get("/api/webssh/history")
            assert resp.status_code == 200
            assert resp.json()["count"] == 2
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)

    def test_get_command_history_with_limit(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        webssh_module._history_store["sess1"] = [
            {"session_id": "sess1", "command": f"cmd{i}", "timestamp": f"2024-01-01T00:0{i}:00"}
            for i in range(10)
        ]
        try:
            resp = client.get("/api/webssh/history?session_id=sess1&limit=3")
            assert resp.status_code == 200
            assert resp.json()["count"] == 3
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)


class TestRecordHistory:
    def test_record_history_adds_entry(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        try:
            webssh_module._record_history("sess1", "ls -la")
            assert "sess1" in webssh_module._history_store
            assert len(webssh_module._history_store["sess1"]) == 1
            assert webssh_module._history_store["sess1"][0]["command"] == "ls -la"
            assert webssh_module._history_store["sess1"][0]["session_id"] == "sess1"
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)

    def test_record_history_max_limit(self):
        import app.api.routes.webssh as webssh_module
        original = webssh_module._history_store.copy()
        webssh_module._history_store.clear()
        try:
            for i in range(600):
                webssh_module._record_history("sess1", f"cmd{i}")
            assert len(webssh_module._history_store["sess1"]) == 500
        finally:
            webssh_module._history_store.clear()
            webssh_module._history_store.update(original)
