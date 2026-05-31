from __future__ import annotations

import argparse
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from app.cli import (
    VERSION,
    Color,
    _add_alias_arg,
    _add_common_args,
    _add_config_arg,
    _build_parser,
    _cmd_account_add,
    _cmd_account_default,
    _cmd_account_edit,
    _cmd_account_list,
    _cmd_account_remove,
    _cmd_account_test,
    _cmd_build,
    _cmd_compose_down,
    _cmd_compose_logs,
    _cmd_compose_ps,
    _cmd_compose_up,
    _cmd_docker_build,
    _cmd_docker_exec,
    _cmd_docker_images,
    _cmd_docker_info,
    _cmd_docker_install,
    _cmd_docker_kill,
    _cmd_docker_logs,
    _cmd_docker_network_ls,
    _cmd_docker_prune,
    _cmd_docker_ps,
    _cmd_docker_pull,
    _cmd_docker_restart,
    _cmd_docker_rm,
    _cmd_docker_rmi,
    _cmd_docker_start,
    _cmd_docker_stop,
    _cmd_docker_volume_ls,
    _cmd_init,
    _cmd_remote_cat,
    _cmd_remote_chmod,
    _cmd_remote_cp,
    _cmd_remote_download,
    _cmd_remote_exec,
    _cmd_remote_find,
    _cmd_remote_ls,
    _cmd_remote_mkdir,
    _cmd_remote_mv,
    _cmd_remote_rm,
    _cmd_remote_upload,
    _cmd_run,
    _cmd_setup,
    _cmd_ssh,
    _cmd_start,
    _cmd_sync,
    _enable_vt_mode,
    _get_account_alias,
    _lazy,
    _load_config,
    _print_error,
    _print_info,
    _print_success,
    _print_table,
    _print_warning,
    main,
)


class TestColor:
    def test_ok(self):
        result = Color.ok("hello")
        assert "\033[32m" in result
        assert "hello" in result
        assert "\033[0m" in result

    def test_err(self):
        result = Color.err("error")
        assert "\033[31m" in result
        assert "error" in result

    def test_warn(self):
        result = Color.warn("warning")
        assert "\033[33m" in result
        assert "warning" in result

    def test_info(self):
        result = Color.info("info")
        assert "\033[36m" in result
        assert "info" in result

    def test_highlight(self):
        result = Color.highlight("hl")
        assert "\033[1m" in result
        assert "\033[34m" in result
        assert "hl" in result

    def test_dim(self):
        result = Color.dim("dim")
        assert "\033[2m" in result
        assert "dim" in result


class TestPrintHelpers:
    def test_print_success(self, capsys):
        _print_success("done")
        captured = capsys.readouterr()
        assert "done" in captured.out

    def test_print_error(self, capsys):
        _print_error("fail")
        captured = capsys.readouterr()
        assert "fail" in captured.err

    def test_print_warning(self, capsys):
        _print_warning("warn")
        captured = capsys.readouterr()
        assert "warn" in captured.out

    def test_print_info(self, capsys):
        _print_info("info")
        captured = capsys.readouterr()
        assert "info" in captured.out

    def test_print_table(self, capsys):
        headers = ["Name", "Type"]
        rows = [["foo", "bar"], ["baz", "qux"]]
        _print_table(headers, rows)
        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "foo" in captured.out
        assert "baz" in captured.out

    def test_print_table_single_row(self, capsys):
        _print_table(["A"], [["x"]])
        captured = capsys.readouterr()
        assert "A" in captured.out
        assert "x" in captured.out


class TestLazy:
    def test_lazy_imports_module(self):
        result = _lazy("argparse")
        import argparse as expected
        assert result is expected


class TestEnableVtMode:
    @patch("sys.platform", "win32")
    def test_enable_vt_mode_windows(self):
        with patch("ctypes.windll") as mock_windll:
            mock_kernel = mock_windll.kernel32
            mock_kernel.GetStdHandle.return_value = 1
            mock_kernel.GetConsoleMode.return_value = 0
            mode_ref = MagicMock()
            mode_ref.value = 3
            with patch("ctypes.c_uint32", return_value=mode_ref):
                with patch("ctypes.byref", return_value=None):
                    _enable_vt_mode()
                    mock_kernel.SetConsoleMode.assert_called_once()

    @patch("sys.platform", "linux")
    def test_enable_vt_mode_non_windows(self):
        _enable_vt_mode()

    @patch("sys.platform", "win32")
    def test_enable_vt_mode_exception(self):
        with patch("ctypes.windll", side_effect=Exception("no ctypes")):
            _enable_vt_mode()


class TestLoadConfig:
    def test_load_config_success(self, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("ssh:\n  host: localhost\n", encoding="utf-8")
        result = _load_config(str(config_file))
        assert result["ssh"]["host"] == "localhost"

    def test_load_config_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            _load_config("/nonexistent/path/settings.yaml")

    @patch("app.cli._DEFAULT_CONFIG_PATH")
    def test_load_config_default_path(self, mock_path, tmp_path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("key: value\n", encoding="utf-8")
        mock_path.__class__ = Path
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda s: str(config_file)
        mock_path.__fspath__ = lambda s: str(config_file)
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: StringIO("key: value\n")
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            result = _load_config(None)
            assert result["key"] == "value"


class TestGetAccountAlias:
    def test_alias_from_args(self):
        args = argparse.Namespace(alias="my-alias", config=None)
        result = _get_account_alias(args)
        assert result == "my-alias"

    @patch("app.cli._load_config")
    def test_alias_from_config_account_alias(self, mock_load):
        mock_load.return_value = {"ssh": {"account_alias": "config-alias"}}
        args = argparse.Namespace(alias=None, config=None)
        result = _get_account_alias(args)
        assert result == "config-alias"

    @patch("app.cli._load_config")
    def test_alias_from_config_alias_key(self, mock_load):
        mock_load.return_value = {"ssh": {"alias": "config-alias2"}}
        args = argparse.Namespace(alias=None, config=None)
        result = _get_account_alias(args)
        assert result == "config-alias2"

    @patch("app.cli._lazy")
    @patch("app.cli._load_config")
    def test_alias_from_default_account(self, mock_load, mock_lazy):
        mock_load.return_value = {"ssh": {}}
        mock_svc = MagicMock()
        default_acct = MagicMock()
        default_acct.alias = "default-alias"
        mock_svc.ssh_account_service.get_default.return_value = default_acct
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(alias=None, config=None)
        result = _get_account_alias(args)
        assert result == "default-alias"

    @patch("app.cli._lazy")
    @patch("app.cli._load_config")
    def test_alias_no_default_raises(self, mock_load, mock_lazy):
        mock_load.return_value = {"ssh": {}}
        mock_svc = MagicMock()
        mock_svc.ssh_account_service.get_default.return_value = None
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(alias=None, config=None)
        with pytest.raises(ValueError, match="未指定 SSH 账户别名"):
            _get_account_alias(args)


class TestCmdInit:
    @patch("app.cli._DEFAULT_CONFIG_PATH")
    def test_init_creates_config(self, mock_path, tmp_path, capsys):
        config_file = tmp_path / "settings.yaml"
        mock_path.exists.return_value = False
        mock_path.parent = tmp_path
        mock_path.__class__ = Path
        mock_path.__str__ = lambda s: str(config_file)
        mock_path.__fspath__ = lambda s: str(config_file)
        with patch("builtins.open", create=True):
            with patch("app.cli._lazy") as mock_lazy:
                mock_yaml = MagicMock()
                mock_lazy.return_value = mock_yaml
                _cmd_init(argparse.Namespace())
                mock_yaml.dump.assert_called_once()
        captured = capsys.readouterr()
        assert "配置文件已创建" in captured.out

    @patch("app.cli._DEFAULT_CONFIG_PATH")
    def test_init_existing_cancel(self, mock_path, capsys):
        mock_path.exists.return_value = True
        with patch("builtins.input", return_value="n"):
            _cmd_init(argparse.Namespace())
        captured = capsys.readouterr()
        assert "已取消" in captured.out

    @patch("app.cli._DEFAULT_CONFIG_PATH")
    def test_init_existing_overwrite(self, mock_path, tmp_path, capsys):
        config_file = tmp_path / "settings.yaml"
        mock_path.exists.return_value = True
        mock_path.parent = tmp_path
        mock_path.__class__ = Path
        mock_path.__str__ = lambda s: str(config_file)
        mock_path.__fspath__ = lambda s: str(config_file)
        with patch("builtins.input", return_value="y"):
            with patch("builtins.open", create=True):
                with patch("app.cli._lazy") as mock_lazy:
                    mock_yaml = MagicMock()
                    mock_lazy.return_value = mock_yaml
                    _cmd_init(argparse.Namespace())
                    mock_yaml.dump.assert_called_once()


class TestCmdRun:
    @patch("app.cli._cmd_start")
    @patch("app.cli._cmd_build")
    @patch("app.cli._cmd_setup")
    @patch("app.cli._cmd_sync")
    def test_cmd_run_calls_all(self, mock_sync, mock_setup, mock_build, mock_start, capsys):
        _cmd_run(argparse.Namespace())
        mock_sync.assert_called_once()
        mock_setup.assert_called_once()
        mock_build.assert_called_once()
        mock_start.assert_called_once()
        captured = capsys.readouterr()
        assert "完整流程执行完毕" in captured.out


class TestCmdSync:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_sync_no_remote_path(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {}}
        args = argparse.Namespace(config=None, local=None, remote=None, alias=None, force=False)
        with pytest.raises(SystemExit):
            _cmd_sync(args)

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_sync_exception(self, mock_lazy, mock_load, mock_alias):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}}
        mock_sync_svc = MagicMock()
        mock_sync_svc.sync_service.start_sync = MagicMock(side_effect=Exception("conn fail"))
        mock_sync_svc.sync_service.set_event_loop = MagicMock()
        mock_lazy.return_value = mock_sync_svc
        args = argparse.Namespace(config=None, local=None, remote=None, alias=None, force=False)
        with pytest.raises(SystemExit):
            _cmd_sync(args)


class TestCmdSetup:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_setup_docker_installed(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"environment": {}}
        mock_docker = MagicMock()
        mock_docker.docker_service.check_docker_installed.return_value = True
        mock_docker.docker_service.get_docker_version.return_value = "24.0.0"
        mock_lazy.return_value = mock_docker
        args = argparse.Namespace(config=None, alias=None)
        _cmd_setup(args)
        captured = capsys.readouterr()
        assert "Docker 已安装" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_setup_docker_not_installed_no_auto(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"environment": {"auto_install": False}}
        mock_docker = MagicMock()
        mock_docker.docker_service.check_docker_installed.return_value = False
        mock_lazy.return_value = mock_docker
        args = argparse.Namespace(config=None, alias=None)
        _cmd_setup(args)
        captured = capsys.readouterr()
        assert "Docker 未安装" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_setup_docker_auto_install(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"environment": {"auto_install": True}}
        mock_docker = MagicMock()
        mock_docker.docker_service.check_docker_installed.return_value = False
        mock_docker.docker_service.install_docker.return_value = "Docker installed"
        mock_lazy.return_value = mock_docker
        args = argparse.Namespace(config=None, alias=None)
        _cmd_setup(args)
        captured = capsys.readouterr()
        assert "Docker installed" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_setup_exception(self, mock_lazy, mock_load, mock_alias):
        mock_load.return_value = {"environment": {}}
        mock_docker = MagicMock()
        mock_docker.docker_service.check_docker_installed.side_effect = Exception("fail")
        mock_lazy.return_value = mock_docker
        args = argparse.Namespace(config=None, alias=None)
        with pytest.raises(SystemExit):
            _cmd_setup(args)


class TestCmdBuild:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_build_not_enabled(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {}, "build": {"enabled": False}}
        args = argparse.Namespace(config=None, alias=None, remote=None)
        _cmd_build(args)
        captured = capsys.readouterr()
        assert "编译功能未启用" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_build_success(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "build": {"enabled": True, "command": "make"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (0, "ok", "")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        _cmd_build(args)
        captured = capsys.readouterr()
        assert "编译成功" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_build_failure(self, mock_lazy, mock_load, mock_alias):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "build": {"enabled": True, "command": "make"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (1, "", "error output")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        with pytest.raises(SystemExit):
            _cmd_build(args)

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_build_exception(self, mock_lazy, mock_load, mock_alias):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "build": {"enabled": True, "command": "make"}}
        mock_svc = MagicMock()
        mock_svc.ssh_account_service.pool.get_connection.side_effect = Exception("conn fail")
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        with pytest.raises(SystemExit):
            _cmd_build(args)


class TestCmdStart:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_start_no_command(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {}, "run": {"remote_command": ""}}
        args = argparse.Namespace(config=None, alias=None, remote=None)
        _cmd_start(args)
        captured = capsys.readouterr()
        assert "未配置运行命令" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_start_success(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "run": {"mode": "remote", "remote_command": "python main.py"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (0, "started", "")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        _cmd_start(args)
        captured = capsys.readouterr()
        assert "启动成功" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_start_failure(self, mock_lazy, mock_load, mock_alias):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "run": {"mode": "remote", "remote_command": "python main.py"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (1, "", "fail")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        with pytest.raises(SystemExit):
            _cmd_start(args)


class TestCmdAccountList:
    @patch("app.cli._get_ssh_account_service")
    def test_account_list_empty(self, mock_svc, capsys):
        mock_svc.return_value.list_accounts.return_value = []
        _cmd_account_list(argparse.Namespace())
        captured = capsys.readouterr()
        assert "暂无 SSH 账户" in captured.out

    @patch("app.cli._get_ssh_account_service")
    def test_account_list_with_accounts(self, mock_svc, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        acct.host = "1.2.3.4"
        acct.port = 22
        acct.username = "root"
        acct.auth_type = "password"
        acct.is_default = True
        acct.group = "prod-group"
        mock_svc.return_value.list_accounts.return_value = [acct]
        _cmd_account_list(argparse.Namespace())
        captured = capsys.readouterr()
        assert "prod" in captured.out


class TestCmdAccountTest:
    @patch("app.cli._get_ssh_account_service")
    def test_account_test_success(self, mock_svc, capsys):
        mock_svc.return_value.test_account.return_value = (True, "OK")
        _cmd_account_test(argparse.Namespace(alias="prod"))
        captured = capsys.readouterr()
        assert "OK" in captured.out

    @patch("app.cli._get_ssh_account_service")
    def test_account_test_failure(self, mock_svc):
        mock_svc.return_value.test_account.return_value = (False, "refused")
        with pytest.raises(SystemExit):
            _cmd_account_test(argparse.Namespace(alias="prod"))

    @patch("app.cli._get_ssh_account_service")
    def test_account_test_value_error(self, mock_svc):
        mock_svc.return_value.test_account.side_effect = ValueError("not found")
        with pytest.raises(SystemExit):
            _cmd_account_test(argparse.Namespace(alias="prod"))


class TestCmdAccountRemove:
    @patch("app.cli._get_ssh_account_service")
    def test_account_remove_not_found(self, mock_svc):
        mock_svc.return_value.get_account.return_value = None
        with pytest.raises(SystemExit):
            _cmd_account_remove(argparse.Namespace(alias="nonexist"))

    @patch("app.cli._get_ssh_account_service")
    def test_account_remove_cancel(self, mock_svc, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        acct.username = "root"
        acct.host = "1.2.3.4"
        mock_svc.return_value.get_account.return_value = acct
        with patch("builtins.input", return_value="n"):
            _cmd_account_remove(argparse.Namespace(alias="prod"))
        captured = capsys.readouterr()
        assert "已取消" in captured.out

    @patch("app.cli._get_ssh_account_service")
    def test_account_remove_confirm(self, mock_svc, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        acct.username = "root"
        acct.host = "1.2.3.4"
        mock_svc.return_value.get_account.return_value = acct
        with patch("builtins.input", return_value="y"):
            _cmd_account_remove(argparse.Namespace(alias="prod"))
        mock_svc.return_value.delete_account.assert_called_once_with("prod")


class TestCmdAccountDefault:
    @patch("app.cli._get_ssh_account_service")
    def test_account_default_success(self, mock_svc, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        mock_svc.return_value.set_default.return_value = acct
        _cmd_account_default(argparse.Namespace(alias="prod"))
        captured = capsys.readouterr()
        assert "已设置" in captured.out

    @patch("app.cli._get_ssh_account_service")
    def test_account_default_value_error(self, mock_svc):
        mock_svc.return_value.set_default.side_effect = ValueError("not found")
        with pytest.raises(SystemExit):
            _cmd_account_default(argparse.Namespace(alias="prod"))


class TestCmdAccountEdit:
    @patch("app.cli._get_ssh_account_service")
    def test_account_edit_not_found(self, mock_svc):
        mock_svc.return_value.get_account.return_value = None
        with pytest.raises(SystemExit):
            _cmd_account_edit(argparse.Namespace(alias="nonexist"))

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_edit_success(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        acct.host = "1.2.3.4"
        acct.port = 22
        acct.username = "root"
        acct.auth_type = "password"
        mock_svc.return_value.get_account.return_value = acct
        mock_lazy.return_value.SSHAccountUpdate = MagicMock(return_value=MagicMock())
        inputs = iter(["", "", "", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_edit(argparse.Namespace(alias="prod"))
        mock_svc.return_value.update_account.assert_called_once()

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_edit_change_auth(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "prod"
        acct.host = "1.2.3.4"
        acct.port = 22
        acct.username = "root"
        acct.auth_type = "password"
        mock_svc.return_value.get_account.return_value = acct
        mock_lazy.return_value.SSHAccountUpdate = MagicMock(return_value=MagicMock())
        inputs = iter(["", "", "", "y", "2", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_edit(argparse.Namespace(alias="prod"))

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_edit_value_error(self, mock_svc, mock_lazy):
        acct = MagicMock()
        acct.alias = "prod"
        acct.host = "1.2.3.4"
        acct.port = 22
        acct.username = "root"
        acct.auth_type = "password"
        mock_svc.return_value.get_account.return_value = acct
        mock_lazy.return_value.SSHAccountUpdate = MagicMock(return_value=MagicMock())
        mock_svc.return_value.update_account.side_effect = ValueError("bad data")
        inputs = iter(["", "", "", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            with pytest.raises(SystemExit):
                _cmd_account_edit(argparse.Namespace(alias="prod"))


class TestCmdAccountAdd:
    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_add_password(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "new"
        mock_svc.return_value.create_account.return_value = acct
        mock_lazy.return_value.SSHAccountCreate = MagicMock(return_value=MagicMock())
        inputs = iter(["new", "1.2.3.4", "22", "root", "1", "pass", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_add(argparse.Namespace())
        captured = capsys.readouterr()
        assert "创建成功" in captured.out

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_add_key(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "new"
        mock_svc.return_value.create_account.return_value = acct
        mock_lazy.return_value.SSHAccountCreate = MagicMock(return_value=MagicMock())
        inputs = iter(["new", "1.2.3.4", "22", "root", "2", "/path/key", "", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_add(argparse.Namespace())

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_add_value_error(self, mock_svc, mock_lazy):
        mock_svc.return_value.create_account.side_effect = ValueError("dup")
        mock_lazy.return_value.SSHAccountCreate = MagicMock(return_value=MagicMock())
        inputs = iter(["new", "1.2.3.4", "22", "root", "1", "pass", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            with pytest.raises(SystemExit):
                _cmd_account_add(argparse.Namespace())


class TestCmdRemoteLs:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_ls_empty(self, mock_alias, mock_fms, capsys):
        mock_fms.return_value.list_directory.return_value = []
        _cmd_remote_ls(argparse.Namespace(path="/", alias=None, config=None))
        captured = capsys.readouterr()
        assert "空目录" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_ls_with_entries(self, mock_alias, mock_fms, capsys):
        entry = MagicMock()
        entry.name = "test.txt"
        entry.is_dir = False
        entry.size = 100
        entry.permissions = "rw-r--r--"
        entry.modify_time = "2025-01-01"
        mock_fms.return_value.list_directory.return_value = [entry]
        _cmd_remote_ls(argparse.Namespace(path="/", alias=None, config=None))
        captured = capsys.readouterr()
        assert "test.txt" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_ls_error(self, mock_alias, mock_fms):
        mock_fms.return_value.list_directory.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_ls(argparse.Namespace(path="/", alias=None, config=None))


class TestCmdRemoteCat:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_cat_success(self, mock_alias, mock_fms, capsys):
        mock_fms.return_value.read_file.return_value = "file content"
        _cmd_remote_cat(argparse.Namespace(path="/etc/hosts", alias=None, config=None))
        captured = capsys.readouterr()
        assert "file content" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_cat_error(self, mock_alias, mock_fms):
        mock_fms.return_value.read_file.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_cat(argparse.Namespace(path="/etc/hosts", alias=None, config=None))


class TestCmdRemoteUpload:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_upload_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_upload(argparse.Namespace(local="/local/file", remote="/remote/file", alias=None, config=None))
        captured = capsys.readouterr()
        assert "上传完成" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_upload_error(self, mock_alias, mock_fms):
        mock_fms.return_value.upload.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_upload(argparse.Namespace(local="/local/file", remote="/remote/file", alias=None, config=None))


class TestCmdRemoteDownload:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_download_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_download(argparse.Namespace(remote="/remote/file", local="/local/file", alias=None, config=None))
        captured = capsys.readouterr()
        assert "下载完成" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_download_no_local(self, mock_alias, mock_fms, capsys):
        _cmd_remote_download(argparse.Namespace(remote="/remote/file", local=None, alias=None, config=None))
        mock_fms.return_value.download.assert_called_once()

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_download_error(self, mock_alias, mock_fms):
        mock_fms.return_value.download.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_download(argparse.Namespace(remote="/remote/file", local=None, alias=None, config=None))


class TestCmdRemoteRm:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_rm_cancel(self, mock_alias, mock_fms, capsys):
        with patch("builtins.input", return_value="n"):
            _cmd_remote_rm(argparse.Namespace(path="/tmp/file", alias=None, config=None))
        captured = capsys.readouterr()
        assert "已取消" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_rm_confirm(self, mock_alias, mock_fms, capsys):
        with patch("builtins.input", return_value="y"):
            _cmd_remote_rm(argparse.Namespace(path="/tmp/file", alias=None, config=None))
        captured = capsys.readouterr()
        assert "已删除" in captured.out


class TestCmdRemoteMkdir:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_mkdir_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_mkdir(argparse.Namespace(path="/tmp/newdir", alias=None, config=None))
        captured = capsys.readouterr()
        assert "已创建" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_mkdir_error(self, mock_alias, mock_fms):
        mock_fms.return_value.create_directory.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_mkdir(argparse.Namespace(path="/tmp/newdir", alias=None, config=None))


class TestCmdRemoteMv:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_mv_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_mv(argparse.Namespace(src="/a", dst="/b", alias=None, config=None))
        captured = capsys.readouterr()
        assert "已移动" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_mv_error(self, mock_alias, mock_fms):
        mock_fms.return_value.rename.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_remote_mv(argparse.Namespace(src="/a", dst="/b", alias=None, config=None))


class TestCmdRemoteCp:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_cp_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_cp(argparse.Namespace(src="/a", dst="/b", alias=None, config=None))
        captured = capsys.readouterr()
        assert "已复制" in captured.out


class TestCmdRemoteChmod:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_chmod_success(self, mock_alias, mock_fms, capsys):
        _cmd_remote_chmod(argparse.Namespace(mode="755", path="/tmp/script.sh", alias=None, config=None))
        captured = capsys.readouterr()
        assert "权限已修改" in captured.out


class TestCmdRemoteExec:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_exec_success(self, mock_alias, mock_fms, capsys):
        mock_fms.return_value.exec_command.return_value = {"exit_code": 0, "stdout": "hello", "stderr": ""}
        _cmd_remote_exec(argparse.Namespace(command="echo hello", alias=None, config=None))
        captured = capsys.readouterr()
        assert "hello" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_exec_with_stderr(self, mock_alias, mock_fms, capsys):
        mock_fms.return_value.exec_command.return_value = {"exit_code": 1, "stdout": "", "stderr": "error msg"}
        _cmd_remote_exec(argparse.Namespace(command="bad cmd", alias=None, config=None))
        captured = capsys.readouterr()
        assert "error msg" in captured.err


class TestCmdRemoteFind:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_find_no_results(self, mock_alias, mock_fms, capsys):
        mock_fms.return_value.search.return_value = []
        _cmd_remote_find(argparse.Namespace(path="/", name="*.log", alias=None, config=None))
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_find_with_results(self, mock_alias, mock_fms, capsys):
        result = MagicMock()
        result.path = "/var/log/app.log"
        result.is_dir = False
        result.size = 1024
        result.permissions = "rw-r--r--"
        mock_fms.return_value.search.return_value = [result]
        _cmd_remote_find(argparse.Namespace(path="/var", name="*.log", alias=None, config=None))
        captured = capsys.readouterr()
        assert "app.log" in captured.out


class TestCmdDockerInfo:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_info_installed_running(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.check_docker_installed.return_value = True
        mock_ds.return_value.get_docker_version.return_value = "24.0"
        mock_ds.return_value.check_docker_running.return_value = True
        mock_ds.return_value.check_docker_permissions.return_value = {
            "in_docker_group": True,
            "has_sudo_access": False,
            "can_run_docker": True,
            "details": "ok",
        }
        _cmd_docker_info(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "24.0" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_info_not_installed(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.check_docker_installed.return_value = False
        mock_ds.return_value.check_docker_running.return_value = False
        mock_ds.return_value.check_docker_permissions.return_value = {
            "in_docker_group": False,
            "has_sudo_access": False,
            "can_run_docker": False,
            "details": "no docker",
        }
        _cmd_docker_info(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "Docker 未安装" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_info_error(self, mock_alias, mock_ds):
        mock_ds.return_value.check_docker_installed.side_effect = Exception("fail")
        with pytest.raises(SystemExit):
            _cmd_docker_info(argparse.Namespace(alias=None, config=None))


class TestCmdDockerPs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_ps_empty(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_containers.return_value = []
        _cmd_docker_ps(argparse.Namespace(alias=None, config=None, all=False))
        captured = capsys.readouterr()
        assert "无容器" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_ps_with_containers(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_containers.return_value = [
            {"ID": "abc123def456", "Names": "web", "Image": "nginx", "Status": "Up", "Ports": "80"}
        ]
        _cmd_docker_ps(argparse.Namespace(alias=None, config=None, all=False))
        captured = capsys.readouterr()
        assert "web" in captured.out


class TestCmdDockerStart:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_start_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.start_container.return_value = "started"
        _cmd_docker_start(argparse.Namespace(container_id="abc", alias=None, config=None))
        captured = capsys.readouterr()
        assert "started" in captured.out


class TestCmdDockerStop:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_stop_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.stop_container.return_value = "stopped"
        _cmd_docker_stop(argparse.Namespace(container_id="abc", timeout=None, alias=None, config=None))
        captured = capsys.readouterr()
        assert "stopped" in captured.out


class TestCmdDockerRestart:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_restart_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.restart_container.return_value = "restarted"
        _cmd_docker_restart(argparse.Namespace(container_id="abc", alias=None, config=None))


class TestCmdDockerKill:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_kill_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.kill_container.return_value = "killed"
        _cmd_docker_kill(argparse.Namespace(container_id="abc", alias=None, config=None))


class TestCmdDockerRm:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_rm_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.remove_container.return_value = "removed"
        _cmd_docker_rm(argparse.Namespace(container_id="abc", force=False, alias=None, config=None))


class TestCmdDockerLogs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_logs_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.get_container_logs.return_value = "log line 1\nlog line 2"
        _cmd_docker_logs(argparse.Namespace(container_id="abc", n=50, alias=None, config=None))
        captured = capsys.readouterr()
        assert "log line 1" in captured.out


class TestCmdDockerExec:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_exec_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.exec_in_container.return_value = (0, "output", "")
        _cmd_docker_exec(argparse.Namespace(container_id="abc", command="ls", alias=None, config=None))
        captured = capsys.readouterr()
        assert "output" in captured.out


class TestCmdDockerImages:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_images_empty(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_images.return_value = []
        _cmd_docker_images(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "无镜像" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_images_with_images(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_images.return_value = [
            {"Repository": "nginx", "Tag": "latest", "ID": "abc123", "Size": "100MB"}
        ]
        _cmd_docker_images(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "nginx" in captured.out


class TestCmdDockerPull:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_pull_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.pull_image.return_value = "pulled"
        _cmd_docker_pull(argparse.Namespace(image="nginx:latest", alias=None, config=None))
        captured = capsys.readouterr()
        assert "pulled" in captured.out


class TestCmdDockerRmi:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_rmi_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.remove_image.return_value = "removed"
        _cmd_docker_rmi(argparse.Namespace(image_id="abc123", alias=None, config=None))


class TestCmdDockerPrune:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_prune_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.prune_images.return_value = {"SpaceReclaimed": 1024}
        _cmd_docker_prune(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "1024" in captured.out


class TestCmdDockerBuild:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_build_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.build_image.return_value = "built"
        _cmd_docker_build(argparse.Namespace(tag="myapp:v1", path=".", dockerfile=None, alias=None, config=None))
        captured = capsys.readouterr()
        assert "构建完成" in captured.out


class TestCmdDockerNetworkLs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_network_ls_empty(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_networks.return_value = []
        _cmd_docker_network_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "无网络" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_network_ls_with_networks(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_networks.return_value = [
            {"ID": "net123", "Name": "bridge", "Driver": "bridge", "Scope": "local"}
        ]
        _cmd_docker_network_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "bridge" in captured.out


class TestCmdDockerVolumeLs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_volume_ls_empty(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_volumes.return_value = []
        _cmd_docker_volume_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "无卷" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_volume_ls_with_volumes(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_volumes.return_value = [
            {"Name": "mydata", "Driver": "local", "Mountpoint": "/var/lib/docker/volumes/mydata"}
        ]
        _cmd_docker_volume_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "mydata" in captured.out


class TestCmdComposeUp:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_up_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_up.return_value = "done"
        _cmd_compose_up(argparse.Namespace(project_path=".", detach=False, alias=None, config=None))
        captured = capsys.readouterr()
        assert "Compose 已启动" in captured.out


class TestCmdComposeDown:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_down_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_down.return_value = "done"
        _cmd_compose_down(argparse.Namespace(project_path=".", alias=None, config=None))
        captured = capsys.readouterr()
        assert "Compose 已停止" in captured.out


class TestCmdComposePs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_ps_empty(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_ps.return_value = []
        _cmd_compose_ps(argparse.Namespace(project_path=".", alias=None, config=None))
        captured = capsys.readouterr()
        assert "无服务" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_ps_with_services(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_ps.return_value = [
            {"Name": "web", "Status": "running", "Ports": "80"}
        ]
        _cmd_compose_ps(argparse.Namespace(project_path=".", alias=None, config=None))
        captured = capsys.readouterr()
        assert "web" in captured.out


class TestCmdComposeLogs:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_logs_success(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_logs.return_value = "log output"
        _cmd_compose_logs(argparse.Namespace(project_path=".", alias=None, config=None))
        captured = capsys.readouterr()
        assert "log output" in captured.out


class TestCmdSsh:
    @patch("app.cli._lazy")
    def test_ssh_sessions_empty(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_webssh.webssh_service.list_sessions.return_value = []
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd="sessions", alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "无活跃会话" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_sessions_with_sessions(self, mock_lazy, capsys):
        session = MagicMock()
        session.session_id = "abc123456789"
        session.account_alias = "prod"
        session.host = "1.2.3.4"
        session.username = "root"
        session.status = MagicMock(value="connected")
        mock_webssh = MagicMock()
        mock_webssh.webssh_service.list_sessions.return_value = [session]
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd="sessions", alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "abc1" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_close_not_found(self, mock_lazy):
        mock_webssh = MagicMock()
        mock_webssh.webssh_service.get_session.return_value = None
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd="close", session_id="nonexist", alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False)
        with pytest.raises(SystemExit):
            _cmd_ssh(args)

    @patch("app.cli._lazy")
    def test_ssh_close_success(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_webssh.webssh_service.get_session.return_value = MagicMock()
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd="close", session_id="sid123", alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "已关闭" in captured.out

    @patch("app.cli.webbrowser")
    @patch("app.cli._lazy")
    def test_ssh_browser_flag(self, mock_lazy, mock_browser):
        mock_webssh = MagicMock()
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=True, session_id=None)
        _cmd_ssh(args)
        mock_browser.open.assert_called_once()

    @patch("app.cli._lazy")
    def test_ssh_no_args(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "WebSSH 地址" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_with_alias(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = "sid123"
        mock_webssh.webssh_service.create_session.return_value = mock_session
        mock_lazy.return_value = mock_webssh
        mock_lazy.side_effect = [mock_webssh, MagicMock(WebSSHConnectRequest=MagicMock(return_value=MagicMock())), mock_webssh]
        args = argparse.Namespace(subcmd=None, alias="prod", host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        with patch("app.cli._lazy") as m:
            m.return_value = mock_webssh
            m.side_effect = None
            mock_webssh.WebSSHConnectRequest = MagicMock(return_value=MagicMock())
            _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "SSH 会话已建立" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_with_host_user(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = "sid456"
        mock_webssh.webssh_service.create_session.return_value = mock_session
        mock_webssh.WebSSHConnectRequest = MagicMock(return_value=MagicMock())
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias=None, host="1.2.3.4", port=22, user="root", password="pass", auth_type="password", browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "SSH 会话已建立" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_no_host_no_alias(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_webssh.WebSSHConnectRequest = MagicMock
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "WebSSH 地址" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_connection_error(self, mock_lazy):
        mock_webssh = MagicMock()
        mock_webssh.WebSSHConnectRequest = MagicMock(return_value=MagicMock())
        mock_webssh.webssh_service.create_session.side_effect = Exception("conn fail")
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias="prod", host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        with pytest.raises(SystemExit):
            _cmd_ssh(args)


class TestBuildParser:
    def test_build_parser_returns_parser(self):
        parser = _build_parser()
        assert parser.prog == "opsv-kits"

    def test_version_flag(self):
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_add_common_args(self):
        parser = argparse.ArgumentParser()
        _add_common_args(parser)
        args = parser.parse_args(["-c", "config.yaml", "-l", "/local", "-r", "/remote", "--alias", "prod"])
        assert args.config == "config.yaml"
        assert args.local == "/local"
        assert args.remote == "/remote"
        assert args.alias == "prod"

    def test_add_alias_arg(self):
        parser = argparse.ArgumentParser()
        _add_alias_arg(parser)
        args = parser.parse_args(["--alias", "prod"])
        assert args.alias == "prod"

    def test_add_config_arg(self):
        parser = argparse.ArgumentParser()
        _add_config_arg(parser)
        args = parser.parse_args(["-c", "config.yaml"])
        assert args.config == "config.yaml"


class TestMain:
    @patch("app.cli._enable_vt_mode")
    @patch("app.cli._build_parser")
    def test_main_no_command(self, mock_build, mock_vt, capsys):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        del mock_args.func
        mock_parser.parse_args.return_value = mock_args
        mock_build.return_value = mock_parser
        with pytest.raises(SystemExit):
            main()
        mock_parser.print_help.assert_called_once()

    @patch("app.cli._enable_vt_mode")
    @patch("app.cli._build_parser")
    def test_main_with_command(self, mock_build, mock_vt):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_build.return_value = mock_parser
        main()
        mock_args.func.assert_called_once_with(mock_args)

    @patch("app.cli._enable_vt_mode")
    @patch("app.cli._build_parser")
    def test_main_keyboard_interrupt(self, mock_build, mock_vt, capsys):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.func.side_effect = KeyboardInterrupt()
        mock_parser.parse_args.return_value = mock_args
        mock_build.return_value = mock_parser
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    @patch("app.cli._enable_vt_mode")
    @patch("app.cli._build_parser")
    def test_main_exception(self, mock_build, mock_vt, capsys):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.func.side_effect = RuntimeError("unexpected")
        mock_parser.parse_args.return_value = mock_args
        mock_build.return_value = mock_parser
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("app.cli._enable_vt_mode")
    @patch("app.cli._build_parser")
    def test_main_with_argv(self, mock_build, mock_vt):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_build.return_value = mock_parser
        main(["init"])
        mock_parser.parse_args.assert_called_once_with(["init"])
