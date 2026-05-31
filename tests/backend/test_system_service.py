from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.system_service import SystemService


@pytest.fixture
def service():
    return SystemService()


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.manager.exec_command.return_value = (0, "output", "")
    return conn


@pytest.fixture
def mock_ssh(mock_conn):
    with patch("app.services.system_service.ssh_account_service") as mock_ssh_svc:
        mock_ssh_svc.get_account.return_value = MagicMock()
        mock_ssh_svc.pool.get_connection.return_value = mock_conn
        yield mock_ssh_svc


class TestConn:
    def test_conn_account_not_found(self, service):
        with patch("app.services.system_service.ssh_account_service") as mock_ssh:
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

    def test_exec_bytes_output(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, b"bytes out", b"bytes err")
        code, stdout, stderr = service._exec("server1", "ls")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    def test_exec_releases_connection(self, service, mock_ssh, mock_conn):
        service._exec("server1", "ls")
        mock_ssh.pool.release_connection.assert_called_once_with(mock_conn)


class TestGetSystemInfo:
    def test_get_system_info(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "myserver", ""),
            (0, "CentOS Linux release 7.9.2009 (Core)", ""),
            (0, "up 30 days, 5:00", ""),
            (0, "3.10.0-1160.el7.x86_64", ""),
        ]
        info = service.get_system_info("server1")
        assert info["hostname"] == "myserver"
        assert "CentOS" in info["os"]
        assert info["uptime"] == "up 30 days, 5:00"
        assert info["kernel"] == "3.10.0-1160.el7.x86_64"

    def test_get_system_info_empty_outputs(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        info = service.get_system_info("server1")
        assert info["os"] == "unknown"
        assert info["kernel"] == ""


class TestGetPerformance:
    def test_get_performance(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "top output", ""),
            (0, "4", ""),
            (0, "Intel(R) Xeon(R)", ""),
            (0, "Mem:  8192000000  4096000000  4096000000", ""),
            (0, "total  102400000000  51200000000  51200000000", ""),
            (0, "0.5 1.0 1.5", ""),
        ]
        result = service.get_performance("server1")
        assert "cpu_raw" in result
        assert result["cpu_cores"] == "4"
        assert result["cpu_model"] == "Intel(R) Xeon(R)"
        assert "memory" in result
        assert "disk" in result
        assert result["loadavg"] == "0.5 1.0 1.5"

    def test_get_performance_no_memory(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
        ]
        result = service.get_performance("server1")
        assert "memory" not in result
        assert "disk" not in result


class TestGetDisksDetail:
    def test_get_disks_detail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            "/dev/sda1  1024000000  512000000  512000000  50  /\n/dev/sda2  2048000000  1024000000  1024000000  50  /home",
            "",
        )
        mounts = service.get_disks_detail("server1")
        assert len(mounts) == 2
        assert mounts[0]["mount"] == "/"
        assert mounts[1]["mount"] == "/home"

    def test_get_disks_detail_empty(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        mounts = service.get_disks_detail("server1")
        assert mounts == []

    def test_get_disks_detail_short_line(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "short", "")
        mounts = service.get_disks_detail("server1")
        assert mounts == []


class TestReboot:
    def test_reboot(self, service, mock_ssh, mock_conn):
        result = service.reboot("server1")
        assert "重启" in result


class TestShutdown:
    def test_shutdown(self, service, mock_ssh, mock_conn):
        result = service.shutdown("server1")
        assert "关机" in result


class TestReloadNetwork:
    def test_reload_network_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.reload_network("server1")
        assert "已重启" in result

    def test_reload_network_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "failed")
        result = service.reload_network("server1")
        assert "失败" in result


class TestReloadSsh:
    def test_reload_ssh_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.reload_ssh("server1")
        assert "已重启" in result

    def test_reload_ssh_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "failed")
        result = service.reload_ssh("server1")
        assert "失败" in result


class TestClearCache:
    def test_clear_cache_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.clear_cache("server1")
        assert "已清理" in result

    def test_clear_cache_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "failed")
        result = service.clear_cache("server1")
        assert "失败" in result


class TestSelinux:
    def test_check_selinux_enforcing(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Enforcing", "")
        result = service.check_selinux("server1")
        assert result["status"] == "Enforcing"
        assert result["enabled"] is True

    def test_check_selinux_disabled(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Disabled", "")
        result = service.check_selinux("server1")
        assert result["enabled"] is False

    def test_check_selinux_unknown(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        result = service.check_selinux("server1")
        assert result["status"] == "unknown"

    def test_set_selinux_permissive(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_selinux("server1", "permissive")
        assert "permissive" in result

    def test_set_selinux_enforcing(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_selinux("server1", "enforcing")
        assert "enforcing" in result

    def test_set_selinux_invalid(self, service, mock_ssh, mock_conn):
        result = service.set_selinux("server1", "invalid")
        assert "无效" in result

    def test_set_selinux_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.set_selinux("server1", "permissive")
        assert "失败" in result


class TestFirewallStatus:
    def test_firewall_installed_active(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/usr/bin/firewall-cmd", ""),
            (0, "running", ""),
        ]
        result = service.get_firewall_status("server1")
        assert result["installed"] is True
        assert result["active"] is True

    def test_firewall_not_installed(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        result = service.get_firewall_status("server1")
        assert result["installed"] is False


class TestSetFirewall:
    def test_set_firewall_enable(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_firewall("server1", enable=True)
        assert "开启" in result

    def test_set_firewall_disable(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_firewall("server1", enable=False)
        assert "关闭" in result

    def test_set_firewall_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.set_firewall("server1", enable=True)
        assert "失败" in result


class TestFirewallRules:
    def test_list_firewall_rules_firewalld(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            "public\n  target: default\n  icmp-block-inversion: no\n  ports: 80/tcp 443/tcp\n  services: ssh http\n  forward-ports: \n  source-ports: \n  icmp-blocks: \n  masquerade: no",
            "",
        )
        rules = service.list_firewall_rules("server1")
        assert isinstance(rules, list)

    def test_list_firewall_rules_iptables_fallback(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", ""),
            (0, "Chain INPUT (policy ACCEPT)\n1  ACCEPT  tcp  --  0.0.0.0/0  0.0.0.0/0  tcp dpt:80", ""),
        ]
        rules = service.list_firewall_rules("server1")
        assert len(rules) >= 1
        assert rules[0]["source"] == "iptables"


class TestPortRules:
    def test_add_port_rule(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.add_port_rule("server1", 8080, "tcp")
        assert "8080" in result

    def test_add_port_rule_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.add_port_rule("server1", 8080)
        assert "失败" in result

    def test_remove_port_rule(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.remove_port_rule("server1", 8080)
        assert "删除" in result


class TestServiceRules:
    def test_add_service_rule(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.add_service_rule("server1", "http")
        assert "http" in result

    def test_remove_service_rule(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.remove_service_rule("server1", "http")
        assert "删除" in result


class TestFirewallZones:
    def test_get_firewall_zones(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "public\n  interfaces: eth0", "")
        zones = service.get_firewall_zones("server1")
        assert "public" in zones

    def test_get_firewall_zones_default(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "")
        zones = service.get_firewall_zones("server1")
        assert zones == ["public"]


class TestSyncTime:
    def test_sync_time_chrony(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.sync_time("server1")
        assert "已同步" in result

    def test_sync_time_timedatectl(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (1, "", "fail"),
            (0, "", ""),
        ]
        result = service.sync_time("server1")
        assert "NTP" in result

    def test_sync_time_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.sync_time("server1")
        assert "失败" in result


class TestSetHostname:
    def test_set_hostname_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_hostname("server1", "newhost")
        assert "newhost" in result

    def test_set_hostname_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.set_hostname("server1", "newhost")
        assert "失败" in result


class TestTimezone:
    def test_get_timezone(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "Asia/Shanghai", ""),
            (0, "Asia/Shanghai", ""),
        ]
        result = service.get_timezone("server1")
        assert result["timezone"] == "Asia/Shanghai"

    def test_set_timezone_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.set_timezone("server1", "Asia/Tokyo")
        assert "Asia/Tokyo" in result

    def test_set_timezone_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.set_timezone("server1", "Invalid/Zone")
        assert "失败" in result


class TestLoggedUsers:
    def test_get_logged_users(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "root     pts/0        2025-01-15 10:00 (192.168.1.1)", ""),
            (0, "w output", ""),
        ]
        result = service.get_logged_users("server1")
        assert len(result["users"]) >= 1
        assert result["users"][0]["user"] == "root"

    def test_get_logged_users_empty(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.get_logged_users("server1")
        assert result["users"] == []


class TestBootTime:
    def test_get_boot_time(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "system boot  2025-01-01 00:00", ""),
            (0, "2025-01-01 00:00:00", ""),
        ]
        result = service.get_boot_time("server1")
        assert "boot_time" in result


class TestKernelModules:
    def test_get_kernel_modules(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "Module                  Size  Used by\nnf_conntrack          139224  1\nnfs                   364024  0", ""),
            (0, "3", ""),
        ]
        result = service.get_kernel_modules("server1")
        assert len(result["modules"]) >= 1
        assert result["modules"][0]["name"] == "nf_conntrack"

    def test_get_kernel_modules_empty(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.get_kernel_modules("server1")
        assert result["modules"] == []


class TestEnabledServices:
    def test_get_enabled_services(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "sshd.service enabled", "")
        result = service.get_enabled_services("server1")
        assert "sshd" in result["services"]


class TestDnsConfig:
    def test_get_dns_config(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "nameserver 8.8.8.8\nnameserver 8.8.4.4", "")
        result = service.get_dns_config("server1")
        assert "8.8.8.8" in result["resolv_conf"]


class TestUlimit:
    def test_get_ulimit(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "core file size          (blocks, -c) 0", "")
        result = service.get_ulimit("server1")
        assert "core" in result["ulimit"]


class TestSwapStatus:
    def test_get_swap_status(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "NAME      TYPE      SIZE USED PRIO\n/dev/sda5 partition 2G   100M  -2", ""),
            (0, "Swap: 2G   100M   1.9G", ""),
        ]
        result = service.get_swap_status("server1")
        assert "swapon" in result
        assert "free" in result


class TestSwapRefresh:
    def test_swap_refresh_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.swap_refresh("server1")
        assert "已刷新" in result

    def test_swap_refresh_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.swap_refresh("server1")
        assert "失败" in result


class TestCleanupOldKernels:
    def test_cleanup_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.cleanup_old_kernels("server1")
        assert "已清理" in result

    def test_cleanup_nothing_to_do(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "Nothing to do")
        result = service.cleanup_old_kernels("server1")
        assert "没有" in result

    def test_cleanup_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error occurred")
        result = service.cleanup_old_kernels("server1")
        assert "失败" in result


class TestCleanupJournal:
    def test_cleanup_journal_success(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.cleanup_journal("server1", days=7)
        assert "7" in result

    def test_cleanup_journal_fail(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "fail")
        result = service.cleanup_journal("server1")
        assert "失败" in result


class TestCheckUpdates:
    def test_check_updates(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (
            0,
            "Loading mirror speeds\nLast metadata expiration\nkernel.x86_64              3.10.0-1160       updates\nnginx.x86_64               1.20.1            epel",
            "",
        )
        result = service.check_updates("server1")
        assert result["update_count"] >= 1

    def test_check_updates_empty(self, service, mock_ssh, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        result = service.check_updates("server1")
        assert result["update_count"] == 0
