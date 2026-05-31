import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_source_dict(source_id="src-1", name="test-source"):
    return {
        "id": source_id,
        "name": name,
        "source_type": "webhook",
        "config": {},
        "webhook_url": "/api/event-trigger/webhook/src-1",
        "webhook_secret": None,
        "account_alias": None,
        "status": "enabled",
        "description": "desc",
        "last_event_at": None,
        "event_count": 0,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


def _make_route_dict(route_id="route-1", source_id="src-1"):
    return {
        "id": route_id,
        "source_id": source_id,
        "workflow_id": "wf-1",
        "filter_group": None,
        "transforms": [],
        "enabled": True,
        "created_at": "2025-01-01T00:00:00",
    }


def _make_event_log_dict(log_id="log-1", source_id="src-1"):
    return {
        "id": log_id,
        "source_id": source_id,
        "source_name": "test-source",
        "event_type": "push",
        "raw_data": {},
        "filtered": False,
        "matched_routes": [],
        "triggered_workflows": [],
        "status": "pending",
        "error_message": None,
        "received_at": "2025-01-01T00:00:00",
    }


class TestEventSourceList:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_sources_success(self, mock_service, client):
        mock_src = MagicMock()
        mock_src.model_dump.return_value = _make_source_dict()
        mock_service.list_sources.return_value = [mock_src]

        response = client.get("/api/event-trigger/sources")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "test-source"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_sources_empty(self, mock_service, client):
        mock_service.list_sources.return_value = []

        response = client.get("/api/event-trigger/sources")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_sources_internal_error(self, mock_service, client):
        mock_service.list_sources.side_effect = Exception("db error")

        response = client.get("/api/event-trigger/sources")
        assert response.status_code == 500


class TestEventSourceGet:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_get_source_success(self, mock_service, client):
        mock_src = MagicMock()
        mock_src.model_dump.return_value = _make_source_dict()
        mock_service.get_source.return_value = mock_src

        response = client.get("/api/event-trigger/sources/src-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "src-1"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_get_source_not_found(self, mock_service, client):
        mock_service.get_source.return_value = None

        response = client.get("/api/event-trigger/sources/nonexistent")
        assert response.status_code == 500

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_get_source_value_error(self, mock_service, client):
        mock_service.get_source.side_effect = ValueError("bad id")

        response = client.get("/api/event-trigger/sources/src-1")
        assert response.status_code == 400


class TestEventSourceCreate:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_create_source_success(self, mock_service, client):
        mock_src = MagicMock()
        mock_src.model_dump.return_value = _make_source_dict(name="new-source")
        mock_service.create_source.return_value = mock_src

        response = client.post("/api/event-trigger/sources", json={
            "name": "new-source",
            "source_type": "webhook",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-source"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_create_source_value_error(self, mock_service, client):
        mock_service.create_source.side_effect = ValueError("invalid data")

        response = client.post("/api/event-trigger/sources", json={
            "name": "new-source",
            "source_type": "webhook",
        })
        assert response.status_code == 400

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_create_source_internal_error(self, mock_service, client):
        mock_service.create_source.side_effect = Exception("db error")

        response = client.post("/api/event-trigger/sources", json={
            "name": "new-source",
            "source_type": "webhook",
        })
        assert response.status_code == 500


class TestEventSourceUpdate:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_update_source_success(self, mock_service, client):
        mock_src = MagicMock()
        mock_src.model_dump.return_value = _make_source_dict(name="updated")
        mock_service.update_source.return_value = mock_src

        response = client.put("/api/event-trigger/sources/src-1", json={"name": "updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_update_source_value_error(self, mock_service, client):
        mock_service.update_source.side_effect = ValueError("not found")

        response = client.put("/api/event-trigger/sources/src-1", json={"name": "updated"})
        assert response.status_code == 400


class TestEventSourceDelete:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_delete_source_success(self, mock_service, client):
        mock_service.delete_source.return_value = None

        response = client.delete("/api/event-trigger/sources/src-1")
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_delete_source_value_error(self, mock_service, client):
        mock_service.delete_source.side_effect = ValueError("not found")

        response = client.delete("/api/event-trigger/sources/src-1")
        assert response.status_code == 400


class TestEventRouteList:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_routes_success(self, mock_service, client):
        mock_route = MagicMock()
        mock_route.model_dump.return_value = _make_route_dict()
        mock_service.list_routes.return_value = [mock_route]

        response = client.get("/api/event-trigger/routes")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_routes_filtered_by_source(self, mock_service, client):
        mock_service.list_routes.return_value = []

        response = client.get("/api/event-trigger/routes?source_id=src-1")
        assert response.status_code == 200
        mock_service.list_routes.assert_called_once_with(source_id="src-1")

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_routes_internal_error(self, mock_service, client):
        mock_service.list_routes.side_effect = Exception("db error")

        response = client.get("/api/event-trigger/routes")
        assert response.status_code == 500


class TestEventRouteCreate:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_create_route_success(self, mock_service, client):
        mock_route = MagicMock()
        mock_route.model_dump.return_value = _make_route_dict()
        mock_service.create_route.return_value = mock_route

        response = client.post("/api/event-trigger/routes", json={
            "source_id": "src-1",
            "workflow_id": "wf-1",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "src-1"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_create_route_value_error(self, mock_service, client):
        mock_service.create_route.side_effect = ValueError("invalid")

        response = client.post("/api/event-trigger/routes", json={
            "source_id": "src-1",
            "workflow_id": "wf-1",
        })
        assert response.status_code == 400


class TestEventRouteUpdate:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_update_route_success(self, mock_service, client):
        mock_route = MagicMock()
        mock_route.model_dump.return_value = _make_route_dict()
        mock_service.update_route.return_value = mock_route

        response = client.put("/api/event-trigger/routes/route-1", json={"enabled": False})
        assert response.status_code == 200

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_update_route_not_found(self, mock_service, client):
        mock_service.update_route.side_effect = ValueError("not found")

        response = client.put("/api/event-trigger/routes/route-1", json={"enabled": False})
        assert response.status_code == 400


class TestEventRouteDelete:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_delete_route_success(self, mock_service, client):
        mock_service.delete_route.return_value = None

        response = client.delete("/api/event-trigger/routes/route-1")
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_delete_route_value_error(self, mock_service, client):
        mock_service.delete_route.side_effect = ValueError("not found")

        response = client.delete("/api/event-trigger/routes/route-1")
        assert response.status_code == 400


class TestWebhookReceive:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_receive_webhook_success(self, mock_service, client):
        mock_log = MagicMock()
        mock_log.id = "log-1"
        mock_service.receive_webhook = AsyncMock(return_value=mock_log)

        response = client.post("/api/event-trigger/webhook/src-1", json={"test": "data"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_id"] == "log-1"

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_receive_webhook_source_not_found(self, mock_service, client):
        mock_service.receive_webhook = AsyncMock(side_effect=ValueError("not found"))

        response = client.post("/api/event-trigger/webhook/nonexistent", json={"test": "data"})
        assert response.status_code == 400

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_receive_webhook_internal_error(self, mock_service, client):
        mock_service.receive_webhook = AsyncMock(side_effect=Exception("db error"))

        response = client.post("/api/event-trigger/webhook/src-1", json={"test": "data"})
        assert response.status_code == 500


class TestEventLogs:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_event_logs_success(self, mock_service, client):
        mock_log = MagicMock()
        mock_log.model_dump.return_value = _make_event_log_dict()
        mock_service.list_event_logs.return_value = [mock_log]

        response = client.get("/api/event-trigger/logs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_event_logs_with_filters(self, mock_service, client):
        mock_service.list_event_logs.return_value = []

        response = client.get("/api/event-trigger/logs?source_id=src-1&event_type=push&status=pending&limit=10&offset=0")
        assert response.status_code == 200
        mock_service.list_event_logs.assert_called_once_with(
            source_id="src-1", event_type="push", status="pending", limit=10, offset=0
        )

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_list_event_logs_internal_error(self, mock_service, client):
        mock_service.list_event_logs.side_effect = Exception("db error")

        response = client.get("/api/event-trigger/logs")
        assert response.status_code == 500


class TestEventReplay:
    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_replay_event_success(self, mock_service, client):
        mock_log = MagicMock()
        mock_log.model_dump.return_value = _make_event_log_dict()
        mock_service.replay_event = AsyncMock(return_value=mock_log)

        response = client.post("/api/event-trigger/logs/log-1/replay")
        assert response.status_code == 200

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_replay_event_not_found(self, mock_service, client):
        mock_service.replay_event = AsyncMock(side_effect=ValueError("not found"))

        response = client.post("/api/event-trigger/logs/nonexistent/replay")
        assert response.status_code == 400

    @patch("app.api.routes.event_trigger.event_bus_service")
    def test_replay_event_internal_error(self, mock_service, client):
        mock_service.replay_event = AsyncMock(side_effect=Exception("error"))

        response = client.post("/api/event-trigger/logs/log-1/replay")
        assert response.status_code == 500
