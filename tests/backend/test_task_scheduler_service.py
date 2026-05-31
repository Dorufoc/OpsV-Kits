from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.task_scheduler import (
    AlertChannel,
    AlertConfig,
    AlertConfigCreate,
    ExecutionStatus,
    RetryPolicy,
    RetryPolicyCreate,
    RetryStrategy,
    ScheduledTask,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    TaskExecution,
    TaskPriority,
    TaskStatus,
    TriggerMode,
)
from app.services.task_scheduler_service import TaskSchedulerService


@pytest.fixture
def svc(tmp_path, monkeypatch):
    db_path = tmp_path / "scheduler.db"
    monkeypatch.setattr(
        "app.services.task_scheduler_service._DB_PATH", db_path
    )
    monkeypatch.setattr(
        "app.services.task_scheduler_service._PERSIST_DIR", tmp_path
    )
    service = TaskSchedulerService()
    return service


def _make_task_create(**overrides) -> ScheduledTaskCreate:
    defaults = {
        "name": "test-task",
        "description": "a test task",
        "cron_expression": "*/5 * * * *",
        "timezone": "Asia/Shanghai",
        "task_type": "shell",
        "command": "echo hello",
        "priority": TaskPriority.MEDIUM,
        "max_concurrent": 1,
        "timeout_seconds": 3600,
        "retry_policy": RetryPolicyCreate(),
        "alert_configs": [],
        "status": TaskStatus.ENABLED,
        "account_alias": "prod",
    }
    defaults.update(overrides)
    return ScheduledTaskCreate(**defaults)


class TestTaskSchedulerInit:
    def test_init_creates_db(self, svc, tmp_path):
        db_path = tmp_path / "scheduler.db"
        assert db_path.exists()

    def test_init_creates_tables(self, svc, tmp_path):
        db_path = tmp_path / "scheduler.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
        assert "scheduled_tasks" in tables
        assert "task_executions" in tables


class TestTaskSchedulerStartStop:
    def test_start(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        svc._scheduler = mock_scheduler
        svc.start()
        mock_scheduler.start.assert_called_once()

    def test_start_idempotent(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        svc._scheduler = mock_scheduler
        svc.start()
        mock_scheduler.start.assert_not_called()

    def test_shutdown(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        svc._scheduler = mock_scheduler
        svc.shutdown()
        mock_scheduler.shutdown.assert_called_once()

    def test_shutdown_not_running(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        svc._scheduler = mock_scheduler
        svc.shutdown()
        mock_scheduler.shutdown.assert_not_called()


class TestTaskCRUD:
    def test_create_task(self, svc):
        data = _make_task_create()
        task = svc.create_task(data)
        assert task.name == "test-task"
        assert task.cron_expression == "*/5 * * * *"
        assert task.status == TaskStatus.ENABLED
        assert task.id is not None

    def test_list_tasks_empty(self, svc):
        tasks = svc.list_tasks()
        assert tasks == []

    def test_list_tasks(self, svc):
        data = _make_task_create()
        svc.create_task(data)
        tasks = svc.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "test-task"

    def test_get_task(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        fetched = svc.get_task(created.id)
        assert fetched.name == "test-task"

    def test_get_task_not_found(self, svc):
        with pytest.raises(ValueError, match="not found"):
            svc.get_task("nonexistent-id")

    def test_delete_task(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        svc.delete_task(created.id)
        with pytest.raises(ValueError):
            svc.get_task(created.id)

    def test_create_task_disabled(self, svc):
        data = _make_task_create(status=TaskStatus.DISABLED)
        task = svc.create_task(data)
        assert task.status == TaskStatus.DISABLED


class TestTaskUpdate:
    def test_update_task_name(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(id=created.id, name="updated-name")
        updated = svc.update_task(created.id, update)
        assert updated.name == "updated-name"

    def test_update_task_no_changes(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(id=created.id)
        updated = svc.update_task(created.id, update)
        assert updated.name == created.name

    def test_update_task_cron_reschedules(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        svc._scheduler = mock_scheduler
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(id=created.id, cron_expression="0 * * * *")
        updated = svc.update_task(created.id, update)
        assert updated.cron_expression == "0 * * * *"

    def test_update_task_status_disabled(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        svc._scheduler = mock_scheduler
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(id=created.id, status=TaskStatus.DISABLED)
        updated = svc.update_task(created.id, update)
        assert updated.status == TaskStatus.DISABLED

    def test_update_task_retry_policy(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(
            id=created.id,
            retry_policy=RetryPolicyCreate(max_retries=5, strategy=RetryStrategy.EXPONENTIAL),
        )
        updated = svc.update_task(created.id, update)
        assert updated.retry_policy.max_retries == 5

    def test_update_task_alert_configs(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(
            id=created.id,
            alert_configs=[AlertConfigCreate(channel=AlertChannel.WEBHOOK, recipients=["http://hook"])],
        )
        updated = svc.update_task(created.id, update)
        assert len(updated.alert_configs) == 1

    def test_update_task_priority(self, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        update = ScheduledTaskUpdate(id=created.id, priority=TaskPriority.HIGH)
        updated = svc.update_task(created.id, update)
        assert updated.priority == TaskPriority.HIGH


class TestTaskToggle:
    def test_toggle_enable(self, svc):
        data = _make_task_create(status=TaskStatus.DISABLED)
        created = svc.create_task(data)
        toggled = svc.toggle_task(created.id, enabled=True)
        assert toggled.status == TaskStatus.ENABLED

    def test_toggle_disable(self, svc):
        data = _make_task_create(status=TaskStatus.ENABLED)
        created = svc.create_task(data)
        toggled = svc.toggle_task(created.id, enabled=False)
        assert toggled.status == TaskStatus.DISABLED

    def test_toggle_same_status(self, svc):
        data = _make_task_create(status=TaskStatus.ENABLED)
        created = svc.create_task(data)
        toggled = svc.toggle_task(created.id, enabled=True)
        assert toggled.status == TaskStatus.ENABLED


class TestRunTaskNow:
    @patch("app.services.task_scheduler_service.asyncio")
    def test_run_task_now(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        execution = svc.run_task_now(created.id)
        assert execution.task_id == created.id
        assert execution.status == ExecutionStatus.PENDING
        assert execution.trigger_mode == TriggerMode.MANUAL

    def test_run_task_not_found(self, svc):
        with pytest.raises(ValueError):
            svc.run_task_now("nonexistent")


class TestExecutions:
    def test_list_executions_empty(self, svc):
        executions = svc.list_executions()
        assert executions == []

    @patch("app.services.task_scheduler_service.asyncio")
    def test_list_executions_for_task(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        svc.run_task_now(created.id)
        executions = svc.list_executions(task_id=created.id)
        assert len(executions) == 1

    @patch("app.services.task_scheduler_service.asyncio")
    def test_list_executions_with_status_filter(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        svc.run_task_now(created.id)
        executions = svc.list_executions(status="pending")
        assert len(executions) == 1

    @patch("app.services.task_scheduler_service.asyncio")
    def test_get_execution(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        exec_obj = svc.run_task_now(created.id)
        fetched = svc.get_execution(exec_obj.id)
        assert fetched.task_id == created.id

    def test_get_execution_not_found(self, svc):
        with pytest.raises(ValueError, match="not found"):
            svc.get_execution("nonexistent")

    @patch("app.services.task_scheduler_service.asyncio")
    def test_list_executions_with_limit_offset(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        svc.run_task_now(created.id)
        executions = svc.list_executions(limit=10, offset=0)
        assert len(executions) == 1


class TestRetryExecution:
    @patch("app.services.task_scheduler_service.asyncio")
    def test_retry_execution(self, mock_asyncio, svc):
        data = _make_task_create()
        created = svc.create_task(data)
        exec_obj = svc.run_task_now(created.id)
        new_exec = svc.retry_execution(exec_obj.id)
        assert new_exec.retry_count == exec_obj.retry_count + 1

    def test_retry_execution_not_found(self, svc):
        with pytest.raises(ValueError):
            svc.retry_execution("nonexistent")


class TestComputeNextRun:
    def test_compute_next_run_valid(self, svc):
        result = svc._compute_next_run("*/5 * * * *", "Asia/Shanghai")
        assert result is not None

    def test_compute_next_run_invalid(self, svc):
        result = svc._compute_next_run("invalid", "Asia/Shanghai")
        assert result is None


class TestComputeRetryDelay:
    def test_fixed_delay(self, svc):
        policy = RetryPolicy(strategy=RetryStrategy.FIXED, interval_seconds=30)
        delay = svc._compute_retry_delay(policy, 0)
        assert delay == 30.0

    def test_exponential_delay(self, svc):
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            interval_seconds=10,
            max_interval_seconds=100,
        )
        delay0 = svc._compute_retry_delay(policy, 0)
        assert delay0 == 10.0
        delay1 = svc._compute_retry_delay(policy, 1)
        assert delay1 == 20.0
        delay2 = svc._compute_retry_delay(policy, 2)
        assert delay2 == 40.0

    def test_exponential_delay_capped(self, svc):
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            interval_seconds=10,
            max_interval_seconds=50,
        )
        delay = svc._compute_retry_delay(policy, 5)
        assert delay == 50.0

    def test_exponential_delay_no_cap(self, svc):
        policy = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            interval_seconds=10,
            max_interval_seconds=None,
        )
        delay = svc._compute_retry_delay(policy, 3)
        assert delay == 80.0

    def test_default_delay(self, svc):
        policy = RetryPolicy(strategy=RetryStrategy.FIXED, interval_seconds=60)
        delay = svc._compute_retry_delay(policy, 0)
        assert delay == 60.0


class TestExecShell:
    @patch("app.services.task_scheduler_service.ssh_account_service")
    def test_exec_shell_success(self, mock_ssh_svc, svc):
        account = MagicMock()
        mock_ssh_svc.get_account.return_value = account
        conn = MagicMock()
        conn.manager.exec_command.return_value = (0, "output", "err")
        mock_ssh_svc.pool.get_connection.return_value = conn
        code, stdout, stderr = svc._exec_shell("prod", "echo hello", timeout=30)
        assert code == 0
        assert stdout == "output"
        mock_ssh_svc.pool.release_connection.assert_called_once_with(conn)

    @patch("app.services.task_scheduler_service.ssh_account_service")
    def test_exec_shell_bytes_output(self, mock_ssh_svc, svc):
        account = MagicMock()
        mock_ssh_svc.get_account.return_value = account
        conn = MagicMock()
        conn.manager.exec_command.return_value = (0, b"bytes output", b"bytes err")
        mock_ssh_svc.pool.get_connection.return_value = conn
        code, stdout, stderr = svc._exec_shell("prod", "echo hello")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    @patch("app.services.task_scheduler_service.ssh_account_service")
    def test_exec_shell_account_not_found(self, mock_ssh_svc, svc):
        mock_ssh_svc.get_account.return_value = None
        with pytest.raises(ValueError, match="not found"):
            svc._exec_shell("nonexist", "echo hello")


class TestExecHttp:
    @pytest.mark.asyncio
    async def test_exec_http_success(self, svc):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="ok")
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await svc._exec_http("http://example.com")
        assert result["status_code"] == 200
        assert result["body"] == "ok"


class TestExecuteTask:
    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, svc):
        await svc._execute_task("nonexistent-id")

    @pytest.mark.asyncio
    async def test_execute_task_shell_success(self, svc):
        data = _make_task_create(retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        loop = asyncio.get_running_loop()
        with patch.object(loop, "run_in_executor", new_callable=AsyncMock, return_value=(0, "ok", "")):
            await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_task_shell_failure(self, svc):
        data = _make_task_create(retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        loop = asyncio.get_running_loop()
        with patch.object(loop, "run_in_executor", new_callable=AsyncMock, return_value=(1, "", "error")):
            with patch.object(svc, "_send_alerts", new_callable=AsyncMock):
                await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_task_max_concurrent(self, svc):
        data = _make_task_create(max_concurrent=1)
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.RUNNING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("exec-running", created.id, created.name, ExecutionStatus.RUNNING.value,
                 TriggerMode.AUTO.value, 0, now.isoformat(), created.account_alias),
            )

        await svc._execute_task(created.id, execution_id)
        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.FAILED
        assert "Max concurrent" in (execution.error or "")

    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, svc):
        data = _make_task_create(task_type="http", command="http://slow.example.com", timeout_seconds=1, retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        with patch.object(svc, "_exec_http", new_callable=AsyncMock, side_effect=asyncio.TimeoutError()):
            with patch.object(svc, "_send_alerts", new_callable=AsyncMock):
                await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_execute_task_no_account_alias(self, svc):
        data = _make_task_create(account_alias=None, retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), None),
            )

        with patch.object(svc, "_send_alerts", new_callable=AsyncMock):
            await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_task_auto_creates_execution(self, svc):
        data = _make_task_create(retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        loop = asyncio.get_running_loop()
        with patch.object(loop, "run_in_executor", new_callable=AsyncMock, return_value=(0, "ok", "")):
            await svc._execute_task(created.id)
        executions = svc.list_executions(task_id=created.id)
        assert len(executions) >= 1

    @pytest.mark.asyncio
    async def test_execute_task_http_success(self, svc):
        data = _make_task_create(task_type="http", command="http://example.com")
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        mock_http_result = {"status_code": 200, "body": "ok", "headers": {}}
        with patch.object(svc, "_exec_http", new_callable=AsyncMock, return_value=mock_http_result):
            await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_task_http_failure(self, svc):
        data = _make_task_create(task_type="http", command="http://example.com", retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        mock_http_result = {"status_code": 500, "body": "error", "headers": {}}
        with patch.object(svc, "_exec_http", new_callable=AsyncMock, return_value=mock_http_result):
            with patch.object(svc, "_send_alerts", new_callable=AsyncMock):
                await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_task_workflow(self, svc):
        data = _make_task_create(workflow_id="wf-123", task_type="shell", retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        mock_wf_service = MagicMock()
        mock_wf_service.execute_workflow = AsyncMock(return_value={"exit_code": 0, "result": "ok"})
        with patch.dict("sys.modules", {"app.services.workflow_service": MagicMock(workflow_service=mock_wf_service)}):
            with patch("asyncio.wait_for", new_callable=AsyncMock, return_value={"exit_code": 0, "result": "ok"}):
                await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_task_workflow_failure(self, svc):
        data = _make_task_create(workflow_id="wf-123", task_type="shell", retry_policy=RetryPolicyCreate(max_retries=0))
        created = svc.create_task(data)
        execution_id = str(uuid.uuid4())
        now = datetime.now()
        with svc._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                    retry_count, started_at, account_alias)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (execution_id, created.id, created.name, ExecutionStatus.PENDING.value,
                 TriggerMode.MANUAL.value, 0, now.isoformat(), created.account_alias),
            )

        with patch("asyncio.wait_for", new_callable=AsyncMock, return_value={"exit_code": 1, "error": "fail"}):
            with patch.object(svc, "_send_alerts", new_callable=AsyncMock):
                await svc._execute_task(created.id, execution_id)

        execution = svc.get_execution(execution_id)
        assert execution.status == ExecutionStatus.FAILED


class TestSendAlerts:
    @pytest.mark.asyncio
    async def test_send_webhook_alert(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.WEBHOOK, recipients=["http://hook.example.com"])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            error="something failed", started_at=datetime.now(), completed_at=datetime.now(),
        )
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await svc._send_alerts(task, execution)
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_alert(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.EMAIL, recipients=["admin@example.com"])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            error="fail", started_at=datetime.now(), completed_at=datetime.now(),
        )
        await svc._send_alerts(task, execution)

    @pytest.mark.asyncio
    async def test_send_dingtalk_alert(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.DINGTALK, recipients=["http://dingtalk.webhook"])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            error="fail", started_at=datetime.now(), completed_at=datetime.now(),
        )
        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await svc._send_alerts(task, execution)
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_wecom_alert(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.WECOM, recipients=["http://wecom.webhook"])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            error="fail", started_at=datetime.now(), completed_at=datetime.now(),
        )
        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await svc._send_alerts(task, execution)
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_disabled(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.WEBHOOK, recipients=["http://hook"], enabled=False)],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            started_at=datetime.now(),
        )
        await svc._send_alerts(task, execution)

    @pytest.mark.asyncio
    async def test_send_alert_no_recipients(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.WEBHOOK, recipients=[])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            started_at=datetime.now(),
        )
        await svc._send_alerts(task, execution)

    @pytest.mark.asyncio
    async def test_send_alert_exception(self, svc):
        task = ScheduledTask(
            id="t1", name="test", cron_expression="* * * * *",
            alert_configs=[AlertConfig(channel=AlertChannel.WEBHOOK, recipients=["http://hook"])],
        )
        execution = TaskExecution(
            id="e1", task_id="t1", task_name="test",
            status=ExecutionStatus.FAILED, trigger_mode=TriggerMode.AUTO,
            error="fail", started_at=datetime.now(), completed_at=datetime.now(),
        )
        mock_session = MagicMock()
        mock_session.__aenter__ = MagicMock(side_effect=Exception("network error"))
        mock_session.__aexit__ = MagicMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await svc._send_alerts(task, execution)


class TestRegisterTask:
    def test_register_task_scheduler_not_running(self, svc):
        task = ScheduledTask(id="t1", name="test", cron_expression="* * * * *")
        svc._register_task(task)

    def test_register_task_scheduler_running(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        svc._scheduler = mock_scheduler
        task = ScheduledTask(id="t1", name="test", cron_expression="* * * * *")
        svc._register_task(task)
        mock_scheduler.add_job.assert_called_once()

    def test_register_task_runtime_error(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler.add_job.side_effect = RuntimeError("event loop")
        svc._scheduler = mock_scheduler
        task = ScheduledTask(id="t1", name="test", cron_expression="* * * * *")
        svc._register_task(task)

    def test_register_task_general_exception(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler.add_job.side_effect = Exception("bad cron")
        svc._scheduler = mock_scheduler
        task = ScheduledTask(id="t1", name="test", cron_expression="bad")
        svc._register_task(task)


class TestUnregisterTask:
    def test_unregister_task_success(self, svc):
        svc._unregister_task("some-id")

    def test_unregister_task_exception(self, svc):
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job.side_effect = Exception("not found")
        svc._scheduler = mock_scheduler
        svc._unregister_task("some-id")


class TestRowToTask:
    def test_row_to_task_full(self, svc):
        now = datetime.now().isoformat()
        row = {
            "id": "t1",
            "name": "test",
            "description": "desc",
            "workflow_id": None,
            "task_type": "shell",
            "command": "echo hello",
            "cron_expression": "*/5 * * * *",
            "timezone": "Asia/Shanghai",
            "priority": "medium",
            "max_concurrent": 1,
            "timeout_seconds": 3600,
            "retry_policy": json.dumps({"max_retries": 3, "strategy": "fixed", "interval_seconds": 60, "max_interval_seconds": None}),
            "alert_configs": json.dumps([{"channel": "webhook", "recipients": ["http://hook"], "template": None, "enabled": True}]),
            "status": "enabled",
            "account_alias": "prod",
            "last_run_at": now,
            "last_run_status": "success",
            "next_run_at": now,
            "created_at": now,
            "updated_at": now,
        }
        task = svc._row_to_task(row)
        assert task.id == "t1"
        assert task.name == "test"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.ENABLED
        assert len(task.alert_configs) == 1
        assert task.retry_policy.max_retries == 3

    def test_row_to_task_minimal(self, svc):
        row = {
            "id": "t2",
            "name": "minimal",
            "cron_expression": "* * * * *",
        }
        task = svc._row_to_task(row)
        assert task.id == "t2"
        assert task.retry_policy.max_retries == 3
        assert task.alert_configs == []

    def test_row_to_task_no_retry_policy(self, svc):
        row = {
            "id": "t3",
            "name": "no-retry",
            "cron_expression": "* * * * *",
            "retry_policy": None,
        }
        task = svc._row_to_task(row)
        assert task.retry_policy.max_retries == 3

    def test_row_to_task_no_alert_configs(self, svc):
        row = {
            "id": "t4",
            "name": "no-alerts",
            "cron_expression": "* * * * *",
            "alert_configs": None,
        }
        task = svc._row_to_task(row)
        assert task.alert_configs == []


class TestRowToExecution:
    def test_row_to_execution_full(self, svc):
        now = datetime.now().isoformat()
        row = {
            "id": "e1",
            "task_id": "t1",
            "task_name": "test",
            "status": "success",
            "trigger_mode": "manual",
            "retry_count": 0,
            "exit_code": 0,
            "output": "hello",
            "error": None,
            "started_at": now,
            "completed_at": now,
            "duration_seconds": 1.5,
            "account_alias": "prod",
        }
        execution = svc._row_to_execution(row)
        assert execution.id == "e1"
        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.duration_seconds == 1.5

    def test_row_to_execution_minimal(self, svc):
        row = {
            "id": "e2",
            "task_id": "t1",
            "task_name": "test",
            "status": "pending",
            "trigger_mode": "auto",
        }
        execution = svc._row_to_execution(row)
        assert execution.id == "e2"
        assert execution.retry_count == 0
        assert execution.exit_code is None
