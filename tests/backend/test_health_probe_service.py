from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.health_probe_service import HealthProbeService
from app.models.health_probe import (
    HttpProbeConfig,
    HttpProbeConfigCreate,
    ProbeStatus,
    ProbeTarget,
    ProbeTargetCreate,
    ProbeTargetUpdate,
    ProbeType,
)


@pytest.fixture
def service():
    return HealthProbeService()


class TestInitDb:
    def test_init_creates_tables(self, service):
        import sqlite3
        from pathlib import Path
        from app.services.health_probe_service import _DB_PATH
        with sqlite3.connect(str(_DB_PATH)) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}
            assert "probe_targets" in table_names
            assert "probe_results" in table_names


class TestCreateTarget:
    def test_create_http_target(self, service):
        data = ProbeTargetCreate(
            name="web-server",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
        )
        target = service.create_target(data)
        assert target.name == "web-server"
        assert target.probe_type == ProbeType.HTTP
        assert target.current_status == ProbeStatus.UNKNOWN

    def test_create_tcp_target(self, service):
        data = ProbeTargetCreate(
            name="db-server",
            probe_type=ProbeType.TCP,
            target="db.example.com:3306",
        )
        target = service.create_target(data)
        assert target.probe_type == ProbeType.TCP

    def test_create_icmp_target(self, service):
        data = ProbeTargetCreate(
            name="gateway",
            probe_type=ProbeType.ICMP,
            target="192.168.1.1",
        )
        target = service.create_target(data)
        assert target.probe_type == ProbeType.ICMP

    def test_create_target_with_tags(self, service):
        data = ProbeTargetCreate(
            name="tagged",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
            tags=["production", "web"],
        )
        target = service.create_target(data)
        assert "production" in target.tags

    def test_create_target_with_http_config(self, service):
        http_cfg = HttpProbeConfigCreate(
            method="POST",
            expected_status_codes=[200, 201],
            content_match="ok",
        )
        data = ProbeTargetCreate(
            name="custom-http",
            probe_type=ProbeType.HTTP,
            target="https://example.com",
            http_config=http_cfg,
        )
        with patch.object(service, "_save_target_to_db"), \
             patch.object(service, "_add_probe_job"):
            target = service.create_target(data)
            assert target.http_config.method == "POST"


class TestGetTarget:
    def test_get_target_found(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        found = service.get_target(target.id)
        assert found is not None

    def test_get_target_not_found(self, service):
        assert service.get_target("nonexistent") is None


class TestListTargets:
    def test_list_targets(self, service):
        data1 = ProbeTargetCreate(name="t1", probe_type=ProbeType.HTTP, target="https://a.com")
        data2 = ProbeTargetCreate(name="t2", probe_type=ProbeType.TCP, target="b.com:80")
        service.create_target(data1)
        service.create_target(data2)
        targets = service.list_targets()
        assert len(targets) >= 2

    def test_list_targets_filter_by_tag(self, service):
        data1 = ProbeTargetCreate(name="t1", probe_type=ProbeType.HTTP, target="https://a.com", tags=["prod"])
        data2 = ProbeTargetCreate(name="t2", probe_type=ProbeType.HTTP, target="https://b.com", tags=["dev"])
        service.create_target(data1)
        service.create_target(data2)
        targets = service.list_targets(tag="prod")
        assert len(targets) >= 1
        assert all("prod" in t.tags for t in targets)

    def test_list_targets_filter_by_type(self, service):
        data = ProbeTargetCreate(name="t1", probe_type=ProbeType.HTTP, target="https://a.com")
        service.create_target(data)
        targets = service.list_targets(probe_type=ProbeType.HTTP)
        assert all(t.probe_type == ProbeType.HTTP for t in targets)


class TestUpdateTarget:
    def test_update_target_name(self, service):
        data = ProbeTargetCreate(name="old", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        update = ProbeTargetUpdate(name="new")
        updated = service.update_target(target.id, update)
        assert updated.name == "new"

    def test_update_target_not_found(self, service):
        update = ProbeTargetUpdate(name="new")
        result = service.update_target("nonexistent", update)
        assert result is None

    def test_update_target_with_http_config(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        update = ProbeTargetUpdate(http_config={"method": "POST", "expected_status_codes": [200]})
        updated = service.update_target(target.id, update)
        assert updated.http_config.method == "POST"


class TestDeleteTarget:
    def test_delete_target(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        result = service.delete_target(target.id)
        assert result is True
        assert service.get_target(target.id) is None

    def test_delete_target_not_found(self, service):
        result = service.delete_target("nonexistent")
        assert result is False


class TestUpdateTargetStatus:
    def test_success_from_unknown(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        from app.models.health_probe import ProbeResult
        result = ProbeResult(
            id="r1", target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=True, response_time_ms=100.0,
        )
        service._update_target_status(target, result)
        assert target.current_status == ProbeStatus.AVAILABLE
        assert target.consecutive_successes == 1
        assert target.consecutive_failures == 0

    def test_failure_from_unknown(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", failure_threshold=3)
        target = service.create_target(data)
        from app.models.health_probe import ProbeResult
        for i in range(3):
            result = ProbeResult(
                id=f"r{i}", target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://a.com",
                success=False, error_message="timeout",
            )
            service._update_target_status(target, result)
        assert target.current_status == ProbeStatus.UNAVAILABLE

    def test_recovery(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", recovery_threshold=2)
        target = service.create_target(data)
        target.current_status = ProbeStatus.UNAVAILABLE
        from app.models.health_probe import ProbeResult
        for i in range(2):
            result = ProbeResult(
                id=f"r{i}", target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://a.com",
                success=True, response_time_ms=50.0,
            )
            service._update_target_status(target, result)
        assert target.current_status == ProbeStatus.AVAILABLE

    def test_becomes_unavailable(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", failure_threshold=2)
        target = service.create_target(data)
        target.current_status = ProbeStatus.AVAILABLE
        from app.models.health_probe import ProbeResult
        for i in range(2):
            result = ProbeResult(
                id=f"r{i}", target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://a.com",
                success=False, error_message="timeout",
            )
            service._update_target_status(target, result)
        assert target.current_status == ProbeStatus.UNAVAILABLE


class TestProbeNow:
    @pytest.mark.asyncio
    async def test_probe_now_http(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        with patch.object(service, "_execute_http_probe", new_callable=AsyncMock) as mock_probe:
            from app.models.health_probe import ProbeResult
            mock_probe.return_value = ProbeResult(
                id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://example.com",
                success=True, response_time_ms=50.0,
            )
            result = await service.probe_now(target.id)
            assert result is not None
            assert result.success is True

    @pytest.mark.asyncio
    async def test_probe_now_not_found(self, service):
        result = await service.probe_now("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_probe_now_tcp(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.TCP, target="example.com:80")
        target = service.create_target(data)
        with patch.object(service, "_execute_tcp_probe", new_callable=AsyncMock) as mock_probe:
            from app.models.health_probe import ProbeResult
            mock_probe.return_value = ProbeResult(
                id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.TCP, target="example.com:80",
                success=True, response_time_ms=20.0,
            )
            result = await service.probe_now(target.id)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_probe_now_icmp(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.ICMP, target="192.168.1.1")
        target = service.create_target(data)
        with patch.object(service, "_execute_icmp_probe", new_callable=AsyncMock) as mock_probe:
            from app.models.health_probe import ProbeResult
            mock_probe.return_value = ProbeResult(
                id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.ICMP, target="192.168.1.1",
                success=True, response_time_ms=5.0,
            )
            result = await service.probe_now(target.id)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_probe_now_exception(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://example.com")
        target = service.create_target(data)
        with patch.object(service, "_execute_http_probe", new_callable=AsyncMock, side_effect=Exception("err")):
            result = await service.probe_now(target.id)
            assert result is not None
            assert result.success is False


class TestExecuteProbe:
    @pytest.mark.asyncio
    async def test_execute_probe_disabled(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com", enabled=False)
        target = service.create_target(data)
        with patch.object(service, "_execute_http_probe", new_callable=AsyncMock) as mock:
            await service._execute_probe(target.id)
            mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_probe_not_found(self, service):
        await service._execute_probe("nonexistent")


class TestQueryProbeLogs:
    def test_query_probe_logs(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        from app.models.health_probe import ProbeResult
        result = ProbeResult(
            id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
            probe_type=ProbeType.HTTP, target="https://a.com",
            success=True, response_time_ms=50.0,
        )
        service._save_result_to_db(result)
        logs, total = service.query_probe_logs(target.id)
        assert total >= 1

    def test_query_probe_logs_with_time_filter(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        logs, total = service.query_probe_logs(
            target.id,
            time_start=datetime(2020, 1, 1),
            time_end=datetime(2030, 1, 1),
        )
        assert isinstance(total, int)


class TestCalculateStatistics:
    def test_calculate_statistics(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        from app.models.health_probe import ProbeResult
        for i in range(3):
            result = ProbeResult(
                id=str(uuid.uuid4()), target_id=target.id, timestamp=datetime.now(),
                probe_type=ProbeType.HTTP, target="https://a.com",
                success=True, response_time_ms=50.0 + i * 10,
            )
            service._save_result_to_db(result)
        stats = service.calculate_statistics(target.id)
        assert stats is not None
        assert stats.total_probes >= 3

    def test_calculate_statistics_not_found(self, service):
        result = service.calculate_statistics("nonexistent")
        assert result is None


class TestGetOverview:
    def test_get_overview(self, service):
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        service.create_target(data)
        overview = service.get_overview()
        assert overview.total_targets >= 1
        assert overview.unknown_count >= 1


class TestAddRemoveProbeJob:
    def test_add_probe_job_no_scheduler(self, service):
        service._scheduler = None
        data = ProbeTargetCreate(name="test", probe_type=ProbeType.HTTP, target="https://a.com")
        target = service.create_target(data)
        service._add_probe_job(target)

    def test_remove_probe_job_no_scheduler(self, service):
        service._scheduler = None
        service._remove_probe_job("nonexistent")


class TestInitialize:
    @pytest.mark.asyncio
    async def test_initialize(self, service):
        with patch("app.services.health_probe_service.AsyncIOScheduler") as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler
            await service.initialize()
            mock_scheduler.start.assert_called_once()


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown(self, service):
        service._scheduler = MagicMock()
        await service.shutdown()
        assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_shutdown_no_scheduler(self, service):
        service._scheduler = None
        await service.shutdown()
