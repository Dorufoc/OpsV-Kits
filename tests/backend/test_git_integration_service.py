from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.git_integration import (
    DeployPipeline,
    DeployStage,
    GitSyncConfig,
    WebhookConfig,
)


@pytest.fixture
def service():
    from app.services.git_integration_service import GitIntegrationService

    svc = GitIntegrationService()
    svc._webhook_configs.clear()
    svc._deploy_pipelines.clear()
    svc._deploy_records.clear()
    svc._sync_configs.clear()
    svc._sync_logs.clear()
    svc._cache.clear()
    return svc


class TestCache:
    def test_set_and_get_cached(self, service):
        service._set_cached("key1", {"data": "value"})
        result = service._get_cached("key1")
        assert result == {"data": "value"}

    def test_get_cached_expired(self, service):
        import time

        service._cache["key1"] = (time.time() - 100, {"data": "value"})
        result = service._get_cached("key1")
        assert result is None

    def test_get_cached_nonexistent(self, service):
        assert service._get_cached("nonexistent") is None

    def test_invalidate_cache(self, service):
        service._set_cached("alias:repo:key1", "val1")
        service._set_cached("alias:repo:key2", "val2")
        service._set_cached("other:repo:key3", "val3")
        service._invalidate_cache("alias", "repo")
        assert service._get_cached("alias:repo:key1") is None
        assert service._get_cached("alias:repo:key2") is None
        assert service._get_cached("other:repo:key3") is not None


class TestWebhookConfig:
    def test_create_webhook_config(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"], branch_filter="main")
        assert config.hook_id is not None
        assert config.platform == "github"
        assert config.enabled is True

    def test_get_webhook_config(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        result = service.get_webhook_config(config.hook_id)
        assert result is not None

    def test_get_webhook_config_nonexistent(self, service):
        assert service.get_webhook_config("nonexistent") is None

    def test_list_webhook_configs(self, service):
        service.create_webhook_config("a1", "/repo1", "github", ["push"])
        service.create_webhook_config("a2", "/repo2", "gitlab", ["push"])
        configs = service.list_webhook_configs()
        assert len(configs) == 2

    def test_list_webhook_configs_by_alias(self, service):
        service.create_webhook_config("a1", "/repo1", "github", ["push"])
        service.create_webhook_config("a2", "/repo2", "gitlab", ["push"])
        configs = service.list_webhook_configs(account_alias="a1")
        assert len(configs) == 1

    def test_update_webhook_config(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        updated = service.update_webhook_config(config.hook_id, events=["push", "pull_request"])
        assert "pull_request" in updated.events

    def test_update_webhook_config_nonexistent(self, service):
        result = service.update_webhook_config("nonexistent", events=["push"])
        assert result is None

    def test_delete_webhook_config(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        assert service.delete_webhook_config(config.hook_id) is True

    def test_delete_webhook_config_nonexistent(self, service):
        assert service.delete_webhook_config("nonexistent") is False


class TestHandleWebhookEvent:
    def test_nonexistent_config(self, service):
        result = service.handle_webhook_event("nonexistent", b"body", {})
        assert result["success"] is False

    def test_disabled_webhook(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        config.enabled = False
        result = service.handle_webhook_event(config.hook_id, b"body", {})
        assert result["success"] is False
        assert "禁用" in result["message"]

    def test_verification_fails(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        with patch("app.services.git_integration_service.verify_webhook") as mock_verify:
            from app.core.webhook_handler import WebhookVerificationError

            mock_verify.side_effect = WebhookVerificationError("bad signature")
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["success"] is False

    def test_parse_event_fails(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        with patch("app.services.git_integration_service.verify_webhook"), \
             patch("app.services.git_integration_service.parse_webhook_event") as mock_parse:
            from app.core.webhook_handler import WebhookVerificationError

            mock_parse.side_effect = WebhookVerificationError("bad event")
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["success"] is False

    def test_branch_not_matched(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"], branch_filter="main")
        with patch("app.services.git_integration_service.verify_webhook"), \
             patch("app.services.git_integration_service.parse_webhook_event") as mock_parse:
            event = MagicMock()
            event.branch = "develop"
            event.tag = None
            event.to_dict.return_value = {}
            mock_parse.return_value = event
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["matched"] is False

    def test_branch_matched(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"], branch_filter="main")
        with patch("app.services.git_integration_service.verify_webhook"), \
             patch("app.services.git_integration_service.parse_webhook_event") as mock_parse:
            event = MagicMock()
            event.branch = "main"
            event.tag = None
            event.platform = "github"
            event.event_type = "push"
            event.to_dict.return_value = {}
            mock_parse.return_value = event
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["matched"] is True


class TestDeployPipeline:
    def test_create_deploy_pipeline(self, service):
        pipeline = service.create_deploy_pipeline(
            name="test-pipeline",
            account_alias="test",
            repo_path="/repo",
            trigger_branches=["main"],
            trigger_tags="v.*",
            stages=[{"name": "build", "commands": ["npm run build"], "work_dir": "/repo"}],
        )
        assert pipeline.pipeline_id is not None
        assert pipeline.name == "test-pipeline"

    def test_get_deploy_pipeline(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        result = service.get_deploy_pipeline(pipeline.pipeline_id)
        assert result is not None

    def test_get_deploy_pipeline_nonexistent(self, service):
        assert service.get_deploy_pipeline("nonexistent") is None

    def test_list_deploy_pipelines(self, service):
        service.create_deploy_pipeline("p1", "a1", "/r1", [], "v.*", [])
        service.create_deploy_pipeline("p2", "a2", "/r2", [], "v.*", [])
        pipelines = service.list_deploy_pipelines()
        assert len(pipelines) == 2

    def test_list_deploy_pipelines_by_alias(self, service):
        service.create_deploy_pipeline("p1", "a1", "/r1", [], "v.*", [])
        service.create_deploy_pipeline("p2", "a2", "/r2", [], "v.*", [])
        pipelines = service.list_deploy_pipelines(account_alias="a1")
        assert len(pipelines) == 1

    def test_update_deploy_pipeline(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        updated = service.update_deploy_pipeline(pipeline.pipeline_id, name="updated")
        assert updated.name == "updated"

    def test_update_deploy_pipeline_nonexistent(self, service):
        result = service.update_deploy_pipeline("nonexistent", name="test")
        assert result is None

    def test_delete_deploy_pipeline(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        assert service.delete_deploy_pipeline(pipeline.pipeline_id) is True

    def test_delete_deploy_pipeline_nonexistent(self, service):
        assert service.delete_deploy_pipeline("nonexistent") is False


class TestDeployRecords:
    def test_list_deploy_records(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                records = service.list_deploy_records()
                assert len(records) >= 1

    def test_execute_nonexistent_pipeline(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.execute_deploy_pipeline("nonexistent")

    def test_get_deploy_record(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                result = service.get_deploy_record(record.record_id)
                assert result is not None

    def test_get_deploy_record_nonexistent(self, service):
        assert service.get_deploy_record("nonexistent") is None


class TestSyncConfig:
    def test_create_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config(
                account_alias="test",
                repo_path="/repo",
                sync_mode="notify_only",
                branch="main",
            )
            assert config.config_id is not None

    def test_get_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
            result = service.get_sync_config(config.config_id)
            assert result is not None

    def test_list_sync_configs(self, service):
        with patch.object(service, "_run_async"):
            service.create_sync_config("a1", "/r1", sync_mode="notify_only", branch="main")
            service.create_sync_config("a2", "/r2", sync_mode="notify_only", branch="main")
        configs = service.list_sync_configs()
        assert len(configs) == 2

    def test_list_sync_configs_by_alias(self, service):
        with patch.object(service, "_run_async"):
            service.create_sync_config("a1", "/r1", sync_mode="notify_only", branch="main")
            service.create_sync_config("a2", "/r2", sync_mode="notify_only", branch="main")
        configs = service.list_sync_configs(account_alias="a1")
        assert len(configs) == 1

    def test_update_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async"):
            updated = service.update_sync_config(config.config_id, check_interval=3600)
            assert updated.check_interval == 3600

    def test_update_sync_config_nonexistent(self, service):
        result = service.update_sync_config("nonexistent", check_interval=3600)
        assert result is None

    def test_delete_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async"):
            assert service.delete_sync_config(config.config_id) is True

    def test_delete_sync_config_nonexistent(self, service):
        with patch.object(service, "_run_async"):
            assert service.delete_sync_config("nonexistent") is False

    def test_get_sync_status(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch("app.services.git_integration_service.git_sync_scheduler") as mock_sched:
            mock_sched.get_task_status.return_value = {"status": "active"}
            status = service.get_sync_status(config.config_id)
            assert status is not None

    def test_get_sync_status_nonexistent(self, service):
        assert service.get_sync_status("nonexistent") is None

    def test_get_sync_logs(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        service._add_sync_log(config.config_id, "pull", "success", "ok")
        logs = service.get_sync_logs(config.config_id)
        assert len(logs) == 1


class TestGitOperations:
    def test_init_repo(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.init.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.init_repo("test", "/repo")
            assert result["success"] is True

    def test_clone_repo(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.clone.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.clone_repo("test", "https://github.com/repo.git", "/target")
            assert result["success"] is True

    def test_get_repo_info_cached(self, service):
        service._set_cached("test:/repo:repo_info", {"cached": True})
        result = service.get_repo_info("test", "/repo")
        assert result == {"cached": True}

    def test_get_repo_info_force_refresh(self, service):
        service._set_cached("test:/repo:repo_info", {"cached": True})
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"fresh": True}
            mock_git.return_value = mock_git_ops
            result = service.get_repo_info("test", "/repo", force_refresh=True)
            assert result == {"fresh": True}


class TestNewId:
    def test_new_id_length(self, service):
        id1 = service._new_id()
        assert len(id1) == 12

    def test_new_id_unique(self, service):
        ids = {service._new_id() for _ in range(100)}
        assert len(ids) == 100
