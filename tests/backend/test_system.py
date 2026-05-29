"""系统管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSystemInfo:
    """系统信息接口测试"""

    @patch("app.api.routes.system.system_service")
    def test_get_system_info(self, mock_system_service, client):
        mock_system_service.get_system_info.return_value = {
            "hostname": "server-01",
            "os": "CentOS Linux 7",
            "kernel": "3.10.0-1160.el7.x86_64",
            "uptime": "10 days, 5:30",
            "cpu_model": "Intel Xeon E5-2680 v4",
            "cpu_cores": 8,
            "memory_total_gb": 32,
        }

        response = client.get("/api/system/info?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "hostname" in data
        assert "os" in data

    @patch("app.api.routes.system.system_service")
    def test_get_performance(self, mock_system_service, client):
        mock_system_service.get_performance.return_value = {
            "cpu_usage_percent": 45.2,
            "memory_usage_percent": 62.5,
            "load_average": [1.5, 2.0, 1.8],
        }

        response = client.get("/api/system/performance?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_usage_percent" in data

    @patch("app.api.routes.system.system_service")
    def test_get_disks(self, mock_system_service, client):
        mock_system_service.get_disks_detail.return_value = [
            {"device": "/dev/sda1", "mount": "/", "total_gb": 100, "used_gb": 45, "usage_percent": 45.0},
            {"device": "/dev/sdb1", "mount": "/data", "total_gb": 500, "used_gb": 200, "usage_percent": 40.0},
        ]

        response = client.get("/api/system/disks?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "disks" in data
        assert len(data["disks"]) == 2


class TestSystemOperations:
    """系统操作接口测试"""

    @patch("app.api.routes.system.system_service")
    def test_reboot_system(self, mock_system_service, client):
        mock_system_service.reboot.return_value = "系统重启指令已发送"

        response = client.post("/api/system/reboot?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "重启" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_shutdown_system(self, mock_system_service, client):
        mock_system_service.shutdown.return_value = "关机指令已发送"

        response = client.post("/api/system/shutdown?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "关机" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_reload_network(self, mock_system_service, client):
        mock_system_service.reload_network.return_value = "网络已重启"

        response = client.post("/api/system/reload/network?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "网络" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_reload_ssh(self, mock_system_service, client):
        mock_system_service.reload_ssh.return_value = "SSH服务已重启"

        response = client.post("/api/system/reload/ssh?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "SSH" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_clear_cache(self, mock_system_service, client):
        mock_system_service.clear_cache.return_value = "缓存已清理"

        response = client.post("/api/system/cache/clear?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "缓存" in data["message"]


class TestSELinux:
    """SELinux管理测试"""

    @patch("app.api.routes.system.system_service")
    def test_get_selinux_status(self, mock_system_service, client):
        mock_system_service.check_selinux.return_value = {
            "status": "enforcing",
            "mode": "enforcing",
        }

        response = client.get("/api/system/selinux?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enforcing"

    @patch("app.api.routes.system.system_service")
    def test_set_selinux_enforcing(self, mock_system_service, client):
        mock_system_service.set_selinux.return_value = "SELinux已设置为enforcing"

        response = client.post("/api/system/selinux?alias=test-server&mode=enforcing")
        assert response.status_code == 200
        data = response.json()
        assert "enforcing" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_set_selinux_permissive(self, mock_system_service, client):
        mock_system_service.set_selinux.return_value = "SELinux已设置为permissive"

        response = client.post("/api/system/selinux?alias=test-server&mode=permissive")
        assert response.status_code == 200


class TestFirewall:
    """防火墙管理测试"""

    @patch("app.api.routes.system.system_service")
    def test_get_firewall_status(self, mock_system_service, client):
        mock_system_service.get_firewall_status.return_value = {
            "status": "active",
            "enabled": True,
        }

        response = client.get("/api/system/firewall/status?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    @patch("app.api.routes.system.system_service")
    def test_enable_firewall(self, mock_system_service, client):
        mock_system_service.set_firewall.return_value = "防火墙已开启"

        response = client.post("/api/system/firewall/set?alias=test-server&enable=true")
        assert response.status_code == 200
        data = response.json()
        assert "开启" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_disable_firewall(self, mock_system_service, client):
        mock_system_service.set_firewall.return_value = "防火墙已关闭"

        response = client.post("/api/system/firewall/set?alias=test-server&enable=false")
        assert response.status_code == 200
        data = response.json()
        assert "关闭" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_list_firewall_rules(self, mock_system_service, client):
        mock_system_service.list_firewall_rules.return_value = [
            {"port": 80, "protocol": "tcp", "zone": "public"},
            {"port": 443, "protocol": "tcp", "zone": "public"},
        ]

        response = client.get("/api/system/firewall/rules?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert len(data["rules"]) == 2

    @patch("app.api.routes.system.system_service")
    def test_list_firewall_zones(self, mock_system_service, client):
        mock_system_service.get_firewall_zones.return_value = ["public", "internal", "trusted"]

        response = client.get("/api/system/firewall/zones?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "zones" in data
        assert len(data["zones"]) == 3

    @patch("app.api.routes.system.system_service")
    def test_add_port_rule(self, mock_system_service, client):
        mock_system_service.add_port_rule.return_value = "端口规则已添加"

        response = client.post(
            "/api/system/firewall/port?alias=test-server&port=8080&protocol=tcp&zone=public"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已添加" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_remove_port_rule(self, mock_system_service, client):
        mock_system_service.remove_port_rule.return_value = "端口规则已删除"

        response = client.delete(
            "/api/system/firewall/port?alias=test-server&port=8080&protocol=tcp&zone=public"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.system.system_service")
    def test_add_service_rule(self, mock_system_service, client):
        mock_system_service.add_service_rule.return_value = "服务规则已添加"

        response = client.post(
            "/api/system/firewall/service?alias=test-server&service=http&zone=public"
        )
        assert response.status_code == 200

    @patch("app.api.routes.system.system_service")
    def test_remove_service_rule(self, mock_system_service, client):
        mock_system_service.remove_service_rule.return_value = "服务规则已删除"

        response = client.delete(
            "/api/system/firewall/service?alias=test-server&service=http&zone=public"
        )
        assert response.status_code == 200


class TestSystemErrors:
    """系统接口错误处理测试"""

    @patch("app.api.routes.system.system_service")
    def test_system_info_account_not_found(self, mock_system_service, client):
        mock_system_service.get_system_info.side_effect = ValueError("SSH 账户不存在")

        response = client.get("/api/system/info?alias=nonexistent")
        assert response.status_code == 404
