import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.fixture
def settings_dir(tmp_path):
    return tmp_path


@pytest.fixture
def settings_service(settings_dir):
    with patch("app.services.settings_service._PERSIST_DIR", settings_dir), \
         patch("app.services.settings_service._SETTINGS_PATH", settings_dir / "settings.json"):
        from app.services.settings_service import SettingsService
        svc = SettingsService()
        svc._settings = {
            "session_ttl_hours": 72,
            "remote_drive_enabled": False,
            "remote_drive_port": 8081,
            "remote_drive_username": "opsv",
            "remote_drive_password": "",
        }
        yield svc


class TestSettingsGet:
    def test_get_existing_key(self, settings_service):
        assert settings_service.get("session_ttl_hours") == 72

    def test_get_missing_key_with_default(self, settings_service):
        assert settings_service.get("nonexistent", "default_val") == "default_val"

    def test_get_missing_key_no_default(self, settings_service):
        assert settings_service.get("nonexistent") is None


class TestSettingsSet:
    def test_set_new_key(self, settings_service):
        settings_service.set("new_key", "new_value")
        assert settings_service.get("new_key") == "new_value"

    def test_set_overwrite_key(self, settings_service):
        settings_service.set("session_ttl_hours", 48)
        assert settings_service.get("session_ttl_hours") == 48

    def test_set_saves_to_disk(self, settings_service, settings_dir):
        settings_service.set("test_key", "test_val")
        path = settings_dir / "settings.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["test_key"] == "test_val"


class TestSettingsGetAll:
    def test_get_all_returns_copy(self, settings_service):
        result = settings_service.get_all()
        assert "session_ttl_hours" in result
        assert "remote_drive_password" not in result
        assert "remote_drive_password_set" in result

    def test_get_all_password_set_flag(self, settings_service):
        settings_service._settings["remote_drive_password"] = "encrypted_pwd"
        result = settings_service.get_all()
        assert result["remote_drive_password_set"] is True

    def test_get_all_password_not_set_flag(self, settings_service):
        result = settings_service.get_all()
        assert result["remote_drive_password_set"] is False


class TestSettingsUpdate:
    def test_update_basic(self, settings_service):
        result = settings_service.update({"session_ttl_hours": 24})
        assert result["session_ttl_hours"] == 24

    def test_update_with_password_encryption(self, settings_service):
        with patch("app.services.settings_service.encrypt", return_value="ENC_PWD"), \
             patch("app.services.settings_service.decrypt", return_value="DEC_PWD"):
            result = settings_service.update({"remote_drive_password": "plain_pwd"})
            assert settings_service._settings["remote_drive_password"] == "ENC_PWD"

    def test_update_empty_password_not_encrypted(self, settings_service):
        with patch("app.services.settings_service.encrypt") as mock_enc:
            settings_service.update({"remote_drive_password": ""})
            mock_enc.assert_not_called()


class TestSettingsDecryptedPassword:
    def test_get_decrypted_password(self, settings_service):
        settings_service._settings["remote_drive_password"] = "ENC"
        with patch("app.services.settings_service.decrypt", return_value="plain"):
            assert settings_service.get_decrypted_password() == "plain"

    def test_get_decrypted_password_empty(self, settings_service):
        assert settings_service.get_decrypted_password() == ""

    def test_get_decrypted_password_decrypt_fails(self, settings_service):
        settings_service._settings["remote_drive_password"] = "bad_enc"
        with patch("app.services.settings_service.decrypt", side_effect=Exception("fail")):
            result = settings_service.get_decrypted_password()
            assert result == "bad_enc"


class TestSettingsLoad:
    def test_load_from_disk(self, settings_dir):
        path = settings_dir / "settings.json"
        path.write_text(json.dumps({"session_ttl_hours": 48}), encoding="utf-8")

        with patch("app.services.settings_service._PERSIST_DIR", settings_dir), \
             patch("app.services.settings_service._SETTINGS_PATH", path):
            from app.services.settings_service import SettingsService
            svc = SettingsService()
            assert svc.get("session_ttl_hours") == 48

    def test_load_missing_file(self, settings_dir):
        with patch("app.services.settings_service._PERSIST_DIR", settings_dir), \
             patch("app.services.settings_service._SETTINGS_PATH", settings_dir / "nonexistent.json"):
            from app.services.settings_service import SettingsService
            svc = SettingsService()
            assert svc.get("session_ttl_hours") == 72

    def test_load_corrupt_file(self, settings_dir):
        path = settings_dir / "settings.json"
        path.write_text("not json", encoding="utf-8")

        with patch("app.services.settings_service._PERSIST_DIR", settings_dir), \
             patch("app.services.settings_service._SETTINGS_PATH", path):
            from app.services.settings_service import SettingsService
            svc = SettingsService()
            assert svc.get("session_ttl_hours") == 72


class TestSettingsGetAllDecrypted:
    def test_get_all_decrypted_with_password(self, settings_service):
        settings_service._settings["remote_drive_password"] = "ENC"
        with patch("app.services.settings_service.decrypt", return_value="plain"):
            result = settings_service._get_all_decrypted()
            assert result["remote_drive_password"] == "plain"

    def test_get_all_decrypted_decrypt_fails(self, settings_service):
        settings_service._settings["remote_drive_password"] = "bad_enc"
        with patch("app.services.settings_service.decrypt", side_effect=Exception("fail")):
            result = settings_service._get_all_decrypted()
            assert result["remote_drive_password"] == ""
