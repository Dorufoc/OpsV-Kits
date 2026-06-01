from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.docker_store_service import (
    DockerStoreService,
    STORE_TEMPLATE_DIR,
)
from app.services.docker_service import DockerCommandError


@pytest.fixture
def service():
    return DockerStoreService()


class TestGetAppsJsonPathFallbacks:
    def test_method2_fallback(self, service):
        with patch.object(Path, "is_file", side_effect=[False, True]):
            result = service._get_apps_json_path()
            assert result is not None

    def test_method3_fallback(self, service):
        call_count = 0
        original_is_file = Path.is_file

        def fake_is_file(self):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False
            if call_count == 3:
                return True
            return original_is_file(self)

        with patch.object(Path, "is_file", fake_is_file):
            result = service._get_apps_json_path()
            assert result is not None

    def test_all_methods_fail(self, service):
        with patch.object(Path, "is_file", return_value=False):
            result = service._get_apps_json_path()
            assert result is None


class TestGetTemplatePathFallbacks:
    def test_method2_fallback(self, service):
        with patch.object(Path, "is_file", side_effect=[False, True]):
            result = service._get_template_path("nginx")
            assert result is not None

    def test_method3_fallback(self, service):
        call_count = 0

        def fake_is_file(self):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False
            if call_count == 3:
                return True
            return False

        with patch.object(Path, "is_file", fake_is_file):
            result = service._get_template_path("nginx")
            assert result is not None

    def test_all_methods_fail(self, service):
        with patch.object(Path, "is_file", return_value=False):
            with pytest.raises(ValueError, match="应用模板不存在"):
                service._get_template_path("nonexistent")


class TestParsePullOutput:
    def _setup_streaming_mocks(self, service, pull_chunks):
        def fake_compose_up_streaming(alias, path, detach=True, on_output=None):
            for stdout_chunk, stderr_chunk in pull_chunks:
                if on_output:
                    on_output(stdout_chunk, stderr_chunk)
            return (0, "", "")

        return fake_compose_up_streaming

    def test_pull_complete_downloaded(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/t/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="image: nginx"), \
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

            mock_docker.compose_up_streaming.side_effect = self._setup_streaming_mocks(
                service, [("Status: Downloaded newer image for nginx:latest\n", "")]
            )

            progress_events = []
            result = service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            assert result["app_id"] == "nginx"
            complete_events = [e for e in progress_events if e.get("type") == "pull_complete"]
            assert len(complete_events) >= 1

    def test_pull_complete_up_to_date(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/t/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="image: nginx"), \
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

            mock_docker.compose_up_streaming.side_effect = self._setup_streaming_mocks(
                service, [("Status: Image is up to date for nginx:latest\n", "")]
            )

            progress_events = []
            service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            complete_events = [e for e in progress_events if e.get("type") == "pull_complete"]
            assert len(complete_events) >= 1

    def test_layer_progress(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/t/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="image: nginx"), \
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

            mock_docker.compose_up_streaming.side_effect = self._setup_streaming_mocks(
                service, [("abc123: Downloading [=========>  ]  5.123MB/10.456MB\n", "")]
            )

            progress_events = []
            service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            progress_pull = [e for e in progress_events if e.get("type") == "pull_progress"]
            assert len(progress_pull) >= 1
            assert progress_pull[0]["layer"] == "abc123"

    def test_extracting_progress(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/t/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="image: nginx"), \
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

            mock_docker.compose_up_streaming.side_effect = self._setup_streaming_mocks(
                service, [("def456: Extracting [=========> ]     1.23MB/5.67MB\n", "")]
            )

            progress_events = []
            service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            extracting = [e for e in progress_events if e.get("type") == "pull_progress" and e.get("action") == "extracting"]
            assert len(extracting) >= 1

    def test_log_output(self, service):
        with patch.object(service, "_validate_app_id"), \
             patch.object(service, "get_app", return_value={"id": "nginx", "template": "docker-compose.yml", "volumes": []}), \
             patch.object(service, "_get_template_path", return_value="/t/docker-compose.yml"), \
             patch.object(service, "_render_compose_template", return_value="image: nginx"), \
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

            mock_docker.compose_up_streaming.side_effect = self._setup_streaming_mocks(
                service, [("Pulling from library/nginx\n", ""), ("Digest: sha256:abc123\n", "")]
            )

            progress_events = []
            service.install_app_streaming("server1", "nginx", {}, on_progress=progress_events.append)
            log_events = [e for e in progress_events if e.get("type") == "log"]
            assert len(log_events) >= 1


class TestParseSizeStrValueError:
    def test_value_error_returns_zero(self):
        with patch("builtins.float", side_effect=ValueError("bad")):
            result = DockerStoreService._parse_size_str("abcMB")
            assert result == 0


class TestGetVolumeSizesInspectException:
    def test_container_inspect_exception_continues(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                Exception("inspect failed"),
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0
            assert result["volumes"] == []

    def test_volume_size_parse_error_backup_fails(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": "/var/lib/docker/volumes/vol1"}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_simple.return_value = ("invalid output", "")
            mock_docker._exec_docker.return_value = (1, "", "error")
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0

    def test_volume_size_backup_success(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": "/var/lib/docker/volumes/vol1"}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_simple.return_value = ("invalid", "")
            mock_docker._exec_docker.return_value = (0, "4096 /vol", "")
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 4096
            assert len(result["volumes"]) == 1

    def test_volume_size_backup_parse_error(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": "/var/lib/docker/volumes/vol1"}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_simple.return_value = ("invalid", "")
            mock_docker._exec_docker.return_value = (0, "not_a_number /vol", "")
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0

    def test_volume_processing_exception(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                Exception("volume inspect error"),
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0

    def test_volume_no_mountpoint(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": ""}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0

    def test_volume_zero_size_skipped(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.side_effect = [
                [{"ID": "c1", "Names": "web"}],
                [{"Mounts": [{"Type": "volume", "Name": "vol1"}]}],
                [{"Mountpoint": "/var/lib/docker/volumes/vol1"}],
            ]
            mock_docker._map_container.return_value = {"id": "c1", "name": "web"}
            mock_docker._exec_docker_simple.return_value = ("0 /vol", "")
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0
            assert len(result["volumes"]) == 0

    def test_container_no_id_skipped(self, service):
        with patch("app.services.docker_store_service.docker_service") as mock_docker:
            mock_docker._exec_docker_json.return_value = [{"ID": "", "Names": "web"}]
            mock_docker._map_container.return_value = {"id": "", "name": "web"}
            result = service._get_volume_sizes("server1", "nginx")
            assert result["total"] == 0
