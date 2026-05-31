import sys
import pytest
import pytest_asyncio
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

_task_scheduler_backup = sys.modules.get("app.services.task_scheduler_service")
sys.modules["app.services.task_scheduler_service"] = MagicMock(
    task_scheduler_service=MagicMock()
)

from app.main import app
from app.services.audit_log_service import AuditLogService

if _task_scheduler_backup is not None:
    sys.modules["app.services.task_scheduler_service"] = _task_scheduler_backup
else:
    sys.modules.pop("app.services.task_scheduler_service", None)
from app.models.audit_log import (
    AuditLogQuery,
    ActionType,
    AuditModule,
    AuditLog,
    AuditLogPageResult,
    AuditLogStatistics,
    AuditLogVerifyResult,
    AuditArchiveInfo,
)
from app.api.routes.audit_log import (
    get_statistics as get_statistics_handler,
    list_archives as list_archives_handler,
    get_recent_logs as get_recent_logs_handler,
)


@pytest.fixture
def service():
    return AuditLogService()


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_audit.db")


@pytest_asyncio.fixture
async def initialized_service(service, temp_db):
    await service.initialize(temp_db)
    yield service
    await service.shutdown()


def sample_entry(**overrides):
    entry = {
        "id": "test123",
        "user_id": "user1",
        "username": "admin",
        "timestamp": datetime.now().isoformat(),
        "ip_address": "192.168.1.1",
        "action_type": "create",
        "module": "docker",
        "detail": json.dumps({"container": "nginx"}),
        "status": "success",
        "client_info": "Mozilla/5.0",
        "request_path": "/api/docker",
        "request_method": "POST",
        "response_code": 200,
        "duration_ms": 45.2,
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


@pytest.fixture
def client():
    return TestClient(app)


class TestAuditLogService:

    @pytest.mark.asyncio
    async def test_initialize_creates_db(self, service, temp_db):
        await service.initialize(temp_db)
        assert Path(temp_db).exists()
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_write_and_read_log(self, initialized_service):
        entry = sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("test123")
        assert result is not None
        assert result.id == "test123"
        assert result.username == "admin"

    @pytest.mark.asyncio
    async def test_batch_write(self, initialized_service):
        entries = []
        for i in range(5):
            e = sample_entry(id=f"batch_{i}", username=f"user_{i}")
            entries.append(e)
        await initialized_service._write_batch(entries)
        for i in range(5):
            result = await initialized_service.get_by_id(f"batch_{i}")
            assert result is not None
            assert result.username == f"user_{i}"

    def test_compute_hash(self):
        entry = sample_entry()
        hash1 = AuditLogService.compute_hash(entry)
        hash2 = AuditLogService.compute_hash(entry)
        assert hash1 == hash2
        entry["username"] = "modified"
        hash3 = AuditLogService.compute_hash(entry)
        assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_query_by_username(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="u1", username="alice"),
            sample_entry(id="u2", username="bob"),
        ])
        result = await initialized_service.query(AuditLogQuery(username="alice"))
        assert result.total == 1
        assert result.items[0].username == "alice"

    @pytest.mark.asyncio
    async def test_query_by_action_type(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="a1", action_type="create"),
            sample_entry(id="a2", action_type="delete"),
        ])
        result = await initialized_service.query(
            AuditLogQuery(action_types=[ActionType.DELETE])
        )
        assert result.total == 1
        assert result.items[0].action_type == ActionType.DELETE

    @pytest.mark.asyncio
    async def test_query_by_module(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="m1", module="docker"),
            sample_entry(id="m2", module="ssh"),
        ])
        result = await initialized_service.query(
            AuditLogQuery(modules=[AuditModule.SSH])
        )
        assert result.total == 1
        assert result.items[0].module == AuditModule.SSH

    @pytest.mark.asyncio
    async def test_query_by_status(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="s1", status="success"),
            sample_entry(id="s2", status="failure"),
        ])
        result = await initialized_service.query(AuditLogQuery(status="failure"))
        assert result.total == 1
        assert result.items[0].status == "failure"

    @pytest.mark.asyncio
    async def test_query_by_time_range(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="t1", timestamp="2024-01-01T10:00:00"),
            sample_entry(id="t2", timestamp="2024-06-15T10:00:00"),
        ])
        result = await initialized_service.query(
            AuditLogQuery(
                time_start=datetime(2024, 6, 1),
                time_end=datetime(2024, 7, 1),
            )
        )
        assert result.total == 1
        assert result.items[0].id == "t2"

    @pytest.mark.asyncio
    async def test_query_pagination(self, initialized_service):
        entries = []
        for i in range(25):
            entries.append(sample_entry(id=f"page_{i}", username=f"user_{i}"))
        await initialized_service._write_batch(entries)
        result = await initialized_service.query(AuditLogQuery(page=1, page_size=10))
        assert result.total == 25
        assert len(result.items) == 10
        assert result.page == 1
        assert result.total_pages == 3

    @pytest.mark.asyncio
    async def test_query_keyword_search(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="k1", detail=json.dumps({"container": "nginx"})),
            sample_entry(id="k2", detail=json.dumps({"container": "apache"})),
        ])
        result = await initialized_service.query(AuditLogQuery(keyword="nginx"))
        assert result.total >= 1
        found = any("nginx" in str(item.detail) for item in result.items)
        assert found

    @pytest.mark.asyncio
    async def test_get_by_id(self, initialized_service):
        entry = sample_entry()
        await initialized_service._write_batch([entry])
        result = await initialized_service.get_by_id("test123")
        assert result is not None
        assert result.id == "test123"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, initialized_service):
        result = await initialized_service.get_by_id("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_integrity_pass(self, initialized_service):
        entry = sample_entry()
        entry["hash"] = _compute_correct_hash(entry)
        await initialized_service._write_batch([entry])
        result = await initialized_service.verify_integrity("test123")
        assert result.total == 1
        assert result.passed == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_verify_integrity_fail(self, initialized_service):
        entry = sample_entry()
        entry["hash"] = "wrong_hash_value"
        await initialized_service._write_batch([entry])
        result = await initialized_service.verify_integrity("test123")
        assert result.total == 1
        assert result.failed == 1
        assert "test123" in result.failed_ids

    @pytest.mark.asyncio
    async def test_get_statistics(self, initialized_service):
        await initialized_service._write_batch([
            sample_entry(id="st1", module="docker", action_type="create", status="success"),
            sample_entry(id="st2", module="ssh", action_type="delete", status="failure"),
        ])
        result = await initialized_service.get_statistics()
        assert isinstance(result, AuditLogStatistics)
        assert isinstance(result.trend, list)
        assert isinstance(result.module_distribution, list)
        assert isinstance(result.action_distribution, list)
        assert isinstance(result.user_ranking, list)

    @pytest.mark.asyncio
    async def test_get_recent_logs(self, initialized_service):
        entries = []
        for i in range(10):
            entries.append(sample_entry(
                id=f"recent_{i}",
                timestamp=datetime(2024, 1, i + 1, 12, 0, 0).isoformat(),
            ))
        await initialized_service._write_batch(entries)
        result = await initialized_service.get_recent_logs(5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_export_csv(self, initialized_service, tmp_path):
        await initialized_service._write_batch([sample_entry()])
        output = str(tmp_path / "export.csv")
        result = await initialized_service.export_csv(AuditLogQuery(), output)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_export_excel(self, initialized_service, tmp_path):
        pytest.importorskip("openpyxl")
        await initialized_service._write_batch([sample_entry()])
        output = str(tmp_path / "export.xlsx")
        result = await initialized_service.export_excel(AuditLogQuery(), output)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_export_pdf(self, initialized_service, tmp_path):
        pytest.importorskip("reportlab")
        await initialized_service._write_batch([sample_entry()])
        output = str(tmp_path / "export.pdf")
        result = await initialized_service.export_pdf(AuditLogQuery(), output)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    @pytest.mark.asyncio
    async def test_backup_creates_file(self, initialized_service):
        await initialized_service._write_batch([sample_entry()])
        backup_path = await initialized_service.backup()
        assert backup_path is not None
        assert Path(backup_path).exists()
        Path(backup_path).unlink(missing_ok=True)
        result = await initialized_service.get_by_id("test123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_archives(self, initialized_service):
        archives = await initialized_service.list_archives()
        assert isinstance(archives, list)


class TestAuditLogAPI:

    @patch("app.api.routes.audit_log.audit_log_service")
    def test_query_logs(self, mock_service, client):
        mock_result = AuditLogPageResult(
            total=0, page=1, page_size=20, total_pages=0, items=[]
        )
        mock_service.query = AsyncMock(return_value=mock_result)
        response = client.post("/api/audit-log/query", json={})
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    @patch("app.api.routes.audit_log.audit_log_service")
    def test_get_log_detail(self, mock_service, client):
        mock_log = AuditLog(
            id="abc123",
            user_id="user1",
            username="admin",
            timestamp=datetime.now(),
            ip_address="127.0.0.1",
            action_type=ActionType.CREATE,
            module=AuditModule.DOCKER,
            status="success",
        )
        mock_service.get_by_id = AsyncMock(return_value=mock_log)
        response = client.get("/api/audit-log/abc123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "abc123"

    @patch("app.api.routes.audit_log.audit_log_service")
    def test_get_log_detail_not_found(self, mock_service, client):
        mock_service.get_by_id = AsyncMock(return_value=None)
        response = client.get("/api/audit-log/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.routes.audit_log.audit_log_service")
    async def test_get_statistics(self, mock_service):
        mock_stats = AuditLogStatistics()
        mock_service.get_statistics = AsyncMock(return_value=mock_stats)
        result = await get_statistics_handler(
            time_start=None, time_end=None, granularity="day"
        )
        assert isinstance(result, AuditLogStatistics)

    @patch("app.api.routes.audit_log.audit_log_service")
    def test_export_logs(self, mock_service, client):
        mock_result = AuditLogPageResult(
            total=5, page=1, page_size=10000, total_pages=1, items=[]
        )
        mock_service.query = AsyncMock(return_value=mock_result)
        mock_service.export_csv = AsyncMock(return_value="/tmp/export.csv")
        response = client.post("/api/audit-log/export", json={
            "query": {},
            "format": "csv",
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "download_url" in data

    @patch("app.api.routes.audit_log.audit_log_service")
    def test_verify_integrity(self, mock_service, client):
        mock_result = AuditLogVerifyResult(
            total=1, passed=1, failed=0, failed_ids=[]
        )
        mock_service.verify_integrity = AsyncMock(return_value=mock_result)
        response = client.post("/api/audit-log/verify", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["passed"] == 1

    @pytest.mark.asyncio
    @patch("app.api.routes.audit_log.audit_log_service")
    async def test_get_archives(self, mock_service):
        mock_service.list_archives = AsyncMock(return_value=[])
        result = await list_archives_handler()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("app.api.routes.audit_log.audit_log_service")
    async def test_get_recent_logs(self, mock_service):
        mock_service.get_recent_logs = AsyncMock(return_value=[])
        result = await get_recent_logs_handler(limit=5)
        assert isinstance(result, list)


class TestAuditMiddleware:

    def test_middleware_excludes_health(self):
        from app.core.audit_middleware import _should_exclude
        assert _should_exclude("/api/health") is True
        assert _should_exclude("/api/health/status") is True
        assert _should_exclude("/docs") is True
        assert _should_exclude("/openapi.json") is True

    @pytest.mark.asyncio
    async def test_middleware_captures_request(self):
        from app.core.audit_middleware import AuditMiddleware

        async def mock_app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            })
            await send({
                "type": "http.response.body",
                "body": b"OK",
            })

        middleware = AuditMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/docker/containers",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        with patch("app.services.audit_log_service.audit_log_service") as mock_svc:
            mock_svc.enqueue_log = AsyncMock()
            await middleware(scope, lambda: {"type": "http.request", "body": b""}, send)
            mock_svc.enqueue_log.assert_called()
            call_args = mock_svc.enqueue_log.call_args[0][0]
            assert call_args["request_path"] == "/api/docker/containers"
            assert call_args["action_type"] == ActionType.CREATE

    def test_middleware_sensitive_detection(self):
        from app.core.audit_middleware import _is_sensitive
        assert _is_sensitive("/api/ssh-accounts/test-connection") is True
        assert _is_sensitive("/api/webssh/connect") is True
        assert _is_sensitive("/api/security/ssh/config") is True
        assert _is_sensitive("/api/system/reboot") is True
        assert _is_sensitive("/api/docker/containers") is False
        assert _is_sensitive("/api/monitor/metrics") is False

    def test_middleware_sanitizes_passwords(self):
        from app.core.audit_middleware import _sanitize_detail
        detail = {
            "username": "admin",
            "password": "secret123",
            "token": "abc",
            "nested": {
                "secret": "hidden",
                "name": "test",
            },
        }
        result = _sanitize_detail(detail)
        assert result["password"] == "***"
        assert result["token"] == "***"
        assert result["username"] == "admin"
        assert result["nested"]["secret"] == "***"
        assert result["nested"]["name"] == "test"
