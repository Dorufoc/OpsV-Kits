import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.log_collector_service import LogCollectorService, _UdpLogProtocol


@pytest.fixture
def service():
    return LogCollectorService()


class TestStartSystemLogCollectionNormalFlow:
    @pytest.mark.asyncio
    async def test_system_log_reads_data(self, service):
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
                return b"test log line\n"
            if call_count == 2:
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
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")

    @pytest.mark.asyncio
    async def test_system_log_channel_exit(self, service):
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

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")

    @pytest.mark.asyncio
    async def test_system_log_exception_retries(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.side_effect = Exception("connection error")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")
        source = service.get_source(source_id)
        assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_system_log_nonexistent_source(self, service):
        await service.start_system_log_collection("nonexistent", "s1", "/var/log/syslog")


class TestStartDockerLogCollectionNormalFlow:
    @pytest.mark.asyncio
    async def test_docker_log_reads_data(self, service):
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
                return b"docker log line\n"
            if call_count == 2:
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
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_docker_log_collection(source_id, "s1", "nginx")

    @pytest.mark.asyncio
    async def test_docker_log_exception_retries(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.side_effect = Exception("connection error")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await service.start_docker_log_collection(source_id, "s1", "nginx")
        source = service.get_source(source_id)
        assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_docker_log_channel_exit(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
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

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop_obj = MagicMock()
                mock_loop.return_value = mock_loop_obj
                mock_loop_obj.run_in_executor = fake_exec_in_executor
                await service.start_docker_log_collection(source_id, "s1", "nginx")


class TestStartFileWatcherAdvanced:
    @pytest.mark.asyncio
    async def test_file_watcher_cancelled(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/tmp/test.log"})
        with patch("app.services.log_collector_service.Path") as mock_path_cls, \
             patch("watchdog.observers.Observer") as mock_observer_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.stat.return_value = MagicMock(st_ino=123, st_size=0)
            mock_path.parent = Path("/tmp")
            mock_path_cls.return_value = mock_path
            mock_observer = MagicMock()
            mock_observer_cls.return_value = mock_observer
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()
                await service.start_file_watcher(source_id, "/tmp/test.log")
        source = service.get_source(source_id)
        assert source["status"] == "stopped"


class TestProcessLogLineEdgeCases:
    @pytest.mark.asyncio
    async def test_process_log_line_with_extra_labels_merge(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "labels": {"env": "prod"}})
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", source_id, {"labels": {"host": "web1"}})
            call_args = mock_storage.write_log.call_args[0][0]
            assert call_args["labels"]["env"] == "prod"
            assert call_args["labels"]["host"] == "web1"

    @pytest.mark.asyncio
    async def test_process_log_line_extra_without_labels(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", "src1", {"host": "10.0.0.1"})
            call_args = mock_storage.write_log.call_args[0][0]
            assert call_args["host"] == "10.0.0.1"


class TestUdpLogProtocolAdvanced:
    def test_datagram_received_decode_error(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.call_soon_threadsafe = MagicMock()
            protocol.datagram_received(b"\xff\xfe\xfd", ("127.0.0.1", 12345))
            mock_loop.return_value.call_soon_threadsafe.assert_called_once()

    def test_datagram_received_exception_in_loop(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        with patch("asyncio.get_event_loop", side_effect=Exception("no loop")):
            protocol.datagram_received(b"test data", ("127.0.0.1", 12345))


class TestShutdownAdvanced:
    @pytest.mark.asyncio
    async def test_shutdown_no_tcp_no_udp_no_watchdog(self, service):
        service._tcp_server = None
        service._udp_transport = None
        service._watchdog_observer = None
        with patch.object(service, "stop_all", new_callable=AsyncMock):
            await service.shutdown()
            assert len(service._subscribers) == 0
            assert len(service._file_offsets) == 0
            assert len(service._watchdog_handlers) == 0

    @pytest.mark.asyncio
    async def test_shutdown_cleans_file_offsets(self, service):
        service._file_offsets["s1"] = (123, 456)
        service._file_offsets["s2"] = (789, 12)
        with patch.object(service, "stop_all", new_callable=AsyncMock):
            service._tcp_server = None
            service._udp_transport = None
            service._watchdog_observer = None
            await service.shutdown()
            assert len(service._file_offsets) == 0


class TestDeleteSourceAdvanced:
    @pytest.mark.asyncio
    async def test_delete_source_with_running_task(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        task = asyncio.create_task(asyncio.sleep(100))
        service._tasks[source_id] = task
        await service.delete_source(source_id)
        assert source_id not in service._tasks
        assert service.get_source(source_id) is None

    @pytest.mark.asyncio
    async def test_delete_source_watchdog_handler_removal_error(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/tmp/test.log"})
        handler = MagicMock()
        service._watchdog_handlers[source_id] = handler
        mock_observer = MagicMock()
        mock_observer.remove_handler_for_path.side_effect = Exception("handler error")
        service._watchdog_observer = mock_observer
        await service.delete_source(source_id)
        assert source_id not in service._watchdog_handlers


class TestNotifySubscribersEdgeCases:
    @pytest.mark.asyncio
    async def test_notify_with_level_and_source_filter(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"level": "ERROR", "source": "src1"})
        await service._notify_subscribers({"level": "ERROR", "source": "src1", "content": "test"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_level_matches_source_not(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"level": "ERROR", "source": "src1"})
        await service._notify_subscribers({"level": "ERROR", "source": "src2", "content": "test"})
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_dead_subscriber_partial_removal(self, service):
        ws1 = AsyncMock()
        ws1.send_json.side_effect = Exception("dead")
        ws2 = AsyncMock()
        service.subscribe(ws1)
        service.subscribe(ws2)
        await service._notify_subscribers({"content": "test"})
        assert len(service._subscribers) == 1
        assert service._subscribers[0]["ws"] is ws2


class TestStartSourceAdvanced:
    @pytest.mark.asyncio
    async def test_start_source_already_has_task(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log"})
        existing_task = MagicMock()
        existing_task.done.return_value = False
        service._tasks[source_id] = existing_task
        await service.start_source(source_id)
        assert service._tasks[source_id] is existing_task


class TestStopSourceAdvanced:
    @pytest.mark.asyncio
    async def test_stop_source_with_cancelled_task(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        task = asyncio.create_task(asyncio.sleep(100))
        service._tasks[source_id] = task
        await service.stop_source(source_id)
        assert source_id not in service._tasks

    @pytest.mark.asyncio
    async def test_stop_source_sets_status_stopped(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service._sources[source_id]["status"] = "running"
        await service.stop_source(source_id)
        assert service._sources[source_id]["status"] == "stopped"


class TestAddSourceEdgeCases:
    def test_add_source_with_all_fields(self, service):
        source_id = service.add_source({
            "type": "docker",
            "alias": "prod-server",
            "path": "/var/log/app.log",
            "container": "web-app",
            "host": "192.168.1.100",
            "port": 5140,
            "enabled": False,
            "labels": {"env": "production", "team": "backend"},
        })
        source = service.get_source(source_id)
        assert source["type"] == "docker"
        assert source["alias"] == "prod-server"
        assert source["host"] == "192.168.1.100"
        assert source["port"] == 5140
        assert source["enabled"] is False
        assert source["labels"]["env"] == "production"

    def test_add_source_generates_unique_ids(self, service):
        id1 = service.add_source({"type": "system"})
        id2 = service.add_source({"type": "system"})
        assert id1 != id2
