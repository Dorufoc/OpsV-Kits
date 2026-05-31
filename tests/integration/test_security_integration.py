from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_FIREWALL_PORT = 59999


@pytest.mark.integration
@pytest.mark.ssh
class TestFirewallRules:
    def test_detect_firewall_backend(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/security/firewall/backend",
            params={"alias": alias},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "backend" in data or isinstance(data, dict)

    def test_list_firewall_rules(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/security/firewall/rules",
            params={"alias": alias},
        )
        assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.ssh
class TestFirewallPortRule:
    @pytest.fixture(autouse=True)
    def _cleanup_port(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> None:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._api_client.delete(
                "/security/firewall/port",
                params={
                    "alias": self._alias,
                    "port": TEST_FIREWALL_PORT,
                    "protocol": "tcp",
                    "zone": "public",
                },
            )
        except Exception:
            pass

    def test_add_and_remove_port_rule(self) -> None:
        add_resp = self._api_client.post(
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

        remove_resp = self._api_client.delete(
            "/security/firewall/port",
            params={
                "alias": self._alias,
                "port": TEST_FIREWALL_PORT,
                "protocol": "tcp",
                "zone": "public",
            },
        )
        assert remove_resp.status_code == 200
        remove_data = remove_resp.json()
        assert "message" in remove_data


@pytest.mark.integration
@pytest.mark.ssh
class TestSSHConfig:
    def test_get_ssh_config(
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

    def test_list_authorized_keys(
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


@pytest.mark.integration
@pytest.mark.ssh
class TestNetworkDiagnostics:
    def test_ping(
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

    def test_traceroute(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/security/network/traceroute",
            params={"alias": alias, "host": "127.0.0.1", "max_hops": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_port_scan(
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
