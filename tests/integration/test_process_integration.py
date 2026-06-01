from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount


@pytest.mark.integration
class TestProcessList:
    def test_get_process_list(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/process/list", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "processes" in data
        assert "count" in data
        assert isinstance(data["processes"], list)
        assert data["count"] >= 0

    def test_get_process_detail(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        list_resp = api_client.get("/api/process/list", params={"alias": alias})
        assert list_resp.status_code == 200
        processes = list_resp.json().get("processes", [])
        if not processes:
            pytest.skip("无法获取进程列表，跳过进程详情测试")

        pid = processes[0].get("pid") or processes[0].get("PID")
        if not pid:
            pytest.skip("无法从进程列表中获取 PID")

        detail_resp = api_client.get(
            "/api/process/detail",
            params={"alias": alias, "pid": pid},
        )
        assert detail_resp.status_code in (200, 404)


@pytest.mark.integration
class TestProcessTermination:
    def test_kill_nonexistent_process(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/process/kill",
            json={
                "alias": alias,
                "pid": 999999,
                "signal": "SIGTERM",
            },
        )
        assert resp.status_code in (200, 404, 500)


@pytest.mark.integration
class TestServiceManagement:
    def test_service_status(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/process/service/control",
            json={
                "alias": alias,
                "service_name": "sshd",
                "action": "status",
            },
        )
        assert resp.status_code in (200, 500)

    def test_service_status_invalid_service(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/process/service/control",
            json={
                "alias": alias,
                "service_name": "nonexistent-service-opsv-test",
                "action": "status",
            },
        )
        assert resp.status_code in (200, 500)


@pytest.mark.integration
class TestProcessPriority:
    def test_set_nice_nonexistent_process(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/process/nice",
            json={
                "alias": alias,
                "pid": 999999,
                "nice_value": 10,
            },
        )
        assert resp.status_code in (200, 404, 500)


@pytest.mark.integration
class TestProcessAlerts:
    def test_get_alerts(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/process/alerts", params={"alias": alias})
        assert resp.status_code == 200

    def test_get_alert_config(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/process/alert-config", params={"alias": alias})
        assert resp.status_code == 200
