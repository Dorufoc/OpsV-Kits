"""远程磁盘管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestRemoteDriveStatus:
    """远程磁盘状态API测试"""

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_enabled_running(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试远程磁盘已启用且运行中的状态"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 8081,
            "remote_drive_username": "opsv",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = "encrypted_password"
        mock_remote_drive.is_running = True

        mock_account = MagicMock()
        mock_account.alias = "server1"
        mock_account.host = "192.168.1.100"
        mock_account.port = 22
        mock_account.is_default = True
        mock_account.username = "opsv"
        mock_ssh.list_accounts.return_value = [mock_account]

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["running"] is True
        assert data["port"] == 8081
        assert data["auth_username"] == "opsv"
        assert data["auth_password_set"] is True
        assert data["account_count"] == 1
        assert len(data["mounts"]) == 1
        assert data["mounts"][0]["alias"] == "server1"
        assert data["mounts"][0]["hostname"] == "192.168.1.100"
        assert data["mounts"][0]["port"] == 22
        assert "localhost:8081" in data["mounts"][0]["url"]
        assert "hostname" in data
        assert "webdav_url" in data
        assert "windows_url" in data

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_disabled_stopped(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试远程磁盘已禁用且未运行的状态"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
            "remote_drive_username": None,
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = None
        mock_remote_drive.is_running = False
        mock_ssh.list_accounts.return_value = []

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["running"] is False
        assert data["auth_password_set"] is False
        assert data["account_count"] == 0
        assert data["mounts"] == []

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_multiple_accounts(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试多个SSH账户的挂载列表"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 9090,
            "remote_drive_username": "admin",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = "secret"
        mock_remote_drive.is_running = True

        account1 = MagicMock()
        account1.alias = "prod-server"
        account1.host = "10.0.0.1"
        account1.port = 22
        account1.is_default = False
        account1.username = "admin"

        account2 = MagicMock()
        account2.alias = "dev-server"
        account2.host = "10.0.0.2"
        account2.port = 2222
        account2.is_default = True
        account2.username = "devuser"

        mock_ssh.list_accounts.return_value = [account1, account2]

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["account_count"] == 2
        assert len(data["mounts"]) == 2
        assert data["mounts"][0]["alias"] == "prod-server"
        assert data["mounts"][1]["alias"] == "dev-server"
        assert data["auth_username"] == "admin"

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_no_password_use_first_account(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试未设置密码时使用第一个账户的用户名"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 8081,
            "remote_drive_username": None,
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = None
        mock_remote_drive.is_running = True

        account = MagicMock()
        account.alias = "myserver"
        account.host = "192.168.1.50"
        account.port = 22
        account.is_default = False
        account.username = "fallback_user"
        mock_ssh.list_accounts.return_value = [account]

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["auth_username"] == "fallback_user"
        assert data["auth_password_set"] is False

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_no_password_use_default_account(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试未设置密码时使用默认账户的用户名"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 8081,
            "remote_drive_username": None,
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = None
        mock_remote_drive.is_running = True

        default_account = MagicMock()
        default_account.alias = "default-server"
        default_account.host = "192.168.1.10"
        default_account.port = 22
        default_account.is_default = True
        default_account.username = "default_user"

        other_account = MagicMock()
        other_account.alias = "other-server"
        other_account.host = "192.168.1.11"
        other_account.port = 22
        other_account.is_default = False
        other_account.username = "other_user"

        mock_ssh.list_accounts.return_value = [other_account, default_account]

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["auth_username"] == "default_user"

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_url_formats(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试URL格式正确性"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 8085,
            "remote_drive_username": "opsv",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = "pass"
        mock_remote_drive.is_running = True

        account = MagicMock()
        account.alias = "test"
        account.host = "1.2.3.4"
        account.port = 22
        account.is_default = True
        account.username = "opsv"
        mock_ssh.list_accounts.return_value = [account]

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["webdav_url"] == "http://localhost:8085/"
        assert data["windows_url"] == "\\\\localhost@8085\\DavWWWRoot\\"
        assert data["mounts"][0]["url"] == "http://localhost:8085/test/"
        assert data["mounts"][0]["windows_url"] == "\\\\localhost@8085\\DavWWWRoot\\test\\"

    @patch("app.api.routes.remote_drive.ssh_account_service")
    @patch("app.api.routes.remote_drive.remote_drive_service")
    @patch("app.api.routes.remote_drive.settings_service")
    def test_get_status_custom_port(self, mock_settings, mock_remote_drive, mock_ssh, client):
        """测试自定义端口配置"""
        mock_settings.get.side_effect = lambda key, default: {
            "remote_drive_enabled": True,
            "remote_drive_port": 9999,
            "remote_drive_username": "opsv",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = "pass"
        mock_remote_drive.is_running = True
        mock_ssh.list_accounts.return_value = []

        response = client.get("/api/remote-drive/status")

        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 9999
        assert "9999" in data["webdav_url"]
