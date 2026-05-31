from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_IMAGE = "alpine:latest"
NONEXISTENT_IMAGE = "opsv-kits/nonexistent-image-xyz:never"
COMPOSE_PROJECT_DIR = "/tmp/opsv-test-compose"
COMPOSE_NETWORK_NAME = "opsv-test-net"
COMPOSE_VOLUME_NAME = "opsv-test-vol"

IMAGE_PULL_WAIT = 30
CONTAINER_START_WAIT = 5
CONTAINER_STOP_WAIT = 3


def _exec_remote(
    api_client: TestClient,
    alias: str,
    command: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    resp = api_client.post(
        "/api/command/exec",
        json={"alias": alias, "command": command, "timeout": timeout},
    )
    assert resp.status_code == 200, f"远程命令执行失败: {resp.text}"
    return resp.json()


def _pull_image(
    api_client: TestClient,
    alias: str,
    image_name: str,
) -> dict[str, Any]:
    resp = api_client.post(
        "/api/docker/images/pull",
        json={"account_alias": alias, "image_name": image_name},
    )
    return resp


def _find_image(
    images: list[dict[str, Any]],
    repo: str,
) -> list[dict[str, Any]]:
    return [
        img
        for img in images
        if img.get("repository", img.get("Repository", "")) == repo
        or img.get("repository", img.get("Repository", "")).endswith(f"/{repo}")
    ]


@pytest.mark.integration
@pytest.mark.docker
class TestDockerImageOps:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._client.delete(
                f"/api/docker/images/{TEST_IMAGE}",
                params={"account_alias": self._alias},
            )
        except Exception:
            pass
        try:
            self._client.delete(
                f"/api/docker/images/alpine:latest",
                params={"account_alias": self._alias},
            )
        except Exception:
            pass

    def test_pull_list_delete_image(self) -> None:
        pull_resp = _pull_image(self._client, self._alias, TEST_IMAGE)
        assert pull_resp.status_code == 200, f"拉取镜像失败: {pull_resp.text}"
        pull_data = pull_resp.json()
        assert "message" in pull_data

        list_resp = self._client.get(
            "/api/docker/images",
            params={"account_alias": self._alias},
        )
        assert list_resp.status_code == 200
        images = list_resp.json()
        assert isinstance(images, list)
        alpine_images = _find_image(images, "alpine")
        assert len(alpine_images) > 0, f"镜像列表中应包含 alpine: {images}"

        delete_resp = self._client.delete(
            f"/api/docker/images/{TEST_IMAGE}",
            params={"account_alias": self._alias},
        )
        assert delete_resp.status_code == 200, f"删除镜像失败: {delete_resp.text}"

        list_resp2 = self._client.get(
            "/api/docker/images",
            params={"account_alias": self._alias},
        )
        assert list_resp2.status_code == 200
        images2 = list_resp2.json()
        alpine_images2 = _find_image(images2, "alpine")
        assert len(alpine_images2) == 0, f"删除后镜像列表不应包含 alpine: {images2}"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerImagePullFailure:
    def test_pull_nonexistent_image_returns_error(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        resp = _pull_image(api_client, ensure_ssh_account.alias, NONEXISTENT_IMAGE)
        assert resp.status_code != 200, (
            f"拉取不存在的镜像应返回错误，实际: {resp.status_code}"
        )


@pytest.mark.integration
@pytest.mark.docker
class TestDockerComposeProject:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._client.post(
                "/api/docker/compose/down",
                json={
                    "account_alias": self._alias,
                    "project_path": f"{COMPOSE_PROJECT_DIR}/docker-compose.yml",
                },
            )
        except Exception:
            pass
        try:
            _exec_remote(
                self._client,
                self._alias,
                f"rm -rf {COMPOSE_PROJECT_DIR}",
                timeout=10.0,
            )
        except Exception:
            pass

    def test_compose_up_logs_down(self) -> None:
        compose_content = (
            "version: '3.8'\n"
            "services:\n"
            "  test-echo:\n"
            "    image: alpine:latest\n"
            "    container_name: opsv-test-echo\n"
            "    command: sh -c 'echo \"opsv-compose-test-started\" && sleep 60'\n"
            "    labels:\n"
            "      managed-by: \"opsv-kits-store\"\n"
        )

        _exec_remote(
            self._client,
            self._alias,
            f"mkdir -p {COMPOSE_PROJECT_DIR}",
            timeout=10.0,
        )

        write_result = _exec_remote(
            self._client,
            self._alias,
            f"cat > {COMPOSE_PROJECT_DIR}/docker-compose.yml << 'OPSVEOF'\n{compose_content}OPSVEOF",
            timeout=10.0,
        )
        assert write_result.get("exit_code", -1) == 0, (
            f"写入 compose 文件失败: {write_result}"
        )

        _pull_image(self._client, self._alias, "alpine:latest")

        up_resp = self._client.post(
            "/api/docker/compose/up",
            json={
                "account_alias": self._alias,
                "project_path": f"{COMPOSE_PROJECT_DIR}/docker-compose.yml",
                "detach": True,
            },
        )
        assert up_resp.status_code == 200, f"Compose up 失败: {up_resp.text}"

        time.sleep(CONTAINER_START_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias},
        )
        assert resp.status_code == 200
        containers = resp.json()
        echo_containers = [
            c
            for c in containers
            if c.get("name", c.get("Names", "")) == "opsv-test-echo"
        ]
        assert len(echo_containers) > 0, "未找到 compose 启动的测试容器"
        assert echo_containers[0].get("state", echo_containers[0].get("State", "")).lower() == "running"

        container_id = echo_containers[0].get("id", echo_containers[0].get("ID", ""))
        if container_id:
            logs_resp = self._client.get(
                f"/api/docker/containers/{container_id}/logs",
                params={"account_alias": self._alias, "tail": 20},
            )
            assert logs_resp.status_code == 200, f"获取日志失败: {logs_resp.text}"
            logs_data = logs_resp.json()
            logs = logs_data.get("logs", [])
            log_text = " ".join(logs) if isinstance(logs, list) else str(logs)
            assert "opsv-compose-test-started" in log_text, (
                f"日志中应包含测试输出: {log_text[:200]}"
            )

        down_resp = self._client.post(
            "/api/docker/compose/down",
            json={
                "account_alias": self._alias,
                "project_path": f"{COMPOSE_PROJECT_DIR}/docker-compose.yml",
            },
        )
        assert down_resp.status_code == 200, f"Compose down 失败: {down_resp.text}"

        time.sleep(CONTAINER_STOP_WAIT)

        resp2 = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp2.status_code == 200
        containers2 = resp2.json()
        echo_containers2 = [
            c
            for c in containers2
            if c.get("name", c.get("Names", "")) == "opsv-test-echo"
        ]
        assert len(echo_containers2) == 0, "Compose down 后容器应被移除"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerNetworkVolume:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._client.delete(
                f"/api/docker/networks/{COMPOSE_NETWORK_NAME}",
                params={"account_alias": self._alias},
            )
        except Exception:
            pass
        try:
            self._client.delete(
                f"/api/docker/volumes/{COMPOSE_VOLUME_NAME}",
                params={"account_alias": self._alias},
            )
        except Exception:
            pass

    def test_network_create_list_delete(self) -> None:
        create_resp = self._client.post(
            "/api/docker/networks",
            json={
                "account_alias": self._alias,
                "name": COMPOSE_NETWORK_NAME,
                "driver": "bridge",
            },
        )
        assert create_resp.status_code == 201, f"创建网络失败: {create_resp.text}"
        create_data = create_resp.json()
        assert "network_id" in create_data or "name" in create_data

        list_resp = self._client.get(
            "/api/docker/networks",
            params={"account_alias": self._alias},
        )
        assert list_resp.status_code == 200
        networks = list_resp.json()
        assert isinstance(networks, list)
        found = any(
            n.get("name", n.get("Name", "")) == COMPOSE_NETWORK_NAME
            for n in networks
        )
        assert found, f"网络列表中应包含 {COMPOSE_NETWORK_NAME}: {networks}"

        info_resp = self._client.get(
            f"/api/docker/networks/{COMPOSE_NETWORK_NAME}",
            params={"account_alias": self._alias},
        )
        assert info_resp.status_code == 200, f"获取网络信息失败: {info_resp.text}"

        delete_resp = self._client.delete(
            f"/api/docker/networks/{COMPOSE_NETWORK_NAME}",
            params={"account_alias": self._alias},
        )
        assert delete_resp.status_code == 200, f"删除网络失败: {delete_resp.text}"

        list_resp2 = self._client.get(
            "/api/docker/networks",
            params={"account_alias": self._alias},
        )
        assert list_resp2.status_code == 200
        networks2 = list_resp2.json()
        found2 = any(
            n.get("name", n.get("Name", "")) == COMPOSE_NETWORK_NAME
            for n in networks2
        )
        assert not found2, f"删除后网络列表不应包含 {COMPOSE_NETWORK_NAME}"

    def test_volume_create_list_delete(self) -> None:
        create_resp = self._client.post(
            "/api/docker/volumes",
            json={
                "account_alias": self._alias,
                "name": COMPOSE_VOLUME_NAME,
            },
        )
        assert create_resp.status_code == 201, f"创建卷失败: {create_resp.text}"
        create_data = create_resp.json()
        assert "volume_name" in create_data

        list_resp = self._client.get(
            "/api/docker/volumes",
            params={"account_alias": self._alias},
        )
        assert list_resp.status_code == 200
        volumes_data = list_resp.json()
        volumes = volumes_data.get("volumes", volumes_data) if isinstance(volumes_data, dict) else volumes_data
        assert isinstance(volumes, list)
        found = any(
            v.get("name", v.get("Name", "")) == COMPOSE_VOLUME_NAME
            for v in volumes
        )
        assert found, f"卷列表中应包含 {COMPOSE_VOLUME_NAME}: {volumes}"

        info_resp = self._client.get(
            f"/api/docker/volumes/{COMPOSE_VOLUME_NAME}",
            params={"account_alias": self._alias},
        )
        assert info_resp.status_code == 200, f"获取卷信息失败: {info_resp.text}"

        delete_resp = self._client.delete(
            f"/api/docker/volumes/{COMPOSE_VOLUME_NAME}",
            params={"account_alias": self._alias},
        )
        assert delete_resp.status_code == 200, f"删除卷失败: {delete_resp.text}"

        list_resp2 = self._client.get(
            "/api/docker/volumes",
            params={"account_alias": self._alias},
        )
        assert list_resp2.status_code == 200
        volumes_data2 = list_resp2.json()
        volumes2 = volumes_data2.get("volumes", volumes_data2) if isinstance(volumes_data2, dict) else volumes_data2
        found2 = any(
            v.get("name", v.get("Name", "")) == COMPOSE_VOLUME_NAME
            for v in volumes2
        )
        assert not found2, f"删除后卷列表不应包含 {COMPOSE_VOLUME_NAME}"
