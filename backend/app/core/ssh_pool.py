from __future__ import annotations

import threading
import time
from typing import Optional

from app.core.ssh_client import SSHClientManager
from app.models.ssh_account import SSHAccount


class PooledConnection:
    def __init__(self, manager: SSHClientManager, account_alias: str):
        self.manager = manager
        self.account_alias = account_alias
        self.last_used: float = time.time()
        self.in_use: bool = False

    def mark_used(self) -> None:
        self.last_used = time.time()
        self.in_use = True

    def mark_released(self) -> None:
        self.in_use = False
        self.last_used = time.time()


class SSHConnectionPool:
    def __init__(
        self,
        max_connections: int = 10,
        idle_timeout: int = 300,
        keepalive_interval: int = 30,
        max_retries: int = 3,
    ):
        self._max_connections = max_connections
        self._idle_timeout = idle_timeout
        self._keepalive_interval = keepalive_interval
        self._max_retries = max_retries
        self._pool: dict[str, list[PooledConnection]] = {}
        self._lock = threading.RLock()
        self._reaper_running = False
        self._stopped = False
        self._start_reaper()

    def get_connection(
        self, account: SSHAccount, timeout: float = 15.0
    ) -> PooledConnection:
        with self._lock:
            alias = account.alias
            if alias in self._pool:
                conn_list = self._pool[alias]
                for conn in conn_list:
                    if not conn.in_use:
                        if not conn.manager.connected:
                            self._reconnect(conn, account, timeout)
                        conn.mark_used()
                        return conn
            if self._total_connections() >= self._max_connections:
                self._evict_idle()
            manager = SSHClientManager(account, self._keepalive_interval)
            manager.connect(timeout)
            conn = PooledConnection(manager, alias)
            conn.mark_used()
            if alias not in self._pool:
                self._pool[alias] = []
            self._pool[alias].append(conn)
            return conn

    def release_connection(self, conn: PooledConnection) -> None:
        with self._lock:
            conn.mark_released()

    def remove_connection(self, account_alias: str) -> None:
        with self._lock:
            if account_alias not in self._pool:
                return
            for conn in self._pool[account_alias]:
                try:
                    conn.manager.close()
                except Exception:
                    pass
            del self._pool[account_alias]

    def close_all(self) -> None:
        with self._lock:
            self._stopped = True
            for alias, conn_list in self._pool.items():
                for conn in conn_list:
                    try:
                        conn.manager.close()
                    except Exception:
                        pass
            self._pool.clear()

    def get_active_count(self) -> int:
        with self._lock:
            count = 0
            for conn_list in self._pool.values():
                for conn in conn_list:
                    if conn.in_use:
                        count += 1
            return count

    def get_idle_count(self) -> int:
        with self._lock:
            count = 0
            for conn_list in self._pool.values():
                for conn in conn_list:
                    if not conn.in_use and conn.manager.connected:
                        count += 1
            return count

    def get_connection_status(self, account_alias: str) -> list[dict]:
        with self._lock:
            if account_alias not in self._pool:
                return []
            results = []
            for conn in self._pool[account_alias]:
                results.append(
                    {
                        "account_alias": conn.account_alias,
                        "connected": conn.manager.connected,
                        "in_use": conn.in_use,
                        "last_used": conn.last_used,
                    }
                )
            return results

    def _total_connections(self) -> int:
        total = 0
        for conn_list in self._pool.values():
            total += len(conn_list)
        return total

    def _evict_idle(self) -> None:
        now = time.time()
        for alias in list(self._pool.keys()):
            conn_list = self._pool[alias]
            conn_list[:] = [
                c
                for c in conn_list
                if c.in_use or (now - c.last_used < self._idle_timeout)
            ]
            for c in conn_list:
                if not c.in_use and not c.manager.connected:
                    conn_list.remove(c)
            if not conn_list:
                del self._pool[alias]

    def _reconnect(
        self, conn: PooledConnection, account: SSHAccount, timeout: float
    ) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                conn.manager.close()
                new_manager = SSHClientManager(account, self._keepalive_interval)
                new_manager.connect(timeout)
                conn.manager = new_manager
                return
            except Exception as e:
                last_error = e
                time.sleep(1 * (attempt + 1))
        raise RuntimeError(
            f"重连失败 (已重试 {self._max_retries} 次): {last_error}"
        )

    def _start_reaper(self) -> None:
        if self._reaper_running:
            return
        self._reaper_running = True

        def _reap():
            while not self._stopped:
                time.sleep(60)
                try:
                    with self._lock:
                        self._evict_idle()
                except Exception:
                    pass

        t = threading.Thread(target=_reap, daemon=True)
        t.start()
