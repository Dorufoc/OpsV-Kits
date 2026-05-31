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


class TestConn:
    def test_conn_account_not_found(self, service):
        with patch("app.services.security_service.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                service._conn("missing")

    def test_conn_success(self, service, mock_ssh, mock_conn):
        result = service._conn("server1")
        assert result is mock_conn


class TestExec:
    def test_exec_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "err")
        code, stdout, stderr = service._exec("server1", "ls")
        assert code == 0
        assert stdout == "output"

    def test_exec_bytes_stdout(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, b"bytes output", b"bytes err")
        code, stdout, stderr = service._exec("server1", "ls")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    def test_exec_releases_connection(self, service, mock_ssh, mock_conn):
        service._exec("server1", "ls")
        mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)


class TestExecStream:
    def test_exec_stream_yields(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "out", "err")
        results = list(service._exec_stream("server1", "ls"))
        assert len(results) == 1
        assert results[0][0] == 0

    def test_exec_stream_releases(self, service, mock_ssh, mock_conn):
        list(service._exec_stream("server1", "ls"))
        mock_ssh.pool.release_connection.assert_called_once()


class TestDetectFirewallBackend:
    def test_firewalld_running(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/usr/bin/firewall-cmd", ""),
            (0, "running", ""),
        ]
        result = service.detect_firewall_backend("server1")
        assert result["backend"] == "firewalld"
        assert result["running"] is True

    def test_ufw_active(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", ""),  # firewall-cmd not found
            (0, "/usr/sbin/ufw", ""),  # ufw found
            (0, "Status: active", ""),  # ufw status
        ]
        result = service.detect_firewall_backend("server1")
        assert result["backend"] == "ufw"
        assert result["running"] is True

    def test_ufw_inactive(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", ""),
            (0, "/usr/sbin/ufw", ""),
            (0, "Status: inactive", ""),
        ]
        result = service.detect_firewall_backend("server1")
        assert result["backend"] == "ufw"
        assert result["running"] is True

    def test_iptables(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", ""),
            (1, "", ""),
            (0, "/usr/sbin/iptables", ""),
        ]
        result = service.detect_firewall_backend("server1")
        assert result["backend"] == "iptables"

    def test_unknown(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        result = service.detect_firewall_backend("server1")
        assert result["backend"] == "unknown"
        assert result["running"] is False


class TestListAllRules:
    def test_firewalld_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld", "running": True}):
            mock_conn.manager.exec_command.return_value = (0, "  ports: 80/tcp 443/tcp 22/tcp\n  services: ssh", "")
            rules = service.list_all_rules("server1")
            assert len(rules) >= 2
            assert any(r["port"] == "80" for r in rules)

    def test_ufw_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw", "running": True}):
            mock_conn.manager.exec_command.return_value = (0, "Status: active\nTo           Action      From\n80/tcp       ALLOW       Anywhere\n22           ALLOW       Anywhere", "")
            rules = service.list_all_rules("server1")
            assert len(rules) >= 1

    def test_iptables_rules(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables", "running": True}):
            mock_conn.manager.exec_command.return_value = (0, "Chain INPUT (policy ACCEPT)\nnum  target     prot opt source       destination\n1    ACCEPT     tcp  --  0.0.0.0/0    dpt: 80", "")
            rules = service.list_all_rules("server1")
            assert len(rules) >= 1

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown", "running": False}):
            rules = service.list_all_rules("server1")
            assert rules == []


class TestAddPortRule:
    def test_firewalld_add(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "success", "")
            result = service.add_port_rule("server1", 8080, "tcp")
            assert "8080" in result

    def test_ufw_add(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "Rule added", "")
            result = service.add_port_rule("server1", 8080, "tcp")
            assert "ufw" in result

    def test_iptables_add(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "iptables"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.add_port_rule("server1", 8080, "tcp")
            assert "iptables" in result

    def test_unknown_backend(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "unknown"}):
            result = service.add_port_rule("server1", 8080)
            assert "未检测到" in result

    def test_firewalld_add_fail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (1, "", "error")
            result = service.add_port_rule("server1", 8080)
            assert "失败" in result


class TestRemovePortRule:
    def test_firewalld_remove(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "success", "")
            result = service.remove_port_rule("server1", 8080)
            assert "删除" in result


class TestIpRules:
    def test_add_ip_rule_allow(self, service, mock_ssh, mock_conn):
        with patch.object(service, "allow_ip", return_value="IP allowed"):
            result = service.add_ip_rule("server1", "1.2.3.4", "allow")
            assert result == "IP allowed"

    def test_add_ip_rule_deny(self, service, mock_ssh, mock_conn):
        with patch.object(service, "deny_ip", return_value="IP denied"):
            result = service.add_ip_rule("server1", "1.2.3.4", "deny")
            assert result == "IP denied"

    def test_allow_ip_firewalld(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.allow_ip("server1", "1.2.3.4")
            assert "1.2.3.4" in result

    def test_deny_ip_ufw(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "ufw"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.deny_ip("server1", "1.2.3.4")
            assert "1.2.3.4" in result

    def test_remove_ip_rule_firewalld(self, service, mock_ssh, mock_conn):
        with patch.object(service, "detect_firewall_backend", return_value={"backend": "firewalld"}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_ip_rule("server1", "1.2.3.4", "allow")
            assert "删除" in result


class TestSshConfig:
    def test_get_ssh_config(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            "Port 2222\nPasswordAuthentication yes\nPermitRootLogin prohibit-password\nPubkeyAuthentication yes",
            "",
        )
        result = service.get_ssh_config("server1")
        assert result["port"] == 2222
        assert result["password_auth"] is True
        assert result["root_login"] is True
        assert result["pubkey_auth"] is True

    def test_get_ssh_config_read_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "no access")
        result = service.get_ssh_config("server1")
        assert result["port"] == 22

    def test_set_ssh_port_invalid(self, service, mock_ssh, mock_conn):
        result = service.set_ssh_port("server1", 99999)
        assert "无效" in result

    def test_set_ssh_port_read_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.set_ssh_port("server1", 2222)
        assert "无法读取" in result

    def test_set_ssh_password_auth(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "PasswordAuthentication no\nPort 22", ""),
            (0, "", ""),
        ]
        with patch.object(service, "restart_sshd", return_value="SSH 服务已重启"):
            result = service.set_ssh_password_auth("server1", True)
            assert "yes" in result

    def test_restart_sshd_systemctl(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.restart_sshd("server1")
        assert "已重启" in result

    def test_restart_sshd_service(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", "fail"),
            (0, "", ""),
        ]
        result = service.restart_sshd("server1")
        assert "已重启" in result

    def test_restart_sshd_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.restart_sshd("server1")
        assert "失败" in result


class TestSshKeys:
    def test_list_authorized_keys(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            "ssh-rsa AAAAB3NzaC1yc2E user@host\nssh-ed25519 AAAAC3NzaC1lZDI1NTE5 user2@host2",
            "",
        )
        keys = service.list_authorized_keys("server1")
        assert len(keys) == 2
        assert keys[0]["type"] == "ssh-rsa"

    def test_list_authorized_keys_empty(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        keys = service.list_authorized_keys("server1")
        assert keys == []

    def test_add_authorized_key_empty(self, service, mock_ssh, mock_conn):
        result = service.add_authorized_key("server1", "")
        assert "不能为空" in result

    def test_add_authorized_key_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.add_authorized_key("server1", "ssh-rsa AAAAB3NzaC1yc2E user@host")
        assert "已添加" in result

    def test_add_authorized_key_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        result = service.add_authorized_key("server1", "ssh-rsa AAAAB3NzaC1yc2E user@host")
        assert "失败" in result

    def test_remove_authorized_key_not_found(self, service, mock_ssh, mock_conn):
        with patch.object(service, "list_authorized_keys", return_value=[]):
            result = service.remove_authorized_key("server1", fingerprint="abc")
            assert "未找到" in result

    def test_remove_authorized_key_by_fingerprint(self, service, mock_ssh, mock_conn):
        with patch.object(service, "list_authorized_keys", return_value=[
            {"fingerprint": "AAAAB3NzaC1yc2EAAAADAQABAAAB", "comment": "user@host", "raw": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB user@host"},
        ]):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.remove_authorized_key("server1", fingerprint="AAAAB3NzaC1yc2EAAAADAQABAAAB")
            assert "已删除" in result

    def test_generate_key_pair_invalid_type(self, service, mock_ssh, mock_conn):
        result = service.generate_key_pair("server1", key_type="dsa")
        assert "error" in result

    def test_generate_key_pair_rsa(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "", ""),
            (0, "-----BEGIN RSA PRIVATE KEY-----\n...", ""),
            (0, "ssh-rsa AAAAB3NzaC1yc2E user@host", ""),
            (0, "", ""),
        ]
        result = service.generate_key_pair("server1", key_type="rsa")
        assert "private_key" in result

    def test_generate_key_pair_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        result = service.generate_key_pair("server1", key_type="ed25519")
        assert "error" in result


class TestAudit:
    def test_audit_login_attempts(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            'Jan 15 10:00:00 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22 ssh2\nJan 15 10:01:00 server sshd[1235]: Failed password for invalid user admin from 10.0.0.1 port 22 ssh2',
            "",
        )
        attempts = service.audit_login_attempts("server1")
        assert len(attempts) == 2
        assert attempts[0]["status"] == "accepted"
        assert attempts[1]["status"] == "invalid"

    def test_audit_login_attempts_no_log(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        attempts = service.audit_login_attempts("server1")
        assert attempts == []

    def test_get_login_logs_with_filter(self, service, mock_ssh, mock_conn):
        with patch.object(service, "audit_login_attempts", return_value=[
            {"user": "root", "status": "accepted"},
            {"user": "admin", "status": "failed"},
        ]):
            result = service.get_login_logs("server1", user="root")
            assert len(result) == 1
            result2 = service.get_login_logs("server1", failed_only=True)
            assert len(result2) == 1

    def test_get_ops_logs(self, service, mock_ssh, mock_conn):
        result = service.get_ops_logs("server1")
        assert result == []


class TestFail2Ban:
    def test_fail2ban_not_installed(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        result = service.get_fail2ban_status("server1")
        assert result["installed"] is False

    def test_fail2ban_installed_inactive(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/usr/bin/fail2ban-client", ""),
            (1, "", ""),
        ]
        result = service.get_fail2ban_status("server1")
        assert result["installed"] is True
        assert result["active"] is False

    def test_fail2ban_active_with_jails(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/usr/bin/fail2ban-client", ""),
            (0, "pong", ""),
            (0, "Status\n|- Number of jail:\t1\n`- Jail list:\tsshd", ""),
            (0, "Status for the jail: sshd\n|- Filter\n|  |- Currently failed:\t1\n|  |- Total failed:\t5\n`- Actions\n   |- Currently banned:\t1\n   |- Total banned:\t2\n   `- Banned IP list:\t1.2.3.4", ""),
        ]
        result = service.get_fail2ban_status("server1")
        assert result["active"] is True
        assert "sshd" in result["jails"]

    def test_unban_ip_with_jail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.unban_ip("server1", "1.2.3.4", jail="sshd")
        assert "解封" in result

    def test_unban_ip_without_jail(self, service, mock_ssh, mock_conn):
        with patch.object(service, "get_fail2ban_status", return_value={"jails": ["sshd"]}):
            mock_conn.manager.exec_command.return_value = (0, "", "")
            result = service.unban_ip("server1", "1.2.3.4")
            assert "解封" in result

    def test_unban_ip_no_jail_match(self, service, mock_ssh, mock_conn):
        with patch.object(service, "get_fail2ban_status", return_value={"jails": ["sshd"]}):
            mock_conn.manager.exec_command.return_value = (1, "", "fail")
            result = service.unban_ip("server1", "1.2.3.4")
            assert "失败" in result


class TestNetworkDiagnostics:
    def test_run_ping(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "PING 8.8.8.8: 4 packets", "")
        result = service.run_ping("server1", "8.8.8.8")
        assert result["code"] == 0

    def test_run_traceroute(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "traceroute output", "")
        result = service.run_traceroute("server1", "8.8.8.8")
        assert result["code"] == 0

    def test_run_port_scan(self, service, mock_ssh, mock_conn):
        with patch.object(service, "port_scan", return_value=[
            {"port": 80, "status": "open"},
            {"port": 443, "status": "closed"},
        ]):
            result = service.run_port_scan("server1", "8.8.8.8", "80,443")
            assert result["code"] == 0

    def test_parse_port_range(self, service):
        result = service._parse_port_range("80,443,8080")
        assert result == [80, 443, 8080]

    def test_parse_port_range_with_dash(self, service):
        result = service._parse_port_range("80-85")
        assert result == [80, 81, 82, 83, 84, 85]

    def test_parse_port_range_invalid(self, service):
        result = service._parse_port_range("abc")
        assert result == []

    def test_ping(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        result = service.ping("server1", "8.8.8.8")
        assert "stdout" in result

    def test_traceroute(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        result = service.traceroute("server1", "8.8.8.8")
        assert "stdout" in result

    def test_port_scan(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "80 open\n443 closed", "")
        result = service.port_scan("server1", "8.8.8.8", [80, 443])
        assert len(result) >= 1

    def test_port_scan_fallback(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", "fail"),
            (0, "", ""),
            (0, "", ""),
        ]
        result = service.port_scan("server1", "8.8.8.8", [80])
        assert len(result) == 1
