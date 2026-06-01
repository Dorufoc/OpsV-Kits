from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount


@pytest.mark.integration
class TestMonitorCPU:
    def test_get_cpu_percent(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/cpu", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "percent" in data or "cpu_percent" in data or isinstance(data, dict)

    def test_get_cpu_cores(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/cpu/cores", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "cores" in data


@pytest.mark.integration
class TestMonitorMemory:
    def test_get_memory_stats(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/memory", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestMonitorDisk:
    def test_get_disk_stats(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/disks", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "disks" in data

    def test_get_disk_io(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/disk-io", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "devices" in data


@pytest.mark.integration
class TestMonitorNetwork:
    def test_get_network_rate(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/network", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "interfaces" in data

    def test_get_network_connections(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/connections", params={"alias": alias})
        assert resp.status_code == 200


@pytest.mark.integration
class TestMonitorLoad:
    def test_get_load_average(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/load", params={"alias": alias})
        assert resp.status_code == 200


@pytest.mark.integration
class TestMonitorDockerStats:
    def test_get_docker_metrics(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/docker", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "containers" in data


@pytest.mark.integration
class TestMonitorSnapshot:
    def test_get_snapshot(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/monitor/snapshot", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
