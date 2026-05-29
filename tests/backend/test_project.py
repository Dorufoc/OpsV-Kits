"""项目管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.project_config import ProjectConfig


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_project_data():
    return {
        "alias": "test-project",
        "local_path": "/home/user/projects/test-app",
        "remote_path": "/opt/projects/test-app",
        "ssh_alias": "test-server",
        "jdk_version": "21",
    }


class TestProjectCRUD:
    """项目CRUD操作测试"""

    @patch("app.api.routes.project.project_config_service")
    def test_list_projects_empty(self, mock_service, client):
        mock_service.list_projects.return_value = []
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.api.routes.project.project_config_service")
    def test_list_projects_with_data(self, mock_service, client):
        mock_projects = [
            ProjectConfig(alias="project1", local_path="/path1", remote_path="/remote1", ssh_alias="server1"),
            ProjectConfig(alias="project2", local_path="/path2", remote_path="/remote2", ssh_alias="server2"),
        ]
        mock_service.list_projects.return_value = mock_projects
        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["alias"] == "project1"

    @patch("app.api.routes.project.project_config_service")
    def test_create_project_success(self, mock_service, client, sample_project_data):
        mock_service.create_project.return_value = ProjectConfig(**sample_project_data)
        response = client.post("/api/projects", json=sample_project_data)
        assert response.status_code == 201
        data = response.json()
        assert data["alias"] == "test-project"
        assert data["ssh_alias"] == "test-server"
        assert data["jdk_version"] == "21"

    @patch("app.api.routes.project.project_config_service")
    def test_create_project_duplicate(self, mock_service, client, sample_project_data):
        mock_service.create_project.side_effect = ValueError("项目已存在")
        response = client.post("/api/projects", json=sample_project_data)
        assert response.status_code == 409

    @patch("app.api.routes.project.project_config_service")
    def test_get_project_success(self, mock_service, client):
        mock_service.get_project.return_value = ProjectConfig(
            alias="test-project", local_path="/path", remote_path="/remote", ssh_alias="server"
        )
        response = client.get("/api/projects/test-project")
        assert response.status_code == 200
        data = response.json()
        assert data["alias"] == "test-project"

    @patch("app.api.routes.project.project_config_service")
    def test_get_project_not_found(self, mock_service, client):
        mock_service.get_project.return_value = None
        response = client.get("/api/projects/nonexistent")
        assert response.status_code == 404

    @patch("app.api.routes.project.project_config_service")
    def test_update_project_success(self, mock_service, client):
        mock_service.update_project.return_value = ProjectConfig(
            alias="test-project", local_path="/new-path", remote_path="/new-remote", ssh_alias="server"
        )
        response = client.put(
            "/api/projects/test-project",
            json={"local_path": "/new-path"},
        )
        assert response.status_code == 200

    @patch("app.api.routes.project.project_config_service")
    def test_update_project_not_found(self, mock_service, client):
        mock_service.update_project.side_effect = ValueError("项目不存在")
        response = client.put(
            "/api/projects/nonexistent",
            json={"local_path": "/new-path"},
        )
        assert response.status_code == 404

    @patch("app.api.routes.project.project_config_service")
    def test_delete_project_success(self, mock_service, client):
        mock_service.delete_project.return_value = None
        response = client.delete("/api/projects/test-project")
        assert response.status_code == 204

    @patch("app.api.routes.project.project_config_service")
    def test_delete_project_not_found(self, mock_service, client):
        mock_service.delete_project.side_effect = ValueError("项目不存在")
        response = client.delete("/api/projects/nonexistent")
        assert response.status_code == 404


class TestProjectValidation:
    """项目数据验证测试"""

    def test_project_config_create_valid(self):
        from app.models.project_config import ProjectConfigCreate
        project = ProjectConfigCreate(
            alias="test-project",
            local_path="/path/to/project",
            remote_path="/remote/path",
            ssh_alias="test-server",
            jdk_version="17",
        )
        assert project.alias == "test-project"
        assert project.jdk_version == "17"

    def test_project_config_create_minimal(self):
        from app.models.project_config import ProjectConfigCreate
        project = ProjectConfigCreate(alias="minimal-project")
        assert project.alias == "minimal-project"
        assert project.local_path == ""
        assert project.remote_path == ""
        assert project.ssh_alias == ""
        assert project.jdk_version == "21"

    def test_project_config_update_partial(self):
        from app.models.project_config import ProjectConfigUpdate
        update = ProjectConfigUpdate(local_path="/new-path", jdk_version="21")
        assert update.local_path == "/new-path"
        assert update.remote_path is None
        assert update.ssh_alias is None
