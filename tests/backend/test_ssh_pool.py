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


class TestPooledConnection:
    def test_mark_used(self):
        from app.core.ssh_pool import PooledConnection

        mgr = MagicMock()
        conn = PooledConnection(mgr, "test")
        conn.mark_used()
        assert conn.in_use is True

    def test_mark_released(self):
        from app.core.ssh_pool import PooledConnection

        mgr = MagicMock()
        conn = PooledConnection(mgr, "test")
        conn.mark_used()
        conn.mark_released()
        assert conn.in_use is False

    def test_last_used_updates(self):
        from app.core.ssh_pool import PooledConnection

        mgr = MagicMock()
        conn = PooledConnection(mgr, "test")
        t1 = conn.last_used
        time.sleep(0.01)
        conn.mark_used()
        assert conn.last_used >= t1


class TestSSHConnectionPool:
    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_connection_new(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        assert conn.in_use is True
        assert conn.account_alias == "test"

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_connection_reuse_idle(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn1 = pool.get_connection(account)
        pool.release_connection(conn1)
        conn2 = pool.get_connection(account)
        assert conn2 is conn1

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_release_connection(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        assert conn.in_use is False

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_remove_connection(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        pool.remove_connection("test")
        assert pool.get_active_count() == 0

    def test_remove_nonexistent_connection(self):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True
        pool.remove_connection("nonexistent")

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_close_all(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        pool.close_all()
        assert pool.get_active_count() == 0
        assert pool.get_idle_count() == 0

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_active_count(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        assert pool.get_active_count() == 1

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_idle_count(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        assert pool.get_idle_count() == 1

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_connection_status(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        pool.get_connection(account)
        status = pool.get_connection_status("test")
        assert len(status) == 1
        assert status[0]["account_alias"] == "test"

    def test_get_connection_status_nonexistent(self):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True
        assert pool.get_connection_status("nonexistent") == []

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_evict_idle(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool, PooledConnection

        pool = SSHConnectionPool(max_connections=5, idle_timeout=0)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        conn.last_used = time.time() - 1000
        pool._evict_idle()
        assert pool.get_idle_count() == 0

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_reconnect_success(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool, PooledConnection

        pool = SSHConnectionPool(max_connections=5, max_retries=1)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool._reconnect(conn, account, 10.0)
        mock_mgr.close.assert_called()

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_reconnect_failure(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5, max_retries=1)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connect.side_effect = Exception("fail")
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn_mock = MagicMock()
        with pytest.raises(RuntimeError, match="重连失败"):
            pool._reconnect(conn_mock, account, 10.0)

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_get_connection_reconnects_disconnected(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5, max_retries=1)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = False
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        mock_mgr.connected = False
        new_mgr = MagicMock()
        new_mgr.connected = True
        mock_mgr_cls.return_value = new_mgr
        conn2 = pool.get_connection(account)
        assert conn2 is conn

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_evict_removes_disconnected_idle(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5, idle_timeout=0)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = False
        mock_mgr_cls.return_value = mock_mgr

        account = _make_account()
        conn = pool.get_connection(account)
        pool.release_connection(conn)
        pool._evict_idle()
        assert "test" not in pool._pool or len(pool._pool["test"]) == 0

    @patch("app.core.ssh_pool.SSHClientManager")
    def test_total_connections(self, mock_mgr_cls):
        from app.core.ssh_pool import SSHConnectionPool

        pool = SSHConnectionPool(max_connections=5)
        pool._stopped = True

        mock_mgr = MagicMock()
        mock_mgr.connected = True
        mock_mgr_cls.return_value = mock_mgr

        assert pool._total_connections() == 0
        account = _make_account()
        pool.get_connection(account)
        assert pool._total_connections() == 1
