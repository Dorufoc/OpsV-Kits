from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.audit_log_service import AuditLogService
from app.models.audit_log import AuditLogQuery


@pytest.fixture
def service():
    return AuditLogService()


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_audit_extra2.db")


@pytest_asyncio.fixture
async def initialized_service(service, temp_db):
    await service.initialize(temp_db)
    yield service
    await service.shutdown()


def _sample_entry(**overrides):
    entry = {
        "id": "extra2_test_1",
        "user_id": "user_extra2",
        "username": "admin_extra2",
        "timestamp": datetime.now().isoformat(),
        "ip_address": "10.0.0.2",
        "action_type": "create",
        "module": "docker",
        "detail": json.dumps({"key": "val"}),
        "status": "success",
        "client_info": "TestClient/2.0",
        "request_path": "/api/docker",
        "request_method": "POST",
        "response_code": 200,
        "duration_ms": 5.0,
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


class TestInitializeDefaultPath:
    @pytest.mark.asyncio
    async def test_initialize_with_none_db_path(self, tmp_path):
        svc = AuditLogService()
        fake_module_file = str(tmp_path / "fake_service.py")
        Path(fake_module_file).touch()
        with patch("app.services.audit_log_service.__file__", fake_module_file):
            await svc.initialize(db_path=None)
            assert svc._db is not None
            assert svc._db_path is not None
            assert "data" in svc._db_path or "audit_logs" in svc._db_path
        await svc.shutdown()


class TestShutdownWithRemainingQueueItems:
    @pytest.mark.asyncio
    async def test_shutdown_with_items_in_queue(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        svc._queue.put_nowait(entry)
        await svc.shutdown()
        svc2 = AuditLogService()
        await svc2.initialize(temp_db)
        result = await svc2.get_by_id("extra2_test_1")
        assert result is not None
        await svc2.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_queue_get_raises_empty(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        svc._queue = MagicMock()
        svc._queue.empty.side_effect = [False, True]
        svc._queue.get_nowait.side_effect = asyncio.QueueEmpty()
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_no_remaining_items(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        while not svc._queue.empty():
            try:
                svc._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        await svc.shutdown()


class TestQueueConsumerLoopTimeout:
    @pytest.mark.asyncio
    async def test_consumer_timeout_flushes_batch(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        svc._queue.put_nowait(entry)
        await asyncio.sleep(svc.BATCH_FLUSH_INTERVAL + 1.0)
        result = await svc.get_by_id("extra2_test_1")
        assert result is not None
        await svc.shutdown()

    @pytest.mark.asyncio
    async def test_consumer_batch_max_size_flush(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        entries = []
        for i in range(svc.BATCH_MAX_SIZE):
            e = _sample_entry(id=f"batch_{i}")
            e["hash"] = _compute_correct_hash(e)
            entries.append(e)
        for e in entries:
            svc._queue.put_nowait(e)
        await asyncio.sleep(2.0)
        for i in range(svc.BATCH_MAX_SIZE):
            result = await svc.get_by_id(f"batch_{i}")
            assert result is not None
        await svc.shutdown()


class TestQueueConsumerLoopCancelled:
    @pytest.mark.asyncio
    async def test_consumer_cancelled_with_batch(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        entry = _sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        svc._queue.put_nowait(entry)
        await svc.shutdown()
        svc2 = AuditLogService()
        await svc2.initialize(temp_db)
        result = await svc2.get_by_id("extra2_test_1")
        assert result is not None
        await svc2.shutdown()


class TestQueueConsumerLoopException:
    @pytest.mark.asyncio
    async def test_consumer_exception_clears_batch(self, temp_db):
        svc = AuditLogService()
        await svc.initialize(temp_db)
        with patch.object(svc, "_write_batch", new_callable=AsyncMock, side_effect=Exception("db error")):
            entry = _sample_entry()
            entry["hash"] = _compute_correct_hash(entry)
            svc._queue.put_nowait(entry)
            await asyncio.sleep(2.0)
        await svc.shutdown()


class TestWriteBatchRollback:
    @pytest.mark.asyncio
    async def test_write_batch_rollback_on_duplicate_id(self, initialized_service):
        entry1 = _sample_entry(id="dup_test")
        entry1["hash"] = _compute_correct_hash(entry1)
        await initialized_service._write_batch([entry1])
        entry2 = _sample_entry(id="dup_test", username="second_user")
        entry2["hash"] = _compute_correct_hash(entry2)
        with pytest.raises(Exception):
            await initialized_service._write_batch([entry2])
        result = await initialized_service.get_by_id("dup_test")
        assert result.username == "admin_extra2"
