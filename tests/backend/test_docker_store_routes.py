import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.docker_service import DockerCommandError

client = TestClient(app)


def _make_docker_error(msg, exit_code=1):
    return DockerCommandError(msg, exit_code)


class TestVerifyAccount:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/apps?account_alias=missing")
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestListApps:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.list_apps.return_value = [{"id": "nginx", "name": "Nginx"}]
        resp = client.get("/api/docker-store/apps?account_alias=srv1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_with_category(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.list_apps.return_value = [{"id": "nginx"}]
        resp = client.get("/api/docker-store/apps?account_alias=srv1&category=web")
        assert resp.status_code == 200
        mock_store.list_apps.assert_called_with("srv1", category="web")

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_docker_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.list_apps.side_effect = _make_docker_error("command not found", 127)
        resp = client.get("/api/docker-store/apps?account_alias=srv1")
        assert resp.status_code == 503


class TestGetAppDetail:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_detail.return_value = {"id": "nginx", "name": "Nginx"}
        resp = client.get("/api/docker-store/apps/nginx?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "nginx"

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_not_found(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_detail.side_effect = _make_docker_error("not found", 1)
        resp = client.get("/api/docker-store/apps/nonexistent?account_alias=srv1")
        assert resp.status_code == 404


class TestInstallApp:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.return_value = "安装成功"
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {"PORT": "8080"}},
        )
        assert resp.status_code == 200
        assert "安装成功" in resp.json()["message"]

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_with_empty_config(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.return_value = "安装成功"
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {}},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_permission_denied(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.side_effect = _make_docker_error("permission denied", 1)
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {}},
        )
        assert resp.status_code == 403


class TestUninstallApp:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.uninstall_app.return_value = "卸载成功"
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "srv1", "purge_data": True},
        )
        assert resp.status_code == 200
        assert "卸载成功" in resp.json()["message"]

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_no_purge(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.uninstall_app.return_value = "卸载成功"
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "srv1", "purge_data": False},
        )
        assert resp.status_code == 200
        mock_store.uninstall_app.assert_called_with("srv1", "nginx", purge_data=False)

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.uninstall_app.side_effect = _make_docker_error("uninstall failed", 1)
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "srv1", "purge_data": False},
        )
        assert resp.status_code == 400


class TestGetAllAppStatuses:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_all_statuses_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_all_app_statuses.return_value = {"nginx": "running"}
        resp = client.get("/api/docker-store/status?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["nginx"] == "running"

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_all_statuses_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_all_app_statuses.side_effect = _make_docker_error("timeout", 1)
        resp = client.get("/api/docker-store/status?account_alias=srv1")
        assert resp.status_code == 504


class TestGetAppStatus:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_status.return_value = {"status": "running"}
        resp = client.get("/api/docker-store/status/nginx?account_alias=srv1")
        assert resp.status_code == 200

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_status.side_effect = _make_docker_error("no such app", 1)
        resp = client.get("/api/docker-store/status/nginx?account_alias=srv1")
        assert resp.status_code == 404


class TestGetAppSize:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_size_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_size_info.return_value = {"total_size": "500MB"}
        resp = client.get("/api/docker-store/size/nginx?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["total_size"] == "500MB"

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_size_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_size_info.side_effect = _make_docker_error("size error", 1)
        resp = client.get("/api/docker-store/size/nginx?account_alias=srv1")
        assert resp.status_code == 400


class TestGetImageVersionSizes:
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_image_version_sizes_success(self, mock_store):
        mock_store.get_image_version_sizes.return_value = {"latest": "150MB"}
        resp = client.get("/api/docker-store/image-sizes/nginx")
        assert resp.status_code == 200
        assert resp.json()["latest"] == "150MB"

    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_image_version_sizes_value_error(self, mock_store):
        mock_store.get_image_version_sizes.side_effect = ValueError("app not found")
        resp = client.get("/api/docker-store/image-sizes/nonexistent")
        assert resp.status_code == 404

    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_image_version_sizes_generic_error(self, mock_store):
        mock_store.get_image_version_sizes.side_effect = Exception("network error")
        resp = client.get("/api/docker-store/image-sizes/nginx")
        assert resp.status_code == 500


class TestRegistryMirrors:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_success(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.check_registry_mirrors.return_value = {"mirrors": ["https://mirror.io"]}
        resp = client.get("/api/docker-store/registry-mirrors?account_alias=srv1")
        assert resp.status_code == 200

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_error(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.check_registry_mirrors.side_effect = _make_docker_error("check failed", 1)
        resp = client.get("/api/docker-store/registry-mirrors?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_set_registry_mirrors_success(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.configure_registry_mirror.return_value = "配置成功"
        resp = client.post(
            "/api/docker-store/registry-mirrors",
            json={"account_alias": "srv1", "mirror_url": "https://mirror.io"},
        )
        assert resp.status_code == 200
        assert "配置成功" in resp.json()["message"]

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_set_registry_mirrors_error(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.configure_registry_mirror.side_effect = _make_docker_error("configure failed", 1)
        resp = client.post(
            "/api/docker-store/registry-mirrors",
            json={"account_alias": "srv1", "mirror_url": "https://mirror.io"},
        )
        assert resp.status_code == 400
