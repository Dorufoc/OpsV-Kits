from __future__ import annotations

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
        "message": "installing",
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    base.update(overrides)
    return base


class TestCheckEnvironmentSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_check_environment_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_environment.return_value = {
            "account_alias": "srv1",
            "project_path": "/opt",
            "java": {"installed": True, "version": "17"},
            "maven": {"installed": True, "version": "3.9"},
            "all_ready": True,
        }
        resp = client.get("/api/environment/check", params={"account_alias": "srv1", "project_path": "/opt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_ready"] is True

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_check_environment_with_jdk_version(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.check_environment.return_value = {
            "account_alias": "srv1",
            "project_path": "/opt",
            "java": {"installed": True, "version": "11"},
            "maven": {"installed": True, "version": "3.9"},
            "all_ready": True,
        }
        resp = client.get("/api/environment/check", params={"account_alias": "srv1", "project_path": "/opt", "jdk_version": "11"})
        assert resp.status_code == 200


class TestInstallEnvironmentNoProjectPath:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_no_project_path_no_java_version(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict()
        mock_build.install_environment.return_value = mock_task
        resp = client.post("/api/environment/install", json={"account_alias": "test-server"})
        assert resp.status_code == 200
        call_args = mock_build.install_environment.call_args
        assert call_args.kwargs.get("java_version") is None or call_args[1].get("java_version") is None

    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_install_with_explicit_java_version(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict()
        mock_build.install_environment.return_value = mock_task
        resp = client.post("/api/environment/install", json={"account_alias": "test-server", "java_version": "21"})
        assert resp.status_code == 200


class TestGetInstallStatus:
    @patch("app.api.routes.build.build_service")
    def test_get_install_status_success(self, mock_build, client):
        mock_build.get_task_dict.return_value = _mock_install_task_dict(status="completed", progress=1.0)
        resp = client.get("/api/environment/status", params={"task_id": "install-001"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @patch("app.api.routes.build.build_service")
    def test_get_install_status_not_found(self, mock_build, client):
        mock_build.get_task_dict.return_value = None
        resp = client.get("/api/environment/status", params={"task_id": "nonexistent"})
        assert resp.status_code == 404


class TestCompileSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_compile_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="compile", status="running")
        mock_build.compile_project.return_value = mock_task
        resp = client.post("/api/build/compile", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
        })
        assert resp.status_code == 200
        assert resp.json()["action"] == "compile"


class TestPackageSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_package_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="package", status="running")
        mock_build.package_project.return_value = mock_task
        resp = client.post("/api/build/package", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
        })
        assert resp.status_code == 200


class TestTestProjectSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_test_project_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="test", status="running")
        mock_build.test_project.return_value = mock_task
        resp = client.post("/api/build/test", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
        })
        assert resp.status_code == 200


class TestRunJarSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_jar_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run", status="running")
        mock_build.run_jar.return_value = mock_task
        resp = client.post("/api/build/run/jar", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "jar_path": "app.jar",
            "jvm_args": "-Xmx512m",
            "app_args": "--spring.profiles.active=dev",
            "server_port": "8080",
        })
        assert resp.status_code == 200


class TestRunSpringBootSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_spring_boot_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run", status="running")
        mock_build.run_spring_boot.return_value = mock_task
        resp = client.post("/api/build/run/spring-boot", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "main_class": "com.example.App",
            "server_port": "9090",
        })
        assert resp.status_code == 200


class TestRunExecJavaSuccess:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_run_exec_java_success(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run", status="running")
        mock_build.run_exec_java.return_value = mock_task
        resp = client.post("/api/build/run/exec", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "main_class": "com.example.Main",
        })
        assert resp.status_code == 200


class TestGenericRunJarMode:
    @patch("app.api.routes.build.ssh_account_service")
    @patch("app.api.routes.build.build_service")
    def test_generic_run_jar_mode(self, mock_build, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(action="run", status="running")
        mock_build.run_jar.return_value = mock_task
        resp = client.post("/api/build/run", json={
            "account_alias": "test-server",
            "project_path": "/opt/project",
            "run_mode": "jar",
            "jar_path": "app.jar",
            "jvm_args": "-Xmx256m",
            "app_args": "--port=8080",
            "server_port": "8080",
        })
        assert resp.status_code == 200
        mock_build.run_jar.assert_called_once()


class TestStopTaskViaPath:
    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_path_success(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.status = "running"
        mock_build.get_build_task.return_value = mock_task
        mock_build.stop_build_task.return_value = True
        resp = client.post("/api/build/stop/task-123")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_path_not_found(self, mock_build, client):
        mock_build.get_build_task.return_value = None
        resp = client.post("/api/build/stop/nonexistent")
        assert resp.status_code == 404

    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_path_cannot_stop(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.status = "completed"
        mock_build.get_build_task.return_value = mock_task
        mock_build.stop_build_task.return_value = False
        resp = client.post("/api/build/stop/task-123")
        assert resp.status_code == 409

    @patch("app.api.routes.build.build_service")
    def test_stop_task_via_body_cannot_stop(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.status = "completed"
        mock_build.get_build_task.return_value = mock_task
        mock_build.stop_build_task.return_value = False
        resp = client.post("/api/build/stop", json={"task_id": "task-123"})
        assert resp.status_code == 409


class TestBuildStatusSuccess:
    @patch("app.api.routes.build.build_service")
    def test_get_build_status_success(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict(status="completed")
        mock_build.get_build_task.return_value = mock_task
        resp = client.get("/api/build/status/task-001")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"


class TestBuildLogSuccess:
    @patch("app.api.routes.build.build_service")
    def test_get_run_log_success(self, mock_build, client):
        mock_task = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        mock_build.read_run_log.return_value = "line1\nline2\nline3"
        resp = client.get("/api/build/log/task-001", params={"max_lines": 100})
        assert resp.status_code == 200
        assert resp.json()["log"] == "line1\nline2\nline3"


class TestBuildHistoryNoAlias:
    @patch("app.api.routes.build.build_service")
    def test_get_build_history_no_alias(self, mock_build, client):
        mock_build.get_build_history.return_value = [
            _mock_task_dict(task_id="task-1"),
            _mock_task_dict(task_id="task-2"),
        ]
        resp = client.get("/api/build/history")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 2


class TestBuildLogsWs:
    @patch("app.api.routes.build.build_service")
    def test_build_logs_ws_task_not_found(self, mock_build, client):
        mock_build.get_build_task.return_value = None
        with client.websocket_connect("/api/build/ws/logs/task-nonexistent") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不存在" in data["message"]

    @patch("app.api.routes.build.build_service")
    def test_build_logs_ws_ping_pong(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict()
        mock_task.add_callback = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        with client.websocket_connect("/api/build/ws/logs/task-001") as ws:
            info = ws.receive_json()
            assert info["type"] == "task_info"
            ws.send_text(json.dumps({"type": "ping"}))
            pong = ws.receive_json()
            assert pong["type"] == "pong"

    @patch("app.api.routes.build.build_service")
    def test_build_logs_ws_get_log(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict()
        mock_task.add_callback = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        with client.websocket_connect("/api/build/ws/logs/task-001") as ws:
            info = ws.receive_json()
            assert info["type"] == "task_info"
            ws.send_text(json.dumps({"type": "get_log"}))
            log_update = ws.receive_json()
            assert log_update["type"] == "log_update"

    @patch("app.api.routes.build.build_service")
    def test_build_logs_ws_invalid_json(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict()
        mock_task.add_callback = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        with client.websocket_connect("/api/build/ws/logs/task-001") as ws:
            info = ws.receive_json()
            assert info["type"] == "task_info"
            ws.send_text("not json")
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "无效" in err["message"]

    @patch("app.api.routes.build.build_service")
    def test_build_logs_ws_unknown_message_type(self, mock_build, client):
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_task_dict()
        mock_task.add_callback = MagicMock()
        mock_build.get_build_task.return_value = mock_task
        with client.websocket_connect("/api/build/ws/logs/task-001") as ws:
            info = ws.receive_json()
            assert info["type"] == "task_info"
            ws.send_text(json.dumps({"type": "unknown_type"}))
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "未知" in err["message"]


class TestEnvironmentStatusWs:
    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_subscribe_success(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.to_dict.return_value = _mock_install_task_dict()
        mock_task.add_callback = MagicMock()
        mock_build.get_task.return_value = mock_task
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "task_id": "install-001"}))
            data = ws.receive_json()
            assert data["type"] == "subscribed"
            assert data["task_id"] == "install-001"

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_subscribe_missing_task_id(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "subscribe"}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "task_id" in data["message"]

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_subscribe_task_not_found(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_build.get_task.return_value = None
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "task_id": "nonexistent"}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "不存在" in data["message"]

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_unsubscribe(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "unsubscribe", "task_id": "install-001"}))
            data = ws.receive_json()
            assert data["type"] == "unsubscribed"

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_ping_pong(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_json()
            assert data["type"] == "pong"

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_invalid_json(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text("not json")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "无效" in data["message"]

    @patch("app.api.routes.build.build_service")
    @patch("app.api.routes.build.ssh_account_service")
    def test_ws_unknown_message_type(self, mock_ssh, mock_build, client):
        mock_ssh.get_account.return_value = MagicMock()
        with client.websocket_connect("/api/environment/ws/status") as ws:
            ws.send_text(json.dumps({"type": "unknown"}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "未知" in data["message"]
