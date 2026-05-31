from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.workflow_service import WorkflowService
from app.models.workflow import (
    ExecutionStatus,
    NodeType,
    TriggerType,
    WorkflowCreate,
    WorkflowStatus,
    WorkflowUpdate,
)


@pytest.fixture
def service():
    svc = WorkflowService()
    return svc


class TestInitDb:
    def test_init_creates_tables(self, service):
        with service._conn() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}
            assert "workflows" in table_names
            assert "workflow_nodes" in table_names
            assert "workflow_edges" in table_names
            assert "workflow_versions" in table_names
            assert "workflow_executions" in table_names
            assert "node_executions" in table_names


class TestCreateWorkflow:
    def test_create_workflow(self, service):
        data = WorkflowCreate(
            name="test-wf",
            description="desc",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "trigger", "config": {"cron": "*/5 * * * *"}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        assert wf.name == "test-wf"
        assert wf.status == WorkflowStatus.DRAFT
        assert len(wf.nodes) == 1

    def test_create_workflow_with_edges(self, service):
        data = WorkflowCreate(
            name="test-wf",
            description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "trigger", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "action", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        assert len(wf.edges) == 1

    def test_create_workflow_empty(self, service):
        data = WorkflowCreate(name="empty", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        assert wf.name == "empty"
        assert len(wf.nodes) == 0


class TestGetWorkflow:
    def test_get_workflow_found(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        found = service.get_workflow(wf.id)
        assert found is not None
        assert found.name == "wf1"

    def test_get_workflow_not_found(self, service):
        assert service.get_workflow("nonexistent") is None


class TestListWorkflows:
    def test_list_workflows(self, service):
        data1 = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        data2 = WorkflowCreate(name="wf2", description="", nodes=[], edges=[])
        service.create_workflow(data1)
        service.create_workflow(data2)
        result = service.list_workflows()
        assert len(result) >= 2


class TestUpdateWorkflow:
    def test_update_workflow_name(self, service):
        data = WorkflowCreate(name="old", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        update = WorkflowUpdate(name="new")
        updated = service.update_workflow(wf.id, update)
        assert updated.name == "new"

    def test_update_workflow_not_found(self, service):
        update = WorkflowUpdate(name="new")
        with pytest.raises(ValueError, match="not found"):
            service.update_workflow("nonexistent", update)

    def test_update_workflow_with_nodes(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        update = WorkflowUpdate(nodes=[{"id": "n1", "node_type": "action_shell", "name": "action", "config": {}}])
        updated = service.update_workflow(wf.id, update)
        assert len(updated.nodes) == 1

    def test_update_workflow_with_nodes_and_edges(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        update = WorkflowUpdate(
            nodes=[{"id": "n3", "node_type": "action_shell", "name": "new", "config": {}}],
            edges=[],
        )
        updated = service.update_workflow(wf.id, update)
        assert len(updated.nodes) == 1
        assert len(updated.edges) == 0


class TestDeleteWorkflow:
    def test_delete_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.delete_workflow(wf.id)
        assert service.get_workflow(wf.id) is None

    def test_delete_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.delete_workflow("nonexistent")


class TestValidateDag:
    def test_valid_dag(self, service):
        result = service.validate_dag(
            [{"id": "n1"}, {"id": "n2"}],
            [{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        assert result["valid"] is True

    def test_cyclic_dag(self, service):
        result = service.validate_dag(
            [{"id": "n1"}, {"id": "n2"}],
            [{"source_node_id": "n1", "target_node_id": "n2"}, {"source_node_id": "n2", "target_node_id": "n1"}],
        )
        assert result["valid"] is False
        assert any("cycles" in e for e in result["errors"])

    def test_isolated_nodes(self, service):
        result = service.validate_dag(
            [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
            [{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        assert result["valid"] is False
        assert any("isolated" in e for e in result["errors"])

    def test_missing_node_id(self, service):
        result = service.validate_dag(
            [{"id": ""}, {"id": "n2"}],
            [],
        )
        assert result["valid"] is False

    def test_missing_edge_source(self, service):
        result = service.validate_dag(
            [{"id": "n1"}],
            [{"source_node_id": "", "target_node_id": "n1"}],
        )
        assert result["valid"] is False

    def test_single_node_no_edges(self, service):
        result = service.validate_dag(
            [{"id": "n1"}],
            [],
        )
        assert result["valid"] is True


class TestSaveVersion:
    def test_save_version(self, service):
        data = WorkflowCreate(name="wf1", description="desc", nodes=[], edges=[])
        wf = service.create_workflow(data)
        version = service.save_version(wf.id, "initial version")
        assert version.version == 2
        assert version.change_note == "initial version"

    def test_save_version_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.save_version("nonexistent")


class TestListVersions:
    def test_list_versions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.save_version(wf.id, "v1")
        versions = service.list_versions(wf.id)
        assert len(versions) >= 1


class TestRollbackVersion:
    def test_rollback_version(self, service):
        data = WorkflowCreate(
            name="wf1", description="original",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        service.save_version(wf.id, "v1")
        service.update_workflow(wf.id, WorkflowUpdate(name="updated"))
        rolled = service.rollback_version(wf.id, 2)
        assert rolled.name == "wf1"

    def test_rollback_version_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.rollback_version("nonexistent", 1)


class TestExportImport:
    def test_export_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="desc", nodes=[], edges=[])
        wf = service.create_workflow(data)
        exported = service.export_workflow(wf.id)
        assert exported["name"] == "wf1"

    def test_export_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.export_workflow("nonexistent")

    def test_import_workflow(self, service):
        data = {"name": "imported", "description": "imported desc", "nodes": [], "edges": []}
        wf = service.import_workflow(data)
        assert wf.name == "imported"

    def test_import_workflow_with_nodes(self, service):
        data = {
            "name": "imported",
            "nodes": [{"id": "n1", "node_type": "action_shell", "name": "action", "config": {"command": "ls"}}],
            "edges": [],
        }
        wf = service.import_workflow(data)
        assert len(wf.nodes) == 1


class TestTemplates:
    def test_list_templates(self, service):
        templates = service.list_templates()
        assert len(templates) > 0

    def test_create_from_template(self, service):
        templates = service.list_templates()
        if templates:
            wf = service.create_from_template(templates[0].id, "my-wf")
            assert wf.name == "my-wf"

    def test_create_from_template_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.create_from_template("nonexistent", "my-wf")


class TestExecuteWorkflow:
    def test_execute_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        execution = service.execute_workflow(wf.id, TriggerType.CRON)
        assert execution.workflow_id == wf.id
        assert execution.status == ExecutionStatus.PENDING

    def test_execute_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.execute_workflow("nonexistent", TriggerType.CRON)


class TestExecutionControl:
    def test_pause_execution(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        service.pause_execution(execution.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.PAUSED

    def test_cancel_execution(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        service.cancel_execution(execution.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.CANCELLED


class TestListExecutions:
    def test_list_executions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.execute_workflow(wf.id, TriggerType.CRON)
        executions = service.list_executions(workflow_id=wf.id)
        assert len(executions) >= 1

    def test_list_all_executions(self, service):
        executions = service.list_executions()
        assert isinstance(executions, list)


class TestGetExecution:
    def test_get_execution_not_found(self, service):
        assert service.get_execution("nonexistent") is None


class TestListNodeExecutions:
    def test_list_node_executions(self, service):
        result = service.list_node_executions("nonexistent")
        assert result == []


class TestResolveVariables:
    def test_resolve_string_variable(self, service):
        context = {"n1": {"status_code": 200}}
        result = service._resolve_variables("${n1.status_code}", context)
        assert result == "200"

    def test_resolve_dict_variable(self, service):
        context = {"n1": {"status_code": 200}}
        result = service._resolve_variables({"key": "${n1.status_code}"}, context)
        assert result["key"] == "200"

    def test_resolve_list_variable(self, service):
        context = {"n1": "hello"}
        result = service._resolve_variables(["${n1}", "static"], context)
        assert result[0] == "hello"

    def test_resolve_missing_variable(self, service):
        context = {}
        result = service._resolve_variables("${n1.status_code}", context)
        assert result == "${n1.status_code}"

    def test_resolve_non_string(self, service):
        assert service._resolve_variables(42, {}) == 42
