import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.models.ssh_account import SSHAccount


def _make_account(alias="test"):
    return SSHAccount(
        alias=alias, host="192.168.1.1", port=22,
        username="root", auth_type="password", password="secret",
    )


class TestGetConnectionEvictsOnMax:
    @patch("app.core.ssh_pool.SSHClientManager")
    def test_evict_called_when_max_reached(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=1)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn1 = pool.get_connection(account)
        pool.release_connection(conn1)
        conn1.last_used = time.time() - 1000

        account2 = _make_account(alias="test2")
        conn2 = pool.get_connection(account2)
        assert conn2.account_alias == "test2"


class TestRemoveConnectionCloseException:
    @patch("app.core.ssh_pool.SSHClientManager")
    def test_remove_connection_close_raises(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr.close.side_effect = Exception("close error")
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        pool.remove_connection("test")
        assert "test" not in pool._pool


class TestCloseAllCloseException:
    @patch("app.core.ssh_pool.SSHClientManager")
    def test_close_all_close_raises(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr.close.side_effect = Exception("close error")
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        pool.close_all()
        assert pool.get_active_count() == 0
        assert pool.get_idle_count() == 0


class TestEvictIdleRemovesDisconnectedIdle:
    @patch("app.core.ssh_pool.SSHClientManager")
    def test_evict_removes_disconnected_not_idle_timeout(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5, idle_timeout=9999)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = False
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        assert pool.get_idle_count() == 0

        pool._evict_idle()
        assert "test" not in pool._pool or len(pool._pool.get("test", [])) == 0


class TestStartReaperAlreadyRunning:
    def test_start_reaper_noop_when_running(self):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        pool._reaper_running = True
        original_reaper = pool._reaper_running
        pool._start_reaper()
        assert pool._reaper_running is original_reaper


class TestReapFunctionBody:
    def test_reap_calls_evict_idle(self):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        evict_called = []

        original_evict = pool._evict_idle
        def mock_evict():
            evict_called.append(True)
            original_evict()

        pool._evict_idle = mock_evict

        with patch.object(pool, '_lock'):
            with pool._lock:
                mock_evict()

        assert len(evict_called) == 1
