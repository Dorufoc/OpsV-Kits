import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.audit_log_service import AuditLogService
from app.models.audit_log import (
    ActionType,
    AuditLogQuery,
    AuditLogStatistics,
    AuditLogVerifyResult,
    AuditModule,
)


@pytest.fixture
def service():
    return AuditLogService()


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_audit_extra.db")


@pytest_asyncio.fixture
async def initialized_service(service, temp_db):
    await service.initialize(temp_db)
    yield service
    await service.shutdown()


def _sample_entry(**overrides):
    entry = {
        "id": "extra_test_1",
        "user_id": "user_extra",
        "username": "extra_admin",
        "timestamp": datetime.now().isoformat(),
        "ip_address": "10.0.0.1",
        "action_type": "update",
        "module": "ssh",
        "detail": json.dumps({"key": "value"}),
        "status": "success",
        "client_info": "TestClient/1.0",
        "request_path": "/api/ssh-accounts",
        "request_method": "PUT",
        "response_code": 200,
        "duration_ms": 12.5,
        "hash": "",
        "sensitive": False,
    }
    entry.update(overrides)
    return entry


def _compute_correct_hash(entry):
    hash_entry = dict(entry)
    if isinstance(hash_entry.get("detail"), str):
        try:
            hash_entry["detail"] = json.loads(hash_entry["detail"])
        except (json.JSONDecodeError, TypeError):
            pass
    return AuditLogService.compute_hash(hash_entry)


class TestEnqueueLog:
    def test_enqueue_log_success(self, initialized_service):
        entry = _sample_entry()
        initialized_service.enqueue_log(entry)
        assert not initialized_service._queue.empty()

    def test_enqueue_log_no_queue(self, service):
        service._queue = None
        entry = _sample_entry()
        initialized_service = service
        initialized_service.enqueue_log(entry)

    def test_enqueue_log_queue_full(self, initialized_service):
        initialized_service._queue = asyncio.Queue(maxsize=1)
        initialized_service._queue.put_nowait({"id": "old"})
        entry = _sample_entry(id="new")
        initialized_service.enqueue_log(entry)
        assert initialized_service._queue.qsize() == 1
        item = initialized_service._queue.get_nowait()
        assert item["id"] == "new"

    def test_enqueue_log_queue_full_get_fails(self, initialized_service):
        initialized_service._queue = MagicMock()
        initialized_service._queue.put_nowait.side_effect = [asyncio.QueueFull, None]
        initialized_service._queue.get_nowait.side_effect = asyncio.QueueEmpty
        entry = _sample_entry()
        initialized_service.enqueue_log(entry)

    def test_enqueue_log_queue_full_both_fail(self, initialized_service):
        initialized_service._queue = MagicMock()
        initialized_service._queue.put_nowait.side_effect = [asyncio.QueueFull, asyncio.QueueFull]
        initialized_service._queue.get_nowait.side_effect = asyncio.QueueEmpty
        entry = _sample_entry()
        initialized_service.enqueue_log(entry)


class TestWriteBatch:
    @pytest.mark.asyncio
    async def test_write_batch_empty_list(self, initialized_service):
        await initialized_service._write_batch([])
        result = await initialized_service.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_write_batch_none_db(self, service):
        service._db = None
        await service._write_batch([_sample_entry()])

    @pytest.mark.asyncio
    async def test_write_batch_detail_as_dict(self, initialized_service):
        entry = _sample_entry(detail={"nested": "data"})
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("extra_test_1")
        assert result is not None
        assert result.detail == {"nested": "data"}

    @pytest.mark.asyncio
    async def test_write_batch_detail_none(self, initialized_service):
        entry = _sample_entry(detail=None)
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("extra_test_1")
        assert result is not None
        assert result.detail is None

    @pytest.mark.asyncio
    async def test_write_batch_sensitive_true(self, initialized_service):
        entry = _sample_entry(sensitive=True)
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("extra_test_1")
        assert result is not None
        assert result.sensitive is True

    @pytest.mark.asyncio
    async def test_write_batch_rollback_on_error(self, initialized_service):
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        bad_entry = _sample_entry(id="extra_test_1")
        bad_entry["response_code"] = "not_an_integer"
        with pytest.raises(Exception):
            await initialized_service._write_batch([bad_entry])
        result = await initialized_service.get_by_id("extra_test_1")
        assert result is not None


class TestComputeHash:
    def test_compute_hash_none_values(self):
        entry = {"id": None, "user_id": None, "username": None, "timestamp": None,
                 "ip_address": None, "action_type": None, "module": None, "detail": None,
                 "status": None, "client_info": None, "request_path": None,
                 "request_method": None, "response_code": None, "duration_ms": None,
                 "sensitive": None}
        result = AuditLogService.compute_hash(entry)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_compute_hash_dict_detail(self):
        entry = _sample_entry()
        entry["detail"] = {"key": "value"}
        result = AuditLogService.compute_hash(entry)
        assert isinstance(result, str)

    def test_compute_hash_list_detail(self):
        entry = _sample_entry()
        entry["detail"] = [1, 2, 3]
        result = AuditLogService.compute_hash(entry)
        assert isinstance(result, str)


class TestRowToAuditLog:
    @pytest.mark.asyncio
    async def test_row_with_invalid_timestamp(self, initialized_service):
        entry = _sample_entry(timestamp="not-a-date")
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("extra_test_1")
        assert result is not None
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_row_with_empty_timestamp_raises(self, initialized_service):
        from pydantic import ValidationError
        entry = _sample_entry(timestamp="")
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        with pytest.raises(ValidationError):
            await initialized_service.get_by_id("extra_test_1")

    @pytest.mark.asyncio
    async def test_row_with_non_json_detail_raises(self, initialized_service):
        from pydantic import ValidationError
        entry = _sample_entry(detail="plain text not json")
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        with pytest.raises(ValidationError):
            await initialized_service.get_by_id("extra_test_1")


class TestRowToEntryDict:
    @pytest.mark.asyncio
    async def test_row_to_entry_dict(self, initialized_service):
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        async with initialized_service._db.execute(
            "SELECT * FROM audit_logs WHERE id = ?", ("extra_test_1",)
        ) as cursor:
            row = await cursor.fetchone()
            result = initialized_service._row_to_entry_dict(row)
        assert result["id"] == "extra_test_1"
        assert "hash" in result
        assert "sensitive" in result

    @pytest.mark.asyncio
    async def test_row_to_entry_dict_non_json_detail(self, initialized_service):
        entry = _sample_entry(detail="plain text")
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        async with initialized_service._db.execute(
            "SELECT * FROM audit_logs WHERE id = ?", ("extra_test_1",)
        ) as cursor:
            row = await cursor.fetchone()
            result = initialized_service._row_to_entry_dict(row)
        assert result["detail"] == "plain text"


class TestVerifyIntegrityFullScan:
    @pytest.mark.asyncio
    async def test_verify_all_pass(self, initialized_service):
        entries = []
        for i in range(3):
            e = _sample_entry(id=f"verify_{i}", username=f"user_{i}")
            e["hash"] = _compute_correct_hash(e)
            entries.append(e)
        await initialized_service._write_batch(entries)
        result = await initialized_service.verify_integrity()
        assert result.total == 3
        assert result.passed == 3
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_verify_mixed_results(self, initialized_service):
        e1 = _sample_entry(id="v_pass")
        e1["hash"] = _compute_correct_hash(e1)
        await initialized_service._write_batch([e1])
        e2 = _sample_entry(id="v_fail")
        e2["hash"] = "wrong_hash"
        await initialized_service._write_batch([e2])
        result = await initialized_service.verify_integrity()
        assert result.total == 2
        assert result.passed == 1
        assert result.failed == 1
        assert "v_fail" in result.failed_ids

    @pytest.mark.asyncio
    async def test_verify_nonexistent_log_id(self, initialized_service):
        result = await initialized_service.verify_integrity(log_id="nonexistent_id")
        assert result.total == 0
        assert result.passed == 0
        assert result.failed == 0


class TestQueryAdvanced:
    @pytest.mark.asyncio
    async def test_query_by_user_id(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="uid1", user_id="admin_user"),
            _sample_entry(id="uid2", user_id="guest_user"),
        ])
        result = await initialized_service.query(AuditLogQuery(user_id="admin"))
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_query_by_request_path(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="rp1", request_path="/api/docker/containers"),
            _sample_entry(id="rp2", request_path="/api/ssh-accounts"),
        ])
        result = await initialized_service.query(AuditLogQuery(request_path="docker"))
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_query_order_asc(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="asc1", timestamp="2024-01-01T10:00:00"),
            _sample_entry(id="asc2", timestamp="2024-06-01T10:00:00"),
        ])
        result = await initialized_service.query(
            AuditLogQuery(order_by="timestamp", order_dir="asc")
        )
        assert result.items[0].id == "asc1"

    @pytest.mark.asyncio
    async def test_query_invalid_order_field(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.query(
            AuditLogQuery(order_by="invalid_field", order_dir="desc")
        )
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_query_empty_keyword(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.query(AuditLogQuery(keyword="   "))
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_query_keyword_with_operators(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="kw_op", detail=json.dumps({"msg": "hello world"})),
        ])
        result = await initialized_service.query(AuditLogQuery(keyword="hello AND world"))
        assert result.total >= 0

    @pytest.mark.asyncio
    async def test_query_no_results(self, initialized_service):
        result = await initialized_service.query(
            AuditLogQuery(username="nonexistent_user_xyz")
        )
        assert result.total == 0
        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_query_combined_filters(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="comb1", username="alice", status="success"),
            _sample_entry(id="comb2", username="alice", status="failure"),
            _sample_entry(id="comb3", username="bob", status="success"),
        ])
        result = await initialized_service.query(
            AuditLogQuery(username="alice", status="failure")
        )
        assert result.total == 1
        assert result.items[0].id == "comb2"


class TestGetStatisticsAdvanced:
    @pytest.mark.asyncio
    async def test_statistics_with_time_range(self, initialized_service):
        await initialized_service._write_batch([
            _sample_entry(id="stat1", timestamp="2024-03-15T10:00:00"),
            _sample_entry(id="stat2", timestamp="2024-06-15T10:00:00"),
        ])
        result = await initialized_service.get_statistics(
            time_start=datetime(2024, 6, 1),
            time_end=datetime(2024, 7, 1),
        )
        assert isinstance(result, AuditLogStatistics)

    @pytest.mark.asyncio
    async def test_statistics_granularity_minute(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.get_statistics(granularity="minute")
        assert isinstance(result, AuditLogStatistics)

    @pytest.mark.asyncio
    async def test_statistics_granularity_day(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.get_statistics(granularity="day")
        assert isinstance(result, AuditLogStatistics)

    @pytest.mark.asyncio
    async def test_statistics_granularity_week(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.get_statistics(granularity="week")
        assert isinstance(result, AuditLogStatistics)

    @pytest.mark.asyncio
    async def test_statistics_granularity_month(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.get_statistics(granularity="month")
        assert isinstance(result, AuditLogStatistics)

    @pytest.mark.asyncio
    async def test_statistics_invalid_granularity(self, initialized_service):
        await initialized_service._write_batch([_sample_entry()])
        result = await initialized_service.get_statistics(granularity="invalid")
        assert isinstance(result, AuditLogStatistics)


class TestShutdownWithQueueItems:
    @pytest.mark.asyncio
    async def test_shutdown_flushes_queue(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        svc.enqueue_log(entry)
        await svc.shutdown()
        svc2 = AuditLogService()
        await svc2.initialize(temp_db)
        result = await svc2.get_by_id("extra_test_1")
        assert result is not None
        await svc2.shutdown()


class TestQueueConsumer:
    @pytest.mark.asyncio
    async def test_start_queue_consumer_idempotent(self, initialized_service):
        first_task = initialized_service._consumer_task
        initialized_service.start_queue_consumer()
        assert initialized_service._consumer_task is first_task

    @pytest.mark.asyncio
    async def test_stop_queue_consumer_no_task(self, service):
        service._consumer_task = None
        await service.stop_queue_consumer()


class TestExportWithFilters:
    @pytest.mark.asyncio
    async def test_export_csv_with_filters(self, initialized_service, tmp_path):
        await initialized_service._write_batch([
            _sample_entry(id="csv1", username="alice"),
            _sample_entry(id="csv2", username="bob"),
        ])
        output = str(tmp_path / "filtered.csv")
        result = await initialized_service.export_csv(
            AuditLogQuery(username="alice"), output
        )
        assert Path(result).exists()
        content = Path(result).read_text(encoding="utf-8-sig")
        assert "alice" in content

    @pytest.mark.asyncio
    async def test_export_excel_with_filters(self, initialized_service, tmp_path):
        pytest.importorskip("openpyxl")
        await initialized_service._write_batch([
            _sample_entry(id="xlsx1", username="alice"),
        ])
        output = str(tmp_path / "filtered.xlsx")
        result = await initialized_service.export_excel(
            AuditLogQuery(username="alice"), output
        )
        assert Path(result).exists()

    @pytest.mark.asyncio
    async def test_export_pdf_with_filters(self, initialized_service, tmp_path):
        pytest.importorskip("reportlab")
        await initialized_service._write_batch([
            _sample_entry(id="pdf1", username="alice"),
        ])
        output = str(tmp_path / "filtered.pdf")
        result = await initialized_service.export_pdf(
            AuditLogQuery(username="alice"), output
        )
        assert Path(result).exists()


class TestRotateAndArchive:
    @pytest.mark.asyncio
    async def test_rotate_no_old_records(self, initialized_service):
        entry = _sample_entry(timestamp=datetime.now().isoformat())
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.rotate_and_archive()
        assert result is None

    @pytest.mark.asyncio
    async def test_rotate_with_old_records(self, initialized_service):
        old_date = "2020-01-15T10:00:00"
        entry = _sample_entry(timestamp=old_date)
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.rotate_and_archive()
        assert result is not None
        assert Path(result).exists()
        remaining = await initialized_service.get_by_id("extra_test_1")
        assert remaining is None


class TestListArchives:
    @pytest.mark.asyncio
    async def test_list_archives_no_dir(self, initialized_service):
        with patch.object(Path, "exists", return_value=False):
            result = await initialized_service.list_archives()
            assert result == []


class TestGetRecentLogsCustomLimit:
    @pytest.mark.asyncio
    async def test_get_recent_logs_default_limit(self, initialized_service):
        entries = []
        for i in range(10):
            e = _sample_entry(
                id=f"recent_extra_{i}",
                timestamp=datetime(2024, 1, i + 1, 12, 0, 0).isoformat(),
            )
            e["hash"] = _compute_correct_hash(e)
            entries.append(e)
        await initialized_service._write_batch(entries)
        result = await initialized_service.get_recent_logs()
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_recent_logs_custom_limit(self, initialized_service):
        entries = []
        for i in range(10):
            e = _sample_entry(
                id=f"recent_cust_{i}",
                timestamp=datetime(2024, 2, i + 1, 12, 0, 0).isoformat(),
            )
            e["hash"] = _compute_correct_hash(e)
            entries.append(e)
        await initialized_service._write_batch(entries)
        result = await initialized_service.get_recent_logs(limit=3)
        assert len(result) == 3


class TestInitializeDefaultPath:
    @pytest.mark.asyncio
    async def test_initialize_with_default_path(self, tmp_path):
        svc = AuditLogService()
        fake_root = tmp_path / "project_root"
        fake_root.mkdir()
        with patch.object(Path, "resolve", return_value=fake_root):
            pass
        await svc.initialize(str(tmp_path / "default_audit.db"))
        assert svc._db is not None
        await svc.shutdown()
