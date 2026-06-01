from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.permission_checker import FilePermissions, PermissionChecker, UserInfo


@pytest.fixture
def mock_manager():
    return MagicMock()


@pytest.fixture
def checker(mock_manager):
    return PermissionChecker(mock_manager)


def _setup_exec(manager, code=0, stdout="", stderr=""):
    if isinstance(stdout, str):
        stdout_bytes = stdout.encode("utf-8")
    else:
        stdout_bytes = stdout
    if isinstance(stderr, str):
        stderr_bytes = stderr.encode("utf-8")
    else:
        stderr_bytes = stderr
    manager.exec_command.return_value = (code, stdout_bytes, stderr_bytes)


class TestExec:
    def test_exec_string_output(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "hello", "world")
        code, stdout, stderr = checker._exec("test")
        assert code == 0
        assert stdout == "hello"
        assert stderr == "world"

    def test_exec_bytes_stdout(self, checker, mock_manager):
        mock_manager.exec_command.return_value = (0, b"bytes_out", b"bytes_err")
        code, stdout, stderr = checker._exec("test")
        assert stdout == "bytes_out"
        assert stderr == "bytes_err"

    def test_exec_mixed_types(self, checker, mock_manager):
        mock_manager.exec_command.return_value = (1, b"bytes_out", "str_err")
        code, stdout, stderr = checker._exec("test")
        assert code == 1
        assert stdout == "bytes_out"

    def test_exec_custom_timeout(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        checker._exec("test", timeout=30.0)
        mock_manager.exec_command.assert_called_once_with("test", timeout=30.0)

    def test_exec_bytes_decode_replace(self, checker, mock_manager):
        mock_manager.exec_command.return_value = (0, b"\xff\xfe", b"\xff\xfe")
        code, stdout, stderr = checker._exec("test")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)


class TestShellPath:
    def test_home_dir(self):
        result = PermissionChecker._shell_path("~")
        assert result == "$HOME"

    def test_home_with_subpath(self):
        result = PermissionChecker._shell_path("~/Documents")
        assert result == "$HOME/Documents"

    def test_home_with_slash_path(self):
        result = PermissionChecker._shell_path("~/a/b/c")
        assert "$HOME" in result

    def test_regular_path(self):
        result = PermissionChecker._shell_path("/tmp/test file.txt")
        assert "test" in result

    def test_path_with_spaces(self):
        result = PermissionChecker._shell_path("/path/with spaces/file")
        assert "spaces" in result

    def test_path_with_special_chars(self):
        result = PermissionChecker._shell_path("/tmp/file;rm -rf")
        assert ";" not in result or "'" in result or '"' in result


class TestCheckReadAccess:
    def test_readable(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        assert checker.check_read_access("/etc/hosts") is True

    def test_not_readable(self, checker, mock_manager):
        _setup_exec(mock_manager, 1, "", "")
        assert checker.check_read_access("/root/secret") is False


class TestCheckExists:
    def test_exists(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        assert checker.check_exists("/etc/hosts") is True

    def test_not_exists(self, checker, mock_manager):
        _setup_exec(mock_manager, 1, "", "")
        assert checker.check_exists("/nonexistent") is False


class TestCheckWriteAccess:
    def test_writable(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        assert checker.check_write_access("/tmp") is True

    def test_not_writable(self, checker, mock_manager):
        _setup_exec(mock_manager, 1, "", "")
        assert checker.check_write_access("/etc/hosts") is False


class TestCheckExecuteAccess:
    def test_executable(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        assert checker.check_execute_access("/usr/bin/ls") is True

    def test_not_executable(self, checker, mock_manager):
        _setup_exec(mock_manager, 1, "", "")
        assert checker.check_execute_access("/etc/hosts") is False


class TestCheckSudoAccess:
    def test_has_sudo(self, checker, mock_manager):
        _setup_exec(mock_manager, 0, "", "")
        assert checker.check_sudo_access() is True

    def test_no_sudo(self, checker, mock_manager):
        _setup_exec(mock_manager, 1, "", "")
        assert checker.check_sudo_access() is False


class TestGetCurrentUser:
    def test_id_command_success(self, checker, mock_manager):
        id_output = "uid=1000(testuser) gid=1000(testgroup) groups=1000(testgroup),27(sudo)"
        mock_manager.exec_command.side_effect = [
            (0, id_output.encode(), b""),
            (0, b"/home/testuser", b""),
            (0, b"/bin/zsh", b""),
        ]
        info = checker.get_current_user()
        assert info.username == "testuser"
        assert info.uid == 1000
        assert info.gid == 1000
        assert len(info.groups) >= 1
        assert info.home == "/home/testuser"
        assert info.shell == "/bin/zsh"
        assert info.is_root is False

    def test_id_command_root(self, checker, mock_manager):
        id_output = "uid=0(root) gid=0(root) groups=0(root)"
        mock_manager.exec_command.side_effect = [
            (0, id_output.encode(), b""),
            (0, b"/root", b""),
            (0, b"/bin/bash", b""),
        ]
        info = checker.get_current_user()
        assert info.username == "root"
        assert info.uid == 0
        assert info.is_root is True

    def test_id_command_fallback_whoami(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (1, b"", b"error"),
            (0, b"fallback_user", b""),
        ]
        info = checker.get_current_user()
        assert info.username == "fallback_user"
        assert info.uid == 0
        assert info.is_root is False

    def test_id_command_fallback_unknown(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (1, b"", b"error"),
            (1, b"", b"error"),
        ]
        info = checker.get_current_user()
        assert info.username == "unknown"

    def test_id_command_empty_home(self, checker, mock_manager):
        id_output = "uid=1000(myuser) gid=1000(mygroup) groups=1000(mygroup)"
        mock_manager.exec_command.side_effect = [
            (0, id_output.encode(), b""),
            (0, b"", b""),
            (0, b"/bin/bash", b""),
        ]
        info = checker.get_current_user()
        assert info.home == "/home/myuser"

    def test_id_command_empty_shell(self, checker, mock_manager):
        id_output = "uid=1000(myuser) gid=1000(mygroup) groups=1000(mygroup)"
        mock_manager.exec_command.side_effect = [
            (0, id_output.encode(), b""),
            (0, b"/home/myuser", b""),
            (0, b"", b""),
        ]
        info = checker.get_current_user()
        assert info.shell == "/bin/bash"

    def test_id_command_whoami_root(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (1, b"", b"error"),
            (0, b"root", b""),
        ]
        info = checker.get_current_user()
        assert info.username == "root"
        assert info.is_root is True


class TestParseIdOutput:
    def test_standard_format(self, checker):
        output = "uid=1000(testuser) gid=1000(testgroup) groups=1000(testgroup),27(sudo),108(docker)"
        info = checker._parse_id_output(output)
        assert info.username == "testuser"
        assert info.uid == 1000
        assert info.gid == 1000
        assert len(info.groups) >= 1
        assert info.is_root is False

    def test_root_user(self, checker):
        output = "uid=0(root) gid=0(root) groups=0(root)"
        info = checker._parse_id_output(output)
        assert info.username == "root"
        assert info.is_root is True

    def test_uid_zero_non_root_name(self, checker):
        output = "uid=0(admin) gid=0(root) groups=0(root)"
        info = checker._parse_id_output(output)
        assert info.is_root is True

    def test_unparseable_output(self, checker):
        output = "some random output"
        info = checker._parse_id_output(output)
        assert info.username == "some random output"
        assert info.uid == 0
        assert info.gid == 0
        assert info.groups == []

    def test_empty_output(self, checker):
        info = checker._parse_id_output("")
        assert info.username == ""

    def test_no_groups(self, checker):
        output = "uid=1000(user) gid=1000(group) "
        info = checker._parse_id_output(output)
        assert info.username == "user"
        assert info.uid == 1000
        assert info.gid == 1000


class TestGetFilePermissions:
    def test_existing_file_stat_linux(self, checker, mock_manager):
        stat_output = "644 -rw-r--r-- root root"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, stat_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/etc/hosts")
        assert perms.exists is True
        assert perms.readable is True
        assert perms.writable is True
        assert perms.executable is True
        assert perms.permission_mode == 0o644
        assert perms.owner == "root"
        assert perms.group == "root"
        assert perms.current_user == "testuser"

    def test_nonexistent_file(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (1, b"", b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/nonexistent")
        assert perms.exists is False
        assert perms.readable is False
        assert perms.writable is False
        assert perms.executable is False
        assert perms.permission_str == ""
        assert perms.owner == ""
        assert perms.group == ""

    def test_stat_fallback_ls(self, checker, mock_manager):
        ls_output = "-rw-r--r-- 1 root root 1234 Jan 01 00:00 /etc/hosts"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (1, b"", b""),
            (0, ls_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/etc/hosts")
        assert perms.exists is True
        assert perms.permission_str == "-rw-r--r--"
        assert perms.owner == "root"
        assert perms.group == "root"

    def test_stat_macos_format(self, checker, mock_manager):
        stat_output = "-rw-r--r-- 0 0"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, stat_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/etc/hosts")
        assert perms.exists is True
        assert perms.permission_str == "-rw-r--r--"
        assert perms.owner == "0"
        assert perms.group == "0"

    def test_stat_non_numeric_mode(self, checker, mock_manager):
        stat_output = "abc -rw-r--r-- owner group"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, stat_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/etc/hosts")
        assert perms.exists is True
        assert perms.permission_mode == 0

    def test_stat_and_ls_both_fail(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (1, b"", b""),
            (1, b"", b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/some/file")
        assert perms.exists is True
        assert perms.permission_str == ""
        assert perms.owner == ""
        assert perms.group == ""

    def test_ls_output_too_short(self, checker, mock_manager):
        ls_output = "short"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (1, b"", b""),
            (0, ls_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/some/file")
        assert perms.exists is True
        assert perms.permission_str == ""

    def test_stat_three_parts(self, checker, mock_manager):
        stat_output = "-rwxr-xr-x owner group"
        mock_manager.exec_command.side_effect = [
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, b"", b""),
            (0, stat_output.encode(), b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("/usr/bin/ls")
        assert perms.exists is True
        assert perms.permission_str == "-rwxr-xr-x"
        assert perms.owner == "owner"
        assert perms.group == "group"

    def test_home_dir_path(self, checker, mock_manager):
        mock_manager.exec_command.side_effect = [
            (1, b"", b""),
            (0, b"testuser", b""),
        ]
        perms = checker.get_file_permissions("~/Documents")
        assert perms.exists is False
        call_args = mock_manager.exec_command.call_args_list[0]
        cmd = call_args[0][0]
        assert "$HOME" in cmd


class TestUserInfo:
    def test_defaults(self):
        info = UserInfo(username="test", uid=1000, gid=1000)
        assert info.username == "test"
        assert info.groups == []
        assert info.home == ""
        assert info.shell == ""
        assert info.is_root is False

    def test_root_user(self):
        info = UserInfo(username="root", uid=0, gid=0, is_root=True)
        assert info.is_root is True


class TestFilePermissions:
    def test_all_fields(self):
        perms = FilePermissions(
            path="/test", exists=True, readable=True, writable=True,
            executable=False, permission_str="-rw-r--r--", permission_mode=0o644,
            owner="root", group="root", current_user="testuser",
        )
        assert perms.path == "/test"
        assert perms.exists is True
        assert perms.permission_mode == 0o644
