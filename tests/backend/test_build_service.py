from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.build_service import BuildService, InstallTaskInfo


@pytest.fixture
def service():
    return BuildService()


@pytest.fixture
def mock_executor():
    with patch("app.services.build_service.RemoteExecutor") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


class TestInstallTaskInfo:
    def test_init_defaults(self):
        task = InstallTaskInfo("t1", "server1", ["java-21", "maven"])
        assert task.task_id == "t1"
        assert task.account_alias == "server1"
        assert task.components == ["java-21", "maven"]
        assert task.status == "pending"
        assert task.progress == 0.0
        assert task.message == ""
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None

    def test_add_callback(self):
        task = InstallTaskInfo("t1", "server1", ["java"])
        cb = MagicMock()
        task.add_callback(cb)
        task._notify()
        cb.assert_called_once_with(task)

    def test_callback_exception_swallowed(self):
        task = InstallTaskInfo("t1", "server1", ["java"])
        cb = MagicMock(side_effect=Exception("cb error"))
        task.add_callback(cb)
        task._notify()

    def test_multiple_callbacks(self):
        task = InstallTaskInfo("t1", "server1", ["java"])
        cb1 = MagicMock()
        cb2 = MagicMock()
        task.add_callback(cb1)
        task.add_callback(cb2)
        task._notify()
        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_to_dict(self):
        task = InstallTaskInfo("t1", "server1", ["java"])
        task.status = "running"
        task.progress = 50.0
        task.message = "installing"
        d = task.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "running"
        assert d["progress"] == 50.0
        assert d["message"] == "installing"


class TestCheckJava:
    def test_java_installed_compatible(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "openjdk version \"21.0.1\" 2023-10-17"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_java("server1", "/project")
        assert result["installed"] is True
        assert result["version"] == "21"
        assert result["compatible"] is True

    def test_java_installed_incompatible(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "openjdk version \"11.0.1\""
        mock_executor.exec_command.return_value = mock_result
        result = service.check_java("server1", "/project", jdk_version="21")
        assert result["installed"] is True
        assert result["version"] == "11"
        assert result["compatible"] is False

    def test_java_not_installed(self, service, mock_executor):
        mock_result_fail = MagicMock()
        mock_result_fail.success = False
        mock_result_fail.stdout = ""
        mock_result_ok = MagicMock()
        mock_result_ok.success = True
        mock_result_ok.stdout = ""
        mock_executor.exec_command.side_effect = [mock_result_fail, mock_result_ok]
        result = service.check_java("server1", "/project")
        assert result["installed"] is False

    def test_java_fallback_with_version(self, service, mock_executor):
        mock_fail = MagicMock()
        mock_fail.success = False
        mock_fail.stdout = ""
        mock_ok = MagicMock()
        mock_ok.success = True
        mock_ok.stdout = "openjdk version \"17.0.1\""
        mock_executor.exec_command.side_effect = [mock_fail, mock_ok]
        result = service.check_java("server1", "/project")
        assert result["installed"] is True
        assert result["version"] == "17"

    def test_java_with_jdk_version(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "openjdk version \"21.0.1\""
        mock_executor.exec_command.return_value = mock_result
        result = service.check_java("server1", "/project", jdk_version="17")
        assert result["required"] == "17"
        assert result["compatible"] is True

    def test_java_default_required_21(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_executor.exec_command.side_effect = [mock_result, mock_result]
        result = service.check_java("server1", "/project")
        assert result["required"] == "21"

    def test_java_version_parse_error(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "openjdk version \"abc\""
        mock_executor.exec_command.return_value = mock_result
        result = service.check_java("server1", "/project")
        assert result["installed"] is False

    def test_java_compatible_value_error(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "openjdk version \"21.0.1\""
        mock_executor.exec_command.return_value = mock_result
        with patch("app.services.build_service._JAVA_VERSION_PATTERN") as mock_pattern:
            mock_match = MagicMock()
            mock_match.group.side_effect = lambda i: "21" if i == 2 else "1."
            mock_pattern.search.return_value = mock_match
            result = service.check_java("server1", "/project", jdk_version="abc")
            assert result["compatible"] is False


class TestCheckMaven:
    def test_maven_installed_compatible(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Apache Maven 3.9.5\nMaven home: /usr/share/maven"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is True

    def test_maven_installed_incompatible(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Apache Maven 3.5.0"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is False

    def test_maven_not_installed(self, service, mock_executor):
        mock_result_fail = MagicMock()
        mock_result_fail.success = False
        mock_result_fail.stdout = ""
        mock_result_ok = MagicMock()
        mock_result_ok.success = False
        mock_result_ok.stdout = ""
        mock_executor.exec_command.side_effect = [mock_result_fail, mock_result_ok]
        result = service.check_maven("server1", "/project")
        assert result["installed"] is False

    def test_maven_fallback_success(self, service, mock_executor):
        mock_fail = MagicMock()
        mock_fail.success = False
        mock_fail.stdout = ""
        mock_ok = MagicMock()
        mock_ok.success = True
        mock_ok.stdout = "Apache Maven 3.9.5"
        mock_executor.exec_command.side_effect = [mock_fail, mock_ok]
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True

    def test_maven_version_parse_error(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Some random output"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is False

    def test_maven_4x_compatible(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Apache Maven 4.0.0"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is True

    def test_maven_version_value_error(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Apache Maven abc.def"
        mock_executor.exec_command.return_value = mock_result
        result = service.check_maven("server1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is False


class TestInstallJava:
    def test_install_java_success(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "Installed"
        mock_verify = MagicMock()
        mock_verify.success = True
        mock_verify.stdout = "openjdk version \"21.0.1\""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_java("server1", version="21")
        assert result["installed"] is True
        assert result["component"] == "java"

    def test_install_java_version_8(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = True
        mock_verify.stdout = "openjdk version \"1.8.0_382\""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_java("server1", version="8")
        assert result["installed"] is True

    def test_install_java_with_dnf_mirror(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_java("server1", dnf_mirror="http://mirror.example.com")
        assert "dnf_mirror" not in result

    def test_install_java_with_proxy(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_java("server1", proxy="http://proxy:8080")
        assert "component" in result

    def test_install_java_with_callback(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        cb = MagicMock()
        service.install_java("server1", status_callback=cb)
        cb.assert_called()

    def test_install_java_verify_fails(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_java("server1", version="21")
        assert result["installed"] is False
        assert result["version_info"] == ""


class TestInstallMaven:
    def test_install_maven_success(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = True
        mock_verify.stdout = "Apache Maven 3.9.5"
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_maven("server1")
        assert result["installed"] is True
        assert result["component"] == "maven"

    def test_install_maven_with_callback(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        cb = MagicMock()
        service.install_maven("server1", status_callback=cb)
        cb.assert_called()

    def test_install_maven_with_dnf_mirror(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_maven("server1", dnf_mirror="http://mirror.example.com")
        assert result["component"] == "maven"

    def test_install_maven_with_proxy(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_maven("server1", proxy="http://proxy:8080")
        assert result["component"] == "maven"

    def test_install_maven_verify_fails(self, service, mock_executor):
        mock_install = MagicMock()
        mock_install.success = True
        mock_install.stdout = "OK"
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_install, mock_verify]
        mock_executor.exec_with_pty = MagicMock(return_value=mock_install)
        result = service.install_maven("server1")
        assert result["installed"] is False


class TestInstallEnvironment:
    def test_install_environment_creates_task(self, service, mock_executor):
        with patch.object(service, "install_java") as mock_java, \
             patch.object(service, "install_maven") as mock_maven:
            mock_java.return_value = {"component": "java", "installed": True, "version_info": "21", "version": "21", "message": "OK"}
            mock_maven.return_value = {"component": "maven", "installed": True, "version_info": "3.9.5", "message": "OK"}
            task = service.install_environment("server1", java_version="21")
            assert task.account_alias == "server1"
            assert "java-21" in task.components
            assert "maven" in task.components

    def test_install_environment_custom_task_id(self, service, mock_executor):
        with patch.object(service, "install_java") as mock_java, \
             patch.object(service, "install_maven") as mock_maven:
            mock_java.return_value = {"component": "java", "installed": True, "version_info": "21", "version": "21", "message": "OK"}
            mock_maven.return_value = {"component": "maven", "installed": True, "version_info": "3.9.5", "message": "OK"}
            task = service.install_environment("server1", task_id="custom-id")
            assert task.task_id == "custom-id"

    def test_install_environment_no_java(self, service, mock_executor):
        with patch.object(service, "install_maven") as mock_maven:
            mock_maven.return_value = {"component": "maven", "installed": True, "version_info": "3.9.5", "message": "OK"}
            task = service.install_environment("server1")
            assert "maven" in task.components
            assert len([c for c in task.components if c.startswith("java")]) == 0

    def test_install_environment_partial_failure(self, service, mock_executor):
        with patch.object(service, "install_java") as mock_java, \
             patch.object(service, "install_maven") as mock_maven:
            mock_java.return_value = {"component": "java", "installed": False, "version_info": "", "version": "21", "message": "Java 21 安装失败"}
            mock_maven.return_value = {"component": "maven", "installed": True, "version_info": "3.9.5", "message": "OK"}
            task = service.install_environment("server1", java_version="21")
            time.sleep(0.5)
            assert task.status in ("completed", "failed", "running")


class TestCheckEnvironment:
    def test_check_environment_all_ready(self, service, mock_executor):
        with patch.object(service, "check_java") as mock_java, \
             patch.object(service, "check_maven") as mock_maven:
            mock_java.return_value = {"installed": True, "version": "21", "required": "21", "compatible": True}
            mock_maven.return_value = {"installed": True, "version": "3.9.5", "compatible": True}
            result = service.check_environment("server1", "/project")
            assert result["all_ready"] is True

    def test_check_environment_not_ready(self, service, mock_executor):
        with patch.object(service, "check_java") as mock_java, \
             patch.object(service, "check_maven") as mock_maven:
            mock_java.return_value = {"installed": True, "version": "11", "required": "21", "compatible": False}
            mock_maven.return_value = {"installed": True, "version": "3.9.5", "compatible": True}
            result = service.check_environment("server1", "/project")
            assert result["all_ready"] is False


class TestTaskManagement:
    def test_get_task(self, service):
        task = InstallTaskInfo("t1", "server1", ["java"])
        service._tasks["t1"] = task
        assert service.get_task("t1") is task
        assert service.get_task("nonexistent") is None

    def test_get_task_dict(self, service):
        task = InstallTaskInfo("t1", "server1", ["java"])
        service._tasks["t1"] = task
        result = service.get_task_dict("t1")
        assert result["task_id"] == "t1"
        assert service.get_task_dict("nonexistent") is None

    def test_list_tasks(self, service):
        task1 = InstallTaskInfo("t1", "server1", ["java"])
        task1.started_at = "2025-01-01T00:00:00"
        task2 = InstallTaskInfo("t2", "server2", ["maven"])
        task2.started_at = "2025-01-02T00:00:00"
        service._tasks["t1"] = task1
        service._tasks["t2"] = task2
        result = service.list_tasks()
        assert len(result) == 2

    def test_list_tasks_filter_by_alias(self, service):
        task1 = InstallTaskInfo("t1", "server1", ["java"])
        task1.started_at = "2025-01-01T00:00:00"
        task2 = InstallTaskInfo("t2", "server2", ["maven"])
        task2.started_at = "2025-01-02T00:00:00"
        service._tasks["t1"] = task1
        service._tasks["t2"] = task2
        result = service.list_tasks(account_alias="server1")
        assert len(result) == 1
        assert result[0]["account_alias"] == "server1"

    def test_list_tasks_limit(self, service):
        for i in range(25):
            task = InstallTaskInfo(f"t{i}", "server1", ["java"])
            task.started_at = f"2025-01-{i+1:02d}T00:00:00"
            service._tasks[f"t{i}"] = task
        result = service.list_tasks(limit=10)
        assert len(result) == 10


class TestBuildTaskManagement:
    def test_create_build_task(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="Apache Maven 3.9.5"
        )
        task = service.create_build_task(
            account_alias="server1",
            project_path="/project",
            action="compile",
        )
        assert task.account_alias == "server1"
        assert task.action == "compile"
        assert task.task_id in service._build_tasks

    def test_get_build_task(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.create_build_task("server1", "/project", "compile")
        found = service.get_build_task(task.task_id)
        assert found is task
        assert service.get_build_task("nonexistent") is None

    def test_stop_build_task_not_found(self, service):
        assert service.stop_build_task("nonexistent") is False

    def test_stop_build_task_already_completed(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.create_build_task("server1", "/project", "compile")
        task.status = "completed"
        assert service.stop_build_task(task.task_id) is False

    def test_stop_build_task_with_pid(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "12345"
        mock_executor.exec_command.return_value = mock_result
        task = service.run_jar("server1", "/project", "/app.jar")
        time.sleep(0.3)
        task.pid = 12345
        task.status = "running"
        pstree_result = MagicMock()
        pstree_result.success = True
        pstree_result.stdout = "12346\n12347"
        mock_executor.exec_command.return_value = pstree_result
        result = service.stop_build_task(task.task_id)
        assert result is True

    def test_get_build_history(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        service.create_build_task("server1", "/project", "compile")
        history = service.get_build_history()
        assert len(history) >= 1

    def test_get_build_history_filter_by_alias(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        service.create_build_task("server1", "/project", "compile")
        history = service.get_build_history(account_alias="server2")
        assert len(history) == 0

    def test_get_build_history_limit(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        for i in range(5):
            service.create_build_task("server1", f"/project{i}", "compile")
        history = service.get_build_history(limit=2)
        assert len(history) <= 2


class TestCompileProject:
    def test_compile_project(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.compile_project("server1", "/project")
        assert task.action == "compile"
        assert "compile" in task.config.get("command", "")

    def test_compile_project_with_jdk(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.compile_project("server1", "/project", jdk_version="17")
        assert task.config.get("jdk_version") == "17"

    def test_compile_project_with_local_path(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.compile_project("server1", "/project", local_path="/local/path")
        assert task.config.get("local_path") == "/local/path"


class TestPackageProject:
    def test_package_project(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.package_project("server1", "/project")
        assert task.action == "package"
        assert "package" in task.config.get("command", "")


class TestTestProject:
    def test_test_project(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.test_project("server1", "/project")
        assert task.action == "test"

    def test_test_project_with_jdk(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command_stream.return_value = 0
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="")
        task = service.test_project("server1", "/project", jdk_version="17")
        assert task.config.get("jdk_version") == "17"


class TestRunMethods:
    def test_run_jar(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_jar("server1", "/project", "/app.jar")
        assert task.action == "run"
        assert task.config["run_mode"] == "jar"
        assert task.config["jar_path"] == "/app.jar"

    def test_run_jar_with_options(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_jar(
            "server1", "/project", "/app.jar",
            jvm_args="-Xmx512m", app_args="--server.port=8081",
            jdk_version="17", server_port="8081"
        )
        assert task.config["jvm_args"] == "-Xmx512m"
        assert task.config["app_args"] == "--server.port=8081"
        assert task.config["jdk_version"] == "17"
        assert task.config["server_port"] == "8081"

    def test_run_spring_boot(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_spring_boot("server1", "/project", main_class="com.App")
        assert task.config["run_mode"] == "spring-boot"
        assert task.config["main_class"] == "com.App"

    def test_run_spring_boot_with_options(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_spring_boot(
            "server1", "/project",
            jdk_version="17", server_port="9090"
        )
        assert task.config["jdk_version"] == "17"
        assert task.config["server_port"] == "9090"

    def test_run_exec_java(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_exec_java("server1", "/project", main_class="com.App")
        assert task.config["run_mode"] == "exec"
        assert task.config["main_class"] == "com.App"

    def test_run_exec_java_with_jdk(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_exec_java(
            "server1", "/project", main_class="com.App",
            jdk_version="17"
        )
        assert task.config["jdk_version"] == "17"


class TestBuildJavaHomeSetup:
    def test_build_java_home_setup_jdk8(self, service):
        result = service._build_java_home_setup("8")
        assert "java-1.8.0-openjdk" in result
        assert "JAVA_HOME" in result

    def test_build_java_home_setup_jdk21(self, service):
        result = service._build_java_home_setup("21")
        assert "java-21-openjdk" in result
        assert "JAVA_HOME" in result

    def test_build_java_home_setup_jdk17(self, service):
        result = service._build_java_home_setup("17")
        assert "java-17-openjdk" in result
        assert "JAVA_HOME" in result


class TestTrySudo:
    def test_try_sudo_success(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "OK"
        mock_executor.exec_command.return_value = mock_result
        messages = []
        service._try_sudo(mock_executor, "dnf install -y java", messages.append)
        assert len(messages) > 0

    def test_try_sudo_long_output(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "x" * 300
        mock_executor.exec_command.return_value = mock_result
        messages = []
        service._try_sudo(mock_executor, "dnf install -y java", messages.append)
        assert len(messages) > 0

    def test_try_sudo_permission_denied(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Permission denied"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        mock_sudo_result = MagicMock()
        mock_sudo_result.success = True
        mock_sudo_result.stdout = "OK"
        mock_executor.exec_with_pty.return_value = mock_sudo_result
        messages = []
        service._try_sudo(mock_executor, "dnf install -y java", messages.append)
        mock_executor.exec_with_pty.assert_called_once()

    def test_try_sudo_permission_denied_sudo_fails(self, service, mock_executor):
        from app.core.remote_executor import RemoteExecutorError
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Permission denied"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        mock_sudo_result = MagicMock()
        mock_sudo_result.success = False
        mock_sudo_result.stderr = "sudo failed"
        mock_executor.exec_with_pty.return_value = mock_sudo_result
        with pytest.raises(RemoteExecutorError):
            service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_general_failure(self, service, mock_executor):
        from app.core.remote_executor import RemoteExecutorError
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Package not found"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        with pytest.raises(RemoteExecutorError):
            service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_bytes_stderr(self, service, mock_executor):
        from app.core.remote_executor import RemoteExecutorError
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = b"Permission denied"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        mock_sudo_result = MagicMock()
        mock_sudo_result.success = True
        mock_sudo_result.stdout = "OK"
        mock_executor.exec_with_pty.return_value = mock_sudo_result
        service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_not_a_root(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Not a root user"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        mock_sudo_result = MagicMock()
        mock_sudo_result.success = True
        mock_sudo_result.stdout = "OK"
        mock_executor.exec_with_pty.return_value = mock_sudo_result
        service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)
        mock_executor.exec_with_pty.assert_called_once()

    def test_try_sudo_sudo_long_output(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "Permission denied"
        mock_result.exit_code = 1
        mock_executor.exec_command.return_value = mock_result
        mock_sudo_result = MagicMock()
        mock_sudo_result.success = True
        mock_sudo_result.stdout = "x" * 300
        mock_executor.exec_with_pty.return_value = mock_sudo_result
        messages = []
        service._try_sudo(mock_executor, "dnf install -y java", messages.append)
        assert len(messages) > 0


class TestParsePomJavaVersion:
    def test_parse_pom_java_version(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '<java.version>17</java.version>'
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == "17"

    def test_parse_pom_compiler_source(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '<maven.compiler.source>11</maven.compiler.source>'
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == "11"

    def test_parse_pom_compiler_target(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '<maven.compiler.target>1.8</maven.compiler.target>'
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == "8"

    def test_parse_pom_no_version(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '<project></project>'
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == ""

    def test_parse_pom_read_failure(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == ""

    def test_parse_pom_empty_stdout(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = ""
        mock_executor.exec_command.return_value = mock_result
        ver = service._parse_pom_java_version(mock_executor, "/project")
        assert ver == ""


class TestDetectMavenRoot:
    def test_success(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "/project"
        mock_executor.exec_command.return_value = mock_result
        result = service._detect_maven_root(mock_executor, "/project")
        assert result == "/project"

    def test_failure(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_executor.exec_command.return_value = mock_result
        result = service._detect_maven_root(mock_executor, "/project")
        assert result is None

    def test_empty_stdout(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = ""
        mock_executor.exec_command.return_value = mock_result
        result = service._detect_maven_root(mock_executor, "/project")
        assert result is None


class TestEnsureJava:
    def test_already_installed_compatible(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_check = MagicMock()
        mock_check.success = True
        mock_check.stdout = "openjdk version \"21.0.1\""
        mock_executor.exec_command.return_value = mock_check
        result = service._ensure_java(mock_executor, task)
        assert result is True

    def test_not_installed_install_fails(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {"jdk_version": "21"})
        mock_check = MagicMock()
        mock_check.success = False
        mock_check.stdout = ""
        mock_executor.exec_command.return_value = mock_check
        mock_executor.exec_command_stream.return_value = 1
        result = service._ensure_java(mock_executor, task)
        assert result is False

    def test_installed_but_lower_version(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {"jdk_version": "21"})
        mock_check = MagicMock()
        mock_check.success = True
        mock_check.stdout = "openjdk version \"11.0.1\""
        mock_executor.exec_command.side_effect = [
            mock_check,
            MagicMock(success=True, stdout="openjdk version \"11.0.1\""),
            MagicMock(success=False, stdout=""),
            MagicMock(success=True, stdout="openjdk version \"11.0.1\""),
        ]
        mock_executor.exec_command_stream.return_value = 1
        result = service._ensure_java(mock_executor, task)
        assert result is False

    def test_no_jdk_version_defaults_21(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_check = MagicMock()
        mock_check.success = True
        mock_check.stdout = "openjdk version \"21.0.1\""
        mock_executor.exec_command.return_value = mock_check
        result = service._ensure_java(mock_executor, task)
        assert result is True


class TestEnsureMaven:
    def test_already_installed(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_check = MagicMock()
        mock_check.success = True
        mock_check.stdout = "Apache Maven 3.9.5"
        mock_executor.exec_command.return_value = mock_check
        result = service._ensure_maven(mock_executor, task)
        assert result is True

    def test_not_installed_install_success(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_fail = MagicMock()
        mock_fail.success = False
        mock_fail.stdout = ""
        mock_verify = MagicMock()
        mock_verify.success = True
        mock_verify.stdout = "Apache Maven 3.9.5"
        mock_executor.exec_command.side_effect = [mock_fail, mock_verify]
        mock_executor.exec_command_stream.return_value = 0
        result = service._ensure_maven(mock_executor, task)
        assert result is True

    def test_not_installed_install_fails(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_fail = MagicMock()
        mock_fail.success = False
        mock_fail.stdout = ""
        mock_verify = MagicMock()
        mock_verify.success = False
        mock_verify.stdout = ""
        mock_executor.exec_command.side_effect = [mock_fail, mock_verify]
        mock_executor.exec_command_stream.return_value = 1
        result = service._ensure_maven(mock_executor, task)
        assert result is False


class TestRunBuildTask:
    def test_unknown_action(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        task.action = "unknown_action"
        service._run_build_task(task)
        assert task.status == "failed"

    def test_exception_during_execution(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        mock_executor.resolve_path.side_effect = Exception("connection error")
        service._run_build_task(task)
        assert task.status == "failed"


class TestKillProcessTree:
    def test_success(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        pstree_result = MagicMock()
        pstree_result.success = True
        pstree_result.stdout = "12346\n12347"
        ok_result = MagicMock()
        ok_result.success = True
        ok_result.stdout = "stopped"
        mock_executor.exec_command.side_effect = [
            pstree_result,
            ok_result, ok_result, ok_result,
            ok_result, ok_result, ok_result,
        ]
        with patch("app.services.build_service.time"):
            service._kill_process_tree(mock_executor, 12345, task)

    def test_pstree_fails_fallback(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        fallback_result = MagicMock()
        mock_executor.exec_command.side_effect = [Exception("pstree not available"), fallback_result]
        service._kill_process_tree(mock_executor, 12345, task)

    def test_child_pid_value_error(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        pstree_result = MagicMock()
        pstree_result.success = True
        pstree_result.stdout = "abc\ndef"
        ok_result = MagicMock()
        ok_result.success = True
        ok_result.stdout = "stopped"
        mock_executor.exec_command.side_effect = [pstree_result, ok_result, ok_result]
        with patch("app.services.build_service.time"):
            service._kill_process_tree(mock_executor, 12345, task)

    def test_process_still_running_force_kill(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "compile", {})
        pstree_result = MagicMock()
        pstree_result.success = True
        pstree_result.stdout = ""
        kill_result = MagicMock()
        running_check = MagicMock()
        running_check.success = True
        running_check.stdout = "running"
        force_kill_result = MagicMock()
        mock_executor.exec_command.side_effect = [
            pstree_result, kill_result,
            running_check, force_kill_result,
        ]
        with patch("app.services.build_service.time"):
            service._kill_process_tree(mock_executor, 12345, task)


class TestReadRunLog:
    def test_task_not_found(self, service):
        result = service.read_run_log("nonexistent")
        assert result == ""

    def test_read_success(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "run", {})
        service._build_tasks[task.task_id] = task
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Application started on port 8080"
        mock_executor.exec_command.return_value = mock_result
        result = service.read_run_log(task.task_id)
        assert "Application started" in result

    def test_read_failure(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "run", {})
        service._build_tasks[task.task_id] = task
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stderr = "File not found"
        mock_executor.exec_command.return_value = mock_result
        result = service.read_run_log(task.task_id)
        assert "File not found" in result

    def test_read_with_local_path(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "run", {"local_path": "/local/myapp"})
        service._build_tasks[task.task_id] = task
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "log content"
        mock_executor.exec_command.return_value = mock_result
        result = service.read_run_log(task.task_id)
        assert result == "log content"


class TestExecuteRunTask:
    def test_unknown_run_mode(self, service, mock_executor):
        from app.models.build_task import new_build_task
        task = new_build_task("server1", "/project", "run", {"run_mode": "unknown"})
        service._execute_run_task(task)
        assert task.status == "failed"
