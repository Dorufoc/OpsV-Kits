from unittest.mock import MagicMock, patch

import pytest


class TestResolveRemotePath:
    def test_non_tilde_path_returned_as_is(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        result = resolve_remote_path(ssh, "/absolute/path")
        assert result == "/absolute/path"

    def test_tilde_expanded_with_home(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        stdout = MagicMock()
        stdout.read.return_value = b"/home/testuser\n"
        ssh.exec_command.return_value = (None, stdout, None)

        result = resolve_remote_path(ssh, "~/projects", username="testuser")
        assert result == "/home/testuser/projects"

    def test_tilde_expanded_fallback_on_exception(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        ssh.exec_command.side_effect = Exception("connection error")

        result = resolve_remote_path(ssh, "~/projects", username="testuser")
        assert result == "/home/testuser/projects"

    def test_tilde_expanded_fallback_no_username(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        ssh.exec_command.side_effect = Exception("connection error")

        result = resolve_remote_path(ssh, "~/projects")
        assert result == "/root/projects"

    def test_tilde_expanded_empty_home(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        stdout = MagicMock()
        stdout.read.return_value = b"\n"
        ssh.exec_command.return_value = (None, stdout, None)

        result = resolve_remote_path(ssh, "~/projects", username="myuser")
        assert result == "/home/myuser/projects"

    def test_tilde_only(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        stdout = MagicMock()
        stdout.read.return_value = b"/home/user\n"
        ssh.exec_command.return_value = (None, stdout, None)

        result = resolve_remote_path(ssh, "~", username="user")
        assert result == "/home/user"

    def test_tilde_with_username_root(self):
        from app.core.ssh_utils import resolve_remote_path

        ssh = MagicMock()
        ssh.exec_command.side_effect = Exception("fail")

        result = resolve_remote_path(ssh, "~/dir", username="root")
        assert result == "/home/root/dir"
