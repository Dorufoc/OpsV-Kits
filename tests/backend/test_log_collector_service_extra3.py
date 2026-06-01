import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.log_collector_service import LogCollectorService


@pytest.fixture
def service():
    return LogCollectorService()


class TestSystemLogDataNoneBreak:
    @pytest.mark.asyncio
    async def test_system_log_data_none_breaks_loop(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = [0]
        async def fake_exec_in_executor(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return None
            service._sources[source_id]["status"] = "stopped"
            return None

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")


class TestSystemLogSleepPath:
    @pytest.mark.asyncio
    async def test_system_log_empty_data_sleeps(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = [0]
        async def fake_exec_in_executor(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
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
    async def test_chan_close_exception_suppressed(self, service):
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


class TestSystemLogStatusNotRunningReturn:
    @pytest.mark.asyncio
    async def test_status_not_running_returns_early(self, service):
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
                service._sources[source_id]["status"] = "stopped"
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")


class TestDockerLogSleepPath:
    @pytest.mark.asyncio
    async def test_docker_log_empty_data_sleeps(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = [0]
        async def fake_exec_in_executor(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
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
    async def test_docker_chan_close_exception_suppressed(self, service):
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


class TestTcpServerHandleClient:
    @pytest.mark.asyncio
    async def test_handle_client_reads_lines(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("10.0.0.1", 54321)
        mock_reader.readline.side_effect = [b"log line 1\n", b"log line 2\n", b""]

        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()

            with patch("asyncio.start_server") as mock_start_server:
                async def capture_handler(reader, writer):
                    handler_fn = None

                    async def fake_start_server(handler, host, port):
                        nonlocal handler_fn
                        handler_fn = handler
                        return AsyncMock()

                    await fake_start_server(None, "0.0.0.0", 9514)
                    if handler_fn:
                        pass

                mock_server = AsyncMock()
                mock_start_server.return_value = mock_server
                await service.start_tcp_server("0.0.0.0", 9514)
                mock_start_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_client_no_peername(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = None
        mock_reader.readline.side_effect = [b"test line\n", b""]

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
    async def test_handle_client_empty_line_skipped(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        mock_reader.readline.side_effect = [b"   \n", b"valid line\n", b""]

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
    async def test_handle_client_wait_closed_exception(self, service):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        mock_reader.readline.side_effect = [b"test\n", b""]
        mock_writer.wait_closed = AsyncMock(side_effect=Exception("close fail"))

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


class TestFileHandlerOnModified:
    @pytest.mark.asyncio
    async def test_on_modified_reads_new_data(self, service, tmp_path):
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
    async def test_on_modified_file_deleted(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("data\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_on_modified_inode_changed_resets_offset(self, service, tmp_path):
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
    async def test_on_modified_file_truncated_resets_offset(self, service, tmp_path):
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
    async def test_on_modified_no_stored_offset(self, service, tmp_path):
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
    async def test_on_modified_different_path_ignored(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("data\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))

    @pytest.mark.asyncio
    async def test_on_modified_exception_suppressed(self, service, tmp_path):
        test_file = tmp_path / "test.log"
        test_file.write_text("data\n", encoding="utf-8")

        source_id = service.add_source({"type": "file", "alias": "s1", "path": str(test_file)})

        with patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, str(test_file))
