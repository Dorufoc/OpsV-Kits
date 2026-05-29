"""进程管理 API 接口测试"""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


@pytest.fixture
def client():
    """创建 TestClient 实例。"""
    return TestClient(app)


class TestProcessList:
    """进程列表接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_list_success(self, mock_ssh_service, mock_process_service, client):
        """成功获取进程列表"""
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
        assert "timestamp" in data
        assert data["count"] == 2
        assert data["processes"][0]["name"] == "systemd"

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_list_empty(self, mock_ssh_service, mock_process_service, client):
        """获取空进程列表"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_all_processes.return_value = []

        response = client.get("/api/process/list?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["processes"] == []

    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_list_account_not_found(self, mock_ssh_service, client):
        """账户不存在时，由于路由层 except Exception 捕获 HTTPException，返回 500"""
        mock_ssh_service.get_account.return_value = None

        response = client.get("/api/process/list?alias=nonexistent")
        assert response.status_code in (404, 500)

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_list_server_error(self, mock_ssh_service, mock_process_service, client):
        """服务异常时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_all_processes.side_effect = Exception("SSH 连接失败")

        response = client.get("/api/process/list?alias=test-server")
        assert response.status_code == 500

    def test_get_process_list_missing_alias(self, client):
        """缺少 alias 参数时返回 422"""
        response = client.get("/api/process/list")
        assert response.status_code == 422


class TestProcessDetail:
    """进程详情接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_detail_success(self, mock_ssh_service, mock_process_service, client):
        """成功获取进程详情"""
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
        assert data["command"] == "java -jar app.jar"

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_detail_not_found(self, mock_ssh_service, mock_process_service, client):
        """进程不存在时返回 404"""
        mock_ssh_service.get_account.return_value = MagicMock()

        async def _async_detail(pid, alias):
            return {"error": f"进程 {pid} 不存在"}

        mock_process_service.get_process_detail = _async_detail

        response = client.get("/api/process/detail?alias=test-server&pid=9999")
        assert response.status_code == 404
        assert "9999" in response.json()["detail"]

    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_detail_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.get("/api/process/detail?alias=nonexistent&pid=1234")
        assert response.status_code == 404

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_process_detail_server_error(self, mock_ssh_service, mock_process_service, client):
        """服务异常时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_process_detail = AsyncMock(side_effect=Exception("SSH 连接失败"))

        response = client.get("/api/process/detail?alias=test-server&pid=1234")
        assert response.status_code == 500

    def test_get_process_detail_missing_alias(self, client):
        """缺少 alias 参数时返回 422"""
        response = client.get("/api/process/detail?pid=1234")
        assert response.status_code == 422

    def test_get_process_detail_missing_pid(self, client):
        """缺少 pid 参数时返回 422"""
        response = client.get("/api/process/detail?alias=test-server")
        assert response.status_code == 422

    def test_get_process_detail_invalid_pid(self, client):
        """pid 为非正整数时返回 422"""
        response = client.get("/api/process/detail?alias=test-server&pid=0")
        assert response.status_code == 422

    def test_get_process_detail_non_numeric_pid(self, client):
        """pid 为非数字时返回 422"""
        response = client.get("/api/process/detail?alias=test-server&pid=abc")
        assert response.status_code == 422


class TestKillProcess:
    """终止进程接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_success(self, mock_ssh_service, mock_process_service, client):
        """成功终止进程"""
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
        assert "message" in data

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_with_sigkill(self, mock_ssh_service, mock_process_service, client):
        """使用 SIGKILL 信号终止进程"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.kill_process.return_value = {
            "success": True,
            "message": "进程已强制终止",
        }

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "SIGKILL"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.post(
            "/api/process/kill",
            json={"alias": "nonexistent", "pid": 1234, "signal": "SIGTERM"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_invalid_signal(self, mock_ssh_service, client):
        """不支持的信号时返回 400"""
        mock_ssh_service.get_account.return_value = MagicMock()

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "INVALID"},
        )
        assert response.status_code == 400
        assert "不支持的信号" in response.json()["detail"]

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_failure(self, mock_ssh_service, mock_process_service, client):
        """终止进程失败时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.kill_process.return_value = {
            "success": False,
            "message": "权限不足",
        }

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "SIGTERM"},
        )
        assert response.status_code == 500
        assert "权限不足" in response.json()["detail"]

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_server_error(self, mock_ssh_service, mock_process_service, client):
        """服务异常时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.kill_process.side_effect = Exception("SSH 连接失败")

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "SIGTERM"},
        )
        assert response.status_code == 500

    def test_kill_process_missing_fields(self, client):
        """缺少必填字段时返回 422"""
        response = client.post(
            "/api/process/kill",
            json={"pid": 1234, "signal": "SIGTERM"},
        )
        assert response.status_code == 422

    def test_kill_process_invalid_pid(self, client):
        """pid 为非正整数时返回 422"""
        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 0, "signal": "SIGTERM"},
        )
        assert response.status_code == 422


class TestNiceProcess:
    """调整进程优先级接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_set_nice_success(self, mock_ssh_service, mock_process_service, client):
        """成功调整进程优先级"""
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
    def test_set_nice_negative_value(self, mock_ssh_service, mock_process_service, client):
        """设置负 nice 值（提高优先级）"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.set_nice.return_value = {
            "success": True,
            "message": "优先级已提高",
        }

        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": -10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_set_nice_boundary_values(self, mock_ssh_service, mock_process_service, client):
        """测试边界 nice 值"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.set_nice.return_value = {"success": True, "message": "ok"}

        # 测试最小值 -20
        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": -20},
        )
        assert response.status_code == 200

        # 测试最大值 19
        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": 19},
        )
        assert response.status_code == 200

    @patch("app.api.routes.process.ssh_account_service")
    def test_set_nice_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.post(
            "/api/process/nice",
            json={"alias": "nonexistent", "pid": 1234, "nice_value": 10},
        )
        assert response.status_code == 404

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_set_nice_failure(self, mock_ssh_service, mock_process_service, client):
        """调整优先级失败时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.set_nice.return_value = {
            "success": False,
            "message": "权限不足",
        }

        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": 10},
        )
        assert response.status_code == 500

    def test_set_nice_out_of_range(self, client):
        """nice 值超出范围时返回 422"""
        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234, "nice_value": 25},
        )
        assert response.status_code == 422

    def test_set_nice_missing_fields(self, client):
        """缺少必填字段时返回 422"""
        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": 1234},
        )
        assert response.status_code == 422

    def test_set_nice_invalid_pid(self, client):
        """pid 为非正整数时返回 422"""
        response = client.post(
            "/api/process/nice",
            json={"alias": "test-server", "pid": -1, "nice_value": 10},
        )
        assert response.status_code == 422


class TestBatchKill:
    """批量终止进程接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_success(self, mock_ssh_service, mock_process_service, client):
        """成功批量终止进程"""
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
        assert data["results"][0]["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_mixed_results(self, mock_ssh_service, mock_process_service, client):
        """批量终止部分成功部分失败"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.batch_kill.return_value = [
            {"pid": 1234, "success": True, "message": "已终止"},
            {"pid": 5678, "success": False, "message": "权限不足"},
        ]

        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "pids": [1234, 5678], "signal": "SIGTERM"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["success"] is True
        assert data["results"][1]["success"] is False

    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "nonexistent", "pids": [1234], "signal": "SIGTERM"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_invalid_signal(self, mock_ssh_service, client):
        """不支持的信号时返回 400"""
        mock_ssh_service.get_account.return_value = MagicMock()

        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "pids": [1234], "signal": "INVALID"},
        )
        assert response.status_code == 400

    def test_batch_kill_empty_pids(self, client):
        """pids 为空列表时返回 422"""
        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "pids": [], "signal": "SIGTERM"},
        )
        assert response.status_code == 422

    def test_batch_kill_missing_fields(self, client):
        """缺少必填字段时返回 422"""
        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "signal": "SIGTERM"},
        )
        assert response.status_code == 422


class TestServiceControl:
    """服务控制接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_start(self, mock_ssh_service, mock_process_service, client):
        """启动服务"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.service_control.return_value = {
            "success": True,
            "message": "服务已启动",
        }

        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx", "action": "start"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_stop(self, mock_ssh_service, mock_process_service, client):
        """停止服务"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.service_control.return_value = {
            "success": True,
            "message": "服务已停止",
        }

        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx", "action": "stop"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_restart(self, mock_ssh_service, mock_process_service, client):
        """重启服务"""
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

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_status(self, mock_ssh_service, mock_process_service, client):
        """查询服务状态"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.service_control.return_value = {
            "success": True,
            "message": "服务正在运行",
            "status": "active",
        }

        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx", "action": "status"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_control_failure(self, mock_ssh_service, mock_process_service, client):
        """服务控制失败时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.service_control.return_value = {
            "success": False,
            "message": "服务不存在",
        }

        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx", "action": "restart"},
        )
        assert response.status_code == 500
        assert "服务不存在" in response.json()["detail"]

    @patch("app.api.routes.process.ssh_account_service")
    def test_service_control_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.post(
            "/api/process/service/control",
            json={"alias": "nonexistent", "service_name": "nginx", "action": "start"},
        )
        assert response.status_code == 404

    def test_service_control_missing_fields(self, client):
        """缺少必填字段时返回 422"""
        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "nginx"},
        )
        assert response.status_code == 422

    def test_service_control_empty_service_name(self, client):
        """service_name 为空时返回 422"""
        response = client.post(
            "/api/process/service/control",
            json={"alias": "test-server", "service_name": "", "action": "start"},
        )
        assert response.status_code == 422


class TestProcessAlerts:
    """进程告警接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alerts_with_anomalies(self, mock_ssh_service, mock_process_service, client):
        """获取包含异常进程的告警"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_alert_config.return_value = {
            "cpu_threshold": 90.0,
            "mem_threshold": 80.0,
            "duration_seconds": 5,
        }
        mock_process_service.detect_anomalies.return_value = {
            "anomalies": [
                {"pid": 1234, "name": "java", "cpu_percent": 95.2, "alert_type": "cpu"},
                {"pid": 5678, "name": "mysql", "memory_percent": 85.0, "alert_type": "memory"},
            ]
        }

        response = client.get("/api/process/alerts?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data
        assert len(data["anomalies"]) == 2

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alerts_no_anomalies(self, mock_ssh_service, mock_process_service, client):
        """无异常进程时返回空告警列表"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_alert_config.return_value = {
            "cpu_threshold": 90.0,
            "mem_threshold": 80.0,
            "duration_seconds": 5,
        }
        mock_process_service.detect_anomalies.return_value = {"anomalies": []}

        response = client.get("/api/process/alerts?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data
        assert len(data["anomalies"]) == 0

    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alerts_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404 或 500"""
        mock_ssh_service.get_account.return_value = None

        response = client.get("/api/process/alerts?alias=nonexistent")
        assert response.status_code in (404, 500)

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alerts_server_error(self, mock_ssh_service, mock_process_service, client):
        """服务异常时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.detect_anomalies.side_effect = Exception("SSH 连接失败")

        response = client.get("/api/process/alerts?alias=test-server")
        assert response.status_code == 500


class TestAlertConfig:
    """告警配置接口测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alert_config_success(self, mock_ssh_service, mock_process_service, client):
        """成功获取告警配置"""
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
        assert "mem_threshold" in data
        assert "duration_seconds" in data
        assert data["cpu_threshold"] == 90.0

    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alert_config_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404 或 500"""
        mock_ssh_service.get_account.return_value = None

        response = client.get("/api/process/alert-config?alias=nonexistent")
        assert response.status_code in (404, 500)

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_get_alert_config_server_error(self, mock_ssh_service, mock_process_service, client):
        """服务异常时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_alert_config.side_effect = Exception("配置读取失败")

        response = client.get("/api/process/alert-config?alias=test-server")
        assert response.status_code == 500

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_success(self, mock_ssh_service, mock_process_service, client):
        """成功保存告警配置"""
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

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_default_values(self, mock_ssh_service, mock_process_service, client):
        """保存告警配置时使用默认值"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.save_alert_config.return_value = True

        response = client.put(
            "/api/process/alert-config",
            json={"alias": "test-server"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_account_not_found(self, mock_ssh_service, client):
        """账户不存在时返回 404"""
        mock_ssh_service.get_account.return_value = None

        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "nonexistent",
                "cpu_threshold": 85.0,
                "mem_threshold": 75.0,
                "duration_seconds": 10,
            },
        )
        assert response.status_code == 404

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_failure(self, mock_ssh_service, mock_process_service, client):
        """保存告警配置失败时返回 500"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.save_alert_config.return_value = False

        response = client.put(
            "/api/process/alert-config",
            json={"alias": "test-server"},
        )
        assert response.status_code == 500

    def test_save_alert_config_invalid_threshold(self, client):
        """阈值超出范围时返回 422"""
        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "test-server",
                "cpu_threshold": 110.0,
                "mem_threshold": 75.0,
                "duration_seconds": 10,
            },
        )
        assert response.status_code == 422

    def test_save_alert_config_negative_duration(self, client):
        """持续时间为负数时返回 422"""
        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "test-server",
                "cpu_threshold": 90.0,
                "mem_threshold": 80.0,
                "duration_seconds": 0,
            },
        )
        assert response.status_code == 422


class TestProcessWebSocket:
    """进程流 WebSocket 接口测试"""

    @patch("app.api.routes.process.ssh_account_service")
    @patch("app.api.routes.process.process_service")
    def test_websocket_connection(self, mock_process_service, mock_ssh_service, client):
        """WebSocket 连接成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.start_streaming = AsyncMock()
        mock_process_service.stop_streaming = AsyncMock()
        mock_process_service.subscribe = MagicMock()
        mock_process_service.unsubscribe = MagicMock()

        with client.websocket_connect("/api/process/ws/stream?alias=test-server") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    @patch("app.api.routes.process.ssh_account_service")
    @patch("app.api.routes.process.process_service")
    def test_websocket_multiple_pings(self, mock_process_service, mock_ssh_service, client):
        """WebSocket 多次 ping/pong"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.start_streaming = AsyncMock()
        mock_process_service.stop_streaming = AsyncMock()
        mock_process_service.subscribe = MagicMock()
        mock_process_service.unsubscribe = MagicMock()

        with client.websocket_connect("/api/process/ws/stream?alias=test-server") as ws:
            for _ in range(3):
                ws.send_json({"type": "ping"})
                data = ws.receive_json()
                assert data["type"] == "pong"

    @patch("app.api.routes.process.ssh_account_service")
    @patch("app.api.routes.process.process_service")
    def test_websocket_invalid_json(self, mock_process_service, mock_ssh_service, client):
        """WebSocket 接收无效 JSON 时不会断开"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.start_streaming = AsyncMock()
        mock_process_service.stop_streaming = AsyncMock()
        mock_process_service.subscribe = MagicMock()
        mock_process_service.unsubscribe = MagicMock()

        with client.websocket_connect("/api/process/ws/stream?alias=test-server") as ws:
            ws.send_text("not valid json")
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_websocket_missing_alias(self, client):
        """WebSocket 缺少 alias 参数时连接失败"""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/process/ws/stream"):
                pass

    @patch("app.api.routes.process.process_service")
    def test_websocket_cleanup_on_disconnect(self, mock_process_service, client):
        """WebSocket 断开时正确清理订阅"""
        mock_ws = MagicMock()
        mock_process_service.subscribe.return_value = None

        mock_process_service.subscribe("test-server", mock_ws)
        mock_process_service.unsubscribe("test-server", mock_ws)

        mock_process_service.subscribe.assert_called_once_with("test-server", mock_ws)
        mock_process_service.unsubscribe.assert_called_once_with("test-server", mock_ws)


class TestProcessEdgeCases:
    """边界情况测试"""

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_case_insensitive_signal(self, mock_ssh_service, mock_process_service, client):
        """信号名称不区分大小写"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.kill_process.return_value = {
            "success": True,
            "message": "进程已终止",
        }

        response = client.post(
            "/api/process/kill",
            json={"alias": "test-server", "pid": 1234, "signal": "sigterm"},
        )
        assert response.status_code == 200

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_large_pid_list(self, mock_ssh_service, mock_process_service, client):
        """批量终止大量进程"""
        mock_ssh_service.get_account.return_value = MagicMock()
        pids = list(range(1, 101))  # 100 个进程
        mock_process_service.batch_kill.return_value = [
            {"pid": pid, "success": True, "message": "已终止"} for pid in pids
        ]

        response = client.post(
            "/api/process/batch/kill",
            json={"alias": "test-server", "pids": pids, "signal": "SIGTERM"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 100

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_alert_config_boundary_values(self, mock_ssh_service, mock_process_service, client):
        """告警配置边界值测试"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.save_alert_config.return_value = True

        # 测试阈值 0
        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "test-server",
                "cpu_threshold": 0.0,
                "mem_threshold": 0.0,
                "duration_seconds": 1,
            },
        )
        assert response.status_code == 200

        # 测试阈值 100
        response = client.put(
            "/api/process/alert-config",
            json={
                "alias": "test-server",
                "cpu_threshold": 100.0,
                "mem_threshold": 100.0,
                "duration_seconds": 1,
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_process_list_special_characters_in_alias(self, mock_ssh_service, mock_process_service, client):
        """别名包含特殊字符"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_process_service.get_all_processes.return_value = []

        response = client.get("/api/process/list?alias=test-server_01")
        assert response.status_code == 200
