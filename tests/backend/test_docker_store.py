"""Docker 应用商店管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def docker_error():
    from app.services.docker_service import DockerCommandError
    return DockerCommandError("command failed", 1, "error output")


class TestDockerStoreApps:
    """Docker 应用商店列表与详情测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_success(self, mock_store_service, mock_ssh_service, client):
        """测试获取应用列表成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.list_apps.return_value = [
            {"id": "nginx", "name": "Nginx", "category": "web"},
            {"id": "mysql", "name": "MySQL", "category": "database"},
        ]

        response = client.get("/api/docker-store/apps?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "nginx"

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_with_category_filter(self, mock_store_service, mock_ssh_service, client):
        """测试按分类过滤应用列表"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.list_apps.return_value = [
            {"id": "nginx", "name": "Nginx", "category": "web"},
        ]

        response = client.get("/api/docker-store/apps?account_alias=test-server&category=web")
        assert response.status_code == 200
        mock_store_service.list_apps.assert_called_with("test-server", category="web")

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_no_category_filter(self, mock_store_service, mock_ssh_service, client):
        """测试不指定分类过滤"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.list_apps.return_value = []

        response = client.get("/api/docker-store/apps?account_alias=test-server")
        assert response.status_code == 200
        mock_store_service.list_apps.assert_called_with("test-server", category=None)

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_list_apps_account_not_found(self, mock_ssh_service, client):
        """测试获取应用列表时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/docker-store/apps?account_alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_success(self, mock_store_service, mock_ssh_service, client):
        """测试获取应用详情成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.get_app_detail.return_value = {
            "id": "nginx",
            "name": "Nginx",
            "description": "Web 服务器",
            "category": "web",
            "version": "1.0.0",
            "account_alias": "test-server",
            "status": {"running": True, "containers": []},
        }

        response = client.get("/api/docker-store/apps/nginx?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "nginx"
        assert data["status"]["running"] is True

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_app_detail_account_not_found(self, mock_ssh_service, client):
        """测试获取应用详情时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/docker-store/apps/nginx?account_alias=nonexistent")
        assert response.status_code == 404


class TestDockerStoreInstall:
    """Docker 应用安装测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_success(self, mock_store_service, mock_ssh_service, client):
        """测试安装应用成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.install_app.return_value = {
            "app_id": "nginx",
            "path": "/www/server/apps/nginx",
            "message": "应用 nginx 已安装并启动",
            "stdout": "",
            "stderr": "",
        }

        response = client.post(
            "/api/docker-store/install/nginx",
            json={
                "account_alias": "test-server",
                "user_config": {"NGINX_PORT": 80},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_with_empty_config(self, mock_store_service, mock_ssh_service, client):
        """测试安装应用时不传 user_config"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.install_app.return_value = {
            "app_id": "nginx",
            "path": "/www/server/apps/nginx",
            "message": "应用 nginx 已安装并启动",
            "stdout": "",
            "stderr": "",
        }

        response = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 200
        mock_store_service.install_app.assert_called_with(
            "test-server", "nginx", user_config={}
        )

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_install_app_account_not_found(self, mock_ssh_service, client):
        """测试安装应用时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "nonexistent"},
        )
        assert response.status_code == 404


class TestDockerStoreUninstall:
    """Docker 应用卸载测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_success(self, mock_store_service, mock_ssh_service, client):
        """测试卸载应用成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.uninstall_app.return_value = "应用 nginx 已卸载"

        response = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "test-server", "purge_data": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_with_purge_data(self, mock_store_service, mock_ssh_service, client):
        """测试卸载应用并清除数据"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.uninstall_app.return_value = "应用 nginx 已卸载并清除数据"

        response = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "test-server", "purge_data": True},
        )
        assert response.status_code == 200
        mock_store_service.uninstall_app.assert_called_with(
            "test-server", "nginx", purge_data=True
        )

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_default_purge_data(self, mock_store_service, mock_ssh_service, client):
        """测试卸载应用时 purge_data 默认值为 False"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.uninstall_app.return_value = "应用 nginx 已卸载"

        response = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 200
        mock_store_service.uninstall_app.assert_called_with(
            "test-server", "nginx", purge_data=False
        )

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_uninstall_app_account_not_found(self, mock_ssh_service, client):
        """测试卸载应用时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "nonexistent"},
        )
        assert response.status_code == 404


class TestDockerStoreStatus:
    """Docker 应用状态查询测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_running(self, mock_store_service, mock_ssh_service, client):
        """测试获取运行中的应用状态"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.get_app_status.return_value = {
            "app_id": "nginx",
            "running": True,
            "running_count": 1,
            "total_count": 1,
            "containers": [{"id": "abc123", "name": "panel-nginx", "state": "running"}],
            "message": "运行中 1/1",
        }

        response = client.get("/api/docker-store/status/nginx?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["running_count"] == 1

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_not_running(self, mock_store_service, mock_ssh_service, client):
        """测试获取未运行应用状态"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_store_service.get_app_status.return_value = {
            "app_id": "nginx",
            "running": False,
            "containers": [],
            "message": "应用未运行或不存在",
        }

        response = client.get("/api/docker-store/status/nginx?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_app_status_account_not_found(self, mock_ssh_service, client):
        """测试获取应用状态时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/docker-store/status/nginx?account_alias=nonexistent")
        assert response.status_code == 404


class TestDockerStoreRegistryMirrors:
    """Docker 镜像源配置测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_success(self, mock_mirrors, mock_ssh_service, client):
        """测试获取镜像源配置成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_mirrors.check_registry_mirrors.return_value = {
            "enabled": True,
            "urls": ["https://mirror.example.com"],
        }

        response = client.get("/api/docker-store/registry-mirrors?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert len(data["urls"]) == 1

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_not_configured(self, mock_mirrors, mock_ssh_service, client):
        """测试获取未配置的镜像源"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_mirrors.check_registry_mirrors.return_value = {
            "enabled": False,
            "urls": [],
        }

        response = client.get("/api/docker-store/registry-mirrors?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_registry_mirrors_account_not_found(self, mock_ssh_service, client):
        """测试获取镜像源时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/docker-store/registry-mirrors?account_alias=nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_set_registry_mirrors_success(self, mock_mirrors, mock_ssh_service, client):
        """测试设置镜像源成功"""
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_mirrors.configure_registry_mirror.return_value = "镜像源配置成功"

        response = client.post(
            "/api/docker-store/registry-mirrors",
            json={
                "account_alias": "test-server",
                "mirror_url": "https://mirror.example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        mock_mirrors.configure_registry_mirror.assert_called_with(
            "test-server", "https://mirror.example.com"
        )

    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_set_registry_mirrors_account_not_found(self, mock_ssh_service, client):
        """测试设置镜像源时账户不存在"""
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/docker-store/registry-mirrors",
            json={
                "account_alias": "nonexistent",
                "mirror_url": "https://mirror.example.com",
            },
        )
        assert response.status_code == 404


class TestDockerStoreErrorHandling:
    """Docker 应用商店错误处理测试"""

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_docker_not_installed(self, mock_store_service, mock_ssh_service, client):
        """测试 Docker 未安装时获取应用列表"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.list_apps.side_effect = DockerCommandError(
            "docker: command not found", 127
        )

        response = client.get("/api/docker-store/apps?account_alias=test-server")
        assert response.status_code == 503

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_permission_error(self, mock_store_service, mock_ssh_service, client):
        """测试 Docker 权限不足时获取应用列表"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.list_apps.side_effect = DockerCommandError(
            "permission denied", 1
        )

        response = client.get("/api/docker-store/apps?account_alias=test-server")
        assert response.status_code == 403

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_not_found_error(self, mock_store_service, mock_ssh_service, client):
        """测试应用不存在时的错误处理"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.get_app_detail.side_effect = DockerCommandError(
            "No such container: panel-nginx", 1
        )

        response = client.get("/api/docker-store/apps/nginx?account_alias=test-server")
        assert response.status_code == 404

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_timeout_error(self, mock_store_service, mock_ssh_service, client):
        """测试安装应用超时错误"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.install_app.side_effect = DockerCommandError(
            "operation timeout", 1
        )

        response = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 504

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_generic_error(self, mock_store_service, mock_ssh_service, client):
        """测试安装应用通用错误"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.install_app.side_effect = DockerCommandError(
            "unknown error occurred", 1
        )

        response = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 400

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_docker_not_installed(self, mock_store_service, mock_ssh_service, client):
        """测试卸载应用时 Docker 未安装"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.uninstall_app.side_effect = DockerCommandError(
            "docker: command not found", 127
        )

        response = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 503

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_permission_error(self, mock_store_service, mock_ssh_service, client):
        """测试获取应用状态时权限不足"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_store_service.get_app_status.side_effect = DockerCommandError(
            "got permission denied", 1
        )

        response = client.get("/api/docker-store/status/nginx?account_alias=test-server")
        assert response.status_code == 403

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_docker_not_installed(self, mock_mirrors, mock_ssh_service, client):
        """测试获取镜像源时 Docker 未安装"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_mirrors.check_registry_mirrors.side_effect = DockerCommandError(
            "docker: command not found", 127
        )

        response = client.get("/api/docker-store/registry-mirrors?account_alias=test-server")
        assert response.status_code == 503

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_set_registry_mirrors_generic_error(self, mock_mirrors, mock_ssh_service, client):
        """测试设置镜像源时通用错误"""
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_mirrors.configure_registry_mirror.side_effect = DockerCommandError(
            "failed to configure", 1
        )

        response = client.post(
            "/api/docker-store/registry-mirrors",
            json={"account_alias": "test-server", "mirror_url": "https://mirror.example.com"},
        )
        assert response.status_code == 400
