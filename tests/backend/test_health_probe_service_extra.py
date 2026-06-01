from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import aiohttp

from app.models.health_probe import (
    HttpProbeConfig,
    HttpProbeConfigCreate,
    ProbeResult,
    ProbeStatus,
    ProbeTarget,
    ProbeTargetCreate,
    ProbeTargetUpdate,
    ProbeType,
)
from app.services.health_probe_service import HealthProbeService, _MAX_LOGS_PER_TARGET


@pytest.fixture
def service():
    return HealthProbeService()


class TestLoadTargetsFromDb:
    def test_load_targets_with_http_config(self, service):
        data = ProbeTargetCreate(
            name="test",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
            http_config=HttpProbeConfigCreate(method="POST", expected_status_codes=[200, 201]),
        )
        target = service.create_target(data)
        target_id = target.id

        new_service = HealthProbeService()
        new_service._load_targets_from_db()
        loaded = new_service.get_target(target_id)
        assert loaded is not None
        assert loaded.http_config is not None
        assert loaded.http_config.method == "POST"
        assert loaded.http_config.expected_status_codes == [200, 201]

    def test_load_targets_with_tags(self, service):
        data = ProbeTargetCreate(
            name="tagged",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
            tags=["prod", "web"],
        )
        target = service.create_target(data)
        target_id = target.id

        new_service = HealthProbeService()
        new_service._load_targets_from_db()
        loaded = new_service.get_target(target_id)
        assert loaded is not None
        assert "prod" in loaded.tags
        assert "web" in loaded.tags

    def test_load_targets_with_status(self, service):
        data = ProbeTargetCreate(
            name="test",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
        )
        target = service.create_target(data)
        target.current_status = ProbeStatus.AVAILABLE
        target.consecutive_failures = 0
        target.consecutive_successes = 5
        service._save_target_to_db(target)

        new_service = HealthProbeService()
        new_service._load_targets_from_db()
        loaded = new_service.get_target(target.id)
        assert loaded is not None
        assert loaded.current_status == ProbeStatus.AVAILABLE
        assert loaded.consecutive_successes == 5

    def test_load_targets_invalid_http_config(self, service):
        data = ProbeTargetCreate(
            name="test",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
        )
        target = service.create_target(data)
        from app.services.health_probe_service import _DB_PATH
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute(
                "UPDATE probe_targets SET http_config = ? WHERE id = ?",
                ("invalid_json", target.id),
            )

        new_service = HealthProbeService()
        new_service._load_targets_from_db()
        loaded = new_service.get_target(target.id)
        assert loaded is not None
        assert loaded.http_config is None

    def test_load_targets_invalid_tags(self, service):
        data = ProbeTargetCreate(
            name="test",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
        )
        target = service.create_target(data)
        from app.services.health_probe_service import _DB_PATH
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute(
                "UPDATE probe_targets SET tags = ? WHERE id = ?",
                ("invalid_json", target.id),
            )

        new_service = HealthProbeService()
        new_service._load_targets_from_db()
        loaded = new_service.get_target(target.id)
        assert loaded is not None
        assert loaded.tags == []


class TestSaveResultToDbLogTrimming:
    def test_log_trimming_triggered(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        result = ProbeResult(
            id=str(uuid.uuid4()),
            target_id=target.id,
            timestamp=datetime.now(),
            probe_type=ProbeType.HTTP,
            target="https://a.com",
            success=True,
            response_time_ms=50.0,
        )
        from app.services.health_probe_service import _DB_PATH
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = (_MAX_LOGS_PER_TARGET + 100,)
            service._save_result_to_db(result)
            delete_calls = [
                c for c in mock_conn.execute.call_args_list
                if "DELETE" in str(c)
            ]
            assert len(delete_calls) >= 1


class TestExecuteHttpProbe:
    @pytest.mark.asyncio
    async def test_http_probe_success(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is True
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_http_probe_unexpected_status(self, service):
        data = ProbeTargetCreate(
            name="test", probe_type=ProbeType.HTTP, target="https://example.com",
            http_config=HttpProbeConfigCreate(expected_status_codes=[200]),
        )
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 500
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is False
            assert "500" in result.error_message

    @pytest.mark.asyncio
    async def test_http_probe_content_match(self, service):
        data = ProbeTargetCreate(
            name="test", probe_type=ProbeType.HTTP, target="https://example.com",
            http_config=HttpProbeConfigCreate(content_match="hello"),
        )
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="hello world")
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is True
            assert result.content_matched is True

    @pytest.mark.asyncio
    async def test_http_probe_content_not_match(self, service):
        data = ProbeTargetCreate(
            name="test", probe_type=ProbeType.HTTP, target="https://example.com",
            http_config=HttpProbeConfigCreate(content_match="xyz"),
        )
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="hello world")
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is False
            assert result.content_matched is False

    @pytest.mark.asyncio
    async def test_http_probe_invalid_regex(self, service):
        data = ProbeTargetCreate(
            name="test", probe_type=ProbeType.HTTP, target="https://example.com",
            http_config=HttpProbeConfigCreate(content_match="[invalid"),
        )
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="hello")
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.content_matched is False

    @pytest.mark.asyncio
    async def test_http_probe_timeout(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is False
            assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_http_probe_client_error(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("connection refused"))
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_http_probe_generic_exception(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_http_probe_with_headers(self, service):
        data = ProbeTargetCreate(
            name="test", probe_type=ProbeType.HTTP, target="https://example.com",
            http_config=HttpProbeConfigCreate(headers={"Authorization": "Bearer token"}),
        )
        target = service.create_target(data)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_request_cm = MagicMock()
        mock_request_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_request_cm)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.health_probe_service.aiohttp.ClientSession", return_value=mock_session), \
             patch("app.services.health_probe_service.aiohttp.ClientTimeout"):
            result = await service._execute_http_probe(target)
            call_kwargs = mock_session.request.call_args
            assert call_kwargs[1]["headers"] == {"Authorization": "Bearer token"}


class TestExecuteTcpProbe:
    @pytest.mark.asyncio
    async def test_tcp_probe_success(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        with patch("asyncio.open_connection", new_callable=AsyncMock, return_value=(mock_reader, mock_writer)):
            result = await service._execute_tcp_probe(target)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_tcp_probe_invalid_format(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="no_colon")
        target = service.create_target(data)
        result = await service._execute_tcp_probe(target)
        assert result.success is False
        assert "Invalid" in result.error_message

    @pytest.mark.asyncio
    async def test_tcp_probe_timeout(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        with patch("asyncio.open_connection", new_callable=AsyncMock, side_effect=asyncio.TimeoutError()):
            result = await service._execute_tcp_probe(target)
            assert result.success is False
            assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_tcp_probe_connection_refused(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        with patch("asyncio.open_connection", new_callable=AsyncMock, side_effect=ConnectionRefusedError()):
            result = await service._execute_tcp_probe(target)
            assert result.success is False
            assert "refused" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_tcp_probe_os_error(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        with patch("asyncio.open_connection", new_callable=AsyncMock, side_effect=OSError("network error")):
            result = await service._execute_tcp_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_tcp_probe_generic_exception(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        with patch("asyncio.open_connection", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            result = await service._execute_tcp_probe(target)
            assert result.success is False


class TestExecuteIcmpProbe:
    @pytest.mark.asyncio
    async def test_icmp_probe_success(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Reply from 192.168.1.1 time=5ms", b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is True
            assert result.response_time_ms == 5.0

    @pytest.mark.asyncio
    async def test_icmp_probe_timeout(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"Request timed out", b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False
            assert "timed out" in result.error_message.lower() or "Timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_icmp_probe_host_unreachable(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"Destination host unreachable", b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False
            assert "unreachable" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_icmp_probe_host_not_found(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="invalid.host")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"could not find host", b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False
            assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_icmp_probe_generic_failure(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"some unknown error", b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_icmp_probe_command_timeout(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False
            assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_icmp_probe_ping_not_found(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, side_effect=FileNotFoundError()):
            result = await service._execute_icmp_probe(target)
            assert result.success is False
            assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_icmp_probe_generic_exception(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            result = await service._execute_icmp_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_icmp_probe_chinese_output(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=("Reply from 192.168.1.1: time=5ms".encode("gbk"), b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_icmp_probe_chinese_timeout(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=("请求超时".encode("gbk"), b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_icmp_probe_chinese_unreachable(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=("目标主机不可达".encode("gbk"), b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_icmp_probe_chinese_host_not_found(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="bad.host")
        target = service.create_target(data)
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=("找不到主机".encode("gbk"), b""))
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
            result = await service._execute_icmp_probe(target)
            assert result.success is False


class TestCreateTargetWithScheduler:
    def test_create_target_enabled_with_scheduler(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=True)
        target = service.create_target(data)
        mock_scheduler.add_job.assert_called_once()

    def test_create_target_disabled_with_scheduler(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=False)
        target = service.create_target(data)
        mock_scheduler.add_job.assert_not_called()

    def test_create_target_scheduler_not_running(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=True)
        target = service.create_target(data)
        mock_scheduler.add_job.assert_not_called()


class TestUpdateTargetReschedule:
    def test_update_enable_from_disabled(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=False)
        target = service.create_target(data)
        update = ProbeTargetUpdate(enabled=True)
        updated = service.update_target(target.id, update)
        assert updated.enabled is True
        mock_scheduler.remove_job.assert_called()
        mock_scheduler.add_job.assert_called()

    def test_update_disable_from_enabled(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=True)
        target = service.create_target(data)
        mock_scheduler.reset_mock()
        update = ProbeTargetUpdate(enabled=False)
        updated = service.update_target(target.id, update)
        assert updated.enabled is False
        mock_scheduler.remove_job.assert_called()
        mock_scheduler.add_job.assert_not_called()

    def test_update_interval_change(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", interval_seconds=60)
        target = service.create_target(data)
        mock_scheduler.reset_mock()
        update = ProbeTargetUpdate(interval_seconds=120)
        updated = service.update_target(target.id, update)
        assert updated.interval_seconds == 120
        mock_scheduler.remove_job.assert_called()
        mock_scheduler.add_job.assert_called()

    def test_update_no_reschedule_same_interval(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", interval_seconds=60)
        target = service.create_target(data)
        mock_scheduler.reset_mock()
        update = ProbeTargetUpdate(name="new name")
        updated = service.update_target(target.id, update)
        assert updated.name == "new name"
        mock_scheduler.remove_job.assert_not_called()
        mock_scheduler.add_job.assert_not_called()


class TestQueryProbeLogsFilter:
    def test_query_with_success_filter(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        success_result = ProbeResult(
            id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=True, response_time_ms=50.0,
        )
        fail_result = ProbeResult(
            id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=False, error_message="timeout",
        )
        service._save_result_to_db(success_result)
        service._save_result_to_db(fail_result)
        success_logs, success_total = service.query_probe_logs(target.id, success=True)
        fail_logs, fail_total = service.query_probe_logs(target.id, success=False)
        assert all(l.success for l in success_logs)
        assert all(not l.success for l in fail_logs)

    def test_query_with_limit_offset(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        for i in range(5):
            result = ProbeResult(
                id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://a.com",
                success=True, response_time_ms=50.0,
            )
            service._save_result_to_db(result)
        _, total = service.query_probe_logs(target.id)
        assert total >= 5
        page1, _ = service.query_probe_logs(target.id, limit=2, offset=0)
        page2, _ = service.query_probe_logs(target.id, limit=2, offset=2)
        assert len(page1) <= 2
        assert len(page2) <= 2


class TestCalculateStatisticsWithTimeFilter:
    def test_statistics_with_time_filter(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        result = ProbeResult(
            id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=True, response_time_ms=50.0,
        )
        service._save_result_to_db(result)
        stats = service.calculate_statistics(
            target.id,
            time_start=datetime(2020, 1, 1),
            time_end=datetime(2030, 1, 1),
        )
        assert stats is not None
        assert stats.total_probes >= 1

    def test_statistics_zero_probes(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        stats = service.calculate_statistics(target.id)
        assert stats is not None
        assert stats.uptime_percent == 0.0


class TestGetOverviewMixed:
    def test_overview_mixed_statuses(self, service):
        data1 = ProbeTargetCreate(name="avail", probe_type=ProbeType.HTTP, target="https://a.com")
        t1 = service.create_target(data1)
        t1.current_status = ProbeStatus.AVAILABLE
        service._save_target_to_db(t1)

        data2 = ProbeTargetCreate(name="unavail", probe_type=ProbeType.HTTP, target="https://b.com")
        t2 = service.create_target(data2)
        t2.current_status = ProbeStatus.UNAVAILABLE
        service._save_target_to_db(t2)

        overview = service.get_overview()
        assert overview.available_count >= 1
        assert overview.unavailable_count >= 1


class TestAddRemoveProbeJobWithScheduler:
    def test_add_probe_job_removes_existing(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        service._scheduler = mock_scheduler
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        service._add_probe_job(target)
        mock_scheduler.remove_job.assert_called()
        mock_scheduler.add_job.assert_called()

    def test_remove_probe_job_exception(self, service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler.remove_job.side_effect = Exception("job not found")
        service._scheduler = mock_scheduler
        service._remove_probe_job("nonexistent")


class TestExecuteProbeUnknownType:
    @pytest.mark.asyncio
    async def test_execute_probe_unknown_type(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        target.probe_type = "unknown"
        await service._execute_probe(target.id)


class TestProbeNowUnknownType:
    @pytest.mark.asyncio
    async def test_probe_now_unknown_type(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        target.probe_type = "unknown"
        result = await service.probe_now(target.id)
        assert result is None


class TestDeleteTargetFromDb:
    def test_delete_removes_results(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        result = ProbeResult(
            id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=True, response_time_ms=50.0,
        )
        service._save_result_to_db(result)
        service._delete_target_from_db(target.id)
        from app.services.health_probe_service import _DB_PATH
        with sqlite3.connect(str(_DB_PATH)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM probe_results WHERE target_id = ?",
                (target.id,),
            ).fetchone()[0]
            assert count == 0
