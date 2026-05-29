"""文件管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestFileManager:
    """文件管理接口测试"""

    @patch("app.api.routes.file_manager.file_manager_service")
    def test_list_files(self, mock_fm_service, client):
        # 构造 mock 的 FileEntry 对象
        mock_entry1 = MagicMock()
        mock_entry1.name = "file1.txt"
        mock_entry1.path = "/opt/project/file1.txt"
        mock_entry1.is_dir = False
        mock_entry1.size = 1024
        mock_entry1.permissions = "-rw-r--r--"
        mock_entry1.owner = "root"
        mock_entry1.group = "root"
        mock_entry1.modify_time = "2024-01-01"

        mock_entry2 = MagicMock()
        mock_entry2.name = "dir1"
        mock_entry2.path = "/opt/project/dir1"
        mock_entry2.is_dir = True
        mock_entry2.size = 0
        mock_entry2.permissions = "drwxr-xr-x"
        mock_entry2.owner = "root"
        mock_entry2.group = "root"
        mock_entry2.modify_time = "2024-01-01"

        mock_fm_service.list_directory.return_value = [mock_entry1, mock_entry2]

        response = client.get(
            "/api/files/list?alias=test-server&path=/opt/project"
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) == 2

    @patch("app.api.routes.file_manager.file_manager_service")
    def test_read_file(self, mock_fm_service, client):
        mock_fm_service.read_file.return_value = "Hello World"

        response = client.get(
            "/api/files/content?alias=test-server&path=/opt/project/file.txt"
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data

    @patch("app.api.routes.file_manager.file_manager_service")
    def test_delete_file(self, mock_fm_service, client):
        mock_fm_service.delete.return_value = None

        response = client.post(
            "/api/files/delete",
            json={"alias": "test-server", "path": "/opt/project/file.txt"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    @patch("app.api.routes.file_manager.file_manager_service")
    def test_create_directory(self, mock_fm_service, client):
        mock_fm_service.create_directory.return_value = None

        response = client.post(
            "/api/files/mkdir",
            json={"alias": "test-server", "path": "/opt/project/new-dir"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"

    @patch("app.api.routes.file_manager.file_manager_service")
    def test_rename_file(self, mock_fm_service, client):
        mock_fm_service.rename.return_value = None

        response = client.post(
            "/api/files/rename",
            json={
                "alias": "test-server",
                "src": "/opt/project/old.txt",
                "dst": "/opt/project/new.txt",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "renamed"
