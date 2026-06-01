from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.workflow import (
    ExecutionStatus,
    NodeType,
    NodeExecution,
    TriggerType,
    Workflow,
    WorkflowCreate,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowNode,
    WorkflowStatus,
    WorkflowUpdate,
    WorkflowVersion,
)
from app.services.workflow_service import WorkflowService


@pytest.fixture
def service(tmp_path):
    db_path = tmp_path / "workflow.db"
    with patch("app.services.workflow_service._DB_PATH", db_path), \
         patch("app.services.workflow_service._PERSIST_DIR", tmp_path):
        svc = WorkflowService()
    svc._db_path = db_path
    svc._persist_dir = tmp_path
    original_conn = svc._conn
    def _patched_conn():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = None
        return conn
    svc._conn = _patched_conn
    return svc


class TestRowToWorkflowNode:
    def test_full_row(self, service):
        row = {
            "id": "n1", "workflow_id": "wf1", "node_type": "trigger_cron",
            "name": "trigger", "config": '{"cron": "*/5 * * * *"}',
            "position_x": 100, "position_y": 200, "description": "desc",
            "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00",
        }
        node = service._row_to_workflow_node(row)
        assert node.id == "n1"
        assert node.node_type == NodeType.TRIGGER_CRON
        assert node.config == {"cron": "*/5 * * * *"}
        assert node.position_x == 100
        assert node.position_y == 200

    def test_null_config(self, service):
        row = {
            "id": "n1", "workflow_id": "wf1", "node_type": "end",
            "name": "end", "config": None,
            "position_x": 0, "position_y": 0, "description": None,
            "created_at": None, "updated_at": None,
        }
        node = service._row_to_workflow_node(row)
        assert node.config == {}

    def test_missing_optional_fields(self, service):
        row = {
            "id": "n1", "workflow_id": "wf1", "node_type": "action_shell",
            "name": "shell", "config": "{}",
        }
        node = service._row_to_workflow_node(row)
        assert node.position_x == 0
        assert node.position_y == 0
        assert node.description is None


class TestRowToWorkflowEdge:
    def test_full_row(self, service):
        row = {
            "id": "e1", "workflow_id": "wf1",
            "source_node_id": "n1", "target_node_id": "n2",
            "source_port": "out", "target_port": "in",
            "label": "true", "created_at": "2024-01-01T00:00:00",
        }
        edge = service._row_to_workflow_edge(row)
        assert edge.source_node_id == "n1"
        assert edge.target_node_id == "n2"
        assert edge.label == "true"

    def test_null_optional_fields(self, service):
        row = {
            "id": "e1", "workflow_id": "wf1",
            "source_node_id": "n1", "target_node_id": "n2",
            "source_port": None, "target_port": None,
            "label": None, "created_at": None,
        }
        edge = service._row_to_workflow_edge(row)
        assert edge.source_port is None
        assert edge.target_port is None
        assert edge.label is None


class TestRowToWorkflow:
    def test_with_nodes_and_edges(self, service):
        row = {
            "id": "wf1", "name": "test", "description": "desc",
            "status": "draft", "version": 1,
            "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00",
        }
        node = WorkflowNode(id="n1", workflow_id="wf1", node_type=NodeType.END, name="end", config={}, position_x=0, position_y=0)
        edge = WorkflowEdge(id="e1", workflow_id="wf1", source_node_id="n1", target_node_id="n2")
        wf = service._row_to_workflow(row, [node], [edge])
        assert wf.id == "wf1"
        assert len(wf.nodes) == 1
        assert len(wf.edges) == 1

    def test_defaults(self, service):
        row = {"id": "wf1", "name": "test"}
        wf = service._row_to_workflow(row)
        assert wf.status == WorkflowStatus.DRAFT
        assert wf.version == 1
        assert wf.nodes == []
        assert wf.edges == []


class TestRowToWorkflowVersion:
    def test_with_snapshot_str(self, service):
        row = {
            "id": "v1", "workflow_id": "wf1", "version": 2,
            "snapshot": '{"name": "test"}', "change_note": "note",
            "created_at": "2024-01-01T00:00:00",
        }
        ver = service._row_to_workflow_version(row)
        assert ver.snapshot == {"name": "test"}
        assert ver.change_note == "note"

    def test_null_snapshot(self, service):
        row = {
            "id": "v1", "workflow_id": "wf1", "version": 1,
            "snapshot": None, "change_note": None,
            "created_at": None,
        }
        ver = service._row_to_workflow_version(row)
        assert ver.snapshot == {}


class TestRowToWorkflowExecution:
    def test_full_row(self, service):
        row = {
            "id": "ex1", "workflow_id": "wf1", "workflow_name": "test",
            "version": 1, "status": "success", "trigger_type": "cron",
            "trigger_source": "manual", "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00", "duration_seconds": 60.0,
            "total_nodes": 3, "success_nodes": 3, "failed_nodes": 0,
            "error_message": None,
        }
        ex = service._row_to_workflow_execution(row)
        assert ex.status == ExecutionStatus.SUCCESS
        assert ex.trigger_type == TriggerType.CRON
        assert ex.duration_seconds == 60.0

    def test_defaults(self, service):
        row = {"id": "ex1", "workflow_id": "wf1"}
        ex = service._row_to_workflow_execution(row)
        assert ex.status == ExecutionStatus.PENDING
        assert ex.trigger_type == TriggerType.CRON
        assert ex.total_nodes == 0
        assert ex.completed_at is None


class TestRowToNodeExecution:
    def test_full_row(self, service):
        row = {
            "id": "ne1", "execution_id": "ex1", "node_id": "n1",
            "node_name": "shell", "node_type": "action_shell",
            "status": "success", "input_data": '{"cmd": "ls"}',
            "output_data": '{"result": "ok"}', "error_message": None,
            "started_at": "2024-01-01T00:00:00", "completed_at": "2024-01-01T00:00:01",
            "duration_seconds": 1.0,
        }
        ne = service._row_to_node_execution(row)
        assert ne.status == ExecutionStatus.SUCCESS
        assert ne.input_data == {"cmd": "ls"}
        assert ne.output_data == {"result": "ok"}

    def test_null_data(self, service):
        row = {
            "id": "ne1", "execution_id": "ex1", "node_id": "n1",
            "node_name": "", "node_type": None,
            "status": "pending", "input_data": None, "output_data": None,
            "error_message": None, "started_at": None, "completed_at": None,
            "duration_seconds": None,
        }
        ne = service._row_to_node_execution(row)
        assert ne.node_type == NodeType.END
        assert ne.input_data is None
        assert ne.output_data is None


class TestCreateWorkflow:
    def test_create_workflow(self, service):
        data = WorkflowCreate(
            name="test-wf", description="desc",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "trigger", "config": {"cron": "*/5 * * * *"}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        assert wf.name == "test-wf"
        assert wf.status == WorkflowStatus.DRAFT
        assert len(wf.nodes) == 1

    def test_create_workflow_with_edges(self, service):
        data = WorkflowCreate(
            name="test-wf", description="",
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

    def test_create_workflow_node_without_id(self, service):
        data = WorkflowCreate(
            name="no-id", description="",
            nodes=[{"node_type": "end", "name": "end", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        assert len(wf.nodes) == 1

    def test_create_workflow_edge_with_ports(self, service):
        data = WorkflowCreate(
            name="ports", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2", "source_port": "out", "target_port": "in", "label": "true"}],
        )
        wf = service.create_workflow(data)
        assert wf.edges[0].source_port == "out"
        assert wf.edges[0].label == "true"


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
        names = [w.name for w in result]
        assert "wf1" in names
        assert "wf2" in names

    def test_list_workflows_empty(self, service):
        result = service.list_workflows()
        assert isinstance(result, list)


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

    def test_update_workflow_status(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        update = WorkflowUpdate(status=WorkflowStatus.ACTIVE)
        updated = service.update_workflow(wf.id, update)
        assert updated.status == WorkflowStatus.ACTIVE

    def test_update_workflow_edges_only(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[],
        )
        wf = service.create_workflow(data)
        update = WorkflowUpdate(edges=[{"source_node_id": "n1", "target_node_id": "n2"}])
        updated = service.update_workflow(wf.id, update)
        assert len(updated.edges) == 1

    def test_update_workflow_nodes_remap_edges(self, service):
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
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t2", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a2", "config": {}},
            ],
        )
        updated = service.update_workflow(wf.id, update)
        assert len(updated.edges) == 1

    def test_update_workflow_description(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        update = WorkflowUpdate(description="new desc")
        updated = service.update_workflow(wf.id, update)
        assert updated.description == "new desc"


class TestDeleteWorkflow:
    def test_delete_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.delete_workflow(wf.id)
        assert service.get_workflow(wf.id) is None

    def test_delete_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.delete_workflow("nonexistent")

    def test_delete_workflow_with_executions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            service.execute_workflow(wf.id, TriggerType.CRON)
        service.delete_workflow(wf.id)
        assert service.get_workflow(wf.id) is None
        assert service.list_executions(workflow_id=wf.id) == []

    def test_delete_workflow_with_versions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.save_version(wf.id, "v1")
        service.delete_workflow(wf.id)
        assert service.list_versions(wf.id) == []


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
        result = service.validate_dag([{"id": ""}, {"id": "n2"}], [])
        assert result["valid"] is False

    def test_missing_edge_source(self, service):
        result = service.validate_dag(
            [{"id": "n1"}],
            [{"source_node_id": "", "target_node_id": "n1"}],
        )
        assert result["valid"] is False

    def test_missing_edge_target(self, service):
        result = service.validate_dag(
            [{"id": "n1"}],
            [{"source_node_id": "n1", "target_node_id": ""}],
        )
        assert result["valid"] is False

    def test_single_node_no_edges(self, service):
        result = service.validate_dag([{"id": "n1"}], [])
        assert result["valid"] is True

    def test_no_nodes_no_edges(self, service):
        result = service.validate_dag([], [])
        assert result["valid"] is True

    def test_multiple_isolated_nodes(self, service):
        result = service.validate_dag(
            [{"id": "n1"}, {"id": "n2"}],
            [],
        )
        assert result["valid"] is False
        assert len([e for e in result["errors"] if "isolated" in e]) == 2


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

    def test_save_version_snapshot_content(self, service):
        data = WorkflowCreate(
            name="wf1", description="desc",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {"cron": "* * * * *"}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        version = service.save_version(wf.id, "v1")
        assert version.snapshot["name"] == "wf1"
        assert len(version.snapshot["nodes"]) == 1
        assert version.snapshot["status"] == "draft"

    def test_save_version_increments(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        v1 = service.save_version(wf.id, "v1")
        v2 = service.save_version(wf.id, "v2")
        assert v1.version == 2
        assert v2.version == 3

    def test_save_version_no_change_note(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        version = service.save_version(wf.id)
        assert version.change_note is None


class TestListVersions:
    def test_list_versions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        service.save_version(wf.id, "v1")
        service.save_version(wf.id, "v2")
        versions = service.list_versions(wf.id)
        assert len(versions) == 2
        assert versions[0].version > versions[1].version

    def test_list_versions_empty(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        versions = service.list_versions(wf.id)
        assert versions == []


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
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with pytest.raises(ValueError, match="not found"):
            service.rollback_version(wf.id, 999)

    def test_rollback_restores_nodes_and_edges(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        service.save_version(wf.id, "v1")
        service.update_workflow(wf.id, WorkflowUpdate(nodes=[], edges=[]))
        assert len(service.get_workflow(wf.id).nodes) == 0
        rolled = service.rollback_version(wf.id, 2)
        assert len(rolled.nodes) == 2
        assert len(rolled.edges) == 1

    def test_rollback_dict_snapshot(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[{"id": "n1", "node_type": "end", "name": "end", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        version = service.save_version(wf.id, "v1")
        with service._conn() as conn:
            conn.execute(
                "UPDATE workflow_versions SET snapshot = ? WHERE id = ?",
                (json.dumps({"name": "dict-test", "description": None, "status": "draft", "nodes": [], "edges": []}), version.id),
            )
        rolled = service.rollback_version(wf.id, version.version)
        assert rolled.name == "dict-test"


class TestExportImport:
    def test_export_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="desc", nodes=[], edges=[])
        wf = service.create_workflow(data)
        exported = service.export_workflow(wf.id)
        assert exported["name"] == "wf1"
        assert exported["status"] == "draft"

    def test_export_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.export_workflow("nonexistent")

    def test_export_workflow_with_nodes(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {"cron": "* * * * *"}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        exported = service.export_workflow(wf.id)
        assert len(exported["nodes"]) == 1
        assert exported["nodes"][0]["node_type"] == "trigger_cron"

    def test_import_workflow(self, service):
        data = {"name": "imported", "description": "imported desc", "nodes": [], "edges": []}
        wf = service.import_workflow(data)
        assert wf.name == "imported"
        assert wf.status == WorkflowStatus.DRAFT

    def test_import_workflow_with_nodes(self, service):
        data = {
            "name": "imported",
            "nodes": [{"id": "n1", "node_type": "action_shell", "name": "action", "config": {"command": "ls"}}],
            "edges": [],
        }
        wf = service.import_workflow(data)
        assert len(wf.nodes) == 1

    def test_import_workflow_with_edges(self, service):
        data = {
            "name": "imported",
            "nodes": [
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            "edges": [{"source_node_id": "n1", "target_node_id": "n2"}],
        }
        wf = service.import_workflow(data)
        assert len(wf.edges) == 1

    def test_import_workflow_missing_name(self, service):
        data = {"nodes": [], "edges": []}
        wf = service.import_workflow(data)
        assert wf.name == "Imported Workflow"

    def test_import_export_roundtrip(self, service):
        data = WorkflowCreate(
            name="roundtrip", description="desc",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {"cron": "* * * * *"}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {"command": "ls"}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        exported = service.export_workflow(wf.id)
        imported = service.import_workflow(exported)
        assert imported.name == "roundtrip"
        assert len(imported.nodes) == 2
        assert len(imported.edges) == 1


class TestTemplates:
    def test_list_templates(self, service):
        templates = service.list_templates()
        assert len(templates) > 0

    def test_create_from_template(self, service):
        templates = service.list_templates()
        wf = service.create_from_template(templates[0].id, "my-wf")
        assert wf.name == "my-wf"
        assert len(wf.nodes) == len(templates[0].nodes)

    def test_create_from_template_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.create_from_template("nonexistent", "my-wf")

    def test_create_from_template_copies_edges(self, service):
        templates = service.list_templates()
        tpl = templates[0]
        wf = service.create_from_template(tpl.id, "my-wf")
        assert len(wf.edges) == len(tpl.edges)


class TestExecuteWorkflow:
    def test_execute_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        assert execution.workflow_id == wf.id
        assert execution.status == ExecutionStatus.PENDING

    def test_execute_workflow_not_found(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.execute_workflow("nonexistent", TriggerType.CRON)

    def test_execute_workflow_with_trigger_source(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.WEBHOOK, "hook-1")
        assert execution.trigger_source == "hook-1"

    def test_execute_workflow_with_nodes(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        assert execution.total_nodes == 2


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

    def test_resume_execution(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        service.pause_execution(execution.id)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            service.resume_execution(execution.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.RUNNING


class TestListExecutions:
    def test_list_executions(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            service.execute_workflow(wf.id, TriggerType.CRON)
        executions = service.list_executions(workflow_id=wf.id)
        assert len(executions) >= 1

    def test_list_all_executions(self, service):
        executions = service.list_executions()
        assert isinstance(executions, list)

    def test_list_executions_with_limit(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        for _ in range(3):
            with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
                service.execute_workflow(wf.id, TriggerType.CRON)
        executions = service.list_executions(workflow_id=wf.id, limit=2)
        assert len(executions) == 2


class TestGetExecution:
    def test_get_execution_not_found(self, service):
        assert service.get_execution("nonexistent") is None

    def test_get_execution_found(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        found = service.get_execution(execution.id)
        assert found is not None
        assert found.workflow_id == wf.id


class TestListNodeExecutions:
    def test_list_node_executions_empty(self, service):
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

    def test_resolve_none_key(self, service):
        context = {"n1": {"status_code": None}}
        result = service._resolve_variables("${n1.status_code}", context)
        assert result == "${n1.status_code}"

    def test_resolve_non_dict_output(self, service):
        context = {"n1": "plain_string"}
        result = service._resolve_variables("${n1.key}", context)
        assert result == "${n1.key}"

    def test_resolve_node_id_only(self, service):
        context = {"n1": "value"}
        result = service._resolve_variables("${n1}", context)
        assert result == "value"

    def test_resolve_nested_dict(self, service):
        context = {"n1": {"a": {"b": "deep"}}}
        result = service._resolve_variables({"outer": {"inner": "${n1.a}"}}, context)
        assert result["outer"]["inner"] == "{'b': 'deep'}"

    def test_resolve_list_of_dicts(self, service):
        context = {"n1": {"val": 10}}
        result = service._resolve_variables([{"k": "${n1.val}"}], context)
        assert result[0]["k"] == "10"

    def test_resolve_bool_value(self, service):
        assert service._resolve_variables(True, {}) is True

    def test_resolve_missing_node_no_key(self, service):
        context = {}
        result = service._resolve_variables("${missing}", context)
        assert result == "{}"


class TestExecuteNode:
    @pytest.mark.asyncio
    async def test_execute_node_no_executor(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.END,
            name="end", config={}, position_x=0, position_y=0,
        )
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {}):
            result = await service._execute_node(execution.id, node, {}, [], {})
        assert result == ("n1", False, {})

    @pytest.mark.asyncio
    async def test_execute_node_success(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.TRIGGER_CRON,
            name="trigger", config={"cron": "* * * * *"}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": {"fired": True}, "error": None}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.TRIGGER_CRON: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], {})
        assert result == ("n1", True, {"fired": True})

    @pytest.mark.asyncio
    async def test_execute_node_failure(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.ACTION_SHELL,
            name="shell", config={"command": "bad_cmd"}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": False, "output": {}, "error": "command not found"}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.ACTION_SHELL: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], {})
        assert result == ("n1", False, {})

    @pytest.mark.asyncio
    async def test_execute_node_exception(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.ACTION_SHELL,
            name="shell", config={}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.side_effect = RuntimeError("boom")
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.ACTION_SHELL: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], {})
        assert result == ("n1", False, {})

    @pytest.mark.asyncio
    async def test_execute_node_condition_true(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.CONDITION,
            name="cond", config={"expression": "1 == 1"}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": {"branch": "true"}, "error": None}
        condition_results = {}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.CONDITION: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], condition_results)
        assert condition_results["n1"] is True

    @pytest.mark.asyncio
    async def test_execute_node_condition_false(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.CONDITION,
            name="cond", config={"expression": "1 != 1"}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": {"branch": "false"}, "error": None}
        condition_results = {}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.CONDITION: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], condition_results)
        assert condition_results["n1"] is False

    @pytest.mark.asyncio
    async def test_execute_node_condition_non_dict_output(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        node = WorkflowNode(
            id="n1", workflow_id=wf.id, node_type=NodeType.CONDITION,
            name="cond", config={}, position_x=0, position_y=0,
        )
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": "not_a_dict", "error": None}
        condition_results = {}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.CONDITION: mock_executor}):
            result = await service._execute_node(execution.id, node, {}, [], condition_results)
        assert condition_results["n1"] is False


class TestRunWorkflowAsync:
    @pytest.mark.asyncio
    async def test_run_empty_workflow(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock) as mock_run:
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.SUCCESS
        assert found.duration_seconds == 0.0

    @pytest.mark.asyncio
    async def test_run_workflow_not_found(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        await service._run_workflow_async(execution.id, "nonexistent-id")
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.FAILED
        assert "not found" in found.error_message

    @pytest.mark.asyncio
    async def test_run_workflow_with_cycle(self, service):
        data = WorkflowCreate(
            name="cyclic", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t1", "config": {}},
                {"id": "n2", "node_type": "trigger_cron", "name": "t2", "config": {}},
            ],
            edges=[
                {"source_node_id": "n1", "target_node_id": "n2"},
                {"source_node_id": "n2", "target_node_id": "n1"},
            ],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.FAILED
        assert "cycles" in found.error_message

    @pytest.mark.asyncio
    async def test_run_workflow_resumes_completed_nodes(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        trigger_exec = AsyncMock()
        trigger_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        shell_exec = AsyncMock()
        shell_exec.execute.return_value = {"success": True, "output": {"result": "ok"}, "error": None}
        registry = {
            NodeType.TRIGGER_CRON: trigger_exec,
            NodeType.ACTION_SHELL: shell_exec,
        }
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", registry):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.SUCCESS
        assert found.success_nodes == 2
        node_execs = service.list_node_executions(execution.id)
        assert len(node_execs) == 2

    @pytest.mark.asyncio
    async def test_run_workflow_paused(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        trigger_exec = AsyncMock()
        trigger_exec.execute.side_effect = lambda c, ctx: (
            service.pause_execution(execution.id),
            {"success": True, "output": {}, "error": None},
        )[1]
        shell_exec = AsyncMock()
        shell_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        registry = {
            NodeType.TRIGGER_CRON: trigger_exec,
            NodeType.ACTION_SHELL: shell_exec,
        }
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", registry):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.PAUSED

    @pytest.mark.asyncio
    async def test_run_workflow_success(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[{"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": {"fired": True}, "error": None}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.TRIGGER_CRON: mock_executor}):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.SUCCESS
        assert found.success_nodes == 1
        assert found.failed_nodes == 0

    @pytest.mark.asyncio
    async def test_run_workflow_node_failure(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[{"id": "n1", "node_type": "action_shell", "name": "a", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": False, "output": {}, "error": "fail"}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.ACTION_SHELL: mock_executor}):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.FAILED
        assert found.failed_nodes == 1

    @pytest.mark.asyncio
    async def test_run_workflow_exception(self, service):
        data = WorkflowCreate(name="wf1", description="", nodes=[], edges=[])
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        with patch.object(service, "get_workflow", side_effect=Exception("db error")):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_run_workflow_condition_branch(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "condition", "name": "c", "config": {}},
                {"id": "n3", "node_type": "action_shell", "name": "true_action", "config": {}},
                {"id": "n4", "node_type": "action_shell", "name": "false_action", "config": {}},
            ],
            edges=[
                {"source_node_id": "n1", "target_node_id": "n2"},
                {"source_node_id": "n2", "target_node_id": "n3", "label": "true"},
                {"source_node_id": "n2", "target_node_id": "n4", "label": "false"},
            ],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        trigger_exec = AsyncMock()
        trigger_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        cond_exec = AsyncMock()
        cond_exec.execute.return_value = {"success": True, "output": {"branch": "true"}, "error": None}
        shell_exec = AsyncMock()
        shell_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        registry = {
            NodeType.TRIGGER_CRON: trigger_exec,
            NodeType.CONDITION: cond_exec,
            NodeType.ACTION_SHELL: shell_exec,
        }
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", registry):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.SUCCESS
        node_execs = service.list_node_executions(execution.id)
        skipped = [ne for ne in node_execs if ne.status == ExecutionStatus.SKIPPED]
        assert len(skipped) == 1

    @pytest.mark.asyncio
    async def test_run_workflow_downstream_of_failure_skipped(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "action_shell", "name": "fail_node", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "after_fail", "config": {}},
            ],
            edges=[{"source_node_id": "n1", "target_node_id": "n2"}],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        fail_exec = AsyncMock()
        fail_exec.execute.return_value = {"success": False, "output": {}, "error": "fail"}
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.ACTION_SHELL: fail_exec}):
            await service._run_workflow_async(execution.id, wf.id)
        node_execs = service.list_node_executions(execution.id)
        skipped = [ne for ne in node_execs if ne.status == ExecutionStatus.SKIPPED]
        assert len(skipped) == 1

    @pytest.mark.asyncio
    async def test_run_workflow_parallel_nodes(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[
                {"id": "n1", "node_type": "trigger_cron", "name": "t", "config": {}},
                {"id": "n2", "node_type": "action_shell", "name": "a1", "config": {}},
                {"id": "n3", "node_type": "action_shell", "name": "a2", "config": {}},
            ],
            edges=[
                {"source_node_id": "n1", "target_node_id": "n2"},
                {"source_node_id": "n1", "target_node_id": "n3"},
            ],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        trigger_exec = AsyncMock()
        trigger_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        shell_exec = AsyncMock()
        shell_exec.execute.return_value = {"success": True, "output": {}, "error": None}
        registry = {
            NodeType.TRIGGER_CRON: trigger_exec,
            NodeType.ACTION_SHELL: shell_exec,
        }
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", registry):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.SUCCESS
        assert found.success_nodes == 3

    @pytest.mark.asyncio
    async def test_run_workflow_gather_exception(self, service):
        data = WorkflowCreate(
            name="wf1", description="",
            nodes=[{"id": "n1", "node_type": "action_shell", "name": "a", "config": {}}],
            edges=[],
        )
        wf = service.create_workflow(data)
        with patch.object(service, "_run_workflow_async", new_callable=AsyncMock):
            execution = service.execute_workflow(wf.id, TriggerType.CRON)
        mock_executor = AsyncMock()
        mock_executor.execute.side_effect = Exception("executor crashed")
        with patch("app.services.workflow_service.EXECUTOR_REGISTRY", {NodeType.ACTION_SHELL: mock_executor}):
            await service._run_workflow_async(execution.id, wf.id)
        found = service.get_execution(execution.id)
        assert found.status == ExecutionStatus.FAILED
