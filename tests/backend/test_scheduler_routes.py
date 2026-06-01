from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

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


class TestListTasksValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_tasks_value_error(self, mock_service, client):
        mock_service.list_tasks.side_effect = ValueError("invalid filter")
        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 400


class TestGetTaskInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_task_internal_error(self, mock_service, client):
        mock_service.get_task.side_effect = Exception("db error")
        response = client.get("/api/scheduler/tasks/task-1")
        assert response.status_code == 500


class TestCreateTaskInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_create_task_internal_error(self, mock_service, client):
        mock_service.create_task.side_effect = Exception("db error")
        response = client.post("/api/scheduler/tasks", json={
            "name": "test-task",
            "cron_expression": "*/5 * * * *",
        })
        assert response.status_code == 500


class TestUpdateTaskInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_update_task_internal_error(self, mock_service, client):
        mock_service.update_task.side_effect = Exception("db error")
        response = client.put("/api/scheduler/tasks/task-1", json={
            "id": "task-1",
            "name": "updated",
        })
        assert response.status_code == 500


class TestDeleteTaskInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_delete_task_internal_error(self, mock_service, client):
        mock_service.delete_task.side_effect = Exception("db error")
        response = client.delete("/api/scheduler/tasks/task-1")
        assert response.status_code == 500


class TestToggleTaskInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_toggle_task_internal_error(self, mock_service, client):
        mock_service.toggle_task.side_effect = Exception("db error")
        response = client.post("/api/scheduler/tasks/task-1/toggle", json={"enabled": True})
        assert response.status_code == 500


class TestRunTaskNowInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_run_task_now_internal_error(self, mock_service, client):
        mock_service.run_task_now.side_effect = Exception("db error")
        response = client.post("/api/scheduler/tasks/task-1/run")
        assert response.status_code == 500


class TestListTaskExecutionsValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_task_executions_value_error(self, mock_service, client):
        mock_service.list_executions.side_effect = ValueError("invalid task")
        response = client.get("/api/scheduler/tasks/task-1/executions")
        assert response.status_code == 400


class TestListTaskExecutionsInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_task_executions_internal_error(self, mock_service, client):
        mock_service.list_executions.side_effect = Exception("db error")
        response = client.get("/api/scheduler/tasks/task-1/executions")
        assert response.status_code == 500


class TestListAllExecutionsValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_all_executions_value_error(self, mock_service, client):
        mock_service.list_executions.side_effect = ValueError("invalid filter")
        response = client.get("/api/scheduler/executions")
        assert response.status_code == 400


class TestListAllExecutionsInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_all_executions_internal_error(self, mock_service, client):
        mock_service.list_executions.side_effect = Exception("db error")
        response = client.get("/api/scheduler/executions")
        assert response.status_code == 500


class TestGetExecutionInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_execution_internal_error(self, mock_service, client):
        mock_service.get_execution.side_effect = Exception("db error")
        response = client.get("/api/scheduler/executions/exec-1")
        assert response.status_code == 500


class TestRetryExecutionInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_retry_execution_internal_error(self, mock_service, client):
        mock_service.retry_execution.side_effect = Exception("db error")
        response = client.post("/api/scheduler/executions/exec-1/retry")
        assert response.status_code == 500


class TestGetSchedulerStatusValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_scheduler_status_value_error(self, mock_service, client):
        mock_scheduler = MagicMock()
        type(mock_service)._scheduler = PropertyMock(side_effect=ValueError("not initialized"))
        response = client.get("/api/scheduler/status")
        assert response.status_code == 400


class TestGetSchedulerStatusInternalError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_scheduler_status_internal_error(self, mock_service, client):
        mock_scheduler = MagicMock()
        type(mock_service)._scheduler = PropertyMock(side_effect=Exception("fatal"))
        response = client.get("/api/scheduler/status")
        assert response.status_code == 500


class TestListTasksMultipleItems:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_tasks_multiple_items(self, mock_service, client):
        task1 = MagicMock()
        task1.model_dump.return_value = _make_task_dict(task_id="task-1", name="task-one")
        task2 = MagicMock()
        task2.model_dump.return_value = _make_task_dict(task_id="task-2", name="task-two")
        mock_service.list_tasks.return_value = [task1, task2]
        response = client.get("/api/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "task-one"
        assert data["items"][1]["name"] == "task-two"


class TestDeleteTaskSuccess:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_delete_task_success(self, mock_service, client):
        mock_service.delete_task.return_value = None
        response = client.delete("/api/scheduler/tasks/task-1")
        assert response.status_code == 200
        assert "已删除" in response.json()["message"]


class TestRetryExecutionValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_retry_execution_value_error(self, mock_service, client):
        mock_service.retry_execution.side_effect = ValueError("cannot retry")
        response = client.post("/api/scheduler/executions/exec-1/retry")
        assert response.status_code == 400


class TestGetExecutionValueError:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_get_execution_value_error(self, mock_service, client):
        mock_service.get_execution.side_effect = ValueError("not found")
        response = client.get("/api/scheduler/executions/nonexistent")
        assert response.status_code == 400


class TestListExecutionsWithPagination:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_executions_with_pagination(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.list_executions.return_value = [mock_exec]
        response = client.get("/api/scheduler/executions?limit=10&offset=5")
        assert response.status_code == 200
        mock_service.list_executions.assert_called_once_with(
            task_id=None, status=None, limit=10, offset=5
        )


class TestListTaskExecutionsWithPagination:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_list_task_executions_with_pagination(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_execution_dict()
        mock_service.list_executions.return_value = [mock_exec]
        response = client.get("/api/scheduler/tasks/task-1/executions?limit=20&offset=10")
        assert response.status_code == 200
        mock_service.list_executions.assert_called_once_with(
            task_id="task-1", limit=20, offset=10
        )


class TestRunTaskNowSuccess:
    @patch("app.api.routes.scheduler.task_scheduler_service")
    def test_run_task_now_success(self, mock_service, client):
        mock_exec = MagicMock()
        exec_dict = _make_execution_dict()
        exec_dict["status"] = "running"
        mock_exec.model_dump.return_value = exec_dict
        mock_service.run_task_now.return_value = mock_exec
        response = client.post("/api/scheduler/tasks/task-1/run")
        assert response.status_code == 200
        assert response.json()["status"] == "running"
