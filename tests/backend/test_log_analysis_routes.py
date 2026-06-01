import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSearchLogs:
    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_search_success(self, mock_storage):
        mock_storage.search = AsyncMock(return_value={"total": 0, "results": []})
        resp = client.post(
            "/api/log-analysis/search",
            json={"query": "error", "filters": {}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_search_value_error(self, mock_storage):
        mock_storage.search = AsyncMock(side_effect=ValueError("bad query"))
        resp = client.post(
            "/api/log-analysis/search",
            json={"query": "error", "filters": {}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_search_generic_error(self, mock_storage):
        mock_storage.search = AsyncMock(side_effect=Exception("db error"))
        resp = client.post(
            "/api/log-analysis/search",
            json={"query": "error", "filters": {}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 500


class TestFilterLogs:
    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_filter_success(self, mock_storage):
        mock_storage.filter_logs = AsyncMock(return_value={"total": 0, "results": []})
        resp = client.post(
            "/api/log-analysis/filter",
            json={"filters": {"level": "ERROR"}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_filter_value_error(self, mock_storage):
        mock_storage.filter_logs = AsyncMock(side_effect=ValueError("bad filter"))
        resp = client.post(
            "/api/log-analysis/filter",
            json={"filters": {"level": "ERROR"}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_filter_generic_error(self, mock_storage):
        mock_storage.filter_logs = AsyncMock(side_effect=Exception("filter error"))
        resp = client.post(
            "/api/log-analysis/filter",
            json={"filters": {"level": "ERROR"}, "page": 1, "page_size": 50},
        )
        assert resp.status_code == 500


class TestAggregation:
    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_trend_aggregation(self, mock_storage):
        mock_storage.get_trend = AsyncMock(return_value=[{"time": "2024-01-01", "count": 5}])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "trend", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_source_distribution_aggregation(self, mock_storage):
        mock_storage.get_source_distribution = AsyncMock(return_value=[{"source": "app1", "count": 10}])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "source_distribution", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_level_distribution_aggregation(self, mock_storage):
        mock_storage.get_level_distribution = AsyncMock(return_value=[{"level": "ERROR", "count": 3}])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "level_distribution", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_keyword_frequency_aggregation(self, mock_storage):
        mock_storage.get_keyword_frequency = AsyncMock(return_value=[{"time": "2024-01-01", "count": 2}])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "keyword_frequency", "time_start": 1704067200.0, "time_end": 1704153600.0, "keyword": "timeout"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_keyword_frequency_missing_keyword(self, mock_storage):
        mock_storage.get_keyword_frequency = AsyncMock(return_value=[])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "keyword_frequency", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_unsupported_aggregation_type(self, mock_storage):
        mock_storage.get_trend = AsyncMock(return_value=[])
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "unknown", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_aggregation_value_error(self, mock_storage):
        mock_storage.get_trend = AsyncMock(side_effect=ValueError("bad params"))
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "trend", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_aggregation_generic_error(self, mock_storage):
        mock_storage.get_trend = AsyncMock(side_effect=Exception("agg error"))
        resp = client.get(
            "/api/log-analysis/aggregation",
            params={"type": "trend", "time_start": 1704067200.0, "time_end": 1704153600.0},
        )
        assert resp.status_code == 500


class TestSources:
    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_get_sources(self, mock_collector):
        mock_collector.get_sources.return_value = [{"id": "src1", "type": "system"}]
        resp = client.get("/api/log-analysis/sources")
        assert resp.status_code == 200
        assert "sources" in resp.json()

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_get_sources_error(self, mock_collector):
        mock_collector.get_sources.side_effect = Exception("source error")
        resp = client.get("/api/log-analysis/sources")
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_add_source_success(self, mock_collector):
        mock_collector.add_source.return_value = "src1"
        resp = client.post(
            "/api/log-analysis/sources",
            json={"type": "system", "alias": "test", "path": "/var/log/syslog", "enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "src1"

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_add_source_value_error(self, mock_collector):
        mock_collector.add_source.side_effect = ValueError("invalid type")
        resp = client.post(
            "/api/log-analysis/sources",
            json={"type": "bad", "alias": "test"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_add_source_generic_error(self, mock_collector):
        mock_collector.add_source.side_effect = Exception("add error")
        resp = client.post(
            "/api/log-analysis/sources",
            json={"type": "system", "alias": "test"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_update_source_success(self, mock_collector):
        resp = client.put(
            "/api/log-analysis/sources/src1",
            json={"alias": "updated", "enabled": True},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_update_source_no_fields(self, mock_collector):
        resp = client.put(
            "/api/log-analysis/sources/src1",
            json={},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_update_source_value_error(self, mock_collector):
        mock_collector.update_source.side_effect = ValueError("not found")
        resp = client.put(
            "/api/log-analysis/sources/src1",
            json={"alias": "updated"},
        )
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_update_source_generic_error(self, mock_collector):
        mock_collector.update_source.side_effect = Exception("update error")
        resp = client.put(
            "/api/log-analysis/sources/src1",
            json={"alias": "updated"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_delete_source_success(self, mock_collector):
        mock_collector.delete_source = AsyncMock()
        resp = client.delete("/api/log-analysis/sources/src1")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_delete_source_value_error(self, mock_collector):
        mock_collector.delete_source = AsyncMock(side_effect=ValueError("not found"))
        resp = client.delete("/api/log-analysis/sources/src1")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_delete_source_generic_error(self, mock_collector):
        mock_collector.delete_source = AsyncMock(side_effect=Exception("delete error"))
        resp = client.delete("/api/log-analysis/sources/src1")
        assert resp.status_code == 500


class TestSourceStartStop:
    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_start_source_success(self, mock_collector):
        mock_collector.start_source = AsyncMock()
        resp = client.post("/api/log-analysis/sources/src1/start")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_start_source_value_error(self, mock_collector):
        mock_collector.start_source = AsyncMock(side_effect=ValueError("not found"))
        resp = client.post("/api/log-analysis/sources/src1/start")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_start_source_generic_error(self, mock_collector):
        mock_collector.start_source = AsyncMock(side_effect=Exception("start error"))
        resp = client.post("/api/log-analysis/sources/src1/start")
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_stop_source_success(self, mock_collector):
        mock_collector.stop_source = AsyncMock()
        resp = client.post("/api/log-analysis/sources/src1/stop")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_stop_source_value_error(self, mock_collector):
        mock_collector.stop_source = AsyncMock(side_effect=ValueError("not found"))
        resp = client.post("/api/log-analysis/sources/src1/stop")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_collector_service")
    def test_stop_source_generic_error(self, mock_collector):
        mock_collector.stop_source = AsyncMock(side_effect=Exception("stop error"))
        resp = client.post("/api/log-analysis/sources/src1/stop")
        assert resp.status_code == 500


class TestAlertRules:
    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_get_alert_rules(self, mock_alert):
        mock_alert.get_rules = AsyncMock(return_value=[])
        resp = client.get("/api/log-analysis/alerts/rules")
        assert resp.status_code == 200
        assert "rules" in resp.json()

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_get_alert_rules_error(self, mock_alert):
        mock_alert.get_rules = AsyncMock(side_effect=Exception("rules error"))
        resp = client.get("/api/log-analysis/alerts/rules")
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_create_alert_rule_success(self, mock_alert):
        mock_alert.create_rule = AsyncMock(return_value="rule1")
        resp = client.post(
            "/api/log-analysis/alerts/rules",
            json={"name": "Test Rule", "pattern": "error", "pattern_type": "keyword"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "rule1"

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_create_alert_rule_value_error(self, mock_alert):
        mock_alert.create_rule = AsyncMock(side_effect=ValueError("bad rule"))
        resp = client.post(
            "/api/log-analysis/alerts/rules",
            json={"name": "Test Rule", "pattern": "error", "pattern_type": "keyword"},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_create_alert_rule_generic_error(self, mock_alert):
        mock_alert.create_rule = AsyncMock(side_effect=Exception("create error"))
        resp = client.post(
            "/api/log-analysis/alerts/rules",
            json={"name": "Test Rule", "pattern": "error", "pattern_type": "keyword"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_update_alert_rule_success(self, mock_alert):
        mock_alert.update_rule = AsyncMock()
        resp = client.put(
            "/api/log-analysis/alerts/rules/1",
            json={"name": "Updated Rule"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_update_alert_rule_no_fields(self, mock_alert):
        resp = client.put("/api/log-analysis/alerts/rules/1", json={})
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_update_alert_rule_value_error(self, mock_alert):
        mock_alert.update_rule = AsyncMock(side_effect=ValueError("not found"))
        resp = client.put(
            "/api/log-analysis/alerts/rules/1",
            json={"name": "Updated"},
        )
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_update_alert_rule_generic_error(self, mock_alert):
        mock_alert.update_rule = AsyncMock(side_effect=Exception("update error"))
        resp = client.put(
            "/api/log-analysis/alerts/rules/1",
            json={"name": "Updated"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_delete_alert_rule_success(self, mock_alert):
        mock_alert.delete_rule = AsyncMock()
        resp = client.delete("/api/log-analysis/alerts/rules/1")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_delete_alert_rule_value_error(self, mock_alert):
        mock_alert.delete_rule = AsyncMock(side_effect=ValueError("not found"))
        resp = client.delete("/api/log-analysis/alerts/rules/1")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_delete_alert_rule_generic_error(self, mock_alert):
        mock_alert.delete_rule = AsyncMock(side_effect=Exception("delete error"))
        resp = client.delete("/api/log-analysis/alerts/rules/1")
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_toggle_alert_rule_success(self, mock_alert):
        mock_alert.toggle_rule = AsyncMock()
        resp = client.post(
            "/api/log-analysis/alerts/rules/1/toggle",
            json={"enabled": False},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_toggle_alert_rule_value_error(self, mock_alert):
        mock_alert.toggle_rule = AsyncMock(side_effect=ValueError("not found"))
        resp = client.post(
            "/api/log-analysis/alerts/rules/1/toggle",
            json={"enabled": False},
        )
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_toggle_alert_rule_generic_error(self, mock_alert):
        mock_alert.toggle_rule = AsyncMock(side_effect=Exception("toggle error"))
        resp = client.post(
            "/api/log-analysis/alerts/rules/1/toggle",
            json={"enabled": False},
        )
        assert resp.status_code == 500


class TestAlertEvents:
    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_get_alert_events_with_rule_id(self, mock_alert):
        mock_alert.get_events = AsyncMock(return_value=[])
        resp = client.get("/api/log-analysis/alerts/events?rule_id=1")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_get_alert_events_without_rule_id(self, mock_alert):
        mock_alert.get_recent_events = AsyncMock(return_value=[])
        resp = client.get("/api/log-analysis/alerts/events?hours=12")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_alert_service")
    def test_get_alert_events_error(self, mock_alert):
        mock_alert.get_recent_events = AsyncMock(side_effect=Exception("events error"))
        resp = client.get("/api/log-analysis/alerts/events")
        assert resp.status_code == 500


class TestLogContext:
    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_get_context_success(self, mock_storage):
        mock_storage.get_context = AsyncMock(return_value={
            "target": {"id": 1, "message": "test"},
            "before": [],
            "after": [],
        })
        resp = client.get("/api/log-analysis/context?log_id=1")
        assert resp.status_code == 200

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_get_context_not_found(self, mock_storage):
        mock_storage.get_context = AsyncMock(return_value={"target": None, "before": [], "after": []})
        resp = client.get("/api/log-analysis/context?log_id=999")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_get_context_value_error(self, mock_storage):
        mock_storage.get_context = AsyncMock(side_effect=ValueError("not found"))
        resp = client.get("/api/log-analysis/context?log_id=1")
        assert resp.status_code == 404

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_get_context_generic_error(self, mock_storage):
        mock_storage.get_context = AsyncMock(side_effect=Exception("context error"))
        resp = client.get("/api/log-analysis/context?log_id=1")
        assert resp.status_code == 500

    @patch("app.api.routes.log_analysis.log_storage_service")
    def test_get_context_with_before_after(self, mock_storage):
        mock_storage.get_context = AsyncMock(return_value={
            "target": {"id": 1},
            "before": [{"id": 0}],
            "after": [{"id": 2}],
        })
        resp = client.get("/api/log-analysis/context?log_id=1&before=3&after=3")
        assert resp.status_code == 200
