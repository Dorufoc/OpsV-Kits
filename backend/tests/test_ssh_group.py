import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.ssh_account_service import SSHAccountService
from app.models.ssh_account import SSHAccountCreate, SSHAccountUpdate, AccountGroup


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fresh_service(tmp_path):
    with patch("app.services.ssh_account_service._PERSIST_DIR", tmp_path):
        with patch("app.services.ssh_account_service._PERSIST_PATH", tmp_path / "accounts.json"):
            service = SSHAccountService()
            with patch("app.api.routes.ssh_account.ssh_account_service", service):
                yield service


@pytest.fixture
def client_with_fresh_service(client, fresh_service):
    return client


class TestGroupService:
    def test_create_group(self, fresh_service):
        group = fresh_service.create_group("生产环境")
        assert group.name == "生产环境"
        assert group.accounts == []

    def test_create_group_duplicate(self, fresh_service):
        fresh_service.create_group("生产环境")
        with pytest.raises(ValueError, match="已存在"):
            fresh_service.create_group("生产环境")

    def test_list_groups(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.create_group("测试环境")
        groups = fresh_service.list_groups()
        assert len(groups) == 2
        names = {g.name for g in groups}
        assert names == {"生产环境", "测试环境"}

    def test_delete_group(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.delete_group("生产环境")
        assert len(fresh_service.list_groups()) == 0

    def test_delete_group_clears_account_group(self, fresh_service):
        fresh_service.create_group("生产环境")
        account = fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        assert account.group == "生产环境"
        fresh_service.delete_group("生产环境")
        updated = fresh_service.get_account("srv1")
        assert updated.group is None

    def test_update_group_rename(self, fresh_service):
        fresh_service.create_group("生产环境")
        group = fresh_service.update_group("生产环境", new_name="生产集群")
        assert group.name == "生产集群"
        groups = fresh_service.list_groups()
        assert len(groups) == 1
        assert groups[0].name == "生产集群"

    def test_update_group_rename_syncs_accounts(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.update_group("生产环境", new_name="生产集群")
        account = fresh_service.get_account("srv1")
        assert account.group == "生产集群"

    def test_update_group_accounts(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.create_account(SSHAccountCreate(
            alias="srv2", host="192.168.1.2", username="root"
        ))
        group = fresh_service.update_group("生产环境", accounts=["srv1", "srv2"])
        assert "srv2" in group.accounts
        account2 = fresh_service.get_account("srv2")
        assert account2.group == "生产环境"

    def test_update_group_remove_account_from_group(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.update_group("生产环境", accounts=[])
        account = fresh_service.get_account("srv1")
        assert account.group is None


class TestAccountGroupSync:
    def test_create_account_auto_creates_group(self, fresh_service):
        account = fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        assert account.group == "生产环境"
        groups = fresh_service.list_groups()
        assert len(groups) == 1
        assert groups[0].name == "生产环境"
        assert "srv1" in groups[0].accounts

    def test_create_account_adds_to_existing_group(self, fresh_service):
        fresh_service.create_group("生产环境")
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        groups = fresh_service.list_groups()
        assert "srv1" in groups[0].accounts

    def test_update_account_group_sync(self, fresh_service):
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.update_account("srv1", SSHAccountUpdate(group="测试环境"))
        groups = fresh_service.list_groups()
        group_names = {g.name for g in groups}
        assert "测试环境" in group_names
        assert "生产环境" in group_names
        prod_group = next(g for g in groups if g.name == "生产环境")
        test_group = next(g for g in groups if g.name == "测试环境")
        assert "srv1" not in prod_group.accounts
        assert "srv1" in test_group.accounts

    def test_update_account_remove_group(self, fresh_service):
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.update_account("srv1", SSHAccountUpdate(group=None))
        account = fresh_service.get_account("srv1")
        assert account.group is None
        groups = fresh_service.list_groups()
        prod_group = next(g for g in groups if g.name == "生产环境")
        assert "srv1" not in prod_group.accounts

    def test_delete_account_removes_from_group(self, fresh_service):
        fresh_service.create_account(SSHAccountCreate(
            alias="srv1", host="192.168.1.1", username="root", group="生产环境"
        ))
        fresh_service.delete_account("srv1")
        groups = fresh_service.list_groups()
        if groups:
            assert "srv1" not in groups[0].accounts


class TestGroupAPI:
    def test_create_group_api(self, client_with_fresh_service):
        resp = client_with_fresh_service.post("/api/accounts/groups", json={"name": "生产环境"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "生产环境"

    def test_list_groups_api(self, client_with_fresh_service):
        client_with_fresh_service.post("/api/accounts/groups", json={"name": "生产环境"})
        resp = client_with_fresh_service.get("/api/accounts/groups")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_group_api(self, client_with_fresh_service):
        client_with_fresh_service.post("/api/accounts/groups", json={"name": "生产环境"})
        resp = client_with_fresh_service.put(
            "/api/accounts/groups/生产环境",
            json={"new_name": "生产集群"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "生产集群"

    def test_delete_group_api(self, client_with_fresh_service):
        client_with_fresh_service.post("/api/accounts/groups", json={"name": "生产环境"})
        resp = client_with_fresh_service.delete("/api/accounts/groups/生产环境")
        assert resp.status_code == 204

    def test_create_account_auto_group_api(self, client_with_fresh_service):
        resp = client_with_fresh_service.post("/api/accounts", json={
            "alias": "srv1", "host": "192.168.1.1", "username": "root", "group": "生产环境"
        })
        assert resp.status_code == 201
        assert resp.json()["group"] == "生产环境"
        groups_resp = client_with_fresh_service.get("/api/accounts/groups")
        groups = groups_resp.json()
        assert any(g["name"] == "生产环境" for g in groups)

    def test_filter_accounts_by_group_api(self, client_with_fresh_service):
        client_with_fresh_service.post("/api/accounts", json={
            "alias": "srv1", "host": "192.168.1.1", "username": "root", "group": "生产环境"
        })
        client_with_fresh_service.post("/api/accounts", json={
            "alias": "srv2", "host": "192.168.1.2", "username": "root", "group": "测试环境"
        })
        resp = client_with_fresh_service.get("/api/accounts", params={"group": "生产环境"})
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) == 1
        assert accounts[0]["alias"] == "srv1"
