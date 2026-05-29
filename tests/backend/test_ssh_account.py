"""SSH账户管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from app.main import app
from app.models.ssh_account import (
    SSHAccount, SSHAccountCreate, SSHAccountUpdate,
    AccountGroup, AccountGroupCreate, AccountGroupUpdate,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_account_data():
    return {
        "alias": "test-server",
        "host": "192.168.1.100",
        "port": 22,
        "username": "testuser",
        "auth_type": "password",
        "password": "testpass123",
        "is_default": False,
        "group": None,
        "workplace_path": "~/projects",
    }


@pytest.fixture
def sample_account_update():
    return {
        "host": "192.168.1.200",
        "port": 2222,
        "username": "newuser",
    }


class TestSSHAccountCRUD:
    """SSH账户CRUD操作测试"""

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_list_accounts_empty(self, mock_service, client):
        mock_service.list_accounts.return_value = []
        response = client.get("/api/accounts")
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_list_accounts_with_data(self, mock_service, client):
        mock_accounts = [
            SSHAccount(alias="server1", host="192.168.1.1", username="user1"),
            SSHAccount(alias="server2", host="192.168.1.2", username="user2"),
        ]
        mock_service.list_accounts.return_value = mock_accounts
        response = client.get("/api/accounts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["alias"] == "server1"

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_list_accounts_with_group_filter(self, mock_service, client):
        mock_service.list_accounts.return_value = []
        response = client.get("/api/accounts?group=production")
        assert response.status_code == 200
        mock_service.list_accounts.assert_called_with(group="production")

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_create_account_success(self, mock_service, client, sample_account_data):
        mock_service.create_account.return_value = SSHAccount(**sample_account_data)
        response = client.post("/api/accounts", json=sample_account_data)
        assert response.status_code == 201
        data = response.json()
        assert data["alias"] == "test-server"
        assert data["host"] == "192.168.1.100"

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_create_account_duplicate(self, mock_service, client, sample_account_data):
        mock_service.create_account.side_effect = ValueError("账户已存在")
        response = client.post("/api/accounts", json=sample_account_data)
        assert response.status_code == 409

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_get_account_success(self, mock_service, client):
        mock_service.get_account.return_value = SSHAccount(
            alias="test-server", host="192.168.1.100", username="testuser"
        )
        response = client.get("/api/accounts/test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["alias"] == "test-server"

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_get_account_not_found(self, mock_service, client):
        mock_service.get_account.return_value = None
        response = client.get("/api/accounts/nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_update_account_success(self, mock_service, client):
        mock_service.update_account.return_value = SSHAccount(
            alias="test-server", host="192.168.1.200", username="newuser"
        )
        response = client.put(
            "/api/accounts/test-server",
            json={"host": "192.168.1.200", "username": "newuser"},
        )
        assert response.status_code == 200

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_update_account_not_found(self, mock_service, client):
        mock_service.update_account.side_effect = ValueError("账户不存在")
        response = client.put(
            "/api/accounts/nonexistent",
            json={"host": "192.168.1.200"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_delete_account_success(self, mock_service, client):
        mock_service.delete_account.return_value = None
        response = client.delete("/api/accounts/test-server")
        assert response.status_code == 204

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_delete_account_not_found(self, mock_service, client):
        mock_service.delete_account.side_effect = ValueError("账户不存在")
        response = client.delete("/api/accounts/nonexistent")
        assert response.status_code == 404


class TestSSHAccountOperations:
    """SSH账户操作测试"""

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_accounts_exist_with_accounts(self, mock_service, client):
        mock_service.list_accounts.return_value = [
            SSHAccount(alias="server1", host="192.168.1.1", username="user1")
        ]
        response = client.get("/api/accounts/exists")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["count"] == 1

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_accounts_exist_no_accounts(self, mock_service, client):
        mock_service.list_accounts.return_value = []
        response = client.get("/api/accounts/exists")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["count"] == 0

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_get_default_account(self, mock_service, client):
        mock_service.get_default.return_value = SSHAccount(
            alias="default-server", host="192.168.1.1", username="admin", is_default=True
        )
        response = client.get("/api/accounts/default/info")
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_set_default_account(self, mock_service, client):
        mock_service.set_default.return_value = SSHAccount(
            alias="test-server", host="192.168.1.1", username="user", is_default=True
        )
        response = client.post("/api/accounts/test-server/default")
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_set_default_account_not_found(self, mock_service, client):
        mock_service.set_default.side_effect = ValueError("账户不存在")
        response = client.post("/api/accounts/nonexistent/default")
        assert response.status_code == 404

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_test_account_success(self, mock_service, client):
        mock_service.test_account.return_value = (True, "连接成功")
        response = client.post("/api/accounts/test-server/test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["alias"] == "test-server"

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_test_account_failure(self, mock_service, client):
        mock_service.test_account.return_value = (False, "连接超时")
        response = client.post("/api/accounts/test-server/test")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_test_account_not_found(self, mock_service, client):
        mock_service.test_account.side_effect = ValueError("账户不存在")
        response = client.post("/api/accounts/nonexistent/test")
        assert response.status_code == 404

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_clear_all_accounts(self, mock_service, client):
        mock_service.clear_all_accounts.return_value = None
        response = client.delete("/api/accounts/clear-all?confirm=yes")
        assert response.status_code == 204

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_clear_all_accounts_confirm_no(self, mock_service, client):
        mock_service.clear_all_accounts.return_value = None
        response = client.delete("/api/accounts/clear-all?confirm=no")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_clear_all_accounts_missing_confirm(self, mock_service, client):
        response = client.delete("/api/accounts/clear-all")
        assert response.status_code == 422

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_get_audit_logs(self, mock_service, client):
        mock_service.get_audit_logs.return_value = []
        response = client.get("/api/accounts/audit/logs?limit=50")
        assert response.status_code == 200
        mock_service.get_audit_logs.assert_called_with(account_alias=None, limit=50)


class TestSSHAccountGroups:
    """SSH账户分组测试"""

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_create_group_success(self, mock_service, client):
        mock_service.create_group.return_value = AccountGroup(
            name="production", accounts=["server1", "server2"]
        )
        response = client.post(
            "/api/accounts/groups",
            json={"name": "production", "accounts": ["server1", "server2"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "production"
        assert len(data["accounts"]) == 2

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_create_group_duplicate(self, mock_service, client):
        mock_service.create_group.side_effect = ValueError("分组已存在")
        response = client.post(
            "/api/accounts/groups",
            json={"name": "production", "accounts": []},
        )
        assert response.status_code == 409

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_list_groups(self, mock_service, client):
        mock_service.list_groups.return_value = [
            AccountGroup(name="production", accounts=["server1"]),
            AccountGroup(name="development", accounts=["server2", "server3"]),
        ]
        response = client.get("/api/accounts/groups/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_update_group_success(self, mock_service, client):
        mock_service.update_group.return_value = AccountGroup(
            name="prod-new", accounts=["server1", "server2"]
        )
        response = client.put(
            "/api/accounts/groups/production",
            json={"new_name": "prod-new", "accounts": ["server1", "server2"]},
        )
        assert response.status_code == 200

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_update_group_not_found(self, mock_service, client):
        mock_service.update_group.side_effect = ValueError("分组不存在")
        response = client.put(
            "/api/accounts/groups/nonexistent",
            json={"new_name": "new-name"},
        )
        assert response.status_code == 400

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_delete_group_success(self, mock_service, client):
        mock_service.delete_group.return_value = None
        response = client.delete("/api/accounts/groups/production")
        assert response.status_code == 204

    @patch("app.api.routes.ssh_account.ssh_account_service")
    def test_delete_group_not_found(self, mock_service, client):
        mock_service.delete_group.side_effect = ValueError("分组不存在")
        response = client.delete("/api/accounts/groups/nonexistent")
        assert response.status_code == 404


class TestSSHAccountConnection:
    """SSH连接测试"""

    @patch("app.api.routes.ssh_account.SSHClientManager")
    def test_test_connection_direct_success(self, mock_manager, client):
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = (True, "连接成功")
        mock_manager.return_value = mock_instance

        response = client.post(
            "/api/accounts/test-connection",
            json={
                "alias": "temp-test",
                "host": "192.168.1.100",
                "port": 22,
                "username": "testuser",
                "auth_type": "password",
                "password": "testpass",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.ssh_account.SSHClientManager")
    def test_test_connection_direct_failure(self, mock_manager, client):
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = (False, "连接超时")
        mock_manager.return_value = mock_instance

        response = client.post(
            "/api/accounts/test-connection",
            json={
                "alias": "temp-test",
                "host": "192.168.1.100",
                "port": 22,
                "username": "testuser",
                "auth_type": "password",
                "password": "wrongpass",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestSSHAccountValidation:
    """SSH账户数据验证测试"""

    def test_ssh_account_create_validation(self):
        # Pydantic 要求所有必填字段都存在，缺少字段时抛出 ValidationError
        with pytest.raises(ValidationError):
            SSHAccountCreate(alias="test")  # 缺少 host, username 等必填字段

    def test_ssh_account_create_required_fields(self):
        # Pydantic 对缺失字段抛出 ValidationError
        with pytest.raises(ValidationError):
            SSHAccountCreate(host="192.168.1.1")

    def test_ssh_account_create_valid_data(self):
        account = SSHAccountCreate(
            alias="test-server",
            host="192.168.1.100",
            port=22,
            username="testuser",
            auth_type="password",
            password="testpass",
        )
        assert account.alias == "test-server"
        assert account.port == 22
        assert account.auth_type == "password"

    def test_ssh_account_update_partial(self):
        update = SSHAccountUpdate(host="192.168.1.200")
        assert update.host == "192.168.1.200"
        assert update.port is None
        assert update.username is None

    def test_account_group_create(self):
        # 使用正确的模型类 AccountGroupCreate
        group = AccountGroupCreate(name="production", accounts=["server1", "server2"])
        assert group.name == "production"
        assert len(group.accounts) == 2

    def test_account_group_update(self):
        # 使用正确的模型类 AccountGroupUpdate
        update = AccountGroupUpdate(new_name="prod-v2")
        assert update.new_name == "prod-v2"
        assert update.accounts is None
