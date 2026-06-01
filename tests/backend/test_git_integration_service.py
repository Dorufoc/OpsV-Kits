from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.git_integration import (
    DeployPipeline,
    DeployStage,
    GitSyncConfig,
    WebhookConfig,
)
from app.services.git_integration_service import GitIntegrationService


@pytest.fixture
def service():
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

    def test_cache_overwrite(self, service):
        service._set_cached("key1", "old")
        service._set_cached("key1", "new")
        assert service._get_cached("key1") == "new"


class TestNewId:
    def test_new_id_length(self, service):
        id1 = service._new_id()
        assert len(id1) == 12

    def test_new_id_unique(self, service):
        ids = {service._new_id() for _ in range(100)}
        assert len(ids) == 100


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

    def test_update_webhook_config_with_none_values(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"])
        updated = service.update_webhook_config(config.hook_id, events=None, platform=None)
        assert updated.events == ["push"]
        assert updated.platform == "github"

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

    def test_wildcard_branch_filter(self, service):
        config = service.create_webhook_config("test", "/repo", "github", ["push"], branch_filter="*")
        with patch("app.services.git_integration_service.verify_webhook"), \
             patch("app.services.git_integration_service.parse_webhook_event") as mock_parse:
            event = MagicMock()
            event.branch = "any-branch"
            event.tag = None
            event.platform = "github"
            event.event_type = "push"
            event.to_dict.return_value = {}
            mock_parse.return_value = event
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["matched"] is True

    def test_with_deploy_pipeline(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        config = service.create_webhook_config("test", "/repo", "github", ["push"], deploy_pipeline_id=pipeline.pipeline_id)
        with patch("app.services.git_integration_service.verify_webhook"), \
             patch("app.services.git_integration_service.parse_webhook_event") as mock_parse, \
             patch.object(service, "execute_deploy_pipeline") as mock_exec:
            event = MagicMock()
            event.branch = "main"
            event.tag = None
            event.platform = "github"
            event.event_type = "push"
            event.to_dict.return_value = {}
            mock_parse.return_value = event
            mock_record = MagicMock()
            mock_record.record_id = "rec123"
            mock_exec.return_value = mock_record
            result = service.handle_webhook_event(config.hook_id, b"body", {})
            assert result["success"] is True
            assert result.get("deploy_record_id") == "rec123"


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

    def test_create_deploy_pipeline_with_stages(self, service):
        pipeline = service.create_deploy_pipeline(
            name="p1",
            account_alias="test",
            repo_path="/repo",
            trigger_branches=["main"],
            trigger_tags="v.*",
            stages=[
                {"name": "build", "commands": ["npm run build"], "work_dir": "/repo"},
                {"name": "deploy", "commands": ["npm run deploy"], "work_dir": "/repo", "continue_on_error": True},
            ],
        )
        assert len(pipeline.stages) == 2

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

    def test_update_deploy_pipeline_with_stages(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        updated = service.update_deploy_pipeline(
            pipeline.pipeline_id,
            stages=[{"name": "new_stage", "commands": ["echo hi"], "work_dir": "/repo"}],
        )
        assert len(updated.stages) == 1

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

    def test_list_deploy_records_by_pipeline(self, service):
        p1 = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        p2 = service.create_deploy_pipeline("p2", "test", "/repo2", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                service.execute_deploy_pipeline(p1.pipeline_id)
                service.execute_deploy_pipeline(p2.pipeline_id)
                records = service.list_deploy_records(pipeline_id=p1.pipeline_id)
                assert all(r.pipeline_id == p1.pipeline_id for r in records)

    def test_list_deploy_records_with_limit(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                service.execute_deploy_pipeline(pipeline.pipeline_id)
                records = service.list_deploy_records(limit=1)
                assert len(records) <= 1


class TestRollbackDeploy:
    def test_rollback_nonexistent_record(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.rollback_deploy("nonexistent")

    def test_rollback_revert_success(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git_ops.revert_commit.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                rollback_record = service.rollback_deploy(record.record_id)
                assert rollback_record is not None
                assert rollback_record.trigger_type == "rollback"

    def test_rollback_revert_fail_checkout_success(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git_ops.revert_commit.return_value = {"success": False, "message": "conflict"}
            mock_git_ops.checkout_commit.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                rollback_record = service.rollback_deploy(record.record_id)
                assert rollback_record is not None

    def test_rollback_both_fail(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git_ops.revert_commit.return_value = {"success": False, "message": "conflict"}
            mock_git_ops.checkout_commit.return_value = {"success": False, "message": "checkout failed"}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                from app.core.git_operations import GitOperationError
                with pytest.raises(GitOperationError, match="回滚失败"):
                    service.rollback_deploy(record.record_id)

    def test_rollback_pipeline_deleted(self, service):
        pipeline = service.create_deploy_pipeline("p1", "test", "/repo", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git_ops.revert_commit.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                record = service.execute_deploy_pipeline(pipeline.pipeline_id)
                service.delete_deploy_pipeline(pipeline.pipeline_id)
                with pytest.raises(ValueError, match="不存在"):
                    service.rollback_deploy(record.record_id)


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

    def test_create_sync_config_disabled(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config(
                account_alias="test",
                repo_path="/repo",
                enabled=False,
                sync_mode="notify_only",
                branch="main",
            )
            assert config.enabled is False

    def test_get_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
            result = service.get_sync_config(config.config_id)
            assert result is not None

    def test_get_sync_config_nonexistent(self, service):
        assert service.get_sync_config("nonexistent") is None

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

    def test_update_sync_config_disable(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async"):
            updated = service.update_sync_config(config.config_id, enabled=False)
            assert updated.enabled is False

    def test_update_sync_config_nonexistent(self, service):
        result = service.update_sync_config("nonexistent", check_interval=3600)
        assert result is None

    def test_delete_sync_config(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async"):
            assert service.delete_sync_config(config.config_id) is True

    def test_delete_sync_config_disabled(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", enabled=False, sync_mode="notify_only", branch="main")
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

    def test_get_sync_logs_with_limit(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        for i in range(10):
            service._add_sync_log(config.config_id, "pull", "success", f"log {i}")
        logs = service.get_sync_logs(config.config_id, limit=5)
        assert len(logs) == 5

    def test_get_sync_logs_nonexistent(self, service):
        logs = service.get_sync_logs("nonexistent")
        assert logs == []


class TestManualPull:
    def test_manual_pull_success(self, service):
        with patch.object(service, "_run_async", return_value={"success": True, "message": "up to date"}):
            with patch.object(service, "_run_async", return_value=None):
                config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async", return_value={"success": True, "message": "pulled"}):
            result = service.manual_pull(config.config_id)
            assert result["success"] is True

    def test_manual_pull_conflict(self, service):
        with patch.object(service, "_run_async", return_value={"success": True, "message": "ok"}):
            with patch.object(service, "_run_async", return_value=None):
                config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async", return_value={"success": False, "message": "merge Conflict detected"}):
            result = service.manual_pull(config.config_id)
            assert result["success"] is False

    def test_manual_pull_error(self, service):
        with patch.object(service, "_run_async", return_value={"success": True, "message": "ok"}):
            with patch.object(service, "_run_async", return_value=None):
                config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        with patch.object(service, "_run_async", return_value={"success": False, "message": "connection refused"}):
            result = service.manual_pull(config.config_id)
            assert result["success"] is False

    def test_manual_pull_nonexistent(self, service):
        result = service.manual_pull("nonexistent")
        assert result["success"] is False


class TestAddSyncLog:
    def test_add_sync_log_trimming(self, service):
        with patch.object(service, "_run_async"):
            config = service.create_sync_config("test", "/repo", sync_mode="notify_only", branch="main")
        for i in range(60):
            service._add_sync_log(config.config_id, "pull", "success", f"log {i}")
        logs = service.get_sync_logs(config.config_id, limit=100)
        assert len(logs) == 50

    def test_add_sync_log_nonexistent_config(self, service):
        service._add_sync_log("nonexistent", "pull", "success", "ok")
        logs = service.get_sync_logs("nonexistent")
        assert logs == []


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

    def test_clone_repo_with_options(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.clone.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.clone_repo("test", "https://github.com/repo.git", "/target", branch="main", depth=1)
            mock_git_ops.clone.assert_called_once_with("https://github.com/repo.git", "/target", branch="main", depth=1)

    def test_add_remote(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.add_remote.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.add_remote("test", "/repo", "origin", "https://github.com/repo.git")
            assert result["success"] is True

    def test_set_remote_url(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.set_remote_url.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.set_remote_url("test", "/repo", "origin", "https://github.com/repo2.git")
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

    def test_list_branches_cached(self, service):
        service._set_cached("test:/repo:branches", [{"name": "main"}])
        result = service.list_branches("test", "/repo")
        assert result == [{"name": "main"}]

    def test_list_branches_force_refresh(self, service):
        service._set_cached("test:/repo:branches", [{"name": "main"}])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.list_branches.return_value = [{"name": "develop"}]
            mock_git.return_value = mock_git_ops
            result = service.list_branches("test", "/repo", force_refresh=True)
            assert result == [{"name": "develop"}]

    def test_create_branch(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.create_branch.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.create_branch("test", "/repo", "feature", base_ref="main", checkout=True)
            mock_git_ops.create_branch.assert_called_once_with("/repo", "feature", base_ref="main", checkout=True)

    def test_switch_branch_clean(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = False
            mock_git_ops.switch_branch.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main")
            assert result["success"] is True

    def test_switch_branch_dirty_no_stash(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = True
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main", stash_if_dirty=False)
            assert result["success"] is False
            assert "未提交变更" in result["message"]

    def test_switch_branch_dirty_stash_success(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = True
            mock_git_ops.stash.return_value = {"success": True}
            mock_git_ops.switch_branch.return_value = {"success": True}
            mock_git_ops.stash_pop.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main", stash_if_dirty=True)
            assert result["success"] is True

    def test_switch_branch_stash_fail(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = True
            mock_git_ops.stash.return_value = {"success": False, "message": "stash error"}
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main", stash_if_dirty=True)
            assert result["success"] is False

    def test_switch_branch_stash_pop_fail(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = True
            mock_git_ops.stash.return_value = {"success": True}
            mock_git_ops.switch_branch.return_value = {"success": True}
            mock_git_ops.stash_pop.return_value = {"success": False, "message": "pop error"}
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main", stash_if_dirty=True)
            assert result["success"] is False
            assert "恢复暂存失败" in result["message"]

    def test_merge_branch(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.merge_branch.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.merge_branch("test", "/repo", "feature", target_branch="main")
            mock_git_ops.merge_branch.assert_called_once_with("/repo", "feature", target_branch="main")

    def test_delete_branch_unmerged(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.is_branch_merged.return_value = False
            mock_git.return_value = mock_git_ops
            result = service.delete_branch("test", "/repo", "feature")
            assert result["success"] is False
            assert "尚未合并" in result["message"]

    def test_delete_branch_force(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.is_branch_merged.return_value = False
            mock_git_ops.delete_branch.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.delete_branch("test", "/repo", "feature", force=True)
            assert result["success"] is True

    def test_delete_branch_merged(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.is_branch_merged.return_value = True
            mock_git_ops.delete_branch.return_value = {"success": True}
            mock_git.return_value = mock_git_ops
            result = service.delete_branch("test", "/repo", "feature")
            assert result["success"] is True

    def test_compare_branches(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.compare_branches.return_value = {"ahead": 3, "behind": 1}
            mock_git.return_value = mock_git_ops
            result = service.compare_branches("test", "/repo", "main", "develop")
            assert result["ahead"] == 3

    def test_get_commit_log(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.log.return_value = {"commits": [], "total": 0}
            mock_git.return_value = mock_git_ops
            result = service.get_commit_log("test", "/repo", page=1, page_size=10)
            assert "commits" in result

    def test_get_commit_detail(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.show_commit.return_value = {"hash": "abc123", "message": "test"}
            mock_git.return_value = mock_git_ops
            result = service.get_commit_detail("test", "/repo", "abc123")
            assert result["hash"] == "abc123"

    def test_get_diff(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.diff.return_value = "diff content"
            mock_git.return_value = mock_git_ops
            result = service.get_diff("test", "/repo", "main", "develop")
            assert result == "diff content"
