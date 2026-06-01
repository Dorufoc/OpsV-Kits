from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

WHOAMI_PORT = 8101
REDIS_PORT = 6380
REDIS_PASSWORD = "opsv_test_redis_123"
NGINX_PORT = 8180

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


def _find_container_by_name(
    containers: list[dict[str, Any]], name_prefix: str
) -> list[dict[str, Any]]:
    return [
        c
        for c in containers
        if c.get("name", "").startswith(name_prefix)
        or c.get("Names", "").startswith(name_prefix)
    ]


def _is_container_running(container: dict[str, Any]) -> bool:
    state = container.get("state", container.get("State", ""))
    return state.lower() == "running" if isinstance(state, str) else False


def _install_app(
    api_client: TestClient,
    alias: str,
    app_id: str,
    user_config: dict[str, Any],
) -> dict[str, Any]:
    resp = api_client.post(
        f"/api/docker-store/install/{app_id}",
        json={"account_alias": alias, "user_config": user_config},
    )
    assert resp.status_code == 200, f"安装应用失败 [{app_id}]: {resp.text}"
    return resp.json()


def _uninstall_app(
    api_client: TestClient,
    alias: str,
    app_id: str,
    purge_data: bool = False,
) -> dict[str, Any]:
    resp = api_client.post(
        f"/api/docker-store/uninstall/{app_id}",
        json={"account_alias": alias, "purge_data": purge_data},
    )
    assert resp.status_code == 200, f"卸载应用失败 [{app_id}]: {resp.text}"
    return resp.json()


def _get_app_status(
    api_client: TestClient,
    alias: str,
    app_id: str,
) -> dict[str, Any]:
    resp = api_client.get(
        f"/api/docker-store/status/{app_id}",
        params={"account_alias": alias},
    )
    assert resp.status_code == 200, f"查询应用状态失败 [{app_id}]: {resp.text}"
    return resp.json()


def _force_cleanup_app(
    api_client: TestClient,
    alias: str,
    app_id: str,
) -> None:
    try:
        _uninstall_app(api_client, alias, app_id, purge_data=True)
    except Exception:
        pass
    try:
        _exec_remote(api_client, alias, f"rm -rf /www/server/apps/{app_id}", timeout=15.0)
    except Exception:
        pass


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreInstallWhoami:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "whoami")

    def test_install_whoami_and_verify(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "whoami",
            {"WHOAMI_PORT": str(WHOAMI_PORT)},
        )

        time.sleep(CONTAINER_START_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        whoami_containers = _find_container_by_name(containers, "panel-whoami")
        assert len(whoami_containers) > 0, "未找到 whoami 容器"
        assert _is_container_running(whoami_containers[0]), "whoami 容器未运行"

        curl_result = _exec_remote(
            self._client,
            self._alias,
            f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{WHOAMI_PORT}/",
            timeout=10.0,
        )
        stdout = curl_result.get("stdout", "").strip().strip("'\"")
        assert stdout == "200", f"whoami HTTP 请求未返回 200，实际: {stdout}"

        _uninstall_app(self._client, self._alias, "whoami")

        time.sleep(CONTAINER_STOP_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        whoami_containers = _find_container_by_name(containers, "panel-whoami")
        assert len(whoami_containers) == 0, "卸载后 whoami 容器仍然存在"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreInstallRedis:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "redis")

    def test_install_redis_and_verify_data_rw(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "redis",
            {"REDIS_PORT": str(REDIS_PORT), "REDIS_PASSWORD": REDIS_PASSWORD},
        )

        time.sleep(CONTAINER_START_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        redis_containers = _find_container_by_name(containers, "panel-redis")
        assert len(redis_containers) > 0, "未找到 Redis 容器"
        assert _is_container_running(redis_containers[0]), "Redis 容器未运行"

        set_result = _exec_remote(
            self._client,
            self._alias,
            f"docker exec panel-redis redis-cli -a {REDIS_PASSWORD} SET opsv:test:key 'hello_opsv'",
            timeout=10.0,
        )
        assert "OK" in set_result.get("stdout", ""), f"Redis SET 失败: {set_result}"

        get_result = _exec_remote(
            self._client,
            self._alias,
            f"docker exec panel-redis redis-cli -a {REDIS_PASSWORD} GET opsv:test:key",
            timeout=10.0,
        )
        assert "hello_opsv" in get_result.get("stdout", ""), f"Redis GET 失败: {get_result}"

        _uninstall_app(self._client, self._alias, "redis")

        time.sleep(CONTAINER_STOP_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        redis_containers = _find_container_by_name(containers, "panel-redis")
        assert len(redis_containers) == 0, "卸载后 Redis 容器仍然存在"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreInstallNginx:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "nginx")

    def test_install_nginx_and_verify_http(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "nginx",
            {"NGINX_PORT": str(NGINX_PORT)},
        )

        time.sleep(CONTAINER_START_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        nginx_containers = _find_container_by_name(containers, "panel-nginx")
        assert len(nginx_containers) > 0, "未找到 Nginx 容器"
        assert _is_container_running(nginx_containers[0]), "Nginx 容器未运行"

        curl_result = _exec_remote(
            self._client,
            self._alias,
            f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{NGINX_PORT}/",
            timeout=10.0,
        )
        stdout = curl_result.get("stdout", "").strip().strip("'\"")
        assert stdout in ("200", "403"), f"Nginx HTTP 请求未返回 200 或 403，实际: {stdout}"

        body_result = _exec_remote(
            self._client,
            self._alias,
            f"curl -s http://127.0.0.1:{NGINX_PORT}/",
            timeout=10.0,
        )
        body = body_result.get("stdout", "")
        assert "Welcome to nginx" in body or "nginx" in body.lower() or "403" in body or "Forbidden" in body, (
            f"Nginx 默认页面内容异常: {body[:200]}"
        )

        _uninstall_app(self._client, self._alias, "nginx")

        time.sleep(CONTAINER_STOP_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()
        nginx_containers = _find_container_by_name(containers, "panel-nginx")
        assert len(nginx_containers) == 0, "卸载后 Nginx 容器仍然存在"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreBatchInstall:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        for app_id in ("whoami", "redis", "nginx"):
            _force_cleanup_app(self._client, self._alias, app_id)

    def test_batch_install_and_verify_all(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "whoami",
            {"WHOAMI_PORT": str(WHOAMI_PORT)},
        )
        _install_app(
            self._client,
            self._alias,
            "redis",
            {"REDIS_PORT": str(REDIS_PORT), "REDIS_PASSWORD": REDIS_PASSWORD},
        )
        _install_app(
            self._client,
            self._alias,
            "nginx",
            {"NGINX_PORT": str(NGINX_PORT)},
        )

        time.sleep(CONTAINER_START_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias},
        )
        assert resp.status_code == 200
        containers = resp.json()

        for prefix in ("panel-whoami", "panel-redis", "panel-nginx"):
            matched = _find_container_by_name(containers, prefix)
            assert len(matched) > 0, f"未找到 {prefix} 容器"
            assert _is_container_running(matched[0]), f"{prefix} 容器未运行"

        for app_id in ("whoami", "redis", "nginx"):
            _uninstall_app(self._client, self._alias, app_id)

        time.sleep(CONTAINER_STOP_WAIT)

        resp = self._client.get(
            "/api/docker/containers",
            params={"account_alias": self._alias, "all": True},
        )
        assert resp.status_code == 200
        containers = resp.json()

        for prefix in ("panel-whoami", "panel-redis", "panel-nginx"):
            matched = _find_container_by_name(containers, prefix)
            assert len(matched) == 0, f"卸载后 {prefix} 容器仍然存在"


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreStatusQuery:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "whoami")

    def test_status_query_returns_correct_info(self) -> None:
        status_before = _get_app_status(self._client, self._alias, "whoami")
        assert status_before.get("running") is False, (
            f"安装前 whoami 不应为运行状态: {status_before}"
        )

        _install_app(
            self._client,
            self._alias,
            "whoami",
            {"WHOAMI_PORT": str(WHOAMI_PORT)},
        )

        time.sleep(CONTAINER_START_WAIT)

        status_after = _get_app_status(self._client, self._alias, "whoami")
        assert status_after.get("running") is True, (
            f"安装后 whoami 应为运行状态: {status_after}"
        )
        assert status_after.get("app_id") == "whoami"
        assert status_after.get("running_count", 0) > 0, (
            f"运行容器数应大于0: {status_after}"
        )
        containers = status_after.get("containers", [])
        assert len(containers) > 0, "状态应包含容器信息"

        all_statuses = self._client.get(
            "/api/docker-store/status",
            params={"account_alias": self._alias},
        )
        assert all_statuses.status_code == 200
        all_data = all_statuses.json()
        assert isinstance(all_data, list)
        whoami_entry = [e for e in all_data if e.get("app_id") == "whoami"]
        assert len(whoami_entry) > 0, "全局状态列表中应包含 whoami"
        assert whoami_entry[0].get("state") in ("running",), (
            f"全局状态中 whoami 应为 running: {whoami_entry[0]}"
        )

        _uninstall_app(self._client, self._alias, "whoami")

        time.sleep(CONTAINER_STOP_WAIT)

        status_final = _get_app_status(self._client, self._alias, "whoami")
        assert status_final.get("running") is False, (
            f"卸载后 whoami 不应为运行状态: {status_final}"
        )


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreUninstallPreserveData:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "redis")

    def test_uninstall_preserve_data_and_reinstall_recovery(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "redis",
            {"REDIS_PORT": str(REDIS_PORT), "REDIS_PASSWORD": REDIS_PASSWORD},
        )

        time.sleep(CONTAINER_START_WAIT)

        set_result = _exec_remote(
            self._client,
            self._alias,
            f"docker exec panel-redis redis-cli -a {REDIS_PASSWORD} SET opsv:persist:test 'persistent_value'",
            timeout=10.0,
        )
        assert "OK" in set_result.get("stdout", ""), f"Redis SET 失败: {set_result}"

        check_dir = _exec_remote(
            self._client,
            self._alias,
            "ls -la /www/server/apps/redis/data/",
            timeout=10.0,
        )
        assert check_dir.get("exit_code", -1) == 0, (
            f"Redis 数据目录应存在: {check_dir}"
        )

        _uninstall_app(self._client, self._alias, "redis", purge_data=False)

        time.sleep(CONTAINER_STOP_WAIT)

        dir_exists = _exec_remote(
            self._client,
            self._alias,
            "test -d /www/server/apps/redis/data && echo 'EXISTS' || echo 'NOT_EXISTS'",
            timeout=10.0,
        )
        assert "EXISTS" in dir_exists.get("stdout", ""), (
            f"卸载（保留数据）后数据目录应存在: {dir_exists}"
        )

        _install_app(
            self._client,
            self._alias,
            "redis",
            {"REDIS_PORT": str(REDIS_PORT), "REDIS_PASSWORD": REDIS_PASSWORD},
        )

        time.sleep(CONTAINER_START_WAIT)

        get_result = _exec_remote(
            self._client,
            self._alias,
            f"docker exec panel-redis redis-cli -a {REDIS_PASSWORD} GET opsv:persist:test",
            timeout=10.0,
        )
        assert "persistent_value" in get_result.get("stdout", ""), (
            f"重装后数据应可恢复: {get_result}"
        )

        _uninstall_app(self._client, self._alias, "redis", purge_data=True)

        time.sleep(CONTAINER_STOP_WAIT)

        dir_gone = _exec_remote(
            self._client,
            self._alias,
            "test -d /www/server/apps/redis/data && echo 'EXISTS' || echo 'NOT_EXISTS'",
            timeout=10.0,
        )
        assert "NOT_EXISTS" in dir_gone.get("stdout", ""), (
            f"最终清理后数据目录不应存在: {dir_gone}"
        )


@pytest.mark.integration
@pytest.mark.docker
class TestDockerStoreUninstallPurgeData:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        _force_cleanup_app(self._client, self._alias, "nginx")

    def test_uninstall_purge_data_removes_volume(self) -> None:
        _install_app(
            self._client,
            self._alias,
            "nginx",
            {"NGINX_PORT": str(NGINX_PORT)},
        )

        time.sleep(CONTAINER_START_WAIT)

        check_dir = _exec_remote(
            self._client,
            self._alias,
            "test -d /www/server/apps/nginx/data && echo 'EXISTS' || echo 'NOT_EXISTS'",
            timeout=10.0,
        )
        assert "EXISTS" in check_dir.get("stdout", ""), (
            f"安装后 Nginx 数据目录应存在: {check_dir}"
        )

        _uninstall_app(self._client, self._alias, "nginx", purge_data=True)

        time.sleep(CONTAINER_STOP_WAIT)

        dir_gone = _exec_remote(
            self._client,
            self._alias,
            "test -d /www/server/apps/nginx && echo 'EXISTS' || echo 'NOT_EXISTS'",
            timeout=10.0,
        )
        assert "NOT_EXISTS" in dir_gone.get("stdout", ""), (
            f"卸载（清除数据）后应用目录不应存在: {dir_gone}"
        )
