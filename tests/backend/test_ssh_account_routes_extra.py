from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.ssh_account import SSHAccount


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_svc():
    with patch("app.api.routes.ssh_account.ssh_account_service") as m:
        yield m


class TestInitWorkplace:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_init_workplace_success(self, mock_service, client):
        mock_service.init_workplace.return_value = "工作区初始化成功"
        resp = client.post("/api/accounts/workplace/init?alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "工作区初始化成功"

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_init_workplace_not_found(self, mock_service, client):
        mock_service.init_workplace.side_effect = ValueError("账户不存在")
        resp = client.post("/api/accounts/workplace/init?alias=missing")
        assert resp.status_code == 404

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_init_workplace_server_error(self, mock_service, client):
        mock_service.init_workplace.side_effect = Exception("SSH 连接失败")
        resp = client.post("/api/accounts/workplace/init?alias=srv1")
        assert resp.status_code == 500


class TestTestConnectionDirect:
    @patch("app.api.routes.ssh_account.SSHClientManager")
    def test_test_connection_exception(self, mock_manager, client):
        mock_instance = MagicMock()
        mock_instance.test_connection.side_effect = Exception("connection error")
        mock_manager.return_value = mock_instance
        resp = client.post("/api/accounts/test-connection", json={
            "alias": "temp", "host": "192.168.1.1", "port": 22,
            "username": "root", "auth_type": "password", "password": "pass",
        })
        assert resp.status_code == 500


class TestClearAllAccountsError:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_clear_all_accounts_error(self, mock_service, client):
        mock_service.clear_all_accounts.side_effect = Exception("cleanup failed")
        resp = client.delete("/api/accounts/clear-all?confirm=yes")
        assert resp.status_code == 500


class TestCreateAccountWithPerformance:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_create_account_success_with_perf(self, mock_service, client):
        mock_perf = MagicMock()
        mock_perf.on_account_created = AsyncMock()
        with patch("app.services.performance_collector.performance_collector", mock_perf):
            mock_service.create_account.return_value = SSHAccount(
                alias="srv1", host="192.168.1.1", username="root"
            )
            resp = client.post("/api/accounts", json={
                "alias": "srv1", "host": "192.168.1.1", "port": 22,
                "username": "root", "auth_type": "password", "password": "pass",
            })
            assert resp.status_code == 201


class TestDeleteAccountWithPerformance:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_delete_account_success(self, mock_service, client):
        mock_perf = MagicMock()
        mock_perf.on_account_deleted = AsyncMock()
        with patch("app.services.performance_collector.performance_collector", mock_perf):
            mock_service.delete_account.return_value = None
            resp = client.delete("/api/accounts/srv1")
            assert resp.status_code == 204


class TestStorageInfo:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_storage_info(self, mock_service, client):
        mock_service.list_accounts.return_value = [SSHAccount(alias="srv1", host="192.168.1.1", username="root")]
        resp = client.get("/api/accounts/storage/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "home_directory" in data
        assert "accounts_count" in data
        assert data["accounts_count"] == 1


class TestGetDefaultAccountNone:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_get_default_none(self, mock_service, client):
        mock_service.get_default.return_value = None
        resp = client.get("/api/accounts/default/info")
        assert resp.status_code == 200
        assert resp.json() is None


class TestListGroupsShort:
    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_list_groups_short(self, mock_service, client):
        from app.models.ssh_account import AccountGroup
        mock_service.list_groups.return_value = [AccountGroup(name="prod", accounts=["srv1"])]
        resp = client.get("/api/accounts/groups")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
