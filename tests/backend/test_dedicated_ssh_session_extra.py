from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import paramiko
import pytest

from app.core.dedicated_ssh_session import DedicatedSSHSession


@pytest.fixture
def mock_account():
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
    return DedicatedSSHSession(mock_account)


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_success(self, session, mock_account):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient, \
             patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_client.exec_command.return_value = (None, MagicMock(read=lambda: b"UTF-8\n"), None)
            MockClient.return_value = mock_client

            result = await session.connect(timeout=5.0)
            assert result is True
            assert session.connected is True
            assert session.is_online is True
            assert session._backoff_index == 0

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, session):
        session._connected = True
        result = await session.connect(timeout=5.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_already_closed(self, session):
        session._closed = True
        result = await session.connect(timeout=5.0)
        assert result is False


class TestDoConnectLocked:
    @pytest.mark.asyncio
    async def test_connect_failure_cleans_up(self, session, mock_account):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient, \
             patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.connect.side_effect = Exception("connection refused")

            result = await session._do_connect_locked(timeout=5.0)
            assert result is False
            assert session._connected is False
            assert session._online is False

    @pytest.mark.asyncio
    async def test_connect_success_sets_state(self, session, mock_account):
        with patch("app.core.dedicated_ssh_session.paramiko.SSHClient") as MockClient, \
             patch("app.core.dedicated_ssh_session._ensure_known_hosts_dir"):
            mock_client = MagicMock()
            mock_transport = MagicMock()
            mock_client.get_transport.return_value = mock_transport
            mock_client.exec_command.return_value = (None, MagicMock(read=lambda: b"UTF-8\n"), None)
            MockClient.return_value = mock_client

            result = await session._do_connect_locked(timeout=5.0)
            assert result is True
            assert session._connected is True
            assert session._online is True
            assert session._backoff_index == 0


class TestReconnectLoop:
    @pytest.mark.asyncio
    async def test_reconnect_loop_connects_successfully(self, session):
        with patch.object(session, "_do_connect_locked", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            session._closed = False
            session._connected = False
            session._backoff_index = 0

            with patch("app.core.dedicated_ssh_session.asyncio.sleep", new_callable=AsyncMock):
                await session._reconnect_loop()
            assert session._online is True

    @pytest.mark.asyncio
    async def test_reconnect_loop_failure_increments_backoff(self, session):
        call_count = [0]
        async def mock_connect_fn(timeout=15.0):
            call_count[0] += 1
            if call_count[0] == 1:
                return False
            return True

        with patch.object(session, "_do_connect_locked", side_effect=mock_connect_fn):
            session._closed = False
            session._connected = False
            session._backoff_index = 0

            with patch("app.core.dedicated_ssh_session.asyncio.sleep", new_callable=AsyncMock):
                await session._reconnect_loop()
            assert session._backoff_index == 0
            assert session._online is True

    @pytest.mark.asyncio
    async def test_reconnect_loop_stops_when_closed(self, session):
        session._closed = True
        session._connected = False
        await session._reconnect_loop()
        assert session._connected is False

    @pytest.mark.asyncio
    async def test_reconnect_loop_stops_when_connected(self, session):
        session._closed = False
        session._connected = True
        await session._reconnect_loop()


class TestCloseWithReconnectTask:
    def test_close_cancels_active_reconnect_task(self, session):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        session._reconnect_task = mock_task
        session._transport = MagicMock()
        session._client = MagicMock()
        session.close()
        mock_task.cancel.assert_called_once()
        assert session._closed is True
        assert session._connected is False
        assert session._online is False

    def test_close_with_no_reconnect_task(self, session):
        session._reconnect_task = None
        session._transport = MagicMock()
        session._client = MagicMock()
        session.close()
        assert session._closed is True

    def test_close_with_completed_reconnect_task(self, session):
        mock_task = MagicMock()
        mock_task.done.return_value = True
        session._reconnect_task = mock_task
        session._transport = MagicMock()
        session._client = MagicMock()
        session.close()
        mock_task.cancel.assert_not_called()
