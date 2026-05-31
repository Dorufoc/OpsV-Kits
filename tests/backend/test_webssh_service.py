import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.webssh_session import SessionStatus, WebSSHConnectRequest, WebSSHSession as WebSSHSessionModel


@pytest.fixture
def persist_dir(tmp_path):
    return tmp_path


@pytest.fixture
def service(persist_dir):
    with patch("app.services.webssh_service._PERSIST_DIR", persist_dir), \
         patch("app.services.webssh_service._HISTORY_PATH", persist_dir / "sessions.json"), \
         patch("app.services.webssh_service.settings_service") as mock_settings:
        mock_settings.get.return_value = 72
        from app.services.webssh_service import WebSSHService
        svc = WebSSHService()
        svc._sessions.clear()
        svc._history.clear()
        svc._stopped = True
        return svc


class TestCreateSession:
    def test_create_with_account(self, service):
        with patch("app.services.webssh_service.ssh_account_service") as mock_svc, \
             patch("app.services.webssh_service.WebSSHSession") as mock_adapter:
            account = MagicMock()
            account.alias = "test"
            account.host = "192.168.1.1"
            account.port = 22
            account.username = "root"
            account.password = "secret"
            account.private_key = None
            account.key_passphrase = None
            mock_svc.get_account.return_value = account
            mock_adapter.return_value = MagicMock()

            req = WebSSHConnectRequest(account_alias="test")
            session = service.create_session(req)
            assert session.host == "192.168.1.1"
            assert session.status == SessionStatus.connected

    def test_create_nonexistent_account(self, service):
        with patch("app.services.webssh_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            req = WebSSHConnectRequest(account_alias="nonexistent")
            with pytest.raises(ValueError, match="不存在"):
                service.create_session(req)

    def test_create_direct_connection(self, service):
        with patch("app.services.webssh_service.WebSSHSession") as mock_adapter:
            mock_adapter.return_value = MagicMock()
            req = WebSSHConnectRequest(host="192.168.1.1", username="root", password="secret")
            session = service.create_session(req)
            assert session.host == "192.168.1.1"

    def test_create_missing_host(self, service):
        req = WebSSHConnectRequest(username="root", password="secret")
        with pytest.raises(ValueError, match="未提供 host/username"):
            service.create_session(req)

    def test_create_missing_credentials(self, service):
        req = WebSSHConnectRequest(host="192.168.1.1", username="root")
        with pytest.raises(ValueError, match="未提供有效的认证凭证"):
            service.create_session(req)


class TestSessionOperations:
    @pytest.fixture
    def session_entry(self, service):
        from app.services.webssh_service import SessionEntry

        session = WebSSHSessionModel(
            session_id="test-session",
            host="192.168.1.1",
            port=22,
            username="root",
            status=SessionStatus.connected,
        )
        adapter = MagicMock()
        adapter.check_health.return_value = True
        entry = SessionEntry(session=session, adapter=adapter)
        service._sessions["test-session"] = entry
        return entry

    def test_write_to_session(self, service, session_entry):
        service.write_to_session("test-session", b"ls\n")
        session_entry.adapter.write.assert_called_once_with(b"ls\n")

    def test_write_to_nonexistent_session(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.write_to_session("nonexistent", b"ls\n")

    def test_resize_session(self, service, session_entry):
        service.resize_session("test-session", 80, 24)
        session_entry.adapter.resize_pty.assert_called_with(80, 24)

    def test_resize_nonexistent_session(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.resize_session("nonexistent", 80, 24)

    def test_close_session(self, service, session_entry):
        service.close_session("test-session")
        assert "test-session" not in service._sessions
        session_entry.adapter.close.assert_called_once()

    def test_close_session_adds_history(self, service, session_entry):
        service.close_session("test-session")
        assert "test-session" in service._history

    def test_get_session(self, service, session_entry):
        session = service.get_session("test-session")
        assert session is not None
        assert session.session_id == "test-session"

    def test_get_session_nonexistent(self, service):
        assert service.get_session("nonexistent") is None

    def test_get_session_updates_status(self, service, session_entry):
        session_entry.adapter.check_health.return_value = False
        session = service.get_session("test-session")
        assert session.status == SessionStatus.disconnected

    def test_list_sessions(self, service, session_entry):
        sessions = service.list_sessions()
        assert len(sessions) == 1

    def test_list_sessions_by_group(self, service, session_entry):
        session_entry.session.group = "grp1"
        sessions = service.list_sessions(group="grp1")
        assert len(sessions) == 1
        sessions = service.list_sessions(group="grp2")
        assert len(sessions) == 0

    def test_list_groups(self, service, session_entry):
        session_entry.session.group = "grp1"
        groups = service.list_groups()
        assert "grp1" in groups

    def test_get_session_count(self, service, session_entry):
        count = service.get_session_count()
        assert count["total"] == 1
        assert count["connected"] == 1


class TestStartReader:
    def test_start_reader_success(self, service):
        from app.services.webssh_service import SessionEntry

        session = WebSSHSessionModel(session_id="r-test", host="1.1.1.1", port=22, username="root")
        adapter = MagicMock()
        entry = SessionEntry(session=session, adapter=adapter)
        service._sessions["r-test"] = entry

        callback = MagicMock()
        service.start_reader("r-test", callback)
        adapter.start_reader.assert_called_with(callback)

    def test_start_reader_nonexistent(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.start_reader("nonexistent", lambda x: None)


class TestSessionHistory:
    def test_list_session_history(self, service):
        service._history["s1"] = {"session_id": "s1", "host": "1.1.1.1", "disconnected_at": "2025-01-15T10:00:00"}
        history = service.list_session_history()
        assert len(history) == 1

    def test_delete_session_history(self, service):
        service._history["s1"] = {"session_id": "s1"}
        service.delete_session_history("s1")
        assert "s1" not in service._history

    def test_clean_expired_history(self, service):
        service._history["s1"] = {"session_id": "s1", "disconnected_at": "2020-01-01T00:00:00"}
        service._clean_expired_history()
        assert "s1" not in service._history


class TestShutdown:
    def test_shutdown(self, service):
        from app.services.webssh_service import SessionEntry

        session = WebSSHSessionModel(session_id="sh-test", host="1.1.1.1", port=22, username="root")
        adapter = MagicMock()
        entry = SessionEntry(session=session, adapter=adapter)
        service._sessions["sh-test"] = entry

        service.shutdown()
        assert service._stopped is True
        assert len(service._sessions) == 0


class TestReapIdle:
    def test_reap_idle_disconnected(self, service):
        from app.services.webssh_service import SessionEntry

        session = WebSSHSessionModel(session_id="idle-test", host="1.1.1.1", port=22, username="root")
        adapter = MagicMock()
        adapter.check_health.return_value = False
        entry = SessionEntry(session=session, adapter=adapter)
        service._sessions["idle-test"] = entry

        service._reap_idle()
        assert "idle-test" not in service._sessions


class TestGenerateSessionId:
    def test_generate_session_id(self):
        from app.services.webssh_service import _generate_session_id

        sid = _generate_session_id()
        assert len(sid) == 12
        assert sid.isalnum()
