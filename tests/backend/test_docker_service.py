import json
from unittest.mock import MagicMock, patch, call

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

    def test_error_default_exit_code(self):
        err = DockerCommandError("msg", -1)
        assert err.exit_code == -1


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
        assert isinstance(stderr, str)

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

    def test_exec_docker_json_empty_lines(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '\n\n{"ID":"abc"}\n\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service._exec_docker_json("test", ["ps"])
        assert len(result) == 1

    def test_exec_docker_simple_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "output", "err")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stdout, stderr = service._exec_docker_simple("test", ["ps"])
        assert stdout == "output"

    def test_exec_docker_simple_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError):
            service._exec_docker_simple("test", ["ps"])

    def test_exec_docker_simple_strips_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "  output  \n", "  err  \n")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stdout, stderr = service._exec_docker_simple("test", ["ps"])
        assert stdout == "output"
        assert stderr == "err"


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

    def test_exec_docker_streaming_with_stdout_data(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        recv_count = [0]
        def recv_side_effect(size):
            recv_count[0] += 1
            if recv_count[0] == 1:
                return b"hello "
            return b""
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 2
        mock_chan.recv_ready.side_effect = [True, True, False, False]
        mock_chan.recv.side_effect = [b"hello ", b"world"]
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker_streaming("test", ["ps"])
        assert "hello" in stdout

    def test_exec_docker_streaming_with_stderr_data(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 2
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.side_effect = [True, True, False, False]
        mock_chan.recv_stderr.side_effect = [b"err1", b"err2"]
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker_streaming("test", ["ps"])
        assert "err1" in stderr

    def test_exec_docker_streaming_with_callback(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        callback_outputs = []
        def on_output(stdout_chunk, stderr_chunk):
            callback_outputs.append((stdout_chunk, stderr_chunk))
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 2
        mock_chan.recv_ready.side_effect = [True, False, False]
        mock_chan.recv.return_value = b"out"
        mock_chan.recv_stderr_ready.side_effect = [True, False, False]
        mock_chan.recv_stderr.return_value = b"err"
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker_streaming("test", ["ps"], on_output=on_output)
        assert len(callback_outputs) >= 1

    def test_exec_docker_streaming_timeout(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        import time
        start = time.time()
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.exit_status_ready.return_value = False
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with patch("time.time", side_effect=[0, 0, 1000]):
            with pytest.raises(TimeoutError, match="超时"):
                service._exec_docker_streaming("test", ["ps"], timeout=600.0)

    def test_exec_docker_streaming_bytes_decode(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 1
        mock_chan.recv_ready.side_effect = [True, False, False]
        mock_chan.recv.return_value = b"\xe4\xb8\xad\xe6\x96\x87"
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service._exec_docker_streaming("test", ["ps"])
        assert "中文" in stdout


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

    def test_empty_list(self, service):
        result = service._pascal_to_camel([])
        assert result == []

    def test_single_char_key(self, service):
        items = [{"A": "val"}]
        result = service._pascal_to_camel(items)
        assert "a" in result[0]


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

    def test_map_container_non_string_names(self, service):
        item = {"ID": "abc", "Names": 123, "State": "Running"}
        result = service._map_container(item)
        assert result["name"] == 123

    def test_map_container_non_string_state(self, service):
        item = {"ID": "abc", "Names": "web", "State": 42}
        result = service._map_container(item)
        assert result["state"] == 42

    def test_map_container_other_keys(self, service):
        item = {"ID": "abc", "Image": "nginx", "Status": "Up 2 hours"}
        result = service._map_container(item)
        assert result["id"] == "abc"
        assert "image" in result
        assert "status" in result

    def test_map_container_empty_dict(self, service):
        result = service._map_container({})
        assert result == {}


class TestMapImage:
    def test_map_image(self, service):
        item = {"ID": "img1", "CreatedAt": "2025", "CreatedSince": "2 hours ago", "Repository": "nginx"}
        result = service._map_image(item)
        assert result["id"] == "img1"
        assert result["created"] == "2025"
        assert result["created_since"] == "2 hours ago"

    def test_map_image_other_keys(self, service):
        item = {"ID": "img1", "Repository": "nginx", "Tag": "latest", "Size": "100MB"}
        result = service._map_image(item)
        assert result["id"] == "img1"
        assert "repository" in result
        assert "tag" in result

    def test_map_image_empty(self, service):
        result = service._map_image({})
        assert result == {}


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

    def test_check_docker_running_exception(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.side_effect = Exception("fail")
        assert service.check_docker_running("test") is False

    def test_check_docker_permissions_all_access(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "docker wheel", ""),
            (0, "", ""),
            (0, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.check_docker_permissions("test")
        assert result["in_docker_group"] is True
        assert result["has_sudo_access"] is True
        assert result["can_run_docker"] is True
        assert "有 Docker 权限" in result["details"]

    def test_check_docker_permissions_docker_group_only(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "docker wheel", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.check_docker_permissions("test")
        assert result["in_docker_group"] is True
        assert result["has_sudo_access"] is False
        assert result["can_run_docker"] is False
        assert "可能需要重新登录" in result["details"]

    def test_check_docker_permissions_sudo_only(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "wheel", ""),
            (0, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.check_docker_permissions("test")
        assert result["in_docker_group"] is False
        assert result["has_sudo_access"] is True
        assert result["can_run_docker"] is False
        assert "sudo" in result["details"]

    def test_check_docker_permissions_no_access(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "wheel", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.check_docker_permissions("test")
        assert result["in_docker_group"] is False
        assert result["has_sudo_access"] is False
        assert result["can_run_docker"] is False
        assert "无 Docker 操作权限" in result["details"]

    def test_check_docker_permissions_bytes_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, b"docker wheel", ""),
            (0, "", ""),
            (0, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.check_docker_permissions("test")
        assert result["in_docker_group"] is True


class TestInstallDocker:
    def test_install_docker_ubuntu(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID=ubuntu\nVERSION="22.04"', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result

    def test_install_docker_centos(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID="centos"\nVERSION="9"', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result

    def test_install_docker_rhel(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID="rhel"\nVERSION="9"', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result

    def test_install_docker_debian(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID=debian\nVERSION="12"', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result

    def test_install_docker_redhat(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID="red hat enterprise linux"\n', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result

    def test_install_docker_unsupported_os(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID=fedora\nVERSION="39"', ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="不支持的操作系统"):
            service.install_docker("test")

    def test_install_docker_os_detect_fail(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="无法检测操作系统"):
            service.install_docker("test")

    def test_install_docker_install_fail(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, 'ID=ubuntu\n', ""),
            (1, "error output", "some error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="安装失败"):
            service.install_docker("test")

    def test_install_docker_bytes_os_release(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, b'ID=ubuntu\n', ""),
            (0, "DOCKER_INSTALLED\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.install_docker("test")
        assert "安装成功" in result


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

    def test_list_containers_empty(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        containers = service.list_containers("test")
        assert containers == []

    def test_get_container_info_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"ID":"abc","Name":"web"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.get_container_info("test", "abc")
        assert result["ID"] == "abc"

    def test_get_container_info_not_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        with pytest.raises(DockerCommandError, match="未找到"):
            service.get_container_info("test", "nonexistent")

    def test_start_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "abc123", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.start_container("test", "abc123")
        assert "abc123" in result

    def test_start_container_empty_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.start_container("test", "abc123")
        assert "已启动" in result

    def test_stop_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "abc123", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.stop_container("test", "abc123")
        assert "abc123" in result

    def test_stop_container_with_timeout(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        service.stop_container("test", "abc123", timeout=10)

    def test_stop_container_empty_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.stop_container("test", "abc123")
        assert "已停止" in result

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

    def test_remove_container_no_force(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_container("test", "abc123")
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

    def test_get_container_logs_with_timestamps(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "2025-01-01T00:00:00Z log", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        logs = service.get_container_logs("test", "abc123", timestamps=True)
        assert "log" in logs

    def test_get_container_stats_with_id(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"CPU":"1.0%"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stats = service.get_container_stats("test", "abc123")
        assert len(stats) == 1

    def test_get_container_stats_without_id(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"CPU":"1.0%"}\n{"CPU":"2.0%"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        stats = service.get_container_stats("test")
        assert len(stats) == 2


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

    def test_pull_image_with_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Status: Downloaded", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.pull_image("test", "nginx:latest")
        assert "Downloaded" in result

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
        assert result["ImagesDeleted"] == []

    def test_prune_images_with_data(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"SpaceReclaimed":1024,"ImagesDeleted":[{"Deleted":"sha256:abc"}]}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.prune_images("test")
        assert result["SpaceReclaimed"] == 1024

    def test_build_image(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "Successfully built img1", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.build_image("test", "myapp:latest", "/Dockerfile", "/context")
        assert "Successfully" in result

    def test_build_image_stderr_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "Building step 1/5")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.build_image("test", "myapp:latest", "/Dockerfile", "/context")
        assert "Building" in result

    def test_search_images(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"nginx","StarCount":10000}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.search_images("test", "nginx")
        assert len(result) == 1
        assert result[0]["Name"] == "nginx"


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

    def test_create_network_with_driver(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "net123", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.create_network("test", "mynet", driver="overlay")
        assert "net123" in result

    def test_remove_network(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_network("test", "net1")
        assert "删除" in result

    def test_get_network_info_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"mynet","ID":"net1"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.get_network_info("test", "net1")
        assert result["Name"] == "mynet"

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

    def test_create_volume_with_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "myvol", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.create_volume("test", "myvol")
        assert "myvol" in result

    def test_remove_volume(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.remove_volume("test", "vol1")
        assert "删除" in result

    def test_get_volume_info_found(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"vol1","Driver":"local"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.get_volume_info("test", "vol1")
        assert result["Name"] == "vol1"

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

    def test_compose_up_yaml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "started", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_up("test", "/app/compose.yaml")
        assert "started" in result

    def test_compose_up_directory(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "started", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_up("test", "/app")
        assert "started" in result

    def test_compose_up_detach(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "started", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_up("test", "/app", detach=True)
        assert "started" in result

    def test_compose_up_streaming(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 1
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service.compose_up_streaming("test", "/app")
        assert code == 0

    def test_compose_up_streaming_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_chan = MagicMock()
        exit_count = [0]
        def exit_side_effect():
            exit_count[0] += 1
            return exit_count[0] > 1
        mock_chan.recv_ready.return_value = False
        mock_chan.recv_stderr_ready.return_value = False
        mock_chan.exit_status_ready.side_effect = exit_side_effect
        mock_chan.recv_exit_status.return_value = 0
        mock_conn.manager.transport.open_session.return_value = mock_chan
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        code, stdout, stderr = service.compose_up_streaming("test", "/app/docker-compose.yml")
        assert code == 0

    def test_compose_down(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "stopped", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_down("test", "/app")
        assert "stopped" in result

    def test_compose_down_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "stopped", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_down("test", "/app/compose.yaml")
        assert "stopped" in result

    def test_compose_ps(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"web","State":"running"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_ps("test", "/app")
        assert len(result) == 1

    def test_compose_ps_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, '{"Name":"web","State":"running"}\n', "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_ps("test", "/app/docker-compose.yml")
        assert len(result) == 1

    def test_compose_logs(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "log output", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_logs("test", "/app")
        assert "log" in result

    def test_compose_logs_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "log output", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_logs("test", "/app/compose.yaml")
        assert "log" in result

    def test_compose_scale(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "scaled", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_scale("test", "/app", "web", 3)
        assert "scaled" in result

    def test_compose_scale_yml(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "scaled", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.compose_scale("test", "/app/docker-compose.yml", "web", 3)
        assert "scaled" in result


class TestFindComposeProjects:
    def test_find_compose_projects_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/app/docker-compose.yml\n/app2/compose.yaml\n", ""),
            (0, "/app\n", ""),
            (0, "/app2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.find_compose_projects("test")
        assert len(result) == 2
        assert result[0]["name"] in ("app", "app2")

    def test_find_compose_projects_empty(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.find_compose_projects("test")
        assert result == []

    def test_find_compose_projects_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.find_compose_projects("test")
        assert result == []

    def test_find_compose_projects_dirname_fail(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "/app/docker-compose.yml\n", ""),
            (1, "", "error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.find_compose_projects("test")
        assert len(result) == 1
        assert result[0]["path"] == "/app/docker-compose.yml"

    def test_find_compose_projects_custom_path(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        result = service.find_compose_projects("test", search_path="/opt")
        assert result == []
