import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_workflow_dict(workflow_id="wf-1", name="test-workflow"):
    return {
        "id": workflow_id,
        "name": name,
        "description": "desc",
        "status": "draft",
        "version": 1,
        "nodes": [],
        "edges": [],
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


def _make_workflow_execution_dict(exec_id="exec-1", workflow_id="wf-1"):
    return {
        "id": exec_id,
        "workflow_id": workflow_id,
        "workflow_name": "test-workflow",
        "version": 1,
        "status": "pending",
        "trigger_type": "cron",
        "trigger_source": None,
        "started_at": "2025-01-01T00:00:00",
        "completed_at": None,
        "duration_seconds": None,
        "total_nodes": 0,
        "success_nodes": 0,
        "failed_nodes": 0,
        "error_message": None,
    }


def _make_workflow_version_dict(version_id="ver-1", workflow_id="wf-1"):
    return {
        "id": version_id,
        "workflow_id": workflow_id,
        "version": 2,
        "snapshot": {},
        "change_note": "test note",
        "created_at": "2025-01-01T00:00:00",
    }


class TestWorkflowList:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_workflows_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict()
        mock_service.list_workflows.return_value = [mock_wf]

        response = client.get("/api/workflow/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "test-workflow"

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_workflows_empty(self, mock_service, client):
        mock_service.list_workflows.return_value = []

        response = client.get("/api/workflow/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_workflows_value_error(self, mock_service, client):
        mock_service.list_workflows.side_effect = ValueError("bad request")

        response = client.get("/api/workflow/")
        assert response.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_workflows_internal_error(self, mock_service, client):
        mock_service.list_workflows.side_effect = RuntimeError("db error")

        response = client.get("/api/workflow/")
        assert response.status_code == 500


class TestWorkflowGet:
    @patch("app.api.routes.workflow.workflow_service")
    def test_get_workflow_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict()
        mock_service.get_workflow.return_value = mock_wf

        response = client.get("/api/workflow/wf-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf-1"

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_workflow_not_found(self, mock_service, client):
        mock_service.get_workflow.return_value = None

        response = client.get("/api/workflow/nonexistent")
        assert response.status_code == 500


class TestWorkflowCreate:
    @patch("app.api.routes.workflow.workflow_service")
    def test_create_workflow_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict()
        mock_service.create_workflow.return_value = mock_wf

        response = client.post("/api/workflow/", json={
            "name": "test-workflow",
            "description": "desc",
            "nodes": [],
            "edges": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-workflow"

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_workflow_value_error(self, mock_service, client):
        mock_service.create_workflow.side_effect = ValueError("invalid data")

        response = client.post("/api/workflow/", json={
            "name": "test-workflow",
            "nodes": [],
            "edges": [],
        })
        assert response.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_workflow_internal_error(self, mock_service, client):
        mock_service.create_workflow.side_effect = Exception("db error")

        response = client.post("/api/workflow/", json={
            "name": "test-workflow",
            "nodes": [],
            "edges": [],
        })
        assert response.status_code == 500


class TestWorkflowUpdate:
    @patch("app.api.routes.workflow.workflow_service")
    def test_update_workflow_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict(name="updated")
        mock_service.update_workflow.return_value = mock_wf

        response = client.put("/api/workflow/wf-1", json={"name": "updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated"

    @patch("app.api.routes.workflow.workflow_service")
    def test_update_workflow_not_found(self, mock_service, client):
        mock_service.update_workflow.side_effect = ValueError("Workflow 'wf-1' not found")

        response = client.put("/api/workflow/wf-1", json={"name": "updated"})
        assert response.status_code == 400


class TestWorkflowDelete:
    @patch("app.api.routes.workflow.workflow_service")
    def test_delete_workflow_success(self, mock_service, client):
        mock_service.delete_workflow.return_value = None

        response = client.delete("/api/workflow/wf-1")
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.workflow.workflow_service")
    def test_delete_workflow_not_found(self, mock_service, client):
        mock_service.delete_workflow.side_effect = ValueError("not found")

        response = client.delete("/api/workflow/wf-1")
        assert response.status_code == 400


class TestWorkflowValidate:
    @patch("app.api.routes.workflow.workflow_service")
    def test_validate_dag_valid(self, mock_service, client):
        mock_service.validate_dag.return_value = {"valid": True, "errors": []}

        response = client.post("/api/workflow/validate", json={
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "edges": [{"source_node_id": "n1", "target_node_id": "n2"}],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @patch("app.api.routes.workflow.workflow_service")
    def test_validate_dag_invalid(self, mock_service, client):
        mock_service.validate_dag.return_value = {"valid": False, "errors": ["Graph contains cycles"]}

        response = client.post("/api/workflow/validate", json={
            "nodes": [{"id": "n1"}],
            "edges": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


class TestWorkflowVersion:
    @patch("app.api.routes.workflow.workflow_service")
    def test_save_version_success(self, mock_service, client):
        mock_ver = MagicMock()
        mock_ver.model_dump.return_value = _make_workflow_version_dict()
        mock_service.save_version.return_value = mock_ver

        response = client.post("/api/workflow/wf-1/save-version", json={"change_note": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_versions_success(self, mock_service, client):
        mock_ver = MagicMock()
        mock_ver.model_dump.return_value = _make_workflow_version_dict()
        mock_service.list_versions.return_value = [mock_ver]

        response = client.get("/api/workflow/wf-1/versions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.workflow.workflow_service")
    def test_rollback_version_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict()
        mock_service.rollback_version.return_value = mock_wf

        response = client.post("/api/workflow/wf-1/rollback", json={"version": 1})
        assert response.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_rollback_version_not_found(self, mock_service, client):
        mock_service.rollback_version.side_effect = ValueError("Version 99 not found")

        response = client.post("/api/workflow/wf-1/rollback", json={"version": 99})
        assert response.status_code == 400


class TestWorkflowExportImport:
    @patch("app.api.routes.workflow.workflow_service")
    def test_export_workflow_success(self, mock_service, client):
        mock_service.export_workflow.return_value = {
            "name": "test-workflow",
            "description": "desc",
            "status": "draft",
            "version": 1,
            "nodes": [],
            "edges": [],
        }

        response = client.get("/api/workflow/wf-1/export")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-workflow"

    @patch("app.api.routes.workflow.workflow_service")
    def test_export_workflow_not_found(self, mock_service, client):
        mock_service.export_workflow.side_effect = ValueError("not found")

        response = client.get("/api/workflow/nonexistent/export")
        assert response.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_import_workflow_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict(name="imported")
        mock_service.import_workflow.return_value = mock_wf

        response = client.post("/api/workflow/import", json={
            "name": "imported",
            "nodes": [],
            "edges": [],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "imported"


class TestWorkflowTemplates:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_templates_success(self, mock_service, client):
        mock_tpl = MagicMock()
        mock_tpl.model_dump.return_value = {
            "id": "service-health-check",
            "name": "服务健康检查与自动重启",
            "description": "desc",
            "category": "monitoring",
            "nodes": [],
            "edges": [],
            "icon": "heartbeat",
        }
        mock_service.list_templates.return_value = [mock_tpl]

        response = client.get("/api/workflow/templates")
        assert response.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_from_template_success(self, mock_service, client):
        mock_wf = MagicMock()
        mock_wf.model_dump.return_value = _make_workflow_dict(name="from-template")
        mock_service.create_from_template.return_value = mock_wf

        response = client.post("/api/workflow/templates/tpl-1/create", json={"name": "from-template"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "from-template"

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_from_template_not_found(self, mock_service, client):
        mock_service.create_from_template.side_effect = ValueError("Template 'bad' not found")

        response = client.post("/api/workflow/templates/bad/create", json={"name": "test"})
        assert response.status_code == 400


class TestWorkflowExecution:
    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_workflow_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_workflow_execution_dict()
        mock_service.execute_workflow.return_value = mock_exec

        response = client.post("/api/workflow/wf-1/execute", json={
            "trigger_type": "cron",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "wf-1"

    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_workflow_not_found(self, mock_service, client):
        mock_service.execute_workflow.side_effect = ValueError("not found")

        response = client.post("/api/workflow/wf-1/execute", json={
            "trigger_type": "cron",
        })
        assert response.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_workflow_invalid_trigger_type(self, mock_service, client):
        response = client.post("/api/workflow/wf-1/execute", json={
            "trigger_type": "invalid_type",
        })
        assert response.status_code == 400


class TestWorkflowExecutionControl:
    @patch("app.api.routes.workflow.workflow_service")
    def test_pause_execution_success(self, mock_service, client):
        mock_service.pause_execution.return_value = None

        response = client.post("/api/workflow/executions/exec-1/pause")
        assert response.status_code == 200
        data = response.json()
        assert "已暂停" in data["message"]

    @patch("app.api.routes.workflow.workflow_service")
    def test_resume_execution_success(self, mock_service, client):
        mock_service.resume_execution.return_value = None

        response = client.post("/api/workflow/executions/exec-1/resume")
        assert response.status_code == 200
        data = response.json()
        assert "已恢复" in data["message"]

    @patch("app.api.routes.workflow.workflow_service")
    def test_cancel_execution_success(self, mock_service, client):
        mock_service.cancel_execution.return_value = None

        response = client.post("/api/workflow/executions/exec-1/cancel")
        assert response.status_code == 200
        data = response.json()
        assert "已取消" in data["message"]

    @patch("app.api.routes.workflow.workflow_service")
    def test_pause_execution_value_error(self, mock_service, client):
        mock_service.pause_execution.side_effect = ValueError("not found")

        response = client.post("/api/workflow/executions/exec-1/pause")
        assert response.status_code == 400


class TestWorkflowExecutionList:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_executions_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_workflow_execution_dict()
        mock_service.list_executions.return_value = [mock_exec]

        response = client.get("/api/workflow/wf-1/executions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_success(self, mock_service, client):
        mock_exec = MagicMock()
        mock_exec.model_dump.return_value = _make_workflow_execution_dict()
        mock_service.get_execution.return_value = mock_exec
        mock_service.list_node_executions.return_value = []

        response = client.get("/api/workflow/executions/exec-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "exec-1"
        assert "node_executions" in data

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_not_found(self, mock_service, client):
        mock_service.get_execution.return_value = None

        response = client.get("/api/workflow/executions/nonexistent")
        assert response.status_code == 500

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_node_executions_success(self, mock_service, client):
        mock_ne = MagicMock()
        mock_ne.model_dump.return_value = {
            "id": "ne-1",
            "execution_id": "exec-1",
            "node_id": "n1",
            "node_name": "node1",
            "node_type": "action_shell",
            "status": "success",
            "input_data": None,
            "output_data": None,
            "error_message": None,
            "started_at": "2025-01-01T00:00:00",
            "completed_at": "2025-01-01T00:00:01",
            "duration_seconds": 1.0,
        }
        mock_service.list_node_executions.return_value = [mock_ne]

        response = client.get("/api/workflow/executions/exec-1/nodes")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
