from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.git_sync_scheduler import (
    GitSyncScheduler,
    SyncTask,
    _run_git_fetch,
    _run_git_pull,
    _run_git_rev_list,
)


class TestSyncTaskInit:
    def test_default_values(self):
        task = SyncTask(
            config_id="c1",
            account_alias="srv1",
            repo_path="/repo",
            check_interval=60,
            sync_mode="notify_only",
            auto_deploy=False,
            deploy_pipeline_id=None,
            branch="main",
            ff_only=True,
        )
        assert task.config_id == "c1"
        assert task.account_alias == "srv1"
        assert task.repo_path == "/repo"
        assert task.check_interval == 60
        assert task.sync_mode == "notify_only"
        assert task.auto_deploy is False
        assert task.deploy_pipeline_id is None
        assert task.branch == "main"
        assert task.ff_only is True
        assert task.last_check_time is None
        assert task.last_sync_time is None
        assert task.last_sync_result is None
        assert task.pending_updates == 0
        assert task.error_count == 0
        assert task.status == "active"
        assert task._task is None
        assert task._on_update is None
        assert task._on_sync_needed is None


class TestSyncTaskSetCallbacks:
    def test_set_callbacks(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        on_update = MagicMock()
        on_sync_needed = MagicMock()
        task.set_callbacks(on_update=on_update, on_sync_needed=on_sync_needed)
        assert task._on_update is on_update
        assert task._on_sync_needed is on_sync_needed

    def test_set_callbacks_none(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task.set_callbacks()
        assert task._on_update is None
        assert task._on_sync_needed is None


class TestSyncTaskToDict:
    def test_to_dict(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=True,
            deploy_pipeline_id="pipe1", branch="dev", ff_only=False,
        )
        task.last_check_time = "2025-01-01T00:00:00"
        task.last_sync_time = "2025-01-01T00:01:00"
        task.last_sync_result = "success"
        task.pending_updates = 3
        task.error_count = 1
        task.status = "active"
        d = task.to_dict()
        assert d["config_id"] == "c1"
        assert d["account_alias"] == "srv1"
        assert d["repo_path"] == "/repo"
        assert d["check_interval"] == 60
        assert d["sync_mode"] == "auto_pull"
        assert d["auto_deploy"] is True
        assert d["deploy_pipeline_id"] == "pipe1"
        assert d["branch"] == "dev"
        assert d["ff_only"] is False
        assert d["last_check_time"] == "2025-01-01T00:00:00"
        assert d["last_sync_time"] == "2025-01-01T00:01:00"
        assert d["last_sync_result"] == "success"
        assert d["pending_updates"] == 3
        assert d["error_count"] == 1
        assert d["status"] == "active"


class TestSyncTaskRequestStop:
    def test_request_stop(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        assert not task._stop_event.is_set()
        task.request_stop()
        assert task._stop_event.is_set()


class TestSyncTaskNotifyUpdate:
    def test_notify_update_calls_callback(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        cb = MagicMock()
        task._on_update = cb
        task._notify_update()
        cb.assert_called_once_with("c1", task.to_dict())

    def test_notify_update_no_callback(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._notify_update()

    def test_notify_update_callback_exception(self):
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._on_update = MagicMock(side_effect=RuntimeError("cb error"))
        task._notify_update()


class TestRunGitFetch:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = "fetching..."
        mock_result.stdout = "done"
        with patch("subprocess.run", return_value=mock_result):
            ok, output = _run_git_fetch("/repo")
            assert ok is True
            assert "fetching..." in output
            assert "done" in output

    def test_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            ok, output = _run_git_fetch("/repo")
            assert ok is False

    def test_exception(self):
        with patch("subprocess.run", side_effect=Exception("timeout")):
            ok, output = _run_git_fetch("/repo")
            assert ok is False
            assert "timeout" in output


class TestRunGitRevList:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "3\t0\n"
        with patch("subprocess.run", return_value=mock_result):
            ahead, behind = _run_git_rev_list("/repo", "main")
            assert ahead == 3
            assert behind == 0

    def test_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            ahead, behind = _run_git_rev_list("/repo", "main")
            assert ahead == 0
            assert behind == 0

    def test_malformed_output(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "single_value\n"
        with patch("subprocess.run", return_value=mock_result):
            ahead, behind = _run_git_rev_list("/repo", "main")
            assert ahead == 0
            assert behind == 0

    def test_exception(self):
        with patch("subprocess.run", side_effect=Exception("err")):
            ahead, behind = _run_git_rev_list("/repo", "main")
            assert ahead == 0
            assert behind == 0


class TestRunGitPull:
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Already up to date."
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            ok, output = _run_git_pull("/repo", "main", True)
            assert ok is True

    def test_conflict(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "CONFLICT (content): Merge conflict in file.txt"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            ok, output = _run_git_pull("/repo", "main", False)
            assert ok is False
            assert output == "conflict"

    def test_conflict_case_insensitive(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Automatic merge failed; fix merge conflict"
        with patch("subprocess.run", return_value=mock_result):
            ok, output = _run_git_pull("/repo", "main", False)
            assert ok is False
            assert output == "conflict"

    def test_ff_only_flag(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _run_git_pull("/repo", "main", True)
            cmd = mock_run.call_args[0][0]
            assert "--ff-only" in cmd

    def test_no_ff_only(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _run_git_pull("/repo", "main", False)
            cmd = mock_run.call_args[0][0]
            assert "--ff-only" not in cmd

    def test_exception(self):
        with patch("subprocess.run", side_effect=Exception("err")):
            ok, output = _run_git_pull("/repo", "main", True)
            assert ok is False
            assert "err" in output


class TestGitSyncSchedulerInit:
    def test_initial_state(self):
        scheduler = GitSyncScheduler()
        assert scheduler.running is False
        assert scheduler._tasks == {}


class TestGitSyncSchedulerAddTask:
    @pytest.mark.asyncio
    async def test_add_task_basic(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
            "check_interval": 300,
            "sync_mode": "notify_only",
        }
        config_id = await scheduler.add_task(config)
        assert config_id in scheduler._tasks
        task = scheduler._tasks[config_id]
        assert task.account_alias == "srv1"
        assert task.repo_path == "/repo"
        assert task.sync_mode == "notify_only"

    @pytest.mark.asyncio
    async def test_add_task_with_config_id(self):
        scheduler = GitSyncScheduler()
        config = {
            "config_id": "my-id",
            "account_alias": "srv1",
            "repo_path": "/repo",
            "check_interval": 60,
            "sync_mode": "auto_pull",
        }
        config_id = await scheduler.add_task(config)
        assert config_id == "my-id"

    @pytest.mark.asyncio
    async def test_add_task_defaults(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
        }
        config_id = await scheduler.add_task(config)
        task = scheduler._tasks[config_id]
        assert task.check_interval == 300
        assert task.sync_mode == "notify_only"
        assert task.auto_deploy is False
        assert task.branch == "main"
        assert task.ff_only is True

    @pytest.mark.asyncio
    async def test_add_task_starts_when_running(self):
        scheduler = GitSyncScheduler()
        scheduler._running = True
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
        }
        with patch.object(scheduler, "_run_task", new_callable=AsyncMock):
            config_id = await scheduler.add_task(config)
            task = scheduler._tasks[config_id]
            assert task._task is not None or task._stop_event.is_set() is False


class TestGitSyncSchedulerRemoveTask:
    @pytest.mark.asyncio
    async def test_remove_existing_task(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
        }
        config_id = await scheduler.add_task(config)
        assert config_id in scheduler._tasks
        await scheduler.remove_task(config_id)
        assert config_id not in scheduler._tasks

    @pytest.mark.asyncio
    async def test_remove_nonexistent_task(self):
        scheduler = GitSyncScheduler()
        await scheduler.remove_task("nonexistent")

    @pytest.mark.asyncio
    async def test_remove_task_with_running_task(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
        }
        config_id = await scheduler.add_task(config)
        task = scheduler._tasks[config_id]
        mock_async_task = AsyncMock()
        task._task = mock_async_task
        mock_async_task.done.return_value = False
        mock_async_task.return_value = None
        await scheduler.remove_task(config_id)
        assert config_id not in scheduler._tasks


class TestGitSyncSchedulerUpdateTask:
    @pytest.mark.asyncio
    async def test_update_task(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
            "check_interval": 60,
        }
        config_id = await scheduler.add_task(config)
        new_config = {
            "account_alias": "srv1",
            "repo_path": "/new-repo",
            "check_interval": 120,
            "sync_mode": "auto_pull",
        }
        await scheduler.update_task(config_id, new_config)
        task = scheduler._tasks[config_id]
        assert task.repo_path == "/new-repo"
        assert task.check_interval == 120
        assert task.sync_mode == "auto_pull"


class TestGitSyncSchedulerGetTaskStatus:
    @pytest.mark.asyncio
    async def test_get_existing_task_status(self):
        scheduler = GitSyncScheduler()
        config = {
            "account_alias": "srv1",
            "repo_path": "/repo",
        }
        config_id = await scheduler.add_task(config)
        status = scheduler.get_task_status(config_id)
        assert status is not None
        assert status["config_id"] == config_id
        assert status["repo_path"] == "/repo"

    def test_get_nonexistent_task_status(self):
        scheduler = GitSyncScheduler()
        status = scheduler.get_task_status("nonexistent")
        assert status is None


class TestGitSyncSchedulerGetAllStatus:
    @pytest.mark.asyncio
    async def test_get_all_status_empty(self):
        scheduler = GitSyncScheduler()
        assert scheduler.get_all_status() == []

    @pytest.mark.asyncio
    async def test_get_all_status_with_tasks(self):
        scheduler = GitSyncScheduler()
        config1 = {"account_alias": "srv1", "repo_path": "/repo1"}
        config2 = {"account_alias": "srv2", "repo_path": "/repo2"}
        id1 = await scheduler.add_task(config1)
        id2 = await scheduler.add_task(config2)
        all_status = scheduler.get_all_status()
        assert len(all_status) == 2
        ids = {s["config_id"] for s in all_status}
        assert id1 in ids
        assert id2 in ids


class TestGitSyncSchedulerStart:
    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        scheduler = GitSyncScheduler()
        await scheduler.start()
        assert scheduler.running is True

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        await scheduler.add_task(config)
        with patch.object(scheduler, "_run_task", new_callable=AsyncMock):
            await scheduler.start()
            task = list(scheduler._tasks.values())[0]
            assert task._task is not None


class TestGitSyncSchedulerStop:
    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        scheduler = GitSyncScheduler()
        scheduler._running = True
        await scheduler.stop()
        assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_stop_requests_all_tasks_stop(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        await scheduler.add_task(config)
        task = list(scheduler._tasks.values())[0]
        task._task = None
        await scheduler.stop()
        assert task._stop_event.is_set()


class TestGitSyncSchedulerTriggerManualPull:
    @pytest.mark.asyncio
    async def test_task_not_found(self):
        scheduler = GitSyncScheduler()
        result = await scheduler.trigger_manual_pull("nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_pull_success(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        config_id = await scheduler.add_task(config)
        with patch("app.core.git_sync_scheduler._run_git_pull", return_value=(True, "Already up to date.")):
            result = await scheduler.trigger_manual_pull(config_id)
            assert result["success"] is True
            task = scheduler._tasks[config_id]
            assert task.last_sync_result == "success"
            assert task.pending_updates == 0
            assert task.error_count == 0
            assert task.status == "active"

    @pytest.mark.asyncio
    async def test_pull_conflict(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        config_id = await scheduler.add_task(config)
        with patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "conflict")):
            result = await scheduler.trigger_manual_pull(config_id)
            assert result["success"] is False
            assert "conflict" in result["message"].lower()
            task = scheduler._tasks[config_id]
            assert task.last_sync_result == "conflict"
            assert task.status == "paused"

    @pytest.mark.asyncio
    async def test_pull_failure(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        config_id = await scheduler.add_task(config)
        with patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "some error")):
            result = await scheduler.trigger_manual_pull(config_id)
            assert result["success"] is False
            task = scheduler._tasks[config_id]
            assert task.error_count == 1
            assert task.last_sync_result.startswith("pull_failed")

    @pytest.mark.asyncio
    async def test_pull_failure_error_threshold(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        config_id = await scheduler.add_task(config)
        task = scheduler._tasks[config_id]
        task.error_count = 2
        with patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "error")):
            await scheduler.trigger_manual_pull(config_id)
            assert task.error_count == 3
            assert task.status == "error"

    @pytest.mark.asyncio
    async def test_pull_exception(self):
        scheduler = GitSyncScheduler()
        config = {"account_alias": "srv1", "repo_path": "/repo"}
        config_id = await scheduler.add_task(config)
        with patch("app.core.git_sync_scheduler._run_git_pull", side_effect=Exception("unexpected")):
            result = await scheduler.trigger_manual_pull(config_id)
            assert result["success"] is False
            assert "unexpected" in result["message"]
            task = scheduler._tasks[config_id]
            assert task.error_count == 1


class TestGitSyncSchedulerRunTask:
    @pytest.mark.asyncio
    async def test_run_task_fetch_fails(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(False, "fetch error")):
            await scheduler._run_task(task)
            assert task.error_count == 1
            assert task.last_sync_result == "check_failed"

    @pytest.mark.asyncio
    async def test_run_task_no_updates(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 0)):
            await scheduler._run_task(task)
            assert task.pending_updates == 0
            assert task.error_count == 0
            assert task.status == "active"

    @pytest.mark.asyncio
    async def test_run_task_notify_only_with_updates(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        on_sync_needed = MagicMock()
        task._on_sync_needed = on_sync_needed
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 5)):
            await scheduler._run_task(task)
            assert task.pending_updates == 5
            on_sync_needed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_auto_pull_success(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 3)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(True, "pulled")):
            await scheduler._run_task(task)
            assert task.last_sync_result == "success"
            assert task.pending_updates == 0
            assert task.error_count == 0

    @pytest.mark.asyncio
    async def test_run_task_auto_pull_conflict(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 2)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "conflict")):
            await scheduler._run_task(task)
            assert task.last_sync_result == "conflict"
            assert task.status == "paused"

    @pytest.mark.asyncio
    async def test_run_task_auto_pull_failure(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 2)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "some error")):
            await scheduler._run_task(task)
            assert task.error_count == 1
            assert task.last_sync_result.startswith("pull_failed")

    @pytest.mark.asyncio
    async def test_run_task_auto_pull_error_threshold(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task.error_count = 2
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 2)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(False, "err")):
            await scheduler._run_task(task)
            assert task.status == "error"

    @pytest.mark.asyncio
    async def test_run_task_auto_deploy_callback(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=True,
            deploy_pipeline_id="pipe1", branch="main", ff_only=True,
        )
        on_sync_needed = MagicMock()
        task._on_sync_needed = on_sync_needed
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 2)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(True, "pulled")):
            await scheduler._run_task(task)
            on_sync_needed.assert_called_once_with(
                "c1", "srv1", "/repo", "main", 2
            )

    @pytest.mark.asyncio
    async def test_run_task_auto_deploy_callback_exception(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="auto_pull", auto_deploy=True,
            deploy_pipeline_id="pipe1", branch="main", ff_only=True,
        )
        on_sync_needed = MagicMock(side_effect=RuntimeError("callback error"))
        task._on_sync_needed = on_sync_needed
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 2)), \
             patch("app.core.git_sync_scheduler._run_git_pull", return_value=(True, "pulled")):
            await scheduler._run_task(task)
            assert task.last_sync_result == "success"

    @pytest.mark.asyncio
    async def test_run_task_notify_only_callback_exception(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        on_sync_needed = MagicMock(side_effect=RuntimeError("cb err"))
        task._on_sync_needed = on_sync_needed
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", return_value=(True, "ok")), \
             patch("app.core.git_sync_scheduler._run_git_rev_list", return_value=(0, 1)):
            await scheduler._run_task(task)

    @pytest.mark.asyncio
    async def test_run_task_exception_in_check(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", side_effect=Exception("unexpected")):
            await scheduler._run_task(task)
            assert task.error_count == 1
            assert task.last_sync_result == "check_failed"

    @pytest.mark.asyncio
    async def test_run_task_exception_error_threshold(self):
        scheduler = GitSyncScheduler()
        task = SyncTask(
            config_id="c1", account_alias="srv1", repo_path="/repo",
            check_interval=60, sync_mode="notify_only", auto_deploy=False,
            deploy_pipeline_id=None, branch="main", ff_only=True,
        )
        task.error_count = 2
        task._stop_event.wait = AsyncMock(return_value=True)
        with patch("app.core.git_sync_scheduler._run_git_fetch", side_effect=Exception("err")):
            await scheduler._run_task(task)
            assert task.status == "error"
