import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, PropertyMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_task_dict(task_id="task-1", name="test-task"):
    return {
        "id": task_id,
        "name": name,
        "description": "desc",
        "workflow_id": None,
        "task_type": "shell",
        "command": "echo hello",
        "cron_expression": "*/5 * * * *",
        "timezone": "Asia/Shanghai",
        "priority": "medium",
        "max_concurrent": 1,
        "timeout_seconds": 3600,
        "retry_policy": {
            "max_retries": 3,
            "strategy": "fixed",
            "interval_seconds": 60,
            "max_interval_seconds": None,
        },
        "alert_configs": [],
        "status": "enabled",
        "account_alias": None,
        "last_run_at": None,
        "last_run_status": None,
        "next_run_at": "2025-01-01T00:05:00",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


def _make_execution_dict(exec_id="exec-1", task_id="task-1"):
    return {
        "id": exec_id,
        "task_id": task_id,
        "task_name": "test-task",
        "status": "pending",
        "trigger_mode": "manual",
        "retry_count": 0,
        "exit_code": None,
        "output": None,
        "error": None,
        "started_at": "2025-01-01T00:00:00",
        "completed_at": None,
        "duration_seconds": None,
        "account_alias": None,
    }


class TestSchedulerListTasks:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_tasks_success(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = _make_task_dict()
        mock_service.list_tasks.return_value = [mock_task]

        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "test-task"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_tasks_empty(self, mock_service, client):
        mock_service.list_tasks.return_value = []

        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_tasks_internal_error(self, mock_service, client):
        mock_service.list_tasks.side_effect = Exception("db error")

        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 500


class TestSchedulerGetTask:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_task_success(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = _make_task_dict()
        mock_service.get_task.return_value = mock_task

        response = client.get("/api/scheduler/tasks/task-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "task-1"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_task_not_found(self, mock_service, client):
        mock_service.get_task.side_effect = ValueError("Task 'task-1' not found")

        response = client.get("/api/scheduler/tasks/task-1")
        assert response.status_code == 400


class TestSchedulerCreateTask:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_create_task_success(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = _make_task_dict()
        mock_service.create_task.return_value = mock_task

        response = client.post("/api/scheduler/tasks", json={
            "name": "test-task",
            "cron_expression": "*/5 * * * *",
            "task_type": "shell",
            "command": "echo hello",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-task"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_create_task_value_error(self, mock_service, client):
        mock_service.create_task.side_effect = ValueError("invalid cron")

        response = client.post("/api/scheduler/tasks", json={
            "name": "test-task",
            "cron_expression": "invalid",
        })
        assert response.status_code == 400

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_create_task_internal_error(self, mock_service, client):
        mock_service.create_task.side_effect = Exception("db error")

        response = client.post("/api/scheduler/tasks", json={
            "name": "test-task",
            "cron_expression": "*/5 * * * *",
        })
        assert response.status_code == 500


class TestSchedulerUpdateTask:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_update_task_success(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = _make_task_dict(name="updated")
        mock_service.update_task.return_value = mock_task

        response = client.put("/api/scheduler/tasks/task-1", json={
            "id": "task-1",
            "name": "updated",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_update_task_not_found(self, mock_service, client):
        mock_service.update_task.side_effect = ValueError("not found")

        response = client.put("/api/scheduler/tasks/task-1", json={
            "id": "task-1",
            "name": "updated",
        })
        assert response.status_code == 400


class TestSchedulerDeleteTask:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_delete_task_success(self, mock_service, client):
        mock_service.delete_task.return_value = None

        response = client.delete("/api/scheduler/tasks/task-1")
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_delete_task_value_error(self, mock_service, client):
        mock_service.delete_task.side_effect = ValueError("not found")

        response = client.delete("/api/scheduler/tasks/task-1")
        assert response.status_code == 400


class TestSchedulerToggleTask:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_toggle_task_enable(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = _make_task_dict()
        mock_service.toggle_task.return_value = mock_task

        response = client.post("/api/scheduler/tasks/task-1/toggle", json={"enabled": True})
        assert response.status_code == 200

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_toggle_task_disable(self, mock_service, client):
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {**_make_task_dict(), "status": "disabled"}
        mock_service.toggle_task.return_value = mock_task

        response = client.post("/api/scheduler/tasks/task-1/toggle", json={"enabled": False})
        assert response.status_code == 200

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_toggle_task_not_found(self, mock_service, client):
        mock_service.toggle_task.side_effect = ValueError("not found")

        response = client.post("/api/scheduler/tasks/task-1/toggle", json={"enabled": True})
        assert response.status_code == 400


class TestSchedulerRunTaskNow:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_run_task_now_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.run_task_now.return_value = mock_exec

        response = client.post("/api/scheduler/tasks/task-1/run")
        assert response.status_code == 200
        data = response.json()
        assert data["trigger_mode"] == "manual"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_run_task_now_not_found(self, mock_service, client):
        mock_service.run_task_now.side_effect = ValueError("not found")

        response = client.post("/api/scheduler/tasks/task-1/run")
        assert response.status_code == 400


class TestSchedulerExecutions:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_task_executions_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.list_executions.return_value = [mock_exec]

        response = client.get("/api/scheduler/tasks/task-1/executions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_all_executions_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.list_executions.return_value = [mock_exec]

        response = client.get("/api/scheduler/executions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_executions_with_filters(self, mock_service, client):
        mock_service.list_executions.return_value = []

        response = client.get("/api/scheduler/executions?task_id=task-1&status=success&limit=10&offset=0")
        assert response.status_code == 200
        mock_service.list_executions.assert_called_once_with(
            task_id="task-1", status="success", limit=10, offset=0
        )

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_execution_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.get_execution.return_value = mock_exec

        response = client.get("/api/scheduler/executions/exec-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "exec-1"

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_execution_not_found(self, mock_service, client):
        mock_service.get_execution.side_effect = ValueError("not found")

        response = client.get("/api/scheduler/executions/nonexistent")
        assert response.status_code == 400

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_retry_execution_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = {**_make_execution_dict(), "retry_count": 1}
        mock_service.retry_execution.return_value = mock_exec

        response = client.post("/api/scheduler/executions/exec-1/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["retry_count"] == 1

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_retry_execution_not_found(self, mock_service, client):
        mock_service.retry_execution.side_effect = ValueError("not found")

        response = client.post("/api/scheduler/executions/nonexistent/retry")
        assert response.status_code == 400


class TestSchedulerStatus:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_scheduler_status(self, mock_service, client):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock()]
        type(mock_service)._scheduler = PropertyMock(return_value=mock_scheduler)

        response = client.get("/api/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["job_count"] == 2

    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_scheduler_status_not_running(self, mock_service, client):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler.get_jobs.return_value = []
        type(mock_service)._scheduler = PropertyMock(return_value=mock_scheduler)

        response = client.get("/api/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert data["job_count"] == 0
