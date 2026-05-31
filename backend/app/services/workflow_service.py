from __future__ import annotations

import asyncio
import copy
import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import networkx as nx

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
    WorkflowTemplate,
    WorkflowUpdate,
    WorkflowVersion,
)
from app.services.ssh_account_service import ssh_account_service
from app.services.workflow_executors import EXECUTOR_REGISTRY

_PERSIST_DIR = Path.home() / ".opsv-kits"
_DB_PATH = _PERSIST_DIR / "workflow.db"

_TEMPLATES = [
    WorkflowTemplate(
        id="service-health-check",
        name="服务健康检查与自动重启",
        description="定时检查服务健康状态，失败时自动重启服务",
        category="monitoring",
        icon="heartbeat",
        nodes=[
            {"id": "n1", "node_type": "trigger_cron", "name": "定时触发", "config": {"cron": "*/5 * * * *"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "action_http", "name": "健康检查", "config": {"url": "http://localhost:8080/health", "method": "GET"}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "condition", "name": "检查结果", "config": {"expression": "${n2.status_code} != 200"}, "position_x": 500, "position_y": 100},
            {"id": "n4", "node_type": "action_shell", "name": "自动重启", "config": {"command": "systemctl restart myapp", "account_alias": ""}, "position_x": 700, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4", "label": "true"},
        ],
    ),
    WorkflowTemplate(
        id="log-rotation",
        name="日志轮转与归档",
        description="定期查找旧日志文件，压缩归档后删除原文件",
        category="maintenance",
        icon="file-text",
        nodes=[
            {"id": "n1", "node_type": "trigger_cron", "name": "定时触发", "config": {"cron": "0 0 * * *"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "action_shell", "name": "查找旧日志", "config": {"command": "find /var/log -name '*.log' -mtime +7", "account_alias": ""}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "action_shell", "name": "压缩归档", "config": {"command": "cd /var/log && tar -czf /var/log/archive/logs_$(date +%Y%m%d).tar.gz $(find . -name '*.log' -mtime +7)", "account_alias": ""}, "position_x": 500, "position_y": 100},
            {"id": "n4", "node_type": "action_shell", "name": "删除原文件", "config": {"command": "find /var/log -name '*.log' -mtime +7 -delete", "account_alias": ""}, "position_x": 700, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4"},
        ],
    ),
    WorkflowTemplate(
        id="git-sync-deploy",
        name="Git 仓库同步与自动部署",
        description="通过 Webhook 触发代码拉取、构建和部署",
        category="deployment",
        icon="git-branch",
        nodes=[
            {"id": "n1", "node_type": "trigger_webhook", "name": "Webhook 触发", "config": {"path": "/webhook/deploy"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "action_shell", "name": "拉取代码", "config": {"command": "cd /var/www/myapp && git pull origin main", "account_alias": ""}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "action_shell", "name": "构建项目", "config": {"command": "cd /var/www/myapp && npm run build", "account_alias": ""}, "position_x": 500, "position_y": 100},
            {"id": "n4", "node_type": "action_shell", "name": "重启服务", "config": {"command": "systemctl restart myapp", "account_alias": ""}, "position_x": 700, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4"},
        ],
    ),
    WorkflowTemplate(
        id="db-backup-cleanup",
        name="数据库定时备份与清理",
        description="定时备份数据库，上传至远程存储并清理旧备份",
        category="backup",
        icon="database",
        nodes=[
            {"id": "n1", "node_type": "trigger_cron", "name": "定时触发", "config": {"cron": "0 2 * * *"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "action_shell", "name": "数据库备份", "config": {"command": "mysqldump -u root mydb > /backup/mydb_$(date +%Y%m%d).sql", "account_alias": ""}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "action_shell", "name": "上传存储", "config": {"command": "rclone copy /backup/ remote:backup/", "account_alias": ""}, "position_x": 500, "position_y": 100},
            {"id": "n4", "node_type": "action_shell", "name": "清理旧备份", "config": {"command": "find /backup -name '*.sql' -mtime +7 -delete", "account_alias": ""}, "position_x": 700, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4"},
        ],
    ),
    WorkflowTemplate(
        id="ssl-check-renew",
        name="SSL 证书到期检查与续期提醒",
        description="定期检查 SSL 证书有效期，即将过期时发送提醒",
        category="security",
        icon="shield",
        nodes=[
            {"id": "n1", "node_type": "trigger_cron", "name": "定时触发", "config": {"cron": "0 0 1 * *"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "action_shell", "name": "检查证书", "config": {"command": "echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -enddate", "account_alias": ""}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "condition", "name": "是否即将过期", "config": {"expression": "${n2.days_remaining} < 30"}, "position_x": 500, "position_y": 100},
            {"id": "n4", "node_type": "notify", "name": "发送提醒", "config": {"channel": "webhook", "message": "SSL 证书即将过期，请及时续期", "recipients": []}, "position_x": 700, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n4", "label": "true"},
        ],
    ),
    WorkflowTemplate(
        id="batch-server-ops",
        name="多服务器批量操作",
        description="定时在多台服务器上执行批量操作",
        category="operations",
        icon="server",
        nodes=[
            {"id": "n1", "node_type": "trigger_cron", "name": "定时触发", "config": {"cron": "0 3 * * *"}, "position_x": 100, "position_y": 100},
            {"id": "n2", "node_type": "loop", "name": "遍历服务器", "config": {"loop_type": "iterate", "items": ["server1", "server2", "server3"], "body_node_ids": ["n3"]}, "position_x": 300, "position_y": 100},
            {"id": "n3", "node_type": "action_shell", "name": "执行操作", "config": {"command": "uptime && df -h", "account_alias": ""}, "position_x": 500, "position_y": 100},
        ],
        edges=[
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
        ],
    ),
]


class WorkflowService:
    def __init__(self):
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    version INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_nodes (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    config TEXT,
                    position_x INTEGER DEFAULT 0,
                    position_y INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_edges (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    source_port TEXT,
                    target_port TEXT,
                    label TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_versions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    snapshot TEXT,
                    change_note TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT,
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    trigger_type TEXT,
                    trigger_source TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    total_nodes INTEGER DEFAULT 0,
                    success_nodes INTEGER DEFAULT 0,
                    failed_nodes INTEGER DEFAULT 0,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS node_executions (
                    id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_name TEXT,
                    node_type TEXT,
                    status TEXT DEFAULT 'pending',
                    input_data TEXT,
                    output_data TEXT,
                    error_message TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(_DB_PATH))

    def _row_to_workflow_node(self, row: dict) -> WorkflowNode:
        config = row.get("config")
        return WorkflowNode(
            id=row["id"],
            workflow_id=row["workflow_id"],
            node_type=NodeType(row["node_type"]),
            name=row["name"],
            config=json.loads(config) if config else {},
            position_x=row.get("position_x", 0),
            position_y=row.get("position_y", 0),
            description=row.get("description"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )

    def _row_to_workflow_edge(self, row: dict) -> WorkflowEdge:
        return WorkflowEdge(
            id=row["id"],
            workflow_id=row["workflow_id"],
            source_node_id=row["source_node_id"],
            target_node_id=row["target_node_id"],
            source_port=row.get("source_port"),
            target_port=row.get("target_port"),
            label=row.get("label"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
        )

    def _row_to_workflow(self, row: dict, nodes: list[WorkflowNode] = None, edges: list[WorkflowEdge] = None) -> Workflow:
        return Workflow(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            status=WorkflowStatus(row.get("status", "draft")),
            version=row.get("version", 1),
            nodes=nodes or [],
            edges=edges or [],
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )

    def _row_to_workflow_version(self, row: dict) -> WorkflowVersion:
        snapshot = row.get("snapshot")
        return WorkflowVersion(
            id=row["id"],
            workflow_id=row["workflow_id"],
            version=row["version"],
            snapshot=json.loads(snapshot) if snapshot else {},
            change_note=row.get("change_note"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
        )

    def _row_to_workflow_execution(self, row: dict) -> WorkflowExecution:
        return WorkflowExecution(
            id=row["id"],
            workflow_id=row["workflow_id"],
            workflow_name=row.get("workflow_name", ""),
            version=row.get("version", 1),
            status=ExecutionStatus(row.get("status", "pending")),
            trigger_type=TriggerType(row.get("trigger_type", "cron")),
            trigger_source=row.get("trigger_source"),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            duration_seconds=row.get("duration_seconds"),
            total_nodes=row.get("total_nodes", 0),
            success_nodes=row.get("success_nodes", 0),
            failed_nodes=row.get("failed_nodes", 0),
            error_message=row.get("error_message"),
        )

    def _row_to_node_execution(self, row: dict) -> NodeExecution:
        input_data = row.get("input_data")
        output_data = row.get("output_data")
        return NodeExecution(
            id=row["id"],
            execution_id=row["execution_id"],
            node_id=row["node_id"],
            node_name=row.get("node_name", ""),
            node_type=NodeType(row["node_type"]) if row.get("node_type") else NodeType.END,
            status=ExecutionStatus(row.get("status", "pending")),
            input_data=json.loads(input_data) if input_data else None,
            output_data=json.loads(output_data) if output_data else None,
            error_message=row.get("error_message"),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            duration_seconds=row.get("duration_seconds"),
        )

    def _get_workflow_nodes(self, workflow_id: str) -> list[WorkflowNode]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM workflow_nodes WHERE workflow_id = ? ORDER BY created_at", (workflow_id,))
            rows = cursor.fetchall()
            return [self._row_to_workflow_node(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def _get_workflow_edges(self, workflow_id: str) -> list[WorkflowEdge]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM workflow_edges WHERE workflow_id = ? ORDER BY created_at", (workflow_id,))
            rows = cursor.fetchall()
            return [self._row_to_workflow_edge(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def list_workflows(self) -> list[Workflow]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM workflows ORDER BY created_at DESC")
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    wf_dict = dict(zip([c[0] for c in cursor.description], row))
                    nodes = self._get_workflow_nodes(wf_dict["id"])
                    edges = self._get_workflow_edges(wf_dict["id"])
                    results.append(self._row_to_workflow(wf_dict, nodes, edges))
                return results

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                wf_dict = dict(zip([c[0] for c in cursor.description], row))
                nodes = self._get_workflow_nodes(workflow_id)
                edges = self._get_workflow_edges(workflow_id)
                return self._row_to_workflow(wf_dict, nodes, edges)

    def create_workflow(self, data: WorkflowCreate) -> Workflow:
        with self._lock:
            workflow_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO workflows (id, name, description, status, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (workflow_id, data.name, data.description, "draft", 1, now, now),
                )

            id_map = {}
            for node_data in data.nodes:
                old_id = node_data.get("id", str(uuid.uuid4()))
                new_id = str(uuid.uuid4())
                id_map[old_id] = new_id
                node_now = datetime.now().isoformat()
                config = node_data.get("config", {})
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_nodes (id, workflow_id, node_type, name, config, position_x, position_y, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            new_id,
                            workflow_id,
                            node_data.get("node_type", "end"),
                            node_data.get("name", ""),
                            json.dumps(config),
                            node_data.get("position_x", 0),
                            node_data.get("position_y", 0),
                            node_data.get("description"),
                            node_now,
                            node_now,
                        ),
                    )

            for edge_data in data.edges:
                edge_id = str(uuid.uuid4())
                source_id = id_map.get(edge_data.get("source_node_id", ""), edge_data.get("source_node_id", ""))
                target_id = id_map.get(edge_data.get("target_node_id", ""), edge_data.get("target_node_id", ""))
                edge_now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, source_port, target_port, label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            edge_id,
                            workflow_id,
                            source_id,
                            target_id,
                            edge_data.get("source_port"),
                            edge_data.get("target_port"),
                            edge_data.get("label"),
                            edge_now,
                        ),
                    )

            return self.get_workflow(workflow_id)

    def update_workflow(self, workflow_id: str, data: WorkflowUpdate) -> Workflow:
        with self._lock:
            existing = self.get_workflow(workflow_id)
            if not existing:
                raise ValueError(f"Workflow '{workflow_id}' not found")

            updates = data.model_dump(exclude_unset=True)

            nodes_data = updates.pop("nodes", None)
            edges_data = updates.pop("edges", None)

            if updates:
                set_clauses = []
                params = []
                for key, value in updates.items():
                    set_clauses.append(f"{key} = ?")
                    params.append(value.value if hasattr(value, "value") else value)
                set_clauses.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(workflow_id)
                with self._conn() as conn:
                    conn.execute(
                        f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = ?",
                        params,
                    )

            if nodes_data is not None:
                with self._conn() as conn:
                    conn.execute("DELETE FROM workflow_nodes WHERE workflow_id = ?", (workflow_id,))

                id_map = {}
                for node_data in nodes_data:
                    old_id = node_data.get("id", str(uuid.uuid4()))
                    new_id = str(uuid.uuid4())
                    id_map[old_id] = new_id
                    node_now = datetime.now().isoformat()
                    config = node_data.get("config", {})
                    with self._conn() as conn:
                        conn.execute(
                            "INSERT INTO workflow_nodes (id, workflow_id, node_type, name, config, position_x, position_y, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                new_id,
                                workflow_id,
                                node_data.get("node_type", "end"),
                                node_data.get("name", ""),
                                json.dumps(config),
                                node_data.get("position_x", 0),
                                node_data.get("position_y", 0),
                                node_data.get("description"),
                                node_now,
                                node_now,
                            ),
                        )

                if edges_data is None:
                    with self._conn() as conn:
                        conn.execute("DELETE FROM workflow_edges WHERE workflow_id = ?", (workflow_id,))
                    for edge in existing.edges:
                        new_source = id_map.get(edge.source_node_id, edge.source_node_id)
                        new_target = id_map.get(edge.target_node_id, edge.target_node_id)
                        edge_id = str(uuid.uuid4())
                        edge_now = datetime.now().isoformat()
                        with self._conn() as conn:
                            conn.execute(
                                "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, source_port, target_port, label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (edge_id, workflow_id, new_source, new_target, edge.source_port, edge.target_port, edge.label, edge_now),
                            )

            if edges_data is not None:
                with self._conn() as conn:
                    conn.execute("DELETE FROM workflow_edges WHERE workflow_id = ?", (workflow_id,))

                current_nodes = self._get_workflow_nodes(workflow_id)
                node_id_set = {n.id for n in current_nodes}

                for edge_data in edges_data:
                    edge_id = str(uuid.uuid4())
                    source_id = edge_data.get("source_node_id", "")
                    target_id = edge_data.get("target_node_id", "")
                    edge_now = datetime.now().isoformat()
                    with self._conn() as conn:
                        conn.execute(
                            "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, source_port, target_port, label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                edge_id,
                                workflow_id,
                                source_id,
                                target_id,
                                edge_data.get("source_port"),
                                edge_data.get("target_port"),
                                edge_data.get("label"),
                                edge_now,
                            ),
                        )

            return self.get_workflow(workflow_id)

    def delete_workflow(self, workflow_id: str) -> None:
        with self._lock:
            existing = self.get_workflow(workflow_id)
            if not existing:
                raise ValueError(f"Workflow '{workflow_id}' not found")

            with self._conn() as conn:
                cursor = conn.execute("SELECT id FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
                execution_ids = [row[0] for row in cursor.fetchall()]
                for exec_id in execution_ids:
                    conn.execute("DELETE FROM node_executions WHERE execution_id = ?", (exec_id,))

                conn.execute("DELETE FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
                conn.execute("DELETE FROM workflow_versions WHERE workflow_id = ?", (workflow_id,))
                conn.execute("DELETE FROM workflow_edges WHERE workflow_id = ?", (workflow_id,))
                conn.execute("DELETE FROM workflow_nodes WHERE workflow_id = ?", (workflow_id,))
                conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))

    def validate_dag(self, nodes: list[dict], edges: list[dict]) -> dict:
        errors = []
        G = nx.DiGraph()

        for node in nodes:
            node_id = node.get("id", "")
            if not node_id:
                errors.append("Node missing id")
                continue
            G.add_node(node_id)

        for edge in edges:
            source = edge.get("source_node_id", "")
            target = edge.get("target_node_id", "")
            if not source or not target:
                errors.append(f"Edge missing source_node_id or target_node_id")
                continue
            G.add_edge(source, target)

        if not nx.is_directed_acyclic_graph(G):
            errors.append("Graph contains cycles")

        node_ids = {n.get("id", "") for n in nodes}
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source_node_id", ""))
            connected_nodes.add(edge.get("target_node_id", ""))
        isolated = node_ids - connected_nodes
        if isolated and len(node_ids) > 1:
            for iso_id in isolated:
                errors.append(f"Node '{iso_id}' is isolated (no edges)")

        return {"valid": len(errors) == 0, "errors": errors}

    def save_version(self, workflow_id: str, change_note: str = None) -> WorkflowVersion:
        with self._lock:
            workflow = self.get_workflow(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow '{workflow_id}' not found")

            snapshot = {
                "name": workflow.name,
                "description": workflow.description,
                "status": workflow.status.value,
                "nodes": [
                    {
                        "id": n.id,
                        "node_type": n.node_type.value,
                        "name": n.name,
                        "config": n.config,
                        "position_x": n.position_x,
                        "position_y": n.position_y,
                        "description": n.description,
                    }
                    for n in workflow.nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "source_node_id": e.source_node_id,
                        "target_node_id": e.target_node_id,
                        "source_port": e.source_port,
                        "target_port": e.target_port,
                        "label": e.label,
                    }
                    for e in workflow.edges
                ],
            }

            version_id = str(uuid.uuid4())
            new_version = workflow.version + 1
            now = datetime.now().isoformat()

            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO workflow_versions (id, workflow_id, version, snapshot, change_note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (version_id, workflow_id, new_version, json.dumps(snapshot), change_note, now),
                )
                conn.execute(
                    "UPDATE workflows SET version = ?, updated_at = ? WHERE id = ?",
                    (new_version, now, workflow_id),
                )

            return self._row_to_workflow_version({
                "id": version_id,
                "workflow_id": workflow_id,
                "version": new_version,
                "snapshot": json.dumps(snapshot),
                "change_note": change_note,
                "created_at": now,
            })

    def list_versions(self, workflow_id: str) -> list[WorkflowVersion]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM workflow_versions WHERE workflow_id = ? ORDER BY version DESC",
                    (workflow_id,),
                )
                rows = cursor.fetchall()
                return [self._row_to_workflow_version(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def rollback_version(self, workflow_id: str, version: int) -> Workflow:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM workflow_versions WHERE workflow_id = ? AND version = ?",
                    (workflow_id, version),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Version {version} not found for workflow '{workflow_id}'")
                ver_dict = dict(zip([c[0] for c in cursor.description], row))

            snapshot = json.loads(ver_dict["snapshot"]) if isinstance(ver_dict["snapshot"], str) else ver_dict["snapshot"]

            with self._conn() as conn:
                conn.execute("DELETE FROM workflow_nodes WHERE workflow_id = ?", (workflow_id,))
                conn.execute("DELETE FROM workflow_edges WHERE workflow_id = ?", (workflow_id,))

            id_map = {}
            for node_data in snapshot.get("nodes", []):
                old_id = node_data.get("id", str(uuid.uuid4()))
                new_id = str(uuid.uuid4())
                id_map[old_id] = new_id
                node_now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_nodes (id, workflow_id, node_type, name, config, position_x, position_y, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            new_id,
                            workflow_id,
                            node_data.get("node_type", "end"),
                            node_data.get("name", ""),
                            json.dumps(node_data.get("config", {})),
                            node_data.get("position_x", 0),
                            node_data.get("position_y", 0),
                            node_data.get("description"),
                            node_now,
                            node_now,
                        ),
                    )

            for edge_data in snapshot.get("edges", []):
                edge_id = str(uuid.uuid4())
                source_id = id_map.get(edge_data.get("source_node_id", ""), edge_data.get("source_node_id", ""))
                target_id = id_map.get(edge_data.get("target_node_id", ""), edge_data.get("target_node_id", ""))
                edge_now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, source_port, target_port, label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (edge_id, workflow_id, source_id, target_id, edge_data.get("source_port"), edge_data.get("target_port"), edge_data.get("label"), edge_now),
                    )

            now = datetime.now().isoformat()
            with self._conn() as conn:
                conn.execute(
                    "UPDATE workflows SET name = ?, description = ?, status = ?, version = ?, updated_at = ? WHERE id = ?",
                    (snapshot.get("name", ""), snapshot.get("description"), snapshot.get("status", "draft"), version, now, workflow_id),
                )

            return self.get_workflow(workflow_id)

    def export_workflow(self, workflow_id: str) -> dict:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        return {
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "version": workflow.version,
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type.value,
                    "name": n.name,
                    "config": n.config,
                    "position_x": n.position_x,
                    "position_y": n.position_y,
                    "description": n.description,
                }
                for n in workflow.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_node_id": e.source_node_id,
                    "target_node_id": e.target_node_id,
                    "source_port": e.source_port,
                    "target_port": e.target_port,
                    "label": e.label,
                }
                for e in workflow.edges
            ],
        }

    def import_workflow(self, data: dict) -> Workflow:
        with self._lock:
            workflow_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO workflows (id, name, description, status, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (workflow_id, data.get("name", "Imported Workflow"), data.get("description"), "draft", 1, now, now),
                )

            id_map = {}
            for node_data in data.get("nodes", []):
                old_id = node_data.get("id", str(uuid.uuid4()))
                new_id = str(uuid.uuid4())
                id_map[old_id] = new_id
                node_now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_nodes (id, workflow_id, node_type, name, config, position_x, position_y, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            new_id,
                            workflow_id,
                            node_data.get("node_type", "end"),
                            node_data.get("name", ""),
                            json.dumps(node_data.get("config", {})),
                            node_data.get("position_x", 0),
                            node_data.get("position_y", 0),
                            node_data.get("description"),
                            node_now,
                            node_now,
                        ),
                    )

            for edge_data in data.get("edges", []):
                edge_id = str(uuid.uuid4())
                source_id = id_map.get(edge_data.get("source_node_id", ""), edge_data.get("source_node_id", ""))
                target_id = id_map.get(edge_data.get("target_node_id", ""), edge_data.get("target_node_id", ""))
                edge_now = datetime.now().isoformat()
                with self._conn() as conn:
                    conn.execute(
                        "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, source_port, target_port, label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (edge_id, workflow_id, source_id, target_id, edge_data.get("source_port"), edge_data.get("target_port"), edge_data.get("label"), edge_now),
                    )

            return self.get_workflow(workflow_id)

    def list_templates(self) -> list[WorkflowTemplate]:
        return list(_TEMPLATES)

    def create_from_template(self, template_id: str, name: str) -> Workflow:
        template = None
        for t in _TEMPLATES:
            if t.id == template_id:
                template = t
                break
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        data = WorkflowCreate(
            name=name,
            description=template.description,
            nodes=copy.deepcopy(template.nodes),
            edges=copy.deepcopy(template.edges),
        )
        return self.create_workflow(data)

    def execute_workflow(self, workflow_id: str, trigger_type: TriggerType, trigger_source: str = None) -> WorkflowExecution:
        with self._lock:
            workflow = self.get_workflow(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow '{workflow_id}' not found")

            execution_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO workflow_executions (id, workflow_id, workflow_name, version, status, trigger_type, trigger_source, started_at, total_nodes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (execution_id, workflow_id, workflow.name, workflow.version, "pending", trigger_type.value, trigger_source, now, len(workflow.nodes)),
                )

            execution = self._row_to_workflow_execution({
                "id": execution_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow.name,
                "version": workflow.version,
                "status": "pending",
                "trigger_type": trigger_type.value,
                "trigger_source": trigger_source,
                "started_at": now,
                "completed_at": None,
                "duration_seconds": None,
                "total_nodes": len(workflow.nodes),
                "success_nodes": 0,
                "failed_nodes": 0,
                "error_message": None,
            })

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_workflow_async(execution_id, workflow_id))
        except RuntimeError:
            thread = threading.Thread(
                target=lambda: asyncio.run(self._run_workflow_async(execution_id, workflow_id)),
                daemon=True,
            )
            thread.start()

        return execution

    def pause_execution(self, execution_id: str) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE workflow_executions SET status = ? WHERE id = ?",
                    ("paused", execution_id),
                )

    def resume_execution(self, execution_id: str) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE workflow_executions SET status = ? WHERE id = ?",
                    ("running", execution_id),
                )

            cursor = conn.execute("SELECT workflow_id FROM workflow_executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            if row:
                workflow_id = row[0]
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._run_workflow_async(execution_id, workflow_id))
                except RuntimeError:
                    thread = threading.Thread(
                        target=lambda: asyncio.run(self._run_workflow_async(execution_id, workflow_id)),
                        daemon=True,
                    )
                    thread.start()

    def cancel_execution(self, execution_id: str) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE workflow_executions SET status = ? WHERE id = ?",
                    ("cancelled", execution_id),
                )

    def list_executions(self, workflow_id: str = None, limit: int = 50) -> list[WorkflowExecution]:
        with self._lock:
            with self._conn() as conn:
                if workflow_id:
                    cursor = conn.execute(
                        "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
                        (workflow_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM workflow_executions ORDER BY started_at DESC LIMIT ?",
                        (limit,),
                    )
                rows = cursor.fetchall()
                return [self._row_to_workflow_execution(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM workflow_executions WHERE id = ?", (execution_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_workflow_execution(dict(zip([c[0] for c in cursor.description], row)))

    def list_node_executions(self, execution_id: str) -> list[NodeExecution]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM node_executions WHERE execution_id = ? ORDER BY started_at",
                    (execution_id,),
                )
                rows = cursor.fetchall()
                return [self._row_to_node_execution(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def _resolve_variables(self, value, context: dict):
        if isinstance(value, str):
            def replacer(match):
                path = match.group(1)
                parts = path.split(".", 1)
                node_id = parts[0]
                key = parts[1] if len(parts) > 1 else None
                node_output = context.get(node_id, {})
                if key and isinstance(node_output, dict):
                    resolved = node_output.get(key)
                    if resolved is not None:
                        return str(resolved)
                elif node_output is not None and not key:
                    return str(node_output)
                return match.group(0)

            return re.sub(r"\$\{([^}]+)\}", replacer, value)
        elif isinstance(value, dict):
            return {k: self._resolve_variables(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_variables(item, context) for item in value]
        return value

    async def _run_workflow_async(self, execution_id: str, workflow_id: str):
        try:
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE workflow_executions SET status = ? WHERE id = ?",
                        ("running", execution_id),
                    )

            workflow = self.get_workflow(workflow_id)
            if not workflow:
                with self._lock:
                    with self._conn() as conn:
                        conn.execute(
                            "UPDATE workflow_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                            ("failed", f"Workflow '{workflow_id}' not found", datetime.now().isoformat(), execution_id),
                        )
                return

            nodes = workflow.nodes
            edges = workflow.edges

            if not nodes:
                now = datetime.now().isoformat()
                with self._lock:
                    with self._conn() as conn:
                        conn.execute(
                            "UPDATE workflow_executions SET status = ?, completed_at = ?, duration_seconds = ? WHERE id = ?",
                            ("success", now, 0.0, execution_id),
                        )
                return

            G = nx.DiGraph()
            for node in nodes:
                G.add_node(node.id)
            for edge in edges:
                G.add_edge(edge.source_node_id, edge.target_node_id)

            if not nx.is_directed_acyclic_graph(G):
                now = datetime.now().isoformat()
                with self._lock:
                    with self._conn() as conn:
                        conn.execute(
                            "UPDATE workflow_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                            ("failed", "Workflow graph contains cycles", now, execution_id),
                        )
                return

            generations = list(nx.topological_generations(G))
            node_map = {node.id: node for node in nodes}

            context = {
                "_node_map": {
                    node.id: {"node_type": node.node_type.value, "name": node.name, "config": node.config}
                    for node in nodes
                },
                "_executors": EXECUTOR_REGISTRY,
            }

            existing_node_execs = self.list_node_executions(execution_id)
            for ne in existing_node_execs:
                if ne.status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.SKIPPED):
                    context[ne.node_id] = ne.output_data or {}

            condition_results = {}
            failed_nodes = set()
            success_count = 0
            failed_count = 0
            skipped_count = 0

            for generation in generations:
                with self._lock:
                    with self._conn() as conn:
                        cursor = conn.execute("SELECT status FROM workflow_executions WHERE id = ?", (execution_id,))
                        row = cursor.fetchone()
                        current_status = row[0] if row else "cancelled"

                if current_status in ("cancelled", "paused"):
                    if current_status == "paused":
                        return
                    break

                tasks = []
                node_ids_in_gen = []

                for node_id in generation:
                    node = node_map.get(node_id)
                    if not node:
                        continue

                    should_execute = True

                    for edge in edges:
                        if edge.target_node_id == node_id and edge.label:
                            source_result = condition_results.get(edge.source_node_id)
                            if source_result is not None:
                                if edge.label == "true" and not source_result:
                                    should_execute = False
                                    break
                                if edge.label == "false" and source_result:
                                    should_execute = False
                                    break

                    if should_execute:
                        for edge in edges:
                            if edge.target_node_id == node_id and edge.source_node_id in failed_nodes:
                                should_execute = False
                                break

                    existing_executed = False
                    for ne in existing_node_execs:
                        if ne.node_id == node_id and ne.status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.SKIPPED):
                            existing_executed = True
                            break

                    if not should_execute:
                        skipped_count += 1
                        node_exec_id = str(uuid.uuid4())
                        ne_now = datetime.now().isoformat()
                        with self._lock:
                            with self._conn() as conn:
                                conn.execute(
                                    "INSERT INTO node_executions (id, execution_id, node_id, node_name, node_type, status, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (node_exec_id, execution_id, node_id, node.name, node.node_type.value, "skipped", ne_now, ne_now),
                                )
                        continue

                    if existing_executed:
                        continue

                    tasks.append(self._execute_node(execution_id, node, context, edges, condition_results))
                    node_ids_in_gen.append(node_id)

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            failed_count += 1
                        elif result:
                            nid, success, output = result
                            context[nid] = output or {}
                            if success:
                                success_count += 1
                            else:
                                failed_count += 1
                                failed_nodes.add(nid)

            completed = datetime.now().isoformat()
            started_row = None
            with self._lock:
                with self._conn() as conn:
                    cursor = conn.execute("SELECT started_at FROM workflow_executions WHERE id = ?", (execution_id,))
                    started_row = cursor.fetchone()

            duration = 0.0
            if started_row and started_row[0]:
                try:
                    duration = (datetime.fromisoformat(completed) - datetime.fromisoformat(started_row[0])).total_seconds()
                except Exception:
                    pass

            final_status = "success" if failed_count == 0 else "failed"
            error_msg = None
            if failed_count > 0:
                error_msg = f"{failed_count} node(s) failed"

            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE workflow_executions SET status = ?, completed_at = ?, duration_seconds = ?, success_nodes = ?, failed_nodes = ?, error_message = ? WHERE id = ?",
                        (final_status, completed, duration, success_count, failed_count, error_msg, execution_id),
                    )

        except Exception as e:
            now = datetime.now().isoformat()
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE workflow_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                        ("failed", str(e), now, execution_id),
                    )

    async def _execute_node(self, execution_id: str, node: WorkflowNode, context: dict, edges: list[WorkflowEdge], condition_results: dict) -> tuple:
        node_id = node.id
        node_type = node.node_type
        config = self._resolve_variables(copy.deepcopy(node.config), context)

        node_exec_id = str(uuid.uuid4())
        started = datetime.now().isoformat()

        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO node_executions (id, execution_id, node_id, node_name, node_type, status, input_data, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (node_exec_id, execution_id, node_id, node.name, node_type.value, "running", json.dumps(config), started),
                )

        executor = EXECUTOR_REGISTRY.get(node_type)
        if not executor:
            completed = datetime.now().isoformat()
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE node_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                        ("failed", f"No executor for node type: {node_type.value}", completed, node_exec_id),
                    )
            return (node_id, False, {})

        try:
            result = await executor.execute(config, context)
            success = result.get("success", False)
            output = result.get("output", {})
            error = result.get("error")

            completed = datetime.now().isoformat()
            status = "success" if success else "failed"

            if node_type == NodeType.CONDITION:
                branch = output.get("branch", "false") if isinstance(output, dict) else "false"
                condition_results[node_id] = branch == "true"

            duration = 0.0
            try:
                duration = (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds()
            except Exception:
                pass

            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE node_executions SET status = ?, output_data = ?, error_message = ?, completed_at = ?, duration_seconds = ? WHERE id = ?",
                        (status, json.dumps(output) if output else None, error, completed, duration, node_exec_id),
                    )

            return (node_id, success, output)
        except Exception as e:
            completed = datetime.now().isoformat()
            with self._lock:
                with self._conn() as conn:
                    conn.execute(
                        "UPDATE node_executions SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                        ("failed", str(e), completed, node_exec_id),
                    )
            return (node_id, False, {})


workflow_service = WorkflowService()
