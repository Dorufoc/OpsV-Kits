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


class TestParseLsLine:
    def test_parse_regular_file(self):
        line = "-rw-r--r-- 1 root root 1234 Jan 15 10:30 test.txt"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert entry.name == "test.txt"
        assert entry.is_dir is False
        assert entry.size == 1234
        assert entry.owner == "root"

    def test_parse_directory(self):
        line = "drwxr-xr-x 2 root root 4096 Jan 15 10:30 mydir"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert entry.is_dir is True

    def test_parse_symlink(self):
        line = "lrwxrwxrwx 1 root root 5 Jan 15 10:30 link -> target"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert entry.is_dir is False
        assert entry.link_target == "target"
        assert entry.name == "link"

    def test_parse_empty_line(self):
        assert _parse_ls_line("", "/home") is None

    def test_parse_dot_entries(self):
        line = "drwxr-xr-x 2 root root 4096 Jan 15 10:30 ."
        assert _parse_ls_line(line, "/home") is None

    def test_parse_dot_dot_entries(self):
        line = "drwxr-xr-x 2 root root 4096 Jan 15 10:30 .."
        assert _parse_ls_line(line, "/home") is None

    def test_parse_chinese_date(self):
        line = "-rw-r--r-- 1 root root 100 1月15日 10:30 file.txt"
        entry = _parse_ls_line(line, "/home", is_chinese=True)
        assert entry is not None

    def test_parse_year_format(self):
        line = "-rw-r--r-- 1 root root 100 Jan 15 2023 old.txt"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert "2023" in entry.modify_time

    def test_parse_invalid_line(self):
        assert _parse_ls_line("not a valid ls line", "/home") is None

    def test_parse_permission_mode(self):
        line = "-rwxr-xr-x 1 root root 0 Jan 15 10:30 exec.sh"
        entry = _parse_ls_line(line, "/home")
        assert entry is not None
        assert entry.permission_mode > 0


class TestParseStatOutput:
    def test_parse_full_output(self):
        output = (
            "文件：test.txt\n"
            "大小：1234 字节\n"
            "Block: 8\n"
            "设备：801h/2049d\n"
            "Inode：12345\n"
            "硬链接：1\n"
            "Access：(0644/-rw-r--r--)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
            "访问时间：2025-01-15 10:30:00\n"
            "修改时间：2025-01-15 10:30:00\n"
            "更改时间：2025-01-15 10:30:00\n"
        )
        detail = _parse_stat_output(output, "/home/test.txt")
        assert detail.path == "/home/test.txt"
        assert detail.size == 1234
        assert detail.is_file is True
        assert detail.owner == "root"

    def test_parse_directory_stat(self):
        output = (
            "文件：mydir\n"
            "大小：4096\n"
            "Access：(0755/drwxr-xr-x)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
        )
        detail = _parse_stat_output(output, "/home/mydir")
        assert detail.is_dir is True
        assert detail.is_file is False

    def test_parse_empty_output(self):
        detail = _parse_stat_output("", "/home/test")
        assert detail.size == 0
        assert detail.is_file is True


class TestRemoteFileManager:
    @pytest.fixture
    def manager(self):
        mock_ssh = MagicMock()
        return RemoteFileManager(mock_ssh)

    def test_detect_locale_chinese(self, manager):
        manager._is_chinese = None
        manager._manager.exec_command.return_value = (0, "zh_CN.UTF-8", "")
        assert manager._detect_locale() is True

    def test_detect_locale_english(self, manager):
        manager._is_chinese = None
        manager._manager.exec_command.return_value = (0, "en_US.UTF-8", "")
        assert manager._detect_locale() is False

    def test_detect_locale_cached(self, manager):
        manager._is_chinese = True
        assert manager._detect_locale() is True

    def test_detect_locale_failure(self, manager):
        manager._is_chinese = None
        manager._manager.exec_command.side_effect = Exception("fail")
        assert manager._detect_locale() is False

    def test_list_directory_success(self, manager):
        manager._is_chinese = False
        ls_output = "total 0\ndrwxr-xr-x 2 root root 4096 Jan 15 10:30 mydir\n-rw-r--r-- 1 root root 100 Jan 15 10:30 file.txt\n"
        manager._manager.exec_command.return_value = (0, ls_output, "")
        entries = manager.list_directory("/home")
        assert len(entries) == 2

    def test_list_directory_failure(self, manager):
        manager._is_chinese = False
        manager._manager.exec_command.return_value = (1, "", "error")
        with pytest.raises(RuntimeError):
            manager.list_directory("/home")

    def test_list_directory_no_stderr(self, manager):
        manager._is_chinese = False
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法列出目录"):
            manager.list_directory("/home")

    def test_get_file_info_stat_success(self, manager):
        stat_output = (
            "文件：test.txt\n"
            "大小：100\n"
            "Access：(0644/-rw-r--r--)\n"
            "Uid：(0)/ root\n"
            "Gid：(0)/ root\n"
            "修改时间：2025-01-15 10:30:00\n"
        )
        manager._manager.exec_command.return_value = (0, stat_output, "")
        detail = manager.get_file_info("/home/test.txt")
        assert detail.size == 100

    def test_get_file_info_stat_fail_ls_fallback(self, manager):
        stat_fail = (1, "", "error")
        ls_output = "-rw-r--r-- 1 root root 100 Jan 15 10:30 test.txt"

        call_count = [0]

        def mock_exec(cmd, timeout=30.0):
            call_count[0] += 1
            if call_count[0] == 1:
                return (1, "", "")
            if call_count[0] == 2:
                return stat_fail
            return (0, ls_output, "")

        manager._manager.exec_command = mock_exec
        detail = manager.get_file_info("/home/test.txt")
        assert detail.size == 100

    def test_get_file_info_all_fail(self, manager):
        manager._manager.exec_command.return_value = (1, "", "error")
        with pytest.raises(RuntimeError):
            manager.get_file_info("/home/test.txt")

    def test_read_file_success(self, manager):
        manager._manager.exec_command.return_value = (0, "file content", "")
        content = manager.read_file("/home/test.txt")
        assert content == "file content"

    def test_read_file_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法读取文件"):
            manager.read_file("/home/test.txt")

    def test_write_file_success(self, manager):
        mock_sftp = MagicMock()
        mock_file = MagicMock()
        mock_sftp.open.return_value.__enter__ = lambda s: mock_file
        mock_sftp.open.return_value.__exit__ = MagicMock(return_value=False)
        manager._manager.open_sftp.return_value = mock_sftp
        manager.write_file("/home/test.txt", "content")

    def test_write_file_failure(self, manager):
        mock_sftp = MagicMock()
        mock_sftp.open.side_effect = Exception("write fail")
        manager._manager.open_sftp.return_value = mock_sftp
        with pytest.raises(RuntimeError, match="无法写入文件"):
            manager.write_file("/home/test.txt", "content")

    def test_create_file_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.create_file("/home/new.txt")

    def test_create_file_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法创建文件"):
            manager.create_file("/home/new.txt")

    def test_create_directory_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.create_directory("/home/newdir")

    def test_create_directory_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法创建目录"):
            manager.create_directory("/home/newdir")

    def test_delete_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.delete("/home/test.txt")

    def test_delete_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法删除"):
            manager.delete("/home/test.txt")

    def test_rename_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.rename("/home/a.txt", "/home/b.txt")

    def test_rename_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法重命名"):
            manager.rename("/home/a.txt", "/home/b.txt")

    def test_copy_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.copy("/home/a.txt", "/home/b.txt")

    def test_copy_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法复制"):
            manager.copy("/home/a.txt", "/home/b.txt")

    def test_chmod_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.chmod("/home/test.txt", "755")

    def test_chmod_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法修改权限"):
            manager.chmod("/home/test.txt", "755")

    def test_chown_success(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.chown("/home/test.txt", user="root")

    def test_chown_with_group(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.chown("/home/test.txt", user="root", group="root")

    def test_chown_no_args_raises(self, manager):
        with pytest.raises(ValueError, match="必须指定"):
            manager.chown("/home/test.txt")

    def test_chown_failure(self, manager):
        manager._manager.exec_command.return_value = (1, "", "")
        with pytest.raises(RuntimeError, match="无法修改所有者"):
            manager.chown("/home/test.txt", user="root")

    def test_upload_file_not_found(self, manager):
        with pytest.raises(FileNotFoundError, match="本地文件不存在"):
            manager.upload("/nonexistent/file.txt", "/remote/path")

    def test_upload_success(self, manager, tmp_path):
        local_file = tmp_path / "test.txt"
        local_file.write_text("hello")
        mock_sftp = MagicMock()
        manager._manager.open_sftp.return_value = mock_sftp
        manager._manager.exec_command.return_value = (0, "", "")
        manager.upload(str(local_file), "/remote/test.txt")

    def test_upload_failure(self, manager, tmp_path):
        local_file = tmp_path / "test.txt"
        local_file.write_text("hello")
        mock_sftp = MagicMock()
        mock_sftp.put.side_effect = Exception("upload fail")
        manager._manager.open_sftp.return_value = mock_sftp
        manager._manager.exec_command.return_value = (0, "", "")
        with pytest.raises(RuntimeError, match="上传失败"):
            manager.upload(str(local_file), "/remote/test.txt")

    def test_download_success(self, manager, tmp_path):
        mock_sftp = MagicMock()
        mock_stat = MagicMock()
        mock_stat.st_size = 100
        mock_sftp.stat.return_value = mock_stat
        manager._manager.open_sftp.return_value = mock_sftp
        manager.download("/remote/test.txt", str(tmp_path / "local.txt"))

    def test_download_failure(self, manager, tmp_path):
        mock_sftp = MagicMock()
        mock_sftp.get.side_effect = Exception("download fail")
        mock_sftp.stat.side_effect = Exception("no stat")
        manager._manager.open_sftp.return_value = mock_sftp
        with pytest.raises(RuntimeError, match="下载失败"):
            manager.download("/remote/test.txt", str(tmp_path / "local.txt"))

    def test_search_success(self, manager):
        search_output = "f\t100\t-rw-r--r--\t2025-01-15 10:30\t/home/test.txt\n"
        manager._manager.exec_command.return_value = (0, search_output, "")
        results = manager.search("/home", "*.txt")
        assert len(results) == 1

    def test_search_empty(self, manager):
        manager._manager.exec_command.return_value = (1, "", "error")
        results = manager.search("/home", "*.txt")
        assert results == []

    def test_search_with_file_type(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.search("/home", "*.txt", file_type="file")
        call_args = manager._manager.exec_command.call_args[0][0]
        assert "-type f" in call_args

    def test_search_with_directory_type(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.search("/home", "*", file_type="directory")
        call_args = manager._manager.exec_command.call_args[0][0]
        assert "-type d" in call_args

    def test_search_with_max_depth(self, manager):
        manager._manager.exec_command.return_value = (0, "", "")
        manager.search("/home", "*", max_depth=3)
        call_args = manager._manager.exec_command.call_args[0][0]
        assert "-maxdepth 3" in call_args

    def test_exec_command(self, manager):
        manager._manager.exec_command.return_value = (0, "output", "err")
        result = manager.exec_command("ls")
        assert result["exit_code"] == 0
        assert result["stdout"] == "output"

    def test_exec_batch(self, manager):
        manager._manager.exec_command.return_value = (0, "output", "err")
        results = manager.exec_batch(["ls", "pwd"])
        assert len(results) == 2

    def test_parse_find_ls_output(self, manager):
        output = "12345 0 root root 100 -rw-r--r-- 1 root root 100 Jan 15 10:30 /home/test.txt\n"
        results = manager._parse_find_ls_output(output)
        assert len(results) == 1
        assert results[0].name == "test.txt"
