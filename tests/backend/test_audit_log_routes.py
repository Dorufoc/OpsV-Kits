from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.audit_log import (
    AuditArchiveInfo,
    AuditLog,
    AuditLogPageResult,
    AuditLogStatistics,
    AuditLogVerifyResult,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_service():
    with patch("app.api.routes.audit_log.audit_log_service") as m:
        yield m


def _make_log(**overrides):
    base = AuditLog(
        id="abc123",
        user_id="u1",
        username="admin",
        timestamp=datetime.now(),
        ip_address="127.0.0.1",
        action_type="create",
        module="ssh",
        detail=None,
        status="success",
        client_info="",
        request_path="/api/test",
        request_method="POST",
        response_code=200,
        duration_ms=10.0,
        hash="",
        sensitive=False,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


class TestQueryAuditLogs:
    def test_query_success(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=0, page=1, page_size=20, total_pages=0, items=[],
        ))
        resp = client.post("/api/audit-log/query", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_query_with_filters(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=1, page=1, page_size=20, total_pages=1, items=[_make_log()],
        ))
        resp = client.post(
            "/api/audit-log/query",
            json={"username": "admin", "action_types": ["create"], "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_query_service_error(self, client, mock_service):
        mock_service.query = AsyncMock(side_effect=Exception("db error"))
        resp = client.post("/api/audit-log/query", json={})
        assert resp.status_code == 500


class TestGetAuditLog:
    def test_get_by_id_success(self, client, mock_service):
        mock_service.get_by_id = AsyncMock(return_value=_make_log(id="log-001"))
        resp = client.get("/api/audit-log/log-001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "log-001"

    def test_get_by_id_not_found(self, client, mock_service):
        mock_service.get_by_id = AsyncMock(return_value=None)
        resp = client.get("/api/audit-log/nonexistent")
        assert resp.status_code == 404

    def test_get_by_id_service_error(self, client, mock_service):
        mock_service.get_by_id = AsyncMock(side_effect=Exception("fail"))
        resp = client.get("/api/audit-log/log-001")
        assert resp.status_code == 500

    def test_get_by_id_reraises_http_exception(self, client, mock_service):
        from fastapi import HTTPException
        mock_service.get_by_id = AsyncMock(side_effect=HTTPException(404, "not found"))
        resp = client.get("/api/audit-log/some-id")
        assert resp.status_code == 404


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_statistics_success(self, mock_service):
        from app.api.routes.audit_log import get_statistics
        mock_service.get_statistics = AsyncMock(return_value=AuditLogStatistics())
        result = await get_statistics(time_start=None, time_end=None, granularity="day")
        assert result.trend == []

    @pytest.mark.asyncio
    async def test_statistics_with_time_range(self, mock_service):
        from app.api.routes.audit_log import get_statistics
        mock_service.get_statistics = AsyncMock(return_value=AuditLogStatistics())
        result = await get_statistics(
            time_start="2025-01-01T00:00:00", time_end="2025-12-31T23:59:59", granularity="week",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_statistics_service_error(self, mock_service):
        from app.api.routes.audit_log import get_statistics
        from fastapi import HTTPException
        mock_service.get_statistics = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(HTTPException) as exc_info:
            await get_statistics()
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_statistics_no_time_params(self, mock_service):
        from app.api.routes.audit_log import get_statistics
        mock_service.get_statistics = AsyncMock(return_value=AuditLogStatistics())
        result = await get_statistics(time_start=None, time_end=None, granularity="day")
        mock_service.get_statistics.assert_awaited_once_with(None, None, "day")


class TestExportAuditLogs:
    def test_export_sync_small_xlsx(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=50, page=1, page_size=10000, total_pages=1, items=[],
        ))
        mock_service.export_excel = AsyncMock(return_value=None)
        resp = client.post(
            "/api/audit-log/export",
            json={"query": {}, "format": "xlsx"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert "download_url" in data
        assert data["format"] == "xlsx"
        assert data["record_count"] == 50

    def test_export_csv_format(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=10, page=1, page_size=10000, total_pages=1, items=[],
        ))
        mock_service.export_csv = AsyncMock(return_value=None)
        resp = client.post(
            "/api/audit-log/export",
            json={"query": {}, "format": "csv"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "csv"

    def test_export_pdf_format(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=5, page=1, page_size=10000, total_pages=1, items=[],
        ))
        mock_service.export_pdf = AsyncMock(return_value=None)
        resp = client.post(
            "/api/audit-log/export",
            json={"query": {}, "format": "pdf"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "pdf"

    def test_export_invalid_format_defaults_xlsx(self, client, mock_service):
        mock_service.query = AsyncMock(return_value=AuditLogPageResult(
            total=5, page=1, page_size=10000, total_pages=1, items=[],
        ))
        mock_service.export_excel = AsyncMock(return_value=None)
        resp = client.post(
            "/api/audit-log/export",
            json={"query": {}, "format": "invalid"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "xlsx"

    def test_export_service_error(self, client, mock_service):
        mock_service.query = AsyncMock(side_effect=Exception("fail"))
        resp = client.post(
            "/api/audit-log/export",
            json={"query": {}, "format": "xlsx"},
        )
        assert resp.status_code == 500


class TestDownloadExport:
    def test_download_task_not_found(self, client, mock_service):
        resp = client.get("/api/audit-log/export/nonexistent/download", params={"format": "xlsx"})
        assert resp.status_code == 404

    def test_download_task_processing(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        task_id = "proc-task-001"
        _export_tasks[task_id] = {"status": "processing", "output_path": "/tmp/fake.xlsx", "format": "xlsx", "record_count": 0}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "xlsx"})
            assert resp.status_code == 202
        finally:
            _export_tasks.pop(task_id, None)

    def test_download_task_failed(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        task_id = "fail-task-001"
        _export_tasks[task_id] = {"status": "failed", "error": "disk full", "format": "xlsx", "record_count": 0}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "xlsx"})
            assert resp.status_code == 500
        finally:
            _export_tasks.pop(task_id, None)

    def test_download_file_not_found(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        task_id = "nofile-task-001"
        _export_tasks[task_id] = {"status": "completed", "output_path": "/nonexistent/file.xlsx", "format": "xlsx", "record_count": 0}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "xlsx"})
            assert resp.status_code == 404
        finally:
            _export_tasks.pop(task_id, None)

    def test_download_success(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"fake xlsx content")
            tmp_path = f.name
        task_id = "ok-task-001"
        _export_tasks[task_id] = {"status": "completed", "output_path": tmp_path, "format": "xlsx", "record_count": 10}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "xlsx"})
            assert resp.status_code == 200
        finally:
            _export_tasks.pop(task_id, None)
            Path(tmp_path).unlink(missing_ok=True)

    def test_download_csv_media_type(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"a,b\n1,2")
            tmp_path = f.name
        task_id = "csv-task-001"
        _export_tasks[task_id] = {"status": "completed", "output_path": tmp_path, "format": "csv", "record_count": 1}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "csv"})
            assert resp.status_code == 200
            assert "text/csv" in resp.headers.get("content-type", "")
        finally:
            _export_tasks.pop(task_id, None)
            Path(tmp_path).unlink(missing_ok=True)

    def test_download_pdf_media_type(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4")
            tmp_path = f.name
        task_id = "pdf-task-001"
        _export_tasks[task_id] = {"status": "completed", "output_path": tmp_path, "format": "pdf", "record_count": 1}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "pdf"})
            assert resp.status_code == 200
            assert "application/pdf" in resp.headers.get("content-type", "")
        finally:
            _export_tasks.pop(task_id, None)
            Path(tmp_path).unlink(missing_ok=True)

    def test_download_unexpected_error(self, client, mock_service):
        from app.api.routes.audit_log import _export_tasks
        task_id = "err-task-001"
        _export_tasks[task_id] = {"status": "completed", "output_path": None, "format": "xlsx", "record_count": 0}
        try:
            resp = client.get(f"/api/audit-log/export/{task_id}/download", params={"format": "xlsx"})
            assert resp.status_code == 500
        finally:
            _export_tasks.pop(task_id, None)


class TestVerifyAuditLogs:
    def test_verify_success(self, client, mock_service):
        mock_service.verify_integrity = AsyncMock(return_value=AuditLogVerifyResult(
            total=100, passed=98, failed=2, failed_ids=["id1", "id2"],
        ))
        resp = client.post("/api/audit-log/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 100
        assert data["failed"] == 2

    def test_verify_with_log_id(self, client, mock_service):
        mock_service.verify_integrity = AsyncMock(return_value=AuditLogVerifyResult(
            total=1, passed=1, failed=0, failed_ids=[],
        ))
        resp = client.post("/api/audit-log/verify", json={"log_id": "abc"})
        assert resp.status_code == 200
        mock_service.verify_integrity.assert_awaited_once_with("abc")

    def test_verify_service_error(self, client, mock_service):
        mock_service.verify_integrity = AsyncMock(side_effect=Exception("fail"))
        resp = client.post("/api/audit-log/verify")
        assert resp.status_code == 500


class TestListArchives:
    @pytest.mark.asyncio
    async def test_list_archives_success(self, mock_service):
        from app.api.routes.audit_log import list_archives
        mock_service.list_archives = AsyncMock(return_value=[
            AuditArchiveInfo(filename="archive_2025.db", size_bytes=1024, record_count=50, period_start="2025-01-01", period_end="2025-06-01")
        ])
        result = await list_archives()
        assert len(result) == 1
        assert result[0].filename == "archive_2025.db"

    @pytest.mark.asyncio
    async def test_list_archives_empty(self, mock_service):
        from app.api.routes.audit_log import list_archives
        mock_service.list_archives = AsyncMock(return_value=[])
        result = await list_archives()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_archives_service_error(self, mock_service):
        from app.api.routes.audit_log import list_archives
        from fastapi import HTTPException
        mock_service.list_archives = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(HTTPException) as exc_info:
            await list_archives()
        assert exc_info.value.status_code == 500


class TestGetRecentLogs:
    @pytest.mark.asyncio
    async def test_recent_logs_success(self, mock_service):
        from app.api.routes.audit_log import get_recent_logs
        mock_service.get_recent_logs = AsyncMock(return_value=[_make_log(id="r1"), _make_log(id="r2")])
        result = await get_recent_logs(limit=5)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_recent_logs_default_limit(self, mock_service):
        from app.api.routes.audit_log import get_recent_logs
        mock_service.get_recent_logs = AsyncMock(return_value=[])
        await get_recent_logs(limit=5)
        mock_service.get_recent_logs.assert_awaited_once_with(5)

    @pytest.mark.asyncio
    async def test_recent_logs_service_error(self, mock_service):
        from app.api.routes.audit_log import get_recent_logs
        from fastapi import HTTPException
        mock_service.get_recent_logs = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(HTTPException) as exc_info:
            await get_recent_logs(limit=10)
        assert exc_info.value.status_code == 500
