from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.task_scheduler import (
    AlertChannel,
    ExecutionStatus,
    RetryPolicy,
    RetryStrategy,
    ScheduledTask,
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    TaskExecution,
    TaskPriority,
    TaskStatus,
    TriggerMode,
)
from app.services.ssh_account_service import ssh_account_service

_PERSIST_DIR = Path.home() / ".opsv-kits"
_DB_PATH = _PERSIST_DIR / "scheduler.db"

_logger = logging.getLogger(__name__)


class TaskSchedulerService:
    def __init__(self):
        self._lock = threading.RLock()
        self._scheduler = AsyncIOScheduler()
        self._init_db()
        self._load_enabled_tasks()

    def _init_db(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    workflow_id TEXT,
                    task_type TEXT DEFAULT 'shell',
                    command TEXT,
                    cron_expression TEXT NOT NULL,
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    priority TEXT DEFAULT 'medium',
                    max_concurrent INTEGER DEFAULT 1,
                    timeout_seconds INTEGER DEFAULT 3600,
                    retry_policy TEXT,
                    alert_configs TEXT,
                    status TEXT DEFAULT 'enabled',
                    account_alias TEXT,
                    last_run_at TEXT,
                    last_run_status TEXT,
                    next_run_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS task_executions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    trigger_mode TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    exit_code INTEGER,
                    output TEXT,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    account_alias TEXT,
                    FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id)
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(_DB_PATH))

    def _load_enabled_tasks(self) -> None:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM scheduled_tasks WHERE status = 'enabled'")
                rows = cursor.fetchall()
                for row in rows:
                    task = self._row_to_task(dict(zip([c[0] for c in cursor.description], row)))
                    self._register_task(task)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown()

    def list_tasks(self) -> list[ScheduledTask]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM scheduled_tasks ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_task(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_task(self, task_id: str) -> ScheduledTask:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if row is None:
                    raise ValueError(f"Task '{task_id}' not found")
                return self._row_to_task(dict(zip([c[0] for c in cursor.description], row)))

    def create_task(self, data: ScheduledTaskCreate) -> ScheduledTask:
        with self._lock:
            task_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            retry_policy = data.retry_policy
            alert_configs = data.alert_configs
            next_run = self._compute_next_run(data.cron_expression, data.timezone)

            task = ScheduledTask(
                id=task_id,
                name=data.name,
                description=data.description,
                workflow_id=data.workflow_id,
                task_type=data.task_type,
                command=data.command,
                cron_expression=data.cron_expression,
                timezone=data.timezone,
                priority=data.priority,
                max_concurrent=data.max_concurrent,
                timeout_seconds=data.timeout_seconds,
                retry_policy=RetryPolicy(**retry_policy.model_dump()),
                alert_configs=[ac.model_dump() for ac in alert_configs],
                status=data.status,
                account_alias=data.account_alias,
                next_run_at=datetime.fromisoformat(next_run) if next_run else None,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO scheduled_tasks (id, name, description, workflow_id, task_type, command,
                        cron_expression, timezone, priority, max_concurrent, timeout_seconds,
                        retry_policy, alert_configs, status, account_alias, next_run_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id, task.name, task.description, task.workflow_id, task.task_type,
                        task.command, task.cron_expression, task.timezone, task.priority.value,
                        task.max_concurrent, task.timeout_seconds,
                        json.dumps(task.retry_policy.model_dump()),
                        json.dumps([ac.model_dump() for ac in task.alert_configs]) if task.alert_configs else "[]",
                        task.status.value, task.account_alias, next_run, now, now,
                    ),
                )

            if task.status == TaskStatus.ENABLED:
                self._register_task(task)

            return task

    def update_task(self, task_id: str, data: ScheduledTaskUpdate) -> ScheduledTask:
        with self._lock:
            existing = self.get_task(task_id)

            updates = data.model_dump(exclude_unset=True)
            if not updates:
                return existing

            needs_reschedule = (
                "cron_expression" in updates
                or "timezone" in updates
                or "status" in updates
            )

            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "retry_policy" and value is not None:
                    value = json.dumps(value) if isinstance(value, dict) else json.dumps(RetryPolicy(**value).model_dump())
                elif key == "alert_configs" and value is not None:
                    value = json.dumps(value)
                elif key == "priority" and value is not None:
                    value = value.value if hasattr(value, "value") else value
                elif key == "status" and value is not None:
                    value = value.value if hasattr(value, "value") else value
                set_clauses.append(f"{key} = ?")
                params.append(value)

            if "cron_expression" in updates or "timezone" in updates:
                cron_expr = updates.get("cron_expression", existing.cron_expression)
                tz = updates.get("timezone", existing.timezone)
                next_run = self._compute_next_run(cron_expr, tz)
                set_clauses.append("next_run_at = ?")
                params.append(next_run)

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(task_id)

            with self._conn() as conn:
                conn.execute(
                    f"UPDATE scheduled_tasks SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )

            updated = self.get_task(task_id)

            if needs_reschedule:
                self._unregister_task(task_id)
                if updated.status == TaskStatus.ENABLED:
                    self._register_task(updated)

            return updated

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            self._unregister_task(task_id)
            with self._conn() as conn:
                conn.execute("DELETE FROM task_executions WHERE task_id = ?", (task_id,))
                conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))

    def toggle_task(self, task_id: str, enabled: bool) -> ScheduledTask:
        with self._lock:
            task = self.get_task(task_id)
            new_status = TaskStatus.ENABLED if enabled else TaskStatus.DISABLED
            if task.status == new_status:
                return task

            now = datetime.now().isoformat()
            with self._conn() as conn:
                conn.execute(
                    "UPDATE scheduled_tasks SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status.value, now, task_id),
                )

            self._unregister_task(task_id)
            if new_status == TaskStatus.ENABLED:
                updated = self.get_task(task_id)
                self._register_task(updated)

            return self.get_task(task_id)

    def run_task_now(self, task_id: str) -> TaskExecution:
        with self._lock:
            task = self.get_task(task_id)

            execution_id = str(uuid.uuid4())
            now = datetime.now()
            execution = TaskExecution(
                id=execution_id,
                task_id=task.id,
                task_name=task.name,
                status=ExecutionStatus.PENDING,
                trigger_mode=TriggerMode.MANUAL,
                retry_count=0,
                started_at=now,
                account_alias=task.account_alias,
            )

            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                        retry_count, started_at, account_alias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        execution.id, execution.task_id, execution.task_name,
                        execution.status.value, execution.trigger_mode.value,
                        execution.retry_count, now.isoformat(), execution.account_alias,
                    ),
                )

            asyncio.ensure_future(self._execute_task(task_id, execution_id))
            return execution

    def list_executions(
        self,
        task_id: str = None,
        status: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskExecution]:
        with self._lock:
            with self._conn() as conn:
                query = "SELECT * FROM task_executions WHERE 1=1"
                params = []
                if task_id is not None:
                    query += " AND task_id = ?"
                    params.append(task_id)
                if status is not None:
                    query += " AND status = ?"
                    params.append(status)
                query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [
                    self._row_to_execution(dict(zip([c[0] for c in cursor.description], row)))
                    for row in rows
                ]

    def get_execution(self, execution_id: str) -> TaskExecution:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM task_executions WHERE id = ?", (execution_id,))
                row = cursor.fetchone()
                if row is None:
                    raise ValueError(f"Execution '{execution_id}' not found")
                return self._row_to_execution(dict(zip([c[0] for c in cursor.description], row)))

    def retry_execution(self, execution_id: str) -> TaskExecution:
        with self._lock:
            original = self.get_execution(execution_id)
            task = self.get_task(original.task_id)

            new_execution_id = str(uuid.uuid4())
            now = datetime.now()
            new_execution = TaskExecution(
                id=new_execution_id,
                task_id=task.id,
                task_name=task.name,
                status=ExecutionStatus.PENDING,
                trigger_mode=TriggerMode.MANUAL,
                retry_count=original.retry_count + 1,
                started_at=now,
                account_alias=task.account_alias,
            )

            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                        retry_count, started_at, account_alias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_execution.id, new_execution.task_id, new_execution.task_name,
                        new_execution.status.value, new_execution.trigger_mode.value,
                        new_execution.retry_count, now.isoformat(), new_execution.account_alias,
                    ),
                )

            asyncio.ensure_future(self._execute_task(task.id, new_execution_id))
            return new_execution

    def _register_task(self, task: ScheduledTask) -> None:
        try:
            if not self._scheduler.running:
                return
            parts = task.cron_expression.split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
                timezone=task.timezone,
            )
            self._scheduler.add_job(
                self._execute_task,
                trigger=trigger,
                id=task.id,
                args=[task.id],
                replace_existing=True,
                misfire_grace_time=60,
            )
        except RuntimeError:
            pass
        except Exception as e:
            _logger.error("Failed to register task %s: %s", task.id, e)

    def _unregister_task(self, task_id: str) -> None:
        try:
            self._scheduler.remove_job(task_id)
        except Exception:
            pass

    async def _execute_task(self, task_id: str, execution_id: str = None) -> None:
        try:
            task = self.get_task(task_id)
        except ValueError:
            _logger.error("Task %s not found during execution", task_id)
            return

        if execution_id is None:
            execution_id = str(uuid.uuid4())
            now = datetime.now()
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                            retry_count, started_at, account_alias)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            execution_id, task.id, task.name,
                            ExecutionStatus.RUNNING.value, TriggerMode.AUTO.value,
                            0, now.isoformat(), task.account_alias,
                        ),
                    )
        else:
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE task_executions SET status = ?, started_at = ? WHERE id = ?",
                        (ExecutionStatus.RUNNING.value, datetime.now().isoformat(), execution_id),
                    )

        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM task_executions WHERE task_id = ? AND status = ?",
                    (task_id, ExecutionStatus.RUNNING.value),
                )
                running_count = cursor.fetchone()[0]

        if running_count > task.max_concurrent:
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE task_executions SET status = ?, error = ?, completed_at = ? WHERE id = ?",
                        (
                            ExecutionStatus.FAILED.value,
                            "Max concurrent executions reached",
                            datetime.now().isoformat(),
                            execution_id,
                        ),
                    )
            return

        exit_code = None
        output = None
        error = None
        final_status = ExecutionStatus.SUCCESS

        try:
            if task.workflow_id:
                from app.services.workflow_service import workflow_service
                result = await asyncio.wait_for(
                    workflow_service.execute_workflow(task.workflow_id),
                    timeout=task.timeout_seconds,
                )
                exit_code = result.get("exit_code", 0)
                output = json.dumps(result) if isinstance(result, dict) else str(result)
                if exit_code and exit_code != 0:
                    final_status = ExecutionStatus.FAILED

            elif task.task_type == "shell":
                if not task.account_alias:
                    raise ValueError("Shell task requires account_alias")
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._exec_shell,
                    task.account_alias,
                    task.command,
                    task.timeout_seconds,
                )
                exit_code, output, error = result
                if exit_code != 0:
                    final_status = ExecutionStatus.FAILED

            elif task.task_type == "http":
                result = await asyncio.wait_for(
                    self._exec_http(task.command),
                    timeout=task.timeout_seconds,
                )
                exit_code = result.get("status_code", -1)
                output = json.dumps(result)
                if exit_code < 200 or exit_code >= 400:
                    final_status = ExecutionStatus.FAILED

        except asyncio.TimeoutError:
            final_status = ExecutionStatus.TIMEOUT
            error = f"Task timed out after {task.timeout_seconds} seconds"
        except Exception as e:
            final_status = ExecutionStatus.FAILED
            error = str(e)

        completed_at = datetime.now()
        execution = self.get_execution(execution_id)
        duration = (completed_at - execution.started_at).total_seconds()

        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE task_executions SET status = ?, exit_code = ?, output = ?, error = ?,
                        completed_at = ?, duration_seconds = ? WHERE id = ?
                    """,
                    (
                        final_status.value, exit_code, output, error,
                        completed_at.isoformat(), duration, execution_id,
                    ),
                )
                conn.execute(
                    "UPDATE scheduled_tasks SET last_run_at = ?, last_run_status = ? WHERE id = ?",
                    (completed_at.isoformat(), final_status.value, task_id),
                )

        if final_status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT):
            retry_policy = task.retry_policy
            if execution.retry_count < retry_policy.max_retries:
                delay = self._compute_retry_delay(retry_policy, execution.retry_count)
                await asyncio.sleep(delay)

                new_execution_id = str(uuid.uuid4())
                now = datetime.now()
                with self._lock:
                    with self._conn() as conn:
                        conn.execute(
                            """
                            INSERT INTO task_executions (id, task_id, task_name, status, trigger_mode,
                                retry_count, started_at, account_alias)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                new_execution_id, task.id, task.name,
                                ExecutionStatus.RETRYING.value, TriggerMode.AUTO.value,
                                execution.retry_count + 1, now.isoformat(), task.account_alias,
                            ),
                        )

                await self._execute_task(task_id, new_execution_id)
            else:
                await self._send_alerts(task, self.get_execution(execution_id))

    async def _send_alerts(self, task: ScheduledTask, execution: TaskExecution) -> None:
        for alert_config in task.alert_configs:
            if not alert_config.enabled:
                continue

            payload = {
                "task_id": task.id,
                "task_name": task.name,
                "execution_id": execution.id,
                "status": execution.status.value,
                "error": execution.error,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            }

            try:
                if alert_config.channel == AlertChannel.WEBHOOK:
                    webhook_url = alert_config.recipients[0] if alert_config.recipients else None
                    if webhook_url:
                        async with aiohttp.ClientSession() as session:
                            await session.post(webhook_url, json=payload)

                elif alert_config.channel == AlertChannel.EMAIL:
                    _logger.info(
                        "Email alert for task %s to %s (not implemented)",
                        task.name,
                        alert_config.recipients,
                    )

                elif alert_config.channel == AlertChannel.DINGTALK:
                    webhook_url = alert_config.recipients[0] if alert_config.recipients else None
                    if webhook_url:
                        dingtalk_payload = {
                            "msgtype": "markdown",
                            "markdown": {
                                "title": f"Task Failed: {task.name}",
                                "text": f"### Task Failed: {task.name}\n\n- Status: {execution.status.value}\n- Error: {execution.error or 'N/A'}\n- Time: {execution.completed_at.isoformat() if execution.completed_at else 'N/A'}",
                            },
                        }
                        async with aiohttp.ClientSession() as session:
                            await session.post(webhook_url, json=dingtalk_payload)

                elif alert_config.channel == AlertChannel.WECOM:
                    webhook_url = alert_config.recipients[0] if alert_config.recipients else None
                    if webhook_url:
                        wecom_payload = {
                            "msgtype": "markdown",
                            "markdown": {
                                "content": f"### Task Failed: {task.name}\n\n> Status: {execution.status.value}\n> Error: {execution.error or 'N/A'}\n> Time: {execution.completed_at.isoformat() if execution.completed_at else 'N/A'}",
                            },
                        }
                        async with aiohttp.ClientSession() as session:
                            await session.post(webhook_url, json=wecom_payload)

            except Exception as e:
                _logger.error("Failed to send %s alert for task %s: %s", alert_config.channel.value, task.name, e)

    def _compute_next_run(self, cron_expression: str, timezone: str) -> Optional[str]:
        try:
            parts = cron_expression.split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
                timezone=timezone,
            )
            next_time = trigger.get_next_fire_time(None, datetime.now())
            if next_time:
                return next_time.isoformat()
        except Exception as e:
            _logger.error("Failed to compute next run for '%s': %s", cron_expression, e)
        return None

    def _compute_retry_delay(self, retry_policy: RetryPolicy, retry_count: int) -> float:
        if retry_policy.strategy == RetryStrategy.FIXED:
            return float(retry_policy.interval_seconds)
        elif retry_policy.strategy == RetryStrategy.EXPONENTIAL:
            delay = retry_policy.interval_seconds * (2 ** retry_count)
            if retry_policy.max_interval_seconds:
                delay = min(delay, retry_policy.max_interval_seconds)
            return float(delay)
        return float(retry_policy.interval_seconds)

    def _exec_shell(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
        account = ssh_account_service.get_account(alias)
        if account is None:
            raise ValueError(f"SSH account '{alias}' not found")
        conn = ssh_account_service.pool.get_connection(account)
        try:
            code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return code, stdout.strip(), stderr.strip()
        finally:
            ssh_account_service.pool.release_connection(conn)

    async def _exec_http(self, url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                body = await response.text()
                return {
                    "status_code": response.status,
                    "body": body[:10000],
                    "headers": dict(response.headers),
                }

    def _row_to_task(self, row: dict) -> ScheduledTask:
        retry_policy_raw = row.get("retry_policy")
        retry_policy = RetryPolicy(**json.loads(retry_policy_raw)) if retry_policy_raw else RetryPolicy()

        alert_configs_raw = row.get("alert_configs")
        from app.models.task_scheduler import AlertConfig
        alert_configs = [AlertConfig(**ac) for ac in json.loads(alert_configs_raw)] if alert_configs_raw else []

        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            workflow_id=row.get("workflow_id"),
            task_type=row.get("task_type", "shell"),
            command=row.get("command"),
            cron_expression=row["cron_expression"],
            timezone=row.get("timezone", "Asia/Shanghai"),
            priority=TaskPriority(row.get("priority", "medium")),
            max_concurrent=row.get("max_concurrent", 1),
            timeout_seconds=row.get("timeout_seconds", 3600),
            retry_policy=retry_policy,
            alert_configs=alert_configs,
            status=TaskStatus(row.get("status", "enabled")),
            account_alias=row.get("account_alias"),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row.get("last_run_at") else None,
            last_run_status=ExecutionStatus(row["last_run_status"]) if row.get("last_run_status") else None,
            next_run_at=datetime.fromisoformat(row["next_run_at"]) if row.get("next_run_at") else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )

    def _row_to_execution(self, row: dict) -> TaskExecution:
        return TaskExecution(
            id=row["id"],
            task_id=row["task_id"],
            task_name=row["task_name"],
            status=ExecutionStatus(row["status"]),
            trigger_mode=TriggerMode(row["trigger_mode"]),
            retry_count=row.get("retry_count", 0),
            exit_code=row.get("exit_code"),
            output=row.get("output"),
            error=row.get("error"),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            duration_seconds=row.get("duration_seconds"),
            account_alias=row.get("account_alias"),
        )


task_scheduler_service = TaskSchedulerService()
