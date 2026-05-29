"""端口管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPortList:
    """端口列表API测试"""

    @patch("app.api.routes.port.port_service")
    def test_get_port_list_success(self, mock_service, client):
        """测试获取端口列表成功"""
        mock_ports = [
            {
                "protocol": "TCP",
                "port": 80,
                "local_address": "0.0.0.0:80",
                "pid": 1234,
                "process_name": "nginx.exe",
                "status": "LISTEN",
            },
            {
                "protocol": "TCP",
                "port": 443,
                "local_address": "0.0.0.0:443",
                "pid": 1234,
                "process_name": "nginx.exe",
                "status": "LISTEN",
            },
            {
                "protocol": "UDP",
                "port": 53,
                "local_address": "127.0.0.1:53",
                "pid": 5678,
                "process_name": "dnscache.exe",
                "status": "",
            },
        ]
        mock_service.get_port_list.return_value = mock_ports

        response = client.get("/api/port/list")

        assert response.status_code == 200
        data = response.json()
        assert "ports" in data
        assert "count" in data
        assert data["count"] == 3
        assert len(data["ports"]) == 3
        assert data["ports"][0]["port"] == 80
        assert data["ports"][0]["protocol"] == "TCP"
        assert data["ports"][0]["process_name"] == "nginx.exe"

    @patch("app.api.routes.port.port_service")
    def test_get_port_list_empty(self, mock_service, client):
        """测试获取空端口列表"""
        mock_service.get_port_list.return_value = []

        response = client.get("/api/port/list")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["ports"] == []

    @patch("app.api.routes.port.port_service")
    def test_get_port_list_error(self, mock_service, client):
        """测试获取端口列表失败"""
        mock_service.get_port_list.side_effect = Exception("command failed")

        response = client.get("/api/port/list")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestPortCheck:
    """端口检测API测试"""

    @patch("app.api.routes.port.port_service")
    def test_check_port_occupied(self, mock_service, client):
        """测试检测被占用的端口"""
        mock_service.check_port.return_value = {
            "port": 8080,
            "occupied": True,
            "details": [
                {
                    "protocol": "TCP",
                    "port": 8080,
                    "local_address": "0.0.0.0:8080",
                    "pid": 9999,
                    "process_name": "java.exe",
                    "status": "LISTEN",
                }
            ],
        }

        response = client.get("/api/port/check?port=8080")

        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 8080
        assert data["occupied"] is True
        assert len(data["details"]) == 1
        assert data["details"][0]["pid"] == 9999

    @patch("app.api.routes.port.port_service")
    def test_check_port_free(self, mock_service, client):
        """测试检测空闲端口"""
        mock_service.check_port.return_value = {
            "port": 9999,
            "occupied": False,
            "details": [],
        }

        response = client.get("/api/port/check?port=9999")

        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 9999
        assert data["occupied"] is False
        assert data["details"] == []

    def test_check_port_invalid_port_low(self, client):
        """测试检测无效端口号（过小）"""
        response = client.get("/api/port/check?port=0")

        assert response.status_code == 422

    def test_check_port_invalid_port_high(self, client):
        """测试检测无效端口号（过大）"""
        response = client.get("/api/port/check?port=70000")

        assert response.status_code == 422

    def test_check_port_missing_parameter(self, client):
        """测试缺少port参数"""
        response = client.get("/api/port/check")

        assert response.status_code == 422

    @patch("app.api.routes.port.port_service")
    def test_check_port_error(self, mock_service, client):
        """测试检测端口时发生错误"""
        mock_service.check_port.side_effect = Exception("detection failed")

        response = client.get("/api/port/check?port=8080")

        assert response.status_code == 500


class TestKillByPort:
    """按端口终止进程API测试"""

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_success(self, mock_service, client):
        """测试成功终止占用端口的进程"""
        mock_service.kill_by_port.return_value = {
            "success": True,
            "message": "已终止端口 8080 上 1 个进程",
            "killed": [{"pid": 1234, "process_name": "node.exe"}],
            "failed": [],
        }

        response = client.post("/api/port/kill-by-port", json={"port": 8080, "force": False})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["killed"]) == 1
        assert data["killed"][0]["pid"] == 1234

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_force(self, mock_service, client):
        """测试强制终止占用端口的进程"""
        mock_service.kill_by_port.return_value = {
            "success": True,
            "message": "已终止端口 3000 上 1 个进程",
            "killed": [{"pid": 5678, "process_name": "python.exe"}],
            "failed": [],
        }

        response = client.post("/api/port/kill-by-port", json={"port": 3000, "force": True})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_service.kill_by_port.assert_called_once_with(3000, True)

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_not_occupied(self, mock_service, client):
        """测试终止未被占用的端口"""
        mock_service.kill_by_port.return_value = {
            "success": False,
            "message": "端口 9999 未被占用",
        }

        response = client.post("/api/port/kill-by-port", json={"port": 9999, "force": False})

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "端口 9999 未被占用"

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_partial_failure(self, mock_service, client):
        """测试部分进程终止失败"""
        mock_service.kill_by_port.return_value = {
            "success": True,
            "message": "已终止端口 8080 上 1 个进程",
            "killed": [{"pid": 1111, "process_name": "app.exe"}],
            "failed": [{"pid": 2222, "process_name": "app2.exe", "error": "拒绝访问"}],
        }

        response = client.post("/api/port/kill-by-port", json={"port": 8080, "force": False})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["killed"]) == 1
        assert len(data["failed"]) == 1

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_all_failed(self, mock_service, client):
        """测试所有进程终止都失败"""
        mock_service.kill_by_port.return_value = {
            "success": False,
            "message": "无法终止端口 8080 上的进程",
            "killed": [],
            "failed": [{"pid": 1234, "process_name": "system.exe", "error": "拒绝访问"}],
        }

        response = client.post("/api/port/kill-by-port", json={"port": 8080, "force": True})

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "无法终止端口 8080 上的进程"

    def test_kill_by_port_invalid_port(self, client):
        """测试无效端口号"""
        response = client.post("/api/port/kill-by-port", json={"port": 0, "force": False})

        assert response.status_code == 422

    def test_kill_by_port_missing_port(self, client):
        """测试缺少port字段"""
        response = client.post("/api/port/kill-by-port", json={"force": False})

        assert response.status_code == 422

    @patch("app.api.routes.port.port_service")
    def test_kill_by_port_error(self, mock_service, client):
        """测试终止进程时发生错误"""
        mock_service.kill_by_port.side_effect = Exception("kill failed")

        response = client.post("/api/port/kill-by-port", json={"port": 8080, "force": False})

        assert response.status_code == 500


class TestKillByPid:
    """按PID终止进程API测试"""

    @patch("app.api.routes.port.port_service")
    def test_kill_by_pid_success(self, mock_service, client):
        """测试成功终止指定PID的进程"""
        mock_service.kill_by_pid.return_value = {
            "success": True,
            "message": "进程 1234 已终止",
            "process_name": "chrome.exe",
        }

        response = client.post("/api/port/kill-by-pid", json={"pid": 1234, "force": False})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["process_name"] == "chrome.exe"

    @patch("app.api.routes.port.port_service")
    def test_kill_by_pid_force(self, mock_service, client):
        """测试强制终止指定PID的进程"""
        mock_service.kill_by_pid.return_value = {
            "success": True,
            "message": "进程 5678 已终止",
            "process_name": "iexplore.exe",
        }

        response = client.post("/api/port/kill-by-pid", json={"pid": 5678, "force": True})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_service.kill_by_pid.assert_called_once_with(5678, True)

    @patch("app.api.routes.port.port_service")
    def test_kill_by_pid_not_found(self, mock_service, client):
        """测试终止不存在的PID"""
        mock_service.kill_by_pid.return_value = {
            "success": False,
            "message": "ERROR: The process \"1234\" not found.",
        }

        response = client.post("/api/port/kill-by-pid", json={"pid": 1234, "force": False})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @patch("app.api.routes.port.port_service")
    def test_kill_by_pid_access_denied(self, mock_service, client):
        """测试终止进程被拒绝"""
        mock_service.kill_by_pid.return_value = {
            "success": False,
            "message": "ERROR: Access is denied.",
        }

        response = client.post("/api/port/kill-by-pid", json={"pid": 4, "force": True})

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_kill_by_pid_invalid_pid_zero(self, client):
        """测试无效PID（0）"""
        response = client.post("/api/port/kill-by-pid", json={"pid": 0, "force": False})

        assert response.status_code == 422

    def test_kill_by_pid_invalid_pid_negative(self, client):
        """测试无效PID（负数）"""
        response = client.post("/api/port/kill-by-pid", json={"pid": -1, "force": False})

        assert response.status_code == 422

    def test_kill_by_pid_missing_pid(self, client):
        """测试缺少pid字段"""
        response = client.post("/api/port/kill-by-pid", json={"force": False})

        assert response.status_code == 422

    @patch("app.api.routes.port.port_service")
    def test_kill_by_pid_error(self, mock_service, client):
        """测试终止进程时发生错误"""
        mock_service.kill_by_pid.side_effect = Exception("unexpected error")

        response = client.post("/api/port/kill-by-pid", json={"pid": 1234, "force": False})

        assert response.status_code == 500


class TestPortRequestValidation:
    """端口请求数据验证测试"""

    def test_kill_port_request_valid(self):
        """测试有效的 KillPortRequest"""
        from app.api.routes.port import KillPortRequest

        req = KillPortRequest(port=8080, force=True)
        assert req.port == 8080
        assert req.force is True

    def test_kill_port_request_default_force(self):
        """测试 KillPortRequest 默认force值"""
        from app.api.routes.port import KillPortRequest

        req = KillPortRequest(port=80)
        assert req.force is False

    def test_kill_port_request_invalid_port(self):
        """测试无效的 KillPortRequest 端口"""
        from app.api.routes.port import KillPortRequest

        with pytest.raises(Exception):
            KillPortRequest(port=0)

    def test_kill_pid_request_valid(self):
        """测试有效的 KillPidRequest"""
        from app.api.routes.port import KillPidRequest

        req = KillPidRequest(pid=1234, force=False)
        assert req.pid == 1234
        assert req.force is False

    def test_kill_pid_request_invalid_pid(self):
        """测试无效的 KillPidRequest PID"""
        from app.api.routes.port import KillPidRequest

        with pytest.raises(Exception):
            KillPidRequest(pid=0)
