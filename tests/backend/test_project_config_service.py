import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.project_config import ProjectConfigCreate, ProjectConfigUpdate


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture
def service(project_dir):
    with patch("app.services.project_config_service._PERSIST_DIR", project_dir), \
         patch("app.services.project_config_service._PERSIST_PATH", project_dir / "projects.json"):
        from app.services.project_config_service import ProjectConfigService
        svc = ProjectConfigService()
        svc._projects.clear()
        yield svc


class TestCreateProject:
    def test_create_project_success(self, service):
        data = ProjectConfigCreate(alias="test-proj", local_path="/local", remote_path="/remote", ssh_alias="myserver")
        project = service.create_project(data)
        assert project.alias == "test-proj"
        assert project.local_path == "/local"
        assert project.remote_path == "/remote"

    def test_create_duplicate_alias_raises(self, service):
        data = ProjectConfigCreate(alias="dup", local_path="/a")
        service.create_project(data)
        with pytest.raises(ValueError, match="已存在"):
            service.create_project(ProjectConfigCreate(alias="dup", local_path="/b"))

    def test_create_project_saves_to_disk(self, service, project_dir):
        data = ProjectConfigCreate(alias="save-test", local_path="/local")
        service.create_project(data)
        path = project_dir / "projects.json"
        assert path.exists()


class TestGetProject:
    def test_get_existing_project(self, service):
        data = ProjectConfigCreate(alias="get-test", local_path="/local")
        service.create_project(data)
        project = service.get_project("get-test")
        assert project is not None
        assert project.alias == "get-test"

    def test_get_nonexistent_project(self, service):
        assert service.get_project("nonexistent") is None


class TestListProjects:
    def test_list_empty(self, service):
        assert service.list_projects() == []

    def test_list_multiple_projects(self, service):
        service.create_project(ProjectConfigCreate(alias="p1", local_path="/a"))
        service.create_project(ProjectConfigCreate(alias="p2", local_path="/b"))
        projects = service.list_projects()
        assert len(projects) == 2


class TestUpdateProject:
    def test_update_project_success(self, service):
        service.create_project(ProjectConfigCreate(alias="upd-test", local_path="/old"))
        updated = service.update_project("upd-test", ProjectConfigUpdate(local_path="/new"))
        assert updated.local_path == "/new"

    def test_update_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.update_project("nope", ProjectConfigUpdate(local_path="/new"))

    def test_update_partial_fields(self, service):
        service.create_project(ProjectConfigCreate(alias="partial", local_path="/a", remote_path="/r"))
        updated = service.update_project("partial", ProjectConfigUpdate(local_path="/b"))
        assert updated.local_path == "/b"
        assert updated.remote_path == "/r"

    def test_update_sets_updated_at(self, service):
        service.create_project(ProjectConfigCreate(alias="ts-test", local_path="/a"))
        updated = service.update_project("ts-test", ProjectConfigUpdate(local_path="/b"))
        assert updated.updated_at is not None


class TestDeleteProject:
    def test_delete_project_success(self, service):
        service.create_project(ProjectConfigCreate(alias="del-test", local_path="/a"))
        service.delete_project("del-test")
        assert service.get_project("del-test") is None

    def test_delete_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="不存在"):
            service.delete_project("nope")


class TestPersistence:
    def test_load_from_disk(self, project_dir):
        path = project_dir / "projects.json"
        data = [{"alias": "loaded", "local_path": "/loaded", "remote_path": "", "ssh_alias": "", "project_type": "java", "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}]
        path.write_text(json.dumps(data), encoding="utf-8")

        with patch("app.services.project_config_service._PERSIST_DIR", project_dir), \
             patch("app.services.project_config_service._PERSIST_PATH", path):
            from app.services.project_config_service import ProjectConfigService
            svc = ProjectConfigService()
            assert svc.get_project("loaded") is not None

    def test_load_corrupt_file(self, project_dir):
        path = project_dir / "projects.json"
        path.write_text("not json", encoding="utf-8")

        with patch("app.services.project_config_service._PERSIST_DIR", project_dir), \
             patch("app.services.project_config_service._PERSIST_PATH", path):
            from app.services.project_config_service import ProjectConfigService
            svc = ProjectConfigService()
            assert svc.list_projects() == []

    def test_load_missing_file(self, project_dir):
        with patch("app.services.project_config_service._PERSIST_DIR", project_dir), \
             patch("app.services.project_config_service._PERSIST_PATH", project_dir / "missing.json"):
            from app.services.project_config_service import ProjectConfigService
            svc = ProjectConfigService()
            assert svc.list_projects() == []
