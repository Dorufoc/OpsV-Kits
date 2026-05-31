from __future__ import annotations

import threading
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

    def test_maven_version_parse_error(self, service, mock_executor):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "Some random output"
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

    def test_run_spring_boot(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_spring_boot("server1", "/project", main_class="com.App")
        assert task.config["run_mode"] == "spring-boot"
        assert task.config["main_class"] == "com.App"

    def test_run_exec_java(self, service, mock_executor):
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(
            success=True, stdout="12345"
        )
        task = service.run_exec_java("server1", "/project", main_class="com.App")
        assert task.config["run_mode"] == "exec"
        assert task.config["main_class"] == "com.App"


class TestBuildJavaHomeSetup:
    def test_build_java_home_setup_jdk8(self, service):
        result = service._build_java_home_setup("8")
        assert "java-1.8.0-openjdk" in result
        assert "JAVA_HOME" in result

    def test_build_java_home_setup_jdk21(self, service):
        result = service._build_java_home_setup("21")
        assert "java-21-openjdk" in result
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
