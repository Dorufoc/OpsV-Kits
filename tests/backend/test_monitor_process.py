"""监控和进程管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestMonitorSnapshot:
    """监控快照接口测试"""

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_snapshot(self, mock_monitor_service, client):
        mock_monitor_service.get_snapshot.return_value = {
            "cpu_usage": 45.2,
            "memory_usage": 62.5,
            "disk_usage": 55.0,
            "network_in": 1024000,
            "network_out": 512000,
            "uptime": "10 days",
        }

        response = client.get("/api/monitor/snapshot?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_usage" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_cpu(self, mock_monitor_service, client):
        mock_monitor_service.get_cpu_percent.return_value = {"cpu_percent": 45.2}

        response = client.get("/api/monitor/cpu?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_memory(self, mock_monitor_service, client):
        mock_monitor_service.get_memory_stats.return_value = {
            "total_mb": 32768,
            "used_mb": 20480,
            "free_mb": 12288,
            "usage_percent": 62.5,
        }

        response = client.get("/api/monitor/memory?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "total_mb" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_disks(self, mock_monitor_service, client):
        mock_monitor_service.get_disk_stats.return_value = [
            {"mount": "/", "total_gb": 100, "used_gb": 45, "usage_percent": 45.0},
        ]

        response = client.get("/api/monitor/disks?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_load_average(self, mock_monitor_service, client):
        mock_monitor_service.get_load_average.return_value = {
            "load_1m": 1.5,
            "load_5m": 2.0,
            "load_15m": 1.8,
        }

        response = client.get("/api/monitor/load?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "load_1m" in data


class TestMonitorAdvanced:
    """高级监控接口测试"""

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_cpu_cores(self, mock_monitor_service, client):
        mock_monitor_service.get_cpu_per_core.return_value = [12.5, 15.3, 8.7, 22.1]

        response = client.get("/api/monitor/cpu/cores?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "cores" in data
        assert len(data["cores"]) == 4

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_disk_io(self, mock_monitor_service, client):
        mock_monitor_service.get_disk_io_rate.return_value = [
            {"device": "sda", "read_rate": 1024, "write_rate": 2048},
        ]

        response = client.get("/api/monitor/disk-io?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_network(self, mock_monitor_service, client):
        mock_monitor_service.get_network_rate.return_value = [
            {"interface": "eth0", "in_bytes": 1024000, "out_bytes": 512000},
        ]

        response = client.get("/api/monitor/network?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "interfaces" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_connections(self, mock_monitor_service, client):
        mock_monitor_service.get_network_connections.return_value = {
            "tcp": 45,
            "udp": 12,
            "established": 30,
        }

        response = client.get("/api/monitor/connections?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "tcp" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_processes(self, mock_monitor_service, client):
        mock_monitor_service.get_top_processes.return_value = [
            {"pid": 1234, "name": "java", "cpu_percent": 15.5, "memory_percent": 8.2},
            {"pid": 5678, "name": "nginx", "cpu_percent": 5.2, "memory_percent": 2.1},
        ]

        response = client.get("/api/monitor/processes?alias=test-server&count=5")
        assert response.status_code == 200
        data = response.json()
        assert "processes" in data
        assert len(data["processes"]) == 2

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_docker_metrics(self, mock_monitor_service, client):
        mock_monitor_service.get_docker_container_metrics.return_value = [
            {"container_id": "abc123", "cpu_percent": 10.5, "memory_mb": 256},
        ]

        response = client.get("/api/monitor/docker?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "containers" in data


class TestMonitorHistory:
    """监控历史数据测试"""

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_history(self, mock_monitor_service, client):
        mock_monitor_service.get_history.return_value = [
            {"timestamp": "2024-01-01T00:00:00", "cpu": 45.2, "memory": 62.5},
            {"timestamp": "2024-01-01T00:01:00", "cpu": 46.1, "memory": 62.8},
        ]

        response = client.get("/api/monitor/history?alias=test-server&seconds=300")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) == 2

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_cpu_series(self, mock_monitor_service, client):
        mock_monitor_service.get_cpu_delta_series.return_value = [45.2, 46.1, 44.8]

        response = client.get("/api/monitor/series/cpu?alias=test-server&points=60")
        assert response.status_code == 200
        data = response.json()
        assert "series" in data

    @patch("app.api.routes.monitor.monitor_service")
    def test_get_memory_series(self, mock_monitor_service, client):
        mock_monitor_service.get_memory_series.return_value = [62.5, 62.8, 63.1]

        response = client.get("/api/monitor/series/memory?alias=test-server&points=60")
        assert response.status_code == 200
        data = response.json()
        assert "series" in data


class TestProcessManagement:
    """进程管理接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_list(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_all_processes.return_value = [
            {"pid": 1, "name": "systemd", "user": "root", "cpu_percent": 0.0, "memory_percent": 0.5},
            {"pid": 1234, "name": "java", "user": "app", "cpu_percent": 15.5, "memory_percent": 8.2},
        ]

        response = client.get("/api/process/list?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "processes" in data
        assert "count" in data
        assert data["count"] == 2

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_detail(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()

        async def _async_detail(pid, alias):
            return {
                "pid": 1234,
                "name": "java",
                "user": "app",
                "status": "S",
                "cpu_percent": 15.5,
                "memory_percent": 8.2,
                "command": "java -jar app.jar",
            }

        mock_process_service.get_process_detail = _async_detail

        response = client.get("/api/process/detail?alias=test-server&pid=1234")
        assert response.status_code == 200
        data = response.json()
        assert data["pid"] == 1234
        assert data["name"] == "java"

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.kill_process.return_value = {
            "success": True,
            "message": "进程已终止",
        }

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "SIGTERM"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_set_nice(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.set_nice.return_value = {
            "success": True,
            "message": "优先级已调整",
        }

        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.batch_kill.return_value = [
            {"pid": 1234, "success": True, "message": "已终止"},
            {"pid": 5678, "success": True, "message": "已终止"},
        ]

        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "pids": [1234, 5678], "signal": "SIGTERM"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_control(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.service_control.return_value = {
            "success": True,
            "message": "服务已重启",
        }

        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx", "action": "restart"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestProcessAlerts:
    """进程告警接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alerts(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_alert_config.return_value = {
            "cpu_threshold": 90.0,
            "mem_threshold": 80.0,
            "duration_seconds": 5,
        }
        mock_process_service.detect_anomalies.return_value = {
            "anomalies": [
                {"pid": 1234, "name": "java", "cpu_percent": 95.2, "alert_type": "cpu"},
            ]
        }

        response = client.get("/api/process/alerts?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alert_config(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_alert_config.return_value = {
            "cpu_threshold": 90.0,
            "mem_threshold": 80.0,
            "duration_seconds": 5,
        }

        response = client.get("/api/process/alert-config?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_threshold" in data

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.save_alert_config.return_value = True

        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "test-server",
                "cpu_threshold": 85.0,
                "mem_threshold": 75.0,
                "duration_seconds": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMonitorErrors:
    """监控接口错误处理测试"""

    @patch("app.api.routes.monitor.monitor_service")
    def test_monitor_snapshot_account_not_found(self, mock_monitor_service, client):
        # 路由层调用 monitor_service.get_snapshot 时，服务层验证账户不存在会抛 ValueError
        mock_monitor_service.get_snapshot.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")

        response = client.get("/api/monitor/snapshot?alias=nonexistent")
        assert response.status_code == 404


class TestProcessErrors:
    """进程接口错误处理测试"""

    @patch("app.api.routes.monitor.monitor_service")
    def test_process_list_account_not_found(self, mock_monitor_service, client):
        mock_monitor_service.get_snapshot.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")

        response = client.get("/api/monitor/snapshot?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_invalid_signal(self, mock_ssh_service, mock_process_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "INVALID"},
        )
        assert response.status_code == 400
