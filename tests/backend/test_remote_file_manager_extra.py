import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.remote_file_manager import (
    FileDetail,
    FileEntry,
    FileSearchResult,
    RemoteFileManager,
    _parse_ls_line,
    _parse_stat_output,
)


@pytest.fixture
def manager():
    mock_ssh = MagicMock()
    return RemoteFileManager(mock_ssh)


class TestDetectLocaleNonZeroCode:
    def test_detect_locale_non_zero_code(self, manager):
        manager._is_chinese = None
        manager._manager.exec_command.return_value = (1, "", "")
        assert manager._detect_locale() is False
        assert manager._is_chinese is False


class TestShellPath:
    def test_shell_path_tilde_only(self):
        result = RemoteFileManager._shell_path("~")
        assert result == "$HOME"

    def test_shell_path_tilde_with_path(self):
        result = RemoteFileManager._shell_path("~/documents")
        assert "$HOME" in result
        assert "documents" in result

    def test_shell_path_regular(self):
        result = RemoteFileManager._shell_path("/home/user/file.txt")
        assert result == "/home/user/file.txt" or "home" in result


class TestExecBytesDecoding:
    def test_exec_bytes_stdout(self, manager):
        manager._manager.exec_command.return_value = (0, b"output", "err")
        code, stdout, stderr = manager._exec("ls")
        assert stdout == "output"
        assert code == 0

    def test_exec_bytes_stderr(self, manager):
        manager._manager.exec_command.return_value = (0, "out", b"error msg")
        code, stdout, stderr = manager._exec("ls")
        assert stderr == "error msg"

    def test_exec_no_bytes(self, manager):
        manager._manager.exec_command.return_value = (0, "out", "err")
        code, stdout, stderr = manager._exec("ls")
        assert stdout == "out"
        assert stderr == "err"


class TestGetFileInfoStatFormat:
    def test_stat_directory(self, manager):
        stat_output = "directory|0755|drwxr-xr-x|4096|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/mydir")
        assert detail.is_dir is True
        assert detail.is_file is False
        assert detail.size == 4096
        assert detail.owner == "root"
        assert detail.permission_mode == 0o755

    def test_stat_socket(self, manager):
        stat_output = "socket|0755|srwxrwxrwx|0|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/var/run/sock")
        assert detail.is_socket is True

    def test_stat_fifo(self, manager):
        stat_output = "fifo|0644|prw-r--r--|0|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/tmp/pipe")
        assert detail.is_fifo is True

    def test_stat_block_device(self, manager):
        stat_output = "block special file|0660|brw-rw----|0|root|disk|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/dev/sda")
        assert detail.is_block_device is True

    def test_stat_char_device(self, manager):
        stat_output = "character special file|0620|crw-rw----|0|root|tty|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/dev/tty0")
        assert detail.is_char_device is True

    def test_stat_link(self, manager):
        stat_output = "symbolic link|0777|lrwxrwxrwx|5|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/link")
        assert detail.is_link is True

    def test_stat_regular_file(self, manager):
        call_count = [0]

        def mock_exec(cmd, timeout=30.0):
            call_count[0] += 1
            if "test -L" in cmd:
                return (1, "", "")
            stat_output = "regular file|0644|-rw-r--r--|1234|user|group|1700000000.0|1700001000.0|1700002000.0"
            return (0, stat_output, "")

        manager._manager.exec_command = mock_exec
        detail = manager.get_file_info("/home/file.txt")
        assert detail.is_file is True
        assert detail.is_dir is False
        assert detail.is_link is False
        assert detail.size == 1234
        assert detail.owner == "user"
        assert detail.group == "group"

    def test_stat_with_timestamps(self, manager):
        stat_output = "regular file|0644|-rw-r--r--|100|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/file.txt")
        assert detail.modify_timestamp == 1700000000.0
        assert detail.access_timestamp == 1700001000.0
        assert detail.change_timestamp == 1700002000.0
        assert detail.modify_time != ""
        assert detail.access_time != ""
        assert detail.change_time != ""

    def test_stat_zero_timestamps(self, manager):
        stat_output = "regular file|0644|-rw-r--r--|100|root|root|0|0|0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/file.txt")
        assert detail.modify_time == ""
        assert detail.access_time == ""
        assert detail.change_time == ""

    def test_stat_non_digit_perm_mode(self, manager):
        stat_output = "regular file|abc|-rw-r--r--|100|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/file.txt")
        assert detail.permission_mode == 0

    def test_stat_empty_size(self, manager):
        stat_output = "regular file|0644|-rw-r--r--||root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/file.txt")
        assert detail.size == 0

    def test_stat_fewer_than_9_parts(self, manager):
        stat_output = "regular file|0644|-rw-r--r--"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/file.txt")
        assert detail.path == "/home/file.txt"

    def test_stat_link_detected_by_perm(self, manager):
        stat_output = "regular file|0777|lrwxrwxrwx|5|root|root|1700000000.0|1700001000.0|1700002000.0"
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/link")
        assert detail.is_link is True


class TestUploadWithProgressCallback:
    def test_upload_with_callback(self, manager, tmp_path):
        local_file = tmp_path / "test.txt"
        local_file.write_text("hello world")
        mock_sftp = MagicMock()
        manager._manager.open_sftp.return_value = mock_sftp
        manager._manager.exec_command.return_value = (0, "", "")

        callback_calls = []
        def progress_cb(sent, total):
            callback_calls.append((sent, total))

        manager.upload(str(local_file), "/remote/test.txt", progress_callback=progress_cb)
        mock_sftp.put.assert_called_once()
        put_callback = mock_sftp.put.call_args[1]["callback"]
        put_callback(5, 11)
        assert len(callback_calls) == 1
        assert callback_calls[0] == (5, 11)


class TestDownloadWithProgressCallback:
    def test_download_with_callback(self, manager, tmp_path):
        mock_sftp = MagicMock()
        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_sftp.stat.return_value = mock_stat
        manager._manager.open_sftp.return_value = mock_sftp

        callback_calls = []
        def progress_cb(sent, total):
            callback_calls.append((sent, total))

        manager.download("/remote/test.txt", str(tmp_path / "local.txt"), progress_callback=progress_cb)
        mock_sftp.get.assert_called_once()
        get_callback = mock_sftp.get.call_args[1]["callback"]
        get_callback(50, 100)
        assert len(callback_calls) == 1
        assert callback_calls[0] == (50, 100)


class TestSearchFallback:
    def test_search_fallback_find_ls(self, manager):
        call_count = [0]

        def mock_exec(cmd, timeout=30.0):
            call_count[0] += 1
            if call_count[0] == 1:
                return (1, "", "error")
            ls_output = "12345 4 -rw-r--r-- 1 root root 100 Jan 15 10:30 /home/test.txt\n"
            return (0, ls_output, "")

        manager._manager.exec_command = mock_exec
        results = manager.search("/home", "*.txt")
        assert len(results) == 1
        assert results[0].name == "test.txt"

    def test_search_fallback_both_fail(self, manager):
        manager._manager.exec_command.return_value = (1, "", "error")
        results = manager.search("/home", "*.txt")
        assert results == []


class TestSearchParseFindLsOutput:
    def test_parse_find_ls_with_symlink(self, manager):
        output = "12345 4 lrwxrwxrwx 1 root root 5 Jan 15 10:30 /home/link -> /home/target\n"
        results = manager._parse_find_ls_output(output)
        assert len(results) == 1
        assert results[0].name == "link"

    def test_parse_find_ls_directory(self, manager):
        output = "12345 4 drwxr-xr-x 2 root root 4096 Jan 15 10:30 /home/mydir\n"
        results = manager._parse_find_ls_output(output)
        assert len(results) == 1
        assert results[0].is_dir is True

    def test_parse_find_ls_too_few_parts(self, manager):
        output = "12345 0 root\n"
        results = manager._parse_find_ls_output(output)
        assert len(results) == 0

    def test_parse_find_ls_non_digit_size(self, manager):
        output = "12345 4 -rw-r--r-- 1 root root abc Jan 15 10:30 /home/test.txt\n"
        results = manager._parse_find_ls_output(output)
        assert len(results) == 1
        assert results[0].size == 0


class TestSearchMainPath:
    def test_search_with_results(self, manager):
        search_output = "f\t100\t-rw-r--r--\t2025-01-15 10:30\t/home/test.txt\nd\t4096\t drwxr-xr-x\t2025-01-15 10:30\t/home/mydir\n"
        manager._manager.exec_command.return_value = (0, search_output, "")
        results = manager.search("/home", "*")
        assert len(results) == 2
        dirs = [r for r in results if r.is_dir]
        files = [r for r in results if not r.is_dir]
        assert len(dirs) == 1
        assert len(files) == 1

    def test_search_too_few_parts_line(self, manager):
        search_output = "f\t100\t-rw-r--r--\n"
        manager._manager.exec_command.return_value = (0, search_output, "")
        results = manager.search("/home", "*")
        assert len(results) == 0


class TestGetFileInfoLinkDetection:
    def test_get_file_info_is_link(self, manager):
        call_count = [0]

        def mock_exec(cmd, timeout=30.0):
            call_count[0] += 1
            if "test -L" in cmd:
                return (0, "", "")
            if "readlink" in cmd:
                return (0, "/home/target", "")
            stat_output = "symbolic link|0777|lrwxrwxrwx|5|root|root|1700000000.0|1700001000.0|1700002000.0"
            return (0, stat_output, "")

        manager._manager.exec_command = mock_exec
        detail = manager.get_file_info("/home/link")
        assert detail.is_link is True
        assert detail.link_target == "/home/target"

    def test_get_file_info_not_link(self, manager):
        call_count = [0]

        def mock_exec(cmd, timeout=30.0):
            call_count[0] += 1
            if "test -L" in cmd:
                return (1, "", "")
            stat_output = "regular file|0644|-rw-r--r--|100|root|root|1700000000.0|1700001000.0|1700002000.0"
            return (0, stat_output, "")

        manager._manager.exec_command = mock_exec
        detail = manager.get_file_info("/home/file.txt")
        assert detail.is_link is False
        assert detail.link_target is None


class TestParseLsLineEdgeCases:
    def test_parse_chinese_date_with_day(self):
        line = "-rw-r--r-- 1 root root 100 3月5日 10:30 file.txt"
        entry = _parse_ls_line(line, "/home", is_chinese=True)
        assert entry is not None
        assert entry.name == "file.txt"

    def test_parse_year_format_modify_time(self):
        line = "-rw-r--r-- 1 root root 100 Jan 15 2023 old.txt"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert "2023" in entry.modify_time

    def test_parse_future_date_adjusts_year(self):
        line = "-rw-r--r-- 1 root root 100 Dec 31 23:59 file.txt"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None


class TestParseStatOutputEdgeCases:
    def test_parse_stat_link(self):
        output = (
            "文件：link\n"
            "大小：5\n"
            "Access：(0777/lrwxrwxrwx)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/home/link")
        assert detail.is_link is True
        assert detail.is_file is False

    def test_parse_stat_socket(self):
        output = (
            "文件：sock\n"
            "大小：0\n"
            "Access：(0755/srwxrwxrwx)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/var/run/sock")
        assert detail.is_socket is True

    def test_parse_stat_fifo(self):
        output = (
            "文件：pipe\n"
            "大小：0\n"
            "Access：(0644/prw-r--r--)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/tmp/pipe")
        assert detail.is_fifo is True

    def test_parse_stat_block_device(self):
        output = (
            "文件：sda\n"
            "大小：0\n"
            "Access：(0660/brw-rw----)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/dev/sda")
        assert detail.is_block_device is True

    def test_parse_stat_char_device(self):
        output = (
            "文件：tty0\n"
            "大小：0\n"
            "Access：(0620/crw-rw----)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/dev/tty0")
        assert detail.is_char_device is True
