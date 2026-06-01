from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.performance_collector import PerformanceCollector


@pytest.fixture
def collector():
    return PerformanceCollector()


@pytest.fixture
def mock_account():
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


class TestLifecycle:
    def test_init_state(self, collector):
        assert collector._history == {}
        assert collector._sessions == {}
        assert collector._tasks == {}
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_start_stop_collecting(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    assert "test-server" in collector._tasks
                    assert "test-server" in collector._sessions
                    await collector.stop_collecting("test-server")
                    assert "test-server" not in collector._tasks
                    assert "test-server" not in collector._sessions

    @pytest.mark.asyncio
    async def test_shutdown(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    await collector.shutdown()
                    assert collector._running is False
                    assert "test-server" not in collector._tasks

    @pytest.mark.asyncio
    async def test_start_collecting_already_running(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    await collector.start_collecting("test-server")
                    assert len([t for t in collector._tasks if t == "test-server"]) == 1

    @pytest.mark.asyncio
    async def test_start_collecting_account_not_found(self, collector):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            await collector.start_collecting("nonexistent")
            assert "nonexistent" not in collector._tasks

    @pytest.mark.asyncio
    async def test_start_collecting_ssh_connect_fail(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = False
                mock_session.connect = AsyncMock(return_value=False)
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    assert "test-server" in collector._tasks

    @pytest.mark.asyncio
    async def test_stop_collecting_not_running(self, collector):
        await collector.stop_collecting("nonexistent")

    @pytest.mark.asyncio
    async def test_initialize_all(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.list_accounts.return_value = [mock_account]
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.initialize_all()
                    assert collector._running is True
                    assert "test-server" in collector._tasks
                    await collector.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_all_no_accounts(self, collector):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.list_accounts.return_value = []
            await collector.initialize_all()
            assert collector._running is True

    @pytest.mark.asyncio
    async def test_on_account_created(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.on_account_created("test-server")
                    assert "test-server" in collector._tasks
                    await collector.stop_collecting("test-server")

    @pytest.mark.asyncio
    async def test_on_account_deleted(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    await collector.on_account_deleted("test-server")
                    assert "test-server" not in collector._tasks

    @pytest.mark.asyncio
    async def test_stop_collecting_closes_session(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                mock_session.close = MagicMock()
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    await collector.stop_collecting("test-server")
                    mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_collecting_clears_prev_samples(self, collector, mock_account):
        with patch("app.services.performance_collector.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            with patch("app.services.performance_collector.DedicatedSSHSession") as MockSession:
                mock_session = AsyncMock()
                mock_session.connected = True
                MockSession.return_value = mock_session
                with patch.object(collector, "_collection_loop", new_callable=AsyncMock):
                    await collector.start_collecting("test-server")
                    collector._prev_samples["test-server"] = {"some": "data"}
                    await collector.stop_collecting("test-server")
                    assert "test-server" not in collector._prev_samples


class TestHistory:
    def test_get_latest_snapshot_empty(self, collector):
        assert collector.get_latest_snapshot("nonexistent") is None

    def test_get_latest_snapshot_with_data(self, collector):
        collector._history["test"].append({"timestamp": 1, "cpu": 50})
        collector._history["test"].append({"timestamp": 2, "cpu": 60})
        result = collector.get_latest_snapshot("test")
        assert result["timestamp"] == 2

    def test_get_history_empty(self, collector):
        assert collector.get_history("nonexistent") == []

    def test_history_circular_buffer(self, collector):
        alias = "test"
        for i in range(4000):
            collector._history[alias].append({"timestamp": i, "data": i})
        assert len(collector._history[alias]) == 3600
        assert collector._history[alias][0]["timestamp"] == 400

    def test_get_history_filter_by_seconds(self, collector):
        alias = "test"
        now = time.time()
        for i in range(100):
            collector._history[alias].append({"timestamp": now - i * 10, "data": i})
        history = collector.get_history(alias, seconds=50)
        assert 5 <= len(history) <= 6


class TestSubscription:
    def test_subscribe_unsubscribe(self, collector):
        callback = MagicMock()
        collector.subscribe("test", callback)
        assert callback in collector._subscribers["test"]
        collector.unsubscribe("test", callback)
        assert callback not in collector._subscribers["test"]

    def test_subscribe_duplicate(self, collector):
        callback = MagicMock()
        collector.subscribe("test", callback)
        collector.subscribe("test", callback)
        assert collector._subscribers["test"].count(callback) == 1

    def test_unsubscribe_nonexistent_alias(self, collector):
        callback = MagicMock()
        collector.unsubscribe("nonexistent", callback)

    def test_unsubscribe_wrong_callback(self, collector):
        cb1 = MagicMock()
        cb2 = MagicMock()
        collector.subscribe("test", cb1)
        collector.unsubscribe("test", cb2)
        assert cb1 in collector._subscribers["test"]

    def test_notify_subscribers(self, collector):
        callback = MagicMock()
        collector.subscribe("test", callback)
        snapshot = {"timestamp": 1.0, "alias": "test"}
        collector._notify_subscribers("test", snapshot)
        callback.assert_called_once_with(snapshot)

    def test_notify_subscribers_exception_handling(self, collector):
        bad_callback = MagicMock(side_effect=Exception("boom"))
        good_callback = MagicMock()
        collector.subscribe("test", bad_callback)
        collector.subscribe("test", good_callback)
        snapshot = {"timestamp": 1.0, "alias": "test"}
        collector._notify_subscribers("test", snapshot)
        bad_callback.assert_called_once()
        good_callback.assert_called_once()

    def test_notify_no_subscribers(self, collector):
        collector._notify_subscribers("nonexistent", {"data": 1})


class TestParseCpu:
    def test_success(self):
        result = (0, "cpu  1234 0 567 8901 0 0 0 0 0 0\n8", "")
        parsed = PerformanceCollector._parse_cpu(result)
        assert parsed["user"] == 1234
        assert parsed["idle"] == 8901
        assert parsed["cores"] == 8

    def test_none(self):
        assert PerformanceCollector._parse_cpu(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_cpu((1, "cpu  1 2 3 4", "")) == {}

    def test_empty_stdout(self):
        assert PerformanceCollector._parse_cpu((0, "", "")) == {}

    def test_insufficient_fields(self):
        assert PerformanceCollector._parse_cpu((0, "cpu  100 200", "")) == {}

    def test_no_cpu_prefix(self):
        assert PerformanceCollector._parse_cpu((0, "xxx  100 0 50 800", "")) == {}

    def test_extended_fields(self):
        result = (0, "cpu  100 0 50 800 10 5 5 3\n4", "")
        parsed = PerformanceCollector._parse_cpu(result)
        assert parsed["iowait"] == 10
        assert parsed["irq"] == 5
        assert parsed["softirq"] == 5
        assert parsed["steal"] == 3

    def test_nproc_parse_error(self):
        result = (0, "cpu  100 0 50 800\nabc", "")
        parsed = PerformanceCollector._parse_cpu(result)
        assert parsed["cores"] == 1

    def test_no_nproc_line(self):
        result = (0, "cpu  100 0 50 800", "")
        parsed = PerformanceCollector._parse_cpu(result)
        assert parsed["cores"] == 1


class TestParseCpuPerCore:
    def test_success(self):
        result = (0, "cpu0 100 0 50 850\ncpu1 200 0 100 700", "")
        parsed = PerformanceCollector._parse_cpu_per_core(result)
        assert "cpu0" in parsed
        assert "cpu1" in parsed
        assert parsed["cpu0"]["user"] == 100

    def test_none(self):
        assert PerformanceCollector._parse_cpu_per_core(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_cpu_per_core((1, "cpu0 1 2 3 4", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_cpu_per_core((0, "", "")) == {}

    def test_insufficient_fields(self):
        assert PerformanceCollector._parse_cpu_per_core((0, "cpu0 100 200", "")) == {}

    def test_no_cpu_prefix(self):
        result = (0, "xxx 100 0 50 800", "")
        parsed = PerformanceCollector._parse_cpu_per_core(result)
        assert parsed == {}

    def test_extended_fields(self):
        result = (0, "cpu0 100 0 50 800 10 5 5 3", "")
        parsed = PerformanceCollector._parse_cpu_per_core(result)
        assert parsed["cpu0"]["iowait"] == 10
        assert parsed["cpu0"]["steal"] == 3


class TestParseMemory:
    def test_success(self):
        stdout = "MemTotal:       16384000 kB\nMemFree:         8192000 kB\nMemAvailable:   12288000 kB\nBuffers:          1024000 kB\nCached:          2048000 kB"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_memory(result)
        assert parsed["total"] == 16384000 * 1024
        assert parsed["percent"] > 0

    def test_none(self):
        assert PerformanceCollector._parse_memory(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_memory((1, "MemTotal: 100 kB", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_memory((0, "", "")) == {}

    def test_no_memavailable(self):
        stdout = "MemTotal:       16384000 kB\nMemFree:         4096000 kB\nBuffers:          1024000 kB\nCached:          2048000 kB"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_memory(result)
        assert parsed["used"] == parsed["total"] - parsed["free"] - parsed["buffers"] - parsed["cached"]

    def test_zero_total(self):
        stdout = "MemTotal:            0 kB\nMemFree:             0 kB"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_memory(result)
        assert parsed["percent"] == 0

    def test_parse_error_in_value(self):
        stdout = "MemTotal:       abc kB\nMemFree:         8192000 kB"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_memory(result)
        assert parsed["total"] == 0


class TestParseDisk:
    def test_success(self):
        stdout = "Filesystem     1K-blocks     Used Available Use% Mounted on\n/dev/sda1       10000000  5000000   5000000  50% /\n/dev/sdb1       20000000 10000000  10000000  50% /data"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk(result)
        assert len(parsed) == 2
        assert parsed[0]["mount"] == "/"

    def test_none(self):
        assert PerformanceCollector._parse_disk(None) == []

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_disk((1, "header\ndata", "")) == []

    def test_empty(self):
        assert PerformanceCollector._parse_disk((0, "", "")) == []

    def test_insufficient_fields(self):
        stdout = "Filesystem  1K-blocks  Used  Avail  Use%  Mounted\n/dev/sda1"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk(result)
        assert parsed == []

    def test_value_error_in_parse(self):
        stdout = "Filesystem  1K-blocks  Used  Avail  Use%  Mounted\n/dev/sda1  abc  5000  5000  50%  /"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk(result)
        assert parsed == []


class TestParseDiskIoRaw:
    def test_success(self):
        stdout = "  1    0 sda 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk_io_raw(result)
        assert "sda" in parsed
        assert parsed["sda"]["reads"] == 100
        assert parsed["sda"]["read_bytes"] == 2000 * 512
        assert parsed["sda"]["write_bytes"] == 4000 * 512

    def test_none(self):
        assert PerformanceCollector._parse_disk_io_raw(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_disk_io_raw((1, "data", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_disk_io_raw((0, "", "")) == {}

    def test_filters_loop_and_ram(self):
        stdout = "  1    0 loop0 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0\n  1    0 ram0 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0\n  1    0 sda 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk_io_raw(result)
        assert "loop0" not in parsed
        assert "ram0" not in parsed
        assert "sda" in parsed

    def test_insufficient_fields(self):
        stdout = "  1    0 sda 100 50"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk_io_raw(result)
        assert parsed == {}

    def test_value_error(self):
        stdout = "  1    0 sda abc 50 2000 300 200 100 4000 500 0 0 0 0 0 0"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_disk_io_raw(result)
        assert parsed == {}


class TestParseNetworkRaw:
    def test_success(self):
        stdout = "Inter-|   Receive                                       |  Transmit\n face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n  eth0: 1000000    5000    0    0    0     0          0         0  2000000    3000    0    0    0     0       0          0\n    lo: 100000    1000    0    0    0     0          0         0  100000    1000    0    0    0     0       0          0"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_network_raw(result)
        assert "eth0" in parsed
        assert "lo" not in parsed
        assert parsed["eth0"]["rx_bytes"] == 1000000
        assert parsed["eth0"]["tx_bytes"] == 2000000

    def test_none(self):
        assert PerformanceCollector._parse_network_raw(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_network_raw((1, "data", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_network_raw((0, "", "")) == {}

    def test_insufficient_fields(self):
        stdout = "header1\nheader2\n  eth0: 100 200"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_network_raw(result)
        assert parsed == {}

    def test_value_error(self):
        stdout = "header1\nheader2\n  eth0: abc 5000 0 0 0 0 0 0 2000000 3000 0 0 0 0 0 0"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_network_raw(result)
        assert parsed == {}


class TestParseLoadavg:
    def test_success(self):
        result = (0, "0.52 0.35 0.25 2/1234 5678", "")
        parsed = PerformanceCollector._parse_loadavg(result)
        assert parsed["1min"] == 0.52
        assert parsed["5min"] == 0.35
        assert parsed["15min"] == 0.25

    def test_none(self):
        assert PerformanceCollector._parse_loadavg(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_loadavg((1, "0.5 0.3 0.2", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_loadavg((0, "", "")) == {}

    def test_insufficient_fields(self):
        assert PerformanceCollector._parse_loadavg((0, "0.52 0.35", "")) == {}

    def test_value_error(self):
        assert PerformanceCollector._parse_loadavg((0, "abc def ghi", "")) == {}


class TestParseProcesses:
    def test_success(self):
        stdout = "  PID  PPID %CPU %MEM COMMAND         ARGS\n    1     0  0.0  0.1 init            /sbin/init\n  123   100  5.5  2.0 python          python app.py"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_processes(result)
        assert len(parsed) == 2
        assert parsed[0]["pid"] == 1
        assert parsed[1]["cpu"] == 5.5

    def test_none(self):
        assert PerformanceCollector._parse_processes(None) == []

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_processes((1, "data", "")) == []

    def test_empty(self):
        assert PerformanceCollector._parse_processes((0, "", "")) == []

    def test_insufficient_fields(self):
        stdout = "PID PPID %CPU %MEM CMD\n1 0 0.0 0.1"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_processes(result)
        assert parsed == []

    def test_value_error(self):
        stdout = "PID PPID %CPU %MEM CMD ARGS\nabc 0 0.0 0.1 init /sbin/init"
        result = (0, stdout, "")
        parsed = PerformanceCollector._parse_processes(result)
        assert parsed == []


class TestParseConnections:
    def test_success(self):
        result = (0, "5\n10", "")
        parsed = PerformanceCollector._parse_connections(result)
        assert parsed["tcp"] == 5
        assert parsed["total"] == 10

    def test_none(self):
        assert PerformanceCollector._parse_connections(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_connections((1, "5\n10", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_connections((0, "", "")) == {}

    def test_single_line(self):
        result = (0, "5", "")
        parsed = PerformanceCollector._parse_connections(result)
        assert parsed["tcp"] == 5
        assert parsed["total"] == 5

    def test_value_error(self):
        result = (0, "abc\ndef", "")
        parsed = PerformanceCollector._parse_connections(result)
        assert parsed == {}


class TestParseUptime:
    def test_success(self):
        result = (0, "12345.67 89012.34", "")
        parsed = PerformanceCollector._parse_uptime(result)
        assert parsed["uptime_seconds"] == 12345.67
        assert parsed["idle_seconds"] == 89012.34

    def test_none(self):
        assert PerformanceCollector._parse_uptime(None) == {}

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_uptime((1, "12345 89012", "")) == {}

    def test_empty(self):
        assert PerformanceCollector._parse_uptime((0, "", "")) == {}

    def test_insufficient_fields(self):
        assert PerformanceCollector._parse_uptime((0, "12345.67", "")) == {}

    def test_value_error(self):
        assert PerformanceCollector._parse_uptime((0, "abc def", "")) == {}


class TestParseDocker:
    def test_success(self):
        line1 = json.dumps({"Names": "nginx", "Image": "nginx:latest"})
        line2 = json.dumps({"Names": "redis", "Image": "redis:latest"})
        result = (0, f"{line1}\n{line2}", "")
        parsed = PerformanceCollector._parse_docker(result)
        assert len(parsed) == 2
        assert parsed[0]["Names"] == "nginx"

    def test_none(self):
        assert PerformanceCollector._parse_docker(None) == []

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_docker((1, "data", "")) == []

    def test_empty(self):
        assert PerformanceCollector._parse_docker((0, "", "")) == []

    def test_empty_array(self):
        result = (0, "[]", "")
        parsed = PerformanceCollector._parse_docker(result)
        assert parsed == []

    def test_invalid_json(self):
        result = (0, "not json\nalso not json", "")
        parsed = PerformanceCollector._parse_docker(result)
        assert parsed == []

    def test_mixed_valid_invalid(self):
        valid = json.dumps({"Names": "nginx"})
        result = (0, f"invalid\n{valid}\nalso invalid", "")
        parsed = PerformanceCollector._parse_docker(result)
        assert len(parsed) == 1
        assert parsed[0]["Names"] == "nginx"

    def test_whitespace_line(self):
        result = (0, "   \n  ", "")
        parsed = PerformanceCollector._parse_docker(result)
        assert parsed == []


class TestParseTemperatures:
    def test_success(self):
        result = (0, "45000\n52000\n38000", "")
        parsed = PerformanceCollector._parse_temperatures(result)
        assert len(parsed) == 3
        assert parsed[0]["temp_c"] == 45.0
        assert parsed[0]["zone"] == "thermal_zone0"

    def test_none(self):
        assert PerformanceCollector._parse_temperatures(None) == []

    def test_nonzero_exit(self):
        assert PerformanceCollector._parse_temperatures((1, "45000", "")) == []

    def test_empty(self):
        assert PerformanceCollector._parse_temperatures((0, "", "")) == []

    def test_value_error(self):
        result = (0, "abc\n45000", "")
        parsed = PerformanceCollector._parse_temperatures(result)
        assert len(parsed) == 1
        assert parsed[0]["temp_c"] == 45.0


class TestRateMetrics:
    def test_no_prev(self):
        collector = PerformanceCollector()
        result = collector._compute_rate_metrics(None, {"timestamp": 100})
        assert result["cpu_percent"] is None
        assert result["disk_io_rate"] == {}
        assert result["network_rate"] == {}

    def test_cpu_percent(self):
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

    def test_cpu_percent_zero_total_diff(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "cpu": {"user": 100, "nice": 0, "system": 0, "idle": 100, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0},
        }
        curr = {
            "timestamp": 2,
            "cpu": {"user": 100, "nice": 0, "system": 0, "idle": 100, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0},
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert result["cpu_percent"] is None

    def test_cpu_per_core_percent(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "cpu_per_core": {
                "cpu0": {"user": 100, "nice": 0, "system": 50, "idle": 800, "iowait": 10, "irq": 5, "softirq": 5, "steal": 0},
            },
        }
        curr = {
            "timestamp": 2,
            "cpu_per_core": {
                "cpu0": {"user": 200, "nice": 0, "system": 100, "idle": 700, "iowait": 20, "irq": 10, "softirq": 10, "steal": 0},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert "cpu0" in result["cpu_per_core_percent"]
        assert result["cpu_per_core_percent"]["cpu0"] > 0

    def test_cpu_per_core_no_prev(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "cpu_per_core": {},
        }
        curr = {
            "timestamp": 2,
            "cpu_per_core": {
                "cpu0": {"user": 200, "nice": 0, "system": 100, "idle": 700, "iowait": 20, "irq": 10, "softirq": 10, "steal": 0},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert result["cpu_per_core_percent"] == {}

    def test_network_rate(self):
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

    def test_network_rate_negative_clamped(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "network_raw": {
                "eth0": {"rx_bytes": 3000, "tx_bytes": 1500, "rx_packets": 30, "tx_packets": 15},
            },
        }
        curr = {
            "timestamp": 2,
            "network_raw": {
                "eth0": {"rx_bytes": 1000, "tx_bytes": 500, "rx_packets": 10, "tx_packets": 5},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert result["network_rate"]["eth0"]["rx_bytes_sec"] == 0

    def test_disk_io_rate(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "disk_io_raw": {
                "sda": {"reads": 100, "read_bytes": 512000, "writes": 50, "write_bytes": 256000},
            },
        }
        curr = {
            "timestamp": 2,
            "disk_io_raw": {
                "sda": {"reads": 200, "read_bytes": 1024000, "writes": 100, "write_bytes": 512000},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert "sda" in result["disk_io_rate"]
        assert result["disk_io_rate"]["sda"]["read_bytes_sec"] == 256000.0
        assert result["disk_io_rate"]["sda"]["write_bytes_sec"] == 128000.0

    def test_disk_io_rate_no_prev(self):
        collector = PerformanceCollector()
        prev = {
            "timestamp": 0,
            "disk_io_raw": {},
        }
        curr = {
            "timestamp": 2,
            "disk_io_raw": {
                "sda": {"reads": 200, "read_bytes": 1024000, "writes": 100, "write_bytes": 512000},
            },
        }
        result = collector._compute_rate_metrics(prev, curr)
        assert result["disk_io_rate"] == {}

    def test_dt_zero(self):
        collector = PerformanceCollector()
        prev = {"timestamp": 100, "cpu": {"user": 100, "nice": 0, "system": 0, "idle": 100, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0}}
        curr = {"timestamp": 100, "cpu": {"user": 200, "nice": 0, "system": 0, "idle": 100, "iowait": 0, "irq": 0, "softirq": 0, "steal": 0}}
        result = collector._compute_rate_metrics(prev, curr)
        assert result["cpu_percent"] is None

    def test_dt_negative(self):
        collector = PerformanceCollector()
        prev = {"timestamp": 200}
        curr = {"timestamp": 100}
        result = collector._compute_rate_metrics(prev, curr)
        assert result["cpu_percent"] is None


class TestCollectOnce:
    @pytest.mark.asyncio
    async def test_no_session(self, collector):
        collector._sessions = {}
        await collector._collect_once("nonexistent")

    @pytest.mark.asyncio
    async def test_session_not_connected_reconnect_fail(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = False
        mock_session._closed = False
        mock_session.connect = AsyncMock(return_value=False)
        collector._sessions["test"] = mock_session
        await collector._collect_once("test")
        mock_session.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_closed_no_reconnect(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = False
        mock_session._closed = True
        collector._sessions["test"] = mock_session
        await collector._collect_once("test")
        mock_session.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_reconnect_success(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = False
        mock_session._closed = False

        async def fake_connect(timeout=15.0):
            mock_session.connected = True
            return True

        mock_session.connect = AsyncMock(side_effect=fake_connect)
        collector._sessions["test"] = mock_session
        with patch.object(collector, "_gather_basic_metrics", return_value={"cpu": {}, "memory": {}}) as mock_gather:
            with patch.object(collector, "_compute_rate_metrics", return_value={"cpu_percent": None, "cpu_per_core_percent": {}, "disk_io_rate": {}, "network_rate": {}}):
                await collector._collect_once("test")
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_once_stores_history(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = True
        collector._sessions["test"] = mock_session
        with patch.object(collector, "_gather_basic_metrics", return_value={"cpu": {}, "memory": {}}):
            with patch.object(collector, "_compute_rate_metrics", return_value={"cpu_percent": None, "cpu_per_core_percent": {}, "disk_io_rate": {}, "network_rate": {}}):
                await collector._collect_once("test")
                assert len(collector._history["test"]) == 1

    @pytest.mark.asyncio
    async def test_collect_once_notifies_subscribers(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = True
        collector._sessions["test"] = mock_session
        callback = MagicMock()
        collector.subscribe("test", callback)
        with patch.object(collector, "_gather_basic_metrics", return_value={"cpu": {}, "memory": {}}):
            with patch.object(collector, "_compute_rate_metrics", return_value={"cpu_percent": None, "cpu_per_core_percent": {}, "disk_io_rate": {}, "network_rate": {}}):
                await collector._collect_once("test")
                callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_once_stores_prev_sample(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = True
        collector._sessions["test"] = mock_session
        with patch.object(collector, "_gather_basic_metrics", return_value={"cpu": {}, "memory": {}}):
            with patch.object(collector, "_compute_rate_metrics", return_value={"cpu_percent": None, "cpu_per_core_percent": {}, "disk_io_rate": {}, "network_rate": {}}):
                await collector._collect_once("test")
                assert "test" in collector._prev_samples


class TestGatherBasicMetrics:
    @pytest.mark.asyncio
    async def test_command_exception(self, collector):
        mock_session = AsyncMock()
        mock_session.exec_command = AsyncMock(side_effect=Exception("SSH error"))
        result = await collector._gather_basic_metrics(mock_session)
        assert result["cpu"] == {}
        assert result["memory"] == {}

    @pytest.mark.asyncio
    async def test_successful_gather(self, collector):
        mock_session = AsyncMock()
        mock_session.exec_command = AsyncMock(return_value=(0, "cpu  100 0 50 800\n4", ""))
        result = await collector._gather_basic_metrics(mock_session)
        assert "cpu" in result
        assert "memory" in result
        assert "disk" in result
        assert "network_raw" in result
        assert "loadavg" in result


class TestCollectionLoop:
    @pytest.mark.asyncio
    async def test_cancellation(self, collector):
        mock_session = AsyncMock()
        mock_session.connected = True
        collector._sessions["test"] = mock_session
        call_count = 0

        async def mock_collect_once(alias):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        with patch.object(collector, "_collect_once", side_effect=mock_collect_once):
            with pytest.raises(asyncio.CancelledError):
                await collector._collection_loop("test")

    @pytest.mark.asyncio
    async def test_timeout_handled(self, collector):
        call_count = 0

        async def mock_collect_once(alias):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            raise asyncio.CancelledError()

        with patch.object(collector, "_collect_once", side_effect=mock_collect_once):
            with pytest.raises(asyncio.CancelledError):
                await collector._collection_loop("test")
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_exception_handled(self, collector):
        call_count = 0

        async def mock_collect_once(alias):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("test error")
            raise asyncio.CancelledError()

        with patch.object(collector, "_collect_once", side_effect=mock_collect_once):
            with pytest.raises(asyncio.CancelledError):
                await collector._collection_loop("test")
            assert call_count == 2
