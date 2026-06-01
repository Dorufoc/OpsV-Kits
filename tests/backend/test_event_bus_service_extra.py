from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.event_bus_service import EventBusService
from app.models.event_trigger import (
    EventSourceType,
    EventSourceStatus,
    EventSourceCreate,
)


@pytest.fixture
def service():
    with patch.object(EventBusService, "_start_background_sources", lambda self: None):
        svc = EventBusService()
    return svc


class TestReceiveWebhookWithSecret:
    @pytest.mark.asyncio
    async def test_github_signature_verified(self, service):
        source_data = EventSourceCreate(
            name="gh-webhook",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gh-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_github_signature", return_value=True), \
             patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_webhook(
                source.id,
                {"X-GitHub-Event": "push", "X-Hub-Signature-256": "sha256=abc"},
                b'{"ref": "refs/heads/main"}',
            )
            assert log is not None

    @pytest.mark.asyncio
    async def test_github_signature_failed(self, service):
        source_data = EventSourceCreate(
            name="gh-webhook-fail",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gh-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_github_signature", return_value=False):
            with pytest.raises(ValueError, match="GitHub webhook signature"):
                await service.receive_webhook(
                    source.id,
                    {"X-GitHub-Event": "push", "X-Hub-Signature-256": "sha256=bad"},
                    b"{}",
                )

    @pytest.mark.asyncio
    async def test_gitlab_token_verified(self, service):
        source_data = EventSourceCreate(
            name="gl-webhook",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gl-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_gitlab_signature", return_value=True), \
             patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_webhook(
                source.id,
                {"X-Gitlab-Event": "Push Hook", "X-Gitlab-Token": "gl-secret"},
                b'{"ref": "refs/heads/main"}',
            )
            assert log is not None

    @pytest.mark.asyncio
    async def test_gitlab_token_failed(self, service):
        source_data = EventSourceCreate(
            name="gl-webhook-fail",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gl-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_gitlab_signature", return_value=False):
            with pytest.raises(ValueError, match="GitLab webhook token"):
                await service.receive_webhook(
                    source.id,
                    {"X-Gitlab-Event": "Push Hook", "X-Gitlab-Token": "bad"},
                    b"{}",
                )

    @pytest.mark.asyncio
    async def test_gitee_token_verified(self, service):
        source_data = EventSourceCreate(
            name="gee-webhook",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gee-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_gitee_signature", return_value=True), \
             patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_webhook(
                source.id,
                {"X-Gitee-Event": "Push Hook", "X-Gitee-Token": "gee-secret"},
                b'{"ref": "refs/heads/main"}',
            )
            assert log is not None

    @pytest.mark.asyncio
    async def test_gitee_token_failed(self, service):
        source_data = EventSourceCreate(
            name="gee-webhook-fail",
            source_type=EventSourceType.WEBHOOK,
            webhook_secret="gee-secret",
        )
        source = service.create_source(source_data)
        with patch("app.services.event_bus_service.verify_gitee_signature", return_value=False):
            with pytest.raises(ValueError, match="Gitee webhook token"):
                await service.receive_webhook(
                    source.id,
                    {"X-Gitee-Event": "Push Hook", "X-Gitee-Token": "bad"},
                    b"{}",
                )

    @pytest.mark.asyncio
    async def test_no_secret_skips_verification(self, service):
        source_data = EventSourceCreate(
            name="no-secret-webhook",
            source_type=EventSourceType.WEBHOOK,
        )
        source = service.create_source(source_data)
        with patch.object(service, "_process_event", new_callable=AsyncMock):
            log = await service.receive_webhook(
                source.id,
                {"X-GitHub-Event": "push"},
                b'{"ref": "refs/heads/main"}',
            )
            assert log is not None


class TestReplayEvent:
    @pytest.mark.asyncio
    async def test_replay_event_success(self, service):
        source_data = EventSourceCreate(name="replay-src", source_type=EventSourceType.WEBHOOK)
        source = service.create_source(source_data)
        with patch.object(service, "_process_event", new_callable=AsyncMock):
            original = await service.receive_event(source.id, "push", {"ref": "main"})
        with patch.object(service, "_process_event", new_callable=AsyncMock):
            replayed = await service.replay_event(original.id)
            assert replayed.source_id == source.id
            assert replayed.event_type == "push"


class TestParseGithubEventExtra:
    def test_other_event_with_sender(self, service):
        headers = {"X-GitHub-Event": "issues"}
        body = json.dumps({
            "sender": {"login": "user1"},
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_github_event(headers, body)
        assert result["pusher"] == "user1"
        assert result["platform"] == "github"

    def test_other_event_no_sender(self, service):
        headers = {"X-GitHub-Event": "issues"}
        body = json.dumps({"repository": {"full_name": "org/repo"}}).encode()
        result = service._parse_github_event(headers, body)
        assert result["pusher"] is None


class TestParseGitlabEventExtra:
    def test_invalid_json(self, service):
        headers = {"X-Gitlab-Event": "Push Hook"}
        result = service._parse_gitlab_event(headers, b"not json")
        assert result["event_type"] == "unknown"
        assert result["platform"] == "gitlab"

    def test_tag_ref(self, service):
        headers = {"X-Gitlab-Event": "Push Hook"}
        body = json.dumps({
            "ref": "refs/tags/v1.0",
            "user_name": "user1",
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        result = service._parse_gitlab_event(headers, body)
        assert result["tag"] == "v1.0"
        assert result["branch"] is None

    def test_other_event(self, service):
        headers = {"X-Gitlab-Event": "Note Hook"}
        body = json.dumps({
            "user_name": "commenter",
            "project": {"path_with_namespace": "org/repo"},
        }).encode()
        result = service._parse_gitlab_event(headers, body)
        assert result["pusher"] == "commenter"


class TestParseGiteeEventExtra:
    def test_invalid_json(self, service):
        headers = {"X-Gitee-Event": "Push Hook"}
        result = service._parse_gitee_event(headers, b"not json")
        assert result["event_type"] == "unknown"
        assert result["platform"] == "gitee"

    def test_tag_ref(self, service):
        headers = {"X-Gitee-Event": "Push Hook"}
        body = json.dumps({
            "ref": "refs/tags/v2.0",
            "user_name": "user1",
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_gitee_event(headers, body)
        assert result["tag"] == "v2.0"
        assert result["branch"] is None

    def test_other_event(self, service):
        headers = {"X-Gitee-Event": "Note Hook"}
        body = json.dumps({
            "user_name": "commenter",
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_gitee_event(headers, body)
        assert result["pusher"] == "commenter"

    def test_merge_request_with_user_name_fallback(self, service):
        headers = {"X-Gitee-Event": "Merge Request Hook"}
        body = json.dumps({
            "merge_request": {"action": "open", "target_branch": "main"},
            "user_name": "dev1",
            "repository": {"full_name": "org/repo"},
        }).encode()
        result = service._parse_gitee_event(headers, body)
        assert "merge_request" in result["event_type"]
        assert result["pusher"] == "dev1"

    def test_repository_path_with_namespace(self, service):
        headers = {"X-Gitee-Event": "Push Hook"}
        body = json.dumps({
            "ref": "refs/heads/main",
            "user_name": "user1",
            "repository": {"path_with_namespace": "org/repo-alt"},
        }).encode()
        result = service._parse_gitee_event(headers, body)
        assert result["repository"] == "org/repo-alt"


class TestVerifyWebhookSignature:
    def test_github_platform(self, service):
        with patch("app.services.event_bus_service.verify_github_signature", return_value=True):
            assert service._verify_webhook_signature(b"body", "sig", "secret", "github") is True

    def test_gitlab_platform(self, service):
        with patch("app.services.event_bus_service.verify_gitlab_signature", return_value=True):
            assert service._verify_webhook_signature(b"body", "sig", "secret", "gitlab") is True

    def test_gitee_platform(self, service):
        with patch("app.services.event_bus_service.verify_gitee_signature", return_value=True):
            assert service._verify_webhook_signature(b"body", "sig", "secret", "gitee") is True

    def test_unknown_platform(self, service):
        assert service._verify_webhook_signature(b"body", "sig", "secret", "unknown") is False


class TestStartFileWatcher:
    @pytest.mark.asyncio
    async def test_missing_path_returns_early(self, service):
        source = MagicMock()
        source.id = "test-src"
        source.config = {"path": "", "events": ["create"], "interval": 1}
        source.account_alias = "server1"
        source.status = EventSourceStatus.ENABLED
        await service._start_file_watcher(source)

    @pytest.mark.asyncio
    async def test_missing_alias_returns_early(self, service):
        source = MagicMock()
        source.id = "test-src"
        source.config = {"path": "/var/log", "events": ["create"], "interval": 1}
        source.account_alias = ""
        source.status = EventSourceStatus.ENABLED
        await service._start_file_watcher(source)


class TestStartMetricWatcher:
    @pytest.mark.asyncio
    async def test_missing_alias_returns_early(self, service):
        source = MagicMock()
        source.id = "test-src"
        source.config = {"metric": "cpu", "threshold": 90.0, "operator": "gt", "interval": 1}
        source.account_alias = ""
        await service._start_metric_watcher(source)


class TestGetMetricValue:
    @pytest.mark.asyncio
    async def test_cpu_metric(self, service):
        mock_monitor = MagicMock()
        mock_monitor.get_cpu_percent.return_value = {"usage_percent": 85.5}
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value={"usage_percent": 85.5})
        with patch("app.services.event_bus_service.asyncio.get_event_loop", return_value=mock_loop), \
             patch.dict("sys.modules", {"app.services.monitor_service": MagicMock(monitor_service=mock_monitor)}):
            result = await service._get_metric_value("server1", "cpu")
            assert result == 85.5

    @pytest.mark.asyncio
    async def test_memory_metric(self, service):
        mock_monitor = MagicMock()
        mock_monitor.get_memory_stats.return_value = {"usage_percent": 72.3}
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value={"usage_percent": 72.3})
        with patch("app.services.event_bus_service.asyncio.get_event_loop", return_value=mock_loop), \
             patch.dict("sys.modules", {"app.services.monitor_service": MagicMock(monitor_service=mock_monitor)}):
            result = await service._get_metric_value("server1", "memory")
            assert result == 72.3

    @pytest.mark.asyncio
    async def test_disk_metric(self, service):
        mock_monitor = MagicMock()
        mock_monitor.get_disk_stats.return_value = [
            {"usage_percent": 60.0},
            {"usage_percent": 80.0},
        ]
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=[{"usage_percent": 60.0}, {"usage_percent": 80.0}])
        with patch("app.services.event_bus_service.asyncio.get_event_loop", return_value=mock_loop), \
             patch.dict("sys.modules", {"app.services.monitor_service": MagicMock(monitor_service=mock_monitor)}):
            result = await service._get_metric_value("server1", "disk")
            assert result == 80.0

    @pytest.mark.asyncio
    async def test_disk_metric_empty(self, service):
        mock_monitor = MagicMock()
        mock_monitor.get_disk_stats.return_value = []
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=[])
        with patch("app.services.event_bus_service.asyncio.get_event_loop", return_value=mock_loop), \
             patch.dict("sys.modules", {"app.services.monitor_service": MagicMock(monitor_service=mock_monitor)}):
            result = await service._get_metric_value("server1", "disk")
            assert result is None

    @pytest.mark.asyncio
    async def test_unknown_metric(self, service):
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)
        with patch("app.services.event_bus_service.asyncio.get_event_loop", return_value=mock_loop):
            result = await service._get_metric_value("server1", "network")
            assert result is None
