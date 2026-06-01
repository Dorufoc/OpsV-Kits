from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.monitor_service import MonitorService


@pytest.fixture
def service():
    return MonitorService()


def _mock_exec(service, stdout="", stderr="", exit_code=0):
    def _exec_impl(alias, cmd, timeout=30.0):
        return exit_code, stdout, stderr
    return patch.object(service, "_exec", side_effect=_exec_impl)


class TestAdaptCollectorSnapshotHostnameException:
    def test_hostname_exec_exception(self, service):
        with patch.object(service, "_exec", side_effect=Exception("ssh error")):
            result = service._adapt_collector_snapshot({"alias": "server1"})
            assert result["hostname"] == "server1"


class TestGetCpuPercentDeltaZero:
    def test_delta_total_zero(self, service):
        service._cpu_prev["server1"] = {
            "user": 100, "nice": 0, "system": 50, "idle": 800,
            "iowait": 10, "irq": 5, "softirq": 5, "steal": 0, "total": 970
        }
        with patch.object(service, "get_cpu_stats", return_value={
            "user": 100, "nice": 0, "system": 50, "idle": 800,
            "iowait": 10, "irq": 5, "softirq": 5, "steal": 0, "total": 970
        }):
            result = service.get_cpu_percent("server1")
            assert result["usage_percent"] == 0


class TestGetCpuPercentWithPrev:
    def test_with_prev_data(self, service):
        service._cpu_prev["server1"] = {
            "user": 100, "nice": 0, "system": 50, "idle": 800,
            "iowait": 10, "irq": 5, "softirq": 5, "steal": 0, "total": 970
        }
        with patch.object(service, "get_cpu_stats", return_value={
            "user": 200, "nice": 0, "system": 100, "idle": 900,
            "iowait": 20, "irq": 10, "softirq": 10, "steal": 0, "total": 1240
        }), _mock_exec(service, stdout="4"):
            result = service.get_cpu_percent("server1")
            assert result["usage_percent"] > 0
            assert "user_percent" in result
            assert "system_percent" in result
            assert "iowait_percent" in result


class TestGetCpuPerCoreEdgeCases:
    def test_insufficient_parts(self, service):
        with _mock_exec(service, stdout="cpu0 100 50"):
            result = service.get_cpu_per_core("server1")
            assert result == []

    def test_second_call_insufficient_parts(self, service):
        call_count = 0

        def exec_side_effect(alias, cmd, timeout=30.0):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 0, "cpu0 100 0 50 800", ""
            return 0, "cpu0 100 50", ""

        with patch.object(service, "_exec", side_effect=exec_side_effect):
            result = service.get_cpu_per_core("server1")
            assert result == []

    def test_with_prev_data(self, service):
        service._cpu_core_prev["server1"] = [
            {"core": 0, "total": 1000, "idle": 800}
        ]
        with _mock_exec(service, stdout="cpu0 200 0 100 1600"):
            result = service.get_cpu_per_core("server1")
            assert len(result) == 1
            assert result[0]["core"] == 0

    def test_empty_result(self, service):
        service._cpu_core_prev["server1"] = []
        with _mock_exec(service, stdout=""):
            result = service.get_cpu_per_core("server1")
            assert result == []


class TestAsyncGetCpuPerCore:
    @pytest.mark.asyncio
    async def test_async_cpu_per_core_no_prev(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "cpu0 100 0 50 800", ""),
            (0, "cpu0 200 0 100 1600", ""),
        ]):
            result = await service.async_get_cpu_per_core("server1")
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_async_cpu_per_core_with_prev(self, service):
        service._cpu_core_prev["server1"] = [
            {"core": 0, "total": 1000, "idle": 800}
        ]
        with _mock_exec(service, stdout="cpu0 200 0 100 1600"):
            result = await service.async_get_cpu_per_core("server1")
            assert len(result) == 1


class TestGetMemoryStatsSwapInsufficient:
    def test_swap_insufficient_parts(self, service):
        stdout = "Mem:       16384000  8192000  4096000  4096000  16384000\nSwap:       4096000"
        with _mock_exec(service, stdout=stdout):
            result = service.get_memory_stats("server1")
            assert result["total"] == 16384000
            assert "swap" not in result


class TestGetDiskIoRate:
    def test_with_prev_data(self, service):
        service._disk_io_prev["server1"] = [
            {
                "device": "sda", "reads_completed": 100, "reads_merged": 50,
                "sectors_read": 2000, "read_time_ms": 300,
                "writes_completed": 200, "writes_merged": 100,
                "sectors_written": 4000, "write_time_ms": 500,
            }
        ]
        with _mock_exec(service, stdout="1 0 sda 200 100 4000 600 400 200 8000 1000 0 0 0"):
            result = service.get_disk_io_rate("server1")
            assert len(result) == 1
            assert result[0]["device"] == "sda"
            assert result[0]["read_bytes_per_sec"] == (4000 - 2000) * 512
            assert result[0]["write_bytes_per_sec"] == (8000 - 4000) * 512

    def test_no_prev(self, service):
        with patch.object(service, "get_disk_io", side_effect=[
            [{"device": "sda", "reads_completed": 100, "reads_merged": 50,
              "sectors_read": 2000, "read_time_ms": 300,
              "writes_completed": 200, "writes_merged": 100,
              "sectors_written": 4000, "write_time_ms": 500}],
            [{"device": "sda", "reads_completed": 200, "reads_merged": 100,
              "sectors_read": 4000, "read_time_ms": 600,
              "writes_completed": 400, "writes_merged": 200,
              "sectors_written": 8000, "write_time_ms": 1000}],
        ]), patch("time.sleep"):
            result = service.get_disk_io_rate("server1")
            assert len(result) == 1

    def test_device_mismatch(self, service):
        service._disk_io_prev["server1"] = [
            {
                "device": "sdb", "reads_completed": 100, "reads_merged": 50,
                "sectors_read": 2000, "read_time_ms": 300,
                "writes_completed": 200, "writes_merged": 100,
                "sectors_written": 4000, "write_time_ms": 500,
            }
        ]
        with _mock_exec(service, stdout="1 0 sda 200 100 4000 600 400 200 8000 1000 0 0 0"):
            result = service.get_disk_io_rate("server1")
            assert len(result) == 0


class TestAsyncGetDiskIoRate:
    @pytest.mark.asyncio
    async def test_async_disk_io_rate_no_prev(self, service):
        with patch.object(service, "get_disk_io", side_effect=[
            [{"device": "sda", "reads_completed": 100, "reads_merged": 50,
              "sectors_read": 2000, "read_time_ms": 300,
              "writes_completed": 200, "writes_merged": 100,
              "sectors_written": 4000, "write_time_ms": 500}],
            [{"device": "sda", "reads_completed": 200, "reads_merged": 100,
              "sectors_read": 4000, "read_time_ms": 600,
              "writes_completed": 400, "writes_merged": 200,
              "sectors_written": 8000, "write_time_ms": 1000}],
        ]), patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.async_get_disk_io_rate("server1")
            assert len(result) == 1


class TestGetNetworkRateEdgeCases:
    def test_empty_a(self, service):
        service._network_prev["server1"] = []
        with _mock_exec(service, stdout="  eth0: 1000000    5000    0    0    0     0          0         0  2000000    3000    0    0    0     0       0          0"):
            result = service.get_network_rate("server1")
            assert result == []

    def test_with_prev_data(self, service):
        service._network_prev["server1"] = [
            {"interface": "eth0", "rx_bytes": 1000000, "rx_packets": 5000,
             "rx_errors": 0, "rx_drop": 0, "tx_bytes": 2000000,
             "tx_packets": 3000, "tx_errors": 0, "tx_drop": 0}
        ]
        with _mock_exec(service, stdout="  eth0: 2000000    10000    0    0    0     0          0         0  4000000    6000    0    0    0     0       0          0"):
            result = service.get_network_rate("server1")
            assert len(result) == 1
            assert result[0]["rx_bytes_per_sec"] == 1000000
            assert result[0]["tx_bytes_per_sec"] == 2000000


class TestAsyncGetNetworkRate:
    @pytest.mark.asyncio
    async def test_async_network_rate_no_prev(self, service):
        with patch.object(service, "get_network_stats", side_effect=[
            [{"interface": "eth0", "rx_bytes": 1000000, "rx_packets": 5000,
              "rx_errors": 0, "rx_drop": 0, "tx_bytes": 2000000,
              "tx_packets": 3000, "tx_errors": 0, "tx_drop": 0}],
            [{"interface": "eth0", "rx_bytes": 2000000, "rx_packets": 10000,
              "rx_errors": 0, "rx_drop": 0, "tx_bytes": 4000000,
              "tx_packets": 6000, "tx_errors": 0, "tx_drop": 0}],
        ]), patch("asyncio.sleep", new_callable=AsyncMock):
            result = await service.async_get_network_rate("server1")
            assert len(result) == 1


class TestGetNetworkConnectionsValueError:
    def test_value_error_in_count(self, service):
        with _mock_exec(service, stdout="  abc ESTAB"):
            result = service.get_network_connections("server1")
            assert result == {}


class TestGetTemperaturesRawSensorsFallback:
    def test_sensors_fallback(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "invalid", ""),
            (0, "coretemp-isa-0000\nPackage id 0:  +45.0°C  (high = +80.0°C)", ""),
        ]):
            result = service._get_temperatures_raw("server1")
            assert len(result) >= 1

    def test_no_thermal_no_sensors(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "invalid", ""),
            (0, "", ""),
        ]):
            result = service._get_temperatures_raw("server1")
            assert result == []


class TestDockerContainerMetricsParseBytes:
    def test_parse_bytes_various_units(self, service):
        stdout_lines = [
            '{"Name":"/app","Container":"abc123","CPUPerc":"5.0%","MemPerc":"10.0%","MemUsage":"100MiB / 1GiB","NetIO":"1KiB / 2KiB","BlockIO":"3KiB / 4KiB","PIDs":"10"}',
        ]
        with _mock_exec(service, stdout="\n".join(stdout_lines)):
            result = service.get_docker_container_metrics("server1")
            assert len(result) == 1
            assert result[0]["mem_used"] > 0
            assert result[0]["mem_total"] > 0

    def test_parse_bytes_empty_string(self, service):
        stdout = '{"Name":"/app","Container":"abc","CPUPerc":"0%","MemPerc":"0%","MemUsage":" / ","NetIO":" / ","BlockIO":" / ","PIDs":"0"}'
        with _mock_exec(service, stdout=stdout):
            result = service.get_docker_container_metrics("server1")
            assert len(result) == 1

    def test_parse_bytes_unknown_unit(self, service):
        stdout = '{"Name":"/app","Container":"abc","CPUPerc":"0%","MemPerc":"0%","MemUsage":"5XB / 10XB","NetIO":"0B / 0B","BlockIO":"0B / 0B","PIDs":"0"}'
        with _mock_exec(service, stdout=stdout):
            result = service.get_docker_container_metrics("server1")
            assert len(result) == 1


class TestGetMiddlewareMetricsEdgeCases:
    def test_mysql_value_error(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "not_a_number\nabc\ndef", ""),
            (0, "", ""),
        ]):
            result = service.get_middleware_metrics("server1")
            assert "mysql" not in result

    def test_redis_non_int_value(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "", ""),
            (0, "total_connections_received:abc\ntotal_commands_processed:500", ""),
        ]):
            result = service.get_middleware_metrics("server1")
            assert "redis" in result
            assert result["redis"]["total_commands_processed"] == 500


class TestAsyncGetSnapshot:
    @pytest.mark.asyncio
    async def test_with_collector(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {
            "alias": "server1",
            "timestamp": time.time(),
        }
        svc = MonitorService(collector=mock_collector)
        with _mock_exec(svc, stdout="myhost"):
            result = await svc.async_get_snapshot("server1")
            assert result["alias"] == "server1"

    @pytest.mark.asyncio
    async def test_without_collector(self, service):
        with patch.object(service, "async_get_cpu_percent", return_value={"usage_percent": 50}), \
             patch.object(service, "async_get_cpu_per_core", return_value=[]), \
             patch.object(service, "get_memory_stats", return_value={}), \
             patch.object(service, "get_disk_stats", return_value=[]), \
             patch.object(service, "async_get_network_rate", return_value=[]), \
             patch.object(service, "get_load_average", return_value={}), \
             patch.object(service, "get_top_processes", return_value=[]), \
             patch.object(service, "get_network_connections", return_value={}), \
             patch.object(service, "get_uptime", return_value=0), \
             patch.object(service, "get_docker_container_metrics", return_value=[]), \
             _mock_exec(service, stdout="myhost"):
            result = await service.async_get_snapshot("server1")
            assert result["alias"] == "server1"


class TestStreamingCollectorCallback:
    @pytest.mark.asyncio
    async def test_collector_callback_with_dead_ws(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {"alias": "server1", "timestamp": time.time()}
        svc = MonitorService(collector=mock_collector)

        dead_ws = MagicMock()
        dead_ws.send_json = AsyncMock(side_effect=Exception("ws closed"))

        svc.subscribe("server1", dead_ws)
        await svc.start_streaming("server1")

        callback = svc._collector_callbacks.get("server1")
        assert callback is not None

        with _mock_exec(svc, stdout="myhost"):
            callback({"alias": "server1", "timestamp": time.time()})

        await svc.stop_streaming("server1")

    @pytest.mark.asyncio
    async def test_collector_guard_task(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {"alias": "server1", "timestamp": time.time()}
        svc = MonitorService(collector=mock_collector)

        await svc.start_streaming("server1")
        assert "server1" in svc._tasks
        assert not svc._tasks["server1"].done()

        await svc.stop_streaming("server1")


class TestStreamingFallbackException:
    @pytest.mark.asyncio
    async def test_fallback_stream_exception(self, service):
        with patch.object(service, "async_get_snapshot", side_effect=Exception("ssh error")), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()
            await service.start_streaming("server1")
            await svc_stop_safe(service, "server1")

    @pytest.mark.asyncio
    async def test_fallback_stream_sleep_time(self, service):
        call_count = 0

        async def fake_snapshot(alias):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()
            return {"timestamp": time.time(), "alias": alias, "hostname": "h",
                    "cpu": {"usage_percent": 50}, "cores": [], "memory": {},
                    "disks": [], "network": [], "load": {}, "connections": {},
                    "top_processes": [], "uptime": 0, "docker_containers": []}

        with patch.object(service, "async_get_snapshot", side_effect=fake_snapshot), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            await service.start_streaming("server1")
            await svc_stop_safe(service, "server1")


async def svc_stop_safe(svc, alias):
    try:
        await svc.stop_streaming(alias)
    except Exception:
        pass
