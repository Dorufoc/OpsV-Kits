from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional

from app.core.encryption import encrypt, decrypt

_PERSIST_DIR = Path.home() / ".opsv-kits"
_SETTINGS_PATH = _PERSIST_DIR / "settings.json"

_DEFAULT_SETTINGS: dict[str, Any] = {
    "session_ttl_hours": 72,
    "remote_drive_enabled": True,
    "remote_drive_port": 8081,
    "remote_drive_username": "opsv",
    "remote_drive_password": "",
}


class SettingsService:
    def __init__(self):
        self._lock = threading.RLock()
        self._settings: dict[str, Any] = dict(_DEFAULT_SETTINGS)
        self._load()

    def _path(self) -> Path:
        return _SETTINGS_PATH

    def _load(self) -> None:
        path = self._path()
        if not path.is_file():
            return
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            merged = dict(_DEFAULT_SETTINGS)
            merged.update(data)
            self._settings = merged
        except Exception:
            self._settings = dict(_DEFAULT_SETTINGS)

    def _save(self) -> None:
        path = self._path()
        try:
            _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._settings[key] = value
            self._save()

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            result = dict(self._settings)
            pwd = result.get("remote_drive_password", "")
            result["remote_drive_password_set"] = bool(pwd)
            result.pop("remote_drive_password", None)
            return result

    def update(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if "remote_drive_password" in data and data["remote_drive_password"]:
                data["remote_drive_password"] = encrypt(data["remote_drive_password"])
            self._settings.update(data)
            self._save()
            return self._get_all_decrypted()

    def get_decrypted_password(self, key: str = "remote_drive_password") -> str:
        with self._lock:
            val = self._settings.get(key, "")
            if not val:
                return ""
            try:
                return decrypt(val)
            except Exception:
                return val

    def _get_all_decrypted(self) -> dict[str, Any]:
        with self._lock:
            result = dict(self._settings)
            pwd = result.get("remote_drive_password", "")
            if pwd:
                try:
                    result["remote_drive_password"] = decrypt(pwd)
                except Exception:
                    result["remote_drive_password"] = ""
            return result


settings_service = SettingsService()
