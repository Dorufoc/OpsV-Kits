from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.log_collector_service import LogCollectorService, _UdpLogProtocol


@pytest.fixture
def service():
    return LogCollectorService()


class TestAddSource:
    def test_add_system_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "server1", "path": "/var/log/syslog"})
        assert source_id is not None
        source = service.get_source(source_id)
        assert source["type"] == "system"
        assert source["alias"] == "server1"

    def test_add_docker_source(self, service):
        source_id = service.add_source({"type": "docker", "alias": "server1", "container": "nginx"})
        source = service.get_source(source_id)
        assert source["type"] == "docker"
        assert source["container"] == "nginx"

    def test_add_source_defaults(self, service):
        source_id = service.add_source({})
        source = service.get_source(source_id)
        assert source["type"] == "system"
        assert source["host"] == "0.0.0.0"
        assert source["port"] == 9514
        assert source["enabled"] is True
        assert source["status"] == "stopped"
        assert source["labels"] == {}

    def test_add_tcp_source(self, service):
        source_id = service.add_source({"type": "tcp", "host": "127.0.0.1", "port": 514})
        source = service.get_source(source_id)
        assert source["type"] == "tcp"
        assert source["host"] == "127.0.0.1"
        assert source["port"] == 514

    def test_add_udp_source(self, service):
        source_id = service.add_source({"type": "udp", "host": "0.0.0.0", "port": 514})
        source = service.get_source(source_id)
        assert source["type"] == "udp"

    def test_add_file_source(self, service):
        source_id = service.add_source({"type": "file", "path": "/var/log/app.log"})
        source = service.get_source(source_id)
        assert source["type"] == "file"
        assert source["path"] == "/var/log/app.log"

    def test_add_source_with_labels(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "labels": {"env": "prod"}})
        source = service.get_source(source_id)
        assert source["labels"] == {"env": "prod"}

    def test_add_source_none_labels(self, service):
        source_id = service.add_source({"type": "system", "labels": None})
        source = service.get_source(source_id)
        assert source["labels"] == {}


class TestDeleteSource:
    @pytest.mark.asyncio
    async def test_delete_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        await service.delete_source(source_id)
        assert service.get_source(source_id) is None

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, service):
        with pytest.raises(ValueError, match="不存在"):
            await service.delete_source("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_source_cleans_file_offsets(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service._file_offsets[source_id] = (123, 456)
        await service.delete_source(source_id)
        assert source_id not in service._file_offsets

    @pytest.mark.asyncio
    async def test_delete_source_cleans_watchdog_handler(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/tmp/test.log"})
        handler = MagicMock()
        service._watchdog_handlers[source_id] = handler
        service._watchdog_observer = MagicMock()
        await service.delete_source(source_id)
        assert source_id not in service._watchdog_handlers


class TestGetSources:
    def test_get_sources(self, service):
        service.add_source({"type": "system", "alias": "s1"})
        service.add_source({"type": "docker", "alias": "s2"})
        sources = service.get_sources()
        assert len(sources) >= 2

    def test_get_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        source = service.get_source(source_id)
        assert source is not None
        assert service.get_source("nonexistent") is None


class TestUpdateSource:
    def test_update_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service.update_source(source_id, {"alias": "s2", "path": "/var/log/new"})
        source = service.get_source(source_id)
        assert source["alias"] == "s2"
        assert source["path"] == "/var/log/new"

    def test_update_source_not_found(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.update_source("nonexistent", {"alias": "s2"})

    def test_update_source_ignores_invalid_keys(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service.update_source(source_id, {"invalid_key": "value", "alias": "s2"})
        source = service.get_source(source_id)
        assert "invalid_key" not in source
        assert source["alias"] == "s2"

    def test_update_source_enabled(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service.update_source(source_id, {"enabled": False})
        source = service.get_source(source_id)
        assert source["enabled"] is False

    def test_update_source_port(self, service):
        source_id = service.add_source({"type": "tcp", "alias": "s1"})
        service.update_source(source_id, {"port": 514})
        source = service.get_source(source_id)
        assert source["port"] == 514

    def test_update_source_labels(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        service.update_source(source_id, {"labels": {"env": "staging"}})
        source = service.get_source(source_id)
        assert source["labels"] == {"env": "staging"}


class TestSubscribe:
    def test_subscribe(self, service):
        ws = MagicMock()
        service.subscribe(ws, {"level": "ERROR"})
        assert len(service._subscribers) == 1
        assert service._subscribers[0]["filters"]["level"] == "ERROR"

    def test_subscribe_no_filters(self, service):
        ws = MagicMock()
        service.subscribe(ws)
        assert service._subscribers[0]["filters"] == {}

    def test_unsubscribe(self, service):
        ws1 = MagicMock()
        ws2 = MagicMock()
        service.subscribe(ws1)
        service.subscribe(ws2)
        service.unsubscribe(ws1)
        assert len(service._subscribers) == 1
        assert service._subscribers[0]["ws"] is ws2

    def test_update_filters(self, service):
        ws = MagicMock()
        service.subscribe(ws)
        service.update_filters(ws, {"level": "WARN", "keyword": "error"})
        assert service._subscribers[0]["filters"]["level"] == "WARN"
        assert service._subscribers[0]["filters"]["keyword"] == "error"

    def test_update_filters_no_match(self, service):
        ws = MagicMock()
        service.subscribe(ws)
        other_ws = MagicMock()
        service.update_filters(other_ws, {"level": "WARN"})
        assert service._subscribers[0]["filters"] == {}


class TestNotifySubscribers:
    @pytest.mark.asyncio
    async def test_notify_matching_subscriber(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"level": "ERROR"})
        await service._notify_subscribers({"level": "ERROR", "content": "test"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_non_matching_subscriber(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"level": "ERROR"})
        await service._notify_subscribers({"level": "INFO", "content": "test"})
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_keyword_filter(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"keyword": "exception"})
        await service._notify_subscribers({"level": "INFO", "content": "an exception occurred"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_source_filter(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"source": "src1"})
        await service._notify_subscribers({"source": "src1", "content": "test"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_dead_subscriber_removed(self, service):
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("connection closed")
        service.subscribe(ws)
        await service._notify_subscribers({"content": "test"})
        assert len(service._subscribers) == 0

    @pytest.mark.asyncio
    async def test_notify_no_filters(self, service):
        ws = AsyncMock()
        service.subscribe(ws)
        await service._notify_subscribers({"content": "test"})
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_keyword_not_matching(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"keyword": "error"})
        await service._notify_subscribers({"level": "INFO", "content": "all is well"})
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_source_not_matching(self, service):
        ws = AsyncMock()
        service.subscribe(ws, {"source": "src1"})
        await service._notify_subscribers({"source": "src2", "content": "test"})
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_multiple_subscribers(self, service):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        service.subscribe(ws1)
        service.subscribe(ws2, {"level": "ERROR"})
        await service._notify_subscribers({"level": "INFO", "content": "test"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()


class TestProcessLogLine:
    @pytest.mark.asyncio
    async def test_process_log_line(self, service):
        service.add_source({"type": "system", "alias": "s1"})
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "ERROR", "message": "test error", "timestamp": 1234567890}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("ERROR test error", "src1")
            mock_storage.write_log.assert_called_once()
            mock_alert.check_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_empty_line(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser:
            await service._process_log_line("   ", "src1")
            mock_parser.parse.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_log_line_with_labels(self, service):
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
    async def test_process_log_line_with_host(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", "src1", {"host": "192.168.1.1"})
            call_args = mock_storage.write_log.call_args[0][0]
            assert call_args["host"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_process_log_line_with_container(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", "src1", {"container_name": "nginx", "container_id": "abc123"})
            call_args = mock_storage.write_log.call_args[0][0]
            assert call_args["container_name"] == "nginx"
            assert call_args["container_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_process_log_line_no_timestamp(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test"}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", "src1")
            call_args = mock_storage.write_log.call_args[0][0]
            assert isinstance(call_args["timestamp"], float)

    @pytest.mark.asyncio
    async def test_process_log_line_no_labels(self, service):
        with patch("app.services.log_collector_service.log_parser_service") as mock_parser, \
             patch("app.services.log_collector_service.log_storage_service") as mock_storage, \
             patch("app.services.log_collector_service.log_alert_service") as mock_alert:
            mock_parser.parse.return_value = {"level": "INFO", "message": "test", "timestamp": 123}
            mock_storage.write_log = AsyncMock()
            mock_alert.check_alert = AsyncMock()
            await service._process_log_line("test", "nonexistent_source")
            call_args = mock_storage.write_log.call_args[0][0]
            assert call_args["labels"] is None


class TestReadChannelData:
    def test_read_channel_data_ready(self, service):
        chan = MagicMock()
        chan.recv_ready.return_value = True
        chan.recv.return_value = b"data"
        result = service._read_channel_data(chan)
        assert result == b"data"

    def test_read_channel_data_not_ready(self, service):
        chan = MagicMock()
        chan.recv_ready.return_value = False
        result = service._read_channel_data(chan)
        assert result == b""

    def test_read_channel_data_exception(self, service):
        chan = MagicMock()
        chan.recv_ready.side_effect = Exception("error")
        result = service._read_channel_data(chan)
        assert result is None


class TestStartSystemLogCollection:
    @pytest.mark.asyncio
    async def test_account_not_found(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")
            source = service.get_source(source_id)
            assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_transport_none(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager.client.get_transport.return_value = None
        mock_conn.manager.encoding = "utf-8"
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")
            source = service.get_source(source_id)
            assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_cancelled(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_transport = MagicMock()
        mock_chan = MagicMock()
        mock_chan.recv_ready.return_value = False
        mock_chan.exit_status_ready.return_value = True
        mock_conn.manager.client.get_transport.return_value = mock_transport
        mock_transport.open_session.return_value = mock_chan
        mock_conn.manager.encoding = "utf-8"

        call_count = 0
        async def fake_exec_in_executor(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.CancelledError()
            return b""

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch.object(service, "_read_channel_data", return_value=b""):
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop_obj = MagicMock()
                    mock_loop.return_value = mock_loop_obj
                    mock_loop_obj.run_in_executor = fake_exec_in_executor
                    await service.start_system_log_collection(source_id, "s1", "/var/log/syslog")
        source = service.get_source(source_id)
        assert source["status"] == "stopped"


class TestStartDockerLogCollection:
    @pytest.mark.asyncio
    async def test_account_not_found(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            await service.start_docker_log_collection(source_id, "s1", "nginx")
            source = service.get_source(source_id)
            assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_transport_none(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        mock_account = MagicMock()
        mock_conn = MagicMock()
        mock_conn.manager.client.get_transport.return_value = None
        mock_conn.manager.encoding = "utf-8"
        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            await service.start_docker_log_collection(source_id, "s1", "nginx")
            source = service.get_source(source_id)
            assert source["status"] == "error"

    @pytest.mark.asyncio
    async def test_cancelled(self, service):
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
                raise asyncio.CancelledError()
            return b""

        with patch("app.services.log_collector_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = mock_account
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection = MagicMock()
            with patch.object(service, "_read_channel_data", return_value=b""):
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop_obj = MagicMock()
                    mock_loop.return_value = mock_loop_obj
                    mock_loop_obj.run_in_executor = fake_exec_in_executor
                    await service.start_docker_log_collection(source_id, "s1", "nginx")
        source = service.get_source(source_id)
        assert source["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_nonexistent_source(self, service):
        await service.start_docker_log_collection("nonexistent", "s1", "nginx")


class TestStartTcpServer:
    @pytest.mark.asyncio
    async def test_start_tcp_server(self, service):
        with patch("asyncio.start_server", new_callable=AsyncMock) as mock_start:
            mock_server = MagicMock()
            mock_start.return_value = mock_server
            await service.start_tcp_server("127.0.0.1", 9514)
            mock_start.assert_called_once()
            assert service._tcp_server is mock_server


class TestStartUdpServer:
    @pytest.mark.asyncio
    async def test_start_udp_server(self, service):
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_obj = MagicMock()
            mock_loop.return_value = mock_loop_obj
            mock_transport = MagicMock()
            mock_loop_obj.create_datagram_endpoint = AsyncMock(return_value=(mock_transport, MagicMock()))
            await service.start_udp_server("0.0.0.0", 9514)
            assert service._udp_transport is mock_transport


class TestStartFileWatcher:
    @pytest.mark.asyncio
    async def test_nonexistent_source(self, service):
        await service.start_file_watcher("nonexistent", "/tmp/test.log")

    @pytest.mark.asyncio
    async def test_file_not_exists(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/nonexistent/file.log"})
        with patch("app.services.log_collector_service.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path
            await service.start_file_watcher(source_id, "/nonexistent/file.log")
            source = service.get_source(source_id)
            assert source["status"] == "error"


class TestStartSource:
    @pytest.mark.asyncio
    async def test_start_system_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log/syslog"})
        with patch.object(service, "start_system_log_collection", new_callable=AsyncMock):
            await service.start_source(source_id)
            assert source_id in service._tasks

    @pytest.mark.asyncio
    async def test_start_docker_source(self, service):
        source_id = service.add_source({"type": "docker", "alias": "s1", "container": "nginx"})
        with patch.object(service, "start_docker_log_collection", new_callable=AsyncMock):
            await service.start_source(source_id)
            assert source_id in service._tasks

    @pytest.mark.asyncio
    async def test_start_tcp_source(self, service):
        source_id = service.add_source({"type": "tcp", "host": "0.0.0.0", "port": 9514})
        with patch.object(service, "start_tcp_server", new_callable=AsyncMock):
            await service.start_source(source_id)
            assert source_id in service._tasks

    @pytest.mark.asyncio
    async def test_start_udp_source(self, service):
        source_id = service.add_source({"type": "udp", "host": "0.0.0.0", "port": 9514})
        with patch.object(service, "start_udp_server", new_callable=AsyncMock):
            await service.start_source(source_id)
            assert source_id in service._tasks

    @pytest.mark.asyncio
    async def test_start_file_source(self, service):
        source_id = service.add_source({"type": "file", "alias": "s1", "path": "/var/log/app.log"})
        with patch.object(service, "start_file_watcher", new_callable=AsyncMock):
            await service.start_source(source_id)
            assert source_id in service._tasks

    @pytest.mark.asyncio
    async def test_start_unknown_type(self, service):
        source_id = service.add_source({"type": "unknown"})
        await service.start_source(source_id)
        assert source_id not in service._tasks

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1", "path": "/var/log"})
        service._tasks[source_id] = MagicMock()
        await service.start_source(source_id)

    @pytest.mark.asyncio
    async def test_start_nonexistent_source(self, service):
        await service.start_source("nonexistent")


class TestStopSource:
    @pytest.mark.asyncio
    async def test_stop_source(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        task = asyncio.create_task(asyncio.sleep(100))
        service._tasks[source_id] = task
        await service.stop_source(source_id)
        source = service.get_source(source_id)
        assert source["status"] == "stopped"
        assert source_id not in service._tasks

    @pytest.mark.asyncio
    async def test_stop_source_no_task(self, service):
        source_id = service.add_source({"type": "system", "alias": "s1"})
        await service.stop_source(source_id)
        source = service.get_source(source_id)
        assert source["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_stop_source_no_source(self, service):
        await service.stop_source("nonexistent")


class TestStartAll:
    @pytest.mark.asyncio
    async def test_start_all(self, service):
        s1 = service.add_source({"type": "system", "alias": "s1", "path": "/var/log", "enabled": True})
        s2 = service.add_source({"type": "docker", "alias": "s2", "container": "nginx", "enabled": False})
        with patch.object(service, "start_source", new_callable=AsyncMock) as mock_start:
            await service.start_all()
            mock_start.assert_called_once_with(s1)


class TestStopAll:
    @pytest.mark.asyncio
    async def test_stop_all(self, service):
        s1 = service.add_source({"type": "system", "alias": "s1"})
        service._tasks[s1] = AsyncMock()
        with patch.object(service, "stop_source", new_callable=AsyncMock) as mock_stop:
            await service.stop_all()
            mock_stop.assert_called_once_with(s1)


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown(self, service):
        with patch.object(service, "stop_all", new_callable=AsyncMock):
            service._tcp_server = MagicMock()
            service._tcp_server.close = MagicMock()
            service._tcp_server.wait_closed = AsyncMock()
            service._udp_transport = MagicMock()
            service._udp_transport.close = MagicMock()
            await service.shutdown()
            assert service._tcp_server is None
            assert service._udp_transport is None
            assert len(service._subscribers) == 0

    @pytest.mark.asyncio
    async def test_shutdown_with_watchdog(self, service):
        with patch.object(service, "stop_all", new_callable=AsyncMock):
            service._tcp_server = None
            service._udp_transport = None
            mock_observer = MagicMock()
            service._watchdog_observer = mock_observer
            service._watchdog_handlers["s1"] = MagicMock()
            await service.shutdown()
            mock_observer.stop.assert_called_once()
            assert service._watchdog_observer is None
            assert len(service._watchdog_handlers) == 0
            assert len(service._file_offsets) == 0

    @pytest.mark.asyncio
    async def test_shutdown_no_servers(self, service):
        with patch.object(service, "stop_all", new_callable=AsyncMock):
            service._tcp_server = None
            service._udp_transport = None
            await service.shutdown()
            assert service._tcp_server is None
            assert service._udp_transport is None


class TestUdpLogProtocol:
    def test_connection_made(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        assert protocol.transport is transport

    def test_datagram_received(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.call_soon_threadsafe = MagicMock()
            protocol.datagram_received(b"test log message", ("127.0.0.1", 12345))
            mock_loop.return_value.call_soon_threadsafe.assert_called_once()

    def test_datagram_received_empty(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.call_soon_threadsafe = MagicMock()
            protocol.datagram_received(b"   ", ("127.0.0.1", 12345))
            mock_loop.return_value.call_soon_threadsafe.assert_not_called()

    def test_error_received(self, service):
        protocol = _UdpLogProtocol(service)
        protocol.error_received(Exception("test"))

    def test_connection_lost(self, service):
        protocol = _UdpLogProtocol(service)
        protocol.connection_lost(Exception("test"))

    def test_datagram_received_exception(self, service):
        protocol = _UdpLogProtocol(service)
        transport = MagicMock()
        protocol.connection_made(transport)
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.call_soon_threadsafe = MagicMock()
            protocol.datagram_received(b"\xff\xfe", ("127.0.0.1", 12345))
