from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestGetCpuCoresGenericError:
    def test_cpu_cores_generic_error(self, client, mock_monitor):
        mock_monitor.get_cpu_per_core.side_effect = Exception("fail")
        resp = client.get("/api/monitor/cpu/cores", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetMemoryGenericError:
    def test_memory_generic_error(self, client, mock_monitor):
        mock_monitor.get_memory_stats.side_effect = Exception("fail")
        resp = client.get("/api/monitor/memory", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetDisksGenericError:
    def test_disks_generic_error(self, client, mock_monitor):
        mock_monitor.get_disk_stats.side_effect = Exception("fail")
        resp = client.get("/api/monitor/disks", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetDiskIoGenericError:
    def test_disk_io_generic_error(self, client, mock_monitor):
        mock_monitor.get_disk_io_rate.side_effect = Exception("fail")
        resp = client.get("/api/monitor/disk-io", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetNetworkGenericError:
    def test_network_generic_error(self, client, mock_monitor):
        mock_monitor.get_network_rate.side_effect = Exception("fail")
        resp = client.get("/api/monitor/network", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetConnectionsGenericError:
    def test_connections_generic_error(self, client, mock_monitor):
        mock_monitor.get_network_connections.side_effect = Exception("fail")
        resp = client.get("/api/monitor/connections", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetLoadGenericError:
    def test_load_generic_error(self, client, mock_monitor):
        mock_monitor.get_load_average.side_effect = Exception("fail")
        resp = client.get("/api/monitor/load", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetProcessesGenericError:
    def test_processes_generic_error(self, client, mock_monitor):
        mock_monitor.get_top_processes.side_effect = Exception("fail")
        resp = client.get("/api/monitor/processes", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetDockerGenericError:
    def test_docker_generic_error(self, client, mock_monitor):
        mock_monitor.get_docker_container_metrics.side_effect = Exception("fail")
        resp = client.get("/api/monitor/docker", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetTemperaturesGenericError:
    def test_temperatures_generic_error(self, client, mock_monitor):
        mock_monitor.get_temperatures.side_effect = Exception("fail")
        resp = client.get("/api/monitor/temperatures", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetHistoryGenericError:
    def test_history_generic_error(self, client, mock_monitor):
        mock_monitor.get_history.side_effect = Exception("fail")
        resp = client.get("/api/monitor/history", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetCpuSeriesGenericError:
    def test_cpu_series_generic_error(self, client, mock_monitor):
        mock_monitor.get_cpu_delta_series.side_effect = Exception("fail")
        resp = client.get("/api/monitor/series/cpu", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetMemorySeriesGenericError:
    def test_memory_series_generic_error(self, client, mock_monitor):
        mock_monitor.get_memory_series.side_effect = Exception("fail")
        resp = client.get("/api/monitor/series/memory", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestMonitorWebsocket:
    @patch("app.api.routes.monitor.monitor_service")
    @patch("app.api.routes.monitor.ssh_account_service")
    def test_monitor_ws_ping_pong(self, mock_ssh, mock_monitor, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_monitor.subscribe = MagicMock()
        mock_monitor.unsubscribe = MagicMock()
        mock_monitor.start_streaming = AsyncMock()
        mock_monitor.get_history.return_value = []

        with client.websocket_connect("/api/monitor/ws/stream?alias=srv1") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_json()
            assert data["type"] == "pong"

    @patch("app.api.routes.monitor.monitor_service")
    @patch("app.api.routes.monitor.ssh_account_service")
    def test_monitor_ws_history_push(self, mock_ssh, mock_monitor, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_monitor.subscribe = MagicMock()
        mock_monitor.unsubscribe = MagicMock()
        mock_monitor.start_streaming = AsyncMock()
        mock_monitor.get_history.return_value = [
            {"cpu": 50.0, "memory": 60.0},
            {"cpu": 55.0, "memory": 65.0},
        ]

        with client.websocket_connect("/api/monitor/ws/stream?alias=srv1") as ws:
            entry1 = ws.receive_json()
            assert entry1["cpu"] == 50.0
            entry2 = ws.receive_json()
            assert entry2["cpu"] == 55.0

    @patch("app.api.routes.monitor.monitor_service")
    @patch("app.api.routes.monitor.ssh_account_service")
    def test_monitor_ws_history_error(self, mock_ssh, mock_monitor, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_monitor.subscribe = MagicMock()
        mock_monitor.unsubscribe = MagicMock()
        mock_monitor.start_streaming = AsyncMock()
        mock_monitor.get_history.side_effect = Exception("history error")

        with client.websocket_connect("/api/monitor/ws/stream?alias=srv1") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_json()
            assert data["type"] == "pong"

    @patch("app.api.routes.monitor.monitor_service")
    @patch("app.api.routes.monitor.ssh_account_service")
    def test_monitor_ws_invalid_json(self, mock_ssh, mock_monitor, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_monitor.subscribe = MagicMock()
        mock_monitor.unsubscribe = MagicMock()
        mock_monitor.start_streaming = AsyncMock()
        mock_monitor.get_history.return_value = []

        with client.websocket_connect("/api/monitor/ws/stream?alias=srv1") as ws:
            ws.send_text("not json")
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_json()
            assert data["type"] == "pong"

    @patch("app.api.routes.monitor.monitor_service")
    @patch("app.api.routes.monitor.ssh_account_service")
    def test_monitor_ws_empty_history(self, mock_ssh, mock_monitor, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_monitor.subscribe = MagicMock()
        mock_monitor.unsubscribe = MagicMock()
        mock_monitor.start_streaming = AsyncMock()
        mock_monitor.get_history.return_value = []

        with client.websocket_connect("/api/monitor/ws/stream?alias=srv1") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_json()
            assert data["type"] == "pong"


class TestGetProcessesCustomCount:
    def test_processes_custom_count(self, client, mock_monitor):
        mock_monitor.get_top_processes.return_value = []
        resp = client.get("/api/monitor/processes", params={"alias": "srv1", "count": 20})
        assert resp.status_code == 200
        mock_monitor.get_top_processes.assert_called_with("srv1", 20)


class TestGetHistoryCustomSeconds:
    def test_history_custom_seconds(self, client, mock_monitor):
        mock_monitor.get_history.return_value = []
        resp = client.get("/api/monitor/history", params={"alias": "srv1", "seconds": 600})
        assert resp.status_code == 200
        mock_monitor.get_history.assert_called_with("srv1", 600)


class TestGetCpuSeriesCustomPoints:
    def test_cpu_series_custom_points(self, client, mock_monitor):
        mock_monitor.get_cpu_delta_series.return_value = []
        resp = client.get("/api/monitor/series/cpu", params={"alias": "srv1", "points": 30})
        assert resp.status_code == 200
        mock_monitor.get_cpu_delta_series.assert_called_with("srv1", 30)


class TestGetMemorySeriesCustomPoints:
    def test_memory_series_custom_points(self, client, mock_monitor):
        mock_monitor.get_memory_series.return_value = []
        resp = client.get("/api/monitor/series/memory", params={"alias": "srv1", "points": 30})
        assert resp.status_code == 200
        mock_monitor.get_memory_series.assert_called_with("srv1", 30)
