from __future__ import annotations

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
    EventStatus,
    EventTransform,
    FilterOperator,
    LogicOperator,
    EventSourceCreate,
    EventRouteCreate,
    EventRouteUpdate,
    EventSourceUpdate,
)


@pytest.fixture
def service():
    with patch.object(EventBusService, "_start_background_sources", lambda self: None):
        svc = EventBusService()
    return svc


class TestInitDb:
    def test_init_creates_tables(self, service):
        with service._conn() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}
            assert "event_sources" in table_names
            assert "event_routes" in table_names
            assert "event_logs" in table_names


class TestCreateSource:
    def test_create_webhook_source(self, service):
        data = EventSourceCreate(
            name="test-webhook",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="secret123",
        )
        source = service.create_source(data)
        assert source.name == "test-webhook"
        assert source.source_type == EventSourceType.WEBHOOK
        assert source.webhook_url is not None
        assert "/webhook/" in source.webhook_url

    def test_create_file_watch_source(self, service):
        data = EventSourceCreate(
            name="file-watcher",
            source_type=EventSourceType.FILE_WATCH,
            account_alias="server1",
            config={"path": "/var/log", "events": ["create", "modify"]},
            status=EventSourceStatus.DISABLED,
        )
        source = service.create_source(data)
        assert source.source_type == EventSourceType.FILE_WATCH
        assert source.webhook_url is None

    def test_create_system_metric_source(self, service):
        data = EventSourceCreate(
            name="cpu-monitor",
            source_type=EventSourceType.SYSTEM_METRIC,
            account_alias="server1",
            config={"metric": "cpu", "threshold": 90},
        )
        source = service.create_source(data)
        assert source.source_type == EventSourceType.SYSTEM_METRIC


class TestGetSource:
    def test_get_source_found(self, service):
        data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(data)
        found = service.get_source(source.id)
        assert found is not None
        assert found.name == "test"

    def test_get_source_not_found(self, service):
        assert service.get_source("nonexistent") is None


class TestListSources:
    def test_list_sources(self, service):
        data1 = EventSourceCreate(name="s1", source_type=EventSourceType.WEBHOOK)
        data2 = EventSourceCreate(name="s2", source_type=EventSourceType.FILE_WATCH, account_alias="s1")
        service.create_source(data1)
        service.create_source(data2)
        sources = service.list_sources()
        assert len(sources) >= 2


class TestUpdateSource:
    def test_update_source_name(self, service):
        data = EventSourceCreate(name="old", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(data)
        update = EventSourceUpdate(name="new")
        updated = service.update_source(source.id, update)
        assert updated.name == "new"

    def test_update_source_not_found(self, service):
        update = EventSourceUpdate(name="new")
        with pytest.raises(ValueError, match="not found"):
            service.update_source("nonexistent", update)

    def test_update_source_no_changes(self, service):
        data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(data)
        update = EventSourceUpdate()
        updated = service.update_source(source.id, update)
        assert updated.name == "test"


class TestDeleteSource:
    def test_delete_source(self, service):
        data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(data)
        service.delete_source(source.id)
        assert service.get_source(source.id) is None

    def test_delete_source_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.delete_source("nonexistent")


class TestCreateRoute:
    def test_create_route(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-1",
        )
        route = service.create_route(route_data)
        assert route.source_id == source.id
        assert route.workflow_id == "wf-1"

    def test_create_route_with_filter(self, service):
        source_data = EventSourceCreate(name="test-filter-src", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        fg_create = EventFilterGroupCreate(
            logic=LogicOperator.AND,
            conditions=[EventFilterConditionCreate(field="event_type", operator=FilterOperator.EQUALS, value="push")],
        )
        route_data = EventRouteCreate(
            source_id=source.id,
            workflow_id="wf-filter-1",
            filter_group=fg_create,
        )
        with patch("app.services.event_bus_service.EventRoute") as MockRoute:
            fg = EventFilterGroup(
                logic=fg_create.logic,
                conditions=[EventFilterCondition(**c.model_dump()) for c in fg_create.conditions],
            )
            mock_route = MagicMock()
            mock_route.id = str(__import__("uuid").uuid4())
            mock_route.source_id = source.id
            mock_route.workflow_id = "wf-filter-1"
            mock_route.filter_group = fg
            mock_route.transforms = []
            mock_route.enabled = True
            MockRoute.return_value = mock_route
            route = service.create_route(route_data)
            assert route.filter_group is not None


class TestUpdateRoute:
    def test_update_route(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-1")
        route = service.create_route(route_data)
        update = EventRouteUpdate(enabled=False)
        updated = service.update_route(route.id, update)
        assert updated.enabled is False

    def test_update_route_not_found(self, service):
        update = EventRouteUpdate(enabled=False)
        with pytest.raises(ValueError, match="not found"):
            service.update_route("nonexistent", update)


class TestDeleteRoute:
    def test_delete_route(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-1")
        route = service.create_route(route_data)
        service.delete_route(route.id)
        routes = service.list_routes(source_id=source.id)
        assert len(routes) == 0


class TestListRoutes:
    def test_list_routes_by_source(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        route_data = EventRouteCreate(source_id=source.id, workflow_id="wf-1")
        service.create_route(route_data)
        routes = service.list_routes(source_id=source.id)
        assert len(routes) >= 1

    def test_list_all_routes(self, service):
        routes = service.list_routes()
        assert isinstance(routes, list)


class TestReceiveEvent:
    @pytest.mark.asyncio
    async def test_receive_event(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        with patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_event(source.id, "push", {"ref": "main"})
            assert log.event_type == "push"
            assert log.source_id == source.id

    @pytest.mark.asyncio
    async def test_receive_event_source_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.receive_event("nonexistent", "push", {})


class TestReceiveWebhook:
    @pytest.mark.asyncio
    async def test_receive_webhook_not_webhook_type(self, service):
        source_data = EventSourceCreate(name="test", source_type=EventSourceType.FILE_WATCH, account_alias="s1")
        source = service.create_source(source_data)
        with pytest.raises(ValueError, match="not a webhook"):
            await service.receive_webhook(source.id, {}, b"{}")

    @pytest.mark.asyncio
    async def test_receive_webhook_source_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.receive_webhook("nonexistent", {}, b"{}")


class TestApplyFilter:
    def test_filter_equals(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="event_type", operator=FilterOperator.EQUALS, value="push")],
        )
        assert service._apply_filter({"event_type": "push"}, fg) is True
        assert service._apply_filter({"event_type": "pull"}, fg) is False

    def test_filter_contains(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="message", operator=FilterOperator.CONTAINS, value="error")],
        )
        assert service._apply_filter({"message": "an error occurred"}, fg) is True
        assert service._apply_filter({"message": "all good"}, fg) is False

    def test_filter_regex(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="branch", operator=FilterOperator.REGEX, value="^feature/")],
        )
        assert service._apply_filter({"branch": "feature/new"}, fg) is True
        assert service._apply_filter({"branch": "main"}, fg) is False

    def test_filter_not_equals(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="status", operator=FilterOperator.NOT_EQUALS, value="ok")],
        )
        assert service._apply_filter({"status": "error"}, fg) is True
        assert service._apply_filter({"status": "ok"}, fg) is False

    def test_filter_or_logic(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.OR,
            conditions=[
                EventFilterCondition(field="a", operator=FilterOperator.EQUALS, value="1"),
                EventFilterCondition(field="b", operator=FilterOperator.EQUALS, value="2"),
            ],
        )
        assert service._apply_filter({"a": "1", "b": "0"}, fg) is True
        assert service._apply_filter({"a": "0", "b": "2"}, fg) is True
        assert service._apply_filter({"a": "0", "b": "0"}, fg) is False

    def test_filter_not_logic(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.NOT,
            conditions=[EventFilterCondition(field="a", operator=FilterOperator.EQUALS, value="1")],
        )
        assert service._apply_filter({"a": "0"}, fg) is True
        assert service._apply_filter({"a": "1"}, fg) is False

    def test_filter_none_field(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="missing", operator=FilterOperator.EQUALS, value="1")],
        )
        assert service._apply_filter({}, fg) is False

    def test_filter_empty_conditions(self, service):
        fg = EventFilterGroup(logic=LogicOperator.AND, conditions=[])
        assert service._apply_filter({}, fg) is False

    def test_filter_regex_error(self, service):
        fg = EventFilterGroup(
            logic=LogicOperator.AND,
            conditions=[EventFilterCondition(field="val", operator=FilterOperator.REGEX, value="[invalid")],
        )
        assert service._apply_filter({"val": "test"}, fg) is False


class TestGetFieldValue:
    def test_simple_field(self, service):
        assert service._get_field_value({"a": 1}, "a") == 1

    def test_nested_field(self, service):
        assert service._get_field_value({"a": {"b": 2}}, "a.b") == 2

    def test_array_index(self, service):
        assert service._get_field_value({"items": [10, 20, 30]}, "items.1") == 20

    def test_missing_field(self, service):
        assert service._get_field_value({"a": 1}, "b") is None

    def test_invalid_index(self, service):
        assert service._get_field_value({"items": [1]}, "items.5") is None


class TestApplyTransforms:
    def test_simple_transform(self, service):
        transforms = [EventTransform(source_field="name", target_field="display_name")]
        result = service._apply_transforms({"name": "test"}, transforms)
        assert result["display_name"] == "test"

    def test_transform_with_template(self, service):
        transforms = [
            EventTransform(source_field="count", target_field="summary", template="Count: {{value}}")
        ]
        result = service._apply_transforms({"count": 42}, transforms)
        assert result["summary"] == "Count: 42"

    def test_transform_nested_target(self, service):
        transforms = [EventTransform(source_field="val", target_field="output.result")]
        result = service._apply_transforms({"val": "ok"}, transforms)
        assert result["output"]["result"] == "ok"

    def test_transform_missing_source(self, service):
        transforms = [EventTransform(source_field="missing", target_field="out")]
        result = service._apply_transforms({"other": 1}, transforms)
        assert "out" not in result


class TestDetectPlatform:
    def test_github(self, service):
        assert service._detect_platform({"X-GitHub-Event": "push"}) == "github"

    def test_gitlab(self, service):
        assert service._detect_platform({"X-Gitlab-Event": "Push Hook"}) == "gitlab"

    def test_gitee(self, service):
        assert service._detect_platform({"X-Gitee-Event": "Push Hook"}) == "gitee"

    def test_unknown(self, service):
        assert service._detect_platform({}) == "unknown"


class TestParseWebhookEvent:
    def test_parse_github_push(self, service):
        headers = {"X-GitHub-Event": "push"}
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [{"id": "abc"}],
            "pusher": {"name": "user1"},
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert result["platform"] == "github"
        assert result["branch"] == "main"
        assert result["pusher"] == "user1"

    def test_parse_github_pull_request(self, service):
        headers = {"X-GitHub-Event": "pull_request"}
        body = json.dumps({
            "action": "opened",
            "pull_request": {"base": {"ref": "main"}, "user": {"login": "user1"}},
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert result["event_type"] == "pull_request.opened"

    def test_parse_gitlab_push(self, service):
        headers = {"X-Gitlab-Event": "Push Hook"}
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [],
            "user_name": "user1",
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert result["platform"] == "gitlab"
        assert result["branch"] == "main"

    def test_parse_gitee_push(self, service):
        headers = {"X-Gitee-Event": "Push Hook"}
        body = json.dumps({
            "ref": "refs/heads/dev",
            "commits": [],
            "user_name": "user1",
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert result["platform"] == "gitee"
        assert result["branch"] == "dev"

    def test_parse_unknown_platform(self, service):
        result = service._parse_webhook_event({}, b'{"key": "value"}')
        assert result["key"] == "value"

    def test_parse_invalid_json(self, service):
        result = service._parse_webhook_event({}, b'not json')
        assert "raw_body" in result

    def test_parse_github_invalid_json(self, service):
        headers = {"X-GitHub-Event": "push"}
        result = service._parse_webhook_event(headers, b'not json')
        assert result["platform"] == "github"

    def test_parse_github_tag(self, service):
        headers = {"X-GitHub-Event": "push"}
        body = json.dumps({"ref": "refs/tags/v1.0", "repository": {}}).encode()
        result = service._parse_webhook_event(headers, body)
        assert result["tag"] == "v1.0"

    def test_parse_gitlab_merge_request(self, service):
        headers = {"X-Gitlab-Event": "Merge Request Hook"}
        body = json.dumps({
            "object_attributes": {"action": "merge", "target_branch": "main"},
            "user": {"name": "user1"},
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert "merge_request" in result["event_type"]

    def test_parse_gitee_merge_request(self, service):
        headers = {"X-Gitee-Event": "Merge Request Hook"}
        body = json.dumps({
            "merge_request": {"action": "open", "target_branch": "main"},
            "user_name": "user1",
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_webhook_event(headers, body)
        assert "merge_request" in result["event_type"]


class TestCompareThreshold:
    def test_gt(self, service):
        assert service._compare_threshold(95, 90, "gt") is True
        assert service._compare_threshold(85, 90, "gt") is False

    def test_lt(self, service):
        assert service._compare_threshold(80, 90, "lt") is True
        assert service._compare_threshold(95, 90, "lt") is False

    def test_gte(self, service):
        assert service._compare_threshold(90, 90, "gte") is True
        assert service._compare_threshold(89, 90, "gte") is False

    def test_lte(self, service):
        assert service._compare_threshold(90, 90, "lte") is True
        assert service._compare_threshold(91, 90, "lte") is False

    def test_unknown_operator(self, service):
        assert service._compare_threshold(95, 90, "unknown") is False


class TestDetectFileChanges:
    def test_create_changes(self, service):
        prev = {"a.txt": 1.0}
        curr = {"a.txt": 1.0, "b.txt": 2.0}
        changes = service._detect_file_changes(prev, curr, ["create"])
        assert len(changes) == 1
        assert changes[0] == ("create", "b.txt")

    def test_delete_changes(self, service):
        prev = {"a.txt": 1.0, "b.txt": 2.0}
        curr = {"a.txt": 1.0}
        changes = service._detect_file_changes(prev, curr, ["delete"])
        assert len(changes) == 1
        assert changes[0] == ("delete", "b.txt")

    def test_modify_changes(self, service):
        prev = {"a.txt": 1.0}
        curr = {"a.txt": 2.0}
        changes = service._detect_file_changes(prev, curr, ["modify"])
        assert len(changes) == 1
        assert changes[0] == ("modify", "a.txt")

    def test_no_changes(self, service):
        prev = {"a.txt": 1.0}
        curr = {"a.txt": 1.0}
        changes = service._detect_file_changes(prev, curr, ["create", "delete", "modify"])
        assert len(changes) == 0


class TestListEventLogs:
    def test_list_event_logs_empty(self):
        import os
        import tempfile
        tmpdir = tempfile.mkdtemp()
        try:
            tmp_db = os.path.join(tmpdir, "test_event.db")
            with patch("app.services.event_bus_service._DB_PATH", Path(tmp_db)), \
                 patch("app.services.event_bus_service._PERSIST_DIR", Path(tmpdir)), \
                 patch.object(EventBusService, "_start_background_sources", lambda self: None):
                fresh_service = EventBusService()
                logs = fresh_service.list_event_logs()
                assert isinstance(logs, list)
        finally:
            import sqlite3
            try:
                conn = sqlite3.connect(str(tmp_db))
                conn.close()
            except Exception:
                pass
            import shutil
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def test_list_event_logs_with_filters(self, service):
        logs = service.list_event_logs(source_id="s1", event_type="push", status="pending")
        assert isinstance(logs, list)


class TestReplayEvent:
    @pytest.mark.asyncio
    async def test_replay_event_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.replay_event("nonexistent")


class TestExecSsh:
    def test_exec_ssh_account_not_found(self, service):
        with patch("app.services.event_bus_service.ssh_account_service") as mock_ssh:
            mock_ssh.get_account.return_value = None
            with pytest.raises(ValueError, match="not found"):
                service._exec_ssh("missing", "ls")

    def test_exec_ssh_success(self, service):
        with patch("app.services.event_bus_service.ssh_account_service") as mock_ssh:
            mock_conn = MagicMock()
            mock_conn.manager.exec_command.return_value = (0, "output", "")
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            code, stdout, stderr = service._exec_ssh("server1", "ls")
            assert code == 0
            mock_ssh.pool.release_connection.assert_called_once()

    def test_exec_ssh_bytes_output(self, service):
        with patch("app.services.event_bus_service.ssh_account_service") as mock_ssh:
            mock_conn = MagicMock()
            mock_conn.manager.exec_command.return_value = (0, b"bytes", b"err")
            mock_ssh.get_account.return_value = MagicMock()
            mock_ssh.pool.get_connection.return_value = mock_conn
            code, stdout, stderr = service._exec_ssh("server1", "ls")
            assert isinstance(stdout, str)
