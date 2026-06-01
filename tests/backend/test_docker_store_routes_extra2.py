from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.docker_service import DockerCommandError

client = TestClient(app)


def _make_docker_error(msg, exit_code=1):
    return DockerCommandError(msg, exit_code)


class TestGetAppDetailDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_permission_denied(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_detail.side_effect = _make_docker_error("permission denied", 1)
        resp = client.get("/api/docker-store/apps/nginx?account_alias=srv1")
        assert resp.status_code == 403

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_detail_timeout(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_detail.side_effect = _make_docker_error("timeout", 1)
        resp = client.get("/api/docker-store/apps/nginx?account_alias=srv1")
        assert resp.status_code == 504


class TestGetRegistryMirrorsDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_get_registry_mirrors_not_found(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.check_registry_mirrors.side_effect = _make_docker_error("not found", 1)
        resp = client.get("/api/docker-store/registry-mirrors?account_alias=srv1")
        assert resp.status_code == 404

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.core.docker_registry_mirrors.docker_registry_mirrors")
    def test_set_registry_mirrors_timeout(self, mock_mirrors, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_mirrors.configure_registry_mirror.side_effect = _make_docker_error("timeout", 1)
        resp = client.post(
            "/api/docker-store/registry-mirrors",
            json={"account_alias": "srv1", "mirror_url": "https://mirror.io"},
        )
        assert resp.status_code == 504


class TestGetImageVersionSizes:
    @patch("app.services.docker_store_service.docker_store_service")
    def test_image_version_sizes_success(self, mock_store):
        mock_store.get_image_version_sizes.return_value = {"nginx:latest": 50}
        resp = client.get("/api/docker-store/image-sizes/nginx")
        assert resp.status_code == 200

    @patch("app.services.docker_store_service.docker_store_service")
    def test_image_version_sizes_value_error(self, mock_store):
        mock_store.get_image_version_sizes.side_effect = ValueError("not found")
        resp = client.get("/api/docker-store/image-sizes/nonexistent")
        assert resp.status_code == 404

    @patch("app.services.docker_store_service.docker_store_service")
    def test_image_version_sizes_generic_error(self, mock_store):
        mock_store.get_image_version_sizes.side_effect = RuntimeError("network error")
        resp = client.get("/api/docker-store/image-sizes/nginx")
        assert resp.status_code == 500


class TestGetAppSizeSuccess:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_size_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_size_info.return_value = {"total_size": "100MB"}
        resp = client.get("/api/docker-store/size/nginx?account_alias=srv1")
        assert resp.status_code == 200


class TestGetAppStatusSuccess:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_status.return_value = {"status": "running"}
        resp = client.get("/api/docker-store/status/nginx?account_alias=srv1")
        assert resp.status_code == 200


class TestGetAllAppStatusesSuccess:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_all_app_statuses_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_all_app_statuses.return_value = {"nginx": "running"}
        resp = client.get("/api/docker-store/status?account_alias=srv1")
        assert resp.status_code == 200


class TestListAppsWithCategory:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_with_category(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.list_apps.return_value = [{"id": "nginx"}]
        resp = client.get("/api/docker-store/apps?account_alias=srv1&category=web")
        assert resp.status_code == 200


class TestInstallAppSuccess:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_success(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.return_value = "安装成功"
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "安装成功"


class TestUninstallAppSuccess:
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


class TestSetRegistryMirrorsSuccess:
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


class TestGetRunningLoopEdgeCases:
    def test_get_running_loop_returns_loop(self):
        from app.api.routes.docker_store import _get_running_loop
        async def _inner():
            loop = _get_running_loop()
            assert loop is not None
            assert loop.is_running()
        asyncio.run(_inner())


class TestUninstallAppDockerErrorGeneric:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_generic_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.uninstall_app.side_effect = _make_docker_error("some error", 1)
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "srv1", "purge_data": False},
        )
        assert resp.status_code == 400


class TestGetAllAppStatusesGenericError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_all_statuses_generic_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_all_app_statuses.side_effect = _make_docker_error("random error", 1)
        resp = client.get("/api/docker-store/status?account_alias=srv1")
        assert resp.status_code == 400
