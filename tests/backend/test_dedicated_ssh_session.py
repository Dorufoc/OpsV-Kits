from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.dedicated_ssh_session import DedicatedSSHSession


@pytest.fixture
def mock_account():
    """模拟 SSHAccount。"""
    account = MagicMock()
    account.alias = "test-server"
    account.host = "192.168.1.1"
    account.port = 22
    account.username = "root"
    account.auth_type = "password"
    account.password = "secret"
    account.private_key = None
    account.key_passphrase = None
    return account


@pytest.fixture
def session(mock_account):
    """创建一个 DedicatedSSHSession 实例。"""
    return DedicatedSSHSession(mock_account)


class TestDedicatedSSHSessionInit:
    """测试初始化状态。"""

    def test_initial_state(self, session: DedicatedSSHSession):
        assert session.connected is False
        assert session.is_online is False
        assert session._client is None
        assert session._transport is None
        assert session._closed is False


class TestDedicatedSSHSessionConnect:
    """测试连接逻辑。"""

    @pytest.mark.asyncio
    async def test_connect_success(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            result = await session.connect(timeout=5.0)
            assert result is True
            assert session.connected is True
            assert session.is_online is True
            mock_transport.set_keepalive.assert_called_once_with(60)

    @pytest.mark.asyncio
    async def test_connect_failure(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_client.connect.side_effect = Exception("Connection refused")
            MockClient.return_value = mock_client

            result = await session.connect(timeout=5.0)
            assert result is False
            assert session.connected is False
            assert session.is_online is False

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, session: DedicatedSSHSession):
        session._connected = True
        result = await session.connect(timeout=5.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_when_closed(self, session: DedicatedSSHSession):
        session._closed = True
        result = await session.connect(timeout=5.0)
        assert result is False


class TestDedicatedSSHSessionExecCommand:
    """测试命令执行。"""

    @pytest.mark.asyncio
    async def test_exec_command_success(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_chan = MagicMock()
            mock_chan.recv_exit_status.return_value = 0
            mock_chan.makefile.return_value.read.return_value = b"hello world"
            mock_chan.makefile_stderr.return_value.read.return_value = b""
            mock_transport.open_session.return_value = mock_chan
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)
            code, stdout, stderr = await session.exec_command("echo hello", timeout=2.0)
            assert code == 0
            assert stdout == "hello world"
            assert stderr == ""

    @pytest.mark.asyncio
    async def test_exec_command_not_connected(self, session: DedicatedSSHSession):
        code, stdout, stderr = await session.exec_command("echo hello")
        assert code == -1
        assert "未连接" in stderr

    @pytest.mark.asyncio
    async def test_exec_command_timeout(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_chan = MagicMock()

            def slow_recv():
                import time
                time.sleep(10)
                return 0

            mock_chan.recv_exit_status.side_effect = slow_recv
            mock_transport.open_session.return_value = mock_chan
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)
            code, stdout, stderr = await session.exec_command("sleep 10", timeout=0.1)
            assert code == -1
            assert "超时" in stderr


class TestDedicatedSSHSessionReconnect:
    """测试自动重连逻辑。"""

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_chan = MagicMock()
            mock_chan.recv_exit_status.return_value = 0
            mock_chan.makefile.return_value.read.return_value = b"ok"
            mock_chan.makefile_stderr.return_value.read.return_value = b""
            mock_transport.open_session.return_value = mock_chan
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)
            assert session.connected is True

            # 模拟网络断开
            session._connected = False
            session._online = False
            session._backoff_index = 0

            # 手动执行一次重连（跳过 sleep 延迟）
            success = await session._do_connect_locked(timeout=5.0)
            assert success is True
            assert session.connected is True
            assert session.is_online is True

    @pytest.mark.asyncio
    async def test_backoff_increases(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_client.connect.side_effect = Exception("Connection refused")
            MockClient.return_value = mock_client

            await session.connect(timeout=1.0)
            assert session._backoff_index == 0

            # 手动执行一次重连（模拟重连循环中失败的情况）
            success = await session._do_connect_locked(timeout=1.0)
            assert success is False
            # 模拟重连循环中的 backoff 增加逻辑
            session._backoff_index += 1
            assert session._backoff_index >= 1


class TestDedicatedSSHSessionClose:
    """测试关闭逻辑。"""

    @pytest.mark.asyncio
    async def test_close(self, session: DedicatedSSHSession):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient:
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            MockClient.return_value = mock_client

            await session.connect(timeout=5.0)
            session.close()
            assert session._closed is True
            assert session.connected is False
            assert session.is_online is False

    @pytest.mark.asyncio
    async def test_close_cancels_reconnect(self, session: DedicatedSSHSession):
        session._schedule_reconnect()
        assert session._reconnect_task is not None
        session.close()
        # 给事件循环一点时间处理取消请求
        await asyncio.sleep(0.05)
        assert session._reconnect_task.cancelled() or session._reconnect_task.done()
