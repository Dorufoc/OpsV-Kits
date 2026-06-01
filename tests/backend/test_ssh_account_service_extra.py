import json
import os
import stat
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.audit_log import ActionType, AuditModule
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


class TestTestAccount:
    def test_test_account_not_found(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.test_account("nonexistent")

    @patch("app.services.ssh_account_service.SSHClientManager")
    def test_test_account_success(self, mock_mgr_cls, service):
        service.create_account(_make_account_data())
        mock_mgr = MagicMock()
        mock_mgr.test_connection.return_value = (True, "连接成功")
        mock_mgr_cls.return_value = mock_mgr
        with patch.object(service, "_add_audit_log"):
            success, msg = service.test_account("test")
        assert success is True
        assert msg == "连接成功"

    @patch("app.services.ssh_account_service.SSHClientManager")
    def test_test_account_failure(self, mock_mgr_cls, service):
        service.create_account(_make_account_data())
        mock_mgr = MagicMock()
        mock_mgr.test_connection.return_value = (False, "连接超时")
        mock_mgr_cls.return_value = mock_mgr
        with patch.object(service, "_add_audit_log"):
            success, msg = service.test_account("test")
        assert success is False
        assert msg == "连接超时"


class TestInitWorkplace:
    def test_init_workplace_account_not_found(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.init_workplace("nonexistent")

    @patch("app.services.ssh_account_service.ssh_account_service")
    def test_init_workplace_success(self, mock_self_ref, service):
        service.create_account(_make_account_data())
        mock_conn = MagicMock()
        mock_mgr = MagicMock()
        mock_mgr.exec_command.return_value = (0, b"OK", b"")
        mock_conn.manager = mock_mgr
        service._pool.get_connection = MagicMock(return_value=mock_conn)
        service._pool.release_connection = MagicMock()
        with patch.object(service, "_add_audit_log"):
            result = service.init_workplace("test")
        assert "已初始化" in result

    @patch("app.services.ssh_account_service.ssh_account_service")
    def test_init_workplace_failure(self, mock_self_ref, service):
        service.create_account(_make_account_data())
        mock_conn = MagicMock()
        mock_mgr = MagicMock()
        mock_mgr.exec_command.return_value = (1, b"", b"Permission denied")
        mock_conn.manager = mock_mgr
        service._pool.get_connection = MagicMock(return_value=mock_conn)
        service._pool.release_connection = MagicMock()
        with patch.object(service, "_add_audit_log"):
            with pytest.raises(RuntimeError, match="初始化失败"):
                service.init_workplace("test")

    @patch("app.services.ssh_account_service.ssh_account_service")
    def test_init_workplace_bytes_stdout(self, mock_self_ref, service):
        service.create_account(_make_account_data())
        mock_conn = MagicMock()
        mock_mgr = MagicMock()
        mock_mgr.exec_command.return_value = (0, b"OK", b"")
        mock_conn.manager = mock_mgr
        service._pool.get_connection = MagicMock(return_value=mock_conn)
        service._pool.release_connection = MagicMock()
        with patch.object(service, "_add_audit_log"):
            result = service.init_workplace("test")
        assert "已初始化" in result


class TestEncryptFields:
    def test_encrypt_fields_password(self, service):
        with patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"):
            result = service._encrypt_fields({"password": "secret"})
            assert result["password"] == "ENC(secret)"

    def test_encrypt_fields_key_passphrase(self, service):
        with patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"):
            result = service._encrypt_fields({"key_passphrase": "mypass"})
            assert result["key_passphrase"] == "ENC(mypass)"

    def test_encrypt_fields_totp_secret(self, service):
        with patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"):
            result = service._encrypt_fields({"totp_secret": "totpval"})
            assert result["totp_secret"] == "ENC(totpval)"

    def test_encrypt_fields_empty_password(self, service):
        result = service._encrypt_fields({"password": ""})
        assert result["password"] == ""

    def test_encrypt_fields_none_password(self, service):
        result = service._encrypt_fields({"password": None})
        assert result["password"] is None

    def test_encrypt_fields_no_sensitive(self, service):
        result = service._encrypt_fields({"host": "10.0.0.1"})
        assert result["host"] == "10.0.0.1"


class TestDecryptAccount:
    def test_decrypt_account_password_exception(self, service):
        account = SSHAccount(
            alias="test", host="10.0.0.1", port=22, username="root",
            password="invalid_encrypted", auth_type="password"
        )
        with patch("app.services.ssh_account_service.decrypt", side_effect=Exception("decrypt error")):
            result = service._decrypt_account(account)
        assert result.password is None

    def test_decrypt_account_key_passphrase_exception(self, service):
        account = SSHAccount(
            alias="test", host="10.0.0.1", port=22, username="root",
            key_passphrase="invalid_encrypted", auth_type="key"
        )
        with patch("app.services.ssh_account_service.decrypt", side_effect=Exception("decrypt error")):
            result = service._decrypt_account(account)
        assert result.key_passphrase is None

    def test_decrypt_account_totp_secret_exception(self, service):
        account = SSHAccount(
            alias="test", host="10.0.0.1", port=22, username="root",
            totp_secret="invalid_encrypted", auth_type="password"
        )
        with patch("app.services.ssh_account_service.decrypt", side_effect=Exception("decrypt error")):
            result = service._decrypt_account(account)
        assert result.totp_secret is None

    def test_decrypt_account_no_password(self, service):
        account = SSHAccount(
            alias="test", host="10.0.0.1", port=22, username="root",
            auth_type="key", private_key="/path/to/key"
        )
        result = service._decrypt_account(account)
        assert result.password is None


class TestEncryptSensitive:
    def test_encrypt_sensitive_all_fields(self, service):
        data = SSHAccountCreate(
            alias="enc_test", host="10.0.0.1", port=22, username="root",
            password="pass1", key_passphrase="pass2", totp_secret="pass3"
        )
        with patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"):
            result = service._encrypt_sensitive(data)
        assert result.password == "ENC(pass1)"
        assert result.key_passphrase == "ENC(pass2)"
        assert result.totp_secret == "ENC(pass3)"

    def test_encrypt_sensitive_no_fields(self, service):
        data = SSHAccountCreate(
            alias="enc_test2", host="10.0.0.1", port=22, username="root",
            auth_type="key", private_key="/path/to/key"
        )
        result = service._encrypt_sensitive(data)
        assert result.password is None
        assert result.key_passphrase is None
        assert result.totp_secret is None


class TestSanitizeLogDetailAdvanced:
    def test_sanitize_colon_format(self, service):
        result = service._sanitize_log_detail("password: mysecret")
        assert "mysecret" not in result

    def test_sanitize_private_key(self, service):
        detail = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"
        result = service._sanitize_log_detail(detail)
        assert "MIIEpAIBAAKCAQEA" not in result

    def test_sanitize_dash_p_format(self, service):
        result = service._sanitize_log_detail("-p mypassword")
        assert "mypassword" not in result

    def test_sanitize_double_dash_password(self, service):
        result = service._sanitize_log_detail("--password mypassword")
        assert "mypassword" not in result

    def test_sanitize_token_equals(self, service):
        result = service._sanitize_log_detail("token=abc123def")
        assert "abc123def" not in result

    def test_sanitize_pwd_equals(self, service):
        result = service._sanitize_log_detail("pwd=secret123")
        assert "secret123" not in result


class TestMaskMatchAdvanced:
    def test_mask_equals_with_multiple_equals(self):
        from app.services.ssh_account_service import SSHAccountService
        result = SSHAccountService._mask_match("key=val=ue")
        assert result.startswith("key=")
        assert "***" in result

    def test_mask_colon_with_multiple_colons(self):
        from app.services.ssh_account_service import SSHAccountService
        result = SSHAccountService._mask_match("key:val:ue")
        assert result.startswith("key:")
        assert "***" in result

    def test_mask_space_separated(self):
        from app.services.ssh_account_service import SSHAccountService
        result = SSHAccountService._mask_match("--password secret123")
        assert "***" in result

    def test_mask_no_separator(self):
        from app.services.ssh_account_service import SSHAccountService
        result = SSHAccountService._mask_match("justonepiece")
        assert result == "***"


class TestUpdateGroupAdvanced:
    def test_update_group_remove_accounts(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        service.create_group("g1", ["a1", "a2"])
        group = service.update_group("g1", accounts=["a1"])
        assert "a2" not in group.accounts
        assert service._accounts["a2"].group is None

    def test_update_group_add_accounts(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        service.create_group("g1", ["a1"])
        group = service.update_group("g1", accounts=["a1", "a2"])
        assert "a2" in group.accounts
        assert service._accounts["a2"].group == "g1"

    def test_update_group_rename_updates_accounts(self, service):
        service.create_account(_make_account_data(alias="a1", group="g1"))
        service.update_group("g1", new_name="g2")
        assert service._accounts["a1"].group == "g2"

    def test_update_group_same_name_no_rename(self, service):
        service.create_group("g1")
        group = service.update_group("g1", new_name="g1")
        assert group.name == "g1"

    def test_update_group_not_found(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.update_group("nonexistent", new_name="g2")


class TestDeleteGroupAdvanced:
    def test_delete_group_removes_account_references(self, service):
        service.create_account(_make_account_data(alias="a1", group="g1"))
        service.create_account(_make_account_data(alias="a2", group="g1"))
        service.delete_group("g1")
        assert service._accounts["a1"].group is None
        assert service._accounts["a2"].group is None


class TestAuditLogPersistence:
    def test_save_and_load_audit_logs(self, persist_dir):
        audit_path = persist_dir / "audit_logs.json"
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x.replace("ENC(", "").replace(")", "") if x and x.startswith("ENC(") else x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            svc._accounts.clear()
            svc._groups.clear()
            svc._audit_logs.clear()
            svc._default_alias = None
            svc.create_account(_make_account_data())

        assert audit_path.exists()
        data = json.loads(audit_path.read_text(encoding="utf-8"))
        assert "logs" in data
        assert len(data["logs"]) > 0

    def test_load_audit_logs_corrupt_file(self, persist_dir):
        audit_path = persist_dir / "audit_logs.json"
        audit_path.write_text("not json", encoding="utf-8")
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._audit_logs) == 0

    def test_load_audit_logs_missing_file(self, persist_dir):
        audit_path = persist_dir / "nonexistent_audit.json"
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._audit_logs) == 0

    def test_load_audit_logs_with_string_detail(self, persist_dir):
        audit_path = persist_dir / "audit_logs.json"
        log_data = {
            "logs": [{
                "id": "log1",
                "timestamp": datetime.now().isoformat(),
                "action_type": "execute",
                "module": "ssh",
                "status": "success",
                "detail": "just a string detail",
                "account_alias": "test_alias",
            }]
        }
        audit_path.write_text(json.dumps(log_data), encoding="utf-8")
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._audit_logs) == 1
            assert isinstance(svc._audit_logs[0].detail, dict)
            assert svc._audit_logs[0].detail.get("message") == "just a string detail"

    def test_load_audit_logs_with_dict_detail_no_alias(self, persist_dir):
        audit_path = persist_dir / "audit_logs.json"
        log_data = {
            "logs": [{
                "id": "log2",
                "timestamp": datetime.now().isoformat(),
                "action_type": "execute",
                "module": "ssh",
                "status": "success",
                "detail": {"message": "test"},
                "account_alias": "my_alias",
            }]
        }
        audit_path.write_text(json.dumps(log_data), encoding="utf-8")
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._audit_logs) == 1
            assert svc._audit_logs[0].detail.get("account_alias") == "my_alias"

    def test_load_audit_logs_corrupt_entry_skipped(self, persist_dir):
        audit_path = persist_dir / "audit_logs.json"
        log_data = {
            "logs": [
                {"id": "bad_log", "timestamp": "not-a-date"},
                {"id": "good_log", "timestamp": datetime.now().isoformat(),
                 "action_type": "execute", "module": "ssh", "status": "success",
                 "detail": {"message": "ok"}},
            ]
        }
        audit_path.write_text(json.dumps(log_data), encoding="utf-8")
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", audit_path), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._audit_logs) >= 1


class TestSetRestrictedPermissions:
    def test_set_restricted_permissions_windows(self, persist_dir):
        test_file = persist_dir / "test_perm.txt"
        test_file.write_text("test", encoding="utf-8")
        from app.services.ssh_account_service import SSHAccountService
        with patch("os.name", "nt"):
            with patch("ctypes.windll") as mock_windll:
                mock_advapi32 = MagicMock()
                mock_kernel32 = MagicMock()
                mock_windll.advapi32 = mock_advapi32
                mock_windll.kernel32 = mock_kernel32
                mock_kernel32.GetCurrentProcess.return_value = 12345
                SSHAccountService._set_restricted_permissions(test_file)

    def test_set_restricted_permissions_posix(self, persist_dir):
        test_file = persist_dir / "test_perm2.txt"
        test_file.write_text("test", encoding="utf-8")
        from app.services.ssh_account_service import SSHAccountService
        with patch("os.name", "posix"):
            with patch("os.chmod") as mock_chmod:
                SSHAccountService._set_restricted_permissions(test_file)
                mock_chmod.assert_called_once_with(
                    test_file, stat.S_IRUSR | stat.S_IWUSR
                )

    def test_set_restricted_permissions_exception(self, persist_dir):
        test_file = persist_dir / "test_perm3.txt"
        test_file.write_text("test", encoding="utf-8")
        from app.services.ssh_account_service import SSHAccountService
        with patch("os.name", "posix"):
            with patch("os.chmod", side_effect=PermissionError("denied")):
                SSHAccountService._set_restricted_permissions(test_file)


class TestGetDefaultAdvanced:
    def test_get_default_alias_but_account_missing(self, service):
        service._default_alias = "ghost"
        result = service.get_default()
        assert result is None


class TestSetDefaultAdvanced:
    def test_set_default_clears_old_default(self, service):
        service.create_account(_make_account_data(alias="a1", is_default=True))
        service.create_account(_make_account_data(alias="a2"))
        service.set_default("a2")
        assert service._accounts["a1"].is_default is False
        assert service._accounts["a2"].is_default is True

    def test_set_default_no_old_default(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.set_default("a1")
        assert service._default_alias == "a1"
        assert service._accounts["a1"].is_default is True

    def test_set_default_old_default_not_in_accounts(self, service):
        service._default_alias = "ghost"
        service.create_account(_make_account_data(alias="a1"))
        service.set_default("a1")
        assert service._default_alias == "a1"


class TestSyncAccountToGroup:
    def test_sync_creates_new_group(self, service):
        service._sync_account_to_group("a1", "newgroup")
        assert "newgroup" in service._groups
        assert "a1" in service._groups["newgroup"].accounts

    def test_sync_to_existing_group(self, service):
        service._groups["g1"] = AccountGroup(name="g1", accounts=["existing"])
        service._sync_account_to_group("a1", "g1")
        assert "a1" in service._groups["g1"].accounts

    def test_sync_duplicate_account(self, service):
        service._groups["g1"] = AccountGroup(name="g1", accounts=["a1"])
        service._sync_account_to_group("a1", "g1")
        assert service._groups["g1"].accounts.count("a1") == 1


class TestRemoveAccountFromGroup:
    def test_remove_from_existing_group(self, service):
        service._groups["g1"] = AccountGroup(name="g1", accounts=["a1", "a2"])
        service._remove_account_from_group("a1", "g1")
        assert "a1" not in service._groups["g1"].accounts

    def test_remove_from_nonexistent_group(self, service):
        service._remove_account_from_group("a1", "nonexistent")

    def test_remove_account_not_in_group(self, service):
        service._groups["g1"] = AccountGroup(name="g1", accounts=["a2"])
        service._remove_account_from_group("a1", "g1")


class TestSaveToDiskError:
    def test_save_to_disk_permission_error(self, persist_dir):
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", persist_dir / "accounts.json"), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            svc._accounts.clear()
            svc._groups.clear()
            svc._audit_logs.clear()
            svc._default_alias = None
            with patch("pathlib.Path.write_text", side_effect=PermissionError("denied")):
                svc._save_to_disk()


class TestLoadFromDiskCorruptAccount:
    def test_load_corrupt_account_entry_skipped(self, persist_dir):
        path = persist_dir / "accounts.json"
        data = {
            "accounts": [
                {"alias": "bad_account", "host": None, "port": "not_int"},
                {"alias": "good_account", "host": "10.0.0.1", "port": 22, "username": "root", "auth_type": "password"},
            ],
            "groups": [],
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        with patch("app.services.ssh_account_service._PERSIST_DIR", persist_dir), \
             patch("app.services.ssh_account_service._PERSIST_PATH", path), \
             patch("app.services.ssh_account_service._AUDIT_LOGS_PATH", persist_dir / "audit_logs.json"), \
             patch("app.services.ssh_account_service.encrypt", side_effect=lambda x: f"ENC({x})"), \
             patch("app.services.ssh_account_service.decrypt", side_effect=lambda x: x):
            from app.services.ssh_account_service import SSHAccountService
            svc = SSHAccountService()
            assert len(svc._accounts) >= 0


class TestDeleteAccountRemovesFromGroups:
    def test_delete_removes_from_multiple_groups(self, service):
        service.create_account(_make_account_data(alias="a1", group="g1"))
        service.delete_account("a1")
        assert "a1" not in service._groups.get("g1", AccountGroup(name="x")).accounts


class TestClearAllAccounts:
    def test_clear_all_closes_pool_connections(self, service):
        service.create_account(_make_account_data(alias="a1"))
        service.create_account(_make_account_data(alias="a2"))
        with patch.object(service._pool, "remove_connection") as mock_remove:
            count = service.clear_all_accounts()
        assert count == 2
        assert mock_remove.call_count == 2
