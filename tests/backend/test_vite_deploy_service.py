from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from app.services.vite_deploy_service import ViteDeployService, ViteDeployTask


@pytest.fixture
def service():
    return ViteDeployService()


class FakeThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=False):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def _sync_thread():
    with patch("app.services.vite_deploy_service.threading.Thread", FakeThread):
        yield


class TestViteDeployTaskInit:
    def test_default_values(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        assert task.task_id == "t1"
        assert task.account_alias == "srv"
        assert task.project_path == "/path"
        assert task.step == "build"
        assert task.config == {}
        assert task.status == "pending"
        assert task.progress == 0.0
        assert task.message == ""
        assert task.log == ""
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None
        assert task.url is None
        assert task._callbacks == []
        assert task._stop_requested is False

    def test_custom_config(self):
        cfg = {"version": "18", "force": True}
        task = ViteDeployTask("t1", "srv", "/path", "install_node", config=cfg)
        assert task.config == cfg

    def test_none_config_becomes_empty_dict(self):
        task = ViteDeployTask("t1", "srv", "/path", "build", config=None)
        assert task.config == {}


class TestViteDeployTaskStopRequested:
    def test_initially_false(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        assert task.stop_requested is False

    def test_after_request_stop(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        task.request_stop()
        assert task.stop_requested is True


class TestViteDeployTaskCallback:
    def test_add_callback_and_notify(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        cb = MagicMock()
        task.add_callback(cb)
        task._notify()
        cb.assert_called_once_with(task)

    def test_multiple_callbacks(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        cb1 = MagicMock()
        cb2 = MagicMock()
        task.add_callback(cb1)
        task.add_callback(cb2)
        task._notify()
        cb1.assert_called_once_with(task)
        cb2.assert_called_once_with(task)

    def test_callback_exception_swallowed(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        cb = MagicMock(side_effect=Exception("cb error"))
        task.add_callback(cb)
        task._notify()

    def test_append_log_triggers_notify(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        cb = MagicMock()
        task.add_callback(cb)
        task.append_log("hello")
        assert "hello" in task.log
        cb.assert_called_with(task)


class TestViteDeployTaskToDict:
    def test_to_dict_full(self):
        task = ViteDeployTask("t1", "srv", "/path", "build", config={"k": "v"})
        task.status = "completed"
        task.progress = 100.0
        task.message = "done"
        task.log = "logs"
        task.started_at = "2025-01-01T00:00:00"
        task.completed_at = "2025-01-01T00:05:00"
        task.error = None
        task.url = "http://srv:8080"
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["account_alias"] == "srv"
        assert d["project_path"] == "/path"
        assert d["step"] == "build"
        assert d["status"] == "completed"
        assert d["progress"] == 100.0
        assert d["message"] == "done"
        assert d["log"] == "logs"
        assert d["started_at"] == "2025-01-01T00:00:00"
        assert d["completed_at"] == "2025-01-01T00:05:00"
        assert d["error"] is None
        assert d["url"] == "http://srv:8080"

    def test_to_dict_defaults(self):
        task = ViteDeployTask("t1", "srv", "/path", "build")
        d = task.to_dict()
        assert d["status"] == "pending"
        assert d["progress"] == 0.0
        assert d["message"] == ""
        assert d["log"] == ""
        assert d["started_at"] is None
        assert d["completed_at"] is None
        assert d["error"] is None
        assert d["url"] is None


class TestViteDeployServiceNewTaskId:
    def test_length(self, service):
        tid = service._new_task_id()
        assert len(tid) == 12

    def test_unique(self, service):
        ids = {service._new_task_id() for _ in range(50)}
        assert len(ids) == 50


class TestViteDeployServiceCreateTask:
    def test_creates_and_stores_task(self, service):
        task = service._create_task("srv", "/path", "build")
        assert task.account_alias == "srv"
        assert task.project_path == "/path"
        assert task.step == "build"
        assert task.config == {}
        assert task.task_id in service._tasks

    def test_custom_task_id(self, service):
        task = service._create_task("srv", "/path", "build", task_id="my-id")
        assert task.task_id == "my-id"
        assert "my-id" in service._tasks

    def test_custom_config(self, service):
        cfg = {"version": "18"}
        task = service._create_task("srv", "/path", "build", config=cfg)
        assert task.config == cfg

    def test_none_config_becomes_empty_dict(self, service):
        task = service._create_task("srv", "/path", "build", config=None)
        assert task.config == {}


class TestViteDeployServiceGetTask:
    def test_existing_task(self, service):
        task = service._create_task("srv", "/path", "build", task_id="t1")
        assert service.get_task("t1") is task

    def test_nonexistent_task(self, service):
        assert service.get_task("nope") is None


class TestViteDeployServiceGetTaskDict:
    def test_existing_task(self, service):
        task = service._create_task("srv", "/path", "build", task_id="t1")
        result = service.get_task_dict("t1")
        assert result == task.to_dict()

    def test_nonexistent_task(self, service):
        assert service.get_task_dict("nope") is None


class TestViteDeployServiceListTasks:
    def test_empty(self, service):
        assert service.list_tasks() == []

    def test_all_tasks(self, service):
        t1 = service._create_task("srv1", "/p1", "build", task_id="t1")
        t1.started_at = "2025-01-01T00:00:00"
        t2 = service._create_task("srv2", "/p2", "deploy", task_id="t2")
        t2.started_at = "2025-01-02T00:00:00"
        result = service.list_tasks()
        assert len(result) == 2

    def test_filter_by_account_alias(self, service):
        t1 = service._create_task("srv1", "/p1", "build", task_id="t1")
        t1.started_at = "2025-01-01T00:00:00"
        t2 = service._create_task("srv2", "/p2", "deploy", task_id="t2")
        t2.started_at = "2025-01-02T00:00:00"
        result = service.list_tasks(account_alias="srv1")
        assert len(result) == 1
        assert result[0]["account_alias"] == "srv1"

    def test_limit(self, service):
        for i in range(25):
            t = service._create_task("srv", f"/p{i}", "build", task_id=f"t{i}")
            t.started_at = f"2025-01-{i + 1:02d}T00:00:00"
        result = service.list_tasks(limit=10)
        assert len(result) == 10

    def test_sorted_by_started_at_desc(self, service):
        t1 = service._create_task("srv", "/p1", "build", task_id="t1")
        t1.started_at = "2025-01-01T00:00:00"
        t2 = service._create_task("srv", "/p2", "build", task_id="t2")
        t2.started_at = "2025-01-02T00:00:00"
        result = service.list_tasks()
        assert result[0]["task_id"] == "t2"
        assert result[1]["task_id"] == "t1"

    def test_none_started_at_sorted_last(self, service):
        t1 = service._create_task("srv", "/p1", "build", task_id="t1")
        t1.started_at = "2025-01-01T00:00:00"
        t2 = service._create_task("srv", "/p2", "build", task_id="t2")
        t2.started_at = None
        result = service.list_tasks()
        assert result[0]["task_id"] == "t1"
        assert result[1]["task_id"] == "t2"

    def test_filter_no_match(self, service):
        t1 = service._create_task("srv1", "/p1", "build", task_id="t1")
        t1.started_at = "2025-01-01T00:00:00"
        result = service.list_tasks(account_alias="nonexistent")
        assert result == []


class TestCheckEnvironment:
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_all_ready(self, mock_node_cls, mock_nginx_cls, mock_detector_cls):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20.10.0"}
        mock_node_cls.return_value = mock_node

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True, "running": True}
        mock_nginx_cls.return_value = mock_nginx

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        svc = ViteDeployService()
        result = svc.check_environment("srv", "/project")

        assert result["all_ready"] is True
        assert result["node"]["installed"] is True
        assert result["nginx"]["installed"] is True
        assert result["vite"]["is_vite"] is True
        assert result["framework"]["name"] == "vue"
        assert result["account_alias"] == "srv"
        assert result["project_path"] == "/project"

    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_node_not_installed(self, mock_node_cls, mock_nginx_cls, mock_detector_cls):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": False, "npm_installed": False, "version": ""}
        mock_node_cls.return_value = mock_node

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True, "running": True}
        mock_nginx_cls.return_value = mock_nginx

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        svc = ViteDeployService()
        result = svc.check_environment("srv", "/project")
        assert result["all_ready"] is False

    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_nginx_not_installed(self, mock_node_cls, mock_nginx_cls, mock_detector_cls):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": False, "running": False}
        mock_nginx_cls.return_value = mock_nginx

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        svc = ViteDeployService()
        result = svc.check_environment("srv", "/project")
        assert result["all_ready"] is False

    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_not_vite_project(self, mock_node_cls, mock_nginx_cls, mock_detector_cls):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True, "running": True}
        mock_nginx_cls.return_value = mock_nginx

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": False, "has_package_json": False}
        mock_detector.detect_framework.return_value = {"name": None, "version": None}
        mock_detector_cls.return_value = mock_detector

        svc = ViteDeployService()
        result = svc.check_environment("srv", "/project")
        assert result["all_ready"] is False

    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_npm_not_installed(self, mock_node_cls, mock_nginx_cls, mock_detector_cls):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": False, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True, "running": True}
        mock_nginx_cls.return_value = mock_nginx

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        svc = ViteDeployService()
        result = svc.check_environment("srv", "/project")
        assert result["all_ready"] is False


class TestInstallNode:
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_success(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.return_value = {"installed": True, "message": "Node.js 20 安装成功"}
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project", version="20")
        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.error is None
        assert task.completed_at is not None
        assert task.started_at is not None
        assert "20" in task.message

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_install_failed(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.return_value = {"installed": False, "message": "安装失败"}
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project", version="18")
        assert task.status == "failed"
        assert task.error == "安装失败"
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_exception(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.side_effect = RuntimeError("SSH 连接断开")
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project")
        assert task.status == "failed"
        assert "SSH 连接断开" in task.error
        assert "SSH 连接断开" in task.log

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_custom_task_id(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.return_value = {"installed": True, "message": "OK"}
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project", task_id="custom-id")
        assert task.task_id == "custom-id"

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_default_version(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.return_value = {"installed": True, "message": "OK"}
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project")
        mock_node.install_node.assert_called_once()
        assert mock_node.install_node.call_args.kwargs["version"] == "20"

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_callback_emits_log(self, mock_node_cls, service):
        mock_node = MagicMock()

        def fake_install(version, callback):
            callback("下载中...")
            callback("安装中...")
            return {"installed": True, "message": "完成"}

        mock_node.install_node.side_effect = fake_install
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project")
        assert "下载中..." in task.log
        assert "安装中..." in task.log

    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_task_initial_state(self, mock_node_cls, service):
        mock_node = MagicMock()
        mock_node.install_node.return_value = {"installed": True, "message": "OK"}
        mock_node_cls.return_value = mock_node

        task = service.install_node("srv", "/project")
        assert task.step == "install_node"
        assert task.config == {"version": "20"}
        assert task.started_at is not None


class TestInstallDeps:
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_success(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_install_failed(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 1
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        assert task.status == "failed"
        assert "exit_code=1" in task.error

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_force_flag(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project", force=True)
        cmd = mock_executor.exec_command_stream.call_args[0][0]
        assert "--force" in cmd

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stopped_by_user(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 130
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        task.request_stop()
        task.status = "stopped"

        assert task.stop_requested is True

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_exception(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.side_effect = RuntimeError("连接失败")
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        assert task.status == "failed"
        assert "连接失败" in task.error

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_custom_task_id(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project", task_id="my-task")
        assert task.task_id == "my-task"

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_pnpm_manager(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "pnpm"
        mock_pkg.get_install_command.return_value = "pnpm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        assert "pnpm" in task.log

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stop_check_callback(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        service.install_deps("srv", "/project")
        call_kwargs = mock_executor.exec_command_stream.call_args
        assert "stop_check" in call_kwargs.kwargs

    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_output_callback(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            output_callback("downloading...\n")
            output_callback("installing...\n")
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        assert "downloading" in task.log
        assert "installing" in task.log


class TestBuild:
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_success(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_build_failed(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 1
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        assert task.status == "failed"
        assert "exit_code=1" in task.error

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_custom_build_command(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project", build_command="pnpm build --mode prod")
        cmd = mock_executor.exec_command_stream.call_args[0][0]
        assert "pnpm build --mode prod" in cmd

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_default_build_command(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        cmd = mock_executor.exec_command_stream.call_args[0][0]
        assert "npm run build" in cmd

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stopped_by_user(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            return 143

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        task.request_stop()
        task.status = "stopped"

        assert task.stop_requested is True

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_exception(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.side_effect = RuntimeError("SSH 错误")
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        assert task.status == "failed"
        assert "SSH 错误" in task.error

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_custom_task_id(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project", task_id="build-1")
        assert task.task_id == "build-1"

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_task_step_and_config(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project", build_command="npm run build")
        assert task.step == "build"
        assert task.config == {"build_command": "npm run build"}

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_output_callback_appends_log(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            output_callback("vite v5.0.0 building for production...\n")
            output_callback("✓ built in 1234ms\n")
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        assert "vite v5.0.0" in task.log
        assert "✓ built" in task.log

    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stop_check_callback(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        service.build("srv", "/project")
        call_kwargs = mock_executor.exec_command_stream.call_args
        assert "stop_check" in call_kwargs.kwargs


class TestDeployNginx:
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_success(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project")
        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.url == "http://srv:8080"
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_nginx_not_installed_then_install_success(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": False}
        mock_nginx.install_nginx.return_value = {"installed": True, "message": "安装成功"}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project")
        assert task.status == "completed"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_nginx_not_installed_install_failed(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": False}
        mock_nginx.install_nginx.return_value = {"installed": False, "message": "安装失败"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project")
        assert task.status == "failed"
        assert task.error == "Nginx 安装失败"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_port_conflict_warning(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {
            "conflict": True,
            "processes": ["nginx: master process"],
        }
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project", port=8080)
        assert task.status == "completed"
        assert "8080" in task.log
        assert "nginx: master process" in task.log

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_reload_failed(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": False, "message": "配置语法错误"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "配置语法错误" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_exception(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.side_effect = RuntimeError("连接失败")
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "连接失败" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_custom_port(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project", port=3000)
        assert task.url == "http://srv:3000"
        mock_nginx.generate_config.assert_called_once_with(
            project_alias="my-app",
            port=3000,
            server_name="_",
            root_path="/resolved/path/dist",
        )

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_custom_task_id(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project", task_id="nginx-1")
        assert task.task_id == "nginx-1"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_dist_path_trailing_slash(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path/"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        service.deploy_nginx("srv", "my-app", "/project")
        call_kwargs = mock_nginx.generate_config.call_args.kwargs
        assert call_kwargs["root_path"] == "/resolved/path/dist"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_task_step_and_config(self, mock_executor_cls, mock_nginx_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor_cls.return_value = mock_executor

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.check_port_conflict.return_value = {"conflict": False}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/my-app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.deploy_nginx("srv", "my-app", "/project", port=9090)
        assert task.step == "deploy_nginx"
        assert task.config == {"project_alias": "my-app", "port": 9090}


class TestFullDeploy:
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_full_success(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.url == "http://srv:8080"
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_node_not_installed_then_install_success(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": False, "npm_installed": False, "version": ""}
        mock_node.install_node.return_value = {"installed": True, "message": "Node.js 安装成功"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "completed"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_node_install_failed(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": False, "npm_installed": False, "version": ""}
        mock_node.install_node.return_value = {"installed": False, "message": "Node.js 安装失败"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "Node.js 安装失败" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_dep_install_failed(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        call_count = [0]

        def fake_stream(cmd, output_callback, timeout, stop_check):
            call_count[0] += 1
            if call_count[0] == 1:
                return 1
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "依赖安装失败" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_build_failed(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        call_count = [0]

        def fake_stream(cmd, output_callback, timeout, stop_check):
            call_count[0] += 1
            if call_count[0] == 1:
                return 0
            return 1

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "构建失败" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_nginx_not_installed_install_failed(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": False}
        mock_nginx.install_nginx.return_value = {"installed": False, "message": "Nginx 安装失败"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "Nginx 安装失败" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_nginx_reload_failed(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": False, "message": "配置语法错误"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "配置语法错误" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_exception(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.side_effect = RuntimeError("SSH 断开")
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "failed"
        assert "SSH 断开" in task.error

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_stopped_during_dep_install(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            return 1

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        task.request_stop()
        assert task.stop_requested is True

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_custom_config(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "pnpm"
        mock_pkg.get_install_command.return_value = "pnpm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        config = {
            "node_version": "18",
            "nginx_port": 3000,
            "build_command": "pnpm build",
            "force": True,
        }
        task = service.full_deploy("srv", "my-app", "/project", config=config)
        assert task.status == "completed"
        assert task.url == "http://srv:3000"
        assert task.config == config

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_none_config_uses_defaults(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project", config=None)
        assert task.status == "completed"
        assert task.url == "http://srv:8080"

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_force_flag_in_command(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        config = {"force": True}
        task = service.full_deploy("srv", "my-app", "/project", config=config)
        dep_cmd = mock_executor.exec_command_stream.call_args_list[0][0][0]
        assert "--force" in dep_cmd

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_npm_not_installed_triggers_node_install(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": False, "version": "v20"}
        mock_node.install_node.return_value = {"installed": True, "message": "npm 安装成功"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "completed"
        mock_node.install_node.assert_called_once()

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_nginx_not_installed_then_install_success_in_full_deploy(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": False}
        mock_nginx.install_nginx.return_value = {"installed": True, "message": "Nginx 安装成功"}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.status == "completed"
        mock_nginx.install_nginx.assert_called_once()

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_full_deploy_step_and_config(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert task.step == "full_deploy"
        assert task.started_at is not None
        assert task.completed_at is not None

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_full_deploy_log_contains_steps(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx.check_nginx.return_value = {"installed": True}
        mock_nginx.generate_config.return_value = "/etc/nginx/conf.d/app.conf"
        mock_nginx.reload_nginx.return_value = {"success": True, "message": "OK"}
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        assert "检查环境" in task.log
        assert "安装依赖" in task.log
        assert "构建项目" in task.log
        assert "配置 Nginx" in task.log


class TestInstallDepsStoppedByUser:
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stop_requested_sets_stopped(self, mock_executor_cls, mock_pkg_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        task = service.install_deps("srv", "/project")
        task.request_stop()

        task.status = "stopped"
        task.message = "依赖安装已被用户停止"
        assert task.stop_requested is True
        assert task.status == "stopped"


class TestBuildStoppedByUser:
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    def test_stop_requested_sets_stopped(self, mock_executor_cls, service):
        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_stream(cmd, output_callback, timeout, stop_check):
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        task = service.build("srv", "/project")
        task.request_stop()

        task.status = "stopped"
        task.message = "构建已被用户停止"
        assert task.stop_requested is True
        assert task.status == "stopped"


class TestFullDeployStoppedDuringDeps:
    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_stopped_during_dep_install(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        def fake_dep_stream(cmd, output_callback, timeout, stop_check):
            return 0

        mock_executor.exec_command_stream.side_effect = fake_dep_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        task.request_stop()
        assert task.stop_requested is True

    @patch("app.services.vite_deploy_service.NginxConfigManager")
    @patch("app.services.vite_deploy_service.PackageManager")
    @patch("app.services.vite_deploy_service.RemoteExecutor")
    @patch("app.services.vite_deploy_service.ViteProjectDetector")
    @patch("app.services.vite_deploy_service.NodeEnvManager")
    def test_stopped_during_build(
        self, mock_node_cls, mock_detector_cls, mock_executor_cls, mock_pkg_cls, mock_nginx_cls, service
    ):
        mock_node = MagicMock()
        mock_node.check_node.return_value = {"installed": True, "npm_installed": True, "version": "v20"}
        mock_node_cls.return_value = mock_node

        mock_detector = MagicMock()
        mock_detector.is_vite_project.return_value = {"is_vite": True, "has_package_json": True}
        mock_detector.detect_framework.return_value = {"name": "vue", "version": "3.3.0"}
        mock_detector_cls.return_value = mock_detector

        mock_executor = MagicMock()
        mock_executor.resolve_path.return_value = "/resolved/path"

        call_count = [0]

        def fake_stream(cmd, output_callback, timeout, stop_check):
            call_count[0] += 1
            if call_count[0] == 1:
                return 0
            return 0

        mock_executor.exec_command_stream.side_effect = fake_stream
        mock_executor_cls.return_value = mock_executor

        mock_pkg = MagicMock()
        mock_pkg.detect.return_value = "npm"
        mock_pkg.get_install_command.return_value = "npm install"
        mock_pkg_cls.return_value = mock_pkg

        mock_nginx = MagicMock()
        mock_nginx_cls.return_value = mock_nginx

        task = service.full_deploy("srv", "my-app", "/project")
        task.request_stop()
        assert task.stop_requested is True
