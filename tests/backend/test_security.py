"""安全API路由测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ==================== 防火墙模块测试 ====================


class TestFirewallBackend:
    """防火墙后端检测测试"""

    @patch("app.api.routes.security.security_service")
    def test_detect_firewall_backend_success(self, mock_service, client):
        mock_service.detect_firewall_backend.return_value = {"backend": "firewalld", "running": True}
        response = client.get("/api/security/firewall/backend?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "firewalld"
        assert data["running"] is True

    @patch("app.api.routes.security.security_service")
    def test_detect_firewall_backend_ufw(self, mock_service, client):
        mock_service.detect_firewall_backend.return_value = {"backend": "ufw", "running": True}
        response = client.get("/api/security/firewall/backend?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "ufw"

    @patch("app.api.routes.security.security_service")
    def test_detect_firewall_backend_unknown(self, mock_service, client):
        mock_service.detect_firewall_backend.return_value = {"backend": "unknown", "running": False}
        response = client.get("/api/security/firewall/backend?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "unknown"

    @patch("app.api.routes.security.security_service")
    def test_detect_firewall_backend_account_not_found(self, mock_service, client):
        mock_service.detect_firewall_backend.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/firewall/backend?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_detect_firewall_backend_internal_error(self, mock_service, client):
        mock_service.detect_firewall_backend.side_effect = Exception("连接超时")
        response = client.get("/api/security/firewall/backend?alias=test-server")
        assert response.status_code == 500

    def test_detect_firewall_backend_missing_alias(self, client):
        response = client.get("/api/security/firewall/backend")
        assert response.status_code == 422


class TestFirewallRules:
    """防火墙规则管理测试"""

    @patch("app.api.routes.security.security_service")
    def test_list_firewall_rules_success(self, mock_service, client):
        mock_service.list_all_rules.return_value = [
            {"port": "22", "protocol": "tcp", "backend": "firewalld"},
            {"port": "80", "protocol": "tcp", "backend": "firewalld"},
        ]
        response = client.get("/api/security/firewall/rules?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) == 2
        assert data["rules"][0]["port"] == "22"

    @patch("app.api.routes.security.security_service")
    def test_list_firewall_rules_empty(self, mock_service, client):
        mock_service.list_all_rules.return_value = []
        response = client.get("/api/security/firewall/rules?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["rules"] == []

    @patch("app.api.routes.security.security_service")
    def test_list_firewall_rules_account_not_found(self, mock_service, client):
        mock_service.list_all_rules.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/firewall/rules?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_list_firewall_rules_internal_error(self, mock_service, client):
        mock_service.list_all_rules.side_effect = Exception("执行失败")
        response = client.get("/api/security/firewall/rules?alias=test-server")
        assert response.status_code == 500


class TestFirewallPort:
    """防火墙端口规则测试"""

    @patch("app.api.routes.security.security_service")
    def test_add_port_rule_success(self, mock_service, client):
        mock_service.add_port_rule.return_value = "端口 8080/tcp 已添加到 public 区域（永久）"
        response = client.post("/api/security/firewall/port?alias=test-server&port=8080&protocol=tcp&zone=public")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "8080" in data["message"]

    @patch("app.api.routes.security.security_service")
    def test_add_port_rule_account_not_found(self, mock_service, client):
        mock_service.add_port_rule.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/firewall/port?alias=nonexistent&port=8080&protocol=tcp&zone=public")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_add_port_rule_internal_error(self, mock_service, client):
        mock_service.add_port_rule.side_effect = Exception("执行命令失败")
        response = client.post("/api/security/firewall/port?alias=test-server&port=8080")
        assert response.status_code == 500

    @patch("app.api.routes.security.security_service")
    def test_remove_port_rule_success(self, mock_service, client):
        mock_service.remove_port_rule.return_value = "端口 8080/tcp 已从 public 区域删除"
        response = client.delete("/api/security/firewall/port?alias=test-server&port=8080&protocol=tcp&zone=public")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_remove_port_rule_account_not_found(self, mock_service, client):
        mock_service.remove_port_rule.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.delete("/api/security/firewall/port?alias=nonexistent&port=8080")
        assert response.status_code == 404

    def test_add_port_rule_invalid_port(self, client):
        response = client.post("/api/security/firewall/port?alias=test-server&port=invalid&protocol=tcp")
        assert response.status_code == 422

    def test_add_port_rule_missing_required_params(self, client):
        response = client.post("/api/security/firewall/port?alias=test-server")
        assert response.status_code == 422


class TestFirewallIP:
    """防火墙IP规则测试"""

    @patch("app.api.routes.security.security_service")
    def test_add_ip_rule_allow(self, mock_service, client):
        mock_service.add_ip_rule.return_value = "IP 192.168.1.1 已允许（firewalld rich rule）"
        response = client.post("/api/security/firewall/ip?alias=test-server&ip=192.168.1.1&action=allow&zone=public")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_add_ip_rule_deny(self, mock_service, client):
        mock_service.add_ip_rule.return_value = "IP 10.0.0.1 已拒绝（firewalld rich rule）"
        response = client.post("/api/security/firewall/ip?alias=test-server&ip=10.0.0.1&action=deny&zone=public")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_add_ip_rule_account_not_found(self, mock_service, client):
        mock_service.add_ip_rule.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/firewall/ip?alias=nonexistent&ip=192.168.1.1")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_add_ip_rule_internal_error(self, mock_service, client):
        mock_service.add_ip_rule.side_effect = Exception("执行失败")
        response = client.post("/api/security/firewall/ip?alias=test-server&ip=192.168.1.1")
        assert response.status_code == 500

    @patch("app.api.routes.security.security_service")
    def test_remove_ip_rule_success(self, mock_service, client):
        mock_service.remove_ip_rule.return_value = "IP 192.168.1.1 的 rich rule 已删除"
        response = client.delete("/api/security/firewall/ip?alias=test-server&ip=192.168.1.1&zone=public")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_remove_ip_rule_account_not_found(self, mock_service, client):
        mock_service.remove_ip_rule.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.delete("/api/security/firewall/ip?alias=nonexistent&ip=192.168.1.1")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_remove_ip_rule_internal_error(self, mock_service, client):
        mock_service.remove_ip_rule.side_effect = Exception("执行失败")
        response = client.delete("/api/security/firewall/ip?alias=test-server&ip=192.168.1.1")
        assert response.status_code == 500

    def test_add_ip_rule_missing_ip(self, client):
        response = client.post("/api/security/firewall/ip?alias=test-server")
        assert response.status_code == 422


# ==================== SSH 管理模块测试 ====================


class TestSSHConfig:
    """SSH配置管理测试"""

    @patch("app.api.routes.security.security_service")
    def test_get_ssh_config_success(self, mock_service, client):
        mock_service.get_ssh_config.return_value = {
            "port": 22,
            "password_auth": True,
            "root_login": True,
            "pubkey_auth": True,
            "raw": "Port 22\nPasswordAuthentication yes",
        }
        response = client.get("/api/security/ssh/config?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 22
        assert data["password_auth"] is True

    @patch("app.api.routes.security.security_service")
    def test_get_ssh_config_custom_port(self, mock_service, client):
        mock_service.get_ssh_config.return_value = {
            "port": 2222,
            "password_auth": False,
            "root_login": False,
            "pubkey_auth": True,
            "raw": "Port 2222\nPasswordAuthentication no",
        }
        response = client.get("/api/security/ssh/config?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 2222
        assert data["password_auth"] is False

    @patch("app.api.routes.security.security_service")
    def test_get_ssh_config_account_not_found(self, mock_service, client):
        mock_service.get_ssh_config.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/ssh/config?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_get_ssh_config_internal_error(self, mock_service, client):
        mock_service.get_ssh_config.side_effect = Exception("执行失败")
        response = client.get("/api/security/ssh/config?alias=test-server")
        assert response.status_code == 500


class TestSSHPort:
    """SSH端口修改测试"""

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_port_success(self, mock_service, client):
        mock_service.set_ssh_port.return_value = "SSH 端口已修改为 2222。SSH 服务已重启；防火墙: 端口 2222/tcp 已添加到 public 区域（永久）"
        response = client.post("/api/security/ssh/port?alias=test-server&port=2222")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "2222" in data["message"]

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_port_account_not_found(self, mock_service, client):
        mock_service.set_ssh_port.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/ssh/port?alias=nonexistent&port=2222")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_port_internal_error(self, mock_service, client):
        mock_service.set_ssh_port.side_effect = Exception("执行失败")
        response = client.post("/api/security/ssh/port?alias=test-server&port=2222")
        assert response.status_code == 500

    def test_set_ssh_port_invalid_port(self, client):
        response = client.post("/api/security/ssh/port?alias=test-server&port=invalid")
        assert response.status_code == 422

    def test_set_ssh_port_missing_port(self, client):
        response = client.post("/api/security/ssh/port?alias=test-server")
        assert response.status_code == 422

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_port_invalid_range(self, mock_service, client):
        mock_service.set_ssh_port.return_value = "无效端口: 99999"
        response = client.post("/api/security/ssh/port?alias=test-server&port=99999")
        assert response.status_code == 200
        data = response.json()
        assert "无效端口" in data["message"]


class TestSSHPasswordAuth:
    """SSH密码认证开关测试"""

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_password_auth_enable(self, mock_service, client):
        mock_service.set_ssh_password_auth.return_value = "PasswordAuthentication 已设置为 yes。SSH 服务已重启"
        response = client.post("/api/security/ssh/password-auth?alias=test-server&enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_password_auth_disable(self, mock_service, client):
        mock_service.set_ssh_password_auth.return_value = "PasswordAuthentication 已设置为 no。SSH 服务已重启"
        response = client.post("/api/security/ssh/password-auth?alias=test-server&enabled=false")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_password_auth_account_not_found(self, mock_service, client):
        mock_service.set_ssh_password_auth.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/ssh/password-auth?alias=nonexistent&enabled=true")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_set_ssh_password_auth_internal_error(self, mock_service, client):
        mock_service.set_ssh_password_auth.side_effect = Exception("执行失败")
        response = client.post("/api/security/ssh/password-auth?alias=test-server&enabled=true")
        assert response.status_code == 500

    def test_set_ssh_password_auth_missing_enabled(self, client):
        response = client.post("/api/security/ssh/password-auth?alias=test-server")
        assert response.status_code == 422

    def test_set_ssh_password_auth_invalid_enabled(self, client):
        response = client.post("/api/security/ssh/password-auth?alias=test-server&enabled=invalid")
        assert response.status_code == 422


class TestSSHKeys:
    """SSH密钥管理测试"""

    @patch("app.api.routes.security.security_service")
    def test_list_authorized_keys_success(self, mock_service, client):
        mock_service.list_authorized_keys.return_value = [
            {
                "index": 1,
                "type": "ssh-rsa",
                "fingerprint": "SHA256:abcdef123456",
                "comment": "user@host",
                "raw": "ssh-rsa AAAA...",
            },
        ]
        response = client.get("/api/security/ssh/keys?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) == 1
        assert data["keys"][0]["type"] == "ssh-rsa"

    @patch("app.api.routes.security.security_service")
    def test_list_authorized_keys_empty(self, mock_service, client):
        mock_service.list_authorized_keys.return_value = []
        response = client.get("/api/security/ssh/keys?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["keys"] == []

    @patch("app.api.routes.security.security_service")
    def test_list_authorized_keys_account_not_found(self, mock_service, client):
        mock_service.list_authorized_keys.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/ssh/keys?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_add_authorized_key_success(self, mock_service, client):
        mock_service.add_authorized_key.return_value = "公钥已添加"
        response = client.post("/api/security/ssh/keys?alias=test-server&public_key=ssh-rsa%20AAAA...%20user@host")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_add_authorized_key_account_not_found(self, mock_service, client):
        mock_service.add_authorized_key.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/ssh/keys?alias=nonexistent&public_key=ssh-rsa%20AAAA...")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_add_authorized_key_internal_error(self, mock_service, client):
        mock_service.add_authorized_key.side_effect = Exception("执行失败")
        response = client.post("/api/security/ssh/keys?alias=test-server&public_key=ssh-rsa%20AAAA...")
        assert response.status_code == 500

    def test_add_authorized_key_missing_public_key(self, client):
        response = client.post("/api/security/ssh/keys?alias=test-server")
        assert response.status_code == 422

    @patch("app.api.routes.security.security_service")
    def test_remove_authorized_key_by_fingerprint(self, mock_service, client):
        mock_service.remove_authorized_key.return_value = "公钥已删除"
        response = client.delete(
            "/api/security/ssh/keys?alias=test-server&fingerprint=SHA256:abcdef123456"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_remove_authorized_key_by_comment(self, mock_service, client):
        mock_service.remove_authorized_key.return_value = "公钥已删除"
        response = client.delete(
            "/api/security/ssh/keys?alias=test-server&comment=user@host"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_remove_authorized_key_not_found(self, mock_service, client):
        mock_service.remove_authorized_key.return_value = "未找到匹配的公钥"
        response = client.delete(
            "/api/security/ssh/keys?alias=test-server&fingerprint=nonexistent"
        )
        assert response.status_code == 200
        data = response.json()
        assert "未找到" in data["message"]

    @patch("app.api.routes.security.security_service")
    def test_remove_authorized_key_account_not_found(self, mock_service, client):
        mock_service.remove_authorized_key.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.delete("/api/security/ssh/keys?alias=nonexistent")
        assert response.status_code == 404


class TestSSHKeyGeneration:
    """SSH密钥生成测试"""

    @patch("app.api.routes.security.security_service")
    def test_generate_key_ed25519(self, mock_service, client):
        mock_service.generate_key_pair.return_value = {
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
            "public_key": "ssh-ed25519 AAAA... user@host",
        }
        response = client.post("/api/security/ssh/keys/generate?alias=test-server&key_type=ed25519&comment=test-key")
        assert response.status_code == 200
        data = response.json()
        assert "private_key" in data
        assert "public_key" in data

    @patch("app.api.routes.security.security_service")
    def test_generate_key_rsa(self, mock_service, client):
        mock_service.generate_key_pair.return_value = {
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
            "public_key": "ssh-rsa AAAA... user@host",
        }
        response = client.post(
            "/api/security/ssh/keys/generate?alias=test-server&key_type=rsa&bits=4096&comment=test-rsa-key"
        )
        assert response.status_code == 200
        data = response.json()
        assert "private_key" in data
        assert "public_key" in data

    @patch("app.api.routes.security.security_service")
    def test_generate_key_unsupported_type(self, mock_service, client):
        mock_service.generate_key_pair.return_value = {"error": "仅支持 rsa 或 ed25519"}
        response = client.post(
            "/api/security/ssh/keys/generate?alias=test-server&key_type=dsa"
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    @patch("app.api.routes.security.security_service")
    def test_generate_key_account_not_found(self, mock_service, client):
        mock_service.generate_key_pair.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/ssh/keys/generate?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_generate_key_internal_error(self, mock_service, client):
        mock_service.generate_key_pair.side_effect = Exception("执行失败")
        response = client.post("/api/security/ssh/keys/generate?alias=test-server")
        assert response.status_code == 500


# ==================== 审计模块测试 ====================


class TestAuditLoginLogs:
    """审计登录日志测试"""

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_success(self, mock_service, client):
        mock_service.get_login_logs.return_value = [
            {
                "timestamp": "May 29 10:15:01",
                "ip": "192.168.1.100",
                "user": "admin",
                "status": "accepted",
                "message": "Accepted password for admin",
            },
            {
                "timestamp": "May 29 10:16:05",
                "ip": "10.0.0.1",
                "user": "root",
                "status": "failed",
                "message": "Failed password for root",
            },
        ]
        response = client.get("/api/security/audit/login-logs?alias=test-server&limit=100")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 2

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_empty(self, mock_service, client):
        mock_service.get_login_logs.return_value = []
        response = client.get("/api/security/audit/login-logs?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_with_user_filter(self, mock_service, client):
        mock_service.get_login_logs.return_value = [
            {
                "timestamp": "May 29 10:15:01",
                "ip": "192.168.1.100",
                "user": "admin",
                "status": "accepted",
                "message": "Accepted password for admin",
            },
        ]
        response = client.get("/api/security/audit/login-logs?alias=test-server&user=admin")
        assert response.status_code == 200
        data = response.json()
        assert data["logs"][0]["user"] == "admin"
        mock_service.get_login_logs.assert_called_once_with("test-server", 100, "admin", False)

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_failed_only(self, mock_service, client):
        mock_service.get_login_logs.return_value = [
            {
                "timestamp": "May 29 10:16:05",
                "ip": "10.0.0.1",
                "user": "root",
                "status": "failed",
                "message": "Failed password for root",
            },
        ]
        response = client.get("/api/security/audit/login-logs?alias=test-server&failed_only=true")
        assert response.status_code == 200
        data = response.json()
        assert all(log["status"] != "accepted" for log in data["logs"])
        mock_service.get_login_logs.assert_called_once_with("test-server", 100, "", True)

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_account_not_found(self, mock_service, client):
        mock_service.get_login_logs.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/audit/login-logs?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_get_login_logs_internal_error(self, mock_service, client):
        mock_service.get_login_logs.side_effect = Exception("执行失败")
        response = client.get("/api/security/audit/login-logs?alias=test-server")
        assert response.status_code == 500


class TestAuditFail2Ban:
    """审计fail2ban状态测试"""

    @patch("app.api.routes.security.security_service")
    def test_get_fail2ban_status_active(self, mock_service, client):
        mock_service.get_fail2ban_status.return_value = {
            "installed": True,
            "active": True,
            "jails": ["sshd", "apache-auth"],
            "banned_ips": [
                {"jail": "sshd", "ip": "10.0.0.1"},
                {"jail": "sshd", "ip": "10.0.0.2"},
            ],
        }
        response = client.get("/api/security/audit/fail2ban?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["active"] is True
        assert len(data["jails"]) == 2
        assert len(data["banned_ips"]) == 2

    @patch("app.api.routes.security.security_service")
    def test_get_fail2ban_status_not_installed(self, mock_service, client):
        mock_service.get_fail2ban_status.return_value = {
            "installed": False,
            "active": False,
            "jails": [],
            "banned_ips": [],
        }
        response = client.get("/api/security/audit/fail2ban?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False

    @patch("app.api.routes.security.security_service")
    def test_get_fail2ban_status_account_not_found(self, mock_service, client):
        mock_service.get_fail2ban_status.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/audit/fail2ban?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_get_fail2ban_status_internal_error(self, mock_service, client):
        mock_service.get_fail2ban_status.side_effect = Exception("执行失败")
        response = client.get("/api/security/audit/fail2ban?alias=test-server")
        assert response.status_code == 500


class TestAuditFail2BanUnban:
    """审计fail2ban解封测试"""

    @patch("app.api.routes.security.security_service")
    def test_unban_ip_with_jail(self, mock_service, client):
        mock_service.unban_ip.return_value = "IP 10.0.0.1 已从 sshd 解封"
        response = client.post("/api/security/audit/fail2ban/unban?alias=test-server&ip=10.0.0.1&jail=sshd")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "10.0.0.1" in data["message"]

    @patch("app.api.routes.security.security_service")
    def test_unban_ip_without_jail(self, mock_service, client):
        mock_service.unban_ip.return_value = "IP 10.0.0.1 已从 sshd 解封"
        response = client.post("/api/security/audit/fail2ban/unban?alias=test-server&ip=10.0.0.1")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.security.security_service")
    def test_unban_ip_not_found(self, mock_service, client):
        mock_service.unban_ip.return_value = "解封失败: 未找到包含该 IP 的 jail"
        response = client.post("/api/security/audit/fail2ban/unban?alias=test-server&ip=10.0.0.99")
        assert response.status_code == 200
        data = response.json()
        assert "解封失败" in data["message"]

    @patch("app.api.routes.security.security_service")
    def test_unban_ip_account_not_found(self, mock_service, client):
        mock_service.unban_ip.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/audit/fail2ban/unban?alias=nonexistent&ip=10.0.0.1")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_unban_ip_internal_error(self, mock_service, client):
        mock_service.unban_ip.side_effect = Exception("执行失败")
        response = client.post("/api/security/audit/fail2ban/unban?alias=test-server&ip=10.0.0.1")
        assert response.status_code == 500

    def test_unban_ip_missing_ip(self, client):
        response = client.post("/api/security/audit/fail2ban/unban?alias=test-server")
        assert response.status_code == 422


class TestAuditOpsLogs:
    """审计操作日志测试"""

    @patch("app.api.routes.security.security_service")
    def test_get_ops_logs_success(self, mock_service, client):
        mock_service.get_ops_logs.return_value = [
            {"timestamp": "2024-01-01 12:00:00", "action": "restart_service", "user": "admin"},
        ]
        response = client.get("/api/security/audit/ops-logs?alias=test-server&limit=100")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    @patch("app.api.routes.security.security_service")
    def test_get_ops_logs_empty(self, mock_service, client):
        mock_service.get_ops_logs.return_value = []
        response = client.get("/api/security/audit/ops-logs?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []

    @patch("app.api.routes.security.security_service")
    def test_get_ops_logs_with_action_filter(self, mock_service, client):
        mock_service.get_ops_logs.return_value = []
        response = client.get("/api/security/audit/ops-logs?alias=test-server&action=restart_service")
        assert response.status_code == 200
        mock_service.get_ops_logs.assert_called_once_with("test-server", 100, "restart_service")

    @patch("app.api.routes.security.security_service")
    def test_get_ops_logs_account_not_found(self, mock_service, client):
        mock_service.get_ops_logs.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.get("/api/security/audit/ops-logs?alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_get_ops_logs_internal_error(self, mock_service, client):
        mock_service.get_ops_logs.side_effect = Exception("执行失败")
        response = client.get("/api/security/audit/ops-logs?alias=test-server")
        assert response.status_code == 500


# ==================== 网络诊断模块测试 ====================


class TestNetworkPing:
    """网络ping测试"""

    @patch("app.api.routes.security.security_service")
    def test_ping_success(self, mock_service, client):
        mock_service.run_ping.return_value = {
            "code": 0,
            "output": "PING 8.8.8.8 (8.8.8.8): 56 data bytes\n4 packets transmitted, 4 received, 0% packet loss",
            "error": "",
        }
        response = client.post("/api/security/network/ping?alias=test-server&host=8.8.8.8&count=4")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "8.8.8.8" in data["output"]

    @patch("app.api.routes.security.security_service")
    def test_ping_failure(self, mock_service, client):
        mock_service.run_ping.return_value = {
            "code": 1,
            "output": "",
            "error": "ping: unknown host nonexistent.example.com",
        }
        response = client.post("/api/security/network/ping?alias=test-server&host=nonexistent.example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1

    @patch("app.api.routes.security.security_service")
    def test_ping_account_not_found(self, mock_service, client):
        mock_service.run_ping.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/network/ping?alias=nonexistent&host=8.8.8.8")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_ping_internal_error(self, mock_service, client):
        mock_service.run_ping.side_effect = Exception("执行失败")
        response = client.post("/api/security/network/ping?alias=test-server&host=8.8.8.8")
        assert response.status_code == 500

    @patch("app.api.routes.security.security_service")
    def test_ping_default_count(self, mock_service, client):
        mock_service.run_ping.return_value = {"code": 0, "output": "ping output", "error": ""}
        response = client.post("/api/security/network/ping?alias=test-server&host=8.8.8.8")
        assert response.status_code == 200
        mock_service.run_ping.assert_called_once_with("test-server", "8.8.8.8", 4)

    def test_ping_missing_host(self, client):
        response = client.post("/api/security/network/ping?alias=test-server")
        assert response.status_code == 422


class TestNetworkTraceroute:
    """网络traceroute测试"""

    @patch("app.api.routes.security.security_service")
    def test_traceroute_success(self, mock_service, client):
        mock_service.run_traceroute.return_value = {
            "code": 0,
            "output": "traceroute to 8.8.8.8 (8.8.8.8), 30 hops max\n1  192.168.1.1  1.234 ms\n2  10.0.0.1  5.678 ms\n3  8.8.8.8  10.123 ms",
            "error": "",
        }
        response = client.post("/api/security/network/traceroute?alias=test-server&host=8.8.8.8&max_hops=30")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "8.8.8.8" in data["output"]

    @patch("app.api.routes.security.security_service")
    def test_traceroute_failure(self, mock_service, client):
        mock_service.run_traceroute.return_value = {
            "code": 1,
            "output": "",
            "error": "traceroute: unknown host nonexistent.example.com",
        }
        response = client.post("/api/security/network/traceroute?alias=test-server&host=nonexistent.example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 1

    @patch("app.api.routes.security.security_service")
    def test_traceroute_account_not_found(self, mock_service, client):
        mock_service.run_traceroute.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/network/traceroute?alias=nonexistent&host=8.8.8.8")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_traceroute_internal_error(self, mock_service, client):
        mock_service.run_traceroute.side_effect = Exception("执行失败")
        response = client.post("/api/security/network/traceroute?alias=test-server&host=8.8.8.8")
        assert response.status_code == 500

    @patch("app.api.routes.security.security_service")
    def test_traceroute_custom_max_hops(self, mock_service, client):
        mock_service.run_traceroute.return_value = {"code": 0, "output": "traceroute output", "error": ""}
        response = client.post("/api/security/network/traceroute?alias=test-server&host=8.8.8.8&max_hops=15")
        assert response.status_code == 200
        mock_service.run_traceroute.assert_called_once_with("test-server", "8.8.8.8", 15)

    def test_traceroute_missing_host(self, client):
        response = client.post("/api/security/network/traceroute?alias=test-server")
        assert response.status_code == 422


class TestNetworkPortScan:
    """网络端口扫描测试"""

    @patch("app.api.routes.security.security_service")
    def test_port_scan_success(self, mock_service, client):
        mock_service.run_port_scan.return_value = {
            "code": 0,
            "output": "22/tcp open\n80/tcp open\n443/tcp open",
            "error": "",
        }
        response = client.post("/api/security/network/portscan?alias=test-server&host=192.168.1.1&ports=1-1000")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "22/tcp open" in data["output"]

    @patch("app.api.routes.security.security_service")
    def test_port_scan_mixed_results(self, mock_service, client):
        mock_service.run_port_scan.return_value = {
            "code": 0,
            "output": "22/tcp open\n80/tcp closed\n443/tcp open",
            "error": "",
        }
        response = client.post("/api/security/network/portscan?alias=test-server&host=192.168.1.1")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "22/tcp open" in data["output"]
        assert "80/tcp closed" in data["output"]

    @patch("app.api.routes.security.security_service")
    def test_port_scan_account_not_found(self, mock_service, client):
        mock_service.run_port_scan.side_effect = ValueError("SSH 账户 'nonexistent' 不存在")
        response = client.post("/api/security/network/portscan?alias=nonexistent&host=192.168.1.1")
        assert response.status_code == 404

    @patch("app.api.routes.security.security_service")
    def test_port_scan_internal_error(self, mock_service, client):
        mock_service.run_port_scan.side_effect = Exception("执行失败")
        response = client.post("/api/security/network/portscan?alias=test-server&host=192.168.1.1")
        assert response.status_code == 500

    @patch("app.api.routes.security.security_service")
    def test_port_scan_custom_ports(self, mock_service, client):
        mock_service.run_port_scan.return_value = {
            "code": 0,
            "output": "80/tcp open\n443/tcp open\n8080/tcp open",
            "error": "",
        }
        response = client.post("/api/security/network/portscan?alias=test-server&host=192.168.1.1&ports=80,443,8080")
        assert response.status_code == 200
        mock_service.run_port_scan.assert_called_once_with("test-server", "192.168.1.1", "80,443,8080")

    def test_port_scan_missing_host(self, client):
        response = client.post("/api/security/network/portscan?alias=test-server")
        assert response.status_code == 422
