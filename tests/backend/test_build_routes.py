import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _mock_task_dict(**overrides):
    base = {
        "task_id": "task-001",
        "account_alias": "test-server",
        "project_path": "/opt/project",
        "action": "compile",
        "status": "running",
        "started_at": "2024-01-01T00:00:00",
        "completed_at": None,
        "log": "",
        "exit_code": None,
        "pid": None,
    }
    base.update(overrides)
    return base


def _mock_install_task_dict(**overrides):
    base = {
        "task_id": "install-001",
        "account_alias": "test-server",
        "components": ["java-17", "maven"],
        "status": "running",
        "progress": 0.0,
        "message": "安装中",
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    base.update(overrides)
    return base


class TestCheckEnvironmentFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_check_environment_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_environment.side_effect = Exception("SSH连接失败")
        response = client.get(
            "/api/environment/check?account_alias=test&project_path=/opt"
        )
        assert response.status_code == 500

    @patch("app.api.routes.build.ssh_account_service")
    def test_check_environment_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.get(
            "/api/environment/check?account_alias=missing&project_path=/opt"
        )
        assert response.status_code == 404


class TestInstallEnvironmentAdvanced:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_auto_detect_java_version(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_java.return_value = {
            "required": "17", "compatible": False
        }
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict(
            components=["java-17", "maven"]
        )
        mock_build.install_environment.return_value = mock_task
        response = client.post(
            "/api/environment/install",
            json={"account_alias": "test-server", "project_path": "/opt"},
        )
        assert response.status_code == 200
        call_args = mock_build.install_environment.call_args
        assert call_args.kwargs.get("java_version") == "17" or call_args[1].get("java_version") == "17"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_auto_detect_java_compatible(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_java.return_value = {
            "required": "17", "compatible": True
        }
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict()
        mock_build.install_environment.return_value = mock_task
        response = client.post(
            "/api/environment/install",
            json={"account_alias": "test-server", "project_path": "/opt"},
        )
        assert response.status_code == 200

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_auto_detect_java_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_java.side_effect = Exception("检测失败")
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict()
        mock_build.install_environment.return_value = mock_task
        response = client.post(
            "/api/environment/install",
            json={"account_alias": "test-server", "project_path": "/opt"},
        )
        assert response.status_code == 200

    @patch("app.api.routes.build.ssh_account_service")
    def test_install_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/environment/install",
            json={"account_alias": "missing"},
        )
        assert response.status_code == 404


class TestCompileFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_compile_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/compile",
            json={"account_alias": "missing", "project_path": "/opt"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_compile_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.compile_project.side_effect = Exception("编译失败")
        response = client.post(
            "/api/build/compile",
            json={"account_alias": "test", "project_path": "/opt"},
        )
        assert response.status_code == 500


class TestPackageFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_package_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/package",
            json={"account_alias": "missing", "project_path": "/opt"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_package_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.package_project.side_effect = Exception("打包失败")
        response = client.post(
            "/api/build/package",
            json={"account_alias": "test", "project_path": "/opt"},
        )
        assert response.status_code == 500


class TestTestProjectFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_test_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/test",
            json={"account_alias": "missing", "project_path": "/opt"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_test_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.test_project.side_effect = Exception("测试失败")
        response = client.post(
            "/api/build/test",
            json={"account_alias": "test", "project_path": "/opt"},
        )
        assert response.status_code == 500


class TestRunJarFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_jar_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/run/jar",
            json={"account_alias": "missing", "project_path": "/opt", "jar_path": "app.jar"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_jar_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.run_jar.side_effect = Exception("运行失败")
        response = client.post(
            "/api/build/run/jar",
            json={"account_alias": "test", "project_path": "/opt", "jar_path": "app.jar"},
        )
        assert response.status_code == 500


class TestRunSpringBootFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_spring_boot_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/run/spring-boot",
            json={"account_alias": "missing", "project_path": "/opt"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_spring_boot_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.run_spring_boot.side_effect = Exception("启动失败")
        response = client.post(
            "/api/build/run/spring-boot",
            json={"account_alias": "test", "project_path": "/opt"},
        )
        assert response.status_code == 500


class TestRunExecJavaFailures:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_exec_account_not_found(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/run/exec",
            json={"account_alias": "missing", "project_path": "/opt", "main_class": "Main"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_exec_service_exception(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.run_exec_java.side_effect = Exception("执行失败")
        response = client.post(
            "/api/build/run/exec",
            json={"account_alias": "test", "project_path": "/opt", "main_class": "Main"},
        )
        assert response.status_code == 500


class TestGenericRun:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_exec_mode(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run")
        mock_build.run_exec_java.return_value = mock_task
        response = client.post(
            "/api/build/run",
            json={
                "account_alias": "test",
                "project_path": "/opt",
                "run_mode": "exec",
                "main_class": "com.example.Main",
            },
        )
        assert response.status_code == 200
        mock_build.run_exec_java.assert_called_once()

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_spring_boot_mode(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run")
        mock_build.run_spring_boot.return_value = mock_task
        response = client.post(
            "/api/build/run",
            json={
                "account_alias": "test",
                "project_path": "/opt",
                "run_mode": "spring-boot",
            },
        )
        assert response.status_code == 200
        mock_build.run_spring_boot.assert_called_once()

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_default_mode(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run")
        mock_build.run_spring_boot.return_value = mock_task
        response = client.post(
            "/api/build/run",
            json={
                "account_alias": "test",
                "project_path": "/opt",
            },
        )
        assert response.status_code == 200
        mock_build.run_spring_boot.assert_called_once()

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_failure(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.run_spring_boot.side_effect = Exception("运行失败")
        response = client.post(
            "/api/build/run",
            json={"account_alias": "test", "project_path": "/opt"},
        )
        assert response.status_code == 500

    @patch("app.api.routes.build.ssh_account_service")
    def test_generic_run_account_not_found(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.post(
            "/api/build/run",
            json={"account_alias": "missing", "project_path": "/opt"},
        )
        assert response.status_code == 404


class TestStopTaskAdvanced:
    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_body(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.status = "running"
        mock_build.get_build_task.return_value = mock_task
        mock_build.stop_build_task.return_value = True
        response = client.post(
            "/api/build/stop",
            json={"task_id": "task-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_body_not_found(self, mock_build, client):
        mock_build.get_build_task.return_value = None
        response = client.post(
            "/api/build/stop",
            json={"task_id": "nonexistent"},
        )
        assert response.status_code == 404


class TestBuildStatusAdvanced:
    @patch("app.api.routes.build.build_service")
    def test_get_build_status_not_found(self, mock_build, client):
        mock_build.get_build_task.return_value = None
        response = client.get("/api/build/status/nonexistent")
        assert response.status_code == 404


class TestBuildLogAdvanced:
    @patch("app.api.routes.build.build_service")
    def test_get_run_log_task_not_found(self, mock_build, client):
        mock_build.get_build_task.return_value = None
        response = client.get("/api/build/log/nonexistent?max_lines=100")
        assert response.status_code == 404

    @patch("app.api.routes.build.build_service")
    def test_get_run_log_read_failure(self, mock_build, client):
        mock_task = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        mock_build.read_run_log.side_effect = Exception("读取失败")
        response = client.get("/api/build/log/task-123?max_lines=100")
        assert response.status_code == 500


class TestBuildHistoryAdvanced:
    @patch("app.api.routes.build.build_service")
    def test_get_build_history_with_alias(self, mock_build, client):
        mock_build.get_build_history.return_value = [
            _mock_task_dict(task_id="task-1", account_alias="test-server")
        ]
        response = client.get("/api/build/history?account_alias=test-server&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data

    @patch("app.api.routes.build.build_service")
    def test_get_build_history_empty(self, mock_build, client):
        mock_build.get_build_history.return_value = []
        response = client.get("/api/build/history")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []


class TestVerifyAccountHelper:
    @patch("app.api.routes.build.ssh_account_service")
    def test_verify_account_missing(self, mock_ssh, client):
        mock_ssh.get_account.return_value = None
        response = client.get(
            "/api/environment/check?account_alias=missing&project_path=/opt"
        )
        assert response.status_code == 404
