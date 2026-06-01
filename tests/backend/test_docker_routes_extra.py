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


class TestSafeWsSend:
    def test_safe_ws_send_no_running_loop(self):
        from app.api.routes.docker import _safe_ws_send
        mock_ws = MagicMock()
        _safe_ws_send(mock_ws, {"type": "test"})
        mock_ws.send_json.assert_not_called()

    def test_safe_ws_send_with_running_loop(self):
        from app.api.routes.docker import _safe_ws_send
        mock_ws = MagicMock()
        async def _inner():
            _safe_ws_send(mock_ws, {"type": "test"})
        asyncio.run(_inner())

    def test_safe_ws_send_exception_handled(self):
        from app.api.routes.docker import _safe_ws_send
        mock_ws = MagicMock()
        async def _inner():
            mock_ws.send_json.side_effect = RuntimeError("closed")
            _safe_ws_send(mock_ws, {"type": "test"})
        asyncio.run(_inner())


class TestGetRunningLoop:
    def test_get_running_loop_with_loop(self):
        from app.api.routes.docker import _get_running_loop
        async def _inner():
            loop = _get_running_loop()
            assert loop is not None
        asyncio.run(_inner())

    def test_get_running_loop_without_loop(self):
        from app.api.routes.docker import _get_running_loop
        result = _get_running_loop()
        assert result is None


class TestHandleDockerErrorBranches:
    def test_command_not_found(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("docker: command not found", 127)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err, "ctx")
        assert exc_info.value.status_code == 503

    def test_not_found(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("image not found", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 404

    def test_no_such(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("no such container", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 404

    def test_permission_denied(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("permission denied", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 403

    def test_got_permission_denied(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("Got permission denied", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 403

    def test_already_running(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("container is already running", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 409

    def test_already_paused(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("container is already paused", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 409

    def test_timeout(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("operation timeout", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 504

    def test_generic_error(self):
        from app.api.routes.docker import _handle_docker_error
        from fastapi import HTTPException
        err = _make_docker_error("unknown error", 1)
        with pytest.raises(HTTPException) as exc_info:
            _handle_docker_error(err)
        assert exc_info.value.status_code == 400


class TestStartContainerAlreadyRunning:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container_already_running_state(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.return_value = {
            "State": {"Status": "running"}
        }
        resp = client.post("/api/docker/containers/abc123/start?account_alias=srv1")
        assert resp.status_code == 200
        assert "已在运行" in resp.json()["message"]


class TestContainerLogsWsMissingAlias:
    @patch("app.api.routes.docker.ssh_account_service")
    def test_container_logs_ws_missing_alias(self, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/docker/ws/containers/abc123/logs") as ws:
            ws.send_text(json.dumps({}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]


class TestContainerLogsWsAccountNotFound:
    @patch("app.api.routes.docker.ssh_account_service")
    def test_container_logs_ws_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        with client.websocket_connect("/api/docker/ws/containers/abc123/logs") as ws:
            ws.send_text(json.dumps({"account_alias": "missing"}))
            data = ws.receive_json()
            assert data["type"] == "error"


class TestContainerLogsWsSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_container_logs_ws_stop_action(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_account = MagicMock()
        mock_ssh.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_ssh.pool = MagicMock()
        mock_ssh.pool.get_connection.return_value = mock_conn
        mock_transport = MagicMock()
        mock_conn.manager._transport = mock_transport
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_transport.open_session.return_value = mock_chan
        mock_ssh.pool.release_connection = MagicMock()

        with client.websocket_connect("/api/docker/ws/containers/abc123/logs") as ws:
            ws.send_text(json.dumps({"account_alias": "srv1"}))
            ws.send_text(json.dumps({"action": "stop"}))


class TestListContainersSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_containers_all(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_containers.return_value = [{"id": "abc"}, {"id": "def"}]
        resp = client.get("/api/docker/containers?account_alias=srv1&all=true")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestRestartContainerSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_restart_container_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.restart_container.return_value = "已重启"
        resp = client.post("/api/docker/containers/abc123/restart?account_alias=srv1")
        assert resp.status_code == 200


class TestKillContainerSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_kill_container_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.kill_container.return_value = "已终止"
        resp = client.post("/api/docker/containers/abc123/kill?account_alias=srv1")
        assert resp.status_code == 200


class TestPauseContainerSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_pause_container_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.pause_container.return_value = "已暂停"
        resp = client.post("/api/docker/containers/abc123/pause?account_alias=srv1")
        assert resp.status_code == 200


class TestUnpauseContainerSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_unpause_container_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.unpause_container.return_value = "已恢复"
        resp = client.post("/api/docker/containers/abc123/unpause?account_alias=srv1")
        assert resp.status_code == 200


class TestRemoveContainerNoForce:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_container_no_force(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_container.return_value = "已删除"
        resp = client.delete("/api/docker/containers/abc?account_alias=srv1")
        assert resp.status_code == 200
        mock_docker.remove_container.assert_called_with("srv1", "abc", force=False)


class TestListImagesSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_images_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_images.return_value = [{"id": "img1"}]
        resp = client.get("/api/docker/images?account_alias=srv1")
        assert resp.status_code == 200


class TestRemoveImageSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_image_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_image.return_value = "已删除"
        resp = client.delete("/api/docker/images/img1?account_alias=srv1")
        assert resp.status_code == 200


class TestPullImageSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_pull_image_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.pull_image.return_value = "已拉取"
        resp = client.post(
            "/api/docker/images/pull",
            json={"account_alias": "srv1", "image_name": "nginx:latest"},
        )
        assert resp.status_code == 200


class TestBuildImageSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_build_image_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.build_image.return_value = "已构建"
        resp = client.post(
            "/api/docker/images/build",
            json={"account_alias": "srv1", "tag": "app:1", "dockerfile_path": ".", "context_path": "."},
        )
        assert resp.status_code == 200


class TestPruneImagesSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_prune_images_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.prune_images.return_value = {"deleted": 3}
        resp = client.post("/api/docker/images/prune?account_alias=srv1")
        assert resp.status_code == 200


class TestCreateNetworkSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_network_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.create_network.return_value = "net-id-123"
        resp = client.post(
            "/api/docker/networks",
            json={"account_alias": "srv1", "name": "mynet", "driver": "bridge"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["network_id"] == "net-id-123"
        assert data["name"] == "mynet"


class TestRemoveNetworkSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_network_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_network.return_value = "已删除"
        resp = client.delete("/api/docker/networks/net1?account_alias=srv1")
        assert resp.status_code == 200


class TestListNetworksSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_networks_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_networks.return_value = [{"name": "bridge"}]
        resp = client.get("/api/docker/networks?account_alias=srv1")
        assert resp.status_code == 200


class TestCreateVolumeSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_volume_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.create_volume.return_value = "vol-name"
        resp = client.post(
            "/api/docker/volumes",
            json={"account_alias": "srv1", "name": "myvol"},
        )
        assert resp.status_code == 201
        assert resp.json()["volume_name"] == "vol-name"


class TestRemoveVolumeSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_volume_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_volume.return_value = "已删除"
        resp = client.delete("/api/docker/volumes/vol1?account_alias=srv1")
        assert resp.status_code == 200


class TestListVolumesSuccess:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_volumes_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_volumes.return_value = [{"name": "vol1"}]
        resp = client.get("/api/docker/volumes?account_alias=srv1")
        assert resp.status_code == 200


class TestGetContainerLogsGenericError:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_logs_generic_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_logs.side_effect = _make_docker_error("some error", 1)
        resp = client.get("/api/docker/containers/abc/logs?account_alias=srv1")
        assert resp.status_code == 400


class TestGetContainerStatsGenericError:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stats_generic_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_stats.side_effect = _make_docker_error("some error", 1)
        resp = client.get("/api/docker/containers/abc/stats?account_alias=srv1")
        assert resp.status_code == 400
