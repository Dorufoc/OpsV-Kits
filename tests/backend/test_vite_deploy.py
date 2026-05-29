"""Vite 部署接口测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """创建 FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_ssh_account():
    """Mock SSH 账户验证，返回有效账户"""
    with patch("app.api.routes.vite_deploy.ssh_account_service") as mock_svc:
        mock_svc.get_account.return_value = MagicMock(alias="test-server")
        yield mock_svc


@pytest.fixture
def mock_vite_deploy_service():
    """Mock Vite 部署服务"""
    with patch("app.api.routes.vite_deploy.vite_deploy_service") as mock_svc:
        yield mock_svc


@pytest.fixture
def sample_task_dict():
    """返回标准任务字典"""
    return {
        "task_id": "task-abc123",
        "account_alias": "test-server",
        "project_path": "/opt/projects/vite-app",
        "step": "build",
        "status": "running",
        "progress": 0.0,
        "message": "开始构建项目...",
        "log": "",
        "started_at": "2024-01-01T00:00:00+00:00",
        "completed_at": None,
        "error": None,
        "url": None,
    }


@pytest.fixture
def mock_task(sample_task_dict):
    """创建模拟任务对象"""
    task = MagicMock()
    task.to_dict.return_value = sample_task_dict
    task.task_id = "task-abc123"
    task.status = "running"
    task.progress = 0.0
    task.message = "开始构建项目..."
    task.step = "build"
    task.log = ""
    task.url = None
    task.add_callback = MagicMock()
    return task


# ─────────────────────────────────────────────
# 环境检测
# ─────────────────────────────────────────────
class TestEnvironmentCheck:
    """环境检测接口测试 (GET /check)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_check_environment_all_ready(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.check_environment.return_value = {
            "account_alias": "test-server",
            "project_path": "/opt/projects/vite-app",
            "node": {"installed": True, "version": "v20.10.0", "npm_installed": True},
            "nginx": {"installed": True, "running": True},
            "vite": {"is_vite": True, "has_package_json": True},
            "framework": {"name": "vue", "version": "3.3.0"},
            "all_ready": True,
        }
        resp = client.get(
            "/api/deploy/vite/check?account_alias=test-server&project_path=/opt/projects/vite-app"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_ready"] is True
        assert data["node"]["installed"] is True
        assert data["framework"]["name"] == "vue"

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_check_environment_not_ready(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.check_environment.return_value = {
            "account_alias": "test-server",
            "project_path": "/opt/projects/vite-app",
            "node": {"installed": False, "version": "", "npm_installed": False},
            "nginx": {"installed": False, "running": False},
            "vite": {"is_vite": False, "has_package_json": False},
            "framework": {"name": None, "version": None},
            "all_ready": False,
        }
        resp = client.get(
            "/api/deploy/vite/check?account_alias=test-server&project_path=/opt/projects/vite-app"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_ready"] is False

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_check_environment_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.get(
            "/api/deploy/vite/check?account_alias=nonexistent&project_path=/opt/project"
        )
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_check_environment_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.check_environment.side_effect = RuntimeError("SSH 连接失败")
        resp = client.get(
            "/api/deploy/vite/check?account_alias=test-server&project_path=/opt/project"
        )
        assert resp.status_code == 500


# ─────────────────────────────────────────────
# 安装 Node.js
# ─────────────────────────────────────────────
class TestSetupNode:
    """安装 Node.js 接口测试 (POST /setup)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_setup_success(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_node.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/setup",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
                "node_version": "20",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        assert data["status"] == "running"
        assert data["step"] == "build"
        mock_svc.install_node.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            version="20",
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_setup_default_version(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_node.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/setup",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
            },
        )
        assert resp.status_code == 200
        mock_svc.install_node.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            version="20",
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_setup_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/deploy/vite/setup",
            json={
                "account_alias": "nonexistent",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 404

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_setup_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_node.side_effect = RuntimeError("远程执行失败")
        resp = client.post(
            "/api/deploy/vite/setup",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 500

    def test_setup_missing_required_fields(self, client):
        resp = client.post(
            "/api/deploy/vite/setup",
            json={"account_alias": "test-server"},
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────
# 安装依赖
# ─────────────────────────────────────────────
class TestInstallDeps:
    """安装依赖接口测试 (POST /install-deps)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_install_deps_success(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_deps.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/install-deps",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
                "force": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        mock_svc.install_deps.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            force=False,
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_install_deps_force(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_deps.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/install-deps",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
                "force": True,
            },
        )
        assert resp.status_code == 200
        mock_svc.install_deps.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            force=True,
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_install_deps_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/deploy/vite/install-deps",
            json={
                "account_alias": "nonexistent",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 404

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_install_deps_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.install_deps.side_effect = RuntimeError("依赖安装失败")
        resp = client.post(
            "/api/deploy/vite/install-deps",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 500


# ─────────────────────────────────────────────
# 构建项目
# ─────────────────────────────────────────────
class TestBuildProject:
    """构建项目接口测试 (POST /build)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_build_success(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.build.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/build",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
                "build_command": "npm run build",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        mock_svc.build.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            build_command="npm run build",
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_build_custom_command(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.build.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/build",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
                "build_command": "pnpm build --mode production",
            },
        )
        assert resp.status_code == 200
        mock_svc.build.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            build_command="pnpm build --mode production",
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_build_default_command(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.build.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/build",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/projects/vite-app",
            },
        )
        assert resp.status_code == 200
        mock_svc.build.assert_called_once_with(
            account_alias="test-server",
            project_path="/opt/projects/vite-app",
            build_command="npm run build",
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_build_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/deploy/vite/build",
            json={
                "account_alias": "nonexistent",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 404

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_build_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.build.side_effect = RuntimeError("构建启动失败")
        resp = client.post(
            "/api/deploy/vite/build",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 500


# ─────────────────────────────────────────────
# 配置 Nginx
# ─────────────────────────────────────────────
class TestDeployNginx:
    """配置 Nginx 接口测试 (POST /nginx)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_nginx_success(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.deploy_nginx.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={
                "account_alias": "test-server",
                "project_alias": "my-vite-app",
                "project_path": "/opt/projects/vite-app",
                "port": 8080,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        mock_svc.deploy_nginx.assert_called_once_with(
            account_alias="test-server",
            project_alias="my-vite-app",
            project_path="/opt/projects/vite-app",
            port=8080,
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_nginx_default_port(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.deploy_nginx.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={
                "account_alias": "test-server",
                "project_alias": "my-vite-app",
                "project_path": "/opt/projects/vite-app",
            },
        )
        assert resp.status_code == 200
        mock_svc.deploy_nginx.assert_called_once_with(
            account_alias="test-server",
            project_alias="my-vite-app",
            project_path="/opt/projects/vite-app",
            port=8080,
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_nginx_custom_port(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.deploy_nginx.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={
                "account_alias": "test-server",
                "project_alias": "my-vite-app",
                "project_path": "/opt/projects/vite-app",
                "port": 3000,
            },
        )
        assert resp.status_code == 200
        mock_svc.deploy_nginx.assert_called_once_with(
            account_alias="test-server",
            project_alias="my-vite-app",
            project_path="/opt/projects/vite-app",
            port=3000,
        )

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_nginx_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={
                "account_alias": "nonexistent",
                "project_alias": "my-app",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 404

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_nginx_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.deploy_nginx.side_effect = RuntimeError("Nginx 配置失败")
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={
                "account_alias": "test-server",
                "project_alias": "my-app",
                "project_path": "/opt/project",
                "port": 8080,
            },
        )
        assert resp.status_code == 500

    def test_nginx_missing_required_fields(self, client):
        resp = client.post(
            "/api/deploy/vite/nginx",
            json={"account_alias": "test-server"},
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────
# 一键部署
# ─────────────────────────────────────────────
class TestFullDeploy:
    """一键部署接口测试 (POST /deploy)"""

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_deploy_success(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.full_deploy.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={
                "account_alias": "test-server",
                "project_alias": "my-vite-app",
                "project_path": "/opt/projects/vite-app",
                "node_version": "20",
                "nginx_port": 8080,
                "build_command": "npm run build",
                "force": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        mock_svc.full_deploy.assert_called_once()
        call_kwargs = mock_svc.full_deploy.call_args
        assert call_kwargs.kwargs["account_alias"] == "test-server"
        assert call_kwargs.kwargs["project_alias"] == "my-vite-app"
        assert call_kwargs.kwargs["project_path"] == "/opt/projects/vite-app"
        assert call_kwargs.kwargs["config"]["node_version"] == "20"
        assert call_kwargs.kwargs["config"]["nginx_port"] == 8080

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_deploy_with_defaults(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.full_deploy.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={
                "account_alias": "test-server",
                "project_alias": "my-app",
                "project_path": "/opt/projects/app",
            },
        )
        assert resp.status_code == 200
        call_kwargs = mock_svc.full_deploy.call_args
        cfg = call_kwargs.kwargs["config"]
        assert cfg["node_version"] == "20"
        assert cfg["nginx_port"] == 8080
        assert cfg["build_command"] == "npm run build"
        assert cfg["force"] is False

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_deploy_force_true(self, mock_svc, mock_ssh, client, mock_task):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.full_deploy.return_value = mock_task
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={
                "account_alias": "test-server",
                "project_alias": "my-app",
                "project_path": "/opt/projects/app",
                "force": True,
            },
        )
        assert resp.status_code == 200
        call_kwargs = mock_svc.full_deploy.call_args
        assert call_kwargs.kwargs["config"]["force"] is True

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    def test_deploy_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={
                "account_alias": "nonexistent",
                "project_alias": "my-app",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 404

    @patch("app.api.routes.vite_deploy.ssh_account_service")
    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_deploy_service_error(self, mock_svc, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_svc.full_deploy.side_effect = RuntimeError("部署启动失败")
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={
                "account_alias": "test-server",
                "project_alias": "my-app",
                "project_path": "/opt/project",
            },
        )
        assert resp.status_code == 500

    def test_deploy_missing_required_fields(self, client):
        resp = client.post(
            "/api/deploy/vite/deploy",
            json={"account_alias": "test-server"},
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────
# 任务状态查询
# ─────────────────────────────────────────────
class TestTaskStatus:
    """任务状态查询接口测试 (GET /status/{task_id})"""

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_status_success(self, mock_svc, client, sample_task_dict):
        mock_svc.get_task_dict.return_value = sample_task_dict
        resp = client.get("/api/deploy/vite/status/task-abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "task-abc123"
        assert data["status"] == "running"
        assert data["progress"] == 0.0

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_status_completed(self, mock_svc, client):
        mock_svc.get_task_dict.return_value = {
            "task_id": "task-done",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "step": "build",
            "status": "completed",
            "progress": 100.0,
            "message": "构建成功",
            "log": "构建日志...",
            "started_at": "2024-01-01T00:00:00+00:00",
            "completed_at": "2024-01-01T00:05:00+00:00",
            "error": None,
            "url": "http://example.com:8080",
        }
        resp = client.get("/api/deploy/vite/status/task-done")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        assert data["url"] == "http://example.com:8080"

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_status_failed(self, mock_svc, client):
        mock_svc.get_task_dict.return_value = {
            "task_id": "task-fail",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "step": "build",
            "status": "failed",
            "progress": 45.0,
            "message": "构建失败 (exit_code=1)",
            "log": "错误日志...",
            "started_at": "2024-01-01T00:00:00+00:00",
            "completed_at": "2024-01-01T00:03:00+00:00",
            "error": "构建失败 (exit_code=1)",
            "url": None,
        }
        resp = client.get("/api/deploy/vite/status/task-fail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["message"] == "构建失败 (exit_code=1)"

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_status_stopped(self, mock_svc, client):
        mock_svc.get_task_dict.return_value = {
            "task_id": "task-stop",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "step": "full_deploy",
            "status": "stopped",
            "progress": 60.0,
            "message": "部署已被用户停止",
            "log": "",
            "started_at": "2024-01-01T00:00:00+00:00",
            "completed_at": "2024-01-01T00:02:00+00:00",
            "error": None,
            "url": None,
        }
        resp = client.get("/api/deploy/vite/status/task-stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_status_task_not_found(self, mock_svc, client):
        mock_svc.get_task_dict.return_value = None
        resp = client.get("/api/deploy/vite/status/nonexistent-task")
        assert resp.status_code == 404
        data = resp.json()
        assert "不存在" in data["detail"]


# ─────────────────────────────────────────────
# 任务历史
# ─────────────────────────────────────────────
class TestTaskHistory:
    """任务历史接口测试 (GET /history)"""

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_with_account(self, mock_svc, client):
        mock_svc.list_tasks.return_value = [
            {
                "task_id": "task-1",
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "step": "build",
                "status": "completed",
                "progress": 100.0,
                "message": "构建成功",
                "log": "",
                "started_at": "2024-01-01T00:00:00+00:00",
                "completed_at": "2024-01-01T00:05:00+00:00",
                "error": None,
                "url": None,
            },
            {
                "task_id": "task-2",
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "step": "deploy_nginx",
                "status": "running",
                "progress": 50.0,
                "message": "部署中",
                "log": "",
                "started_at": "2024-01-01T00:06:00+00:00",
                "completed_at": None,
                "error": None,
                "url": None,
            },
        ]
        resp = client.get("/api/deploy/vite/history?account_alias=test-server&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 2
        mock_svc.list_tasks.assert_called_once_with(account_alias="test-server", limit=10)

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_without_account(self, mock_svc, client):
        mock_svc.list_tasks.return_value = []
        resp = client.get("/api/deploy/vite/history?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"] == []
        mock_svc.list_tasks.assert_called_once_with(account_alias=None, limit=5)

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_empty_result(self, mock_svc, client):
        mock_svc.list_tasks.return_value = []
        resp = client.get("/api/deploy/vite/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tasks"] == []

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_default_limit(self, mock_svc, client):
        mock_svc.list_tasks.return_value = []
        resp = client.get("/api/deploy/vite/history")
        mock_svc.list_tasks.assert_called_once_with(account_alias=None, limit=20)

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_max_limit(self, mock_svc, client):
        mock_svc.list_tasks.return_value = []
        resp = client.get("/api/deploy/vite/history?limit=200")
        assert resp.status_code == 200

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_limit_too_large(self, mock_svc, client):
        resp = client.get("/api/deploy/vite/history?limit=999")
        assert resp.status_code == 422

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_history_limit_too_small(self, mock_svc, client):
        resp = client.get("/api/deploy/vite/history?limit=0")
        assert resp.status_code == 422


# ─────────────────────────────────────────────
# WebSocket 日志
# ─────────────────────────────────────────────
class TestWebSocketLogs:
    """WebSocket 日志接口测试 (WebSocket /ws/logs/{task_id})"""

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_ws_connect_success(self, mock_svc, client, mock_task):
        mock_svc.get_task.return_value = mock_task
        with client.websocket_connect("/api/deploy/vite/ws/logs/task-abc123") as ws:
            # 首先接收 task_info 消息
            data = ws.receive_json()
            assert data["type"] == "task_info"
            assert data["data"]["task_id"] == "task-abc123"

            # 发送 ping 消息，应收到 pong
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

            # 发送 get_log 消息
            ws.send_json({"type": "get_log"})
            log_data = ws.receive_json()
            assert log_data["type"] == "log_update"
            assert "data" in log_data

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_ws_task_not_found(self, mock_svc, client):
        mock_svc.get_task.return_value = None
        with client.websocket_connect("/api/deploy/vite/ws/logs/nonexistent-task") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不存在" in data["message"]

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_ws_invalid_json(self, mock_svc, client, mock_task):
        mock_svc.get_task.return_value = mock_task
        with client.websocket_connect("/api/deploy/vite/ws/logs/task-abc123") as ws:
            # 先接收 task_info
            ws.receive_json()
            # 发送无效 JSON (WebSocket 的 send_text 发送非 JSON 字符串)
            ws.send_text("not a valid json")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "无效" in data["message"]

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_ws_unknown_message_type(self, mock_svc, client, mock_task):
        mock_svc.get_task.return_value = mock_task
        with client.websocket_connect("/api/deploy/vite/ws/logs/task-abc123") as ws:
            # 先接收 task_info
            ws.receive_json()
            # 发送未知消息类型
            ws.send_json({"type": "unknown_type"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "未知" in data["message"]

    @patch("app.api.routes.vite_deploy.vite_deploy_service")
    def test_ws_disconnect_graceful(self, mock_svc, client, mock_task):
        mock_svc.get_task.return_value = mock_task
        with client.websocket_connect("/api/deploy/vite/ws/logs/task-abc123") as ws:
            # 接收 task_info 后关闭连接
            ws.receive_json()
            # WebSocket 上下文管理器退出时会自动关闭连接
