from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from app.services.docker_store_service import (
    DockerStoreService,
    _human_readable_size,
    _parse_size_to_bytes,
    RUNTIME_APP_DIR,
    MANAGED_BY_LABEL,
)
from app.services.docker_service import DockerCommandError


@pytest.fixture
def service():
    return DockerStoreService()


class TestHumanReadableSize:
    def test_bytes(self):
        assert _human_readable_size(100) == "100.0 B"

    def test_kilobytes(self):
        assert _human_readable_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert _human_readable_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _human_readable_size(1024 ** 3) == "1.0 GB"

    def test_terabytes(self):
        assert _human_readable_size(1024 ** 4) == "1.0 TB"

    def test_petabytes(self):
        assert _human_readable_size(1024 ** 5) == "1.0 PB"

    def test_negative(self):
        assert _human_readable_size(-1) == "未知"

    def test_zero(self):
        assert _human_readable_size(0) == "0.0 B"

    def test_large_bytes(self):
        assert _human_readable_size(500) == "500.0 B"

    def test_fractional_kb(self):
        result = _human_readable_size(1536)
        assert "KB" in result


class TestParseSizeToBytes:
    def test_parse_mb(self):
        assert _parse_size_to_bytes("100MB") == 100 * 1024 ** 2

    def test_parse_gb(self):
        assert _parse_size_to_bytes("2GB") == 2 * 1024 ** 3

    def test_parse_kb(self):
        assert _parse_size_to_bytes("512KB") == 512 * 1024

    def test_parse_tb(self):
        assert _parse_size_to_bytes("1TB") == 1024 ** 4

    def test_parse_b(self):
        assert _parse_size_to_bytes("100B") == 100

    def test_parse_na(self):
        assert _parse_size_to_bytes("N/A") == -1

    def test_parse_empty(self):
        assert _parse_size_to_bytes("") == -1

    def test_parse_none_like(self):
        assert _parse_size_to_bytes(None) == -1

    def test_parse_plain_number(self):
        assert _parse_size_to_bytes("1024") == 1024

    def test_parse_invalid(self):
        assert _parse_size_to_bytes("abc") == -1

    def test_parse_float_mb(self):
        result = _parse_size_to_bytes("1.5MB")
        assert result == int(1.5 * 1024 ** 2)


class TestValidateAppId:
    def test_valid_id(self):
        DockerStoreService._validate_app_id("nginx")

    def test_valid_id_with_dash(self):
        DockerStoreService._validate_app_id("my-app")

    def test_empty_id(self):
        with pytest.raises(ValueError, match="不能为空"):
            DockerStoreService._validate_app_id("")

    def test_none_id(self):
        with pytest.raises(ValueError, match="不能为空"):
            DockerStoreService._validate_app_id(None)

    def test_non_string_id(self):
        with pytest.raises(ValueError, match="不能为空"):
            DockerStoreService._validate_app_id(123)

    def test_path_traversal(self):
        with pytest.raises(ValueError, match="路径穿越"):
            DockerStoreService._validate_app_id("../etc/passwd")

    def test_starts_with_slash(self):
        with pytest.raises(ValueError, match="不能以"):
            DockerStoreService._validate_app_id("/etc/passwd")

    def test_illegal_chars_angle(self):
        with pytest.raises(ValueError, match="非法字符"):
            DockerStoreService._validate_app_id("app<>test")

    def test_illegal_chars_colon(self):
        with pytest.raises(ValueError, match="非法字符"):
            DockerStoreService._validate_app_id("app:test")

    def test_illegal_chars_pipe(self):
        with pytest.raises(ValueError, match="非法字符"):
            DockerStoreService._validate_app_id("app|test")

    def test_illegal_chars_backslash(self):
        with pytest.raises(ValueError, match="非法字符"):
            DockerStoreService._validate_app_id("app\\test")

    def test_illegal_chars_null(self):
        with pytest.raises(ValueError, match="非法字符"):
            DockerStoreService._validate_app_id("app\x00test")


class TestValidatePath:
    def test_valid_path(self):
        DockerStoreService._validate_path(f"{RUNTIME_APP_DIR}/nginx/data")

    def test_invalid_path(self):
        with pytest.raises(ValueError, match="非法路径"):
            DockerStoreService._validate_path("/etc/passwd")

    def test_empty_path(self):
        with pytest.raises(ValueError, match="不能为空"):
            DockerStoreService._validate_path("")

    def test_none_path(self):
        with pytest.raises(ValueError, match="不能为空"):
            DockerStoreService._validate_path(None)

    def test_root_app_dir(self):
        DockerStoreService._validate_path(RUNTIME_APP_DIR)


class TestRenderComposeTemplate:
    def test_render_success(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("image: ${image_name}\nport: ${port}", encoding="utf-8")
        result = DockerStoreService._render_compose_template(
            str(template), {"image_name": "nginx", "port": "80"}
        )
        assert "nginx" in result
        assert "80" in result

    def test_render_file_not_found(self):
        with pytest.raises(ValueError, match="模板文件不存在"):
            DockerStoreService._render_compose_template("/nonexistent/path", {})

    def test_render_with_json_value(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("env: ${env_vars}", encoding="utf-8")
        result = DockerStoreService._render_compose_template(
            str(template), {"env_vars": {"key": "val"}}
        )
        assert "key" in result

    def test_render_with_int_value(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("port: ${port}", encoding="utf-8")
        result = DockerStoreService._render_compose_template(
            str(template), {"port": 8080}
        )
        assert "8080" in result

    def test_render_with_bool_value(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("debug: ${debug}", encoding="utf-8")
        result = DockerStoreService._render_compose_template(
            str(template), {"debug": True}
        )
        assert "True" in result

    def test_render_with_float_value(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("ratio: ${ratio}", encoding="utf-8")
        result = DockerStoreService._render_compose_template(
            str(template), {"ratio": 0.5}
        )
        assert "0.5" in result

    def test_render_os_error(self, tmp_path):
        template = tmp_path / "docker-compose.yml"
        template.write_text("image: nginx", encoding="utf-8")
        with patch("builtins.open", side_effect=OSError("permission denied")):
            with pytest.raises(ValueError, match="读取模板失败"):
                DockerStoreService._render_compose_template(str(template), {})


class TestExtractImagesFromCompose:
    def test_extract_images(self):
        content = "services:\n  web:\n    image: nginx:latest\n  db:\n    image: mysql:8.0"
        images = DockerStoreService._extract_images_from_compose(content)
        assert "nginx:latest" in images
        assert "mysql:8.0" in images

    def test_extract_images_empty(self):
        images = DockerStoreService._extract_images_from_compose("")
        assert images == []

    def test_extract_images_quoted(self):
        content = '    image: "redis:7"'
        images = DockerStoreService._extract_images_from_compose(content)
        assert "redis:7" in images

    def test_extract_images_single_quoted(self):
        content = "    image: 'postgres:15'"
        images = DockerStoreService._extract_images_from_compose(content)
        assert "postgres:15" in images

    def test_extract_images_no_tag(self):
        content = "    image: nginx"
        images = DockerStoreService._extract_images_from_compose(content)
        assert "nginx" in images


class TestParseSizeStr:
    def test_parse_mb(self):
        assert DockerStoreService._parse_size_str("5.123MB") == int(5.123 * 1024 ** 2)

    def test_parse_kb(self):
        assert DockerStoreService._parse_size_str("100KB") == 100 * 1024

    def test_parse_gb(self):
        assert DockerStoreService._parse_size_str("2GB") == 2 * 1024 ** 3

    def test_parse_tb(self):
        assert DockerStoreService._parse_size_str("1TB") == 1024 ** 4

    def test_parse_b(self):
        assert DockerStoreService._parse_size_str("512B") == 512

    def test_parse_plain(self):
        assert DockerStoreService._parse_size_str("1024") == 1024

    def test_parse_invalid(self):
        assert DockerStoreService._parse_size_str("abc") == 0

    def test_parse_empty(self):
        assert DockerStoreService._parse_size_str("") == 0

    def test_parse_whitespace(self):
        assert DockerStoreService._parse_size_str("  100KB  ") == 100 * 1024


class TestEnsureRuntimeDirs:
    def test_ensure_dirs_with_volumes(self, service):
        with patch.object(service, "_validate_path"), \
             patch.object(service, "_exec_remote_simple", return_value=("", "")):
            service._ensure_runtime_dirs("server1", "nginx", ["data", "logs"])

    def test_ensure_dirs_with_absolute_volumes(self, service):
        with patch.object(service, "_validate_path"), \
             patch.object(service, "_exec_remote_simple", return_value=("", "")):
            service._ensure_runtime_dirs("server1", "nginx", ["/custom/vol"])

    def test_ensure_dirs_with_empty_volumes(self, service):
        with patch.object(service, "_validate_path"), \
             patch.object(service, "_exec_remote_simple", return_value=("", "")):
            service._ensure_runtime_dirs("server1", "nginx", ["", "  "])

    def test_ensure_dirs_no_volumes(self, service):
        with patch.object(service, "_validate_path"), \
             patch.object(service, "_exec_remote_simple", return_value=("", "")):
            service._ensure_runtime_dirs("server1", "nginx", None)


class TestListApps:
    def test_list_apps_no_json(self, service):
        with patch.object(service, "_get_apps_json_path", return_value=None):
            result = service.list_apps()
            assert result == []

    def test_list_apps_with_category(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = json.dumps({
                "apps": [
                    {"id": "nginx", "category": "web"},
                    {"id": "mysql", "category": "database"},
                ]
            })
            result = service.list_apps(category="web")
            assert len(result) == 1
            assert result[0]["id"] == "nginx"

    def test_list_apps_json_decode_error(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = "invalid json"
            result = service.list_apps()
            assert result == []

    def test_list_apps_list_format(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = json.dumps([
                {"id": "nginx"},
            ])
            result = service.list_apps()
            assert len(result) == 1

    def test_list_apps_invalid_data_type(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = json.dumps("just a string")
            result = service.list_apps()
            assert result == []

    def test_list_apps_invalid_apps_type(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = json.dumps({"apps": "not a list"})
            result = service.list_apps()
            assert result == []

    def test_list_apps_os_error(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.side_effect = OSError("read error")
            result = service.list_apps()
            assert result == []

    def test_list_apps_no_category_filter(self, service):
        with patch.object(service, "_get_apps_json_path") as mock_path:
            mock_path.return_value = MagicMock()
            mock_path.return_value.read_text.return_value = json.dumps({
                "apps": [
                    {"id": "nginx", "category": "web"},
                    {"id": "mysql", "category": "database"},
                ]
            })
            result = service.list_apps()
            assert len(result) == 2


class TestGetApp:
    def test_get_app_found(self, service):
        with patch.object(service, "list_apps", return_value=[{"id": "nginx", "name": "Nginx"}]):
            result = service.get_app("nginx")
            assert result["id"] == "nginx"

    def test_get_app_not_found(self, service):
        with patch.object(service, "list_apps", return_value=[{"id": "nginx"}]):
            with pytest.raises(ValueError, match="未找到"):
                service.get_app("nonexistent")

    def test_get_app_invalid_id(self, service):
        with pytest.raises(ValueError):
            service.get_app("")


class TestGetAppDetail:
    def test_get_app_detail(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx", "name": "Nginx"}), \
             patch.object(service, "get_app_status", return_value={"running": True, "containers": []}):
            result = service.get_app_detail("server1", "nginx")
            assert result["account_alias"] == "server1"
            assert result["status"]["running"] is True

    def test_get_app_detail_status_error(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx"}), \
             patch.object(service, "get_app_status", side_effect=Exception("error")):
            result = service.get_app_detail("server1", "nginx")
            assert result["status"]["running"] is False
            assert "未运行" in result["status"]["message"]


class TestInstallApp:
    def test_install_app_success(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/templates/nginx/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="rendered compose"), \
             patch.object(service, "_validate_path"), \
             patch.object(service, "_ensure_runtime_dirs"), \
             patch.object(service, "_get_connection") as mock_get_conn, \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (0, "", "")
            sftp_mock = MagicMock()
            mock_conn.manager.open_sftp.return_value = sftp_mock
            mock_docker.compose_up.return_value = "started"
            result = service.install_app("server1", "nginx", {})
            assert result["app_id"] == "nginx"

    def test_install_app_invalid_id(self, service):
        with pytest.raises(ValueError):
            service.install_app("server1", "", {})

    def test_install_app_mkdir_fail(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/templates/nginx/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="rendered"), \
             patch.object(service, "_validate_path"), \
             patch.object(service, "_ensure_runtime_dirs"), \
             patch.object(service, "_get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (1, "", "mkdir failed")
            with pytest.raises(DockerCommandError, match="创建应用目录失败"):
                service.install_app("server1", "nginx", {})


class TestInstallAppStreaming:
    def test_install_app_streaming_success(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/templates/nginx/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="rendered"), \
             patch.object(service, "_validate_path"), \
             patch.object(service, "_ensure_runtime_dirs"), \
             patch.object(service, "_get_connection") as mock_get_conn, \
             patch.object(service, "_extract_images_from_compose", return_value=["nginx"]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (0, "", "")
            sftp_mock = MagicMock()
            mock_conn.manager.open_sftp.return_value = sftp_mock
            mock_docker.compose_up_streaming.return_value = (0, "started", "")
            progress_events = []
            result = service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            assert result["app_id"] == "nginx"

    def test_install_app_streaming_failure(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/templates/nginx/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="rendered"), \
             patch.object(service, "_validate_path"), \
             patch.object(service, "_ensure_runtime_dirs"), \
             patch.object(service, "_get_connection") as mock_get_conn, \
             patch.object(service, "_extract_images_from_compose", return_value=["nginx"]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (0, "", "")
            sftp_mock = MagicMock()
            mock_conn.manager.open_sftp.return_value = sftp_mock
            mock_docker.compose_up_streaming.return_value = (1, "", "compose error")
            progress_events = []
            with pytest.raises(DockerCommandError):
                service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)

    def test_install_app_streaming_exception(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", side_effect=Exception("unexpected")):
            progress_events = []
            with pytest.raises(Exception, match="unexpected"):
                service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            error_events = [e for e in progress_events if e.get("type") == "error"]
            assert len(error_events) > 0


class TestUninstallApp:
    def test_uninstall_without_purge(self, service):
        with patch.object(service, "_validate_path"), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker.compose_down.return_value = "stopped"
            result = service.uninstall_app("server1", "nginx")
            assert "数据保留" in result["message"]

    def test_uninstall_with_purge(self, service):
        with patch.object(service, "_validate_path"), \
             patch.object(service, "_exec_remote_simple", return_value=("", "")), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker.compose_down.return_value = "stopped"
            result = service.uninstall_app("server1", "nginx", purge_data=True)
            assert "清理数据" in result["message"]

    def test_uninstall_invalid_id(self, service):
        with pytest.raises(ValueError):
            service.uninstall_app("server1", "")


class TestGetAppStatus:
    def test_get_app_status_no_containers(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = []
            result = service.get_app_status("server1", "nginx")
            assert result["running"] is False
            assert result["containers"] == []

    def test_get_app_status_running(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"Names": "panel-nginx-web", "State": "running"}]
            mock_docker._map_container.return_value = {"name": "panel-nginx-web", "state": "running", "id": "abc123"}
            result = service.get_app_status("server1", "nginx")
            assert result["running"] is True
            assert result["running_count"] == 1

    def test_get_app_status_stopped(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"Names": "panel-nginx-web", "State": "exited"}]
            mock_docker._map_container.return_value = {"name": "panel-nginx-web", "state": "exited", "id": "abc123"}
            result = service.get_app_status("server1", "nginx")
            assert result["running"] is False

    def test_get_app_status_mixed(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [
                {"Names": "panel-nginx-web", "State": "running"},
                {"Names": "panel-nginx-db", "State": "exited"},
            ]
            mock_docker._map_container.side_effect = [
                {"name": "panel-nginx-web", "state": "running", "id": "abc"},
                {"name": "panel-nginx-db", "state": "exited", "id": "def"},
            ]
            result = service.get_app_status("server1", "nginx")
            assert result["running"] is True
            assert result["running_count"] == 1
            assert result["total_count"] == 2

    def test_get_app_status_invalid_id(self, service):
        with pytest.raises(ValueError):
            service.get_app_status("server1", "")


class TestGetAllAppStatuses:
    def test_get_all_app_statuses_no_apps(self, service):
        with patch.object(service, "list_apps", return_value=[]):
            result = service.get_all_app_statuses("server1")
            assert result == []

    def test_get_all_app_statuses_not_installed(self, service):
        with patch.object(service, "list_apps", return_value=[{"id": "nginx"}]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = []
            result = service.get_all_app_statuses("server1")
            assert len(result) == 1
            assert result[0]["state"] == "not_installed"

    def test_get_all_app_statuses_running(self, service):
        with patch.object(service, "list_apps", return_value=[{"id": "nginx"}]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"Names": "panel-nginx-web", "State": "running"}]
            mock_docker._map_container.return_value = {"name": "panel-nginx-web", "state": "running", "id": "abc"}
            result = service.get_all_app_statuses("server1")
            assert result[0]["state"] == "running"

    def test_get_all_app_statuses_stopped(self, service):
        with patch.object(service, "list_apps", return_value=[{"id": "nginx"}]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"Names": "panel-nginx-web", "State": "exited"}]
            mock_docker._map_container.return_value = {"name": "panel-nginx-web", "state": "exited", "id": "abc"}
            result = service.get_all_app_statuses("server1")
            assert result[0]["state"] == "stopped"

    def test_get_all_app_statuses_no_id_app(self, service):
        with patch.object(service, "list_apps", return_value=[{}]), \
             patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = []
            result = service.get_all_app_statuses("server1")
            assert len(result) == 0


class TestGetAppSizeInfo:
    def test_get_app_size_info(self, service):
        with patch.object(service, "_get_image_sizes", return_value={"total": 1024, "images": []}), \
             patch.object(service, "_get_container_sizes", return_value={"total": 512, "containers": []}), \
             patch.object(service, "_get_volume_sizes", return_value={"total": 0, "volumes": []}), \
             patch.object(service, "_get_data_dir_size", return_value=2048):
            result = service.get_app_size_info("server1", "nginx")
            assert result["total_size"] == 1024 + 512 + 0 + 2048
            assert result["app_id"] == "nginx"

    def test_get_app_size_info_with_exceptions(self, service):
        with patch.object(service, "_get_image_sizes", side_effect=Exception("err")), \
             patch.object(service, "_get_container_sizes", side_effect=Exception("err")), \
             patch.object(service, "_get_volume_sizes", side_effect=Exception("err")), \
             patch.object(service, "_get_data_dir_size", side_effect=Exception("err")):
            result = service.get_app_size_info("server1", "nginx")
            assert result["total_size"] == 0

    def test_get_app_size_info_with_components(self, service):
        with patch.object(service, "_get_image_sizes", return_value={
            "total": 1024, "images": [{"repository": "nginx", "size": 1024, "id": "img1"}]
        }), \
             patch.object(service, "_get_container_sizes", return_value={
            "total": 512, "containers": [{"name": "web", "size": 512, "id": "c1"}]
        }), \
             patch.object(service, "_get_volume_sizes", return_value={
            "total": 256, "volumes": [{"name": "vol1", "size": 256, "mountpoint": "/var/lib/docker/volumes/vol1"}]
        }), \
             patch.object(service, "_get_data_dir_size", return_value=2048):
            result = service.get_app_size_info("server1", "nginx")
            assert result["total_size"] == 1024 + 512 + 256 + 2048
            assert len(result["components"]) == 4

    def test_get_app_size_info_invalid_id(self, service):
        with pytest.raises(ValueError):
            service.get_app_size_info("server1", "")


class TestGetImageSizes:
    def test_no_images(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_simple.return_value = ("", "")
            result = service._get_image_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["images"] == []

    def test_with_matched_images(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_simple.return_value = ("nginx:latest\n", "")
            mock_docker._exec_docker_json.return_value = [
                {"Repository": "nginx", "Tag": "latest", "ID": "img1", "Size": "100MB"}
            ]
            result = service._get_image_sizes("server1", "nginx")
            assert result["total"] > 0
            assert len(result["images"]) == 1

    def test_with_no_matched_images(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_simple.return_value = ("nginx:latest\n", "")
            mock_docker._exec_docker_json.return_value = [
                {"Repository": "mysql", "Tag": "8.0", "ID": "img2", "Size": "500MB"}
            ]
            result = service._get_image_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["images"] == []


class TestGetContainerSizes:
    def test_no_containers(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = []
            result = service._get_container_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["containers"] == []

    def test_with_containers(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"ID": "c1", "Names": "web"}]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"SizeRw": 1024, "GraphDriver": {"Data": {}}}],
            ]
            result = service._get_container_sizes("server1", "nginx")
            assert result["total"] == 1024
            assert len(result["containers"]) == 1

    def test_with_zero_size_rw(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"ID": "c1", "Names": "web"}]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"SizeRw": 0, "GraphDriver": {"Data": {}}}],
            ]
            result = service._get_container_sizes("server1", "nginx")
            assert result["total"] == 0

    def test_with_inspect_exception(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"ID": "c1", "Names": "web"}]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                DockerCommandError("inspect failed", 1),
            ]
            result = service._get_container_sizes("server1", "nginx")
            assert result["total"] == 0


class TestGetVolumeSizes:
    def test_no_containers(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = []
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["volumes"] == []

    def test_with_volumes(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": "/var/lib/docker/volumes/vol1"}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_simple.return_value = ("1024 /vol", "")
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 1024
            assert len(result["volumes"]) == 1

    def test_with_no_volume_mounts(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "bind", "Source": "/host/path"}]}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["volumes"] == []


class TestGetDataDirSize:
    def test_success(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker.return_value = (0, "2048 /app_data", "")
            result = service._get_data_dir_size("server1", "/www/server/apps/nginx")
            assert result == 2048

    def test_failure(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker.return_value = (1, "", "error")
            result = service._get_data_dir_size("server1", "/www/server/apps/nginx")
            assert result == 0

    def test_exception(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker.side_effect = Exception("fail")
            result = service._get_data_dir_size("server1", "/www/server/apps/nginx")
            assert result == 0

    def test_invalid_output(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker.return_value = (0, "invalid output", "")
            result = service._get_data_dir_size("server1", "/www/server/apps/nginx")
            assert result == 0


class TestGetImageVersionSizes:
    def test_get_image_version_sizes_no_template(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx", "versions": ["latest"]}), \
             patch.object(service, "_get_image_name_from_template", return_value=None):
            result = service.get_image_version_sizes("nginx")
            assert result["image_name"] is None
            assert result["message"] is not None

    def test_get_image_version_sizes_with_image(self, service):
        with patch.object(service, "get_app", return_value={"id": "nginx", "versions": ["latest"]}), \
             patch.object(service, "_get_image_name_from_template", return_value="nginx"), \
             patch.object(service, "_query_docker_hub_size", return_value={
                 "size": 1024000, "size_human": "1.0 MB", "status": "found",
                 "compressed_size": 0, "compressed_size_human": "未知",
                 "architecture": "amd64", "os": "linux", "last_updated": "2025-01-01",
             }):
            result = service.get_image_version_sizes("nginx")
            assert result["image_name"] == "nginx"
            assert len(result["versions"]) == 1

    def test_get_image_name_from_template(self, service):
        with patch.object(service, "_get_template_path", return_value="/fake/path"), \
             patch("pathlib.Path.read_text", return_value="image: nginx:latest\nports:\n  - 80"):
            result = service._get_image_name_from_template("nginx")
            assert result == "nginx"

    def test_get_image_name_with_variable(self, service):
        with patch.object(service, "_get_template_path", return_value="/fake/path"), \
             patch("pathlib.Path.read_text", return_value="image: nginx:${VERSION}"):
            result = service._get_image_name_from_template("nginx")
            assert result == "nginx"

    def test_get_image_name_template_error(self, service):
        with patch.object(service, "_get_template_path", side_effect=Exception("err")):
            result = service._get_image_name_from_template("nginx")
            assert result is None

    def test_get_image_name_no_image_line(self, service):
        with patch.object(service, "_get_template_path", return_value="/fake/path"), \
             patch("pathlib.Path.read_text", return_value="services:\n  web:\n    ports:\n      - 80"):
            result = service._get_image_name_from_template("nginx")
            assert result is None


class TestQueryDockerHubSize:
    def test_query_docker_hub_official_image(self, service):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "images": [{"architecture": "amd64", "os": "linux", "size": 1024000}],
                "last_updated": "2025-01-01",
            }).encode()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = service._query_docker_hub_size("nginx", "latest")
            assert result["status"] == "found"
            assert result["size"] == 1024000

    def test_query_docker_hub_non_amd64(self, service):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "images": [{"architecture": "arm64", "os": "linux", "size": 512000}],
                "last_updated": "2025-01-01",
            }).encode()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = service._query_docker_hub_size("nginx", "latest")
            assert result["status"] == "found"
            assert result["architecture"] == "arm64"

    def test_query_docker_hub_non_official_image(self, service):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "images": [{"architecture": "amd64", "os": "linux", "size": 2048000}],
                "last_updated": "2025-01-01",
            }).encode()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = service._query_docker_hub_size("myuser/myapp", "latest")
            assert result["status"] == "found"

    def test_query_docker_hub_404(self, service):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("", 404, "Not Found", {}, None)):
            result = service._query_docker_hub_size("nonexistent", "latest")
            assert result["status"] == "not_found"

    def test_query_docker_hub_500(self, service):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("", 500, "Server Error", {}, None)):
            result = service._query_docker_hub_size("nginx", "latest")
            assert "error_500" in result["status"]

    def test_query_docker_hub_error(self, service):
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = service._query_docker_hub_size("nginx", "latest")
            assert "error" in result["status"]

    def test_query_docker_hub_no_images_with_full_size(self, service):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "images": [],
                "full_size": 2048000,
            }).encode()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = service._query_docker_hub_size("nginx", "latest")
            assert result["status"] == "found"
            assert result["size"] == 2048000

    def test_query_docker_hub_no_images_no_full_size(self, service):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "images": [],
            }).encode()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = service._query_docker_hub_size("nginx", "latest")
            assert result["status"] == "not_found"


class TestExecRemote:
    def test_exec_remote_success(self, service):
        with patch.object(service, "_get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (0, "output", "")
            code, stdout, stderr = service._exec_remote("server1", "ls")
            assert code == 0

    def test_exec_remote_bytes_output(self, service):
        with patch.object(service, "_get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.manager.exec_command.return_value = (0, b"bytes", b"err")
            code, stdout, stderr = service._exec_remote("server1", "ls")
            assert isinstance(stdout, str)
            assert isinstance(stderr, str)

    def test_exec_remote_account_not_found(self, service):
        with patch("app.services.docker_store_service.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                service._exec_remote("missing", "ls")

    def test_exec_remote_simple_success(self, service):
        with patch.object(service, "_exec_remote", return_value=(0, "output", "")):
            stdout, stderr = service._exec_remote_simple("server1", "ls")
            assert stdout == "output"

    def test_exec_remote_simple_failure(self, service):
        with patch.object(service, "_exec_remote", return_value=(1, "", "error")):
            with pytest.raises(DockerCommandError):
                service._exec_remote_simple("server1", "bad_cmd")
