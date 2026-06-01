from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_IMAGE = "hello-world:latest"
TEST_CONTAINER_PREFIX = "opsv-test-"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerInfo:
    def test_get_docker_info(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/docker/info", params={"account_alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert "installed" in data
        assert "running" in data


@pytest.mark.integration
@pytest.mark.docker
class TestDockerContainerList:
    def test_list_containers(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/docker/containers",
            params={"account_alias": alias, "all": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_images(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/docker/images", params={"account_alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.docker
class TestDockerContainerLifecycle:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._container_ids: list[str] = []
        yield
        for cid in self._container_ids:
            try:
                self._api_client.delete(
                    f"/api/docker/containers/{cid}",
                    params={"account_alias": self._alias, "force": True},
                )
            except Exception:
                pass

    def test_pull_image(self) -> None:
        resp = self._api_client.post(
            "/api/docker/images/pull",
            json={
                "account_alias": self._alias,
                "image_name": TEST_IMAGE,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    def test_container_create_start_stop_remove(self) -> None:
        pull_resp = self._api_client.post(
            "/api/docker/images/pull",
            json={
                "account_alias": self._alias,
                "image_name": TEST_IMAGE,
            },
        )
        assert pull_resp.status_code == 200

        container_name = f"{TEST_CONTAINER_PREFIX}{int(time.time())}"
        create_resp = self._api_client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": f"docker create --name {container_name} {TEST_IMAGE}",
                "timeout": 30.0,
            },
        )
        assert create_resp.status_code == 200
        create_data = create_resp.json()
        container_id = create_data.get("stdout", "").strip()
        if not container_id:
            pytest.skip("无法通过命令创建容器，跳过生命周期测试")
        self._container_ids.append(container_id)

        start_resp = self._api_client.post(
            f"/api/docker/containers/{container_id}/start",
            params={"account_alias": self._alias},
        )
        assert start_resp.status_code == 200

        time.sleep(2)

        stop_resp = self._api_client.post(
            f"/api/docker/containers/{container_id}/stop",
            json={"account_alias": self._alias, "timeout": 10},
        )
        assert stop_resp.status_code == 200

        remove_resp = self._api_client.delete(
            f"/api/docker/containers/{container_id}",
            params={"account_alias": self._alias, "force": True},
        )
        assert remove_resp.status_code == 200
        self._container_ids.remove(container_id)


@pytest.mark.integration
@pytest.mark.docker
class TestDockerContainerLogs:
    def test_get_container_logs(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/docker/containers",
            params={"account_alias": alias},
        )
        assert resp.status_code == 200
        containers = resp.json()
        if not containers:
            pytest.skip("没有运行中的容器，跳过日志测试")

        container_id = containers[0].get("Id", containers[0].get("id", ""))
        if not container_id:
            pytest.skip("无法获取容器 ID")

        logs_resp = api_client.get(
            f"/api/docker/containers/{container_id}/logs",
            params={"account_alias": alias, "tail": 10},
        )
        assert logs_resp.status_code in (200, 404)


@pytest.mark.integration
@pytest.mark.docker
class TestDockerComposeProjects:
    def test_list_compose_projects(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/docker/compose/projects",
            params={"account_alias": alias, "search_path": "/opt"},
        )
        assert resp.status_code == 200
