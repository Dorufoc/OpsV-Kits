from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_svc():
    with patch("app.api.routes.file_manager.file_manager_service") as m:
        yield m


def _make_entry(**overrides):
    base = MagicMock()
    base.name = "test.txt"
    base.path = "/home/user/test.txt"
    base.is_dir = False
    base.size = 100
    base.permissions = "rw-r--r--"
    base.owner = "user"
    base.group = "user"
    base.modify_time = "2025-01-01 00:00:00"
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def _make_file_info(**overrides):
    info = MagicMock()
    info.path = "/home/user/test.txt"
    info.is_dir = False
    info.is_file = True
    info.is_link = False
    info.is_socket = False
    info.is_fifo = False
    info.is_block_device = False
    info.is_char_device = False
    info.size = 100
    info.blocks = 8
    info.permissions = "rw-r--r--"
    info.permission_mode = "644"
    info.modify_time = "2025-01-01 00:00:00"
    info.access_time = "2025-01-01 00:00:00"
    info.change_time = "2025-01-01 00:00:00"
    info.owner = "user"
    info.group = "user"
    info.link_target = None
    for k, v in overrides.items():
        setattr(info, k, v)
    return info


def _make_perm(**overrides):
    perm = MagicMock()
    perm.path = "/home/user/test.txt"
    perm.exists = True
    perm.readable = True
    perm.writable = True
    perm.executable = False
    perm.permission_str = "rw-r--r--"
    perm.permission_mode = "644"
    perm.owner = "user"
    perm.group = "user"
    perm.current_user = "user"
    for k, v in overrides.items():
        setattr(perm, k, v)
    return perm


def _make_user_info(**overrides):
    ui = MagicMock()
    ui.username = "root"
    ui.uid = 0
    ui.gid = 0
    ui.groups = ["root"]
    ui.home = "/root"
    ui.shell = "/bin/bash"
    ui.is_root = True
    for k, v in overrides.items():
        setattr(ui, k, v)
    return ui


def _make_bookmark(**overrides):
    bm = MagicMock()
    bm.alias = "srv1"
    bm.path = "/home/user"
    bm.label = "Home"
    bm.created_at = "2025-01-01T00:00:00"
    for k, v in overrides.items():
        setattr(bm, k, v)
    return bm


class TestGetFileStatRuntimeError:
    def test_stat_runtime_error(self, client, mock_svc):
        mock_svc.get_file_info.side_effect = RuntimeError("ssh failed")
        resp = client.get("/api/files/stat", params={"alias": "srv1", "path": "/home/user/test.txt"})
        assert resp.status_code == 500


class TestReadFileContentValueError:
    def test_read_value_error(self, client, mock_svc):
        mock_svc.read_file.side_effect = ValueError("not found")
        resp = client.get("/api/files/content", params={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404


class TestReadFileContentRuntimeError:
    def test_read_runtime_error(self, client, mock_svc):
        mock_svc.read_file.side_effect = RuntimeError("ssh failed")
        resp = client.get("/api/files/content", params={"alias": "srv1", "path": "/home/user/test.txt"})
        assert resp.status_code == 500


class TestSaveFileContentRuntimeError:
    def test_save_runtime_error(self, client, mock_svc):
        mock_svc.write_file.side_effect = RuntimeError("ssh failed")
        resp = client.post("/api/files/content", json={"alias": "srv1", "path": "/tmp/f.txt", "content": "hi"})
        assert resp.status_code == 500


class TestCreateDirectoryValueError:
    def test_mkdir_value_error(self, client, mock_svc):
        mock_svc.create_directory.side_effect = ValueError("not found")
        resp = client.post("/api/files/mkdir", json={"alias": "srv1", "path": "/nope/newdir"})
        assert resp.status_code == 404


class TestCreateDirectoryRuntimeError:
    def test_mkdir_runtime_error(self, client, mock_svc):
        mock_svc.create_directory.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/mkdir", json={"alias": "srv1", "path": "/tmp/newdir"})
        assert resp.status_code == 500


class TestDeletePathPermissionError:
    def test_delete_permission_error(self, client, mock_svc):
        mock_svc.delete.side_effect = PermissionError("denied")
        resp = client.post("/api/files/delete", json={"alias": "srv1", "path": "/root/file"})
        assert resp.status_code == 403


class TestDeletePathRuntimeError:
    def test_delete_runtime_error(self, client, mock_svc):
        mock_svc.delete.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/delete", json={"alias": "srv1", "path": "/tmp/file"})
        assert resp.status_code == 500


class TestRenamePathValueError:
    def test_rename_value_error(self, client, mock_svc):
        mock_svc.rename.side_effect = ValueError("not found")
        resp = client.post("/api/files/rename", json={"alias": "srv1", "src": "/nope", "dst": "/tmp/b"})
        assert resp.status_code == 404


class TestRenamePathRuntimeError:
    def test_rename_runtime_error(self, client, mock_svc):
        mock_svc.rename.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/rename", json={"alias": "srv1", "src": "/tmp/a", "dst": "/tmp/b"})
        assert resp.status_code == 500


class TestCopyPathValueError:
    def test_copy_value_error(self, client, mock_svc):
        mock_svc.copy.side_effect = ValueError("not found")
        resp = client.post("/api/files/copy", json={"alias": "srv1", "src": "/nope", "dst": "/tmp/b"})
        assert resp.status_code == 404


class TestChmodPathValueError:
    def test_chmod_value_error(self, client, mock_svc):
        mock_svc.chmod.side_effect = ValueError("not found")
        resp = client.post("/api/files/chmod", json={"alias": "srv1", "path": "/nope", "mode": "755"})
        assert resp.status_code == 404


class TestChmodPathRuntimeError:
    def test_chmod_runtime_error(self, client, mock_svc):
        mock_svc.chmod.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/chmod", json={"alias": "srv1", "path": "/tmp/f", "mode": "755"})
        assert resp.status_code == 500


class TestChownPathPermissionError:
    def test_chown_permission_error(self, client, mock_svc):
        mock_svc.chown.side_effect = PermissionError("denied")
        resp = client.post("/api/files/chown", json={"alias": "srv1", "path": "/tmp/f", "user": "root", "group": "root"})
        assert resp.status_code == 403


class TestChownPathRuntimeError:
    def test_chown_runtime_error(self, client, mock_svc):
        mock_svc.chown.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/chown", json={"alias": "srv1", "path": "/tmp/f", "user": "root", "group": "root"})
        assert resp.status_code == 500


class TestUploadFileRuntimeError:
    def test_upload_runtime_error(self, client, mock_svc):
        mock_svc.upload.side_effect = RuntimeError("ssh failed")
        resp = client.post("/api/files/upload", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 500


class TestDownloadFileRuntimeError:
    def test_download_runtime_error(self, client, mock_svc):
        mock_svc.download.side_effect = RuntimeError("ssh failed")
        resp = client.get("/api/files/download", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 500


class TestSearchFilesValueError:
    def test_search_value_error(self, client, mock_svc):
        mock_svc.search.side_effect = ValueError("not found")
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/nope", "pattern": "*"})
        assert resp.status_code == 404


class TestSearchFilesRuntimeError:
    def test_search_runtime_error(self, client, mock_svc):
        mock_svc.search.side_effect = RuntimeError("fail")
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/home", "pattern": "*"})
        assert resp.status_code == 500


class TestExecBatchCommandsRuntimeError:
    def test_batch_runtime_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_batch.side_effect = RuntimeError("fail")
        resp = client.post("/api/command/exec/batch", json={"alias": "srv1", "commands": ["ls"]})
        assert resp.status_code == 500


class TestExecBatchCommandsValueError:
    def test_batch_value_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_batch.side_effect = ValueError("not found")
        resp = client.post("/api/command/exec/batch", json={"alias": "srv1", "commands": ["ls"]})
        assert resp.status_code == 404


class TestCheckSudoRuntimeError:
    def test_sudo_runtime_error(self, client, mock_svc):
        mock_svc.check_sudo.side_effect = RuntimeError("fail")
        resp = client.get("/api/permission/sudo", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestGetUserInfoRuntimeError:
    def test_user_info_runtime_error(self, client, mock_svc):
        mock_svc.get_user_info.side_effect = RuntimeError("fail")
        resp = client.get("/api/permission/user", params={"alias": "srv1"})
        assert resp.status_code == 500


class TestBatchChmodWithRecursive:
    def test_batch_chmod_with_recursive_flag(self, client, mock_svc):
        mock_svc.batch_chmod.return_value = [{"path": "/tmp/a", "status": "changed"}]
        resp = client.post("/api/files/batch/chmod", json={"alias": "srv1", "paths": ["/tmp/a"], "mode": "755", "recursive": True})
        assert resp.status_code == 200
        mock_svc.batch_chmod.assert_called_once_with("srv1", ["/tmp/a"], "755", recursive=True)


class TestListDirectoryWithDirEntry:
    def test_list_directory_dir_entry(self, client, mock_svc):
        mock_svc.list_directory.return_value = [_make_entry(name="mydir", is_dir=True, path="/home/mydir")]
        resp = client.get("/api/files/list", params={"alias": "srv1", "path": "/home"})
        assert resp.status_code == 200
        assert resp.json()["entries"][0]["is_dir"] is True


class TestGetFileStatWithLink:
    def test_stat_symlink(self, client, mock_svc):
        mock_svc.get_file_info.return_value = _make_file_info(is_link=True, link_target="/etc/config")
        resp = client.get("/api/files/stat", params={"alias": "srv1", "path": "/home/user/link"})
        assert resp.status_code == 200
        assert resp.json()["is_link"] is True
        assert resp.json()["link_target"] == "/etc/config"


class TestSearchWithFileType:
    def test_search_file_type_directory(self, client, mock_svc):
        mock_svc.search.return_value = [_make_entry(name="subdir", is_dir=True)]
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/home", "pattern": "sub*", "file_type": "directory"})
        assert resp.status_code == 200
        mock_svc.search.assert_called_once_with("srv1", "/home", "sub*", max_depth=None, file_type="directory")
