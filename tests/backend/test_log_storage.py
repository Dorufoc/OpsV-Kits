import asyncio
import json
import os
import tempfile
import time

import pytest
import pytest_asyncio

from app.services.log_storage_service import LogStorageService


@pytest_asyncio.fixture
async def storage():
    svc = LogStorageService()
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_log.db")
        await svc.initialize(db_path=db_path)
        yield svc
        await svc.shutdown()


@pytest.mark.asyncio
async def test_initialize_creates_tables(storage):
    log_id = await storage.write_log({
        "timestamp": time.time(),
        "source": "test",
        "level": "INFO",
        "content": "test message",
    })
    assert log_id > 0


@pytest.mark.asyncio
async def test_write_log(storage):
    log_id = await storage.write_log({
        "timestamp": time.time(),
        "source": "test_source",
        "level": "INFO",
        "content": "hello world",
        "structured_data": {"key": "value"},
        "container_name": "web",
        "container_id": "abc123",
        "labels": {"env": "prod"},
        "host": "192.168.1.1",
    })
    assert log_id > 0


@pytest.mark.asyncio
async def test_write_logs_batch(storage):
    entries = [
        {"timestamp": time.time() + i, "source": "batch", "level": "INFO", "content": f"msg {i}"}
        for i in range(5)
    ]
    ids = await storage.write_logs(entries)
    assert len(ids) == 5
    assert all(id > 0 for id in ids)


@pytest.mark.asyncio
async def test_search_fulltext(storage):
    await storage.write_log({"timestamp": time.time(), "source": "s1", "level": "INFO", "content": "error database connection failed"})
    await storage.write_log({"timestamp": time.time(), "source": "s2", "level": "INFO", "content": "request processed successfully"})

    result = await storage.search("error database")
    assert result["total"] >= 1
    assert any("error" in r["content"].lower() for r in result["results"])


@pytest.mark.asyncio
async def test_search_with_filters(storage):
    now = time.time()
    await storage.write_log({"timestamp": now - 100, "source": "app1", "level": "ERROR", "content": "error occurred"})
    await storage.write_log({"timestamp": now, "source": "app2", "level": "INFO", "content": "all good"})

    result = await storage.search("error", filters={"level": "ERROR"})
    assert result["total"] >= 1
    assert all(r["level"] == "ERROR" for r in result["results"])


@pytest.mark.asyncio
async def test_filter_logs(storage):
    now = time.time()
    await storage.write_log({"timestamp": now - 100, "source": "app1", "level": "ERROR", "content": "old error"})
    await storage.write_log({"timestamp": now, "source": "app2", "level": "INFO", "content": "new info"})

    result = await storage.filter_logs({"level": "ERROR"})
    assert result["total"] >= 1
    assert all(r["level"] == "ERROR" for r in result["results"])


@pytest.mark.asyncio
async def test_filter_by_time_range(storage):
    now = time.time()
    await storage.write_log({"timestamp": now - 3600, "source": "old", "level": "INFO", "content": "old log"})
    await storage.write_log({"timestamp": now, "source": "new", "level": "INFO", "content": "new log"})

    result = await storage.filter_logs({"time_start": now - 60, "time_end": now + 60})
    assert result["total"] >= 1
    assert all(r["source"] == "new" for r in result["results"])


@pytest.mark.asyncio
async def test_get_trend(storage):
    now = time.time()
    for i in range(10):
        await storage.write_log({"timestamp": now - i * 60, "source": "app", "level": "INFO", "content": f"log {i}"})

    trend = await storage.get_trend(now - 600, now, granularity="minute")
    assert len(trend) > 0
    assert "bucket" in trend[0]
    assert "count" in trend[0]


@pytest.mark.asyncio
async def test_get_source_distribution(storage):
    now = time.time()
    for src in ["app1", "app2", "app1", "app3"]:
        await storage.write_log({"timestamp": now, "source": src, "level": "INFO", "content": "msg"})

    dist = await storage.get_source_distribution(now - 60, now + 60, top_n=10)
    assert len(dist) > 0
    assert dist[0]["source"] == "app1"


@pytest.mark.asyncio
async def test_get_level_distribution(storage):
    now = time.time()
    for level in ["INFO", "ERROR", "INFO", "WARN"]:
        await storage.write_log({"timestamp": now, "source": "app", "level": level, "content": "msg"})

    dist = await storage.get_level_distribution(now - 60, now + 60)
    assert len(dist) > 0


@pytest.mark.asyncio
async def test_get_context(storage):
    now = time.time()
    ids = []
    for i in range(10):
        log_id = await storage.write_log({"timestamp": now + i, "source": "ctx", "level": "INFO", "content": f"log line {i}"})
        ids.append(log_id)

    target_id = ids[5]
    ctx = await storage.get_context(target_id, before=2, after=2)
    assert ctx["target"] is not None
    assert ctx["target"]["id"] == target_id
    assert len(ctx["before"]) <= 2
    assert len(ctx["after"]) <= 2


@pytest.mark.asyncio
async def test_pagination(storage):
    for i in range(25):
        await storage.write_log({"timestamp": time.time() + i * 0.01, "source": "page", "level": "INFO", "content": f"msg {i}"})

    page1 = await storage.filter_logs({"source": "page"}, page=1, page_size=10)
    assert page1["page"] == 1
    assert page1["page_size"] == 10
    assert len(page1["results"]) == 10
    assert page1["total"] == 25
