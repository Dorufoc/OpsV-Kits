from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.core.remote_executor import CommandResult


def _make_result(exit_code=0, stdout="", stderr=""):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


@pytest.fixture
def mock_executor():
    with patch("app.core.nginx_config_manager.RemoteExecutor") as MockCls:
        mock = MagicMock()
        MockCls.return_value = mock
        yield mock


class TestNginxConfigManagerInit:
    def test_init_creates_executor(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mgr = NginxConfigManager("test-server")
        assert mgr._account_alias == "test-server"

    def test_init_different_alias(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout="command not found"),
        ]
        mgr = NginxConfigManager("test-server")
        mgr.check_nginx(account_alias="other-server")
        from app.core.nginx_config_manager import RemoteExecutor
        assert RemoteExecutor.call_count >= 2


class TestCheckNginx:
    def test_not_installed_which_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout="command not found"),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is False
        assert result["running"] is False

    def test_installed_with_version(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx version: nginx/1.24.0"),
            _make_result(exit_code=0, stdout="root 1234 nginx"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is True
        assert result["version"] == "1.24.0"
        assert result["running"] is True

    def test_installed_not_running(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx version: nginx/1.22.1"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is True
        assert result["running"] is False

    def test_which_fails_nginx_v_succeeds(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="nginx version: nginx/1.18.0"),
            _make_result(exit_code=0, stdout="nginx version: nginx/1.18.0"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is True
        assert result["version"] == "1.18.0"

    def test_which_fails_nginx_v_no_nginx(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout="command not found"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is False

    def test_version_no_match(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="some other output"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["installed"] is False
        assert result["version"] == ""

    def test_ps_check_not_running(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx/1.24.0"),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx()
        assert result["running"] is False

    def test_different_account_alias(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout="command not found"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_nginx(account_alias="other")
        assert result["installed"] is False


class TestDetectPackageManager:
    def test_detect_apt_ubuntu(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=ubuntu\nNAME="Ubuntu"'),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_apt_debian(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=debian\nNAME="Debian"'),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_apt_deepin(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=deepin'),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_dnf_fedora(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=fedora'),
            _make_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "dnf"

    def test_detect_yum_centos(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=centos'),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "yum"

    def test_detect_yum_rhel(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=rhel'),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "yum"

    def test_detect_rocky_uses_dnf(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=rocky'),
            _make_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "dnf"

    def test_detect_fallback_apt(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="/usr/bin/apt"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_fallback_dnf(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "dnf"

    def test_detect_fallback_yum(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="/usr/bin/yum"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "yum"

    def test_detect_no_package_manager(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager, NginxConfigManagerError
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        with pytest.raises(NginxConfigManagerError, match="无法检测系统包管理器"):
            mgr._detect_package_manager(mock_executor)

    def test_detect_os_release_empty(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout=""),
            _make_result(exit_code=0, stdout="/usr/bin/apt"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_kali(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=kali'),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_uos(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=uos'),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "apt"

    def test_detect_almalinux(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=almalinux'),
            _make_result(exit_code=0, stdout="/usr/bin/dnf"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "dnf"

    def test_detect_oracle(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=oracle'),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr._detect_package_manager(mock_executor)
        assert result == "yum"


class TestInstallNginx:
    def test_install_apt_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=ubuntu'),
            _make_result(exit_code=0, stdout="Setting up nginx"),
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx/1.24.0"),
            _make_result(exit_code=0, stdout="root 1234 nginx"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.install_nginx()
        assert result["installed"] is True
        assert result["version"] == "1.24.0"

    def test_install_yum_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=centos'),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="Installed: nginx"),
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx/1.24.0"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.install_nginx()
        assert result["installed"] is True

    def test_install_dnf_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=fedora'),
            _make_result(exit_code=0, stdout="/usr/bin/dnf"),
            _make_result(exit_code=0, stdout="Installed: nginx"),
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx/1.24.0"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.install_nginx()
        assert result["installed"] is True

    def test_install_needs_sudo(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=ubuntu'),
            _make_result(exit_code=1, stderr="Permission denied"),
            _make_result(exit_code=0, stdout="Setting up nginx"),
            _make_result(exit_code=0, stdout="/usr/sbin/nginx"),
            _make_result(exit_code=0, stdout="nginx/1.24.0"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.install_nginx()
        assert result["installed"] is True

    def test_install_sudo_also_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager, NginxConfigManagerError
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=ubuntu'),
            _make_result(exit_code=1, stderr="Permission denied"),
            _make_result(exit_code=1, stderr="sudo also failed"),
        ]
        mgr = NginxConfigManager("test")
        with pytest.raises(NginxConfigManagerError, match="Nginx 安装失败"):
            mgr.install_nginx()

    def test_install_unsupported_pkg_manager(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager, NginxConfigManagerError
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout='ID=someos'),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        with pytest.raises(NginxConfigManagerError, match="无法检测系统包管理器"):
            mgr.install_nginx()


class TestCheckPortConflict:
    def test_no_conflict(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert result["conflict"] is False
        assert result["processes"] == []

    def test_conflict_netstat(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="tcp  0  0  0.0.0.0:8080  0.0.0.0:*  LISTEN  1234/nginx"),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert result["conflict"] is True
        assert len(result["processes"]) > 0

    def test_conflict_ss(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="LISTEN  0  128  0.0.0.0:8080  0.0.0.0:*  users:((\"nginx\",pid=1234))"),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert result["conflict"] is True

    def test_conflict_lsof(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=0, stdout="nginx  1234  root  3u  IPv4  12345  0t0  TCP *:8080 (LISTEN)"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert result["conflict"] is True

    def test_conflict_dedup_processes(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        line = "tcp  0  0  0.0.0.0:8080  LISTEN  nginx"
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout=line),
            _make_result(exit_code=0, stdout=line),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert len(result["processes"]) == 1

    def test_conflict_empty_lines_skipped(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="\n\n  \n"),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080)
        assert result["conflict"] is False

    def test_different_account_alias(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
            _make_result(exit_code=1, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.check_port_conflict(8080, account_alias="other")
        assert result["conflict"] is False


class TestGenerateConfig:
    def test_generate_config_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.resolve_path.return_value = "/home/user/project"
        mock_executor.exec_command.return_value = _make_result(exit_code=0, stdout="")
        mgr = NginxConfigManager("test")
        result = mgr.generate_config("myapp", 8080, "example.com", "/home/user/project")
        assert "opsv-vite-myapp.conf" in result
        mock_executor.resolve_path.assert_called_once_with("/home/user/project")

    def test_generate_config_needs_sudo(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.resolve_path.return_value = "/home/user/project"
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stderr="Permission denied"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.generate_config("myapp", 8080, "example.com", "/home/user/project")
        assert "opsv-vite-myapp.conf" in result

    def test_generate_config_sudo_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager, NginxConfigManagerError
        mock_executor.resolve_path.return_value = "/home/user/project"
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stderr="Permission denied"),
            _make_result(exit_code=1, stderr="still denied"),
        ]
        mgr = NginxConfigManager("test")
        with pytest.raises(NginxConfigManagerError, match="无法写入 Nginx 配置"):
            mgr.generate_config("myapp", 8080, "example.com", "/home/user/project")

    def test_generate_config_content(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.resolve_path.return_value = "/var/www/html"
        mock_executor.exec_command.return_value = _make_result(exit_code=0, stdout="")
        mgr = NginxConfigManager("test")
        mgr.generate_config("proj", 3000, "localhost", "/var/www/html")
        write_call = mock_executor.exec_command.call_args
        cmd = write_call[0][0]
        assert "listen 3000" in cmd
        assert "server_name localhost" in cmd
        assert "root /var/www/html" in cmd

    def test_generate_config_different_account(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.resolve_path.return_value = "/home/user/project"
        mock_executor.exec_command.return_value = _make_result(exit_code=0, stdout="")
        mgr = NginxConfigManager("test")
        mgr.generate_config("myapp", 8080, "example.com", "/home/user/project", account_alias="other")


class TestReloadNginx:
    def test_reload_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="syntax is ok"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.reload_nginx()
        assert result["success"] is True

    def test_reload_test_needs_sudo(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stderr="permission"),
            _make_result(exit_code=0, stdout="syntax is ok"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.reload_nginx()
        assert result["success"] is True

    def test_reload_test_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stderr="config test failed"),
            _make_result(exit_code=1, stderr="still failed"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.reload_nginx()
        assert result["success"] is False
        assert "配置测试失败" in result["message"]

    def test_reload_needs_sudo(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="ok"),
            _make_result(exit_code=1, stderr="permission"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.reload_nginx()
        assert result["success"] is True

    def test_reload_sudo_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout="ok"),
            _make_result(exit_code=1, stderr="fail"),
            _make_result(exit_code=1, stderr="sudo fail"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.reload_nginx()
        assert result["success"] is False
        assert "reload 失败" in result["message"]


class TestRemoveConfig:
    def test_remove_config_success(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout=""),
            _make_result(exit_code=0, stdout="ok"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.remove_config("myapp")
        assert result["success"] is True
        assert "配置已删除" in result["message"]

    def test_remove_config_needs_sudo_rm(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=1, stderr="permission"),
            _make_result(exit_code=0, stdout=""),
            _make_result(exit_code=0, stdout="ok"),
            _make_result(exit_code=0, stdout=""),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.remove_config("myapp")
        assert result["success"] is True

    def test_remove_config_reload_fails(self, mock_executor):
        from app.core.nginx_config_manager import NginxConfigManager
        mock_executor.exec_command.side_effect = [
            _make_result(exit_code=0, stdout=""),
            _make_result(exit_code=1, stderr="test fail"),
            _make_result(exit_code=1, stderr="still fail"),
        ]
        mgr = NginxConfigManager("test")
        result = mgr.remove_config("myapp")
        assert result["success"] is False
        assert "重载失败" in result["message"]


class TestNginxConfigManagerError:
    def test_is_exception(self):
        from app.core.nginx_config_manager import NginxConfigManagerError
        assert issubclass(NginxConfigManagerError, Exception)

    def test_raise_and_catch(self):
        from app.core.nginx_config_manager import NginxConfigManagerError
        with pytest.raises(NginxConfigManagerError, match="test error"):
            raise NginxConfigManagerError("test error")
