from unittest.mock import MagicMock, patch, call

import pytest

from app.core.remote_executor import CommandResult


def _make_command_result(exit_code=0, stdout="", stderr=""):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


@pytest.fixture
def mock_executor():
    with patch("app.core.node_env_manager.RemoteExecutor") as MockCls:
        mock = MagicMock()
        MockCls.return_value = mock
        yield mock, MockCls


@pytest.fixture
def manager(mock_executor):
    from app.core.node_env_manager import NodeEnvManager
    return NodeEnvManager("test")


class TestNodeEnvManagerInit:
    def test_init_creates_executor(self):
        with patch("app.core.node_env_manager.RemoteExecutor") as MockCls:
            from app.core.node_env_manager import NodeEnvManager
            NodeEnvManager("myalias")
            MockCls.assert_called_once_with("myalias")

    def test_stores_account_alias(self, manager):
        assert manager._account_alias == "test"


class TestCheckNode:
    def test_node_installed_success_path(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="v20.11.0"),
            _make_command_result(exit_code=0, stdout="10.2.3"),
        ]
        result = manager.check_node()
        assert result["installed"] is True
        assert result["version"] == "20.11.0"
        assert result["npm_installed"] is True
        assert result["npm_version"] == "10.2.3"

    def test_node_installed_fallback_path(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="v18.0.0"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="9.0.0"),
        ]
        result = manager.check_node()
        assert result["installed"] is True
        assert result["version"] == "18.0.0"
        assert result["npm_installed"] is True
        assert result["npm_version"] == "9.0.0"

    def test_node_not_installed(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout="command not found"),
            _make_command_result(exit_code=0, stdout="command not found"),
            _make_command_result(exit_code=1, stdout="command not found"),
            _make_command_result(exit_code=0, stdout="command not found"),
        ]
        result = manager.check_node()
        assert result["installed"] is False
        assert result["version"] == ""
        assert result["npm_installed"] is False
        assert result["npm_version"] == ""

    def test_node_version_without_v_prefix(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="20.11.0"),
            _make_command_result(exit_code=0, stdout="10.2.3"),
        ]
        result = manager.check_node()
        assert result["installed"] is True
        assert result["version"] == "20.11.0"

    def test_node_version_no_match(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="no version here"),
            _make_command_result(exit_code=0, stdout="no version here"),
        ]
        result = manager.check_node()
        assert result["installed"] is False
        assert result["npm_installed"] is False

    def test_npm_only_installed(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="no version"),
            _make_command_result(exit_code=0, stdout="10.2.3"),
        ]
        result = manager.check_node()
        assert result["installed"] is False
        assert result["npm_installed"] is True

    def test_different_account_alias(self, manager, mock_executor):
        mock_exec, MockCls = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="v20.0.0"),
            _make_command_result(exit_code=0, stdout="10.0.0"),
        ]
        manager.check_node(account_alias="other")
        MockCls.assert_called_with("other")


class TestDetectPackageManager:
    def test_ubuntu_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout='ID=ubuntu\nVERSION="22.04"'
        )
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_debian_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout='ID=debian\nVERSION="12"'
        )
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_deepin_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout='ID=deepin'
        )
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_uos_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout='ID=uos'
        )
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_kali_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.return_value = _make_command_result(
            exit_code=0, stdout='ID=kali'
        )
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_centos_with_dnf(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=centos'),
            _make_command_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "dnf"

    def test_centos_without_dnf(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=centos'),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "yum"

    def test_fedora_with_dnf(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=fedora'),
            _make_command_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "dnf"

    def test_rhel_with_dnf(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=rhel'),
            _make_command_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "dnf"

    def test_rocky_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=rocky'),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "yum"

    def test_almalinux_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=almalinux'),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "yum"

    def test_oracle_detected(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=oracle'),
            _make_command_result(exit_code=1, stdout=""),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "yum"

    def test_fallback_apt(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="unknown_os"),
            _make_command_result(exit_code=0, stdout="/usr/bin/apt"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_fallback_dnf(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="unknown_os"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "dnf"

    def test_fallback_yum(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="unknown_os"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/yum"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "yum"

    def test_no_package_manager_raises(self, manager, mock_executor):
        from app.core.node_env_manager import NodeEnvManagerError
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout="unknown_os"),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=1, stdout=""),
        ]
        with pytest.raises(NodeEnvManagerError, match="无法检测系统包管理器"):
            manager._detect_package_manager(mock_exec)

    def test_os_release_empty(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/apt"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"

    def test_os_release_fails(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="/usr/bin/apt"),
        ]
        result = manager._detect_package_manager(mock_exec)
        assert result == "apt"


class TestInstallNode:
    def test_install_apt_success(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout="v20.11.0"),
            _make_command_result(exit_code=0, stdout="10.2.3"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        result = manager.install_node(version="20")
        assert result["installed"] is True
        assert result["node_version"] == "20.11.0"
        assert result["npm_version"] == "10.2.3"
        assert "成功" in result["message"]

    def test_install_yum_success(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=centos'),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout="v18.0.0"),
            _make_command_result(exit_code=0, stdout="9.0.0"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        result = manager.install_node(version="18")
        assert result["installed"] is True
        assert result["node_version"] == "18.0.0"

    def test_install_dnf_success(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=fedora'),
            _make_command_result(exit_code=0, stdout="/usr/bin/dnf"),
            _make_command_result(exit_code=0, stdout="v20.0.0"),
            _make_command_result(exit_code=0, stdout="10.0.0"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        result = manager.install_node(version="20")
        assert result["installed"] is True

    def test_install_primary_fails_fallback_succeeds(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout="v20.11.0"),
            _make_command_result(exit_code=0, stdout="10.2.3"),
        ]
        mock_exec.exec_command_stream.side_effect = [1, 0]

        result = manager.install_node(version="20")
        assert result["installed"] is True
        assert mock_exec.exec_command_stream.call_count == 2

    def test_install_primary_fails_fallback_fails(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        mock_exec.exec_command_stream.side_effect = [1, 1]

        result = manager.install_node(version="20")
        assert result["installed"] is False
        assert "失败" in result["message"]

    def test_install_with_callback(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout="v20.0.0"),
            _make_command_result(exit_code=0, stdout="10.0.0"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        messages = []
        result = manager.install_node(version="20", callback=messages.append)
        assert len(messages) > 0
        assert any("包管理器" in m for m in messages)

    def test_install_unsupported_package_manager(self, manager, mock_executor):
        from app.core.node_env_manager import NodeEnvManagerError
        mock_exec, _ = mock_executor
        with patch.object(manager, "_detect_package_manager", return_value="unknown_pkg"):
            with pytest.raises(NodeEnvManagerError, match="不支持的包管理器"):
                manager.install_node()

    def test_install_yum_fallback_command(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=centos'),
            _make_command_result(exit_code=1, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
            _make_command_result(exit_code=0, stdout=""),
        ]
        mock_exec.exec_command_stream.side_effect = [1, 0]

        result = manager.install_node(version="18")
        fallback_call = mock_exec.exec_command_stream.call_args_list[1]
        assert "yum install -y nodejs npm" in fallback_call[0][0]

    def test_install_different_account_alias(self, manager, mock_executor):
        mock_exec, MockCls = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout="v20.0.0"),
            _make_command_result(exit_code=0, stdout="10.0.0"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        manager.install_node(account_alias="other", version="20")
        MockCls.assert_called_with("other")

    def test_install_default_version(self, manager, mock_executor):
        mock_exec, _ = mock_executor
        mock_exec.exec_command.side_effect = [
            _make_command_result(exit_code=0, stdout='ID=ubuntu'),
            _make_command_result(exit_code=0, stdout="v20.0.0"),
            _make_command_result(exit_code=0, stdout="10.0.0"),
        ]
        mock_exec.exec_command_stream.return_value = 0

        result = manager.install_node()
        assert result["version"] == "20"


class TestNodeEnvManagerError:
    def test_is_exception(self):
        from app.core.node_env_manager import NodeEnvManagerError
        assert issubclass(NodeEnvManagerError, Exception)

    def test_raise_and_catch(self):
        from app.core.node_env_manager import NodeEnvManagerError
        with pytest.raises(NodeEnvManagerError, match="test"):
            raise NodeEnvManagerError("test")
