"""WebSSH接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestWebSSHAPI:
    """WebSSH接口测试"""

    @patch("app.api.routes.webssh.webssh_service")
    def test_webssh_list_sessions(self, mock_webssh_service, client):
        mock_webssh_service.list_sessions.return_value = []
        mock_webssh_service.list_groups.return_value = []
        mock_webssh_service.get_session_count.return_value = 0

        response = client.get("/api/webssh/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "count" in data
        assert "groups" in data

    @patch("app.api.routes.webssh.webssh_service")
    def test_webssh_disconnect(self, mock_webssh_service, client):
        mock_webssh_service.disconnect.return_value = {"success": True, "message": "已断开"}

        response = client.post(
            "/api/webssh/disconnect",
            json={"session_id": "session-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.webssh.webssh_service")
    def test_webssh_command(self, mock_webssh_service, client):
        mock_webssh_service.send_command.return_value = {"success": True}

        response = client.post(
            "/api/webssh/command",
            json={"session_id": "session-123", "command": "ls -la"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
