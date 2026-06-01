from __future__ import annotations

import asyncio
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


def _mock_conn(service):
    return patch.object(service, "_conn", return_value=MagicMock())


class TestConn:
    def test_conn_account_not_found(self, service):
        with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                service._conn("nonexistent")

    def test_conn_success(self, service):
        with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
            mock_account = MagicMock()
            mock_svc.get_account.return_value = mock_account
            mock_conn = MagicMock()
            mock_svc.pool.get_connection.return_value = mock_conn
            result = service._conn("server1")
            assert result is mock_conn


class TestExec:
    def test_exec_string_output(self, service):
        with _mock_conn(service):
            with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
                mock_svc.pool.release_connection = MagicMock()
                mock_conn = MagicMock()
                mock_conn.manager.exec_command.return_value = (0, "output", "err")
                with patch.object(service, "_conn", return_value=mock_conn):
                    code, out, err = service._exec("server1", "ls")
                    assert code == 0
                    assert out == "output"

    def test_exec_bytes_output(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, b"bytes output", b"bytes err")
        with patch.object(service, "_conn", return_value=mock_conn):
            with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
                mock_svc.pool.release_connection = MagicMock()
                code, out, err = service._exec("server1", "ls")
                assert isinstance(out, str)
                assert isinstance(err, str)

    def test_exec_strips_output(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "  output  ", "  err  ")
        with patch.object(service, "_conn", return_value=mock_conn):
            with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
                mock_svc.pool.release_connection = MagicMock()
                code, out, err = service._exec("server1", "ls")
                assert out == "output"
                assert err == "err"


class TestGetCached:
    def test_cache_miss(self, service):
        getter = MagicMock(return_value="value")
        result = service._get_cached("server1", "key1", 10.0, getter)
        assert result == "value"
        getter.assert_called_once()

    def test_cache_hit(self, service):
        getter = MagicMock(return_value="value")
        service._get_cached("server1", "key1", 10.0, getter)
        getter.reset_mock()
        result = service._get_cached("server1", "key1", 10.0, getter)
        assert result == "value"
        getter.assert_not_called()

    def test_cache_expired(self, service):
        getter = MagicMock(return_value="old")
        service._get_cached("server1", "key1", 0.0, getter)
        getter.reset_mock()
        getter.return_value = "new"
        result = service._get_cached("server1", "key1", 0.0, getter)
        assert result == "new"
        getter.assert_called_once()


class TestGetCpuStats:
    def test_success(self, service):
        with _mock_exec(service, stdout="cpu  100 0 50 800 10 5 5 0"):
            result = service.get_cpu_stats("server1")
            assert result["user"] == 100
            assert result["idle"] == 800
            assert result["iowait"] == 10

    def test_insufficient_fields(self, service):
        with _mock_exec(service, stdout="cpu  100 0"):
            result = service.get_cpu_stats("server1")
            assert "error" in result

    def test_extended_fields(self, service):
        with _mock_exec(service, stdout="cpu  100 0 50 800 10 5 5 3 0 0"):
            result = service.get_cpu_stats("server1")
            assert result["steal"] == 3


class TestGetCpuPercent:
    def test_no_prev(self, service):
        with patch.object(service, "get_cpu_stats") as mock_stats:
            mock_stats.side_effect = [
                {"user": 100, "nice": 0, "system": 50, "idle": 800, "iowait": 10, "irq": 5, "softirq": 5, "steal": 0, "total": 970},
                {"user": 200, "nice": 0, "system": 100, "idle": 400, "iowait": 20, "irq": 10, "softirq": 10, "steal": 0, "total": 740},
            ]
            with _mock_exec(service, stdout="4"):
                result = service.get_cpu_percent("server1")
                assert "usage_percent" in result

    def test_with_prev(self, service):
        service._cpu_prev["server1"] = {"user": 100, "nice": 0, "system": 50, "idle": 800, "iowait": 10, "irq": 5, "softirq": 5, "steal": 0, "total": 970}
        with patch.object(service, "get_cpu_stats") as mock_stats:
            mock_stats.return_value = {"user": 200, "nice": 0, "system": 100, "idle": 900, "iowait": 20, "irq": 10, "softirq": 10, "steal": 0, "total": 1240}
            with _mock_exec(service, stdout="4"):
                result = service.get_cpu_percent("server1")
                assert result["usage_percent"] > 0

    def test_error_in_stats(self, service):
        service._cpu_prev["server1"] = {"error": "fail"}
        with patch.object(service, "get_cpu_stats") as mock_stats:
            mock_stats.return_value = {"error": "fail"}
            with _mock_exec(service, stdout="4"):
                result = service.get_cpu_percent("server1")
                assert result["usage_percent"] == 0


class TestGetMemoryStats:
    def test_success(self, service):
        stdout = "Mem:       16384000  8192000  4096000  4096000  16384000\nSwap:       4096000        0  4096000"
        with _mock_exec(service, stdout=stdout):
            result = service.get_memory_stats("server1")
            assert result["total"] == 16384000
            assert result["used"] == 8192000
            assert result["swap"]["total"] == 4096000

    def test_no_swap(self, service):
        stdout = "Mem:       16384000  8192000  4096000  4096000  16384000"
        with _mock_exec(service, stdout=stdout):
            result = service.get_memory_stats("server1")
            assert "swap" not in result

    def test_empty_output(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_memory_stats("server1")
            assert result == {}


class TestGetDiskStats:
    def test_success(self, service):
        stdout = "Filesystem     1B-blocks        Used   Available Use% Mounted on\n/dev/sda1      10000000000 5000000000 5000000000  50% /"
        with _mock_exec(service, stdout=stdout):
            result = service.get_disk_stats("server1")
            assert len(result) >= 1
            assert result[0]["mount"] == "/"

    def test_cached(self, service):
        with patch.object(service, "_get_disk_stats_raw", return_value=[{"mount": "/"}]) as mock_raw:
            result = service.get_disk_stats("server1")
            assert len(result) == 1
            mock_raw.assert_called_once()
            result2 = service.get_disk_stats("server1")
            mock_raw.assert_called_once()


class TestGetDiskIo:
    def test_success(self, service):
        stdout = "  1    0 sda 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0"
        with _mock_exec(service, stdout=stdout):
            result = service.get_disk_io("server1")
            assert len(result) == 1
            assert result[0]["device"] == "sda"

    def test_filters_prefix(self, service):
        stdout = "  1    0 loop0 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0\n  1    0 sda 100 50 2000 300 200 100 4000 500 0 0 0 0 0 0"
        with _mock_exec(service, stdout=stdout):
            result = service.get_disk_io("server1")
            assert len(result) == 1
            assert result[0]["device"] == "sda"


class TestGetNetworkStats:
    def test_success(self, service):
        stdout = "  eth0: 1000000    5000    0    0    0     0          0         0  2000000    3000    0    0    0     0       0          0\n    lo: 100000    1000    0    0    0     0          0         0  100000    1000    0    0    0     0       0          0"
        with _mock_exec(service, stdout=stdout):
            result = service.get_network_stats("server1")
            assert len(result) == 1
            assert result[0]["interface"] == "eth0"

    def test_empty_output(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_network_stats("server1")
            assert result == []


class TestGetNetworkConnections:
    def test_success(self, service):
        stdout = "      5 ESTAB\n     10 LISTEN"
        with _mock_exec(service, stdout=stdout):
            result = service.get_network_connections("server1")
            assert result["ESTAB"] == 5
            assert result["LISTEN"] == 10

    def test_empty(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_network_connections("server1")
            assert result == {}


class TestGetLoadAverage:
    def test_success(self, service):
        with _mock_exec(service, stdout="0.52 0.35 0.25 2/1234 5678"):
            result = service.get_load_average("server1")
            assert result["load_1m"] == 0.52
            assert result["load_5m"] == 0.35
            assert result["load_15m"] == 0.25
            assert result["running"] == 2
            assert result["total_processes"] == 1234

    def test_insufficient_fields(self, service):
        with _mock_exec(service, stdout="0.52 0.35"):
            result = service.get_load_average("server1")
            assert result["load_1m"] == 0
            assert result["load_5m"] == 0
            assert result["load_15m"] == 0

    def test_empty(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_load_average("server1")
            assert result["load_1m"] == 0


class TestGetTopProcesses:
    def test_success(self, service):
        stdout = "1234,root,10.5,5.2,java\n5678,app,3.0,2.1,node"
        with _mock_exec(service, stdout=stdout):
            result = service.get_top_processes("server1")
            assert len(result) == 2
            assert result[0]["pid"] == 1234
            assert result[0]["cpu_percent"] == 10.5

    def test_empty(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_top_processes("server1")
            assert result == []


class TestGetUptime:
    def test_success(self, service):
        with _mock_exec(service, stdout="12345.67 89012.34"):
            result = service.get_uptime("server1")
            assert result == 12345.67

    def test_empty(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_uptime("server1")
            assert result == 0


class TestGetTemperatures:
    def test_success(self, service):
        with _mock_exec(service, stdout="45000\n52000"):
            result = service.get_temperatures("server1")
            assert len(result) == 2
            assert result[0]["temperature_celsius"] == 45.0

    def test_cached(self, service):
        with patch.object(service, "_get_temperatures_raw", return_value=[{"sensor": "z0", "temperature_celsius": 45.0}]):
            result = service.get_temperatures("server1")
            assert len(result) == 1


class TestCheckMysql:
    def test_alive(self, service):
        with _mock_exec(service, stdout="ALIVE"):
            result = service.check_mysql("server1")
            assert result["alive"] is True

    def test_dead(self, service):
        with _mock_exec(service, stdout="DEAD"):
            result = service.check_mysql("server1")
            assert result["alive"] is False


class TestCheckRedis:
    def test_alive(self, service):
        with _mock_exec(service, stdout="PONG"):
            result = service.check_redis("server1")
            assert result["alive"] is True

    def test_dead(self, service):
        with _mock_exec(service, stdout="NO_CONNECTION"):
            result = service.check_redis("server1")
            assert result["alive"] is False


class TestCheckMq:
    def test_rabbitmq_alive(self, service):
        with _mock_exec(service, stdout="Status of node rabbit@host"):
            result = service.check_mq("server1", "rabbitmq")
            assert result["alive"] is True
            assert result["type"] == "rabbitmq"

    def test_rabbitmq_running(self, service):
        with _mock_exec(service, stdout="The rabbitmq is running"):
            result = service.check_mq("server1", "rabbitmq")
            assert result["alive"] is True

    def test_rabbitmq_dead(self, service):
        with _mock_exec(service, stdout="DEAD"):
            result = service.check_mq("server1", "rabbitmq")
            assert result["alive"] is False

    def test_kafka_alive(self, service):
        with _mock_exec(service, stdout="localhost:9092"):
            result = service.check_mq("server1", "kafka")
            assert result["alive"] is True
            assert result["type"] == "kafka"

    def test_kafka_dead(self, service):
        with _mock_exec(service, stdout="DEAD"):
            result = service.check_mq("server1", "kafka")
            assert result["alive"] is False

    def test_unsupported(self, service):
        result = service.check_mq("server1", "activemq")
        assert result["alive"] is False
        assert result["type"] == "activemq"


class TestCheckNginx:
    def test_alive_successful(self, service):
        with _mock_exec(service, stdout="test is successful"):
            result = service.check_nginx("server1")
            assert result["alive"] is True

    def test_alive_active(self, service):
        with _mock_exec(service, stdout="active"):
            result = service.check_nginx("server1")
            assert result["alive"] is True

    def test_dead(self, service):
        with _mock_exec(service, stdout="failed"):
            result = service.check_nginx("server1")
            assert result["alive"] is False


class TestCheckMiddlewareAll:
    def test_all(self, service):
        with patch.object(service, "check_mysql", return_value={"alive": True}), \
             patch.object(service, "check_redis", return_value={"alive": True}), \
             patch.object(service, "check_mq", return_value={"alive": True}), \
             patch.object(service, "check_nginx", return_value={"alive": True}):
            result = service.check_middleware_all("server1")
            assert result["mysql"]["alive"] is True
            assert result["redis"]["alive"] is True


class TestGetMiddlewareMetrics:
    def test_mysql_metrics(self, service):
        stdout_mysql = "12345\n10\n5"
        with _mock_exec(service, stdout=stdout_mysql):
            with patch.object(service, "_exec") as mock_exec:
                mock_exec.side_effect = [
                    (0, stdout_mysql, ""),
                    (0, "", ""),
                ]
                result = service.get_middleware_metrics("server1")
                assert "mysql" in result

    def test_redis_metrics(self, service):
        with patch.object(service, "_exec") as mock_exec:
            mock_exec.side_effect = [
                (0, "", ""),
                (0, "total_connections_received:100\ntotal_commands_processed:500", ""),
            ]
            result = service.get_middleware_metrics("server1")
            assert "redis" in result

    def test_empty_metrics(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_middleware_metrics("server1")
            assert result == {}


class TestAdaptCollectorSnapshot:
    def test_full_snapshot(self, service):
        with _mock_exec(service, stdout="myhost"):
            collector_data = {
                "alias": "server1",
                "timestamp": time.time(),
                "cpu_percent": 45.5,
                "cpu": {"cores": 4},
                "cpu_per_core_percent": {"cpu0": 30.0, "cpu1": 50.0},
                "memory": {"total": 16384000000, "used": 8192000000, "free": 4096000000, "available": 12288000000, "percent": 50.0},
                "disk": [{"filesystem": "/dev/sda1", "size": 100000000000, "used": 50000000000, "available": 50000000000, "percent": 50, "mount": "/"}],
                "network_rate": {"eth0": {"rx_bytes_sec": 1000, "tx_bytes_sec": 500, "rx_packets_sec": 10, "tx_packets_sec": 5}},
                "loadavg": {"1min": 0.5, "5min": 0.3, "15min": 0.2},
                "connections": {"tcp": 10, "total": 20},
                "processes": [{"pid": 1, "cpu": 10.0, "mem": 5.0, "comm": "init"}],
                "uptime": {"uptime_seconds": 12345.0},
            }
            result = service._adapt_collector_snapshot(collector_data)
            assert result["alias"] == "server1"
            assert result["cpu"]["usage_percent"] == 45.5
            assert len(result["cores"]) == 2
            assert result["memory"]["usage_percent"] == 50.0
            assert len(result["disks"]) == 1
            assert len(result["network"]) == 1
            assert result["load"]["load_1m"] == 0.5
            assert len(result["top_processes"]) == 1
            assert result["uptime"] == 12345.0

    def test_minimal_snapshot(self, service):
        with _mock_exec(service, stdout="myhost"):
            result = service._adapt_collector_snapshot({"alias": "server1"})
            assert result["cpu"]["usage_percent"] == 0
            assert result["memory"]["usage_percent"] == 0

    def test_zero_total_memory(self, service):
        with _mock_exec(service, stdout="myhost"):
            result = service._adapt_collector_snapshot({
                "alias": "server1",
                "memory": {"total": 0, "used": 0, "free": 0, "available": 0, "percent": 0},
            })
            assert result["memory"]["available_percent"] == 0


class TestGetSnapshot:
    def test_with_collector(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {
            "alias": "server1",
            "timestamp": time.time(),
        }
        svc = MonitorService(collector=mock_collector)
        with _mock_exec(svc, stdout="myhost"):
            result = svc.get_snapshot("server1")
            assert result["alias"] == "server1"

    def test_without_collector(self, service):
        with patch.object(service, "get_cpu_percent", return_value={"usage_percent": 50}), \
             patch.object(service, "get_cpu_per_core", return_value=[]), \
             patch.object(service, "get_memory_stats", return_value={}), \
             patch.object(service, "get_disk_stats", return_value=[]), \
             patch.object(service, "get_network_rate", return_value=[]), \
             patch.object(service, "get_load_average", return_value={}), \
             patch.object(service, "get_top_processes", return_value=[]), \
             patch.object(service, "get_network_connections", return_value={}), \
             patch.object(service, "get_uptime", return_value=0), \
             patch.object(service, "get_docker_container_metrics", return_value=[]), \
             _mock_exec(service, stdout="myhost"):
            result = service.get_snapshot("server1")
            assert result["alias"] == "server1"
            assert "timestamp" in result


class TestStoreAndGetHistory:
    def test_store_and_retrieve(self, service):
        data = {"timestamp": time.time(), "cpu": {"usage_percent": 50}}
        service.store_snapshot("server1", data)
        history = service.get_history("server1")
        assert len(history) == 1

    def test_history_filter_by_seconds(self, service):
        now = time.time()
        service.store_snapshot("server1", {"timestamp": now - 100, "cpu": {}})
        service.store_snapshot("server1", {"timestamp": now - 10, "cpu": {}})
        service.store_snapshot("server1", {"timestamp": now, "cpu": {}})
        history = service.get_history("server1", seconds=50)
        assert len(history) == 2

    def test_history_with_collector(self, service):
        mock_collector = MagicMock()
        mock_collector.get_history.return_value = [
            {"alias": "server1", "timestamp": time.time()},
        ]
        svc = MonitorService(collector=mock_collector)
        with _mock_exec(svc, stdout="myhost"):
            history = svc.get_history("server1")
            assert len(history) == 1

    def test_empty_history(self, service):
        history = service.get_history("server1")
        assert history == []


class TestSubscribeUnsubscribe:
    def test_subscribe(self, service):
        ws = MagicMock()
        service.subscribe("server1", ws)
        assert ws in service._subscribers["server1"]

    def test_unsubscribe(self, service):
        ws = MagicMock()
        service.subscribe("server1", ws)
        service.unsubscribe("server1", ws)
        assert ws not in service._subscribers["server1"]

    def test_unsubscribe_nonexistent(self, service):
        ws = MagicMock()
        service.unsubscribe("server1", ws)


class TestCpuDeltaSeries:
    def test_empty(self, service):
        result = service.get_cpu_delta_series("server1")
        assert result == []

    def test_with_data(self, service):
        now = time.time()
        service.store_snapshot("server1", {"timestamp": now, "cpu": {"usage_percent": 50}})
        result = service.get_cpu_delta_series("server1")
        assert len(result) == 1
        assert result[0]["cpu_percent"] == 50


class TestMemorySeries:
    def test_empty(self, service):
        result = service.get_memory_series("server1")
        assert result == []

    def test_with_data(self, service):
        now = time.time()
        service.store_snapshot("server1", {"timestamp": now, "memory": {"usage_percent": 75}})
        result = service.get_memory_series("server1")
        assert len(result) == 1
        assert result[0]["memory_percent"] == 75


class TestDockerContainerMetrics:
    def test_success(self, service):
        stdout = '{"Name":"/nginx","Container":"abc123def456","CPUPerc":"5.0%","MemPerc":"10.0%","MemUsage":"100MiB / 1GiB","NetIO":"1KiB / 2KiB","BlockIO":"3KiB / 4KiB","PIDs":"10"}'
        with _mock_exec(service, stdout=stdout):
            result = service.get_docker_container_metrics("server1")
            assert len(result) == 1
            assert result[0]["name"] == "nginx"
            assert result[0]["cpu_percent"] == 5.0

    def test_invalid_json(self, service):
        stdout = "not json"
        with _mock_exec(service, stdout=stdout):
            result = service.get_docker_container_metrics("server1")
            assert result == []

    def test_empty(self, service):
        with _mock_exec(service, stdout=""):
            result = service.get_docker_container_metrics("server1")
            assert result == []


class TestStreaming:
    @pytest.mark.asyncio
    async def test_start_streaming_already_running(self, service):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        service._tasks["server1"] = mock_task
        await service.start_streaming("server1")

    @pytest.mark.asyncio
    async def test_stop_streaming(self, service):
        mock_task = asyncio.create_task(asyncio.sleep(100))
        service._tasks["server1"] = mock_task
        await service.stop_streaming("server1")
        assert "server1" not in service._tasks

    @pytest.mark.asyncio
    async def test_stop_streaming_no_task(self, service):
        await service.stop_streaming("server1")

    @pytest.mark.asyncio
    async def test_start_streaming_with_collector(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {"alias": "server1", "timestamp": time.time()}
        svc = MonitorService(collector=mock_collector)
        await svc.start_streaming("server1")
        assert "server1" in svc._tasks
        assert "server1" in svc._collector_callbacks
        await svc.stop_streaming("server1")

    @pytest.mark.asyncio
    async def test_stop_streaming_with_collector_callback(self, service):
        mock_collector = MagicMock()
        mock_collector.get_latest_snapshot.return_value = {"alias": "server1", "timestamp": time.time()}
        svc = MonitorService(collector=mock_collector)
        await svc.start_streaming("server1")
        await svc.stop_streaming("server1")
        mock_collector.unsubscribe.assert_called_once()
        assert "server1" not in svc._collector_callbacks
