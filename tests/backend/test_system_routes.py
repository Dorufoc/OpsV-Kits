from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_service():
    with patch("app.api.routes.system.system_service") as m:
        yield m


_GET_ROUTES = [
    ("/api/system/info", "get_system_info", {"os": "Linux"}),
    ("/api/system/performance", "get_performance", {"uptime": 12345}),
    ("/api/system/selinux", "check_selinux", {"mode": "enforcing"}),
    ("/api/system/firewall/status", "get_firewall_status", {"active": True}),
    ("/api/system/firewall/rules", "list_firewall_rules", ["rule1"]),
    ("/api/system/firewall/zones", "get_firewall_zones", ["public"]),
    ("/api/system/toolkit/timezone", "get_timezone", {"timezone": "UTC"}),
    ("/api/system/toolkit/logged-users", "get_logged_users", ["root"]),
    ("/api/system/toolkit/boot-time", "get_boot_time", {"boot_time": "2025-01-01"}),
    ("/api/system/toolkit/kernel-modules", "get_kernel_modules", ["nf_conntrack"]),
    ("/api/system/toolkit/enabled-services", "get_enabled_services", ["sshd"]),
    ("/api/system/toolkit/dns-config", "get_dns_config", {"nameservers": ["8.8.8.8"]}),
    ("/api/system/toolkit/ulimit", "get_ulimit", {"open_files": 65535}),
    ("/api/system/toolkit/swap-status", "get_swap_status", {"total": 2048}),
    ("/api/system/toolkit/check-updates", "check_updates", {"updates": 5}),
]


class TestGetRoutes:
    @pytest.mark.parametrize("path,method_name,return_val", _GET_ROUTES)
    def test_get_success(self, client, mock_service, path, method_name, return_val):
        getattr(mock_service, method_name).return_value = return_val
        resp = client.get(path, params={"alias": "srv1"})
        assert resp.status_code == 200

    @pytest.mark.parametrize("path,method_name,return_val", _GET_ROUTES)
    def test_get_value_error(self, client, mock_service, path, method_name, return_val):
        getattr(mock_service, method_name).side_effect = ValueError("not found")
        resp = client.get(path, params={"alias": "srv1"})
        assert resp.status_code == 404

    @pytest.mark.parametrize("path,method_name,return_val", _GET_ROUTES)
    def test_get_generic_error(self, client, mock_service, path, method_name, return_val):
        getattr(mock_service, method_name).side_effect = Exception("fail")
        resp = client.get(path, params={"alias": "srv1"})
        assert resp.status_code == 500


_POST_MSG_ROUTES = [
    ("/api/system/reboot", "reboot", "rebooted"),
    ("/api/system/shutdown", "shutdown", "shutting down"),
    ("/api/system/reload/network", "reload_network", "network reloaded"),
    ("/api/system/reload/ssh", "reload_ssh", "ssh reloaded"),
    ("/api/system/cache/clear", "clear_cache", "cache cleared"),
    ("/api/system/toolkit/sync-time", "sync_time", "time synced"),
    ("/api/system/toolkit/swap-refresh", "swap_refresh", "swap refreshed"),
    ("/api/system/toolkit/cleanup-kernels", "cleanup_old_kernels", "kernels cleaned"),
]


class TestPostMessageRoutes:
    @pytest.mark.parametrize("path,method_name,msg", _POST_MSG_ROUTES)
    def test_post_success(self, client, mock_service, path, method_name, msg):
        getattr(mock_service, method_name).return_value = msg
        resp = client.post(path, params={"alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["message"] == msg

    @pytest.mark.parametrize("path,method_name,msg", _POST_MSG_ROUTES)
    def test_post_value_error(self, client, mock_service, path, method_name, msg):
        getattr(mock_service, method_name).side_effect = ValueError("not found")
        resp = client.post(path, params={"alias": "srv1"})
        assert resp.status_code == 404

    @pytest.mark.parametrize("path,method_name,msg", _POST_MSG_ROUTES)
    def test_post_generic_error(self, client, mock_service, path, method_name, msg):
        getattr(mock_service, method_name).side_effect = Exception("fail")
        resp = client.post(path, params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetDisks:
    def test_disks_success(self, client, mock_service):
        mock_service.get_disks_detail.return_value = [{"device": "/dev/sda1", "size": "100G"}]
        resp = client.get("/api/system/disks", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "disks" in resp.json()

    def test_disks_value_error(self, client, mock_service):
        mock_service.get_disks_detail.side_effect = ValueError("not found")
        resp = client.get("/api/system/disks", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestSetSelinux:
    def test_set_selinux_success(self, client, mock_service):
        mock_service.set_selinux.return_value = "SELinux set to permissive"
        resp = client.post("/api/system/selinux", params={"alias": "srv1", "mode": "permissive"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "SELinux set to permissive"

    def test_set_selinux_value_error(self, client, mock_service):
        mock_service.set_selinux.side_effect = ValueError("not found")
        resp = client.post("/api/system/selinux", params={"alias": "srv1", "mode": "enforcing"})
        assert resp.status_code == 404


class TestSetFirewall:
    def test_set_firewall_success(self, client, mock_service):
        mock_service.set_firewall.return_value = "firewall enabled"
        resp = client.post("/api/system/firewall/set", params={"alias": "srv1", "enable": True})
        assert resp.status_code == 200
        assert resp.json()["message"] == "firewall enabled"

    def test_set_firewall_value_error(self, client, mock_service):
        mock_service.set_firewall.side_effect = ValueError("not found")
        resp = client.post("/api/system/firewall/set", params={"alias": "srv1", "enable": False})
        assert resp.status_code == 404


class TestAddPortRule:
    def test_add_port_success(self, client, mock_service):
        mock_service.add_port_rule.return_value = "port added"
        resp = client.post("/api/system/firewall/port", params={"alias": "srv1", "port": 8080, "protocol": "tcp", "zone": "public"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "port added"

    def test_add_port_default_params(self, client, mock_service):
        mock_service.add_port_rule.return_value = "port added"
        resp = client.post("/api/system/firewall/port", params={"alias": "srv1", "port": 443})
        assert resp.status_code == 200
        mock_service.add_port_rule.assert_called_with("srv1", 443, "tcp", "public")

    def test_add_port_value_error(self, client, mock_service):
        mock_service.add_port_rule.side_effect = ValueError("not found")
        resp = client.post("/api/system/firewall/port", params={"alias": "srv1", "port": 8080})
        assert resp.status_code == 404


class TestRemovePortRule:
    def test_remove_port_success(self, client, mock_service):
        mock_service.remove_port_rule.return_value = "port removed"
        resp = client.delete("/api/system/firewall/port", params={"alias": "srv1", "port": 8080, "protocol": "tcp", "zone": "public"})
        assert resp.status_code == 200

    def test_remove_port_value_error(self, client, mock_service):
        mock_service.remove_port_rule.side_effect = ValueError("not found")
        resp = client.delete("/api/system/firewall/port", params={"alias": "srv1", "port": 8080})
        assert resp.status_code == 404


class TestAddServiceRule:
    def test_add_service_success(self, client, mock_service):
        mock_service.add_service_rule.return_value = "service added"
        resp = client.post("/api/system/firewall/service", params={"alias": "srv1", "service": "http", "zone": "public"})
        assert resp.status_code == 200

    def test_add_service_value_error(self, client, mock_service):
        mock_service.add_service_rule.side_effect = ValueError("not found")
        resp = client.post("/api/system/firewall/service", params={"alias": "srv1", "service": "http"})
        assert resp.status_code == 404


class TestRemoveServiceRule:
    def test_remove_service_success(self, client, mock_service):
        mock_service.remove_service_rule.return_value = "service removed"
        resp = client.delete("/api/system/firewall/service", params={"alias": "srv1", "service": "http", "zone": "public"})
        assert resp.status_code == 200

    def test_remove_service_value_error(self, client, mock_service):
        mock_service.remove_service_rule.side_effect = ValueError("not found")
        resp = client.delete("/api/system/firewall/service", params={"alias": "srv1", "service": "http"})
        assert resp.status_code == 404


class TestSetHostname:
    def test_set_hostname_success(self, client, mock_service):
        mock_service.set_hostname.return_value = "hostname set"
        resp = client.post("/api/system/toolkit/hostname", params={"alias": "srv1", "hostname": "newhost"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "hostname set"

    def test_set_hostname_value_error(self, client, mock_service):
        mock_service.set_hostname.side_effect = ValueError("not found")
        resp = client.post("/api/system/toolkit/hostname", params={"alias": "srv1", "hostname": "newhost"})
        assert resp.status_code == 404


class TestSetTimezone:
    def test_set_timezone_success(self, client, mock_service):
        mock_service.set_timezone.return_value = "timezone set"
        resp = client.post("/api/system/toolkit/timezone", params={"alias": "srv1", "timezone": "Asia/Shanghai"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "timezone set"

    def test_set_timezone_value_error(self, client, mock_service):
        mock_service.set_timezone.side_effect = ValueError("not found")
        resp = client.post("/api/system/toolkit/timezone", params={"alias": "srv1", "timezone": "UTC"})
        assert resp.status_code == 404


class TestCleanupJournal:
    def test_cleanup_journal_success(self, client, mock_service):
        mock_service.cleanup_journal.return_value = "journal cleaned"
        resp = client.post("/api/system/toolkit/cleanup-journal", params={"alias": "srv1", "days": 7})
        assert resp.status_code == 200

    def test_cleanup_journal_default_days(self, client, mock_service):
        mock_service.cleanup_journal.return_value = "journal cleaned"
        resp = client.post("/api/system/toolkit/cleanup-journal", params={"alias": "srv1"})
        assert resp.status_code == 200
        mock_service.cleanup_journal.assert_called_with("srv1", 7)

    def test_cleanup_journal_value_error(self, client, mock_service):
        mock_service.cleanup_journal.side_effect = ValueError("not found")
        resp = client.post("/api/system/toolkit/cleanup-journal", params={"alias": "srv1"})
        assert resp.status_code == 404
