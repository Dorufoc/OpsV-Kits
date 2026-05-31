from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_FIREWALL_PORT = 59999


@pytest.mark.integration
@pytest.mark.ssh
class TestFirewallRealOps:
    @pytest.fixture(autouse=True)
    def _setup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> None:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._original_rules: list[dict] = []

    def _port_rule_exists(self, rules: list[dict], port: int, protocol: str = "tcp") -> bool:
        for rule in rules:
            rule_port = rule.get("port") or rule.get("ports") or ""
            rule_proto = rule.get("protocol", "tcp")
            if str(port) in str(rule_port) and rule_proto == protocol:
                return True
        return False

    def test_firewall_read_modify_restore(self) -> None:
        list_resp = self._client.get(
            "/security/firewall/rules",
            params={"alias": self._alias},
        )
        assert list_resp.status_code == 200
        original_data = list_resp.json()
        original_rules = original_data.get("rules", original_data.get("items", []))
        port_existed_before = self._port_rule_exists(original_rules, TEST_FIREWALL_PORT)

        add_resp = self._client.post(
            "/security/firewall/port",
            params={
                "alias": self._alias,
                "port": TEST_FIREWALL_PORT,
                "protocol": "tcp",
                "zone": "public",
            },
        )
        assert add_resp.status_code == 200
        add_data = add_resp.json()
        assert "message" in add_data

        after_add_resp = self._client.get(
            "/security/firewall/rules",
            params={"alias": self._alias},
        )
        assert after_add_resp.status_code == 200
        after_add_rules = after_add_resp.json().get("rules", after_add_resp.json().get("items", []))
        assert self._port_rule_exists(after_add_rules, TEST_FIREWALL_PORT), (
            f"端口 {TEST_FIREWALL_PORT}/tcp 规则未在防火墙规则中找到"
        )

        remove_resp = self._client.delete(
            "/security/firewall/port",
            params={
                "alias": self._alias,
                "port": TEST_FIREWALL_PORT,
                "protocol": "tcp",
                "zone": "public",
            },
        )
        assert remove_resp.status_code == 200

        after_remove_resp = self._client.get(
            "/security/firewall/rules",
            params={"alias": self._alias},
        )
        assert after_remove_resp.status_code == 200
        after_remove_rules = after_remove_resp.json().get("rules", after_remove_resp.json().get("items", []))

        if not port_existed_before:
            assert not self._port_rule_exists(after_remove_rules, TEST_FIREWALL_PORT), (
                f"端口 {TEST_FIREWALL_PORT}/tcp 规则删除后仍存在"
            )


@pytest.mark.integration
@pytest.mark.ssh
class TestSSHConfigRealOps:
    def test_read_ssh_config_and_verify_fields(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/security/ssh/config",
            params={"alias": alias},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        has_key_field = any(
            key in data
            for key in ("Port", "port", "PermitRootLogin", "PasswordAuthentication", "PubkeyAuthentication")
        )
        assert has_key_field, f"SSH 配置响应中未找到任何已知关键字段: {list(data.keys())}"

    def test_read_authorized_keys_returns_list(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/security/ssh/keys",
            params={"alias": alias},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert isinstance(data["keys"], list)


@pytest.mark.integration
@pytest.mark.ssh
class TestNetworkDiagnosticsReal:
    def test_ping_localhost_succeeds(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/security/network/ping",
            params={"alias": alias, "host": "127.0.0.1", "count": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        has_output = any(key in data for key in ("output", "raw", "result", "success", "stats"))
        assert has_output, f"ping 响应中未找到输出字段: {list(data.keys())}"

    @pytest.mark.timeout(30)
    def test_ping_nonexistent_host_handles_timeout(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/security/network/ping",
            params={"alias": alias, "host": "256.256.256.256", "count": 1},
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)

    def test_port_scan_localhost_finds_ssh(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/security/network/portscan",
            params={"alias": alias, "host": "127.0.0.1", "ports": "22"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        ports_data = data.get("ports", data.get("open_ports", data.get("results", [])))
        ssh_found = False
        if isinstance(ports_data, list):
            for entry in ports_data:
                port_val = entry.get("port", entry.get("number", ""))
                if str(port_val) == "22":
                    ssh_found = True
                    break
        elif isinstance(ports_data, dict):
            ssh_found = "22" in str(ports_data)
        else:
            ssh_found = "22" in str(data)
        assert ssh_found, f"端口扫描未发现 SSH 端口 22: {data}"
