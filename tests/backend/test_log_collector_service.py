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
