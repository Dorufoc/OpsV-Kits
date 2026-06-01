from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.event_bus_service import EventBusService
from app.models.event_trigger import (
    EventFilterCondition,
    EventFilterConditionCreate,
    EventFilterGroup,
    EventFilterGroupCreate,
    EventSourceType,
    EventSourceStatus,
    EventSourceCreate,
    EventSourceUpdate,
    EventRouteCreate,
    EventRouteUpdate,
    EventStatus,
    EventTransform,
    EventTransformCreate,
    FilterOperator,
    LogicOperator,
)


@pytest.fixture
def service():
    with patch.object(EventBusService, "_start_background_sources", lambda self: None):
        svc = EventBusService()
    return svc


class TestStartBackgroundSourcesWithLoop:
    def test_file_watch_with_running_loop(self):
        mock_source = MagicMock()
        mock_source.status = EventSourceStatus.ENABLED
        mock_source.source_type = EventSourceType.FILE_WATCH
        mock_source.config = {"path": "/var/log", "events": ["create"], "interval": 1}
        mock_source.account_alias = "server1"

        with patch.object(EventBusService, "_start_background_sources", lambda self: None):
            svc = EventBusService()

        mock_task = MagicMock()
        with patch.object(svc, "list_sources", return_value=[mock_source]), \
             patch("app.services.event_bus_service.asyncio.get_running_loop") as mock_get_loop, \
             patch("app.services.event_bus_service.threading.Thread") as mock_thread:
            mock_loop = MagicMock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop
            svc._start_background_sources()
            mock_loop.create_task.assert_called_once()

    def test_system_metric_with_running_loop(self):
        mock_source = MagicMock()
        mock_source.status = EventSourceStatus.ENABLED
        mock_source.source_type = EventSourceType.SYSTEM_METRIC
        mock_source.config = {"metric": "cpu", "threshold": 90, "interval": 60}
        mock_source.account_alias = "server1"

        with patch.object(EventBusService, "_start_background_sources", lambda self: None):
            svc = EventBusService()

        mock_task = MagicMock()
        with patch.object(svc, "list_sources", return_value=[mock_source]), \
             patch("app.services.event_bus_service.asyncio.get_running_loop") as mock_get_loop, \
             patch("app.services.event_bus_service.threading.Thread") as mock_thread:
            mock_loop = MagicMock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop
            svc._start_background_sources()
            mock_loop.create_task.assert_called_once()

    def test_system_metric_no_running_loop(self):
        mock_source = MagicMock()
        mock_source.status = EventSourceStatus.ENABLED
        mock_source.source_type = EventSourceType.SYSTEM_METRIC
        mock_source.config = {"metric": "cpu", "threshold": 90, "interval": 60}
        mock_source.account_alias = "server1"

        with patch.object(EventBusService, "_start_background_sources", lambda self: None):
            svc = EventBusService()

        with patch.object(svc, "list_sources", return_value=[mock_source]), \
             patch("app.services.event_bus_service.asyncio.get_running_loop", side_effect=RuntimeError), \
             patch("app.services.event_bus_service.threading.Thread") as mock_thread:
            svc._start_background_sources()
            mock_thread.assert_called_once()

    def test_start_background_sources_exception(self):
        with patch.object(EventBusService, "_start_background_sources", lambda self: None):
            svc = EventBusService()

        with patch.object(svc, "list_sources", side_effect=Exception("db error")):
            svc._start_background_sources()


class TestCreateSourceWithRunningLoop:
    def test_create_file_watch_with_running_loop(self, service):
        data = EventSourceCreate(
            name="fw-loop",
            source_type=EventSourceType.FILE_WATCH,
            account_alias="server1",
            config={"path": "/var/log", "events": ["create"], "interval": 1},
        )
        mock_task = MagicMock()
        with patch("app.services.event_bus_service.asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop
            source = service.create_source(data)
            assert source.source_type == EventSourceType.FILE_WATCH

    def test_create_system_metric_with_running_loop(self, service):
        data = EventSourceCreate(
            name="metric-loop",
            source_type=EventSourceType.SYSTEM_METRIC,
            account_alias="server1",
            config={"metric": "cpu", "threshold": 90, "interval": 60},
        )
        mock_task = MagicMock()
        with patch("app.services.event_bus_service.asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop
            source = service.create_source(data)
            assert source.source_type == EventSourceType.SYSTEM_METRIC

    def test_create_system_metric_no_running_loop(self, service):
        data = EventSourceCreate(
            name="metric-thread",
            source_type=EventSourceType.SYSTEM_METRIC,
            account_alias="server1",
            config={"metric": "cpu", "threshold": 90, "interval": 60},
        )
        with patch("app.services.event_bus_service.asyncio.get_running_loop", side_effect=RuntimeError), \
             patch("app.services.event_bus_service.threading.Thread") as mock_thread:
            source = service.create_source(data)
            mock_thread.assert_called_once()


class TestRowToEventLogWithData:
    @pytest.mark.asyncio
    async def test_event_log_with_raw_data_and_matched_routes(self, service):
        source_data = EventSourceCreate(name="log-test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        with patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_event(source.id, "push", {"ref": "main", "action": "opened"})

        with service._conn() as conn:
            conn.execute(
                "UPDATE event_logs SET raw_data = ?, matched_routes = ?, triggered_workflows = ?, filtered = ? WHERE id = ?",
                (json.dumps({"key": "value"}), json.dumps(["route1"]), json.dumps(["wf1"]), 1, log.id),
            )

        logs = service.list_event_logs()
        found = next((l for l in logs if l.id == log.id), None)
        assert found is not None
        assert found.raw_data == {"key": "value"}
        assert found.matched_routes == ["route1"]
        assert found.triggered_workflows == ["wf1"]
        assert found.filtered is True


class TestUpdateRouteWithFields:
    def test_update_route_filter_group(self, service):
        source_data = EventSourceCreate(name="route-fg", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-1")
        route = service.create_route(route_data)
        fg = EventFilterGroupCreate(
            logic=LogicOperator.AND,
            conditions=[EventFilterConditionCreate(field="type", operator=FilterOperator.EQUALS, value="push")],
        )
        update = EventRouteUpdate(filter_group=fg)
        updated = service.update_route(route.id, update)
        assert updated is not None

    def test_update_route_transforms(self, service):
        source_data = EventSourceCreate(name="route-tf", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-2")
        route = service.create_route(route_data)
        transforms = [EventTransformCreate(source_field="name", target_field="display")]
        update = EventRouteUpdate(transforms=transforms)
        updated = service.update_route(route.id, update)
        assert updated is not None

    def test_update_route_enabled(self, service):
        source_data = EventSourceCreate(name="route-en", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-3", enabled=True)
        route = service.create_route(route_data)
        update = EventRouteUpdate(enabled=False)
        updated = service.update_route(route.id, update)
        assert updated.enabled is False


class TestProcessEvent:
    @pytest.mark.asyncio
    async def test_process_event_with_matching_route(self, service):
        source_data = EventSourceCreate(name="proc-match", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-match",
        )
        service.create_route(route_data)

        with patch("app.services.workflow_service.workflow_service") as mock_wf:
            mock_wf.execute_workflow = AsyncMock()
            log = await service.receive_event(source.id, "push", {"event_type": "push"})
            assert log is not None

    @pytest.mark.asyncio
    async def test_process_event_no_matching_route(self, service):
        source_data = EventSourceCreate(name="proc-nomatch", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-nomatch",
        )
        service.create_route(route_data)

        log = await service.receive_event(source.id, "push", {"event_type": "pull"})
        assert log is not None

    @pytest.mark.asyncio
    async def test_process_event_route_error(self, service):
        source_data = EventSourceCreate(name="proc-err", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-err",
        )
        service.create_route(route_data)

        with patch("app.services.workflow_service.workflow_service") as mock_wf:
            mock_wf.execute_workflow = AsyncMock(side_effect=Exception("workflow error"))
            log = await service.receive_event(source.id, "push", {"event_type": "push"})
            assert log is not None

    @pytest.mark.asyncio
    async def test_process_event_disabled_route(self, service):
        source_data = EventSourceCreate(name="proc-disabled", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-disabled",
            enabled=False,
        )
        service.create_route(route_data)

        log = await service.receive_event(source.id, "push", {"event_type": "push"})
        assert log is not None

    @pytest.mark.asyncio
    async def test_process_event_matched_but_not_triggered(self, service):
        source_data = EventSourceCreate(name="proc-matched", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-matched",
        )
        service.create_route(route_data)

        with patch("app.services.workflow_service.workflow_service") as mock_wf:
            mock_wf.execute_workflow = AsyncMock(side_effect=Exception("fail"))
            log = await service.receive_event(source.id, "push", {"event_type": "push"})
            assert log is not None


class TestApplyFilterDefaultLogic:
    def test_default_logic_with_results(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="a", operator=FilterOperator.EQUALS, value="1")],
        )
        assert service._apply_filter({"a": "1"}, fg) is True

    def test_default_logic_empty_conditions(self, service):
        fg = EventFilterGroup(logic=LogicOperator.AND, conditions=[])
        assert service._apply_filter({}, fg) is False


class TestGetFieldValueNonDictList:
    def test_field_value_on_non_dict_non_list(self, service):
        assert service._get_field_value({"a": 42}, "a.b") is None

    def test_field_value_on_integer(self, service):
        assert service._get_field_value(42, "a") is None


class TestEvaluateConditionUnknownOperator:
    def test_unknown_operator(self, service):
        assert service._evaluate_condition("value", "unknown_op", "value") is False


class TestApplyTransformsTemplateException:
    def test_template_exception_fallback(self, service):
        transforms = [EventTransform(source_field="val", target_field="out", template="bad {{nonexistent}}")]
        result = service._apply_transforms({"val": "hello"}, transforms)
        assert result.get("out") is not None


class TestStartFileWatcherLoop:
    @pytest.mark.asyncio
    async def test_file_watcher_detects_changes(self, service):
        source = MagicMock()
        source.id = "fw-test"
        source.config = {"path": "/var/log", "events": ["create", "modify", "delete"], "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]
        original_get_source = service.get_source

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 2:
                s = MagicMock()
                s.status = EventSourceStatus.DISABLED
                return s
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_exec_ssh", return_value=(0, "/var/log/a.txt|1.0\n/var/log/b.txt|2.0", "")), \
             patch.object(service, "receive_event", new_callable=AsyncMock) as mock_receive:
            await service._start_file_watcher(source)

    @pytest.mark.asyncio
    async def test_file_watcher_no_stdout(self, service):
        source = MagicMock()
        source.id = "fw-nostdout"
        source.config = {"path": "/var/log", "events": ["create"], "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                s = MagicMock()
                s.status = EventSourceStatus.DISABLED
                return s
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_exec_ssh", return_value=(1, "", "")):
            await service._start_file_watcher(source)

    @pytest.mark.asyncio
    async def test_file_watcher_exception(self, service):
        source = MagicMock()
        source.id = "fw-exc"
        source.config = {"path": "/var/log", "events": ["create"], "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                raise asyncio.CancelledError
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_exec_ssh", side_effect=Exception("ssh fail")):
            await service._start_file_watcher(source)


class TestStartMetricWatcherLoop:
    @pytest.mark.asyncio
    async def test_metric_watcher_threshold_exceeded(self, service):
        source = MagicMock()
        source.id = "mw-test"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                s = MagicMock()
                s.status = EventSourceStatus.DISABLED
                return s
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_get_metric_value", new_callable=AsyncMock, return_value=95.0), \
             patch.object(service, "receive_event", new_callable=AsyncMock) as mock_receive:
            await service._start_metric_watcher(source)
            mock_receive.assert_called_once()

    @pytest.mark.asyncio
    async def test_metric_watcher_threshold_not_exceeded(self, service):
        source = MagicMock()
        source.id = "mw-below"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                s = MagicMock()
                s.status = EventSourceStatus.DISABLED
                return s
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_get_metric_value", new_callable=AsyncMock, return_value=50.0), \
             patch.object(service, "receive_event", new_callable=AsyncMock) as mock_receive:
            await service._start_metric_watcher(source)
            mock_receive.assert_not_called()

    @pytest.mark.asyncio
    async def test_metric_watcher_none_value(self, service):
        source = MagicMock()
        source.id = "mw-none"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                s = MagicMock()
                s.status = EventSourceStatus.DISABLED
                return s
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_get_metric_value", new_callable=AsyncMock, return_value=None), \
             patch.object(service, "receive_event", new_callable=AsyncMock) as mock_receive:
            await service._start_metric_watcher(source)
            mock_receive.assert_not_called()

    @pytest.mark.asyncio
    async def test_metric_watcher_exception(self, service):
        source = MagicMock()
        source.id = "mw-exc"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 1:
                raise asyncio.CancelledError
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_get_metric_value", new_callable=AsyncMock, side_effect=Exception("monitor fail")):
            await service._start_metric_watcher(source)

    @pytest.mark.asyncio
    async def test_metric_watcher_source_disabled(self, service):
        source = MagicMock()
        source.id = "mw-disabled"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 0.01}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED

        disabled_source = MagicMock()
        disabled_source.status = EventSourceStatus.DISABLED

        call_count = [0]

        def mock_get_source(sid):
            call_count[0] += 1
            if call_count[0] > 0:
                return disabled_source
            return source

        with patch.object(service, "get_source", side_effect=mock_get_source), \
             patch.object(service, "_get_metric_value", new_callable=AsyncMock, return_value=95.0):
            await service._start_metric_watcher(source)
