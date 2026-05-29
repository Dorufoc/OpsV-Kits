import time
import asyncio
from unittest.mock import patch, MagicMock
import pytest

from app.services.monitor_service import monitor_service


@pytest.fixture(autouse=True)
def reset_monitor_state():
    monitor_service._history.clear()
    monitor_service._subscribers.clear()
    monitor_service._tasks.clear()
    monitor_service._cache.clear()
    monitor_service._cache_ttl.clear()
    monitor_service._cpu_prev.clear()
    monitor_service._cpu_core_prev.clear()
    monitor_service._disk_io_prev.clear()
    monitor_service._network_prev.clear()
    yield
    monitor_service._history.clear()
    monitor_service._subscribers.clear()
    monitor_service._tasks.clear()
    monitor_service._cache.clear()
    monitor_service._cache_ttl.clear()
    monitor_service._cpu_prev.clear()
    monitor_service._cpu_core_prev.clear()
    monitor_service._disk_io_prev.clear()
    monitor_service._network_prev.clear()


@pytest.fixture
def mock_ssh_account():
    with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_svc.pool = mock_pool
        yield mock_svc


class TestMonitorPerformance:
    def test_snapshot_response_time(self, mock_ssh_account):
        call_count = 0
        def fake_exec(alias, cmd, timeout=30.0):
            nonlocal call_count
            call_count += 1
            if "cat /proc/stat | head -1" in cmd:
                return (0, "cpu  1000 0 500 8000 0 0 0 0", "")
            if "grep '^cpu[0-9]'" in cmd:
                return (0, "cpu0  1000 0 500 8000\ncpu1  1000 0 500 8000", "")
            if "free -b" in cmd:
                return (0, "Mem:  16384 8192 4096 1024 1024 8192\nSwap: 4096 0 4096", "")
            if "df -B1" in cmd:
                return (0, "/dev/sda1 1000000000 500000000 500000000 50% /", "")
            if "cat /proc/net/dev" in cmd:
                return (0, "  eth0: 1000 10 0 0 0 0 0 0 500 5 0 0 0 0 0 0", "")
            if "cat /proc/loadavg" in cmd:
                return (0, "0.5 0.3 0.1 2/100 1234", "")
            if "ps aux" in cmd:
                return (0, "1234,root,10.0,5.0,nginx", "")
            if "ss -tan" in cmd:
                return (0, "  10 ESTABLISHED", "")
            if "cat /proc/uptime" in cmd:
                return (0, "3600.0 0.0", "")
            if "docker stats" in cmd:
                return (0, "", "")
            if "hostname" in cmd:
                return (0, "testhost", "")
            if "nproc" in cmd:
                return (0, "2", "")
            return (0, "", "")

        with patch.object(monitor_service, "_exec", side_effect=fake_exec):
            start = time.perf_counter()
            result = monitor_service.get_snapshot("test-alias")
            elapsed = time.perf_counter() - start

            assert result["alias"] == "test-alias"
            assert result["hostname"] == "testhost"
            assert elapsed < 3.0

    def test_individual_metrics_response_time(self, mock_ssh_account):
        def fake_exec(alias, cmd, timeout=30.0):
            if "cat /proc/stat | head -1" in cmd:
                return (0, "cpu  1000 0 500 8000 0 0 0 0", "")
            if "free -b" in cmd:
                return (0, "Mem:  16384 8192 4096 1024 1024 8192\nSwap: 4096 0 4096", "")
            if "df -B1" in cmd:
                return (0, "/dev/sda1 1000000000 500000000 500000000 50% /", "")
            if "cat /proc/net/dev" in cmd:
                return (0, "  eth0: 1000 10 0 0 0 0 0 0 500 5 0 0 0 0 0 0", "")
            if "nproc" in cmd:
                return (0, "2", "")
            return (0, "", "")

        with patch.object(monitor_service, "_exec", side_effect=fake_exec):
            start_cpu = time.perf_counter()
            cpu = monitor_service.get_cpu_percent("test-alias")
            elapsed_cpu = time.perf_counter() - start_cpu
            assert elapsed_cpu < 2.0
            assert "usage_percent" in cpu

            monitor_service._cpu_prev.clear()
            start_mem = time.perf_counter()
            mem = monitor_service.get_memory_stats("test-alias")
            elapsed_mem = time.perf_counter() - start_mem
            assert elapsed_mem < 2.0
            assert "total" in mem

            start_disk = time.perf_counter()
            disk = monitor_service.get_disk_stats("test-alias")
            elapsed_disk = time.perf_counter() - start_disk
            assert elapsed_disk < 2.0
            assert isinstance(disk, list)

            monitor_service._network_prev.clear()
            start_net = time.perf_counter()
            net = monitor_service.get_network_rate("test-alias")
            elapsed_net = time.perf_counter() - start_net
            assert elapsed_net < 2.0
            assert isinstance(net, list)

    def test_cache_hit_response_time(self, mock_ssh_account):
        call_count = 0
        def fake_exec(alias, cmd, timeout=30.0):
            nonlocal call_count
            call_count += 1
            if "df -B1" in cmd:
                return (0, "/dev/sda1 1000000000 500000000 500000000 50% /", "")
            return (0, "", "")

        with patch.object(monitor_service, "_exec", side_effect=fake_exec):
            first = monitor_service.get_disk_stats("test-alias")
            assert call_count >= 1

            start = time.perf_counter()
            second = monitor_service.get_disk_stats("test-alias")
            elapsed = time.perf_counter() - start

            assert second == first
            assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_async_snapshot_parallel(self, mock_ssh_account):
        call_times = []
        def fake_exec(alias, cmd, timeout=30.0):
            call_times.append((cmd, time.perf_counter()))
            if "cat /proc/stat | head -1" in cmd:
                return (0, "cpu  1000 0 500 8000 0 0 0 0", "")
            if "grep '^cpu[0-9]'" in cmd:
                return (0, "cpu0  1000 0 500 8000\ncpu1  1000 0 500 8000", "")
            if "free -b" in cmd:
                return (0, "Mem:  16384 8192 4096 1024 1024 8192\nSwap: 4096 0 4096", "")
            if "df -B1" in cmd:
                return (0, "/dev/sda1 1000000000 500000000 500000000 50% /", "")
            if "cat /proc/net/dev" in cmd:
                return (0, "  eth0: 1000 10 0 0 0 0 0 0 500 5 0 0 0 0 0 0", "")
            if "cat /proc/loadavg" in cmd:
                return (0, "0.5 0.3 0.1 2/100 1234", "")
            if "ps aux" in cmd:
                return (0, "1234,root,10.0,5.0,nginx", "")
            if "ss -tan" in cmd:
                return (0, "  10 ESTABLISHED", "")
            if "cat /proc/uptime" in cmd:
                return (0, "3600.0 0.0", "")
            if "docker stats" in cmd:
                return (0, "", "")
            if "hostname" in cmd:
                return (0, "testhost", "")
            if "nproc" in cmd:
                return (0, "2", "")
            return (0, "", "")

        with patch.object(monitor_service, "_exec", side_effect=fake_exec):
            monitor_service._cpu_prev.clear()
            monitor_service._cpu_core_prev.clear()
            monitor_service._network_prev.clear()
            monitor_service._disk_io_prev.clear()

            await monitor_service.async_get_snapshot("test-alias")

            first_time = min(t for _, t in call_times)
            parallel_window = 0.2
            parallel_calls = [cmd for cmd, t in call_times if t - first_time <= parallel_window]
            assert len(parallel_calls) >= 6
