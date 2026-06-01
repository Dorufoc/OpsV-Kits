from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_workflow():
    wf = MagicMock()
    wf.model_dump.return_value = {"id": "wf1", "name": "test"}
    return wf


def _mock_execution():
    ex = MagicMock()
    ex.model_dump.return_value = {"id": "ex1", "status": "running"}
    return ex


class TestListWorkflowsErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_value_error(self, mock_service):
        mock_service.list_workflows.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_generic_error(self, mock_service):
        mock_service.list_workflows.side_effect = Exception("fail")
        resp = client.get("/api/workflow/")
        assert resp.status_code == 500


class TestGetWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_get_value_error(self, mock_service):
        mock_service.get_workflow.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/wf1")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_generic_error(self, mock_service):
        mock_service.get_workflow.side_effect = Exception("fail")
        resp = client.get("/api/workflow/wf1")
        assert resp.status_code == 500


class TestCreateWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_create_value_error(self, mock_service):
        mock_service.create_workflow.side_effect = ValueError("bad")
        resp = client.post(
            "/api/workflow/",
            json={"name": "test", "nodes": [], "edges": []},
        )
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_generic_error(self, mock_service):
        mock_service.create_workflow.side_effect = Exception("fail")
        resp = client.post(
            "/api/workflow/",
            json={"name": "test", "nodes": [], "edges": []},
        )
        assert resp.status_code == 500


class TestUpdateWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_update_value_error(self, mock_service):
        mock_service.update_workflow.side_effect = ValueError("bad")
        resp = client.put("/api/workflow/wf1", json={"name": "updated"})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_update_generic_error(self, mock_service):
        mock_service.update_workflow.side_effect = Exception("fail")
        resp = client.put("/api/workflow/wf1", json={"name": "updated"})
        assert resp.status_code == 500


class TestDeleteWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_delete_value_error(self, mock_service):
        mock_service.delete_workflow.side_effect = ValueError("bad")
        resp = client.delete("/api/workflow/wf1")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_delete_generic_error(self, mock_service):
        mock_service.delete_workflow.side_effect = Exception("fail")
        resp = client.delete("/api/workflow/wf1")
        assert resp.status_code == 500


class TestValidateWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_validate_value_error(self, mock_service):
        mock_service.validate_dag.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/validate", json={"nodes": [], "edges": []})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_validate_generic_error(self, mock_service):
        mock_service.validate_dag.side_effect = Exception("fail")
        resp = client.post("/api/workflow/validate", json={"nodes": [], "edges": []})
        assert resp.status_code == 500


class TestSaveVersionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_save_version_value_error(self, mock_service):
        mock_service.save_version.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/wf1/save-version", json={"change_note": "test"})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_save_version_generic_error(self, mock_service):
        mock_service.save_version.side_effect = Exception("fail")
        resp = client.post("/api/workflow/wf1/save-version", json={"change_note": "test"})
        assert resp.status_code == 500


class TestListVersionsErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_versions_value_error(self, mock_service):
        mock_service.list_versions.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/wf1/versions")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_versions_generic_error(self, mock_service):
        mock_service.list_versions.side_effect = Exception("fail")
        resp = client.get("/api/workflow/wf1/versions")
        assert resp.status_code == 500


class TestRollbackVersionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_rollback_value_error(self, mock_service):
        mock_service.rollback_version.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/wf1/rollback", json={"version": 1})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_rollback_generic_error(self, mock_service):
        mock_service.rollback_version.side_effect = Exception("fail")
        resp = client.post("/api/workflow/wf1/rollback", json={"version": 1})
        assert resp.status_code == 500


class TestExportWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_export_value_error(self, mock_service):
        mock_service.export_workflow.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/wf1/export")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_export_generic_error(self, mock_service):
        mock_service.export_workflow.side_effect = Exception("fail")
        resp = client.get("/api/workflow/wf1/export")
        assert resp.status_code == 500


class TestImportWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_import_value_error(self, mock_service):
        mock_service.import_workflow.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/import", json={"name": "test"})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_import_generic_error(self, mock_service):
        mock_service.import_workflow.side_effect = Exception("fail")
        resp = client.post("/api/workflow/import", json={"name": "test"})
        assert resp.status_code == 500


class TestListTemplatesErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_templates_value_error(self, mock_service):
        mock_service.get_workflow.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/templates")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_templates_generic_error(self, mock_service):
        mock_service.get_workflow.side_effect = Exception("fail")
        resp = client.get("/api/workflow/templates")
        assert resp.status_code == 500


class TestCreateFromTemplateErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_create_from_template_value_error(self, mock_service):
        mock_service.create_from_template.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/templates/tpl1/create", json={"name": "new_wf"})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_from_template_generic_error(self, mock_service):
        mock_service.create_from_template.side_effect = Exception("fail")
        resp = client.post("/api/workflow/templates/tpl1/create", json={"name": "new_wf"})
        assert resp.status_code == 500


class TestExecuteWorkflowErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_value_error(self, mock_service):
        mock_service.execute_workflow.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/wf1/execute", json={"trigger_type": "cron"})
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_generic_error(self, mock_service):
        mock_service.execute_workflow.side_effect = Exception("fail")
        resp = client.post("/api/workflow/wf1/execute", json={"trigger_type": "cron"})
        assert resp.status_code == 500


class TestPauseExecutionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_pause_value_error(self, mock_service):
        mock_service.pause_execution.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/executions/ex1/pause")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_pause_generic_error(self, mock_service):
        mock_service.pause_execution.side_effect = Exception("fail")
        resp = client.post("/api/workflow/executions/ex1/pause")
        assert resp.status_code == 500


class TestResumeExecutionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_resume_value_error(self, mock_service):
        mock_service.resume_execution.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/executions/ex1/resume")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_resume_generic_error(self, mock_service):
        mock_service.resume_execution.side_effect = Exception("fail")
        resp = client.post("/api/workflow/executions/ex1/resume")
        assert resp.status_code == 500


class TestCancelExecutionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_cancel_value_error(self, mock_service):
        mock_service.cancel_execution.side_effect = ValueError("bad")
        resp = client.post("/api/workflow/executions/ex1/cancel")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_cancel_generic_error(self, mock_service):
        mock_service.cancel_execution.side_effect = Exception("fail")
        resp = client.post("/api/workflow/executions/ex1/cancel")
        assert resp.status_code == 500


class TestListExecutionsErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_executions_value_error(self, mock_service):
        mock_service.list_executions.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/wf1/executions")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_executions_generic_error(self, mock_service):
        mock_service.list_executions.side_effect = Exception("fail")
        resp = client.get("/api/workflow/wf1/executions")
        assert resp.status_code == 500


class TestGetExecutionErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_value_error(self, mock_service):
        mock_service.get_execution.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/executions/ex1")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_generic_error(self, mock_service):
        mock_service.get_execution.side_effect = Exception("fail")
        resp = client.get("/api/workflow/executions/ex1")
        assert resp.status_code == 500

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_not_found(self, mock_service):
        mock_service.get_execution.return_value = None
        resp = client.get("/api/workflow/executions/ex1")
        assert resp.status_code == 500


class TestListNodeExecutionsErrors:
    @patch("app.api.routes.workflow.workflow_service")
    def test_list_node_executions_value_error(self, mock_service):
        mock_service.list_node_executions.side_effect = ValueError("bad")
        resp = client.get("/api/workflow/executions/ex1/nodes")
        assert resp.status_code == 400

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_node_executions_generic_error(self, mock_service):
        mock_service.list_node_executions.side_effect = Exception("fail")
        resp = client.get("/api/workflow/executions/ex1/nodes")
        assert resp.status_code == 500


class TestWorkflowSuccessPaths:
    @patch("app.api.routes.workflow.workflow_service")
    def test_get_workflow_success(self, mock_service):
        mock_service.get_workflow.return_value = _mock_workflow()
        resp = client.get("/api/workflow/wf1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "wf1"

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_workflow_success(self, mock_service):
        mock_service.create_workflow.return_value = _mock_workflow()
        resp = client.post(
            "/api/workflow/",
            json={"name": "test", "nodes": [], "edges": []},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_update_workflow_success(self, mock_service):
        mock_service.update_workflow.return_value = _mock_workflow()
        resp = client.put("/api/workflow/wf1", json={"name": "updated"})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_delete_workflow_success(self, mock_service):
        mock_service.delete_workflow.return_value = None
        resp = client.delete("/api/workflow/wf1")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_validate_workflow_success(self, mock_service):
        mock_service.validate_dag.return_value = {"valid": True}
        resp = client.post("/api/workflow/validate", json={"nodes": [], "edges": []})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_save_version_success(self, mock_service):
        mock_ver = MagicMock()
        mock_ver.model_dump.return_value = {"version": 1}
        mock_service.save_version.return_value = mock_ver
        resp = client.post("/api/workflow/wf1/save-version", json={"change_note": "test"})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_versions_success(self, mock_service):
        mock_ver = MagicMock()
        mock_ver.model_dump.return_value = {"version": 1}
        mock_service.list_versions.return_value = [mock_ver]
        resp = client.get("/api/workflow/wf1/versions")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_rollback_success(self, mock_service):
        mock_service.rollback_version.return_value = _mock_workflow()
        resp = client.post("/api/workflow/wf1/rollback", json={"version": 1})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_export_success(self, mock_service):
        mock_service.export_workflow.return_value = {"name": "test"}
        resp = client.get("/api/workflow/wf1/export")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_import_success(self, mock_service):
        mock_service.import_workflow.return_value = _mock_workflow()
        resp = client.post("/api/workflow/import", json={"name": "test"})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_templates_success(self, mock_service):
        mock_tpl = MagicMock()
        mock_tpl.model_dump.return_value = {"id": "tpl1"}
        mock_service.list_templates.return_value = [mock_tpl]
        resp = client.get("/api/workflow/templates")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_create_from_template_success(self, mock_service):
        mock_service.create_from_template.return_value = _mock_workflow()
        resp = client.post("/api/workflow/templates/tpl1/create", json={"name": "new_wf"})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_execute_success(self, mock_service):
        mock_service.execute_workflow.return_value = _mock_execution()
        resp = client.post("/api/workflow/wf1/execute", json={"trigger_type": "cron"})
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_pause_success(self, mock_service):
        mock_service.pause_execution.return_value = None
        resp = client.post("/api/workflow/executions/ex1/pause")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_resume_success(self, mock_service):
        mock_service.resume_execution.return_value = None
        resp = client.post("/api/workflow/executions/ex1/resume")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_cancel_success(self, mock_service):
        mock_service.cancel_execution.return_value = None
        resp = client.post("/api/workflow/executions/ex1/cancel")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_executions_success(self, mock_service):
        mock_ex = MagicMock()
        mock_ex.model_dump.return_value = {"id": "ex1"}
        mock_service.list_executions.return_value = [mock_ex]
        resp = client.get("/api/workflow/wf1/executions")
        assert resp.status_code == 200

    @patch("app.api.routes.workflow.workflow_service")
    def test_get_execution_success(self, mock_service):
        mock_ex = MagicMock()
        mock_ex.model_dump.return_value = {"id": "ex1", "status": "running"}
        mock_service.get_execution.return_value = mock_ex
        mock_ne = MagicMock()
        mock_ne.model_dump.return_value = {"node_id": "n1"}
        mock_service.list_node_executions.return_value = [mock_ne]
        resp = client.get("/api/workflow/executions/ex1")
        assert resp.status_code == 200
        data = resp.json()
        assert "node_executions" in data

    @patch("app.api.routes.workflow.workflow_service")
    def test_list_node_executions_success(self, mock_service):
        mock_ne = MagicMock()
        mock_ne.model_dump.return_value = {"node_id": "n1"}
        mock_service.list_node_executions.return_value = [mock_ne]
        resp = client.get("/api/workflow/executions/ex1/nodes")
        assert resp.status_code == 200
