from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

skip_if_no_ssh = pytest.mark.skipif(
    not os.environ.get("OPSV_SSH_HOST"),
    reason="集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。",
)


@pytest.mark.integration
@skip_if_no_ssh
class TestSSHConnectionTimeout:
    def test_unreachable_host_timeout(self, api_client: TestClient) -> None:
        resp = api_client.post(
            "/api/accounts/test-connection",
            json={
                "alias": "__timeout_test__",
                "host": "10.255.255.1",
                "port": 22,
                "username": "root",
                "auth_type": "password",
                "password": "anything",
            },
        )
        assert resp.status_code in (200, 500)
        data = resp.json()
        if resp.status_code == 200:
            assert data.get("success") is False
            msg = data.get("message", "").lower()
            assert any(
                kw in msg
                for kw in ["超时", "timeout", "连接失败", "网络错误", "不可达", "无法解析", "拒绝", "banner", "error reading"]
            ), f"超时错误信息不明确: {data.get('message')}"


@pytest.mark.integration
@skip_if_no_ssh
class TestSSHAuthFailure:
    def test_wrong_password_auth_failure(
        self, api_client: TestClient, ssh_config: dict[str, Any]
    ) -> None:
        resp = api_client.post(
            "/api/accounts/test-connection",
            json={
                "alias": "__auth_fail_test__",
                "host": ssh_config["host"],
                "port": ssh_config["port"],
                "username": ssh_config["username"],
                "auth_type": "password",
                "password": "definitely_wrong_password_12345",
            },
        )
        assert resp.status_code in (200, 500)
        data = resp.json()
        if resp.status_code == 200:
            assert data.get("success") is False
            msg = data.get("message", "").lower()
            assert any(
                kw in msg
                for kw in ["认证失败", "认证", "auth", "denied", "密码", "password"]
            ), f"认证失败错误信息不明确: {data.get('message')}"


@pytest.mark.integration
@skip_if_no_ssh
class TestDockerPullFailure:
    def test_pull_nonexistent_image(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/docker/images/pull",
            json={
                "account_alias": alias,
                "image_name": "nonexistent-image-xyz:latest",
            },
        )
        assert resp.status_code in (400, 404, 500, 503)
        if resp.status_code not in (503,):
            data = resp.json()
            detail = data.get("detail", "").lower()
            assert any(
                kw in detail
                for kw in ["not found", "未找到", "pull", "failed", "不存在", "error"]
            ), f"拉取失败错误信息不明确: {data.get('detail')}"


@pytest.mark.integration
@skip_if_no_ssh
class TestDockerContainerNotFound:
    def test_get_nonexistent_container(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        fake_id = "nonexistent_container_id_xyz"
        resp = api_client.get(
            f"/api/docker/containers/{fake_id}",
            params={"account_alias": alias},
        )
        assert resp.status_code == 404

    def test_start_nonexistent_container(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        fake_id = "nonexistent_container_id_xyz"
        resp = api_client.post(
            f"/api/docker/containers/{fake_id}/start",
            params={"account_alias": alias},
        )
        assert resp.status_code in (404, 400, 500)

    def test_stop_nonexistent_container(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        fake_id = "nonexistent_container_id_xyz"
        resp = api_client.post(
            f"/api/docker/containers/{fake_id}/stop",
            json={"account_alias": alias},
        )
        assert resp.status_code in (404, 400, 500)

    def test_remove_nonexistent_container(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        fake_id = "nonexistent_container_id_xyz"
        resp = api_client.delete(
            f"/api/docker/containers/{fake_id}",
            params={"account_alias": alias, "force": True},
        )
        assert resp.status_code in (200, 404, 400, 500)


@pytest.mark.integration
@skip_if_no_ssh
class TestConcurrentSSHCommands:
    def test_concurrent_echo_commands(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        num_commands = 5
        results: dict[int, dict[str, Any]] = {}

        def _exec_command(index: int) -> tuple[int, dict[str, Any]]:
            resp = api_client.post(
                "/api/command/exec",
                json={
                    "alias": alias,
                    "command": f"echo concurrent_{index}",
                    "timeout": 15.0,
                },
            )
            return index, resp.json()

        with ThreadPoolExecutor(max_workers=num_commands) as executor:
            futures = [
                executor.submit(_exec_command, i) for i in range(num_commands)
            ]
            for future in as_completed(futures, timeout=60.0):
                index, data = future.result()
                results[index] = data

        assert len(results) == num_commands, (
            f"并发命令数量不匹配: 期望 {num_commands}, 实际 {len(results)}"
        )
        for i in range(num_commands):
            stdout = results[i].get("stdout", "")
            assert f"concurrent_{i}" in stdout, (
                f"命令 {i} 输出不正确: {stdout}"
            )


@pytest.mark.integration
@skip_if_no_ssh
class TestRapidContainerOperations:
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

    def test_rapid_create_and_remove(self) -> None:
        pull_resp = self._api_client.post(
            "/api/docker/images/pull",
            json={
                "account_alias": self._alias,
                "image_name": "hello-world:latest",
            },
        )
        if pull_resp.status_code not in (200,):
            pytest.skip("无法拉取 hello-world 镜像，跳过快速操作测试")

        container_name = f"opsv-rapid-test-{int(time.time())}"
        create_resp = self._api_client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": f"docker create --name {container_name} hello-world:latest",
                "timeout": 30.0,
            },
        )
        assert create_resp.status_code == 200
        container_id = create_resp.json().get("stdout", "").strip()
        if not container_id:
            pytest.skip("无法创建容器，跳过快速操作测试")
        self._container_ids.append(container_id)

        start_resp = self._api_client.post(
            f"/api/docker/containers/{container_id}/start",
            params={"account_alias": self._alias},
        )
        assert start_resp.status_code == 200

        time.sleep(1)

        remove_resp = self._api_client.delete(
            f"/api/docker/containers/{container_id}",
            params={"account_alias": self._alias, "force": True},
        )
        assert remove_resp.status_code == 200
        self._container_ids.remove(container_id)

        verify_resp = self._api_client.get(
            f"/api/docker/containers/{container_id}",
            params={"account_alias": self._alias},
        )
        assert verify_resp.status_code in (404, 500) or (
            verify_resp.status_code == 200
            and verify_resp.json().get("State", {}).get("Status", "") != "running"
        )


@pytest.mark.integration
@skip_if_no_ssh
class TestAPIErrorResponses:
    def test_ssh_account_not_found(self, api_client: TestClient) -> None:
        resp = api_client.get("/api/accounts/__nonexistent_alias__")
        assert resp.status_code == 404
        assert "不存在" in resp.json().get("detail", "")

    def test_docker_info_missing_alias(self, api_client: TestClient) -> None:
        resp = api_client.get("/api/docker/info")
        assert resp.status_code == 422

    def test_docker_containers_missing_alias(self, api_client: TestClient) -> None:
        resp = api_client.get("/api/docker/containers")
        assert resp.status_code == 422

    def test_vite_deploy_check_missing_params(self, api_client: TestClient) -> None:
        resp = api_client.get("/api/deploy/vite/check")
        assert resp.status_code == 422

    def test_vite_deploy_setup_invalid_account(
        self,
        api_client: TestClient,
    ) -> None:
        resp = api_client.post(
            "/api/deploy/vite/setup",
            json={
                "account_alias": "__nonexistent_alias__",
                "project_path": "/tmp/test",
                "node_version": "20",
            },
        )
        assert resp.status_code == 404

    def test_db_toolkit_mysql_query_invalid_account(
        self,
        api_client: TestClient,
    ) -> None:
        resp = api_client.post(
            "/api/db-toolkit/mysql/query",
            json={
                "account_alias": "__nonexistent_alias__",
                "connection": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "",
                    "database": "",
                },
                "sql": "SELECT 1",
            },
        )
        assert resp.status_code == 404

    def test_dangerous_sql_detection(self, api_client: TestClient) -> None:
        resp = api_client.post(
            "/api/db-toolkit/check-dangerous-sql",
            json={"sql": "DROP TABLE users"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_dangerous") is True
        assert data.get("level") == "critical"

    def test_dangerous_sql_safe_query(self, api_client: TestClient) -> None:
        resp = api_client.post(
            "/api/db-toolkit/check-dangerous-sql",
            json={"sql": "SELECT * FROM users WHERE id = 1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_dangerous") is False

    def test_dangerous_redis_detection(self, api_client: TestClient) -> None:
        resp = api_client.post(
            "/api/db-toolkit/check-dangerous-redis",
            json={"command": "FLUSHALL"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_dangerous") is True
        assert data.get("level") == "critical"

    def test_dangerous_redis_safe_command(self, api_client: TestClient) -> None:
        resp = api_client.post(
            "/api/db-toolkit/check-dangerous-redis",
            json={"command": "GET mykey"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("is_dangerous") is False

    def test_vite_deploy_status_nonexistent_task(
        self,
        api_client: TestClient,
    ) -> None:
        resp = api_client.get("/api/deploy/vite/status/nonexistent_task_id")
        assert resp.status_code == 404
