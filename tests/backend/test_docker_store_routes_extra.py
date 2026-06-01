from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.docker_service import DockerCommandError

client = TestClient(app)


def _make_docker_error(msg, exit_code=1):
    return DockerCommandError(msg, exit_code)


class TestHandleDockerErrorBranches:
    def test_command_not_found(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("docker: command not found", 127)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err, "test_ctx")
        assert exc_info.value.status_code == 503
        assert "Docker 未安装" in exc_info.value.detail

    def test_not_found(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("image not found", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 404
        assert "资源未找到" in exc_info.value.detail

    def test_no_such(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("no such container", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 404

    def test_permission_denied(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("permission denied", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 403
        assert "权限不足" in exc_info.value.detail

    def test_got_permission_denied(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("Got permission denied", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 403

    def test_timeout(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("operation timeout", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 504
        assert "超时" in exc_info.value.detail

    def test_generic_error(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("some random error", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 400

    def test_with_context(self):
        from app.api.routes.docker_store import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("error msg", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err, "install_app")
        assert exc_info.value.status_code == 400


class TestListAppsNoCategory:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_list_apps_no_category(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.list_apps.return_value = [{"id": "nginx"}, {"id": "redis"}]
        resp = client.get("/api/docker-store/apps?account_alias=srv1")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestInstallAppAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_install_app_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "missing", "user_config": {}},
        )
        assert resp.status_code == 404


class TestUninstallAppAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_uninstall_app_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "missing", "purge_data": False},
        )
        assert resp.status_code == 404


class TestGetAllAppStatusesAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_all_statuses_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/status?account_alias=missing")
        assert resp.status_code == 404


class TestGetAppStatusAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_app_status_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/status/nginx?account_alias=missing")
        assert resp.status_code == 404


class TestGetAppSizeAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_app_size_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/size/nginx?account_alias=missing")
        assert resp.status_code == 404


class TestGetRegistryMirrorsAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_registry_mirrors_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/registry-mirrors?account_alias=missing")
        assert resp.status_code == 404


class TestSetRegistryMirrorsAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_set_registry_mirrors_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/docker-store/registry-mirrors",
            json={"account_alias": "missing", "mirror_url": "https://mirror.io"},
        )
        assert resp.status_code == 404


class TestGetAppDetailAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_get_app_detail_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker-store/apps/nginx?account_alias=missing")
        assert resp.status_code == 404


class TestGetAppSizeDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_size_command_not_found(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_size_info.side_effect = _make_docker_error("command not found", 127)
        resp = client.get("/api/docker-store/size/nginx?account_alias=srv1")
        assert resp.status_code == 503

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_size_timeout(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_size_info.side_effect = _make_docker_error("timeout", 1)
        resp = client.get("/api/docker-store/size/nginx?account_alias=srv1")
        assert resp.status_code == 504


class TestGetAppStatusDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_app_status_permission_denied(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_app_status.side_effect = _make_docker_error("permission denied", 1)
        resp = client.get("/api/docker-store/status/nginx?account_alias=srv1")
        assert resp.status_code == 403


class TestGetRunningLoop:
    def test_get_running_loop_with_loop(self):
        from app.api.routes.docker_store import _get_running_loop
        async def _inner():
            loop = _get_running_loop()
            assert loop is not None
        asyncio.run(_inner())

    def test_get_running_loop_without_loop(self):
        from app.api.routes.docker_store import _get_running_loop
        result = _get_running_loop()
        assert result is None


class TestInstallAppWsMissingAlias:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_install_ws_missing_account_alias(self, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/docker-store/ws/install/nginx") as ws:
            ws.send_text(json.dumps({"user_config": {"PORT": "8080"}}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]


class TestInstallAppWsAccountNotFound:
    @patch("app.api.routes.docker_store.ssh_account_service")
    def test_install_ws_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        with client.websocket_connect("/api/docker-store/ws/install/nginx") as ws:
            ws.send_text(json.dumps({"account_alias": "missing", "user_config": {}}))
            data = ws.receive_json()
            assert data["type"] == "error"


class TestInstallAppDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_timeout_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.side_effect = _make_docker_error("timeout", 1)
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {}},
        )
        assert resp.status_code == 504

    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_install_app_command_not_found_error(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.install_app.side_effect = _make_docker_error("command not found", 127)
        resp = client.post(
            "/api/docker-store/install/nginx",
            json={"account_alias": "srv1", "user_config": {}},
        )
        assert resp.status_code == 503


class TestUninstallAppDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_uninstall_app_permission_denied(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.uninstall_app.side_effect = _make_docker_error("permission denied", 1)
        resp = client.post(
            "/api/docker-store/uninstall/nginx",
            json={"account_alias": "srv1", "purge_data": False},
        )
        assert resp.status_code == 403


class TestGetAllAppStatusesDockerError:
    @patch("app.api.routes.docker_store.ssh_account_service")
    @patch("app.services.docker_store_service.docker_store_service")
    def test_get_all_statuses_command_not_found(self, mock_store, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_store.get_all_app_statuses.side_effect = _make_docker_error("command not found", 127)
        resp = client.get("/api/docker-store/status?account_alias=srv1")
        assert resp.status_code == 503
