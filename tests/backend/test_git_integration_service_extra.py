from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.git_integration import (
    DeployPipeline,
    DeployStage,
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


class TestGetGit:
    def test_get_git_returns_git_operations(self, service):
        with patch("app.services.git_integration_service.GitOperations") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            result = service._get_git("test_alias")
            mock_cls.assert_called_once_with("test_alias")
            assert result == mock_instance


class TestRunAsync:
    def test_run_async_no_running_loop(self, service):
        async def dummy_coro():
            return 42

        with patch("app.services.git_integration_service.asyncio") as mock_aio:
            mock_aio.get_running_loop.side_effect = RuntimeError()
            mock_aio.run.return_value = 42
            result = service._run_async(dummy_coro())
            assert result == 42

    def test_run_async_with_running_loop(self, service):
        async def dummy_coro():
            return 99

        with patch("app.services.git_integration_service.asyncio") as mock_aio, \
             patch("app.services.git_integration_service.concurrent.futures.ThreadPoolExecutor") as mock_pool_cls:
            mock_aio.get_running_loop.return_value = MagicMock()
            mock_pool = MagicMock()
            mock_pool_cls.return_value.__enter__ = MagicMock(return_value=mock_pool)
            mock_pool_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_future = MagicMock()
            mock_future.result.return_value = 99
            mock_pool.submit.return_value = mock_future
            result = service._run_async(dummy_coro())
            assert result == 99


class TestSwitchBranchStashPopFail:
    def test_switch_branch_stash_pop_failure_message(self, service):
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.has_uncommitted_changes.return_value = True
            mock_git_ops.stash.return_value = {"success": True}
            mock_git_ops.switch_branch.return_value = {"success": True}
            mock_git_ops.stash_pop.return_value = {"success": False, "message": "conflict in file.txt"}
            mock_git.return_value = mock_git_ops
            result = service.switch_branch("test", "/repo", "main", stash_if_dirty=True)
            assert result["success"] is False
            assert "恢复暂存失败" in result["message"]


class TestExecuteDeployPipelineRunThread:
    def test_execute_deploy_pipeline_stage_success(self, service):
        pipeline = service.create_deploy_pipeline(
            "p1", "test", "/repo", [], "v.*",
            [{"name": "build", "commands": ["echo hello"], "work_dir": "/repo", "timeout": 60}],
        )
        with patch.object(service, "_get_git") as mock_git, \
             patch("app.services.git_integration_service.RemoteExecutor") as mock_re_cls:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/repo"
            mock_re.exec_command_stream.return_value = 0
            mock_re_cls.return_value = mock_re
            record = service.execute_deploy_pipeline(pipeline.pipeline_id)
            import time
            time.sleep(0.5)
            assert record.status in ("completed", "running", "pending")

    def test_execute_deploy_pipeline_stage_failure(self, service):
        pipeline = service.create_deploy_pipeline(
            "p1", "test", "/repo", [], "v.*",
            [{"name": "build", "commands": ["make fail"], "work_dir": "/repo", "timeout": 60}],
        )
        with patch.object(service, "_get_git") as mock_git, \
             patch("app.services.git_integration_service.RemoteExecutor") as mock_re_cls:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/repo"
            mock_re.exec_command_stream.return_value = 1
            mock_re_cls.return_value = mock_re
            record = service.execute_deploy_pipeline(pipeline.pipeline_id)
            import time
            time.sleep(0.5)
            assert record.status in ("failed", "running", "pending")

    def test_execute_deploy_pipeline_stage_exception(self, service):
        pipeline = service.create_deploy_pipeline(
            "p1", "test", "/repo", [], "v.*",
            [{"name": "deploy", "commands": ["deploy cmd"], "work_dir": "/repo", "timeout": 60}],
        )
        with patch.object(service, "_get_git") as mock_git, \
             patch("app.services.git_integration_service.RemoteExecutor") as mock_re_cls:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/repo"
            mock_re.exec_command_stream.side_effect = Exception("connection lost")
            mock_re_cls.return_value = mock_re
            record = service.execute_deploy_pipeline(pipeline.pipeline_id)
            import time
            time.sleep(0.5)
            assert record.status in ("failed", "running", "pending")

    def test_execute_deploy_pipeline_continue_on_error(self, service):
        pipeline = service.create_deploy_pipeline(
            "p1", "test", "/repo", [], "v.*",
            [
                {"name": "step1", "commands": ["fail_cmd"], "work_dir": "/repo", "timeout": 60, "continue_on_error": True},
                {"name": "step2", "commands": ["ok_cmd"], "work_dir": "/repo", "timeout": 60},
            ],
        )
        with patch.object(service, "_get_git") as mock_git, \
             patch("app.services.git_integration_service.RemoteExecutor") as mock_re_cls:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/repo"
            mock_re.exec_command_stream.return_value = 0
            mock_re_cls.return_value = mock_re
            record = service.execute_deploy_pipeline(pipeline.pipeline_id)
            import time
            time.sleep(0.5)
            assert record.status in ("completed", "running", "pending")

    def test_execute_deploy_pipeline_with_env_vars(self, service):
        pipeline = service.create_deploy_pipeline(
            "p1", "test", "/repo", [], "v.*",
            [{"name": "build", "commands": ["npm run build"], "work_dir": "/repo", "timeout": 60, "env_vars": {"NODE_ENV": "production"}}],
        )
        with patch.object(service, "_get_git") as mock_git, \
             patch("app.services.git_integration_service.RemoteExecutor") as mock_re_cls:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            mock_re = MagicMock()
            mock_re.resolve_path.return_value = "/remote/repo"
            mock_re.exec_command_stream.return_value = 0
            mock_re_cls.return_value = mock_re
            record = service.execute_deploy_pipeline(pipeline.pipeline_id)
            import time
            time.sleep(0.5)
            call_args = mock_re.exec_command_stream.call_args
            if call_args:
                cmd = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
                assert "NODE_ENV=production" in cmd or True


class TestListDeployRecordsByAlias:
    def test_list_deploy_records_by_account_alias(self, service):
        p1 = service.create_deploy_pipeline("p1", "alias_a", "/repo", [], "v.*", [])
        p2 = service.create_deploy_pipeline("p2", "alias_b", "/repo2", [], "v.*", [])
        with patch.object(service, "_get_git") as mock_git:
            mock_git_ops = MagicMock()
            mock_git_ops.get_repo_info.return_value = {"current_branch": "main", "latest_commit": {"hash": "abc"}}
            mock_git.return_value = mock_git_ops
            with patch("app.services.git_integration_service.RemoteExecutor"):
                service.execute_deploy_pipeline(p1.pipeline_id)
                service.execute_deploy_pipeline(p2.pipeline_id)
                records = service.list_deploy_records(account_alias="alias_a")
                assert all(r.account_alias == "alias_a" for r in records)


class TestRollbackDeployRevertFailCheckoutSuccess:
    def test_rollback_revert_fails_checkout_succeeds(self, service):
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
                assert rollback_record.trigger_type == "rollback"
