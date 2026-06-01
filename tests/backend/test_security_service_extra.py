from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.security_service import SecurityService


@pytest.fixture
def service():
    return SecurityService()


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.manager.exec_command.return_value = (0, "output", "")
    return conn


@pytest.fixture
def mock_ssh(mock_conn):
    with patch("app.services.security_service.ssh_account_service") as mock_ssh_svc:
        mock_ssh_svc.get_account.return_value = MagicMock()
        mock_ssh_svc.pool.get_connection.return_value = mock_conn
        yield mock_ssh_svc


class TestRemovePortRuleUfw:
    def test_ufw_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_port_rule("server1", 8080, "tcp")
            assert "ufw" in result
            assert "删除" in result

    def test_ufw_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (1, "", "ufw error")
            result = service.remove_port_rule("server1", 8080, "tcp")
            assert "失败" in result


class TestRemovePortRuleIptables:
    def test_iptables_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_port_rule("server1", 8080, "tcp")
            assert "iptables" in result
            assert "删除" in result

    def test_iptables_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (1, "", "iptables error")
            result = service.remove_port_rule("server1", 8080, "tcp")
            assert "失败" in result


class TestRemovePortRuleUnknown:
    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            result = service.remove_port_rule("server1", 8080)
            assert "未检测到" in result


class TestListIpRules:
    def test_firewalld_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, 'rule family="ipv4" source address="1.2.3.4" accept\nrule family="ipv4" source address="5.6.7.8" reject', "")
            rules = service.list_ip_rules("server1")
            assert len(rules) == 2
            assert rules[0]["backend"] == "firewalld"
            assert "raw" in rules[0]

    def test_firewalld_empty(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            rules = service.list_ip_rules("server1")
            assert rules == []

    def test_firewalld_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (1, "", "error")
            rules = service.list_ip_rules("server1")
            assert rules == []

    def test_ufw_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "Status: active\nTo           Action      From\n1.2.3.4      ALLOW       Anywhere\n5.6.7.8      DENY        Anywhere", "")
            rules = service.list_ip_rules("server1")
            assert len(rules) == 2
            assert all(r["backend"] == "ufw" for r in rules)

    def test_ufw_mixed_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "Status: active\nTo           Action      From\n1.2.3.4      ALLOW       Anywhere\n80/tcp       ALLOW       Anywhere", "")
            rules = service.list_ip_rules("server1")
            assert len(rules) == 2

    def test_ufw_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (1, "", "error")
            rules = service.list_ip_rules("server1")
            assert rules == []

    def test_iptables_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "Chain INPUT (policy ACCEPT)\nnum  target     prot opt source       destination\n1    ACCEPT     all  --  1.2.3.4      0.0.0.0/0    source:1.2.3.4\n2    DROP       all  --  5.6.7.8      0.0.0.0/0    source:5.6.7.8", "")
            rules = service.list_ip_rules("server1")
            assert len(rules) == 2
            assert all(r["backend"] == "iptables" for r in rules)

    def test_iptables_no_ip_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "Chain INPUT (policy ACCEPT)\nnum  target     prot opt source       destination\n1    ACCEPT     tcp  --  0.0.0.0/0    dpt: 80", "")
            rules = service.list_ip_rules("server1")
            assert rules == []

    def test_iptables_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (1, "", "error")
            rules = service.list_ip_rules("server1")
            assert rules == []

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            rules = service.list_ip_rules("server1")
            assert rules == []


class TestAllowIpExtra:
    def test_ufw_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "ufw" in result
            assert "1.2.3.4" in result

    def test_ufw_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (1, "", "ufw error")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_iptables_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "iptables" in result
            assert "1.2.3.4" in result

    def test_iptables_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (1, "", "iptables error")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_firewalld_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (1, "", "firewalld error")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            result = service.allow_ip("server1", "1.2.3.4")
            assert "未检测到" in result


class TestDenyIpExtra:
    def test_firewalld_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "firewalld" in result
            assert "1.2.3.4" in result

    def test_firewalld_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (1, "", "firewalld error")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_ufw_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "ufw" in result
            assert "1.2.3.4" in result

    def test_ufw_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (1, "", "ufw error")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_iptables_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "iptables" in result
            assert "1.2.3.4" in result

    def test_iptables_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (1, "", "iptables error")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "失败" in result

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            result = service.deny_ip("server1", "1.2.3.4")
            assert "未检测到" in result


class TestRemoveIpRuleExtra:
    def test_ufw_allow_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "ufw" in result
            assert "删除" in result

    def test_ufw_deny_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_ip_rule("server1", "1.2.3.4", "deny")
            assert "ufw" in result

    def test_ufw_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (1, "", "ufw error")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "失败" in result

    def test_iptables_allow_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "iptables" in result
            assert "删除" in result

    def test_iptables_deny_success(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_ip_rule("server1", "1.2.3.4", "deny")
            assert "iptables" in result

    def test_iptables_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (1, "", "iptables error")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "失败" in result

    def test_firewalld_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (1, "", "error")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "失败" in result

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "未检测到" in result


class TestGetSshConfigExtra:
    def test_port_index_error(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Port", "")
        result = service.get_ssh_config("server1")
        assert result["port"] == 22

    def test_port_value_error(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Port abc", "")
        result = service.get_ssh_config("server1")
        assert result["port"] == 22

    def test_password_auth_no(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "PasswordAuthentication no", "")
        result = service.get_ssh_config("server1")
        assert result["password_auth"] is False

    def test_root_login_no(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "PermitRootLogin no", "")
        result = service.get_ssh_config("server1")
        assert result["root_login"] is False

    def test_pubkey_auth_no(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "PubkeyAuthentication no", "")
        result = service.get_ssh_config("server1")
        assert result["pubkey_auth"] is False


class TestSetSshPortExtra:
    def test_set_port_success_replace(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "Port 22\nPasswordAuthentication yes", ""),
            (0, "", ""),
        ]
        with patch.object(service, "restart_sshd", return_value="SSH 服务已重启"), \
             patch.object(service, "add_port_rule", return_value="端口 2222/tcp 已添加"):
            result = service.set_ssh_port("server1", 2222)
            assert "2222" in result

    def test_set_port_success_append(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "PasswordAuthentication yes", ""),
            (0, "", ""),
        ]
        with patch.object(service, "restart_sshd", return_value="SSH 服务已重启"), \
             patch.object(service, "add_port_rule", return_value="端口 2222/tcp 已添加"):
            result = service.set_ssh_port("server1", 2222)
            assert "2222" in result

    def test_set_port_write_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "Port 22", ""),
            (1, "", "write error"),
        ]
        result = service.set_ssh_port("server1", 2222)
        assert "失败" in result

    def test_set_port_boundary_low(self, service, mock_ssh, mock_conn):
        result = service.set_ssh_port("server1", 0)
        assert "无效" in result

    def test_set_port_boundary_high(self, service, mock_ssh, mock_conn):
        result = service.set_ssh_port("server1", 70000)
        assert "无效" in result

    def test_set_port_valid_boundary(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "Port 22", ""),
            (0, "", ""),
        ]
        with patch.object(service, "restart_sshd", return_value="SSH 服务已重启"), \
             patch.object(service, "add_port_rule", return_value="端口 1/tcp 已添加"):
            result = service.set_ssh_port("server1", 1)
            assert "1" in result
