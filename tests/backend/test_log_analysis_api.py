import os
import tempfile
import time

import httpx
import pytest
import pytest_asyncio

from app.main import app
from app.services.log_storage_service import log_storage_service
from app.services.log_alert_service import log_alert_service


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    if log_storage_service._db is not None:
        await log_storage_service.shutdown()
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_api.db")
        await log_storage_service.initialize(db_path=db_path)
        await log_alert_service.initialize()
        yield
        await log_alert_service.shutdown()
        await log_storage_service.shutdown()


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_search_logs(client):
    resp = await client.post("/api/log-analysis/search", json={
        "query": "test",
        "filters": {},
        "page": 1,
        "page_size": 50,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "results" in data


@pytest.mark.asyncio
async def test_filter_logs(client):
    resp = await client.post("/api/log-analysis/filter", json={
        "filters": {"level": "INFO"},
        "page": 1,
        "page_size": 50,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_aggregation(client):
    now = time.time()
    resp = await client.get("/api/log-analysis/aggregation", params={
        "type": "level_distribution",
        "time_start": now - 3600,
        "time_end": now,
    })
    assert resp.status_code == 200
    assert "data" in resp.json()


@pytest.mark.asyncio
async def test_get_sources(client):
    resp = await client.get("/api/log-analysis/sources")
    assert resp.status_code == 200
    assert "sources" in resp.json()


@pytest.mark.asyncio
async def test_add_source(client):
    resp = await client.post("/api/log-analysis/sources", json={
        "type": "system",
        "alias": "test-server",
        "path": "/var/log/syslog",
        "enabled": False,
    })
    assert resp.status_code == 200
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_get_alert_rules(client):
    resp = await client.get("/api/log-analysis/alerts/rules")
    assert resp.status_code == 200
    assert "rules" in resp.json()


@pytest.mark.asyncio
async def test_create_alert_rule(client):
    resp = await client.post("/api/log-analysis/alerts/rules", json={
        "name": "Test Alert",
        "pattern": "error",
        "pattern_type": "keyword",
        "time_window": 300,
        "threshold": 1,
        "enabled": True,
        "silence_period": 3600,
    })
    assert resp.status_code == 200
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_get_alert_events(client):
    resp = await client.get("/api/log-analysis/alerts/events", params={"hours": 24})
    assert resp.status_code == 200
    assert "events" in resp.json()


@pytest.mark.asyncio
async def test_get_context_not_found(client):
    resp = await client.get("/api/log-analysis/context", params={"log_id": 999999})
    assert resp.status_code == 404
