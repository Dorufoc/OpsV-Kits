from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import paramiko
import pytest

from app.core.ssh_client import SSHClientManager, _ensure_known_hosts_dir
from app.models.ssh_account import SSHAccount


def _make_account(**kwargs):
    defaults = {
        "alias": "test",
        "host": "192.168.1.1",
        "port": 22,
        "username": "root",
        "auth_type": "password",
        "password": "secret",
    }
    defaults.update(kwargs)
    return SSHAccount(**defaults)


@pytest.fixture
def account():
    return _make_account()


@pytest.fixture
def manager(account):
    return SSHClientManager(account)


class TestStartKeepalive:
    @patch("app.core.ssh_client.paramiko.SSHClient")
    @patch("app.core.ssh_client._ensure_known_hosts_dir")
    def test_start_keepalive_creates_thread(self, mock_ensure, mock_ssh_cls, manager):
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client
        mock_transport = MagicMock()
        mock_client.get_transport.return_value = mock_transport
        stdout = MagicMock()
        stdout.read.return_value = b"UTF-8\n"
        mock_client.exec_command.return_value = (None, stdout, None)

        with patch("app.core.ssh_client.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            manager.connect(timeout=10.0)
            mock_thread.assert_called_once()
            assert mock_thread.call_args[1]["daemon"] is True


class TestExecCommandWithEnvironment:
    def test_exec_command_with_env_vars(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        mock_transport = MagicMock()
        mock_transport.open_session.return_value = mock_chan
        manager._client.get_transport.return_value = mock_transport

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_command(
                "ls", environment={"JAVA_HOME": "/usr/lib/jvm/java-21", "PATH": "/usr/bin"}
            )
            assert code == 0
            assert mock_chan.set_environment_variable.call_count == 2

    def test_exec_command_without_environment(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        mock_transport = MagicMock()
        mock_transport.open_session.return_value = mock_chan
        manager._client.get_transport.return_value = mock_transport

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_command("ls")
            assert code == 0
            mock_chan.set_environment_variable.assert_not_called()


class TestExecWithPtyWithEnvironment:
    def test_exec_with_pty_with_env_vars(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        manager._transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        manager._transport.open_session.return_value = mock_chan

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_with_pty(
                "top", environment={"TERM": "xterm-256color", "LANG": "en_US.UTF-8"}
            )
            assert code == 0
            assert mock_chan.set_environment_variable.call_count == 2

    def test_exec_with_pty_without_environment(self, manager):
        manager._connected = True
        manager._client = MagicMock()
        manager._transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_exit_status.return_value = 0
        mock_chan.makefile.return_value = MagicMock()
        mock_chan.makefile_stderr.return_value = MagicMock()
        manager._transport.open_session.return_value = mock_chan

        with patch("app.core.ssh_client._read_channel", side_effect=["output", ""]):
            code, stdout, stderr = manager.exec_with_pty("top")
            assert code == 0
            mock_chan.set_environment_variable.assert_not_called()


class TestEnsureKnownHostsDirWindows:
    def test_ensure_known_hosts_dir_on_windows(self):
        with patch("app.core.ssh_client.os") as mock_os, \
             patch("app.core.ssh_client._KNOWN_HOSTS_PATH") as mock_path:
            mock_os.name = "nt"
            mock_os.chmod = MagicMock()
            mock_parent = MagicMock()
            mock_path.parent = mock_parent
            mock_path.exists.return_value = True
            mock_path.__str__ = lambda self: "C:\\Users\\test\\.ssh\\known_hosts"
            _ensure_known_hosts_dir()
            mock_os.chmod.assert_called_once()
            call_args = mock_os.chmod.call_args[0]
            assert stat.S_IRUSR | stat.S_IWUSR in [call_args[1]] if len(call_args) > 1 else [True]

    def test_ensure_known_hosts_dir_on_linux(self):
        with patch("app.core.ssh_client.os") as mock_os, \
             patch("app.core.ssh_client._KNOWN_HOSTS_PATH") as mock_path:
            mock_os.name = "posix"
            mock_os.chmod = MagicMock()
            mock_parent = MagicMock()
            mock_path.parent = mock_parent
            mock_path.exists.return_value = True
            mock_path.__str__ = lambda self: "/home/user/.ssh/known_hosts"
            _ensure_known_hosts_dir()
            mock_os.chmod.assert_called_once()
            call_args = mock_os.chmod.call_args[0]
            assert call_args[1] == 0o600

    def test_ensure_known_hosts_dir_creates_file(self):
        with patch("app.core.ssh_client.os") as mock_os, \
             patch("app.core.ssh_client._KNOWN_HOSTS_PATH") as mock_path:
            mock_os.name = "nt"
            mock_os.chmod = MagicMock()
            mock_parent = MagicMock()
            mock_path.parent = mock_parent
            mock_path.exists.return_value = False
            _ensure_known_hosts_dir()
            mock_path.touch.assert_called_once_with(exist_ok=True)
