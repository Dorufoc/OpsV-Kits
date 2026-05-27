from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from app.core.webssh_adapter import WebSSHSession
from app.models.webssh_session import (
    SessionStatus,
    WebSSHConnectRequest,
    WebSSHSession as WebSSHSessionModel,
)
from app.services.settings_service import settings_service
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

_PERSIST_DIR = Path.home() / ".opsv-kits"
_HISTORY_PATH = _PERSIST_DIR / "sessions.json"


class SessionEntry:
    def __init__(
        self,
        session: WebSSHSessionModel,
        adapter: Optional[WebSSHSession] = None,
    ):
        self.session = session
        self.adapter = adapter
        self.output_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=2048)


class WebSSHService:
    def __init__(self, idle_timeout: int = 600):
        self._idle_timeout = idle_timeout
        self._sessions: dict[str, SessionEntry] = {}
        self._history: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._reaper_running = False
        self._stopped = False
        self._load_history()
        self._start_reaper()

    # ── 会话历史持久化 ──────────────────────────────────────────────

    def _history_path(self) -> Path:
        return _HISTORY_PATH

    def _load_history(self) -> None:
        path = self._history_path()
        if not path.is_file():
            return
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self._history = data
            logger.info(f"已加载 {len(self._history)} 条会话历史")
        except Exception:
            self._history = {}

    def _save_history(self) -> None:
        path = self._history_path()
        try:
            _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._history, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _add_history(self, session: WebSSHSessionModel) -> None:
        record = {
            "session_id": session.session_id,
            "account_alias": session.account_alias,
            "host": session.host,
            "port": session.port,
            "username": session.username,
            "group": session.group,
            "disconnected_at": datetime.now().isoformat(),
        }
        with self._lock:
            self._history[session.session_id] = record
            self._save_history()

    def _clean_expired_history(self) -> None:
        ttl_hours = settings_service.get("session_ttl_hours", 72)
        cutoff = datetime.now() - timedelta(hours=ttl_hours)
        expired = []
        with self._lock:
            for sid, record in self._history.items():
                ts_str = record.get("disconnected_at", "")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts < cutoff:
                            expired.append(sid)
                    except Exception:
                        continue
            for sid in expired:
                del self._history[sid]
            if expired:
                self._save_history()
                logger.info(f"已清理 {len(expired)} 条过期会话历史")

    def list_session_history(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(
                list(self._history.values()),
                key=lambda x: x.get("disconnected_at", ""),
                reverse=True,
            )

    def delete_session_history(self, session_id: str) -> None:
        with self._lock:
            self._history.pop(session_id, None)
            self._save_history()

    # ── 会话管理 ────────────────────────────────────────────────────

    def create_session(self, req: WebSSHConnectRequest) -> WebSSHSessionModel:
        session_id = _generate_session_id()
        account_alias: Optional[str] = None
        host = req.host or ""
        port = req.port
        username = req.username or ""
        password = req.password
        private_key = req.private_key
        key_passphrase = req.key_passphrase
        totp = req.totp_secret

        logger.info(
            f"[{session_id}] creating session: "
            f"account_alias={req.account_alias}, host={host}, "
            f"port={port}, username={username}"
        )

        if req.account_alias:
            account = ssh_account_service.get_account(req.account_alias)
            if account is None:
                raise ValueError(f"SSH账户 '{req.account_alias}' 不存在")
            account_alias = account.alias
            host = account.host
            port = account.port
            username = account.username
            # 优先使用用户传入的凭证，如果没有则使用账户保存的凭证
            # 不限制认证类型，用户可以用密码覆盖密钥账户，反之亦然
            password = password or account.password
            private_key = private_key or account.private_key
            key_passphrase = key_passphrase or account.key_passphrase

        if not host or not username:
            raise ValueError("未提供 host/username 连接参数")

        # 验证至少有一种认证方式可用
        has_credential = bool(password) or bool(private_key)
        if not has_credential:
            raise ValueError(
                "未提供有效的认证凭证，请提供密码或私钥进行连接"
            )

        logger.info(f"[{session_id}] connecting SSH: {username}@{host}:{port}")
        adapter = WebSSHSession(
            session_id=session_id,
            host=host,
            port=port,
            username=username,
            password=password,
            private_key=private_key,
            key_passphrase=key_passphrase,
            totp=totp,
        )
        adapter.connect()

        session_model = WebSSHSessionModel(
            session_id=session_id,
            account_alias=account_alias,
            host=host,
            port=port,
            username=username,
            status=SessionStatus.connected,
            group=req.group,
        )

        entry = SessionEntry(session=session_model, adapter=adapter)
        with self._lock:
            self._sessions[session_id] = entry
        return session_model

    def start_reader(
        self, session_id: str, callback: Callable[[bytes], None]
    ) -> None:
        entry = self._get_entry(session_id)
        if entry is None or entry.adapter is None:
            raise ValueError(f"会话 '{session_id}' 不存在")
        entry.adapter.start_reader(callback)

    def write_to_session(self, session_id: str, data: bytes) -> None:
        entry = self._get_entry(session_id)
        if entry is None or entry.adapter is None:
            raise ValueError(f"会话 '{session_id}' 不存在或已关闭")
        entry.adapter.write(data)
        entry.session.last_active = datetime.now()

    def resize_session(
        self, session_id: str, width: int, height: int
    ) -> None:
        entry = self._get_entry(session_id)
        if entry is None or entry.adapter is None:
            raise ValueError(f"会话 '{session_id}' 不存在或已关闭")
        entry.adapter.resize_pty(width, height)
        entry.session.last_active = datetime.now()

    def close_session(self, session_id: str) -> None:
        with self._lock:
            entry = self._sessions.pop(session_id, None)
        if entry is not None:
            if entry.adapter is not None:
                entry.adapter.close()
            entry.session.status = SessionStatus.disconnected
            self._add_history(entry.session)

    def get_session(
        self, session_id: str
    ) -> Optional[WebSSHSessionModel]:
        entry = self._get_entry(session_id)
        if entry is None:
            return None
        self._update_session_status(entry)
        return entry.session

    def list_sessions(
        self, group: Optional[str] = None
    ) -> list[WebSSHSessionModel]:
        with self._lock:
            sessions = []
            for entry in self._sessions.values():
                self._update_session_status(entry)
                if group is None or entry.session.group == group:
                    sessions.append(entry.session.model_copy())
        return sessions

    def list_groups(self) -> list[str]:
        with self._lock:
            groups: set[str] = set()
            for entry in self._sessions.values():
                if entry.session.group:
                    groups.add(entry.session.group)
            return sorted(groups)

    def get_session_count(self) -> dict[str, int]:
        with self._lock:
            total = len(self._sessions)
            connected = sum(
                1
                for e in self._sessions.values()
                if e.session.status == SessionStatus.connected
            )
            return {"total": total, "connected": connected}

    def _get_entry(self, session_id: str) -> Optional[SessionEntry]:
        with self._lock:
            return self._sessions.get(session_id)

    def _update_session_status(
        self, entry: SessionEntry
    ) -> None:
        if entry.adapter is None:
            return
        if entry.session.status == SessionStatus.connected:
            if not entry.adapter.check_health():
                entry.session.status = SessionStatus.disconnected

    def _start_reaper(self) -> None:
        if self._reaper_running:
            return
        self._reaper_running = True

        def _reap():
            while not self._stopped:
                time.sleep(300)
                try:
                    self._reap_idle()
                    self._clean_expired_history()
                except Exception:
                    pass

        t = threading.Thread(
            target=_reap, daemon=True, name="webssh-reaper"
        )
        t.start()

    def _reap_idle(self) -> None:
        now = datetime.now()
        stale_ids: list[str] = []
        with self._lock:
            for session_id, entry in self._sessions.items():
                if entry.adapter is None:
                    continue
                if not entry.adapter.check_health():
                    stale_ids.append(session_id)
                    continue
                elapsed = (
                    now - entry.session.last_active
                ).total_seconds()
                if elapsed > self._idle_timeout:
                    stale_ids.append(session_id)
        for session_id in stale_ids:
            self.close_session(session_id)

    def shutdown(self) -> None:
        self._stopped = True
        with self._lock:
            session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            self.close_session(session_id)


def _generate_session_id() -> str:
    return uuid.uuid4().hex[:12]


webssh_service = WebSSHService()
