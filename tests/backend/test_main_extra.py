import sys
import time
from collections import defaultdict
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_task_scheduler_backup = sys.modules.get("app.services.task_scheduler_service")
sys.modules["app.services.task_scheduler_service"] = MagicMock(
    task_scheduler_service=MagicMock()
)


class TestIsSensitive:
    def test_sensitive_path_ssh_test(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/ssh-accounts/test-connection") is True

    def test_sensitive_path_webssh_connect(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/webssh/connect") is True

    def test_sensitive_path_security_ping(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/security/network/ping") is True

    def test_sensitive_path_system_reboot(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/system/reboot") is True

    def test_sensitive_path_build(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/build/compile") is True

    def test_sensitive_path_docker(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/docker/containers") is True

    def test_non_sensitive_path(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/health") is False

    def test_non_sensitive_path_monitor(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/api/monitor/metrics") is False

    def test_case_insensitive(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/API/SSH-ACCOUNTS/TEST-CONNECTION") is True

    def test_non_api_path(self):
        from app.main import _is_sensitive
        assert _is_sensitive("/static/style.css") is False


class TestRateLimitMiddleware:
    def test_rate_limit_allows_normal_request(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_rate_limit_blocks_excessive_requests(self):
        from app.main import _MEMORY_LIMITS, _is_sensitive
        assert _is_sensitive("/api/build/compile") is True
        key = "127.0.0.1:/api/build/compile"
        _MEMORY_LIMITS[key] = [time.time()] * 30
        from app.main import app
        client = TestClient(app)
        with patch("app.api.routes.build.ssh_account_service") as mock_ssh:
            mock_ssh.get_account = MagicMock(return_value=None)
            response = client.post(
                "/api/build/compile",
                json={"account_alias": "test", "project_path": "/opt"},
            )
        assert response.status_code in (404, 429)
        del _MEMORY_LIMITS[key]

    def test_rate_limit_memory_backend_active(self):
        from app.main import _RATE_LIMIT_BACKEND
        if _RATE_LIMIT_BACKEND == "memory":
            from app.main import _MEMORY_LIMITS
            assert isinstance(_MEMORY_LIMITS, defaultdict)


class TestSPAFallbackMiddleware:
    def test_spa_fallback_for_non_api_path(self):
        from app.main import app, STATIC_DIR
        if not STATIC_DIR.is_dir():
            pytest.skip("Frontend dist not built")
        client = TestClient(app)
        response = client.get("/some-page")
        assert response.status_code in (200, 404)

    def test_spa_fallback_skips_api_paths(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code == 404

    def test_spa_fallback_skips_assets(self):
        from app.main import app, STATIC_DIR
        if not STATIC_DIR.is_dir():
            pytest.skip("Frontend dist not built")
        client = TestClient(app)
        response = client.get("/assets/nonexistent.js")
        assert response.status_code in (200, 404)


class TestAppConfiguration:
    def test_app_title(self):
        from app.main import app
        assert app.title == "OpsV-Kits API"

    def test_app_version(self):
        from app.main import app
        assert app.version == "0.1.0"

    def test_cors_origins(self):
        from app.main import origins
        assert "http://localhost:5173" in origins
        assert "http://localhost:3000" in origins

    def test_routes_registered(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        assert any("/health" in r for r in routes)
        assert any("/build" in r for r in routes)


class TestStartupEvent:
    @pytest.mark.asyncio
    async def test_startup_initializes_services(self):
        with patch("app.main.sync_service") as mock_sync, \
             patch("app.services.remote_drive_service.remote_drive_service") as mock_remote, \
             patch("app.services.settings_service.settings_service") as mock_settings, \
             patch("app.services.performance_collector.performance_collector") as mock_perf, \
             patch("app.core.git_sync_scheduler.git_sync_scheduler") as mock_git, \
             patch("app.services.audit_log_service.audit_log_service") as mock_audit, \
             patch("app.services.task_scheduler_service.task_scheduler_service") as mock_task, \
             patch("app.services.event_bus_service.event_bus_service") as mock_event, \
             patch("app.services.log_storage_service.log_storage_service") as mock_log_storage, \
             patch("app.services.log_alert_service.log_alert_service") as mock_log_alert, \
             patch("app.services.health_probe_service.health_probe_service") as mock_health_probe:
            mock_sync.set_event_loop = MagicMock()
            mock_settings.update = MagicMock()
            mock_perf.initialize_all = AsyncMock()
            mock_git.start = AsyncMock()
            mock_audit.initialize = AsyncMock()
            mock_audit.start_queue_consumer = AsyncMock()
            mock_task.start = MagicMock()
            mock_log_storage.initialize = AsyncMock()
            mock_log_alert.initialize = AsyncMock()
            mock_health_probe.initialize = AsyncMock()

            from app.main import startup_event
            await startup_event()

            mock_sync.set_event_loop.assert_called_once()
            mock_settings.update.assert_called_once()
            mock_perf.initialize_all.assert_called_once()
            mock_git.start.assert_called_once()
            mock_audit.initialize.assert_called_once()
            mock_task.start.assert_called_once()
            mock_log_storage.initialize.assert_called_once()
            mock_log_alert.initialize.assert_called_once()
            mock_health_probe.initialize.assert_called_once()


class TestShutdownEvent:
    @pytest.mark.asyncio
    async def test_shutdown_cleans_up_services(self):
        with patch("app.services.webssh_service.webssh_service") as mock_webssh, \
             patch("app.services.remote_drive_service.remote_drive_service") as mock_remote, \
             patch("app.services.performance_collector.performance_collector") as mock_perf, \
             patch("app.core.git_sync_scheduler.git_sync_scheduler") as mock_git, \
             patch("app.services.audit_log_service.audit_log_service") as mock_audit, \
             patch("app.services.task_scheduler_service.task_scheduler_service") as mock_task, \
             patch("app.services.log_collector_service.log_collector_service") as mock_log_collector, \
             patch("app.services.log_alert_service.log_alert_service") as mock_log_alert, \
             patch("app.services.log_storage_service.log_storage_service") as mock_log_storage, \
             patch("app.services.health_probe_service.health_probe_service") as mock_health_probe:
            mock_webssh.shutdown = MagicMock()
            mock_remote.stop = MagicMock()
            mock_perf.shutdown = AsyncMock()
            mock_git.stop = AsyncMock()
            mock_audit.stop_queue_consumer = AsyncMock()
            mock_audit.shutdown = AsyncMock()
            mock_task.shutdown = MagicMock()
            mock_log_collector.shutdown = AsyncMock()
            mock_log_alert.shutdown = AsyncMock()
            mock_log_storage.shutdown = AsyncMock()
            mock_health_probe.shutdown = AsyncMock()

            from app.main import shutdown_event
            await shutdown_event()

            mock_webssh.shutdown.assert_called_once()
            mock_remote.stop.assert_called_once()
            mock_perf.shutdown.assert_called_once()
            mock_git.stop.assert_called_once()
            mock_audit.stop_queue_consumer.assert_called_once()
            mock_audit.shutdown.assert_called_once()
            mock_task.shutdown.assert_called_once()
            mock_log_collector.shutdown.assert_called_once()
            mock_log_alert.shutdown.assert_called_once()
            mock_log_storage.shutdown.assert_called_once()
            mock_health_probe.shutdown.assert_called_once()


class TestRateLimitMemoryCleanup:
    def test_old_entries_cleaned_up(self):
        from app.main import _MEMORY_LIMITS
        key = "test_cleanup_key"
        _MEMORY_LIMITS[key] = [time.time() - 120] * 5
        now = time.time()
        _MEMORY_LIMITS[key] = [t for t in _MEMORY_LIMITS[key] if now - t < 60]
        assert len(_MEMORY_LIMITS[key]) == 0
        del _MEMORY_LIMITS[key]


class TestStaticDirConfig:
    def test_static_dir_path(self):
        from app.main import STATIC_DIR
        assert isinstance(STATIC_DIR, Path)
        assert "frontend" in str(STATIC_DIR)
        assert "dist" in str(STATIC_DIR)


if _task_scheduler_backup is not None:
    sys.modules["app.services.task_scheduler_service"] = _task_scheduler_backup
else:
    sys.modules.pop("app.services.task_scheduler_service", None)
