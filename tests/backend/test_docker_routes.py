import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.docker_service import DockerCommandError

client = TestClient(app)


def _make_docker_error(msg, exit_code=1):
    return DockerCommandError(msg, exit_code)


class TestVerifyAccount:
    @patch("app.api.routes.docker.ssh_account_service")
    def test_account_not_found_returns_404(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/docker/info?account_alias=missing")
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestGetDockerInfo:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_installed_with_full_info(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.check_docker_installed.return_value = True
        mock_docker.get_docker_version.return_value = "24.0.7"
        mock_docker.check_docker_running.return_value = True
        mock_docker.check_docker_permissions.return_value = {"has_docker_group": True}
        resp = client.get("/api/docker/info?account_alias=srv1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["installed"] is True
        assert data["version"] == "24.0.7"
        assert data["running"] is True
        assert data["permissions"] == {"has_docker_group": True}

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_not_installed_skips_version_check(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.check_docker_installed.return_value = False
        resp = client.get("/api/docker/info?account_alias=srv1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["installed"] is False
        assert data["version"] is None
        assert data["running"] is False
        assert data["permissions"] == {}
        mock_docker.get_docker_version.assert_not_called()


class TestInstallDocker:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.install_docker.return_value = "安装成功"
        resp = client.post("/api/docker/install", json={"account_alias": "srv1"})
        assert resp.status_code == 200
        assert "安装成功" in resp.json()["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_command_not_found(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.install_docker.side_effect = _make_docker_error("docker: command not found", 127)
        resp = client.post("/api/docker/install", json={"account_alias": "srv1"})
        assert resp.status_code == 503

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_permission_denied(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.install_docker.side_effect = _make_docker_error("Got permission denied", 1)
        resp = client.post("/api/docker/install", json={"account_alias": "srv1"})
        assert resp.status_code == 403

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_timeout(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.install_docker.side_effect = _make_docker_error("operation timeout", 1)
        resp = client.post("/api/docker/install", json={"account_alias": "srv1"})
        assert resp.status_code == 504

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_generic_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.install_docker.side_effect = _make_docker_error("some unknown error", 1)
        resp = client.post("/api/docker/install", json={"account_alias": "srv1"})
        assert resp.status_code == 400


class TestStartContainerEdgeCases:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container_race_condition_already_running(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.side_effect = DockerCommandError("error", 1)
        mock_docker.start_container.side_effect = _make_docker_error("container is already running", 1)
        resp = client.post("/api/docker/containers/abc123/start?account_alias=srv1")
        assert resp.status_code == 200
        assert "已在运行" in resp.json()["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container_already_paused_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.side_effect = DockerCommandError("error", 1)
        mock_docker.start_container.side_effect = _make_docker_error("is already paused", 1)
        resp = client.post("/api/docker/containers/abc123/start?account_alias=srv1")
        assert resp.status_code == 409

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container_not_found_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.side_effect = DockerCommandError("error", 1)
        mock_docker.start_container.side_effect = _make_docker_error("not found container", 1)
        resp = client.post("/api/docker/containers/abc123/start?account_alias=srv1")
        assert resp.status_code == 404


class TestStopContainer:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stop_with_timeout(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.stop_container.return_value = "已停止"
        resp = client.post(
            "/api/docker/containers/abc123/stop",
            json={"account_alias": "srv1", "timeout": 10},
        )
        assert resp.status_code == 200
        mock_docker.stop_container.assert_called_with("srv1", "abc123", timeout=10)

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stop_no_timeout(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.stop_container.return_value = "已停止"
        resp = client.post(
            "/api/docker/containers/abc123/stop",
            json={"account_alias": "srv1"},
        )
        assert resp.status_code == 200
        mock_docker.stop_container.assert_called_with("srv1", "abc123", timeout=None)


class TestContainerLogs:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_logs_no_such_object(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_logs.side_effect = _make_docker_error("No such object: abc", 1)
        resp = client.get("/api/docker/containers/abc/logs?account_alias=srv1")
        assert resp.status_code == 404

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_logs_empty(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_logs.return_value = ""
        resp = client.get("/api/docker/containers/abc/logs?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["logs"] == []

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_logs_with_timestamps(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_logs.return_value = "line1\nline2"
        resp = client.get("/api/docker/containers/abc/logs?account_alias=srv1&timestamps=true")
        assert resp.status_code == 200
        assert len(resp.json()["logs"]) == 2


class TestContainerStats:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stats_no_such_object(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_stats.side_effect = _make_docker_error("No such object: abc", 1)
        resp = client.get("/api/docker/containers/abc/stats?account_alias=srv1")
        assert resp.status_code == 404

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stats_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_stats.return_value = {"cpu_percent": 10.0}
        resp = client.get("/api/docker/containers/abc/stats?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["cpu_percent"] == 10.0


class TestExecInContainer:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_exec_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.exec_in_container.return_value = (0, "output", "")
        resp = client.post(
            "/api/docker/containers/abc123/exec",
            json={"account_alias": "srv1", "command": "ls"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exit_code"] == 0
        assert data["stdout"] == "output"
        assert data["stderr"] == ""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_exec_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.exec_in_container.side_effect = _make_docker_error("exec failed", 1)
        resp = client.post(
            "/api/docker/containers/abc123/exec",
            json={"account_alias": "srv1", "command": "ls"},
        )
        assert resp.status_code == 400


class TestSearchImages:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_search_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.search_images.return_value = [{"name": "nginx"}]
        resp = client.get("/api/docker/images/search?account_alias=srv1&term=nginx")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_search_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.search_images.side_effect = _make_docker_error("search failed", 1)
        resp = client.get("/api/docker/images/search?account_alias=srv1&term=nginx")
        assert resp.status_code == 400


class TestGetNetworkInfo:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_network_not_found(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_network_info.side_effect = _make_docker_error("network net1 not found", 1)
        resp = client.get("/api/docker/networks/net1?account_alias=srv1")
        assert resp.status_code == 404
        assert "网络" in resp.json()["detail"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_network_info_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_network_info.return_value = {"Name": "mynet", "Driver": "bridge"}
        resp = client.get("/api/docker/networks/net1?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["Name"] == "mynet"


class TestGetVolumeInfo:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_volume_not_found(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_volume_info.side_effect = _make_docker_error("volume vol1 not found", 1)
        resp = client.get("/api/docker/volumes/vol1?account_alias=srv1")
        assert resp.status_code == 404
        assert "卷" in resp.json()["detail"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_volume_info_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_volume_info.return_value = {"Name": "vol1", "Driver": "local"}
        resp = client.get("/api/docker/volumes/vol1?account_alias=srv1")
        assert resp.status_code == 200
        assert resp.json()["Name"] == "vol1"


class TestContainerRemoveForce:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_force(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_container.return_value = "已删除"
        resp = client.delete("/api/docker/containers/abc?account_alias=srv1&force=true")
        assert resp.status_code == 200
        mock_docker.remove_container.assert_called_with("srv1", "abc", force=True)


class TestComposeProjects:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_projects_with_search_path(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.find_compose_projects.return_value = [{"name": "app"}]
        resp = client.get("/api/docker/compose/projects?account_alias=srv1&search_path=/opt")
        assert resp.status_code == 200
        mock_docker.find_compose_projects.assert_called_with("srv1", search_path="/opt")

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_up_detach(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.compose_up.return_value = "已启动"
        resp = client.post(
            "/api/docker/compose/up",
            json={"account_alias": "srv1", "project_path": "/opt/app", "detach": True},
        )
        assert resp.status_code == 200
        mock_docker.compose_up.assert_called_with("srv1", "/opt/app", detach=True)

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_down_success(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.compose_down.return_value = "已停止"
        resp = client.post(
            "/api/docker/compose/down",
            json={"account_alias": "srv1", "project_path": "/opt/app"},
        )
        assert resp.status_code == 200


class TestDockerErrorHandlingBranches:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_no_such_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_containers.side_effect = _make_docker_error("no such container", 1)
        resp = client.get("/api/docker/containers?account_alias=srv1")
        assert resp.status_code == 404

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_already_running_conflict(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.restart_container.side_effect = _make_docker_error("is already running", 1)
        resp = client.post("/api/docker/containers/abc/restart?account_alias=srv1")
        assert resp.status_code == 409

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_already_paused_conflict(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.pause_container.side_effect = _make_docker_error("is already paused", 1)
        resp = client.post("/api/docker/containers/abc/pause?account_alias=srv1")
        assert resp.status_code == 409

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_generic_docker_error_returns_400(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.kill_container.side_effect = _make_docker_error("unknown error", 1)
        resp = client.post("/api/docker/containers/abc/kill?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_image_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_image.side_effect = _make_docker_error("image not found", 1)
        resp = client.delete("/api/docker/images/img1?account_alias=srv1")
        assert resp.status_code == 404

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_pull_image_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.pull_image.side_effect = _make_docker_error("permission denied", 1)
        resp = client.post(
            "/api/docker/images/pull",
            json={"account_alias": "srv1", "image_name": "nginx:latest"},
        )
        assert resp.status_code == 403

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_build_image_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.build_image.side_effect = _make_docker_error("build failed", 1)
        resp = client.post(
            "/api/docker/images/build",
            json={"account_alias": "srv1", "tag": "app:1", "dockerfile_path": ".", "context_path": "."},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_prune_images_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.prune_images.side_effect = _make_docker_error("prune error", 1)
        resp = client.post("/api/docker/images/prune?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_networks_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_networks.side_effect = _make_docker_error("network error", 1)
        resp = client.get("/api/docker/networks?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_network_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.create_network.side_effect = _make_docker_error("create failed", 1)
        resp = client.post(
            "/api/docker/networks",
            json={"account_alias": "srv1", "name": "net1", "driver": "bridge"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_network_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_network.side_effect = _make_docker_error("remove failed", 1)
        resp = client.delete("/api/docker/networks/net1?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_volumes_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.list_volumes.side_effect = _make_docker_error("volume error", 1)
        resp = client.get("/api/docker/volumes?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_volume_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.create_volume.side_effect = _make_docker_error("create vol failed", 1)
        resp = client.post(
            "/api/docker/volumes",
            json={"account_alias": "srv1", "name": "vol1"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_volume_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.remove_volume.side_effect = _make_docker_error("remove vol failed", 1)
        resp = client.delete("/api/docker/volumes/vol1?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_projects_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.find_compose_projects.side_effect = _make_docker_error("compose error", 1)
        resp = client.get("/api/docker/compose/projects?account_alias=srv1")
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_up_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.compose_up.side_effect = _make_docker_error("compose up error", 1)
        resp = client.post(
            "/api/docker/compose/up",
            json={"account_alias": "srv1", "project_path": "/opt/app"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_down_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.compose_down.side_effect = _make_docker_error("compose down error", 1)
        resp = client.post(
            "/api/docker/compose/down",
            json={"account_alias": "srv1", "project_path": "/opt/app"},
        )
        assert resp.status_code == 400


class TestGetContainerNoSuchObject:
    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_container_no_such_object(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.side_effect = _make_docker_error("No such object: abc", 1)
        resp = client.get("/api/docker/containers/abc?account_alias=srv1")
        assert resp.status_code == 404
        assert "未找到" in resp.json()["detail"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_container_other_error(self, mock_docker, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_docker.get_container_info.side_effect = _make_docker_error("other error", 1)
        resp = client.get("/api/docker/containers/abc?account_alias=srv1")
        assert resp.status_code == 400
