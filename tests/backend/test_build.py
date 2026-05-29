"""构建和编译接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestEnvironmentCheck:
    """环境检测接口测试"""

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_check_environment_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_build_service.check_environment.return_value = {
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "java": {"installed": True, "version": "17.0.1"},
            "maven": {"installed": True, "version": "3.8.6"},
            "all_ready": True,
        }
        response = client.get(
            "/api/environment/check?account_alias=test-server&project_path=/opt/project"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["all_ready"] is True

    @patch("app.api.routes.build.ssh_account_service")
    def test_check_environment_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get(
            "/api/environment/check?account_alias=nonexistent&project_path=/opt/project"
        )
        assert response.status_code == 404


class TestEnvironmentInstall:
    """环境安装接口测试"""

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_environment_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "task-123",
            "account_alias": "test-server",
            "components": ["java", "maven"],
            "status": "running",
            "progress": 0.0,
            "message": "安装中",
            "started_at": None,
            "completed_at": None,
            "error": None,
        }
        mock_build_service.install_environment.return_value = mock_task

        response = client.post(
            "/api/environment/install",
            json={
                "account_alias": "test-server",
                "java_version": "17",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] == "running"

    @patch("app.api.routes.build.ssh_account_service")
    def test_install_environment_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/environment/install",
            json={"account_alias": "nonexistent"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_get_install_status(self, mock_build_service, mock_ssh_service, client):
        mock_build_service.get_task_dict.return_value = {
            "task_id": "task-123",
            "account_alias": "test-server",
            "components": ["java", "maven"],
            "status": "completed",
            "progress": 100.0,
            "message": "安装完成",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:10:00",
            "error": None,
        }
        response = client.get("/api/environment/status?task_id=task-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0

    @patch("app.api.routes.build.build_service")
    def test_get_install_status_task_not_found(self, mock_build_service, client):
        mock_build_service.get_task_dict.return_value = None
        response = client.get("/api/environment/status?task_id=nonexistent")
        assert response.status_code == 404


class TestBuildCompile:
    """编译构建接口测试"""

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_compile_project_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "build-123",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "compile",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12345,
        }
        mock_build_service.compile_project.return_value = mock_task

        response = client.post(
            "/api/build/compile",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "command": "mvn clean compile",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "build-123"
        assert data["action"] == "compile"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_package_project_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "build-456",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "package",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12346,
        }
        mock_build_service.package_project.return_value = mock_task

        response = client.post(
            "/api/build/package",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "package"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_test_project_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "build-789",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "test",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12347,
        }
        mock_build_service.test_project.return_value = mock_task

        response = client.post(
            "/api/build/test",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "test"


class TestBuildRun:
    """运行应用接口测试"""

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_jar_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "run-123",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "run-jar",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12350,
        }
        mock_build_service.run_jar.return_value = mock_task

        response = client.post(
            "/api/build/run/jar",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "jar_path": "target/app.jar",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "run-jar"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_spring_boot_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "run-456",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "run-spring-boot",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12351,
        }
        mock_build_service.run_spring_boot.return_value = mock_task

        response = client.post(
            "/api/build/run/spring-boot",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "server_port": "8080",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "run-spring-boot"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_exec_java_success(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "run-789",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "run-exec",
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": 12352,
        }
        mock_build_service.run_exec_java.return_value = mock_task

        response = client.post(
            "/api/build/run/exec",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "main_class": "com.example.Main",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "run-exec"

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_jar_mode(self, mock_build_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "run-generic",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "run-jar",
            "status": "running",
            "started_at": None,
            "completed_at": None,
            "log": "",
            "exit_code": None,
            "pid": None,
        }
        mock_build_service.run_jar.return_value = mock_task

        response = client.post(
            "/api/build/run",
            json={
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "run_mode": "jar",
                "jar_path": "target/app.jar",
            },
        )
        assert response.status_code == 200


class TestBuildTaskManagement:
    """构建任务管理接口测试"""

    @patch("app.api.routes.build.build_service")
    def test_stop_task_success(self, mock_build_service, client):
        mock_task = MagicMock()
        mock_task.status = "running"
        mock_build_service.get_build_task.return_value = mock_task
        mock_build_service.stop_build_task.return_value = True

        response = client.post("/api/build/stop/task-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    @patch("app.api.routes.build.build_service")
    def test_stop_task_not_found(self, mock_build_service, client):
        mock_build_service.get_build_task.return_value = None
        response = client.post("/api/build/stop/nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.build.build_service")
    def test_stop_task_cannot_stop(self, mock_build_service, client):
        mock_task = MagicMock()
        mock_task.status = "completed"
        mock_build_service.get_build_task.return_value = mock_task
        mock_build_service.stop_build_task.return_value = False

        response = client.post("/api/build/stop/task-123")
        assert response.status_code == 409

    @patch("app.api.routes.build.build_service")
    def test_get_build_status(self, mock_build_service, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "task_id": "task-123",
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "action": "compile",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:05:00",
            "log": "Build successful",
            "exit_code": 0,
            "pid": None,
        }
        mock_build_service.get_build_task.return_value = mock_task

        response = client.get("/api/build/status/task-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["exit_code"] == 0

    @patch("app.api.routes.build.build_service")
    def test_get_build_history(self, mock_build_service, client):
        mock_build_service.get_build_history.return_value = [
            {
                "task_id": "task-1",
                "account_alias": "test-server",
                "project_path": "/opt/project",
                "action": "compile",
                "status": "completed",
                "started_at": None,
                "completed_at": None,
                "log": "",
                "exit_code": 0,
                "pid": None,
            }
        ]
        response = client.get("/api/build/history?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) == 1

    @patch("app.api.routes.build.build_service")
    def test_get_run_log(self, mock_build_service, client):
        mock_task = MagicMock()
        mock_build_service.get_build_task.return_value = mock_task
        mock_build_service.read_run_log.return_value = "Line 1\nLine 2\nLine 3"

        response = client.get("/api/build/log/task-123?max_lines=100")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert "Line 1" in data["log"]
