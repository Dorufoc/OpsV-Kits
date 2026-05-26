from __future__ import annotations

import copy
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.core.encryption import decrypt, encrypt
from app.core.ssh_client import SSHClientManager
from app.core.ssh_pool import SSHConnectionPool
from app.models.audit_log import AuditLog
from app.models.ssh_account import (
    AccountGroup,
    SSHAccount,
    SSHAccountCreate,
    SSHAccountUpdate,
)


_PERSIST_DIR = Path.home() / ".opsv-kits"
_PERSIST_PATH = _PERSIST_DIR / "accounts.json"


class SSHAccountService:
    def __init__(self):
        self._accounts: dict[str, SSHAccount] = {}
        self._groups: dict[str, AccountGroup] = {}
        self._audit_logs: list[AuditLog] = []
        self._lock = threading.RLock()
        self._pool = SSHConnectionPool()
        self._default_alias: Optional[str] = None
        self._load_from_disk()

    # ── 持久化 ──────────────────────────────────────────────────────

    def _persist_path(self) -> Path:
        return _PERSIST_PATH

    def _load_from_disk(self) -> None:
        path = self._persist_path()
        if not path.is_file():
            return
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            accounts_data: list[dict[str, Any]] = data.get("accounts", [])
            groups_data: list[dict[str, Any]] = data.get("groups", [])
            self._default_alias = data.get("default_alias")

            for item in accounts_data:
                try:
                    account = SSHAccount.model_validate(item)
                    self._accounts[account.alias] = account
                except Exception:
                    continue

            for item in groups_data:
                try:
                    group = AccountGroup.model_validate(item)
                    self._groups[group.name] = group
                except Exception:
                    continue
        except Exception:
            self._accounts.clear()
            self._groups.clear()
            self._default_alias = None

    def _save_to_disk(self) -> None:
        path = self._persist_path()
        try:
            _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            accounts_data = []
            for account in self._accounts.values():
                d = account.model_dump(mode="json")
                accounts_data.append(d)
            groups_data = []
            for group in self._groups.values():
                groups_data.append(group.model_dump(mode="json"))
            data = {
                "accounts": accounts_data,
                "groups": groups_data,
                "default_alias": self._default_alias,
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── CRUD ────────────────────────────────────────────────────────

    def create_account(self, data: SSHAccountCreate) -> SSHAccount:
        with self._lock:
            if data.alias in self._accounts:
                raise ValueError(f"账户别名 '{data.alias}' 已存在")
            encrypted = self._encrypt_sensitive(data)
            account = SSHAccount(
                alias=encrypted.alias,
                host=encrypted.host,
                port=encrypted.port,
                username=encrypted.username,
                auth_type=encrypted.auth_type,
                password=encrypted.password,
                private_key=encrypted.private_key,
                key_passphrase=encrypted.key_passphrase,
                totp_secret=encrypted.totp_secret,
                is_default=encrypted.is_default,
                group=encrypted.group,
            )
            self._accounts[data.alias] = account
            if account.is_default:
                self._default_alias = account.alias
            self._add_audit_log(account.alias, "create", "success", "账户创建成功")
            self._save_to_disk()
            return self._decrypt_account(account)

    def get_account(self, alias: str) -> Optional[SSHAccount]:
        with self._lock:
            account = self._accounts.get(alias)
            if account is None:
                return None
            return self._decrypt_account(account)

    def list_accounts(
        self, group: Optional[str] = None
    ) -> list[SSHAccount]:
        with self._lock:
            result = []
            for account in self._accounts.values():
                if group and account.group != group:
                    continue
                result.append(self._decrypt_account(account))
            return result

    def update_account(self, alias: str, data: SSHAccountUpdate) -> SSHAccount:
        with self._lock:
            if alias not in self._accounts:
                raise ValueError(f"账户 '{alias}' 不存在")
            existing = self._accounts[alias]
            update_data = data.model_dump(exclude_unset=True)
            encrypted_updates = self._encrypt_fields(update_data)
            merged = existing.model_copy(update=encrypted_updates)
            self._accounts[alias] = merged
            if merged.is_default:
                self._default_alias = merged.alias
            if data.is_default is False and self._default_alias == alias:
                self._default_alias = None
            self._add_audit_log(alias, "update", "success", "账户更新成功")
            self._save_to_disk()
            return self._decrypt_account(merged)

    def delete_account(self, alias: str) -> None:
        with self._lock:
            if alias not in self._accounts:
                raise ValueError(f"账户 '{alias}' 不存在")
            self._pool.remove_connection(alias)
            del self._accounts[alias]
            for group in self._groups.values():
                if alias in group.accounts:
                    group.accounts.remove(alias)
            if self._default_alias == alias:
                self._default_alias = None
            self._add_audit_log(alias, "delete", "success", "账户删除成功")
            self._save_to_disk()

    def test_account(self, alias: str, timeout: float = 10.0) -> tuple[bool, str]:
        with self._lock:
            account = self._accounts.get(alias)
            if account is None:
                raise ValueError(f"账户 '{alias}' 不存在")
            decrypted = self._decrypt_account(account)
        manager = SSHClientManager(decrypted)
        success, message = manager.test_connection(timeout)
        status = "success" if success else "failure"
        self._add_audit_log(alias, "test", status, message)
        return success, message

    def set_default(self, alias: str) -> SSHAccount:
        with self._lock:
            if alias not in self._accounts:
                raise ValueError(f"账户 '{alias}' 不存在")
            if self._default_alias is not None and self._default_alias in self._accounts:
                old_default = self._accounts[self._default_alias]
                self._accounts[self._default_alias] = old_default.model_copy(
                    update={"is_default": False}
                )
            self._default_alias = alias
            account = self._accounts[alias]
            self._accounts[alias] = account.model_copy(update={"is_default": True})
            self._add_audit_log(alias, "set_default", "success", "设置为默认账户")
            self._save_to_disk()
            return self._decrypt_account(self._accounts[alias])

    def get_default(self) -> Optional[SSHAccount]:
        with self._lock:
            if self._default_alias is None:
                return None
            account = self._accounts.get(self._default_alias)
            if account is None:
                return None
            return self._decrypt_account(account)

    def init_workplace(self, alias: str) -> str:
        account = self.get_account(alias)
        if account is None:
            raise ValueError(f"账户 '{alias}' 不存在")
        conn = self._pool.get_connection(account)
        try:
            mgr = conn.manager
            path = account.workplace_path
            cmd = f"mkdir -p '{path}' 2>/dev/null && chmod 755 '{path}' 2>/dev/null && echo OK"
            exit_code, stdout, stderr = mgr.exec_command(cmd, timeout=10.0)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if exit_code == 0 and stdout.strip() == "OK":
                return f"工作目录已初始化: {path}"
            raise RuntimeError(f"初始化失败: {stderr}")
        finally:
            self._pool.release_connection(conn)

    # ── 分组管理 ────────────────────────────────────────────────────

    def create_group(self, name: str, accounts: Optional[list[str]] = None) -> AccountGroup:
        with self._lock:
            if name in self._groups:
                raise ValueError(f"分组 '{name}' 已存在")
            group = AccountGroup(name=name, accounts=accounts or [])
            self._groups[name] = group
            self._save_to_disk()
            return group

    def list_groups(self) -> list[AccountGroup]:
        with self._lock:
            return list(self._groups.values())

    def delete_group(self, name: str) -> None:
        with self._lock:
            if name not in self._groups:
                raise ValueError(f"分组 '{name}' 不存在")
            del self._groups[name]
            self._save_to_disk()

    # ── 审计日志 ────────────────────────────────────────────────────

    def get_audit_logs(
        self, account_alias: Optional[str] = None, limit: int = 100
    ) -> list[AuditLog]:
        with self._lock:
            logs = self._audit_logs
            if account_alias:
                logs = [log for log in logs if log.account_alias == account_alias]
            return logs[-limit:]

    # ── 加密辅助 ────────────────────────────────────────────────────

    def _encrypt_sensitive(self, data: SSHAccountCreate) -> SSHAccountCreate:
        encrypted = data.model_copy(deep=True)
        if encrypted.password:
            encrypted.password = encrypt(encrypted.password)
        if encrypted.key_passphrase:
            encrypted.key_passphrase = encrypt(encrypted.key_passphrase)
        if encrypted.totp_secret:
            encrypted.totp_secret = encrypt(encrypted.totp_secret)
        return encrypted

    def _encrypt_fields(self, data: dict) -> dict:
        result = copy.deepcopy(data)
        if "password" in result and result["password"]:
            result["password"] = encrypt(result["password"])
        if "key_passphrase" in result and result["key_passphrase"]:
            result["key_passphrase"] = encrypt(result["key_passphrase"])
        if "totp_secret" in result and result["totp_secret"]:
            result["totp_secret"] = encrypt(result["totp_secret"])
        return result

    def _decrypt_account(self, account: SSHAccount) -> SSHAccount:
        decrypted = account.model_copy(deep=True)
        if decrypted.password:
            try:
                decrypted.password = decrypt(decrypted.password)
            except Exception:
                decrypted.password = None
        if decrypted.key_passphrase:
            try:
                decrypted.key_passphrase = decrypt(decrypted.key_passphrase)
            except Exception:
                decrypted.key_passphrase = None
        if decrypted.totp_secret:
            try:
                decrypted.totp_secret = decrypt(decrypted.totp_secret)
            except Exception:
                decrypted.totp_secret = None
        return decrypted

    def _add_audit_log(
        self, account_alias: str, action: str, status: str, detail: str
    ) -> None:
        log = AuditLog(
            timestamp=datetime.now(),
            account_alias=account_alias,
            action=action,
            status=status,
            detail=detail,
        )
        self._audit_logs.append(log)
        if len(self._audit_logs) > 10000:
            self._audit_logs = self._audit_logs[-5000:]

    @property
    def pool(self) -> SSHConnectionPool:
        return self._pool


ssh_account_service = SSHAccountService()
