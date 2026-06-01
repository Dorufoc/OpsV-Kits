from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.build_service import BuildService, InstallTaskInfo
from app.core.remote_executor import RemoteExecutorError
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


class TestInstallTaskInfo:
    def test_to_dict(self):
        task = InstallTaskInfo("tid1", "srv1", ["java-21", "maven"])
        task.status = "running"
        task.progress = 50.0
        task.message = "installing"
        task.started_at = "2024-01-01T00:00:00"
        task.completed_at = None
        task.error = None
        d = task.to_dict()
        assert d["task_id"] == "tid1"
        assert d["account_alias"] == "srv1"
        assert d["components"] == ["java-21", "maven"]
        assert d["status"] == "running"
        assert d["progress"] == 50.0

    def test_add_callback_and_notify(self):
        task = InstallTaskInfo("tid2", "srv1", ["maven"])
        results = []
        task.add_callback(lambda t: results.append(t.status))
        task.status = "completed"
        task._notify()
        assert results == ["completed"]

    def test_callback_exception_is_swallowed(self):
        task = InstallTaskInfo("tid3", "srv1", ["maven"])
        task.add_callback(lambda t: 1 / 0)
        task._notify()


class TestCheckJava:
    def test_check_java_installed_with_jdk_version(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
        ]
        result = service.check_java("srv1", "/project", jdk_version="21")
        assert result["installed"] is True
        assert result["version"] == "21"
        assert result["required"] == "21"
        assert result["compatible"] is True

    def test_check_java_not_installed_fallback(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stdout=""),
            MagicMock(success=True, stdout="openjdk version \"11.0.1\""),
        ]
        result = service.check_java("srv1", "/project")
        assert result["installed"] is True
        assert result["version"] == "11"
        assert result["compatible"] is False

    def test_check_java_incompatible_version(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="openjdk version \"11.0.1\""),
        ]
        result = service.check_java("srv1", "/project", jdk_version="17")
        assert result["installed"] is True
        assert result["compatible"] is False

    def test_check_java_no_version_found(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stdout=""),
            MagicMock(success=False, stdout="no java found"),
        ]
        result = service.check_java("srv1", "/project")
        assert result["installed"] is False
        assert result["required"] == "21"

    def test_check_java_version_parse_error(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="openjdk version \"abc\""),
        ]
        result = service.check_java("srv1", "/project", jdk_version="21")
        assert result["installed"] is False
        assert result["compatible"] is False


class TestCheckMaven:
    def test_check_maven_installed_compatible(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="Apache Maven 3.9.5 (abc)\nOther info"),
        ]
        result = service.check_maven("srv1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is True

    def test_check_maven_installed_old_version(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="Apache Maven 3.5.0 (abc)\nOther info"),
        ]
        result = service.check_maven("srv1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is False

    def test_check_maven_not_installed(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stdout=""),
            MagicMock(success=False, stdout="mvn not found"),
        ]
        result = service.check_maven("srv1", "/project")
        assert result["installed"] is False

    def test_check_maven_fallback_installed(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=False, stdout=""),
            MagicMock(success=True, stdout="Apache Maven 3.8.1 (abc)\nInfo"),
        ]
        result = service.check_maven("srv1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is True

    def test_check_maven_version_parse_error(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="Some random output without maven version"),
        ]
        result = service.check_maven("srv1", "/project")
        assert result["installed"] is True
        assert result["compatible"] is False


class TestInstallJava:
    def test_install_java_success(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
        ]
        with patch.object(service, "_try_sudo"):
            result = service.install_java("srv1", version="21")
        assert result["component"] == "java"
        assert result["version"] == "21"

    def test_install_java_jdk8_package_name(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="openjdk version \"1.8.0\""),
        ]
        with patch.object(service, "_try_sudo") as mock_sudo:
            result = service.install_java("srv1", version="8")
            sudo_cmd = mock_sudo.call_args[0][1]
            assert "java-1.8.0-openjdk" in sudo_cmd

    def test_install_java_with_mirror_and_proxy(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
        ]
        with patch.object(service, "_try_sudo") as mock_sudo:
            result = service.install_java("srv1", version="21", dnf_mirror="http://mirror", proxy="http://proxy")
            sudo_cmd = mock_sudo.call_args[0][1]
            assert "--setopt=baseurl=http://mirror" in sudo_cmd
            assert "--setopt=proxy=http://proxy" in sudo_cmd

    def test_install_java_verify_fails(self, service, mock_executor):
        with patch.object(service, "_try_sudo"):
            mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
            result = service.install_java("srv1", version="21")
        assert result["installed"] is False

    def test_install_java_with_callback(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="openjdk version \"21.0.1\""),
        ]
        messages = []
        with patch.object(service, "_try_sudo"):
            result = service.install_java("srv1", version="21", status_callback=messages.append)
        assert len(messages) > 0


class TestInstallMaven:
    def test_install_maven_success(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5 (abc)"),
        ]
        with patch.object(service, "_try_sudo"):
            result = service.install_maven("srv1")
        assert result["component"] == "maven"
        assert result["installed"] is True

    def test_install_maven_with_mirror_proxy(self, service, mock_executor):
        mock_executor.exec_command.side_effect = [
            MagicMock(success=True, stdout="installed"),
            MagicMock(success=True, stdout="Apache Maven 3.9.5"),
        ]
        with patch.object(service, "_try_sudo") as mock_sudo:
            result = service.install_maven("srv1", dnf_mirror="http://m", proxy="http://p")
            sudo_cmd = mock_sudo.call_args[0][1]
            assert "--setopt=baseurl=http://m" in sudo_cmd

    def test_install_maven_verify_fails(self, service, mock_executor):
        with patch.object(service, "_try_sudo"):
            mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
            result = service.install_maven("srv1")
        assert result["installed"] is False


class TestInstallEnvironment:
    def test_install_environment_creates_task(self, service):
        with patch.object(service, "install_java", return_value={"component": "java", "installed": True}), \
             patch.object(service, "install_maven", return_value={"component": "maven", "installed": True}), \
             patch("app.services.build_service.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            task = service.install_environment("srv1", java_version="21")
            assert task.account_alias == "srv1"
            assert "java-21" in task.components
            assert "maven" in task.components
            assert task.status == "running"

    def test_install_environment_no_java(self, service):
        with patch.object(service, "install_maven", return_value={"component": "maven", "installed": True}), \
             patch("app.services.build_service.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            task = service.install_environment("srv1")
            assert "java" not in str(task.components)
            assert "maven" in task.components

    def test_install_environment_with_custom_task_id(self, service):
        with patch.object(service, "install_maven", return_value={"component": "maven", "installed": True}), \
             patch("app.services.build_service.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            task = service.install_environment("srv1", task_id="custom_id")
            assert task.task_id == "custom_id"


class TestTrySudo:
    def test_try_sudo_success(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="ok")
        results = []
        service._try_sudo(mock_executor, "dnf install -y java", results.append)
        assert len(results) == 1

    def test_try_sudo_permission_denied_then_sudo(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(
            success=False, stderr="Permission denied", exit_code=1
        )
        mock_executor.exec_with_pty.return_value = MagicMock(success=True, stdout="installed via sudo")
        results = []
        service._try_sudo(mock_executor, "dnf install -y java", results.append)
        mock_executor.exec_with_pty.assert_called_once()
        assert len(results) == 2

    def test_try_sudo_permission_denied_sudo_fails(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(
            success=False, stderr="Permission denied", exit_code=1
        )
        mock_executor.exec_with_pty.return_value = MagicMock(success=False, stderr="sudo failed")
        with pytest.raises(RemoteExecutorError, match="sudo"):
            service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_other_error(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(
            success=False, stderr="package not found", exit_code=1
        )
        with pytest.raises(RemoteExecutorError, match="安装命令执行失败"):
            service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_bytes_stderr(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(
            success=False, stderr=b"Permission denied", exit_code=1
        )
        mock_executor.exec_with_pty.return_value = MagicMock(success=True, stdout="ok")
        service._try_sudo(mock_executor, "dnf install -y java", lambda x: None)

    def test_try_sudo_long_stdout_truncated(self, service, mock_executor):
        long_output = "x" * 300
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout=long_output)
        results = []
        service._try_sudo(mock_executor, "dnf install -y java", results.append)
        assert len(results[0]) <= 200


class TestParsePomJavaVersion:
    def test_parse_java_version_tag(self, service, mock_executor):
        pom = "<properties><java.version>17</java.version></properties>"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout=pom)
        result = service._parse_pom_java_version(mock_executor, "/project")
        assert result == "17"

    def test_parse_source_tag(self, service, mock_executor):
        pom = "<properties><maven.compiler.source>11</maven.compiler.source></properties>"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout=pom)
        result = service._parse_pom_java_version(mock_executor, "/project")
        assert result == "11"

    def test_parse_target_tag(self, service, mock_executor):
        pom = "<properties><maven.compiler.target>1.8</maven.compiler.target></properties>"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout=pom)
        result = service._parse_pom_java_version(mock_executor, "/project")
        assert result == "8"

    def test_parse_no_version(self, service, mock_executor):
        pom = "<properties><other>value</other></properties>"
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout=pom)
        result = service._parse_pom_java_version(mock_executor, "/project")
        assert result == ""

    def test_parse_pom_not_found(self, service, mock_executor):
        mock_executor.exec_command.return_value = MagicMock(success=False, stdout="")
        result = service._parse_pom_java_version(mock_executor, "/project")
        assert result == ""


class TestReadRunLog:
    def test_read_run_log_success(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {"run_mode": "jar", "jar_path": "/app.jar"})
        with patch.object(service, "get_build_task", return_value=task):
            mock_executor.resolve_path.return_value = "/remote/path"
            mock_executor.exec_command.return_value = MagicMock(success=True, stdout="log line 1\nlog line 2")
            result = service.read_run_log(task.task_id)
            assert "log line 1" in result

    def test_read_run_log_not_found(self, service):
        result = service.read_run_log("nonexistent")
        assert result == ""

    def test_read_run_log_with_local_path(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {
            "run_mode": "jar", "jar_path": "/app.jar", "local_path": "C:\\Users\\myapp"
        })
        with patch.object(service, "get_build_task", return_value=task):
            mock_executor.resolve_path.return_value = "/remote/path"
            mock_executor.exec_command.return_value = MagicMock(success=True, stdout="log content")
            result = service.read_run_log(task.task_id)
            assert "log content" in result

    def test_read_run_log_read_fails(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {"run_mode": "jar", "jar_path": "/app.jar"})
        with patch.object(service, "get_build_task", return_value=task):
            mock_executor.resolve_path.return_value = "/remote/path"
            mock_executor.exec_command.return_value = MagicMock(success=False, stderr="file not found")
            result = service.read_run_log(task.task_id)
            assert "无法读取" in result


class TestKillProcessTree:
    def test_kill_process_tree_success(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {})
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="stopped")
        with patch("app.services.build_service.time") as mock_time:
            mock_time.sleep = MagicMock()
            service._kill_process_tree(mock_executor, 12345, task)
        assert any("已终止" in line for line in task.log.split("\n"))

    def test_kill_process_tree_pstree_fails(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {})
        call_count = [0]
        def exec_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("pstree error")
            return MagicMock(success=True, stdout="")
        mock_executor.exec_command.side_effect = exec_side_effect
        with patch("app.services.build_service.time") as mock_time:
            mock_time.sleep = MagicMock()
            service._kill_process_tree(mock_executor, 12345, task)
        assert any("强制终止" in line for line in task.log.split("\n"))

    def test_kill_process_tree_child_pid_parse_error(self, service, mock_executor):
        task = new_build_task("srv1", "/project", "run", {})
        mock_executor.exec_command.return_value = MagicMock(success=True, stdout="stopped")
        with patch("app.services.build_service.time") as mock_time:
            mock_time.sleep = MagicMock()
            service._kill_process_tree(mock_executor, 12345, task)
