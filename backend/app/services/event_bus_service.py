from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.core.webhook_handler import (
    verify_gitee_signature,
    verify_github_signature,
    verify_gitlab_signature,
)
from app.models.event_trigger import (
    EventFilterCondition,
    EventFilterGroup,
    EventLog,
    EventRoute,
    EventRouteCreate,
    EventRouteUpdate,
    EventSource,
    EventSourceCreate,
    EventSourceStatus,
    EventSourceType,
    EventStatus,
    EventTransform,
)
from app.services.ssh_account_service import ssh_account_service

_PERSIST_DIR = Path.home() / ".opsv-kits"
_DB_PATH = _PERSIST_DIR / "event_trigger.db"

logger = logging.getLogger(__name__)


class EventBusService:
    def __init__(self):
        self._lock = threading.RLock()
        self._init_db()
        self._bg_tasks: list[asyncio.Task] = []
        self._error_counts: dict[str, int] = {}
        self._start_background_sources()

    def _init_db(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS event_sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    config TEXT DEFAULT '{}',
                    webhook_url TEXT,
                    webhook_secret TEXT,
                    account_alias TEXT,
                    status TEXT DEFAULT 'enabled',
                    description TEXT,
                    last_event_at TEXT,
                    event_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS event_routes (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    filter_group TEXT,
                    transforms TEXT DEFAULT '[]',
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (source_id) REFERENCES event_sources(id)
                );

                CREATE TABLE IF NOT EXISTS event_logs (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    raw_data TEXT DEFAULT '{}',
                    filtered INTEGER DEFAULT 0,
                    matched_routes TEXT DEFAULT '[]',
                    triggered_workflows TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    received_at TEXT
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(_DB_PATH))

    def _start_background_sources(self) -> None:
        try:
            sources = self.list_sources()
            for source in sources:
                if source.status != EventSourceStatus.ENABLED:
                    continue
                if source.source_type == EventSourceType.FILE_WATCH:
                    try:
                        loop = asyncio.get_running_loop()
                        self._bg_tasks.append(loop.create_task(self._start_file_watcher(source)))
                    except RuntimeError:
                        thread = threading.Thread(
                            target=lambda: asyncio.run(self._start_file_watcher(source)),
                            daemon=True,
                        )
                        thread.start()
                elif source.source_type == EventSourceType.SYSTEM_METRIC:
                    try:
                        loop = asyncio.get_running_loop()
                        self._bg_tasks.append(loop.create_task(self._start_metric_watcher(source)))
                    except RuntimeError:
                        thread = threading.Thread(
                            target=lambda: asyncio.run(self._start_metric_watcher(source)),
                            daemon=True,
                        )
                        thread.start()
        except Exception as e:
            logger.error("Failed to start background sources: %s", e)

    def _row_to_event_source(self, row: dict) -> EventSource:
        config = row.get("config")
        return EventSource(
            id=row["id"],
            name=row["name"],
            source_type=EventSourceType(row["source_type"]),
            config=json.loads(config) if config else {},
            webhook_url=row.get("webhook_url"),
            webhook_secret=row.get("webhook_secret"),
            account_alias=row.get("account_alias"),
            status=EventSourceStatus(row.get("status", "enabled")),
            description=row.get("description"),
            last_event_at=datetime.fromisoformat(row["last_event_at"]) if row.get("last_event_at") else None,
            event_count=row.get("event_count", 0),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
        )

    def _row_to_event_route(self, row: dict) -> EventRoute:
        fg = row.get("filter_group")
        transforms_raw = row.get("transforms")
        return EventRoute(
            id=row["id"],
            source_id=row["source_id"],
            workflow_id=row["workflow_id"],
            filter_group=EventFilterGroup.model_validate(json.loads(fg)) if fg else None,
            transforms=[EventTransform.model_validate(t) for t in json.loads(transforms_raw)] if transforms_raw else [],
            enabled=bool(row.get("enabled", 1)),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
        )

    def _row_to_event_log(self, row: dict) -> EventLog:
        raw = row.get("raw_data")
        mr = row.get("matched_routes")
        tw = row.get("triggered_workflows")
        return EventLog(
            id=row["id"],
            source_id=row["source_id"],
            source_name=row["source_name"],
            event_type=row["event_type"],
            raw_data=json.loads(raw) if raw else {},
            filtered=bool(row.get("filtered", 0)),
            matched_routes=json.loads(mr) if mr else [],
            triggered_workflows=json.loads(tw) if tw else [],
            status=EventStatus(row.get("status", "pending")),
            error_message=row.get("error_message"),
            received_at=datetime.fromisoformat(row["received_at"]) if row.get("received_at") else datetime.now(),
        )

    def list_sources(self) -> list[EventSource]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM event_sources ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_event_source(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_source(self, source_id: str) -> Optional[EventSource]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM event_sources WHERE id = ?", (source_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_event_source(dict(zip([c[0] for c in cursor.description], row)))
                return None

    def create_source(self, data: EventSourceCreate) -> EventSource:
        with self._lock:
            source_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            webhook_url = None
            if data.source_type == EventSourceType.WEBHOOK:
                webhook_url = f"/api/event-trigger/webhook/{source_id}"
            source = EventSource(
                id=source_id,
                name=data.name,
                source_type=data.source_type,
                config=data.config,
                webhook_url=webhook_url,
                webhook_secret=data.webhook_secret,
                account_alias=data.account_alias,
                status=data.status,
                description=data.description,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO event_sources (id, name, source_type, config, webhook_url,
                        webhook_secret, account_alias, status, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.id, source.name, source.source_type.value,
                        json.dumps(source.config), source.webhook_url,
                        source.webhook_secret, source.account_alias,
                        source.status.value, source.description, now, now,
                    ),
                )
            if source.status == EventSourceStatus.ENABLED:
                if source.source_type == EventSourceType.FILE_WATCH:
                    try:
                        loop = asyncio.get_running_loop()
                        self._bg_tasks.append(loop.create_task(self._start_file_watcher(source)))
                    except RuntimeError:
                        thread = threading.Thread(
                            target=lambda: asyncio.run(self._start_file_watcher(source)),
                            daemon=True,
                        )
                        thread.start()
                elif source.source_type == EventSourceType.SYSTEM_METRIC:
                    try:
                        loop = asyncio.get_running_loop()
                        self._bg_tasks.append(loop.create_task(self._start_metric_watcher(source)))
                    except RuntimeError:
                        thread = threading.Thread(
                            target=lambda: asyncio.run(self._start_metric_watcher(source)),
                            daemon=True,
                        )
                        thread.start()
            return source

    def update_source(self, source_id: str, data: EventSourceUpdate) -> EventSource:
        with self._lock:
            existing = self.get_source(source_id)
            if not existing:
                raise ValueError(f"Event source '{source_id}' not found")
            updates = data.model_dump(exclude_unset=True)
            if not updates:
                return existing
            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "config" and value is not None:
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value.value if hasattr(value, "value") else value)
            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(source_id)
            with self._conn() as conn:
                conn.execute(
                    f"UPDATE event_sources SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )
            return self.get_source(source_id)

    def delete_source(self, source_id: str) -> None:
        with self._lock:
            existing = self.get_source(source_id)
            if not existing:
                raise ValueError(f"Event source '{source_id}' not found")
            with self._conn() as conn:
                conn.execute("DELETE FROM event_routes WHERE source_id = ?", (source_id,))
                conn.execute("DELETE FROM event_sources WHERE id = ?", (source_id,))

    def list_routes(self, source_id: str = None) -> list[EventRoute]:
        with self._lock:
            with self._conn() as conn:
                if source_id:
                    cursor = conn.execute(
                        "SELECT * FROM event_routes WHERE source_id = ? ORDER BY created_at DESC",
                        (source_id,),
                    )
                else:
                    cursor = conn.execute("SELECT * FROM event_routes ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_event_route(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def create_route(self, data: EventRouteCreate) -> EventRoute:
        with self._lock:
            route_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            fg_json = json.dumps(data.filter_group.model_dump()) if data.filter_group else None
            transforms_json = json.dumps([t.model_dump() for t in data.transforms]) if data.transforms else "[]"
            route = EventRoute(
                id=route_id,
                source_id=data.source_id,
                workflow_id=data.workflow_id,
                filter_group=data.filter_group,
                transforms=data.transforms,
                enabled=data.enabled,
                created_at=datetime.fromisoformat(now),
            )
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO event_routes (id, source_id, workflow_id, filter_group,
                        transforms, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (route.id, route.source_id, route.workflow_id, fg_json, transforms_json, int(route.enabled), now),
                )
            return route

    def update_route(self, route_id: str, data: EventRouteUpdate) -> EventRoute:
        with self._lock:
            routes = self.list_routes()
            existing = next((r for r in routes if r.id == route_id), None)
            if not existing:
                raise ValueError(f"Event route '{route_id}' not found")
            updates = data.model_dump(exclude_unset=True)
            if not updates:
                return existing
            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "filter_group" and value is not None:
                    value = json.dumps(value)
                elif key == "transforms" and value is not None:
                    value = json.dumps(value)
                elif key == "enabled" and value is not None:
                    value = int(value)
                set_clauses.append(f"{key} = ?")
                params.append(value)
            params.append(route_id)
            with self._conn() as conn:
                conn.execute(
                    f"UPDATE event_routes SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )
            routes = self.list_routes()
            return next((r for r in routes if r.id == route_id), existing)

    def delete_route(self, route_id: str) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute("DELETE FROM event_routes WHERE id = ?", (route_id,))

    async def receive_webhook(self, source_id: str, headers: dict, body: bytes) -> EventLog:
        source = self.get_source(source_id)
        if not source:
            raise ValueError(f"Event source '{source_id}' not found")
        if source.source_type != EventSourceType.WEBHOOK:
            raise ValueError(f"Event source '{source_id}' is not a webhook type")
        if source.webhook_secret:
            platform = self._detect_platform(headers)
            if platform == "github":
                signature = headers.get("X-Hub-Signature-256", "")
                if not verify_github_signature(body, signature, source.webhook_secret):
                    raise ValueError("GitHub webhook signature verification failed")
            elif platform == "gitlab":
                token = headers.get("X-Gitlab-Token", "")
                if not verify_gitlab_signature(body, token, source.webhook_secret):
                    raise ValueError("GitLab webhook token verification failed")
            elif platform == "gitee":
                password = headers.get("X-Gitee-Token", "")
                if not verify_gitee_signature(body, password, source.webhook_secret):
                    raise ValueError("Gitee webhook token verification failed")
        parsed = self._parse_webhook_event(headers, body)
        event_type = parsed.get("event_type", "unknown")
        event_log = self._create_event_log(source_id, source.name, event_type, parsed)
        await self._process_event(event_log)
        return event_log

    async def receive_event(self, source_id: str, event_type: str, data: dict) -> EventLog:
        source = self.get_source(source_id)
        if not source:
            raise ValueError(f"Event source '{source_id}' not found")
        event_log = self._create_event_log(source_id, source.name, event_type, data)
        await self._process_event(event_log)
        return event_log

    def _create_event_log(self, source_id: str, source_name: str, event_type: str, data: dict) -> EventLog:
        with self._lock:
            log_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            event_log = EventLog(
                id=log_id,
                source_id=source_id,
                source_name=source_name,
                event_type=event_type,
                raw_data=data,
                status=EventStatus.PENDING,
                received_at=datetime.fromisoformat(now),
            )
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO event_logs (id, source_id, source_name, event_type, raw_data,
                        status, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_log.id, event_log.source_id, event_log.source_name,
                        event_log.event_type, json.dumps(event_log.raw_data),
                        event_log.status.value, now,
                    ),
                )
                conn.execute(
                    "UPDATE event_sources SET last_event_at = ?, event_count = event_count + 1 WHERE id = ?",
                    (now, source_id),
                )
            return event_log

    def list_event_logs(
        self,
        source_id: str = None,
        event_type: str = None,
        status: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EventLog]:
        with self._lock:
            with self._conn() as conn:
                conditions = []
                params = []
                if source_id:
                    conditions.append("source_id = ?")
                    params.append(source_id)
                if event_type:
                    conditions.append("event_type = ?")
                    params.append(event_type)
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                cursor = conn.execute(
                    f"SELECT * FROM event_logs {where} ORDER BY received_at DESC LIMIT ? OFFSET ?",
                    params + [limit, offset],
                )
                rows = cursor.fetchall()
                return [self._row_to_event_log(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    async def replay_event(self, log_id: str) -> EventLog:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM event_logs WHERE id = ?", (log_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"Event log '{log_id}' not found")
                original = self._row_to_event_log(dict(zip([c[0] for c in cursor.description], row)))
        new_log = self._create_event_log(original.source_id, original.source_name, original.event_type, original.raw_data)
        await self._process_event(new_log)
        return new_log

    async def _process_event(self, event_log: EventLog) -> None:
        from app.services.workflow_service import workflow_service
        from app.models.workflow import TriggerType

        routes = self.list_routes(source_id=event_log.source_id)
        enabled_routes = [r for r in routes if r.enabled]
        matched_route_ids: list[str] = []
        triggered_workflow_ids: list[str] = []
        errors: list[str] = []

        for route in enabled_routes:
            try:
                if route.filter_group:
                    if not self._apply_filter(event_log.raw_data, route.filter_group):
                        continue
                matched_route_ids.append(route.id)
                transformed_data = self._apply_transforms(event_log.raw_data, route.transforms)
                workflow_service.execute_workflow(
                    route.workflow_id,
                    trigger_type=TriggerType.EVENT,
                    trigger_source=event_log.id,
                )
                triggered_workflow_ids.append(route.workflow_id)
            except Exception as e:
                errors.append(f"Route {route.id}: {str(e)}")
                logger.error("Error processing route %s: %s", route.id, e)

        new_status = EventStatus.TRIGGERED if triggered_workflow_ids else (EventStatus.IGNORED if not matched_route_ids else EventStatus.MATCHED)
        if errors and not triggered_workflow_ids:
            new_status = EventStatus.ERROR

        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE event_logs SET filtered = ?, matched_routes = ?, triggered_workflows = ?,
                        status = ?, error_message = ? WHERE id = ?
                    """,
                    (
                        int(bool(matched_route_ids)),
                        json.dumps(matched_route_ids),
                        json.dumps(triggered_workflow_ids),
                        new_status.value,
                        "; ".join(errors) if errors else None,
                        event_log.id,
                    ),
                )

    def _apply_filter(self, data: dict, filter_group: EventFilterGroup) -> bool:
        results = []
        for condition in filter_group.conditions:
            field_value = self._get_field_value(data, condition.field)
            result = self._evaluate_condition(field_value, condition.operator, condition.value)
            results.append(result)

        if filter_group.logic == "and":
            return all(results) if results else False
        elif filter_group.logic == "or":
            return any(results) if results else False
        elif filter_group.logic == "not":
            return not any(results) if results else True
        return all(results) if results else False

    def _get_field_value(self, data: dict, field_path: str) -> Any:
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else None
            else:
                return None
        return current

    def _evaluate_condition(self, field_value: Any, operator: str, expected: str) -> bool:
        if field_value is None:
            return False
        str_value = str(field_value)
        if operator == "equals":
            return str_value == expected
        elif operator == "not_equals":
            return str_value != expected
        elif operator == "contains":
            return expected in str_value
        elif operator == "regex":
            try:
                return bool(re.search(expected, str_value))
            except re.error:
                return False
        return False

    def _apply_transforms(self, data: dict, transforms: list[EventTransform]) -> dict:
        result = dict(data)
        for transform in transforms:
            source_value = self._get_field_value(data, transform.source_field)
            if source_value is not None:
                if transform.template:
                    try:
                        target_value = transform.template.replace("{{value}}", str(source_value))
                    except Exception:
                        target_value = str(source_value)
                else:
                    target_value = source_value
                parts = transform.target_field.split(".")
                current = result
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = target_value
        return result

    def _detect_platform(self, headers: dict) -> str:
        if "X-GitHub-Event" in headers:
            return "github"
        elif "X-Gitlab-Event" in headers:
            return "gitlab"
        elif "X-Gitee-Event" in headers:
            return "gitee"
        return "unknown"

    def _parse_webhook_event(self, headers: dict, body: bytes) -> dict:
        platform = self._detect_platform(headers)
        if platform == "github":
            return self._parse_github_event(headers, body)
        elif platform == "gitlab":
            return self._parse_gitlab_event(headers, body)
        elif platform == "gitee":
            return self._parse_gitee_event(headers, body)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw_body": body.decode("utf-8", errors="replace")}

    def _parse_github_event(self, headers: dict, body: bytes) -> dict:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {"event_type": "unknown", "platform": "github"}
        event_type = headers.get("X-GitHub-Event", "unknown")
        branch = None
        tag = None
        commits: list[dict] = []
        pusher = None
        repository = None
        repo_info = data.get("repository")
        if repo_info:
            repository = repo_info.get("full_name")
        if event_type == "push":
            ref = data.get("ref", "")
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
            elif ref.startswith("refs/tags/"):
                tag = ref[len("refs/tags/"):]
            commits = data.get("commits", [])
            pusher_info = data.get("pusher")
            if pusher_info:
                pusher = pusher_info.get("name")
        elif event_type == "pull_request":
            pr = data.get("pull_request", {})
            action = data.get("action", "")
            event_type = f"pull_request.{action}"
            branch = pr.get("base", {}).get("ref")
            pusher = pr.get("user", {}).get("login")
        else:
            sender = data.get("sender")
            if sender:
                pusher = sender.get("login")
        return {
            "platform": "github",
            "event_type": event_type,
            "branch": branch,
            "tag": tag,
            "commits": commits,
            "pusher": pusher,
            "repository": repository,
            "payload": data,
        }

    def _parse_gitlab_event(self, headers: dict, body: bytes) -> dict:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {"event_type": "unknown", "platform": "gitlab"}
        event_type = headers.get("X-Gitlab-Event", "unknown")
        branch = None
        tag = None
        commits: list[dict] = []
        pusher = None
        repository = None
        repo_info = data.get("project")
        if repo_info:
            repository = repo_info.get("path_with_namespace")
        if event_type == "Push Hook":
            ref = data.get("ref", "")
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
            elif ref.startswith("refs/tags/"):
                tag = ref[len("refs/tags/"):]
            commits = data.get("commits", [])
            pusher = data.get("user_name")
        elif event_type == "Merge Request Hook":
            mr = data.get("object_attributes", {})
            action = mr.get("action", "")
            event_type = f"merge_request.{action}"
            branch = mr.get("target_branch")
            pusher = data.get("user", {}).get("name")
        else:
            pusher = data.get("user_name")
        return {
            "platform": "gitlab",
            "event_type": event_type,
            "branch": branch,
            "tag": tag,
            "commits": commits,
            "pusher": pusher,
            "repository": repository,
            "payload": data,
        }

    def _parse_gitee_event(self, headers: dict, body: bytes) -> dict:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return {"event_type": "unknown", "platform": "gitee"}
        event_type = headers.get("X-Gitee-Event", "unknown")
        branch = None
        tag = None
        commits: list[dict] = []
        pusher = None
        repository = None
        repo_info = data.get("repository")
        if repo_info:
            repository = repo_info.get("full_name") or repo_info.get("path_with_namespace")
        if event_type == "Push Hook":
            ref = data.get("ref", "")
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
            elif ref.startswith("refs/tags/"):
                tag = ref[len("refs/tags/"):]
            commits = data.get("commits", [])
            pusher = data.get("user_name")
        elif event_type == "Merge Request Hook":
            mr = data.get("merge_request", data.get("object_attributes", {}))
            action = mr.get("action", data.get("action", ""))
            event_type = f"merge_request.{action}"
            branch = mr.get("target_branch")
            pusher = data.get("user", {}).get("name") or data.get("user_name")
        else:
            pusher = data.get("user_name")
        return {
            "platform": "gitee",
            "event_type": event_type,
            "branch": branch,
            "tag": tag,
            "commits": commits,
            "pusher": pusher,
            "repository": repository,
            "payload": data,
        }

    def _verify_webhook_signature(self, body: bytes, signature: str, secret: str, platform: str) -> bool:
        if platform == "github":
            return verify_github_signature(body, signature, secret)
        elif platform == "gitlab":
            return verify_gitlab_signature(body, signature, secret)
        elif platform == "gitee":
            return verify_gitee_signature(body, signature, secret)
        return False

    async def _start_file_watcher(self, source: EventSource) -> None:
        config = source.config
        path = config.get("path", "")
        events = config.get("events", ["create", "modify", "delete"])
        interval = config.get("interval", 30)
        alias = source.account_alias

        if not path or not alias:
            logger.warning("File watcher source %s missing path or account_alias", source.id)
            return

        previous_listing: dict[str, float] = {}

        while True:
            try:
                await asyncio.sleep(interval)
                current_source = self.get_source(source.id)
                if not current_source or current_source.status != EventSourceStatus.ENABLED:
                    break

                code, stdout, _ = self._exec_ssh(alias, f"find '{path}' -type f -printf '%p|%T@\\n' 2>/dev/null || echo ''", 15)
                current_listing: dict[str, float] = {}
                if code == 0 and stdout:
                    for line in stdout.strip().split("\n"):
                        if "|" not in line:
                            continue
                        parts = line.rsplit("|", 1)
                        if len(parts) == 2:
                            try:
                                current_listing[parts[0]] = float(parts[1])
                            except ValueError:
                                current_listing[parts[0]] = 0.0

                if previous_listing:
                    changes = self._detect_file_changes(previous_listing, current_listing, events)
                    for change_type, file_path in changes:
                        await self.receive_event(
                            source.id,
                            f"file_{change_type}",
                            {"path": file_path, "change_type": change_type, "watch_path": path},
                        )

                previous_listing = current_listing
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_key = f"file_watch:{source.id}"
                self._error_counts[err_key] = self._error_counts.get(err_key, 0) + 1
                err_count = self._error_counts[err_key]
                if err_count <= 3:
                    logger.error("File watcher error for source %s: %s", source.id, e)
                elif err_count == 4:
                    logger.warning("File watcher errors for source %s will be suppressed", source.id)
                await asyncio.sleep(interval)

    def _detect_file_changes(
        self,
        previous: dict[str, float],
        current: dict[str, float],
        watch_events: list[str],
    ) -> list[tuple[str, str]]:
        changes: list[tuple[str, str]] = []
        prev_set = set(previous.keys())
        curr_set = set(current.keys())

        if "create" in watch_events:
            for f in curr_set - prev_set:
                changes.append(("create", f))
        if "delete" in watch_events:
            for f in prev_set - curr_set:
                changes.append(("delete", f))
        if "modify" in watch_events:
            for f in prev_set & curr_set:
                if previous[f] != current[f]:
                    changes.append(("modify", f))
        return changes

    async def _start_metric_watcher(self, source: EventSource) -> None:
        config = source.config
        metric = config.get("metric", "cpu")
        threshold = config.get("threshold", 90.0)
        operator = config.get("operator", "gt")
        interval = config.get("interval", 60)
        alias = source.account_alias

        if not alias:
            logger.warning("Metric watcher source %s missing account_alias", source.id)
            return

        while True:
            try:
                await asyncio.sleep(interval)
                current_source = self.get_source(source.id)
                if not current_source or current_source.status != EventSourceStatus.ENABLED:
                    break

                value = await self._get_metric_value(alias, metric)
                if value is not None and self._compare_threshold(value, threshold, operator):
                    await self.receive_event(
                        source.id,
                        f"metric_{metric}_alert",
                        {
                            "metric": metric,
                            "current_value": value,
                            "threshold": threshold,
                            "operator": operator,
                        },
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Metric watcher error for source %s: %s", source.id, e)
                await asyncio.sleep(interval)

    async def _get_metric_value(self, alias: str, metric: str) -> Optional[float]:
        from app.services.monitor_service import monitor_service

        loop = asyncio.get_event_loop()
        if metric == "cpu":
            result = await loop.run_in_executor(None, monitor_service.get_cpu_percent, alias)
            return result.get("usage_percent")
        elif metric == "memory":
            result = await loop.run_in_executor(None, monitor_service.get_memory_stats, alias)
            return result.get("usage_percent")
        elif metric == "disk":
            result = await loop.run_in_executor(None, monitor_service.get_disk_stats, alias)
            if result and isinstance(result, list):
                max_usage = max((d.get("usage_percent", 0) for d in result), default=0)
                return max_usage
        return None

    def _compare_threshold(self, value: float, threshold: float, operator: str) -> bool:
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        return False

    def _exec_ssh(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
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


event_bus_service = EventBusService()
