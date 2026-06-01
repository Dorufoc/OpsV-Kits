from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.build_service import BuildService
from app.models.build_task import new_build_task


@pytest.fixture
def service():
    return BuildService()


@pytest.fixture
def mock_executor():
    with patch("app.services.build_service.RemoteExecutor") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


class TestExecuteMavenTask:
    def test_maven_not_found(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "failed"

    def test_java_not_available(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=False, stdout=""),
            MagicMock(success=False, stdout=""),
        ]
        mock_executor.exec_command_stream.return_value = 1
        service._execute_maven_task(task)
        assert task.status == "failed"

    def test_maven_not_available(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        maven_root_result = MagicMock(success=True, stdout="/remote/path")
        java_check_result = MagicMock(success=True, stdout="openjdk version \"21.0.1\"")
        maven_check_result = MagicMock(success=False, stdout="")
        maven_install_stream = MagicMock(success=False, stdout="")
        maven_verify_result = MagicMock(success=False, stdout="")
        mock_executor.exec_command.side_effect = [
            maven_root_result,
            java_check_result,
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            maven_check_result,
            maven_verify_result,
        ]
        mock_executor.exec_command_stream.return_value = 1
        service._execute_maven_task(task)
        assert task.status == "failed"

    def test_compile_success(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "completed"

    def test_compile_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        mock_executor.exec_command_stream.return_value = 1
        service._execute_maven_task(task)
        assert task.status == "failed"

    def test_compile_stopped(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]

        def stream_with_stop(command, output_callback, timeout=None, stop_check=None):
            task.request_stop()
            return 0

        mock_executor.exec_command_stream.side_effect = stream_with_stop
        service._execute_maven_task(task)
        assert task.status == "stopped"

    def test_compile_with_jdk8(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile", "jdk_version": "8"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"1.8.0\""),
            MagicMock(success=True, stdout="openjdk version \"1.8.0\""),
            MagicMock(success=True, stdout="8"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "completed"

    def test_compile_with_local_path(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile", "local_path": "C:\\Users\\myapp"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path/myapp"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "completed"

    def test_compile_non_mvn_command(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "gradle build"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="21"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "completed"

    def test_compile_java_version_lower_than_target(self, service, mock_executor):
        task = new_build_task("server1", "/project", "compile", {"command": "mvn compile", "jdk_version": "21"})
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="openjdk version \"11.0.1\""),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
        ]
        mock_executor.exec_command_stream.return_value = 0
        service._execute_maven_task(task)
        assert task.status == "completed"


class TestFollowLogFile:
    def test_follow_log_reads_file(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {})
        task.status = "running"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="line1\nline2"),
            MagicMock(success=True, stdout="100"),
            MagicMock(success=False, stdout=""),
        ]
        with patch("app.services.build_service.time") as mock_time:
            mock_time.time.side_effect = [0, 0.5, 1.5]
            mock_time.sleep = MagicMock()
            service._follow_log_file(task, "/remote/nohup.log", duration=1)

    def test_follow_log_stops_when_task_not_running(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {})
        task.status = "completed"
        with patch("app.services.build_service.time") as mock_time:
            mock_time.time.side_effect = [0]
            service._follow_log_file(task, "/remote/nohup.log", duration=30)


class TestExecuteRunTask:
    def test_run_jar_success_with_log(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
            "jvm_args": "",
            "app_args": "",
        })
        with patch("app.services.build_service.RemoteExecutor") as mock_re_cls, \
             patch("app.services.build_service.threading.Thread") as mock_thread_cls, \
             patch("app.services.build_service.time") as mock_time:
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/path"
            nohup_result = MagicMock(success=True, stdout="12345")
            log_result = MagicMock(success=True, stdout="log content")
            call_count = [0]
            def exec_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return nohup_result
                return log_result
            mock_re.exec_command.side_effect = exec_side_effect
            mock_re_cls.return_value = mock_re
            mock_thread_cls.return_value = MagicMock()
            mock_time.sleep = MagicMock()
            service._execute_run_task(task)
        assert task.pid == 12345

    def test_run_spring_boot_no_pom(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
        service._execute_run_task(task)
        assert task.status == "failed"


class TestRunJarInternal:
    def test_pid_parse_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="not_a_pid"),
            MagicMock(success=True, stdout="error log content"),
        ]
        result = service._run_jar_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stderr="connection refused"),
            MagicMock(success=False, stderr="no log file"),
        ]
        result = service._run_jar_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure_with_log(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stderr="error"),
            MagicMock(success=True, stdout="app error log"),
        ]
        result = service._run_jar_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_pid_parse_failure_no_log(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="not_a_pid"),
            MagicMock(success=False, stderr="no file"),
        ]
        result = service._run_jar_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_with_server_port(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="12345")
        result = service._run_jar_internal(task)
        assert task.pid == 12345
        assert result is not None

    def test_with_jdk_version(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "/app.jar",
            "jdk_version": "17",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="12345")
        result = service._run_jar_internal(task)
        assert task.pid == 12345

    def test_relative_jar_path(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "jar",
            "jar_path": "target/app.jar",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="12345")
        result = service._run_jar_internal(task)
        assert task.pid == 12345


class TestRunSpringBootInternal:
    def test_no_pom_xml(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
        result = service._run_spring_boot_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_pid_parse_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="not_a_pid"),
            MagicMock(success=True, stdout="error log"),
        ]
        result = service._run_spring_boot_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=False, stderr="connection refused"),
            MagicMock(success=False, stderr="no log"),
        ]
        result = service._run_spring_boot_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure_with_log(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=False, stderr="error"),
            MagicMock(success=True, stdout="spring error log"),
        ]
        result = service._run_spring_boot_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_success_with_jdk(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "spring-boot",
            "server_port": "8080",
            "jdk_version": "17",
            "main_class": "com.example.App",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="12345"),
        ]
        result = service._run_spring_boot_internal(task)
        assert task.pid == 12345
        assert result is not None


class TestRunExecJavaInternal:
    def test_no_pom_xml(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "exec",
            "main_class": "com.example.App",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
        result = service._run_exec_java_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_pid_parse_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "exec",
            "main_class": "com.example.App",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="not_a_pid"),
            MagicMock(success=True, stdout="error log"),
        ]
        result = service._run_exec_java_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "exec",
            "main_class": "com.example.App",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=False, stderr="connection refused"),
            MagicMock(success=False, stderr="no log"),
        ]
        result = service._run_exec_java_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_startup_failure_with_log(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "exec",
            "main_class": "com.example.App",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=False, stderr="error"),
            MagicMock(success=True, stdout="exec error log"),
        ]
        result = service._run_exec_java_internal(task)
        assert task.status == "failed"
        assert result is None

    def test_success_with_jdk(self, service, mock_executor):
        task = new_build_task("server1", "/project", "run", {
            "run_mode": "exec",
            "main_class": "com.example.App",
            "jdk_version": "17",
        })
        mock_executor.resolve_path.return_value = "/remote/path"
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="/remote/path"),
            MagicMock(success=True, stdout="12345"),
        ]
        result = service._run_exec_java_internal(task)
        assert task.pid == 12345
        assert result is not None
