from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_monitor():
    with patch("app.api.routes.monitor.monitor_service") as m:
        yield m


@pytest.fixture
def mock_ssh_account():
    with patch("app.api.routes.monitor.ssh_account_service") as m:
        yield m


class TestGetSnapshot:
    def test_snapshot_success(self, client, mock_monitor):
        mock_monitor.get_snapshot.return_value = {"cpu": 50.0, "memory": 60.0}
        resp = client.get("/api/monitor/snapshot", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["cpu"] == 50.0

    def test_snapshot_value_error(self, client, mock_monitor):
        mock_monitor.get_snapshot.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/snapshot", params={"alias": "srv1"})
        assert resp.status_code == 404

    def test_snapshot_generic_error(self, client, mock_monitor):
        mock_monitor.get_snapshot.side_effect = Exception("fail")
        resp = client.get("/api/monitor/snapshot", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetCpu:
    def test_cpu_success(self, client, mock_monitor):
        mock_monitor.get_cpu_percent.return_value = {"percent": 45.0}
        resp = client.get("/api/monitor/cpu", params={"alias": "srv1"})
        assert resp.status_code == 200

    def test_cpu_value_error(self, client, mock_monitor):
        mock_monitor.get_cpu_percent.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/cpu", params={"alias": "srv1"})
        assert resp.status_code == 404

    def test_cpu_generic_error(self, client, mock_monitor):
        mock_monitor.get_cpu_percent.side_effect = Exception("fail")
        resp = client.get("/api/monitor/cpu", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetCpuCores:
    def test_cpu_cores_success(self, client, mock_monitor):
        mock_monitor.get_cpu_per_core.return_value = [10.0, 20.0, 30.0, 40.0]
        resp = client.get("/api/monitor/cpu/cores", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["cores"] == [10.0, 20.0, 30.0, 40.0]

    def test_cpu_cores_value_error(self, client, mock_monitor):
        mock_monitor.get_cpu_per_core.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/cpu/cores", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetMemory:
    def test_memory_success(self, client, mock_monitor):
        mock_monitor.get_memory_stats.return_value = {"total": 8192, "used": 4096}
        resp = client.get("/api/monitor/memory", params={"alias": "srv1"})
        assert resp.status_code == 200

    def test_memory_value_error(self, client, mock_monitor):
        mock_monitor.get_memory_stats.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/memory", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetDisks:
    def test_disks_success(self, client, mock_monitor):
        mock_monitor.get_disk_stats.return_value = [{"device": "/dev/sda1", "percent": 70.0}]
        resp = client.get("/api/monitor/disks", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "disks" in resp.json()

    def test_disks_value_error(self, client, mock_monitor):
        mock_monitor.get_disk_stats.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/disks", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetDiskIo:
    def test_disk_io_success(self, client, mock_monitor):
        mock_monitor.get_disk_io_rate.return_value = [{"device": "sda", "read": 100}]
        resp = client.get("/api/monitor/disk-io", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "devices" in resp.json()

    def test_disk_io_value_error(self, client, mock_monitor):
        mock_monitor.get_disk_io_rate.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/disk-io", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetNetwork:
    def test_network_success(self, client, mock_monitor):
        mock_monitor.get_network_rate.return_value = [{"iface": "eth0", "send": 1024}]
        resp = client.get("/api/monitor/network", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "interfaces" in resp.json()

    def test_network_value_error(self, client, mock_monitor):
        mock_monitor.get_network_rate.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/network", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetConnections:
    def test_connections_success(self, client, mock_monitor):
        mock_monitor.get_network_connections.return_value = {"established": 10}
        resp = client.get("/api/monitor/connections", params={"alias": "srv1"})
        assert resp.status_code == 200

    def test_connections_value_error(self, client, mock_monitor):
        mock_monitor.get_network_connections.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/connections", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetLoad:
    def test_load_success(self, client, mock_monitor):
        mock_monitor.get_load_average.return_value = {"load1": 0.5, "load5": 0.8, "load15": 1.0}
        resp = client.get("/api/monitor/load", params={"alias": "srv1"})
        assert resp.status_code == 200

    def test_load_value_error(self, client, mock_monitor):
        mock_monitor.get_load_average.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/load", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetProcesses:
    def test_processes_success(self, client, mock_monitor):
        mock_monitor.get_top_processes.return_value = [{"pid": 1, "name": "init", "cpu": 0.1}]
        resp = client.get("/api/monitor/processes", params={"alias": "srv1", "count": 5})
        assert resp.status_code == 200
        assert "processes" in resp.json()

    def test_processes_default_count(self, client, mock_monitor):
        mock_monitor.get_top_processes.return_value = []
        resp = client.get("/api/monitor/processes", params={"alias": "srv1"})
        assert resp.status_code == 200
        mock_monitor.get_top_processes.assert_called_with("srv1", 10)

    def test_processes_value_error(self, client, mock_monitor):
        mock_monitor.get_top_processes.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/processes", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetDocker:
    def test_docker_success(self, client, mock_monitor):
        mock_monitor.get_docker_container_metrics.return_value = [{"name": "web", "cpu": 5.0}]
        resp = client.get("/api/monitor/docker", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "containers" in resp.json()

    def test_docker_value_error(self, client, mock_monitor):
        mock_monitor.get_docker_container_metrics.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/docker", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetMiddleware:
    def test_middleware_success(self, client, mock_monitor):
        mock_monitor.check_middleware_all.return_value = {"redis": "up"}
        mock_monitor.get_middleware_metrics.return_value = {"redis_memory": "10mb"}
        resp = client.get("/api/monitor/middleware", params={"alias": "srv1"})
        assert resp.status_code == 200
        data = resp.json()
        assert "health" in data
        assert "metrics" in data

    def test_middleware_value_error(self, client, mock_monitor):
        mock_monitor.check_middleware_all.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/middleware", params={"alias": "srv1"})
        assert resp.status_code == 404

    def test_middleware_generic_error(self, client, mock_monitor):
        mock_monitor.check_middleware_all.side_effect = Exception("fail")
        resp = client.get("/api/monitor/middleware", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetTemperatures:
    def test_temperatures_success(self, client, mock_monitor):
        mock_monitor.get_temperatures.return_value = [{"sensor": "core0", "temp": 45.0}]
        resp = client.get("/api/monitor/temperatures", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "temperatures" in resp.json()

    def test_temperatures_value_error(self, client, mock_monitor):
        mock_monitor.get_temperatures.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/temperatures", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetHistory:
    def test_history_success(self, client, mock_monitor):
        mock_monitor.get_history.return_value = [{"ts": "2025-01-01", "cpu": 50.0}]
        resp = client.get("/api/monitor/history", params={"alias": "srv1", "seconds": 300})
        assert resp.status_code == 200
        assert "history" in resp.json()

    def test_history_default_seconds(self, client, mock_monitor):
        mock_monitor.get_history.return_value = []
        resp = client.get("/api/monitor/history", params={"alias": "srv1"})
        assert resp.status_code == 200
        mock_monitor.get_history.assert_called_with("srv1", 300)

    def test_history_value_error(self, client, mock_monitor):
        mock_monitor.get_history.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/history", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetCpuSeries:
    def test_cpu_series_success(self, client, mock_monitor):
        mock_monitor.get_cpu_delta_series.return_value = [50.0, 55.0]
        resp = client.get("/api/monitor/series/cpu", params={"alias": "srv1", "points": 60})
        assert resp.status_code == 200
        assert "series" in resp.json()

    def test_cpu_series_default_points(self, client, mock_monitor):
        mock_monitor.get_cpu_delta_series.return_value = []
        resp = client.get("/api/monitor/series/cpu", params={"alias": "srv1"})
        assert resp.status_code == 200
        mock_monitor.get_cpu_delta_series.assert_called_with("srv1", 60)

    def test_cpu_series_value_error(self, client, mock_monitor):
        mock_monitor.get_cpu_delta_series.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/series/cpu", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestGetMemorySeries:
    def test_memory_series_success(self, client, mock_monitor):
        mock_monitor.get_memory_series.return_value = [60.0, 65.0]
        resp = client.get("/api/monitor/series/memory", params={"alias": "srv1", "points": 60})
        assert resp.status_code == 200
        assert "series" in resp.json()

    def test_memory_series_value_error(self, client, mock_monitor):
        mock_monitor.get_memory_series.side_effect = ValueError("not found")
        resp = client.get("/api/monitor/series/memory", params={"alias": "srv1"})
        assert resp.status_code == 404

    def test_memory_series_generic_error(self, client, mock_monitor):
        mock_monitor.get_memory_series.side_effect = Exception("fail")
        resp = client.get("/api/monitor/series/memory", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestEnsureAccount:
    @pytest.mark.asyncio
    async def test_ensure_account_not_found(self, mock_ssh_account):
        mock_ssh_account.get_account.return_value = None
        from app.api.routes.monitor import _ensure_account
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await _ensure_account("nonexistent")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ensure_account_exists(self, mock_ssh_account):
        mock_ssh_account.get_account.return_value = {"alias": "srv1"}
        from app.api.routes.monitor import _ensure_account
        await _ensure_account("srv1")
