"""Docker管理接口测试"""
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


class TestDockerInfo:
    """Docker信息检测测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_docker_info_installed(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.check_docker_installed.return_value = True
        mock_docker_service.get_docker_version.return_value = "Docker 24.0.7"
        mock_docker_service.check_docker_running.return_value = True
        mock_docker_service.check_docker_permissions.return_value = {"has_docker_group": True}

        response = client.get("/api/docker/info?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["running"] is True
        assert "Docker" in data["version"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_docker_info_not_installed(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.check_docker_installed.return_value = False

        response = client.get("/api/docker/info?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["version"] is None
        assert data["running"] is False

    @patch("app.api.routes.docker.ssh_account_service")
    def test_get_docker_info_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/docker/info?account_alias=nonexistent")
        assert response.status_code == 404


class TestDockerInstall:
    """Docker安装测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_install_docker_success(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.install_docker.return_value = "Docker安装成功"

        response = client.post(
            "/api/docker/install",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "安装成功" in data["message"]


class TestDockerContainers:
    """Docker容器管理测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_containers(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.list_containers.return_value = [
            {"Id": "abc123", "Names": ["/nginx"], "Status": "Up 2 days"},
            {"Id": "def456", "Names": ["/redis"], "Status": "Up 1 day"},
        ]

        response = client.get("/api/docker/containers?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["Names"] == ["/nginx"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_containers_all(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.list_containers.return_value = []

        response = client.get("/api/docker/containers?account_alias=test-server&all=true")
        assert response.status_code == 200
        mock_docker_service.list_containers.assert_called_with("test-server", all=True)

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_container_info(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.get_container_info.return_value = {
            "Id": "abc123",
            "Name": "/nginx",
            "State": {"Status": "running"},
        }

        response = client.get("/api/docker/containers/abc123?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["Id"] == "abc123"

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.start_container.return_value = "容器已启动"

        response = client.post(
            "/api/docker/containers/abc123/start?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已启动" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_start_container_already_running(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.get_container_info.return_value = {
            "State": {"Status": "running"}
        }

        response = client.post(
            "/api/docker/containers/abc123/start?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已在运行" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_stop_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.stop_container.return_value = "容器已停止"

        response = client.post(
            "/api/docker/containers/abc123/stop",
            json={"account_alias": "test-server"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "已停止" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_restart_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.restart_container.return_value = "容器已重启"

        response = client.post(
            "/api/docker/containers/abc123/restart?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已重启" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_kill_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.kill_container.return_value = "容器已强制停止"

        response = client.post(
            "/api/docker/containers/abc123/kill?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已强制停止" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.remove_container.return_value = "容器已删除"

        response = client.delete(
            "/api/docker/containers/abc123?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_pause_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.pause_container.return_value = "容器已暂停"

        response = client.post(
            "/api/docker/containers/abc123/pause?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已暂停" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_unpause_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.unpause_container.return_value = "容器已恢复"

        response = client.post(
            "/api/docker/containers/abc123/unpause?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已恢复" in data["message"]


class TestDockerLogs:
    """Docker日志测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_container_logs(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.get_container_logs.return_value = "Line 1\nLine 2\nLine 3"

        response = client.get(
            "/api/docker/containers/abc123/logs?account_alias=test-server&tail=50"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["logs"], list)
        assert len(data["logs"]) == 3

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_get_container_stats(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.get_container_stats.return_value = {
            "cpu_percent": 15.5,
            "memory_usage": 256000000,
            "memory_limit": 512000000,
        }

        response = client.get(
            "/api/docker/containers/abc123/stats?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data


class TestDockerImages:
    """Docker镜像管理测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_images(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.list_images.return_value = [
            {"Id": "img1", "RepoTags": ["nginx:latest"], "Size": "150MB"},
        ]

        response = client.get("/api/docker/images?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["RepoTags"] == ["nginx:latest"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_pull_image(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.pull_image.return_value = "镜像拉取成功"

        response = client.post(
            "/api/docker/images/pull",
            json={"account_alias": "test-server", "image_name": "nginx:latest"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "拉取成功" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_image(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.remove_image.return_value = "镜像已删除"

        response = client.delete(
            "/api/docker/images/img1?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_build_image(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.build_image.return_value = "镜像构建成功"

        response = client.post(
            "/api/docker/images/build",
            json={
                "account_alias": "test-server",
                "tag": "myapp:latest",
                "dockerfile_path": "./Dockerfile",
                "context_path": ".",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "构建成功" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_prune_images(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.prune_images.return_value = {"deleted": ["img1", "img2"]}

        response = client.post("/api/docker/images/prune?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data


class TestDockerNetworks:
    """Docker网络管理测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_networks(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.list_networks.return_value = [
            {"Name": "bridge", "Driver": "bridge"},
            {"Name": "host", "Driver": "host"},
        ]

        response = client.get("/api/docker/networks?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_network(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.create_network.return_value = "net123"

        response = client.post(
            "/api/docker/networks",
            json={"account_alias": "test-server", "name": "mynet", "driver": "bridge"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "mynet"
        assert data["network_id"] == "net123"

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_network(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.remove_network.return_value = "网络已删除"

        response = client.delete(
            "/api/docker/networks/net123?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]


class TestDockerVolumes:
    """Docker卷管理测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_volumes(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.list_volumes.return_value = [
            {"Name": "postgres_data", "Driver": "local"},
        ]

        response = client.get("/api/docker/volumes?account_alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_create_volume(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.create_volume.return_value = "myvolume"

        response = client.post(
            "/api/docker/volumes",
            json={"account_alias": "test-server", "name": "myvolume"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["volume_name"] == "myvolume"

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_remove_volume(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.remove_volume.return_value = "卷已删除"

        response = client.delete(
            "/api/docker/volumes/myvolume?account_alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]


class TestDockerCompose:
    """Docker Compose测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_list_compose_projects(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.find_compose_projects.return_value = [
            {"name": "webapp", "path": "/opt/webapp", "services": ["nginx", "app"]},
        ]

        response = client.get(
            "/api/docker/compose/projects?account_alias=test-server&search_path=/opt"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_up(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.compose_up.return_value = "Compose项目已启动"

        response = client.post(
            "/api/docker/compose/up",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/webapp/docker-compose.yml",
                "detach": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "已启动" in data["message"]

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_compose_down(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.compose_down.return_value = "Compose项目已停止"

        response = client.post(
            "/api/docker/compose/down",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/webapp/docker-compose.yml",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "已停止" in data["message"]


class TestDockerExec:
    """Docker容器内执行命令测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_exec_in_container(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_docker_service.exec_in_container.return_value = (0, "Hello World", "")

        response = client.post(
            "/api/docker/containers/abc123/exec",
            json={
                "account_alias": "test-server",
                "command": "echo 'Hello World'",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exit_code"] == 0
        assert "Hello World" in data["stdout"]


class TestDockerErrorHandling:
    """Docker错误处理测试"""

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_docker_not_installed_error(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        # mock 使 docker_service 抛出 DockerCommandError
        mock_docker_service.list_containers.side_effect = DockerCommandError(
            "docker: command not found", 127
        )

        response = client.get("/api/docker/containers?account_alias=test-server")
        # 路由层的 _handle_docker_error 会根据错误内容返回 503
        assert response.status_code == 503

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_docker_permission_error(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_docker_service.list_containers.side_effect = DockerCommandError(
            "permission denied", 1
        )

        response = client.get("/api/docker/containers?account_alias=test-server")
        # 路由层的 _handle_docker_error 会返回 403
        assert response.status_code == 403

    @patch("app.api.routes.docker.ssh_account_service")
    @patch("app.api.routes.docker.docker_service")
    def test_docker_not_found_error(self, mock_docker_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        from app.services.docker_service import DockerCommandError
        mock_docker_service.get_container_info.side_effect = DockerCommandError(
            "No such object: abc123", 1
        )

        response = client.get("/api/docker/containers/abc123?account_alias=test-server")
        # get_container 路由有特殊处理：先检查 "No such object" 返回 404
        assert response.status_code == 404
