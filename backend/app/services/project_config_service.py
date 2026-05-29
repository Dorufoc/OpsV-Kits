from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.project_config import ProjectConfig, ProjectConfigCreate, ProjectConfigUpdate

_PERSIST_DIR = Path.home() / ".opsv-kits"
_PERSIST_PATH = _PERSIST_DIR / "projects.json"


class ProjectConfigService:
    def __init__(self):
        self._projects: dict[str, ProjectConfig] = {}
        self._lock = threading.RLock()
        self._load_from_disk()

    # ── 持久化 ──────────────────────────────────────────────────────

    def _persist_path(self) -> Path:
        return _PERSIST_PATH

    def _load_from_disk(self) -> None:
        path = self._persist_path()
        if not path.is_file():
            return
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            projects_data: list[dict] = data if isinstance(data, list) else data.get("projects", [])
            for item in projects_data:
                try:
                    project = ProjectConfig.model_validate(item)
                    self._projects[project.alias] = project
                except Exception:
                    continue
        except Exception:
            self._projects.clear()

    def _save_to_disk(self) -> None:
        path = self._persist_path()
        try:
            _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            projects_data = [p.model_dump(mode="json") for p in self._projects.values()]
            path.write_text(
                json.dumps(projects_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── CRUD ────────────────────────────────────────────────────────

    def create_project(self, data: ProjectConfigCreate) -> ProjectConfig:
        with self._lock:
            if data.alias in self._projects:
                raise ValueError(f"项目别名 '{data.alias}' 已存在")
            project = ProjectConfig(
                alias=data.alias,
                local_path=data.local_path,
                remote_path=data.remote_path,
                ssh_alias=data.ssh_alias,
                project_type=data.project_type,
                jdk_version=data.jdk_version,
                node_version=data.node_version,
                nginx_port=data.nginx_port,
                build_command=data.build_command,
            )
            self._projects[data.alias] = project
            self._save_to_disk()
            return project

    def get_project(self, alias: str) -> Optional[ProjectConfig]:
        with self._lock:
            project = self._projects.get(alias)
            if project is None:
                return None
            return project

    def list_projects(self) -> list[ProjectConfig]:
        with self._lock:
            return list(self._projects.values())

    def update_project(self, alias: str, data: ProjectConfigUpdate) -> ProjectConfig:
        with self._lock:
            if alias not in self._projects:
                raise ValueError(f"项目 '{alias}' 不存在")
            existing = self._projects[alias]
            update_data = data.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.now().isoformat()
            merged = existing.model_copy(update=update_data)
            self._projects[alias] = merged
            self._save_to_disk()
            return merged

    def delete_project(self, alias: str) -> None:
        with self._lock:
            if alias not in self._projects:
                raise ValueError(f"项目 '{alias}' 不存在")
            del self._projects[alias]
            self._save_to_disk()


project_config_service = ProjectConfigService()
