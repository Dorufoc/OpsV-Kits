"""设置管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSettingsAPI:
    """设置管理API测试"""

    @patch("app.api.routes.settings.settings_service")
    def test_get_settings(self, mock_service, client):
        mock_service.get_all.return_value = {
            "session_ttl_hours": 24,
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
            "remote_drive_username": None,
            "remote_drive_password": None,
        }
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "session_ttl_hours" in data
        assert "remote_drive_enabled" in data

    @patch("app.services.remote_drive_service.remote_drive_service")
    @patch("app.api.routes.settings.settings_service")
    def test_update_settings_session_ttl(self, mock_service, mock_remote_drive, client):
        mock_service.get_all.return_value = {
            "session_ttl_hours": 48,
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
        }
        mock_service.get.side_effect = lambda key, default: {
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
        }.get(key, default)

        response = client.put(
            "/api/settings",
            json={"session_ttl_hours": 48},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_ttl_hours"] == 48

    @patch("app.services.remote_drive_service.remote_drive_service")
    @patch("app.api.routes.settings.settings_service")
    def test_update_settings_remote_drive_enable(self, mock_service, mock_remote_drive, client):
        mock_service.get_all.return_value = {
            "session_ttl_hours": 24,
            "remote_drive_enabled": True,
            "remote_drive_port": 8081,
        }
        mock_service.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 8081,
        }.get(key, default)
        mock_remote_drive.is_running = False

        response = client.put(
            "/api/settings",
            json={"remote_drive_enabled": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["remote_drive_enabled"] is True

    @patch("app.services.remote_drive_service.remote_drive_service")
    @patch("app.api.routes.settings.settings_service")
    def test_update_settings_remote_drive_disable(self, mock_service, mock_remote_drive, client):
        mock_service.get_all.return_value = {
            "session_ttl_hours": 24,
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
        }
        mock_service.get.side_effect = lambda key, default: {
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
        }.get(key, default)
        mock_remote_drive.is_running = True

        response = client.put(
            "/api/settings",
            json={"remote_drive_enabled": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["remote_drive_enabled"] is False

    @patch("app.api.routes.settings.settings_service")
    def test_update_settings_invalid_ttl(self, mock_service, client):
        response = client.put(
            "/api/settings",
            json={"session_ttl_hours": 0},
        )
        assert response.status_code == 422

    @patch("app.api.routes.settings.settings_service")
    def test_update_settings_invalid_port(self, mock_service, client):
        response = client.put(
            "/api/settings",
            json={"remote_drive_port": 80},
        )
        assert response.status_code == 422


class TestSettingsValidation:
    """设置数据验证测试"""

    def test_settings_update_valid_ttl(self):
        from app.api.routes.settings import SettingsUpdate
        settings = SettingsUpdate(session_ttl_hours=24)
        assert settings.session_ttl_hours == 24

    def test_settings_update_valid_port(self):
        from app.api.routes.settings import SettingsUpdate
        settings = SettingsUpdate(remote_drive_port=9090)
        assert settings.remote_drive_port == 9090

    def test_settings_update_multiple_fields(self):
        from app.api.routes.settings import SettingsUpdate
        settings = SettingsUpdate(
            session_ttl_hours=48,
            remote_drive_enabled=True,
            remote_drive_port=8082,
        )
        assert settings.session_ttl_hours == 48
        assert settings.remote_drive_enabled is True
        assert settings.remote_drive_port == 8082
