import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_target_dict(target_id="tgt-1", name="test-target"):
    return {
        "id": target_id,
        "name": name,
        "probe_type": "http",
        "target": "https://example.com",
        "interval_seconds": 60,
        "timeout_seconds": 10,
        "enabled": True,
        "failure_threshold": 3,
        "recovery_threshold": 2,
        "http_config": None,
        "tags": [],
        "current_status": "unknown",
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "last_probe_time": None,
        "last_success_time": None,
        "last_failure_time": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


def _make_probe_result_dict(target_id="tgt-1"):
    return {
        "id": "result-1",
        "target_id": target_id,
        "timestamp": "2025-01-01T00:00:00",
        "probe_type": "http",
        "target": "https://example.com",
        "success": True,
        "response_time_ms": 50.0,
        "status_code": 200,
        "error_message": None,
        "content_matched": None,
    }


def _make_statistics_dict(target_id="tgt-1"):
    return {
        "target_id": target_id,
        "uptime_percent": 99.5,
        "avg_response_time_ms": 45.0,
        "max_response_time_ms": 100.0,
        "min_response_time_ms": 20.0,
        "total_probes": 100,
        "success_count": 99,
        "failure_count": 1,
        "current_status": "available",
        "last_probe_time": "2025-01-01T00:00:00",
        "last_success_time": "2025-01-01T00:00:00",
        "last_failure_time": None,
    }


def _make_overview_dict():
    return {
        "total_targets": 2,
        "available_count": 1,
        "unavailable_count": 1,
        "unknown_count": 0,
        "targets": [
            _make_target_dict(name="target-1"),
            {**_make_target_dict(target_id="tgt-2", name="target-2"), "current_status": "unavailable"},
        ],
    }


class TestHealthProbeCreateTarget:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_create_target_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        target_data = _make_target_dict()
        mock_target = ProbeTarget(**target_data)
        mock_service.create_target.return_value = mock_target

        response = client.post("/api/health-probe/targets", json={
            "name": "test-target",
            "probe_type": "http",
            "target": "https://example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-target"

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_create_target_internal_error(self, mock_service, client):
        mock_service.create_target.side_effect = Exception("db error")

        response = client.post("/api/health-probe/targets", json={
            "name": "test-target",
            "probe_type": "http",
            "target": "https://example.com",
        })
        assert response.status_code == 500


class TestHealthProbeListTargets:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_list_targets_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.list_targets.return_value = [mock_target]

        response = client.get("/api/health-probe/targets")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-target"

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_list_targets_empty(self, mock_service, client):
        mock_service.list_targets.return_value = []

        response = client.get("/api/health-probe/targets")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_list_targets_filtered_by_tag(self, mock_service, client):
        mock_service.list_targets.return_value = []

        response = client.get("/api/health-probe/targets?tag=production")
        assert response.status_code == 200
        mock_service.list_targets.assert_called_once_with(tag="production", probe_type=None)

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_list_targets_filtered_by_probe_type(self, mock_service, client):
        mock_service.list_targets.return_value = []

        response = client.get("/api/health-probe/targets?probe_type=http")
        assert response.status_code == 200
        mock_service.list_targets.assert_called_once_with(tag=None, probe_type="http")


class TestHealthProbeGetTarget:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_target_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target

        response = client.get("/api/health-probe/targets/tgt-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "tgt-1"

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_target_not_found(self, mock_service, client):
        mock_service.get_target.return_value = None

        response = client.get("/api/health-probe/targets/nonexistent")
        assert response.status_code == 404


class TestHealthProbeUpdateTarget:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_update_target_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        updated_data = {**_make_target_dict(), "name": "updated"}
        mock_target = ProbeTarget(**updated_data)
        mock_service.update_target.return_value = mock_target

        response = client.put("/api/health-probe/targets/tgt-1", json={"name": "updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated"

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_update_target_not_found(self, mock_service, client):
        mock_service.update_target.return_value = None

        response = client.put("/api/health-probe/targets/nonexistent", json={"name": "updated"})
        assert response.status_code == 404


class TestHealthProbeDeleteTarget:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_delete_target_success(self, mock_service, client):
        mock_service.delete_target.return_value = True

        response = client.delete("/api/health-probe/targets/tgt-1")
        assert response.status_code == 200
        data = response.json()
        assert "删除成功" in data["message"]

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_delete_target_not_found(self, mock_service, client):
        mock_service.delete_target.return_value = False

        response = client.delete("/api/health-probe/targets/nonexistent")
        assert response.status_code == 404


class TestHealthProbeNow:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_probe_now_success(self, mock_service, client):
        from app.models.health_probe import ProbeResult
        mock_result = ProbeResult(**_make_probe_result_dict())
        mock_service.probe_now = AsyncMock(return_value=mock_result)

        response = client.post("/api/health-probe/targets/tgt-1/probe")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status_code"] == 200

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_probe_now_target_not_found(self, mock_service, client):
        mock_service.probe_now = AsyncMock(return_value=None)

        response = client.post("/api/health-probe/targets/nonexistent/probe")
        assert response.status_code == 404


class TestHealthProbeLogs:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_probe_logs_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target
        mock_service.query_probe_logs.return_value = ([], 0)

        response = client.get("/api/health-probe/targets/tgt-1/logs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_probe_logs_target_not_found(self, mock_service, client):
        mock_service.get_target.return_value = None

        response = client.get("/api/health-probe/targets/nonexistent/logs")
        assert response.status_code == 404

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_probe_logs_with_filters(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target
        mock_service.query_probe_logs.return_value = ([], 0)

        response = client.get("/api/health-probe/targets/tgt-1/logs?limit=10&offset=0&success=true")
        assert response.status_code == 200
        mock_service.query_probe_logs.assert_called_once()
        call_kwargs = mock_service.query_probe_logs.call_args
        assert call_kwargs.kwargs["limit"] == 10
        assert call_kwargs.kwargs["offset"] == 0
        assert call_kwargs.kwargs["success"] is True


class TestHealthProbeStatistics:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_statistics_success(self, mock_service, client):
        from app.models.health_probe import ProbeTarget, ProbeStatistics
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target
        mock_stats = ProbeStatistics(**_make_statistics_dict())
        mock_service.calculate_statistics.return_value = mock_stats

        response = client.get("/api/health-probe/targets/tgt-1/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["uptime_percent"] == 99.5
        assert data["total_probes"] == 100

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_statistics_target_not_found(self, mock_service, client):
        mock_service.get_target.return_value = None

        response = client.get("/api/health-probe/targets/nonexistent/statistics")
        assert response.status_code == 404

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_statistics_no_data(self, mock_service, client):
        from app.models.health_probe import ProbeTarget
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target
        mock_service.calculate_statistics.return_value = None

        response = client.get("/api/health-probe/targets/tgt-1/statistics")
        assert response.status_code == 404

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_statistics_custom_hours(self, mock_service, client):
        from app.models.health_probe import ProbeTarget, ProbeStatistics
        mock_target = ProbeTarget(**_make_target_dict())
        mock_service.get_target.return_value = mock_target
        mock_stats = ProbeStatistics(**_make_statistics_dict())
        mock_service.calculate_statistics.return_value = mock_stats

        response = client.get("/api/health-probe/targets/tgt-1/statistics?hours=48")
        assert response.status_code == 200


class TestHealthProbeOverview:
    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_overview_success(self, mock_service, client):
        from app.models.health_probe import ProbeOverview
        mock_overview = ProbeOverview(**_make_overview_dict())
        mock_service.get_overview.return_value = mock_overview

        response = client.get("/api/health-probe/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_targets"] == 2
        assert data["available_count"] == 1
        assert data["unavailable_count"] == 1

    @patch("app.api.routes.health_probe.health_probe_service")
    def test_get_overview_empty(self, mock_service, client):
        from app.models.health_probe import ProbeOverview
        mock_overview = ProbeOverview(total_targets=0, available_count=0, unavailable_count=0, unknown_count=0)
        mock_service.get_overview.return_value = mock_overview

        response = client.get("/api/health-probe/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_targets"] == 0
