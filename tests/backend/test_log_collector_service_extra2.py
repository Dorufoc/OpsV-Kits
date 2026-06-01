from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.log_collector_service import LogCollectorService, _UdpLogProtocol


@pytest.fixture
def service():
    return LogCollectorService()


class TestReadChannelData:
    def test_exception_returns_none(self, service):
        mock_chan = MagicMock()
        mock_chan.recv_ready.side_effect = Exception("channel broken")
        result = service._read_channel_data(mock_chan)
        assert result is None

    def test_not_ready_returns_empty(self, service):
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        result = service._read_channel_data(mock_chan)
        assert result == b""


class TestSystemLogSleepPath:
    @pytest.mark.asyncio
    async def test_system_log_empty_data_sleep(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = 0

        async def fake_exec_in_executor(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b""
            service._sources[source_id]["status"] = "stopped"
            return None

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc, \
             patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            with patch("asyncio.get_event_loop") as mock_loop, \
                 patch("asyncio.sleep", new_callable=AsyncMock):
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")


class TestSystemLogChanCloseException:
    @pytest.mark.asyncio
    async def test_chan_close_exception(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.close.side_effect = Exception("close error")
        mock_chan.exit_status_ready.return_value = True
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        async def fake_exec_in_executor(*args, **kwargs):
            return b""

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")


class TestSystemLogStatusNotRunning:
    @pytest.mark.asyncio
    async def test_status_not_running_after_loop(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.exit_status_ready.return_value = True
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        async def fake_exec_in_executor(*args, **kwargs):
            return b""

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")


class TestDockerLogSleepPath:
    @pytest.mark.asyncio
    async def test_docker_log_empty_data_sleep(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = 0

        async def fake_exec_in_executor(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b""
            service._sources[source_id]["status"] = "stopped"
            return None

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc, \
             patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            mock_parser.parse.return_value = {"level": "INFO", "message": "docker", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            with patch("asyncio.get_event_loop") as mock_loop, \
                 patch("asyncio.sleep", new_callable=AsyncMock):
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_docker_log_collection(source_id, "s1", "nginx")


class TestDockerLogChanCloseException:
    @pytest.mark.asyncio
    async def test_chan_close_exception(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.close.side_effect = Exception("close error")
        mock_chan.exit_status_ready.return_value = True
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        async def fake_exec_in_executor(*args, **kwargs):
            return b""

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_docker_log_collection(source_id, "s1", "nginx")


class TestStartTcpServer:
    @pytest.mark.asyncio
    async def test_tcp_server_handle_client(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        mock_reader.readline.side_effect = [b"test log line\n", b""]

        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()

            with patch("asyncio.start_server") as mock_start_server:
                mock_server = AsyncMock()
                mock_start_server.return_value = mock_server
                await service.start_tcp_server("0.0.0.0", 9514)
                mock_start_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_tcp_server_writer_close_exception(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        mock_reader.readline.side_effect = [b"test line\n", b""]
        mock_writer.wait_closed = AsyncMock(side_effect=Exception("close error"))

        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()

            with patch("asyncio.start_server") as mock_start_server:
                mock_server = AsyncMock()
                mock_start_server.return_value = mock_server
                await service.start_tcp_server("0.0.0.0", 9514)

    @pytest.mark.asyncio
    async def test_tcp_server_reader_exception(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        mock_reader.readline.side_effect = Exception("read error")

        with patch("asyncio.start_server") as mock_start_server:
            mock_server = AsyncMock()
            mock_start_server.return_value = mock_server
            await service.start_tcp_server("0.0.0.0", 9514)


class TestFileWatcherOnModified:
    @pytest.mark.asyncio
    async def test_file_handler_on_modified_reads_new_data(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("initial line\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert, \
             patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()

            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_file_handler_inode_changed(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("initial\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            service._file_offsets[source_id] = (99999, 100)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_file_handler_file_truncated(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("initial\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            stat = test_file.stat()
            service._file_offsets[source_id] = (stat.st_ino, stat.st_size + 1000)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_file_handler_no_stored_offset(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("data\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            service._file_offsets.pop(source_id, None)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_file_handler_nonexistent_file(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/nonexistent/file.log"})
        with patch("app.services.log_collector_service.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path
            await service.start_file_watcher(source_id, "/nonexistent/file.log")
        source = service.get_source(source_id)
        assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_file_watcher_no_more_handlers_stops_observer(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("data\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

            mock_observer.stop.assert_called_once()


class TestSystemLogCancelledError:
    @pytest.mark.asyncio
    async def test_system_log_cancelled(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_svc.get_account.side_effect = asyncio.CancelledError()
            await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")
        source = service.get_source(source_id)
        assert source["status"] == "stopped"


class TestDockerLogCancelledError:
    @pytest.mark.asyncio
    async def test_docker_log_cancelled(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_svc.get_account.side_effect = asyncio.CancelledError()
            await service.start_docker_log_collection(source_id, "s1", "nginx")
        source = service.get_source(source_id)
        assert source["status"] == "stopped"
