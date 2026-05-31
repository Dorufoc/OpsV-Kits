from __future__ import annotations

import asyncio
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.performance_collector import PerformanceCollector


@pytest.fixture
def collector():
    """创建一个干净的 PerformanceCollector 实例。"""
    return PerformanceCollector()


@pytest.fixture
def mock_account():
    """模拟 SSHAccount。"""
    account = MagicMock()
    account.alias = "test-server"
    account.host = "192.168.1.1"
    account.port = 22
    account.username = "root"
    account.auth_type = "password"
    account.password = "secret"
    account.private_key = None
    account.key_passphrase = None
    return account


class TestPerformanceCollectorLifecycle:
    """测试 PerformanceCollector 的生命周期管理。"""

    def test_init_state(self, collector: PerformanceCollector):
        assert collector._history == {}
        assert collector._sessions == {}
        assert collector._tasks == {}
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_start_stop_collecting(self, collector: PerformanceCollector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account

            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session

                await collector.start_collecting("test-server")
                assert "test-server" in collector._tasks
                assert "test-server" in collector._sessions

                await collector.stop_collecting("test-server")
                assert "test-server" not in collector._tasks
                assert "test-server" not in collector._sessions

    @pytest.mark.asyncio
    async def test_shutdown(self, collector: PerformanceCollector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account

            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session

                await collector.start_collecting("test-server")
                await collector.shutdown()
                assert collector._running is False
                assert "test-server" not in collector._tasks


class TestPerformanceCollectorHistory:
    """测试历史数据存储与访问。"""

    def test_get_latest_snapshot_empty(self, collector: PerformanceCollector):
        assert collector.get_latest_snapshot("nonexistent") is None

    def test_get_history_empty(self, collector: PerformanceCollector):
        assert collector.get_history("nonexistent") == []

    def test_history_circular_buffer(self, collector: PerformanceCollector):
        alias = "test"
        for i in range(4000):
            collector._history[alias].append({"timestamp": i, "data": i})
        assert len(collector._history[alias]) == 3600
        assert collector._history[alias][0]["timestamp"] == 400

    def test_get_history_filter_by_seconds(self, collector: PerformanceCollector):
        alias = "test"
        now = time.time()
        for i in range(100):
            collector._history[alias].append({"timestamp": now - i * 10, "data": i})

        history = collector.get_history(alias, seconds=50)
        # 由于 time.time() 在调用时会有微小差异，结果可能是 5 或 6
        assert 5 <= len(history) <= 6  # now, now-10, now-20, now-30, now-40, now-50


class TestPerformanceCollectorSubscription:
    """测试订阅/发布机制。"""

    def test_subscribe_unsubscribe(self, collector: PerformanceCollector):
        callback = MagicMock()
        collector.subscribe("test", callback)
        assert callback in collector._subscribers["test"]

        collector.unsubscribe("test", callback)
        assert callback not in collector._subscribers["test"]

    def test_notify_subscribers(self, collector: PerformanceCollector):
        callback = MagicMock()
        collector.subscribe("test", callback)

        snapshot = {"timestamp": 1.0, "alias": "test"}
        collector._notify_subscribers("test", snapshot)
        callback.assert_called_once_with(snapshot)

    def test_notify_subscribers_exception_handling(self, collector: PerformanceCollector):
        bad_callback = MagicMock(side_effect=Exception("boom"))
        good_callback = MagicMock()
        collector.subscribe("test", bad_callback)
        collector.subscribe("test", good_callback)

        snapshot = {"timestamp": 1.0, "alias": "test"}
        collector._notify_subscribers("test", snapshot)
        bad_callback.assert_called_once()
        good_callback.assert_called_once()


class TestPerformanceCollectorParsing:
    """测试数据解析器。"""

    def test_parse_cpu(self):
        result = (0, "cpu  1234 0 567 8901 0 0 0 0 0 0\n8", "")
        parsed = PerformanceCollector._parse_cpu(result)
        assert parsed["user"] == 1234
        assert parsed["idle"] == 8901
        assert parsed["cores"] == 8

    def test_parse_cpu_per_core(self):
        result = (0, "cpu0 100 0 50 850\ncpu1 200 0 100 700", "")
        parsed = PerformanceCollector._parse_cpu_per_core(result)
        assert "cpu0" in parsed
        assert "cpu1" in parsed
        assert parsed["cpu0"]["user"] == 100

    def test_parse_memory(self):
        stdout = "MemTotal:       16384000 kB\nMemFree:         8192000 kB\nMemAvailable:   12288000 kB\nBuffers:          1024000 kB\nCached:          2048000 kB"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_memory(result)
        assert parsed["total"] == 16384000 * 1024
        assert parsed["percent"] > 0

    def test_parse_disk(self):
        stdout = "Filesystem     1K-blocks     Used Available Use% Mounted on\n/dev/sda1       10000000  5000000   5000000  50% /\n/dev/sdb1       20000000 10000000  10000000  50% /data"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk(result)
        assert len(parsed) == 2
        assert parsed[0]["mount"] == "/"

    def test_parse_loadavg(self):
        result = (0, "0.52 0.35 0.25 2/1234 5678", "")
        parsed = PerformanceCollector._parse_loadavg(result)
        assert parsed["1min"] == 0.52
        assert parsed["5min"] == 0.35
        assert parsed["15min"] == 0.25

    def test_parse_uptime(self):
        result = (0, "12345.67 89012.34", "")
        parsed = PerformanceCollector._parse_uptime(result)
        assert parsed["uptime_seconds"] == 12345.67
        assert parsed["idle_seconds"] == 89012.34

    def test_parse_temperatures(self):
        result = (0, "45000\n52000\n38000", "")
        parsed = PerformanceCollector._parse_temperatures(result)
        assert len(parsed) == 3
        assert parsed[0]["temp_c"] == 45.0


class TestPerformanceCollectorRateMetrics:
    """测试速率计算逻辑。"""

    def test_compute_rate_metrics_no_prev(self):
        collector = PerformanceCollector()
        result = collector._compute_rate_metrics(None, {"timestamp": 100})
        assert result["cpu_percent"] is None
        assert result["disk_io_rate"] == {}
        assert result["network_rate"] == {}

    def test_compute_rate_metrics_cpu(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "cpu": {"user": 100, "nice": 10, "system": 50, "idle": 800, "iowait": 20, "irq": 5, "softirq": 5, "steal": 0},
        }
        curr = {
            "timestamp": 2,
            "cpu": {"user": 300, "nice": 10, "system": 150, "idle": 50, "iowait": 30, "irq": 15, "softirq": 15, "steal": 430},
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert result["cpu_percent"] is not None
        assert result["cpu_percent"] > 0

    def test_compute_rate_metrics_network(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "network_raw": {
                "eth0": {"rx_bytes": 1000, "tx_bytes": 500, "rx_packets": 10, "tx_packets": 5},
            },
        }
        curr = {
            "timestamp": 2,
            "network_raw": {
                "eth0": {"rx_bytes": 3000, "tx_bytes": 1500, "rx_packets": 30, "tx_packets": 15},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert "eth0" in result["network_rate"]
        assert result["network_rate"]["eth0"]["rx_bytes_sec"] == 1000.0
