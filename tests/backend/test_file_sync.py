from unittest.mock import MagicMock, patch, call
import os
import stat
import tempfile

import pytest

from app.core.file_sync import FileSyncEngine


def _make_sftp():
    return MagicMock()


def _make_gitignore_parser():
    parser = MagicMock()
    parser.is_ignored.return_value = False
    return parser


def _make_engine(local_path=None, remote_path="/remote", sftp=None, gitignore_parser=None, progress_callback=None):
    if local_path is None:
        local_path = tempfile.mkdtemp()
    if sftp is None:
        sftp = _make_sftp()
    if gitignore_parser is None:
        gitignore_parser = _make_gitignore_parser()
    return FileSyncEngine(local_path, remote_path, sftp, gitignore_parser, progress_callback)


class TestFileSyncEngineInit:
    def test_init_sets_paths(self):
        sftp = _make_sftp()
        parser = _make_gitignore_parser()
        engine = FileSyncEngine("/local", "/remote/", sftp, parser)
        assert engine._local_path == os.path.abspath("/local")
        assert engine._remote_path == "/remote"

    def test_init_default_state(self):
        engine = _make_engine()
        assert engine.stopped is False
        assert engine.new_files == set()
        assert engine.modified_files == set()
        assert engine.deleted_files == set()

    def test_init_with_progress_callback(self):
        cb = MagicMock()
        engine = _make_engine(progress_callback=cb)
        assert engine._progress_callback is cb


class TestFileSyncEngineProperties:
    def test_stopped_property(self):
        engine = _make_engine()
        assert engine.stopped is False
        engine._stopped = True
        assert engine.stopped is True

    def test_new_files_returns_copy(self):
        engine = _make_engine()
        engine._new_files.add("a.txt")
        nf = engine.new_files
        nf.add("b.txt")
        assert "b.txt" not in engine._new_files

    def test_modified_files_returns_copy(self):
        engine = _make_engine()
        engine._modified_files.add("a.txt")
        mf = engine.modified_files
        mf.add("b.txt")
        assert "b.txt" not in engine._modified_files

    def test_deleted_files_returns_copy(self):
        engine = _make_engine()
        engine._deleted_files.add("a.txt")
        df = engine.deleted_files
        df.add("b.txt")
        assert "b.txt" not in engine._deleted_files


class TestFileSyncEngineStop:
    def test_stop_sets_stopped(self):
        engine = _make_engine()
        engine.stop()
        assert engine.stopped is True


class TestFileSyncEngineReport:
    def test_report_calls_callback(self):
        cb = MagicMock()
        engine = _make_engine(progress_callback=cb)
        engine._report("scan", 0.5, "msg")
        cb.assert_called_once_with("scan", 0.5, "msg")

    def test_report_no_callback(self):
        engine = _make_engine()
        engine._report("scan", 0.5, "msg")


class TestFileSyncEngineScanLocal:
    def test_scan_local_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = _make_engine(local_path=tmpdir)
            files, sizes, dirs = engine._scan_local()
            assert files == set()
            assert sizes == {}
            assert dirs == set()

    def test_scan_local_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
            engine = _make_engine(local_path=tmpdir)
            files, sizes, dirs = engine._scan_local()
            assert "test.txt" in files
            assert sizes["test.txt"] == 5

    def test_scan_local_skips_dot_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dot_dir = os.path.join(tmpdir, ".hidden")
            os.makedirs(dot_dir)
            with open(os.path.join(dot_dir, "secret.txt"), "w") as f:
                f.write("x")
            engine = _make_engine(local_path=tmpdir)
            files, sizes, dirs = engine._scan_local()
            assert "secret.txt" not in files

    def test_scan_local_skips_gitignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "ignored.txt"), "w") as f:
                f.write("x")
            parser = _make_gitignore_parser()
            parser.is_ignored.side_effect = lambda p, is_dir=False: p == "ignored.txt"
            engine = _make_engine(local_path=tmpdir, gitignore_parser=parser)
            files, sizes, dirs = engine._scan_local()
            assert "ignored.txt" not in files

    def test_scan_local_with_subdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "sub")
            os.makedirs(sub)
            with open(os.path.join(sub, "file.txt"), "w") as f:
                f.write("data")
            engine = _make_engine(local_path=tmpdir)
            files, sizes, dirs = engine._scan_local()
            assert "sub/file.txt" in files
            assert "sub" in dirs

    def test_scan_local_oserror(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "bad.txt")
            with open(fpath, "w") as f:
                f.write("x")
            engine = _make_engine(local_path=tmpdir)
            with patch("os.stat", side_effect=OSError("fail")):
                files, sizes, dirs = engine._scan_local()
            assert "bad.txt" not in files


class TestFileSyncEngineScanRemote:
    def test_scan_remote_empty(self):
        sftp = _make_sftp()
        sftp.listdir_attr.return_value = []
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert files == set()
        assert sizes == {}
        assert dirs == set()

    def test_scan_remote_file_not_found(self):
        sftp = _make_sftp()
        sftp.listdir_attr.side_effect = FileNotFoundError("no dir")
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert files == set()

    def test_scan_remote_with_files(self):
        sftp = _make_sftp()
        entry = MagicMock()
        entry.filename = "test.txt"
        entry.st_mode = 0o100644
        entry.st_size = 100
        sftp.listdir_attr.return_value = [entry]
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert "test.txt" in files
        assert sizes["test.txt"] == 100

    def test_scan_remote_skips_dot_files(self):
        sftp = _make_sftp()
        entry = MagicMock()
        entry.filename = ".hidden"
        entry.st_mode = 0o100644
        entry.st_size = 10
        sftp.listdir_attr.return_value = [entry]
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert ".hidden" not in files

    def test_scan_remote_with_directory(self):
        sftp = _make_sftp()
        dir_entry = MagicMock()
        dir_entry.filename = "subdir"
        dir_entry.st_mode = 0o40755
        dir_entry.st_size = 4096
        inner_entry = MagicMock()
        inner_entry.filename = "inner"
        inner_entry.st_mode = 0o40755
        inner_entry.st_size = 4096
        sftp.listdir_attr.side_effect = [
            [dir_entry],
            [inner_entry],
            [],
        ]
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert "subdir/inner" in dirs

    def test_scan_remote_none_st_mode(self):
        sftp = _make_sftp()
        entry = MagicMock()
        entry.filename = "file.txt"
        entry.st_mode = None
        entry.st_size = 50
        sftp.listdir_attr.return_value = [entry]
        engine = _make_engine(sftp=sftp)
        files, sizes, dirs = engine._scan_remote()
        assert "file.txt" in files


class TestFileSyncEngineCreateRemoteDirs:
    def test_create_remote_dirs_existing(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._create_remote_dirs({"sub"})
        sftp.stat.assert_called()

    def test_create_remote_dirs_new(self):
        sftp = _make_sftp()
        sftp.stat.side_effect = FileNotFoundError("no")
        engine = _make_engine(sftp=sftp)
        engine._create_remote_dirs({"sub"})
        sftp.mkdir.assert_called()

    def test_create_remote_dirs_mkdir_oserror(self):
        sftp = _make_sftp()
        sftp.stat.side_effect = FileNotFoundError("no")
        sftp.mkdir.side_effect = OSError("fail")
        engine = _make_engine(sftp=sftp)
        engine._create_remote_dirs({"sub"})

    def test_create_remote_dirs_stat_oserror(self):
        sftp = _make_sftp()
        sftp.stat.side_effect = OSError("fail")
        engine = _make_engine(sftp=sftp)
        engine._create_remote_dirs({"sub"})

    def test_create_remote_dirs_stopped(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._stopped = True
        engine._create_remote_dirs({"sub"})
        sftp.stat.assert_not_called()


class TestFileSyncEngineUploadFiles:
    def test_upload_files_empty(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._upload_files(set())

    def test_upload_files_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            engine._upload_files({"test.txt"})
            sftp.put.assert_called_once()

    def test_upload_files_not_found(self):
        sftp = _make_sftp()
        sftp.put.side_effect = FileNotFoundError("no file")
        engine = _make_engine(sftp=sftp)
        engine._upload_files({"missing.txt"})

    def test_upload_files_put_exception_then_putfo_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
            sftp = _make_sftp()
            sftp.put.side_effect = Exception("put fail")
            engine = _make_engine(local_path=tmpdir, sftp=sftp)
            engine._upload_files({"test.txt"})
            sftp.putfo.assert_called_once()

    def test_upload_files_put_exception_putfo_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello")
            sftp = _make_sftp()
            sftp.put.side_effect = Exception("put fail")
            sftp.putfo.side_effect = Exception("putfo fail")
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            engine._upload_files({"test.txt"})
            report_calls = [c for c in cb.call_args_list if c[0][0] == "upload"]
            assert any("失败" in c[0][2] for c in report_calls)

    def test_upload_files_stopped(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._stopped = True
        engine._upload_files({"test.txt"})
        sftp.put.assert_not_called()

    def test_upload_files_modified_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "mod.txt")
            with open(fpath, "w") as f:
                f.write("data")
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            engine._modified_files.add("mod.txt")
            engine._upload_files({"mod.txt"})
            report_calls = [c for c in cb.call_args_list if c[0][0] == "upload" and "修改" in c[0][2]]
            assert len(report_calls) > 0


class TestFileSyncEngineEnsureRemoteDir:
    def test_ensure_remote_dir_empty(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._ensure_remote_dir("file.txt")

    def test_ensure_remote_dir_existing(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._ensure_remote_dir("/remote/sub/file.txt")
        sftp.stat.assert_called()

    def test_ensure_remote_dir_new(self):
        sftp = _make_sftp()
        sftp.stat.side_effect = FileNotFoundError("no")
        engine = _make_engine(sftp=sftp)
        engine._ensure_remote_dir("/remote/sub/file.txt")
        sftp.mkdir.assert_called()

    def test_ensure_remote_dir_mkdir_oserror(self):
        sftp = _make_sftp()
        sftp.stat.side_effect = FileNotFoundError("no")
        sftp.mkdir.side_effect = OSError("fail")
        engine = _make_engine(sftp=sftp)
        engine._ensure_remote_dir("/remote/sub/file.txt")


class TestFileSyncEngineDeleteFiles:
    def test_delete_files_success(self):
        sftp = _make_sftp()
        cb = MagicMock()
        engine = _make_engine(sftp=sftp, progress_callback=cb)
        engine._delete_files({"old.txt"})
        sftp.remove.assert_called_once()

    def test_delete_files_not_found(self):
        sftp = _make_sftp()
        sftp.remove.side_effect = FileNotFoundError("no")
        engine = _make_engine(sftp=sftp)
        engine._delete_files({"old.txt"})

    def test_delete_files_exception(self):
        sftp = _make_sftp()
        sftp.remove.side_effect = Exception("fail")
        engine = _make_engine(sftp=sftp)
        engine._delete_files({"old.txt"})

    def test_delete_files_stopped(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._stopped = True
        engine._delete_files({"old.txt"})
        sftp.remove.assert_not_called()


class TestFileSyncEngineDeleteEmptyDirs:
    def test_delete_empty_dirs_success(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._delete_empty_dirs({"sub"})
        sftp.rmdir.assert_called_once()

    def test_delete_empty_dirs_exception(self):
        sftp = _make_sftp()
        sftp.rmdir.side_effect = Exception("fail")
        engine = _make_engine(sftp=sftp)
        engine._delete_empty_dirs({"sub"})

    def test_delete_empty_dirs_stopped(self):
        sftp = _make_sftp()
        engine = _make_engine(sftp=sftp)
        engine._stopped = True
        engine._delete_empty_dirs({"sub"})
        sftp.rmdir.assert_not_called()


class TestFileSyncEngineFullSync:
    def test_full_sync_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            file_entry = MagicMock()
            file_entry.filename = "test.txt"
            file_entry.st_mode = 0o100644
            file_entry.st_size = 0
            sftp.listdir_attr.return_value = [file_entry]
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("")
            engine.full_sync()
            complete_calls = [c for c in cb.call_args_list if c[0][0] == "complete"]
            assert len(complete_calls) > 0

    def test_full_sync_stopped_after_local_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            engine = _make_engine(local_path=tmpdir, sftp=sftp)
            original_scan_local = engine._scan_local
            def scan_and_stop():
                engine._stopped = True
                return original_scan_local()
            engine._scan_local = scan_and_stop
            engine.full_sync()
            sftp.listdir_attr.assert_not_called()

    def test_full_sync_stopped_after_remote_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            sftp.listdir_attr.return_value = []
            engine = _make_engine(local_path=tmpdir, sftp=sftp)
            original_scan_remote = engine._scan_remote
            def scan_and_stop():
                engine._stopped = True
                return original_scan_remote()
            engine._scan_remote = scan_and_stop
            engine.full_sync()

    def test_full_sync_stopped_during_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            sftp.listdir_attr.return_value = []
            engine = _make_engine(local_path=tmpdir, sftp=sftp)
            with open(os.path.join(tmpdir, "a.txt"), "w") as f:
                f.write("x")
            with open(os.path.join(tmpdir, "b.txt"), "w") as f:
                f.write("y")
            engine._stopped = True
            engine.full_sync()

    def test_full_sync_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            sftp.listdir_attr.return_value = []
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("hello")
            engine.full_sync(force=True)
            sftp.put.assert_called()

    def test_full_sync_with_deletions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            remote_entry = MagicMock()
            remote_entry.filename = "old.txt"
            remote_entry.st_mode = 0o100644
            remote_entry.st_size = 10
            sftp.listdir_attr.return_value = [remote_entry]
            engine.full_sync()
            sftp.remove.assert_called()

    def test_full_sync_stopped_before_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            engine = _make_engine(local_path=tmpdir, sftp=sftp)
            remote_entry = MagicMock()
            remote_entry.filename = "old.txt"
            remote_entry.st_mode = 0o100644
            remote_entry.st_size = 10
            sftp.listdir_attr.return_value = [remote_entry]
            original_upload = engine._upload_files
            def upload_and_stop(files):
                engine._stopped = True
                original_upload(files)
            engine._upload_files = upload_and_stop
            engine.full_sync()

    def test_full_sync_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("hello world")
            remote_entry = MagicMock()
            remote_entry.filename = "test.txt"
            remote_entry.st_mode = 0o100644
            remote_entry.st_size = 5
            sftp.listdir_attr.return_value = [remote_entry]
            engine.full_sync()
            assert "test.txt" in engine.modified_files

    def test_full_sync_progress_check_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sftp = _make_sftp()
            cb = MagicMock()
            engine = _make_engine(local_path=tmpdir, sftp=sftp, progress_callback=cb)
            for i in range(55):
                with open(os.path.join(tmpdir, f"file{i:03d}.txt"), "w") as f:
                    f.write("x")
            remote_entries = []
            for i in range(55):
                entry = MagicMock()
                entry.filename = f"file{i:03d}.txt"
                entry.st_mode = 0o100644
                entry.st_size = 1
                remote_entries.append(entry)
            sftp.listdir_attr.return_value = remote_entries
            engine.full_sync()
            diff_calls = [c for c in cb.call_args_list if c[0][0] == "diff" and "检查更新" in c[0][2]]
            assert len(diff_calls) > 0
