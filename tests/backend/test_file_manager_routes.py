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


def _make_cmd_record(**overrides):
    r = MagicMock()
    r.timestamp = "2025-01-01T00:00:00"
    r.account_alias = "srv1"
    r.command = "ls -la"
    r.exit_code = 0
    r.stdout = "output"
    r.stderr = ""
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


def _make_op_record(**overrides):
    r = MagicMock()
    r.timestamp = "2025-01-01T00:00:00"
    r.account_alias = "srv1"
    r.action = "delete"
    r.path = "/tmp/file"
    r.status = "success"
    r.detail = ""
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


class TestListDirectory:
    def test_list_success(self, client, mock_svc):
        mock_svc.list_directory.return_value = [_make_entry()]
        resp = client.get("/api/files/list", params={"alias": "srv1", "path": "/home"})
        assert resp.status_code == 200
        assert resp.json()["path"] == "/home"

    def test_list_permission_error(self, client, mock_svc):
        mock_svc.list_directory.side_effect = PermissionError("denied")
        resp = client.get("/api/files/list", params={"alias": "srv1", "path": "/root"})
        assert resp.status_code == 403

    def test_list_value_error(self, client, mock_svc):
        mock_svc.list_directory.side_effect = ValueError("not found")
        resp = client.get("/api/files/list", params={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404

    def test_list_runtime_error(self, client, mock_svc):
        mock_svc.list_directory.side_effect = RuntimeError("fail")
        resp = client.get("/api/files/list", params={"alias": "srv1", "path": "/home"})
        assert resp.status_code == 500


class TestGetFileStat:
    def test_stat_success(self, client, mock_svc):
        mock_svc.get_file_info.return_value = _make_file_info()
        resp = client.get("/api/files/stat", params={"alias": "srv1", "path": "/home/user/test.txt"})
        assert resp.status_code == 200
        assert resp.json()["is_file"] is True

    def test_stat_permission_error(self, client, mock_svc):
        mock_svc.get_file_info.side_effect = PermissionError("denied")
        resp = client.get("/api/files/stat", params={"alias": "srv1", "path": "/etc/shadow"})
        assert resp.status_code == 403

    def test_stat_value_error(self, client, mock_svc):
        mock_svc.get_file_info.side_effect = ValueError("not found")
        resp = client.get("/api/files/stat", params={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404


class TestReadFileContent:
    def test_read_success(self, client, mock_svc):
        mock_svc.read_file.return_value = "hello world"
        resp = client.get("/api/files/content", params={"alias": "srv1", "path": "/home/user/test.txt"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello world"

    def test_read_permission_error(self, client, mock_svc):
        mock_svc.read_file.side_effect = PermissionError("denied")
        resp = client.get("/api/files/content", params={"alias": "srv1", "path": "/etc/shadow"})
        assert resp.status_code == 403


class TestSaveFileContent:
    def test_save_success(self, client, mock_svc):
        resp = client.post("/api/files/content", json={"alias": "srv1", "path": "/tmp/f.txt", "content": "hi"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_save_permission_error(self, client, mock_svc):
        mock_svc.write_file.side_effect = PermissionError("denied")
        resp = client.post("/api/files/content", json={"alias": "srv1", "path": "/root/f.txt", "content": "hi"})
        assert resp.status_code == 403

    def test_save_value_error(self, client, mock_svc):
        mock_svc.write_file.side_effect = ValueError("not found")
        resp = client.post("/api/files/content", json={"alias": "srv1", "path": "/nope", "content": "hi"})
        assert resp.status_code == 404


class TestCreateDirectory:
    def test_mkdir_success(self, client, mock_svc):
        resp = client.post("/api/files/mkdir", json={"alias": "srv1", "path": "/tmp/newdir"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_mkdir_permission_error(self, client, mock_svc):
        mock_svc.create_directory.side_effect = PermissionError("denied")
        resp = client.post("/api/files/mkdir", json={"alias": "srv1", "path": "/root/newdir"})
        assert resp.status_code == 403


class TestDeletePath:
    def test_delete_success(self, client, mock_svc):
        resp = client.post("/api/files/delete", json={"alias": "srv1", "path": "/tmp/file"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_delete_value_error(self, client, mock_svc):
        mock_svc.delete.side_effect = ValueError("not found")
        resp = client.post("/api/files/delete", json={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404


class TestRenamePath:
    def test_rename_success(self, client, mock_svc):
        resp = client.post("/api/files/rename", json={"alias": "srv1", "src": "/tmp/a", "dst": "/tmp/b"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "renamed"

    def test_rename_permission_error(self, client, mock_svc):
        mock_svc.rename.side_effect = PermissionError("denied")
        resp = client.post("/api/files/rename", json={"alias": "srv1", "src": "/tmp/a", "dst": "/tmp/b"})
        assert resp.status_code == 403


class TestCopyPath:
    def test_copy_success(self, client, mock_svc):
        resp = client.post("/api/files/copy", json={"alias": "srv1", "src": "/tmp/a", "dst": "/tmp/b"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "copied"

    def test_copy_runtime_error(self, client, mock_svc):
        mock_svc.copy.side_effect = RuntimeError("fail")
        resp = client.post("/api/files/copy", json={"alias": "srv1", "src": "/tmp/a", "dst": "/tmp/b"})
        assert resp.status_code == 500


class TestChmodPath:
    def test_chmod_success(self, client, mock_svc):
        resp = client.post("/api/files/chmod", json={"alias": "srv1", "path": "/tmp/f", "mode": "755"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "755"

    def test_chmod_permission_error(self, client, mock_svc):
        mock_svc.chmod.side_effect = PermissionError("denied")
        resp = client.post("/api/files/chmod", json={"alias": "srv1", "path": "/tmp/f", "mode": "755"})
        assert resp.status_code == 403


class TestChownPath:
    def test_chown_success(self, client, mock_svc):
        resp = client.post("/api/files/chown", json={"alias": "srv1", "path": "/tmp/f", "user": "root", "group": "root"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "changed"

    def test_chown_none_user_group(self, client, mock_svc):
        resp = client.post("/api/files/chown", json={"alias": "srv1", "path": "/tmp/f", "user": None, "group": None})
        assert resp.status_code == 200

    def test_chown_value_error(self, client, mock_svc):
        mock_svc.chown.side_effect = ValueError("not found")
        resp = client.post("/api/files/chown", json={"alias": "srv1", "path": "/nope", "user": "root", "group": "root"})
        assert resp.status_code == 404


class TestUploadFile:
    def test_upload_success(self, client, mock_svc):
        resp = client.post("/api/files/upload", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "uploaded"

    def test_upload_file_not_found(self, client, mock_svc):
        mock_svc.upload.side_effect = FileNotFoundError("not found")
        resp = client.post("/api/files/upload", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/nope"})
        assert resp.status_code == 404

    def test_upload_permission_error(self, client, mock_svc):
        mock_svc.upload.side_effect = PermissionError("denied")
        resp = client.post("/api/files/upload", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 403


class TestDownloadFile:
    def test_download_success(self, client, mock_svc):
        resp = client.get("/api/files/download", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "downloaded"

    def test_download_permission_error(self, client, mock_svc):
        mock_svc.download.side_effect = PermissionError("denied")
        resp = client.get("/api/files/download", params={"alias": "srv1", "remote_path": "/tmp/f", "local_path": "/local/f"})
        assert resp.status_code == 403

    def test_download_value_error(self, client, mock_svc):
        mock_svc.download.side_effect = ValueError("not found")
        resp = client.get("/api/files/download", params={"alias": "srv1", "remote_path": "/nope", "local_path": "/local/f"})
        assert resp.status_code == 404


class TestSearchFiles:
    def test_search_success(self, client, mock_svc):
        mock_svc.search.return_value = [_make_entry(name="found.txt")]
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/home", "pattern": "*.txt"})
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_search_with_optional_params(self, client, mock_svc):
        mock_svc.search.return_value = []
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/home", "pattern": "*.log", "max_depth": 3, "file_type": "file"})
        assert resp.status_code == 200

    def test_search_permission_error(self, client, mock_svc):
        mock_svc.search.side_effect = PermissionError("denied")
        resp = client.get("/api/files/search", params={"alias": "srv1", "path": "/root", "pattern": "*"})
        assert resp.status_code == 403


class TestExecCommand:
    def test_exec_success(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_command.return_value = {"stdout": "ok", "stderr": "", "exit_code": 0}
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "ls"})
        assert resp.status_code == 200

    def test_exec_dangerous_command(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (True, "rm -rf")
        mock_svc._record_operation = MagicMock()
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "rm -rf /"})
        assert resp.status_code == 400

    def test_exec_permission_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_command.side_effect = PermissionError("denied")
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "ls"})
        assert resp.status_code == 403

    def test_exec_timeout_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_command.side_effect = TimeoutError("timeout")
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "sleep 999"})
        assert resp.status_code == 408

    def test_exec_value_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_command.side_effect = ValueError("not found")
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "ls"})
        assert resp.status_code == 404

    def test_exec_runtime_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_command.side_effect = RuntimeError("fail")
        resp = client.post("/api/command/exec", json={"alias": "srv1", "command": "ls"})
        assert resp.status_code == 500


class TestExecBatchCommands:
    def test_batch_success(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_batch.return_value = [{"stdout": "ok", "exit_code": 0}]
        resp = client.post("/api/command/exec/batch", json={"alias": "srv1", "commands": ["ls", "pwd"]})
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_batch_dangerous_command(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (True, "rm -rf")
        mock_svc._record_operation = MagicMock()
        resp = client.post("/api/command/exec/batch", json={"alias": "srv1", "commands": ["ls", "rm -rf /"]})
        assert resp.status_code == 400

    def test_batch_timeout_error(self, client, mock_svc):
        mock_svc._is_dangerous_command.return_value = (False, "")
        mock_svc.exec_batch.side_effect = TimeoutError("timeout")
        resp = client.post("/api/command/exec/batch", json={"alias": "srv1", "commands": ["ls"]})
        assert resp.status_code == 408


class TestCommandHistory:
    def test_history_success(self, client, mock_svc):
        mock_svc.get_command_history.return_value = [_make_cmd_record()]
        resp = client.get("/api/command/history", params={"alias": "srv1", "limit": 50})
        assert resp.status_code == 200
        assert "records" in resp.json()

    def test_history_no_alias(self, client, mock_svc):
        mock_svc.get_command_history.return_value = []
        resp = client.get("/api/command/history", params={"limit": 10})
        assert resp.status_code == 200


class TestCheckPermission:
    def test_check_success(self, client, mock_svc):
        mock_svc.check_permission.return_value = _make_perm()
        resp = client.get("/api/permission/check", params={"alias": "srv1", "path": "/tmp/f"})
        assert resp.status_code == 200
        assert resp.json()["readable"] is True

    def test_check_value_error(self, client, mock_svc):
        mock_svc.check_permission.side_effect = ValueError("not found")
        resp = client.get("/api/permission/check", params={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404

    def test_check_runtime_error(self, client, mock_svc):
        mock_svc.check_permission.side_effect = RuntimeError("fail")
        resp = client.get("/api/permission/check", params={"alias": "srv1", "path": "/tmp/f"})
        assert resp.status_code == 500


class TestGetUserInfo:
    def test_user_info_success(self, client, mock_svc):
        mock_svc.get_user_info.return_value = _make_user_info()
        resp = client.get("/api/permission/user", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["is_root"] is True

    def test_user_info_value_error(self, client, mock_svc):
        mock_svc.get_user_info.side_effect = ValueError("not found")
        resp = client.get("/api/permission/user", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestCheckSudo:
    def test_sudo_success(self, client, mock_svc):
        mock_svc.check_sudo.return_value = True
        resp = client.get("/api/permission/sudo", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["has_sudo"] is True

    def test_sudo_value_error(self, client, mock_svc):
        mock_svc.check_sudo.side_effect = ValueError("not found")
        resp = client.get("/api/permission/sudo", params={"alias": "srv1"})
        assert resp.status_code == 404


class TestListBookmarks:
    def test_list_success(self, client, mock_svc):
        mock_svc.list_bookmarks.return_value = [_make_bookmark()]
        resp = client.get("/api/bookmarks", params={"alias": "srv1"})
        assert resp.status_code == 200
        assert "bookmarks" in resp.json()

    def test_list_no_alias(self, client, mock_svc):
        mock_svc.list_bookmarks.return_value = []
        resp = client.get("/api/bookmarks")
        assert resp.status_code == 200


class TestAddBookmark:
    def test_add_success(self, client, mock_svc):
        mock_svc.add_bookmark.return_value = _make_bookmark()
        resp = client.post("/api/bookmarks", json={"alias": "srv1", "path": "/home", "label": "Home"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "added"


class TestRemoveBookmark:
    def test_remove_success(self, client, mock_svc):
        mock_svc.remove_bookmark.return_value = True
        resp = client.request("DELETE", "/api/bookmarks", json={"alias": "srv1", "path": "/home"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"

    def test_remove_not_found(self, client, mock_svc):
        mock_svc.remove_bookmark.return_value = False
        resp = client.request("DELETE", "/api/bookmarks", json={"alias": "srv1", "path": "/nope"})
        assert resp.status_code == 404


class TestOperationHistory:
    def test_history_success(self, client, mock_svc):
        mock_svc.get_operation_history.return_value = [_make_op_record()]
        resp = client.get("/api/operations/history", params={"alias": "srv1", "limit": 50})
        assert resp.status_code == 200
        assert "records" in resp.json()


class TestBatchDelete:
    def test_batch_delete_success(self, client, mock_svc):
        mock_svc.batch_delete.return_value = [{"path": "/tmp/a", "status": "deleted"}]
        resp = client.post("/api/files/batch/delete", json={"alias": "srv1", "paths": ["/tmp/a", "/tmp/b"]})
        assert resp.status_code == 200
        assert "results" in resp.json()


class TestBatchChmod:
    def test_batch_chmod_success(self, client, mock_svc):
        mock_svc.batch_chmod.return_value = [{"path": "/tmp/a", "status": "changed"}]
        resp = client.post("/api/files/batch/chmod", json={"alias": "srv1", "paths": ["/tmp/a"], "mode": "755"})
        assert resp.status_code == 200
        assert "results" in resp.json()

    def test_batch_chmod_recursive(self, client, mock_svc):
        mock_svc.batch_chmod.return_value = []
        resp = client.post("/api/files/batch/chmod", json={"alias": "srv1", "paths": ["/tmp/a"], "mode": "755", "recursive": True})
        assert resp.status_code == 200
