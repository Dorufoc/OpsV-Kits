from __future__ import annotations

import os
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

skip_if_no_ssh = pytest.mark.skipif(
    not os.environ.get("OPSV_SSH_HOST"),
    reason="集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。",
)

skip_if_no_vite = pytest.mark.skipif(
    not os.environ.get("OPSV_VITE_TEST", ""),
    reason="Vite 部署测试跳过：未设置 OPSV_VITE_TEST=1 环境变量。",
)

TEST_PROJECT_DIR = "/tmp/opsv-vite-test-project"
TEST_PROJECT_ALIAS = "opsv-vite-test"


def _wait_for_task_completion(
    api_client: TestClient,
    task_id: str,
    timeout: float = 300.0,
    poll_interval: float = 3.0,
) -> dict[str, Any]:
    start = time.time()
    while time.time() - start < timeout:
        resp = api_client.get(f"/deploy/vite/status/{task_id}")
        if resp.status_code != 200:
            time.sleep(poll_interval)
            continue
        data = resp.json()
        status = data.get("status", "")
        if status in ("completed", "failed", "stopped"):
            return data
        time.sleep(poll_interval)
    return {"status": "timeout", "message": f"任务 {task_id} 在 {timeout}s 内未完成"}


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_vite
class TestViteEnvironmentCheck:
    def test_check_node_environment(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/deploy/vite/check",
            params={
                "account_alias": alias,
                "project_path": "/tmp",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "node" in data
        assert "nginx" in data
        assert "vite" in data
        assert "all_ready" in data

        node_info = data["node"]
        if node_info.get("installed"):
            version = node_info.get("version", "")
            assert len(version) > 0, "Node.js 已安装但版本号为空"


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_vite
class TestViteProjectBuild:
    @pytest.fixture(autouse=True)
    def _setup_and_cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        self._api_client.post(
            "/command/exec",
            json={
                "alias": self._alias,
                "command": f"rm -rf {TEST_PROJECT_DIR}",
                "timeout": 15.0,
            },
        )

    def test_create_and_build_vite_project(self) -> None:
        alias = self._alias

        create_resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": (
                    f"mkdir -p {TEST_PROJECT_DIR} && "
                    f"cd {TEST_PROJECT_DIR} && "
                    f'echo \'{{"name":"opsv-test","version":"1.0.0","scripts":{{"build":"vite build"}},"devDependencies":{{"vite":"^5.0.0"}}}}\' > package.json && '
                    f"npm install 2>&1"
                ),
                "timeout": 120.0,
            },
        )
        assert create_resp.status_code == 200
        create_data = create_resp.json()
        assert create_data.get("exit_code", -1) == 0, (
            f"Vite 项目创建失败: {create_data.get('stderr', '')}"
        )

        index_resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": (
                    f"mkdir -p {TEST_PROJECT_DIR}/src && "
                    f"echo '<!DOCTYPE html><html><body><div id=\"app\"></div><script type=\"module\" src=\"/src/main.js\"></script></body></html>' > {TEST_PROJECT_DIR}/index.html && "
                    f"echo 'document.getElementById(\"app\").textContent = \"Hello OpsV\";' > {TEST_PROJECT_DIR}/src/main.js && "
                    f"echo 'import {{ defineConfig }} from \"vite\"; export default defineConfig({{}});' > {TEST_PROJECT_DIR}/vite.config.js"
                ),
                "timeout": 15.0,
            },
        )
        assert index_resp.status_code == 200

        build_resp = self._api_client.post(
            "/deploy/vite/build",
            json={
                "account_alias": alias,
                "project_path": TEST_PROJECT_DIR,
                "build_command": "npx vite build",
            },
        )
        assert build_resp.status_code == 200
        task_data = build_resp.json()
        task_id = task_data.get("task_id")
        assert task_id is not None

        result = _wait_for_task_completion(self._api_client, task_id, timeout=120.0)
        assert result.get("status") == "completed", (
            f"Vite 构建任务失败: {result.get('error', result.get('message', ''))}"
        )

        verify_resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": f"test -d {TEST_PROJECT_DIR}/dist && echo 'dist_exists'",
                "timeout": 10.0,
            },
        )
        assert verify_resp.status_code == 200
        assert "dist_exists" in verify_resp.json().get("stdout", ""), (
            "构建完成后 dist 目录不存在"
        )


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_vite
class TestViteNginxConfig:
    @pytest.fixture(autouse=True)
    def _setup_and_cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        self._api_client.post(
            "/command/exec",
            json={
                "alias": self._alias,
                "command": (
                    f"rm -rf {TEST_PROJECT_DIR} && "
                    f"rm -f /etc/nginx/conf.d/{TEST_PROJECT_ALIAS}.conf"
                ),
                "timeout": 10.0,
            },
        )

    def test_generate_nginx_config(self) -> None:
        alias = self._alias

        self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": f"mkdir -p {TEST_PROJECT_DIR}/dist && echo 'test' > {TEST_PROJECT_DIR}/dist/index.html",
                "timeout": 10.0,
            },
        )

        nginx_resp = self._api_client.post(
            "/deploy/vite/nginx",
            json={
                "account_alias": alias,
                "project_alias": TEST_PROJECT_ALIAS,
                "project_path": TEST_PROJECT_DIR,
                "port": 8888,
            },
        )
        assert nginx_resp.status_code == 200
        task_data = nginx_resp.json()
        task_id = task_data.get("task_id")
        assert task_id is not None

        result = _wait_for_task_completion(self._api_client, task_id, timeout=60.0)
        assert result.get("status") in ("completed", "failed"), (
            f"Nginx 配置任务异常: {result}"
        )

        if result.get("status") == "completed":
            verify_resp = self._api_client.post(
                "/command/exec",
                json={
                    "alias": alias,
                    "command": f"test -f /etc/nginx/conf.d/{TEST_PROJECT_ALIAS}.conf && echo 'config_exists'",
                    "timeout": 10.0,
                },
            )
            if verify_resp.status_code == 200:
                stdout = verify_resp.json().get("stdout", "")
                if "config_exists" in stdout:
                    syntax_resp = self._api_client.post(
                        "/command/exec",
                        json={
                            "alias": alias,
                            "command": "nginx -t 2>&1",
                            "timeout": 10.0,
                        },
                    )
                    if syntax_resp.status_code == 200:
                        syntax_out = syntax_resp.json().get("stdout", "") + syntax_resp.json().get("stderr", "")
                        assert "successful" in syntax_out.lower() or "ok" in syntax_out.lower(), (
                            f"Nginx 配置语法检查失败: {syntax_out}"
                        )


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_vite
class TestViteFullDeploy:
    @pytest.fixture(autouse=True)
    def _setup_and_cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        self._api_client.post(
            "/command/exec",
            json={
                "alias": self._alias,
                "command": (
                    f"rm -rf {TEST_PROJECT_DIR} && "
                    f"rm -f /etc/nginx/conf.d/{TEST_PROJECT_ALIAS}.conf"
                ),
                "timeout": 10.0,
            },
        )

    def test_full_deploy_pipeline(self) -> None:
        alias = self._alias

        self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": (
                    f"mkdir -p {TEST_PROJECT_DIR}/src && "
                    f'cd {TEST_PROJECT_DIR} && '
                    f'echo \'{{"name":"opsv-test","version":"1.0.0","scripts":{{"build":"vite build"}},"devDependencies":{{"vite":"^5.0.0"}}}}\' > package.json && '
                    f"echo '<!DOCTYPE html><html><body><div id=\"app\"></div><script type=\"module\" src=\"/src/main.js\"></script></body></html>' > index.html && "
                    f"echo 'document.getElementById(\"app\").textContent = \"Hello OpsV Full Deploy\";' > src/main.js && "
                    f"echo 'import {{ defineConfig }} from \"vite\"; export default defineConfig({{}});' > vite.config.js && "
                    f"npm install 2>&1"
                ),
                "timeout": 120.0,
            },
        )

        deploy_resp = self._api_client.post(
            "/deploy/vite/deploy",
            json={
                "account_alias": alias,
                "project_alias": TEST_PROJECT_ALIAS,
                "project_path": TEST_PROJECT_DIR,
                "node_version": "20",
                "nginx_port": 8889,
                "build_command": "npx vite build",
                "force": False,
            },
        )
        assert deploy_resp.status_code == 200
        task_data = deploy_resp.json()
        task_id = task_data.get("task_id")
        assert task_id is not None

        result = _wait_for_task_completion(self._api_client, task_id, timeout=300.0)
        assert result.get("status") == "completed", (
            f"一键部署失败: {result.get('error', result.get('message', ''))}"
        )

        dist_resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": alias,
                "command": f"test -d {TEST_PROJECT_DIR}/dist && echo 'dist_ok'",
                "timeout": 10.0,
            },
        )
        if dist_resp.status_code == 200:
            assert "dist_ok" in dist_resp.json().get("stdout", ""), (
                "一键部署后 dist 目录不存在"
            )
