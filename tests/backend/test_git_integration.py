from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.git_operations import GitOperationError
from app.core.git_sync_scheduler import GitSyncScheduler, SyncTask
from app.core.webhook_handler import (
    WebhookEvent,
    WebhookVerificationError,
    parse_gitee_event,
    parse_github_event,
    parse_gitlab_event,
    verify_gitee_signature,
    verify_github_signature,
    verify_gitlab_signature,
    verify_webhook,
)
from app.models.git_integration import (
    DeployPipeline,
    DeployStage,
    GitRepo,
    GitSyncConfig,
    WebhookConfig,
)
from app.services.git_integration_service import GitIntegrationService


class TestVerifyGithubSignature:
    def test_verify_github_signature_valid(self):
        secret = "my_secret_key"
        body = b'{"ref":"refs/heads/main"}'
        expected_sig = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert verify_github_signature(body, expected_sig, secret) is True

    def test_verify_github_signature_invalid(self):
        secret = "my_secret_key"
        body = b'{"ref":"refs/heads/main"}'
        wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        assert verify_github_signature(body, wrong_sig, secret) is False


class TestVerifyGitlabSignature:
    def test_verify_gitlab_signature_valid(self):
        secret = "my_gitlab_token"
        token = "my_gitlab_token"
        assert verify_gitlab_signature(b"body", token, secret) is True

    def test_verify_gitlab_signature_invalid(self):
        secret = "my_gitlab_token"
        token = "wrong_token"
        assert verify_gitlab_signature(b"body", token, secret) is False


class TestVerifyGiteeSignature:
    def test_verify_gitee_signature_valid(self):
        secret = "my_gitee_password"
        password = "my_gitee_password"
        assert verify_gitee_signature(b"body", password, secret) is True

    def test_verify_gitee_signature_invalid(self):
        secret = "my_gitee_password"
        password = "wrong_password"
        assert verify_gitee_signature(b"body", password, secret) is False


class TestVerifyWebhook:
    def test_verify_webhook_github_valid(self):
        secret = "secret"
        body = b'{"ref":"refs/heads/main"}'
        sig = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        headers = {"X-Hub-Signature-256": sig}
        assert verify_webhook("github", body, headers, secret) is True

    def test_verify_webhook_github_missing_header(self):
        with pytest.raises(WebhookVerificationError, match="Missing X-Hub-Signature-256"):
            verify_webhook("github", b"body", {}, "secret")

    def test_verify_webhook_gitlab_valid(self):
        headers = {"X-Gitlab-Token": "token123"}
        assert verify_webhook("gitlab", b"body", headers, "token123") is True

    def test_verify_webhook_gitlab_missing_header(self):
        with pytest.raises(WebhookVerificationError, match="Missing X-Gitlab-Token"):
            verify_webhook("gitlab", b"body", {}, "token123")

    def test_verify_webhook_gitee_valid(self):
        headers = {"X-Gitee-Password": "pass123"}
        assert verify_webhook("gitee", b"body", headers, "pass123") is True

    def test_verify_webhook_gitee_missing_header(self):
        with pytest.raises(WebhookVerificationError, match="Missing X-Gitee-Password"):
            verify_webhook("gitee", b"body", {}, "pass123")

    def test_verify_webhook_unsupported_platform(self):
        with pytest.raises(WebhookVerificationError, match="Unsupported platform"):
            verify_webhook("bitbucket", b"body", {}, "secret")


class TestParseGithubPushEvent:
    def test_parse_github_push_event(self):
        body = json.dumps({
            "ref": "refs/heads/main",
            "commits": [
                {"id": "abc123", "message": "test commit", "author": {"name": "dev"}}
            ],
            "pusher": {"name": "devuser"},
            "repository": {"full_name": "owner/repo"},
        }).encode("utf-8")
        headers = {"X-GitHub-Event": "push"}
        event = parse_github_event(body, headers)
        assert event.platform == "github"
        assert event.event_type == "push"
        assert event.branch == "main"
        assert event.tag is None
        assert len(event.commits) == 1
        assert event.commits[0]["id"] == "abc123"
        assert event.pusher == "devuser"
        assert event.repository == "owner/repo"

    def test_parse_github_tag_event(self):
        body = json.dumps({
            "ref": "refs/tags/v1.0",
            "commits": [],
            "repository": {"full_name": "owner/repo"},
        }).encode("utf-8")
        headers = {"X-GitHub-Event": "push"}
        event = parse_github_event(body, headers)
        assert event.branch is None
        assert event.tag == "v1.0"

    def test_parse_github_pull_request_event(self):
        body = json.dumps({
            "action": "opened",
            "pull_request": {
                "base": {"ref": "main"},
                "user": {"login": "pruser"},
            },
            "repository": {"full_name": "owner/repo"},
        }).encode("utf-8")
        headers = {"X-GitHub-Event": "pull_request"}
        event = parse_github_event(body, headers)
        assert event.event_type == "pull_request.opened"
        assert event.branch == "main"
        assert event.pusher == "pruser"

    def test_parse_github_invalid_json(self):
        with pytest.raises(WebhookVerificationError, match="Invalid JSON body"):
            parse_github_event(b"not json", {"X-GitHub-Event": "push"})


class TestParseGitlabPushEvent:
    def test_parse_gitlab_push_event(self):
        body = json.dumps({
            "ref": "refs/heads/develop",
            "commits": [
                {"id": "def456", "message": "gitlab commit"}
            ],
            "user_name": "gitlabuser",
            "project": {"path_with_namespace": "group/project"},
        }).encode("utf-8")
        headers = {"X-Gitlab-Event": "Push Hook"}
        event = parse_gitlab_event(body, headers)
        assert event.platform == "gitlab"
        assert event.event_type == "Push Hook"
        assert event.branch == "develop"
        assert len(event.commits) == 1
        assert event.pusher == "gitlabuser"
        assert event.repository == "group/project"

    def test_parse_gitlab_merge_request_event(self):
        body = json.dumps({
            "object_attributes": {
                "action": "merge",
                "target_branch": "main",
            },
            "user": {"name": "mruser"},
            "project": {"path_with_namespace": "group/project"},
        }).encode("utf-8")
        headers = {"X-Gitlab-Event": "Merge Request Hook"}
        event = parse_gitlab_event(body, headers)
        assert event.event_type == "merge_request.merge"
        assert event.branch == "main"
        assert event.pusher == "mruser"


class TestParseGiteePushEvent:
    def test_parse_gitee_push_event(self):
        body = json.dumps({
            "ref": "refs/heads/feature",
            "commits": [
                {"id": "ghi789", "message": "gitee commit"}
            ],
            "user_name": "giteeuser",
            "repository": {"full_name": "org/repo"},
        }).encode("utf-8")
        headers = {"X-Gitee-Event": "Push Hook"}
        event = parse_gitee_event(body, headers)
        assert event.platform == "gitee"
        assert event.event_type == "Push Hook"
        assert event.branch == "feature"
        assert len(event.commits) == 1
        assert event.pusher == "giteeuser"
        assert event.repository == "org/repo"

    def test_parse_gitee_merge_request_event(self):
        body = json.dumps({
            "merge_request": {
                "action": "open",
                "target_branch": "main",
            },
            "user": {"name": "giteemruser"},
            "repository": {"full_name": "org/repo"},
        }).encode("utf-8")
        headers = {"X-Gitee-Event": "Merge Request Hook"}
        event = parse_gitee_event(body, headers)
        assert event.event_type == "merge_request.open"
        assert event.branch == "main"
        assert event.pusher == "giteemruser"


class TestGitOperationError:
    def test_git_operation_error(self):
        with pytest.raises(GitOperationError, match="something went wrong"):
            raise GitOperationError("something went wrong")

    def test_git_operation_error_is_exception(self):
        err = GitOperationError("test")
        assert isinstance(err, Exception)
        assert str(err) == "test"


class TestGitRepoModel:
    def test_git_repo_model(self):
        now = datetime.now(timezone.utc).isoformat()
        repo = GitRepo(
            account_alias="server1",
            repo_path="/home/user/project",
            current_branch="main",
            branches=["main", "develop"],
            remotes={"origin": "git@github.com:user/project.git"},
            repo_size="150M",
            last_commit_hash="abc123def456",
            last_commit_message="Initial commit",
            last_commit_author="dev",
            last_commit_time=now,
            is_bare=False,
            has_uncommitted_changes=False,
        )
        assert repo.account_alias == "server1"
        assert repo.repo_path == "/home/user/project"
        assert repo.current_branch == "main"
        assert "main" in repo.branches
        assert repo.remotes["origin"] == "git@github.com:user/project.git"
        data = repo.model_dump()
        assert data["account_alias"] == "server1"
        assert data["last_commit_hash"] == "abc123def456"


class TestWebhookConfigModel:
    def test_webhook_config_model(self):
        now = datetime.now(timezone.utc).isoformat()
        config = WebhookConfig(
            hook_id="hook123",
            account_alias="server1",
            repo_path="/home/user/project",
            platform="github",
            secret="s3cret",
            events=["push"],
            branch_filter="main",
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        assert config.hook_id == "hook123"
        assert config.platform == "github"
        assert config.events == ["push"]
        assert config.branch_filter == "main"
        assert config.enabled is True
        data = config.model_dump()
        assert data["hook_id"] == "hook123"
        assert data["secret"] == "s3cret"


class TestDeployPipelineModel:
    def test_deploy_pipeline_model(self):
        now = datetime.now(timezone.utc).isoformat()
        stage = DeployStage(
            name="build",
            commands=["npm install", "npm run build"],
            work_dir="/home/user/project",
        )
        pipeline = DeployPipeline(
            pipeline_id="pipe123",
            name="CI Pipeline",
            account_alias="server1",
            repo_path="/home/user/project",
            trigger_branches=["main"],
            trigger_tags="v.*",
            stages=[stage],
            created_at=now,
            updated_at=now,
        )
        assert pipeline.pipeline_id == "pipe123"
        assert pipeline.name == "CI Pipeline"
        assert len(pipeline.stages) == 1
        assert pipeline.stages[0].name == "build"
        assert pipeline.stages[0].commands == ["npm install", "npm run build"]
        data = pipeline.model_dump()
        assert data["pipeline_id"] == "pipe123"
        assert len(data["stages"]) == 1


class TestGitSyncConfigModel:
    def test_git_sync_config_model(self):
        now = datetime.now(timezone.utc).isoformat()
        config = GitSyncConfig(
            config_id="sync123",
            account_alias="server1",
            repo_path="/home/user/project",
            enabled=True,
            check_interval=1800,
            sync_mode="auto_pull",
            branch="main",
            ff_only=True,
            created_at=now,
            updated_at=now,
        )
        assert config.config_id == "sync123"
        assert config.sync_mode == "auto_pull"
        assert config.check_interval == 1800
        assert config.ff_only is True
        assert config.status == "active"
        data = config.model_dump()
        assert data["config_id"] == "sync123"
        assert data["pending_updates"] == 0


class TestGitIntegrationService:
    def setup_method(self):
        self.service = GitIntegrationService()

    def test_create_webhook_config(self):
        config = self.service.create_webhook_config(
            account_alias="server1",
            repo_path="/home/user/project",
            platform="github",
            events=["push"],
            branch_filter="main",
        )
        assert config.hook_id
        assert config.account_alias == "server1"
        assert config.platform == "github"
        assert config.events == ["push"]
        assert config.branch_filter == "main"
        assert config.enabled is True
        assert config.secret
        assert config.created_at
        assert config.updated_at

    def test_list_webhook_configs(self):
        self.service.create_webhook_config(
            account_alias="server1",
            repo_path="/repo1",
            platform="github",
            events=["push"],
        )
        self.service.create_webhook_config(
            account_alias="server2",
            repo_path="/repo2",
            platform="gitlab",
            events=["push"],
        )
        all_configs = self.service.list_webhook_configs()
        assert len(all_configs) == 2
        server1_configs = self.service.list_webhook_configs(account_alias="server1")
        assert len(server1_configs) == 1
        assert server1_configs[0].account_alias == "server1"

    def test_create_deploy_pipeline(self):
        pipeline = self.service.create_deploy_pipeline(
            name="Test Pipeline",
            account_alias="server1",
            repo_path="/home/user/project",
            trigger_branches=["main"],
            trigger_tags="v.*",
            stages=[
                {"name": "build", "commands": ["npm install"], "work_dir": "/project"},
            ],
        )
        assert pipeline.pipeline_id
        assert pipeline.name == "Test Pipeline"
        assert pipeline.account_alias == "server1"
        assert len(pipeline.stages) == 1
        assert pipeline.stages[0].name == "build"

    def test_create_sync_config(self):
        with patch.object(self.service, "_run_async"):
            config = self.service.create_sync_config(
                account_alias="server1",
                repo_path="/home/user/project",
                enabled=True,
                sync_mode="auto_pull",
                branch="main",
            )
        assert config.config_id
        assert config.account_alias == "server1"
        assert config.sync_mode == "auto_pull"
        assert config.branch == "main"
        assert config.enabled is True

    def test_cache_mechanism(self):
        self.service._set_cached("test_key", {"data": "value"})
        result = self.service._get_cached("test_key")
        assert result == {"data": "value"}

    def test_cache_mechanism_expired(self):
        self.service._cache_ttl = -1.0
        self.service._set_cached("expired_key", {"data": "old"})
        result = self.service._get_cached("expired_key")
        assert result is None
        self.service._cache_ttl = 30.0

    def test_cache_invalidation(self):
        self.service._set_cached("server1:/repo:info", {"data": "value"})
        self.service._set_cached("server1:/repo:branches", ["main"])
        self.service._set_cached("server2:/repo:info", {"other": "data"})
        self.service._invalidate_cache("server1", "/repo")
        assert self.service._get_cached("server1:/repo:info") is None
        assert self.service._get_cached("server1:/repo:branches") is None
        assert self.service._get_cached("server2:/repo:info") == {"other": "data"}

    def test_get_webhook_config(self):
        config = self.service.create_webhook_config(
            account_alias="server1",
            repo_path="/repo",
            platform="github",
            events=["push"],
        )
        found = self.service.get_webhook_config(config.hook_id)
        assert found is not None
        assert found.hook_id == config.hook_id
        assert self.service.get_webhook_config("nonexistent") is None

    def test_delete_webhook_config(self):
        config = self.service.create_webhook_config(
            account_alias="server1",
            repo_path="/repo",
            platform="github",
            events=["push"],
        )
        assert self.service.delete_webhook_config(config.hook_id) is True
        assert self.service.get_webhook_config(config.hook_id) is None
        assert self.service.delete_webhook_config("nonexistent") is False

    def test_update_webhook_config(self):
        config = self.service.create_webhook_config(
            account_alias="server1",
            repo_path="/repo",
            platform="github",
            events=["push"],
        )
        updated = self.service.update_webhook_config(
            config.hook_id, events=["push", "pull_request"], enabled=False
        )
        assert updated is not None
        assert updated.events == ["push", "pull_request"]
        assert updated.enabled is False

    def test_list_deploy_pipelines(self):
        self.service.create_deploy_pipeline(
            name="P1", account_alias="server1", repo_path="/r1",
            trigger_branches=["main"], trigger_tags="", stages=[],
        )
        self.service.create_deploy_pipeline(
            name="P2", account_alias="server2", repo_path="/r2",
            trigger_branches=["main"], trigger_tags="", stages=[],
        )
        all_pipelines = self.service.list_deploy_pipelines()
        assert len(all_pipelines) == 2
        server1_pipelines = self.service.list_deploy_pipelines(account_alias="server1")
        assert len(server1_pipelines) == 1

    def test_list_sync_configs(self):
        with patch.object(self.service, "_run_async"):
            self.service.create_sync_config(
                account_alias="server1", repo_path="/r1", sync_mode="notify_only", branch="main",
            )
            self.service.create_sync_config(
                account_alias="server2", repo_path="/r2", sync_mode="auto_pull", branch="develop",
            )
        all_configs = self.service.list_sync_configs()
        assert len(all_configs) == 2
        server1_configs = self.service.list_sync_configs(account_alias="server1")
        assert len(server1_configs) == 1


class TestSyncTask:
    def test_sync_task_to_dict(self):
        task = SyncTask(
            config_id="cfg123",
            account_alias="server1",
            repo_path="/home/user/project",
            check_interval=300,
            sync_mode="auto_pull",
            auto_deploy=False,
            deploy_pipeline_id=None,
            branch="main",
            ff_only=True,
        )
        d = task.to_dict()
        assert d["config_id"] == "cfg123"
        assert d["account_alias"] == "server1"
        assert d["repo_path"] == "/home/user/project"
        assert d["check_interval"] == 300
        assert d["sync_mode"] == "auto_pull"
        assert d["auto_deploy"] is False
        assert d["deploy_pipeline_id"] is None
        assert d["branch"] == "main"
        assert d["ff_only"] is True
        assert d["last_check_time"] is None
        assert d["last_sync_time"] is None
        assert d["last_sync_result"] is None
        assert d["pending_updates"] == 0
        assert d["error_count"] == 0
        assert d["status"] == "active"

    def test_sync_task_callbacks(self):
        task = SyncTask(
            config_id="cfg123",
            account_alias="server1",
            repo_path="/repo",
            check_interval=300,
            sync_mode="notify_only",
            auto_deploy=False,
            deploy_pipeline_id=None,
            branch="main",
            ff_only=True,
        )
        callback = MagicMock()
        task.set_callbacks(on_update=callback)
        task._notify_update()
        callback.assert_called_once_with("cfg123", task.to_dict())


class TestGitSyncScheduler:
    def test_sync_scheduler_add_remove_task(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "server1",
            "repo_path": "/home/user/project",
            "check_interval": 300,
            "sync_mode": "notify_only",
            "branch": "main",
            "ff_only": True,
        }
        config_id = asyncio_run(scheduler.add_task(config))
        assert config_id in scheduler._tasks
        status = scheduler.get_task_status(config_id)
        assert status is not None
        assert status["account_alias"] == "server1"
        assert status["branch"] == "main"

        asyncio_run(scheduler.remove_task(config_id))
        assert scheduler.get_task_status(config_id) is None

    def test_sync_scheduler_get_all_status(self):
        scheduler = GitSyncScheduler()
        id1 = asyncio_run(scheduler.add_task({
            "account_alias": "s1", "repo_path": "/r1",
            "check_interval": 300, "sync_mode": "notify_only", "branch": "main",
        }))
        id2 = asyncio_run(scheduler.add_task({
            "account_alias": "s2", "repo_path": "/r2",
            "check_interval": 600, "sync_mode": "auto_pull", "branch": "develop",
        }))
        all_status = scheduler.get_all_status()
        assert len(all_status) == 2
        asyncio_run(scheduler.remove_task(id1))
        asyncio_run(scheduler.remove_task(id2))

    def test_sync_scheduler_get_nonexistent_status(self):
        scheduler = GitSyncScheduler()
        assert scheduler.get_task_status("nonexistent") is None


def asyncio_run(coro):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=10)
    else:
        return asyncio.run(coro)
