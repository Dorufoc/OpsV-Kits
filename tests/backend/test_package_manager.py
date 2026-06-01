from unittest.mock import MagicMock, patch

import pytest

from app.core.remote_executor import CommandResult


def _make_command_result(exit_code=0, stdout="", stderr=""):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


@pytest.fixture
def mock_executor():
    with patch("app.core.package_manager.RemoteExecutor") as MockCls:
        mock = MagicMock()
        MockCls.return_value = mock
        mock.resolve_path.return_value = "/home/user/project"
        yield mock, MockCls


@pytest.fixture
def manager(mock_executor):
    from app.core.package_manager import PackageManager
    return PackageManager("test")


class TestPackageManagerInit:
    def test_init_creates_executor(self):
        with patch("app.core.package_manager.RemoteExecutor") as MockCls:
            from app.core.package_manager import PackageManager
            PackageManager("myalias")
            MockCls.assert_called_once_with("myalias")

    def test_initial_state(self, manager):
        assert manager._manager is None
        assert manager._install_command is None


class TestDetect:
    def test_empty_path_raises(self, manager, mock_executor):
        from app.core.package_manager import PackageManagerError
        with pytest.raises(PackageManagerError, match="项目路径不能为空"):
            manager.detect(project_path="")

    def test_detect_pnpm_lock(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        result = manager.detect(project_path="/project")
        assert result == "pnpm"
        assert manager._manager == "pnpm"
        assert manager._install_command == "pnpm install"

    def test_detect_yarn_lock(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "yarn"
        assert manager._install_command == "yarn install"

    def test_detect_npm_lock(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "npm"
        assert manager._install_command == "npm install"

    def test_detect_npm_shrinkwrap(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "npm"

    def test_detect_fallback_pnpm(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="/usr/bin/pnpm"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "pnpm"

    def test_detect_fallback_yarn(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/yarn"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "yarn"

    def test_detect_fallback_npm(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/npm"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "npm"

    def test_detect_default_npm_when_nothing_found(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = manager.detect(project_path="/project")
        assert result == "npm"
        assert manager._install_command == "npm install"

    def test_detect_lock_file_check_fails(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/pnpm"),
        ]
        result = manager.detect(project_path="/project")
        assert result == "pnpm"

    def test_detect_calls_resolve_path(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="~/project")
        mock_exec.resolve_path.assert_called_once_with("~/project")

    def test_detect_different_account_alias(self, manager, mock_executor):
        mock_exec, MockCls = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(account_alias="other", project_path="/project")
        MockCls.assert_called_with("other")

    def test_detect_same_account_alias(self, manager, mock_executor):
        mock_exec, MockCls = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(account_alias="test", project_path="/project")
        assert MockCls.call_count == 1


class TestBuildInstallCommand:
    def test_npm_command(self, manager):
        assert manager._build_install_command("npm") == "npm install"

    def test_yarn_command(self, manager):
        assert manager._build_install_command("yarn") == "yarn install"

    def test_pnpm_command(self, manager):
        assert manager._build_install_command("pnpm") == "pnpm install"

    def test_unknown_defaults_to_npm(self, manager):
        assert manager._build_install_command("unknown") == "npm install"


class TestGetInstallCommand:
    def test_before_detect_raises(self, manager):
        from app.core.package_manager import PackageManagerError
        with pytest.raises(PackageManagerError, match="请先调用 detect"):
            manager.get_install_command()

    def test_after_detect(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="/project")
        assert manager.get_install_command() == "pnpm install"


class TestGetManager:
    def test_before_detect_raises(self, manager):
        from app.core.package_manager import PackageManagerError
        with pytest.raises(PackageManagerError, match="请先调用 detect"):
            manager.get_manager()

    def test_after_detect(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="/project")
        assert manager.get_manager() == "pnpm"


class TestGetRunCommand:
    def test_before_detect_raises(self, manager):
        from app.core.package_manager import PackageManagerError
        with pytest.raises(PackageManagerError, match="请先调用 detect"):
            manager.get_run_command("dev")

    def test_npm_run_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        manager.detect(project_path="/project")
        assert manager.get_run_command("test") == "npm run test"

    def test_yarn_run_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        manager.detect(project_path="/project")
        assert manager.get_run_command("dev") == "yarn dev"

    def test_pnpm_run_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="/project")
        assert manager.get_run_command("build") == "pnpm build"

    def test_unknown_manager_defaults_to_npm(self, manager):
        manager._manager = "unknown"
        assert manager.get_run_command("start") == "npm run start"


class TestGetBuildCommand:
    def test_build_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="/project")
        assert manager.get_build_command() == "pnpm build"

    def test_build_command_npm(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        manager.detect(project_path="/project")
        assert manager.get_build_command() == "npm run build"


class TestGetDevCommand:
    def test_dev_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout="yes"
        )
        manager.detect(project_path="/project")
        assert manager.get_dev_command() == "pnpm dev"

    def test_dev_command_yarn(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no"),
            _make_command_result(exit_code=0, stdout="yes"),
        ]
        manager.detect(project_path="/project")
        assert manager.get_dev_command() == "yarn dev"


class TestPackageManagerError:
    def test_is_exception(self):
        from app.core.package_manager import PackageManagerError
        assert issubclass(PackageManagerError, Exception)

    def test_raise_and_catch(self):
        from app.core.package_manager import PackageManagerError
        with pytest.raises(PackageManagerError, match="test"):
            raise PackageManagerError("test")
