import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.docker_service import DockerCommandError, DockerService


@pytest.fixture
def mock_ssh_account_service():
    with patch("app.services.docker_service.ssh_account_service") as mock_svc:
        account = MagicMock()
        account.alias = "test"
        mock_svc.get_account.return_value = account
        mock_pool = MagicMock()
        mock_svc.pool = mock_pool
        yield mock_svc


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.manager.exec_command.return_value = (0, "ok", "")
    conn.manager.transport = MagicMock()
    return conn


@pytest.fixture
def service():
    return DockerService()


class TestDockerCommandError:
    def test_error_with_exit_code(self):
        err = DockerCommandError("test error", 1)
        assert err.exit_code == 1
        assert "test error" in str(err)


class TestDockerServiceExec:
    def test_exec_docker_success(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker("test", ["ps"])
        assert code == 0
        mock_ssh_account_service.pool.release_connection.assert_called_once()

    def test_exec_docker_bytes_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, b"output", b"err")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker("test", ["ps"])
        assert isinstance(stdout, str)

    def test_exec_docker_nonexistent_account(self, service, mock_ssh_account_service):
        mock_ssh_account_service.get_account.return_value = None
        with pytest.raises(ValueError, match="不存在"):
            service._exec_docker("nonexistent", ["ps"])

    def test_exec_docker_json_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"ID":"abc"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service._exec_docker_json("test", ["ps", "--format", "{{json .}}"])
        assert len(result) == 1
        assert result[0]["ID"] == "abc"

    def test_exec_docker_json_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError):
            service._exec_docker_json("test", ["ps"])

    def test_exec_docker_json_bad_json(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, 'not json\n{"ID":"abc"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service._exec_docker_json("test", ["ps"])
        assert len(result) == 1

    def test_exec_docker_simple_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stdout, stderr = service._exec_docker_simple("test", ["ps"])
        assert stdout == "output"

    def test_exec_docker_simple_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError):
            service._exec_docker_simple("test", ["ps"])


class TestDockerServiceStreaming:
    def test_exec_docker_streaming_success(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()

        call_count = [0]

        def mock_exit_ready():
            call_count[0] += 1
            return call_count[0] > 1

        mock_chan.exit_status_ready.side_effect = mock_exit_ready
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn

        code, stdout, stderr = service._exec_docker_streaming("test", ["ps"])
        assert code == 0

    def test_exec_docker_streaming_no_transport(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.transport = None
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(RuntimeError, match="SSH 传输通道未建立"):
            service._exec_docker_streaming("test", ["ps"])


class TestPascalToCamel:
    def test_conversion(self, service):
        items = [{"Name": "test", "ID": "abc"}, {"CreatedAt": "2025"}]
        result = service._pascal_to_camel(items)
        assert result[0]["name"] == "test"
        assert result[0]["iD"] == "abc"
        assert result[1]["createdAt"] == "2025"

    def test_empty_key(self, service):
        items = [{"": "value", "Name": "test"}]
        result = service._pascal_to_camel(items)
        assert "" not in result[0]


class TestMapContainer:
    def test_map_container_with_slash_name(self, service):
        item = {"ID": "abc", "Names": "/mycontainer", "State": "Running", "CreatedAt": "2025"}
        result = service._map_container(item)
        assert result["name"] == "mycontainer"
        assert result["id"] == "abc"
        assert result["state"] == "running"
        assert result["created"] == "2025"

    def test_map_container_without_slash(self, service):
        item = {"ID": "abc", "Names": "mycontainer", "State": "Running"}
        result = service._map_container(item)
        assert result["name"] == "mycontainer"


class TestMapImage:
    def test_map_image(self, service):
        item = {"ID": "img1", "CreatedAt": "2025", "CreatedSince": "2 hours ago", "Repository": "nginx"}
        result = service._map_image(item)
        assert result["id"] == "img1"
        assert result["created"] == "2025"
        assert result["created_since"] == "2 hours ago"


class TestDockerEnvironment:
    def test_check_docker_installed_true(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Docker version 24.0", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        assert service.check_docker_installed("test") is True

    def test_check_docker_installed_false(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        assert service.check_docker_installed("test") is False

    def test_check_docker_installed_exception(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.side_effect = Exception("fail")
        assert service.check_docker_installed("test") is False

    def test_get_docker_version(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Docker version 24.0.7", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        version = service.get_docker_version("test")
        assert "24.0.7" in version

    def test_get_docker_version_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.side_effect = Exception("fail")
        assert service.get_docker_version("test") is None

    def test_check_docker_running_true(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "info", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        assert service.check_docker_running("test") is True

    def test_check_docker_running_false(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        assert service.check_docker_running("test") is False


class TestContainerManagement:
    def test_list_containers(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"ID":"abc","Names":"/web","State":"running","CreatedAt":"2025"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        containers = service.list_containers("test")
        assert len(containers) == 1
        assert containers[0]["name"] == "web"

    def test_list_containers_all(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"ID":"abc","Names":"web","State":"running"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        containers = service.list_containers("test", all=True)
        assert len(containers) == 1

    def test_start_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "abc123", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.start_container("test", "abc123")
        assert "abc123" in result

    def test_stop_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "abc123", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.stop_container("test", "abc123")
        assert "abc123" in result

    def test_stop_container_with_timeout(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        service.stop_container("test", "abc123", timeout=10)

    def test_restart_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.restart_container("test", "abc123")
        assert "重启" in result

    def test_kill_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.kill_container("test", "abc123")
        assert "强制停止" in result

    def test_remove_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_container("test", "abc123", force=True)
        assert "删除" in result

    def test_pause_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.pause_container("test", "abc123")
        assert "暂停" in result

    def test_unpause_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.unpause_container("test", "abc123")
        assert "恢复" in result

    def test_exec_in_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service.exec_in_container("test", "abc123", "ls")
        assert code == 0

    def test_get_container_logs(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "log line 1\nlog line 2\n", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        logs = service.get_container_logs("test", "abc123", tail=50)
        assert "log line" in logs

    def test_get_container_stats(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"CPU":"1.0%"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stats = service.get_container_stats("test", "abc123")
        assert len(stats) == 1


class TestImageManagement:
    def test_list_images(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"ID":"img1","Repository":"nginx","CreatedAt":"2025","CreatedSince":"2h"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        images = service.list_images("test")
        assert len(images) == 1

    def test_pull_image(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.pull_image("test", "nginx:latest")
        assert "nginx" in result

    def test_remove_image(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_image("test", "img1")
        assert "删除" in result

    def test_prune_images_empty(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.prune_images("test")
        assert result["SpaceReclaimed"] == 0


class TestNetworkManagement:
    def test_list_networks(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"bridge","ID":"net1"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        networks = service.list_networks("test")
        assert len(networks) == 1

    def test_create_network(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.create_network("test", "mynet")
        assert "mynet" in result

    def test_remove_network(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_network("test", "net1")
        assert "删除" in result

    def test_get_network_info_not_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="未找到"):
            service.get_network_info("test", "nonexistent")


class TestVolumeManagement:
    def test_list_volumes(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"vol1","Driver":"local"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        volumes = service.list_volumes("test")
        assert len(volumes) == 1

    def test_create_volume(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.create_volume("test", "myvol")
        assert "myvol" in result

    def test_remove_volume(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_volume("test", "vol1")
        assert "删除" in result

    def test_get_volume_info_not_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="未找到"):
            service.get_volume_info("test", "nonexistent")


class TestComposeManagement:
    def test_compose_up_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "started", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_up("test", "/app/docker-compose.yml")
        assert "started" in result

    def test_compose_up_directory(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "started", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_up("test", "/app")
        assert "started" in result

    def test_compose_down(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "stopped", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_down("test", "/app")
        assert "stopped" in result

    def test_compose_ps(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"web","State":"running"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_ps("test", "/app")
        assert len(result) == 1

    def test_compose_logs(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "log output", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_logs("test", "/app")
        assert "log" in result

    def test_compose_scale(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "scaled", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_scale("test", "/app", "web", 3)
        assert "scaled" in result
