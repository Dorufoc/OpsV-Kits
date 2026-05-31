import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.ssh_account import AccountGroup, SSHAccount, SSHAccountCreate, SSHAccountUpdate


def _make_account_data(**kwargs):
    defaults = {
        "alias": "test",
        "host": "192.168.1.1",
        "port": 22,
        "username": "root",
        "auth_type": "password",
        "password": "secret",
    }
    defaults.update(kwargs)
    return SSHAccountCreate(**defaults)


@pytest.fixture
def persist_dir(tmp_path):
    return tmp_path


@pytest.fixture
def service(persist_dir):
    with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
         patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
         patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
         patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
         patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x.replace("ENC(", "").replace(")", "") if x and x.startswith("ENC(") else x), \
         patch("app.services.ssh_account_service.SSHAccountService._add_audit_log"):
        from app.services.ssh_account_service import SSHAccountService
        svc = SSHAccountService()
        svc._accounts.clear()
        svc._groups.clear()
        svc._default_alias = None
        svc._audit_logs.clear()
        yield svc


class TestCreateAccount:
    def test_create_success(self, service):
        data = _make_account_data()
        account = service.create_account(data)
        assert account.alias == "test"
        assert account.host == "192.168.1.1"

    def test_create_duplicate_raises(self, service):
        data = _make_account_data()
        service.create_account(data)
        with pytest.raises(ValueError, match="已存在"):
            service.create_account(data)

    def test_create_default_account(self, service):
        data = _make_account_data(alias="default", is_default=True)
        account = service.create_account(data)
        assert account.is_default is True
        assert service._default_alias == "default"

    def test_create_with_group(self, service):
        data = _make_account_data(alias="grp_test", group="mygroup")
        account = service.create_account(data)
        assert account.group == "mygroup"
        assert "grp_test" in service._groups["mygroup"].accounts

    def test_create_max_accounts_limit(self, service):
        for i in range(100):
            data = _make_account_data(alias=f"acc{i}", host=f"10.0.0.{i}")
            service.create_account(data)
        with pytest.raises(ValueError, match="上限"):
            data = _make_account_data(alias="overflow")
            service.create_account(data)


class TestGetAccount:
    def test_get_existing(self, service):
        data = _make_account_data()
        service.create_account(data)
        account = service.get_account("test")
        assert account is not None
        assert account.alias == "test"

    def test_get_nonexistent(self, service):
        assert service.get_account("nonexistent") is None


class TestListAccounts:
    def test_list_all(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        accounts = service.list_accounts()
        assert len(accounts) == 2

    def test_list_by_group(self, service):
        service.create_account(_make_account_data(alias="a1", group="grp1"))
        service.create_account(_make_account_data(alias="a2", group="grp2"))
        accounts = service.list_accounts(group="grp1")
        assert len(accounts) == 1


class TestUpdateAccount:
    def test_update_success(self, service):
        service.create_account(_make_account_data())
        updated = service.update_account("test", SSHAccountUpdate(host="10.0.0.1"))
        assert updated.host == "10.0.0.1"

    def test_update_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.update_account("nope", SSHAccountUpdate(host="10.0.0.1"))

    def test_update_set_default(self, service):
        service.create_account(_make_account_data(alias="a1", is_default=True))
        service.create_account(_make_account_data(alias="a2"))
        service.update_account("a2", SSHAccountUpdate(is_default=True))
        assert service._default_alias == "a2"

    def test_update_unset_default(self, service):
        service.create_account(_make_account_data(alias="a1", is_default=True))
        service.update_account("a1", SSHAccountUpdate(is_default=False))
        assert service._default_alias is None

    def test_update_change_group(self, service):
        service.create_account(_make_account_data(alias="a1", group="g1"))
        service.update_account("a1", SSHAccountUpdate(group="g2"))
        assert service._accounts["a1"].group == "g2"


class TestDeleteAccount:
    def test_delete_success(self, service):
        service.create_account(_make_account_data())
        service.delete_account("test")
        assert service.get_account("test") is None

    def test_delete_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.delete_account("nope")

    def test_delete_default_clears(self, service):
        service.create_account(_make_account_data(alias="def", is_default=True))
        service.delete_account("def")
        assert service._default_alias is None


class TestClearAllAccounts:
    def test_clear_all(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        count = service.clear_all_accounts()
        assert count == 2
        assert service.list_accounts() == []


class TestSetDefault:
    def test_set_default(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        result = service.set_default("a2")
        assert result.is_default is True
        assert service._default_alias == "a2"

    def test_set_default_nonexistent(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.set_default("nope")


class TestGetDefault:
    def test_get_default(self, service):
        service.create_account(_make_account_data(alias="def", is_default=True))
        result = service.get_default()
        assert result is not None
        assert result.alias == "def"

    def test_get_default_none(self, service):
        assert service.get_default() is None


class TestGroupManagement:
    def test_create_group(self, service):
        group = service.create_group("mygroup", ["a1"])
        assert group.name == "mygroup"

    def test_create_duplicate_group(self, service):
        service.create_group("mygroup")
        with pytest.raises(ValueError, match="已存在"):
            service.create_group("mygroup")

    def test_list_groups(self, service):
        service.create_group("g1")
        service.create_group("g2")
        groups = service.list_groups()
        assert len(groups) == 2

    def test_delete_group(self, service):
        service.create_account(_make_account_data(alias="a1", group="g1"))
        service.delete_group("g1")
        assert service._accounts["a1"].group is None

    def test_delete_nonexistent_group(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.delete_group("nope")

    def test_update_group_rename(self, service):
        service.create_group("g1")
        group = service.update_group("g1", new_name="g2")
        assert group.name == "g2"

    def test_update_group_rename_conflict(self, service):
        service.create_group("g1")
        service.create_group("g2")
        with pytest.raises(ValueError, match="已存在"):
            service.update_group("g1", new_name="g2")

    def test_update_group_accounts(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_group("g1")
        group = service.update_group("g1", accounts=["a1"])
        assert "a1" in group.accounts


class TestAuditLogs:
    def test_get_audit_logs(self, service):
        service.create_account(_make_account_data())
        logs = service.get_audit_logs()
        assert isinstance(logs, list)

    def test_get_audit_logs_by_alias(self, service):
        service.create_account(_make_account_data())
        logs = service.get_audit_logs(account_alias="test")
        assert isinstance(logs, list)


class TestSanitizeLogDetail:
    def test_sanitize_password(self, service):
        result = service._sanitize_log_detail("password=secret123")
        assert "secret123" not in result
        assert "***" in result

    def test_sanitize_key_value(self, service):
        result = service._sanitize_log_detail("token=abc123")
        assert "abc123" not in result

    def test_sanitize_empty(self, service):
        assert service._sanitize_log_detail("") == ""

    def test_sanitize_no_match(self, service):
        result = service._sanitize_log_detail("normal log entry")
        assert result == "normal log entry"


class TestMaskMatch:
    def test_equals_format(self):
        from app.services.ssh_account_service import SSHAccountService

        result = SSHAccountService._mask_match("password=secret")
        assert result == "password=***"

    def test_colon_format(self):
        from app.services.ssh_account_service import SSHAccountService

        result = SSHAccountService._mask_match("password: secret")
        assert result == "password: ***"

    def test_space_format(self):
        from app.services.ssh_account_service import SSHAccountService

        result = SSHAccountService._mask_match("-p secret")
        assert "***" in result

    def test_no_separator(self):
        from app.services.ssh_account_service import SSHAccountService

        result = SSHAccountService._mask_match("justtext")
        assert result == "***"


class TestPersistence:
    def test_save_and_load(self, persist_dir):
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x.replace("ENC(", "").replace(")", "") if x and x.startswith("ENC(") else x), \
             patch("app.services.ssh_account_service.SSHAccountService._add_audit_log"):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            svc._accounts.clear()
            svc._groups.clear()
            svc._audit_logs.clear()
            svc.create_account(_make_account_data())

        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x.replace("ENC(", "").replace(")", "") if x and x.startswith("ENC(") else x), \
             patch("app.services.ssh_account_service.SSHAccountService._add_audit_log"):
            from app.services.ssh_account_service import SSHAccountService
            svc2 = SSHAccountService()
            assert "test" in svc2._accounts

    def test_load_corrupt_file(self, persist_dir):
        path = persist_dir / "accounts.json"
        path.write_text("not json", encoding="utf-8")

        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", path), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x), \
             patch("app.services.ssh_account_service.SSHAccountService._add_audit_log"):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._accounts) == 0


class TestPoolProperty:
    def test_pool_returns_instance(self, service):
        assert service.pool is not None
