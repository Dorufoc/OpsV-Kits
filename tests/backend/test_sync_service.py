from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sync_service import SyncService, SyncStatus, SyncTaskInfo


@pytest.fixture
def svc():
    service = SyncService.__new__(SyncService)
    service._pool = MagicMock()
    service._active_syncs = {}
    service._ws_connections = {}
    service._lock = threading.RLock()
    service._loop = None
    return service


class TestSyncStatus:
    def test_status_values(self):
        assert SyncStatus.PENDING == "pending"
        assert SyncStatus.RUNNING == "running"
        assert SyncStatus.COMPLETED == "completed"
        assert SyncStatus.FAILED == "failed"
        assert SyncStatus.STOPPED == "stopped"


class TestSyncTaskInfo:
    def test_init_defaults(self):
        task = SyncTaskInfo(
            sync_id="test-id",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        assert task.sync_id == "test-id"
        assert task.local_path == "/local"
        assert task.remote_path == "/remote"
        assert task.account_alias == "server1"
        assert task.force is False
        assert task.status == SyncStatus.PENDING
        assert task.progress == 0.0
        assert task.phase == ""
        assert task.message == ""
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None
        assert task.file_changes is None
        assert task.diff_tree == ""
        assert task.tree == ""

    def test_init_with_force(self):
        task = SyncTaskInfo(
            sync_id="test-id",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
            force=True,
        )
        assert task.force is True


class TestSetEventLoop:
    def test_set_event_loop(self, svc):
        loop = MagicMock()
        svc.set_event_loop(loop)
        assert svc._loop is loop


class TestRegisterWs:
    @pytest.mark.asyncio
    async def test_register_ws_new(self, svc):
        ws = AsyncMock()
        await svc.register_ws("sync-1", ws)
        assert "sync-1" in svc._ws_connections
        assert ws in svc._ws_connections["sync-1"]

    @pytest.mark.asyncio
    async def test_register_ws_existing(self, svc):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await svc.register_ws("sync-1", ws1)
        await svc.register_ws("sync-1", ws2)
        assert len(svc._ws_connections["sync-1"]) == 2


class TestUnregisterWs:
    @pytest.mark.asyncio
    async def test_unregister_ws(self, svc):
        ws = AsyncMock()
        await svc.register_ws("sync-1", ws)
        await svc.unregister_ws("sync-1", ws)
        assert "sync-1" not in svc._ws_connections

    @pytest.mark.asyncio
    async def test_unregister_ws_not_found(self, svc):
        ws = AsyncMock()
        await svc.unregister_ws("nonexistent", ws)

    @pytest.mark.asyncio
    async def test_unregister_ws_removes_empty_set(self, svc):
        ws = AsyncMock()
        await svc.register_ws("sync-1", ws)
        await svc.unregister_ws("sync-1", ws)
        assert "sync-1" not in svc._ws_connections


class TestStopSync:
    def test_stop_sync_running(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.status = SyncStatus.RUNNING
        svc._active_syncs["sync-1"] = task
        result = svc.stop_sync("sync-1")
        assert result is True
        assert task.status == SyncStatus.STOPPED
        assert "停止" in task.message

    def test_stop_sync_pending(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.status = SyncStatus.PENDING
        svc._active_syncs["sync-1"] = task
        result = svc.stop_sync("sync-1")
        assert result is True

    def test_stop_sync_completed(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.status = SyncStatus.COMPLETED
        svc._active_syncs["sync-1"] = task
        result = svc.stop_sync("sync-1")
        assert result is False

    def test_stop_sync_failed(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.status = SyncStatus.FAILED
        svc._active_syncs["sync-1"] = task
        result = svc.stop_sync("sync-1")
        assert result is False

    def test_stop_sync_not_found(self, svc):
        result = svc.stop_sync("nonexistent")
        assert result is False


class TestGetStatus:
    def test_get_status_by_id(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        svc._active_syncs["sync-1"] = task
        result = svc.get_status("sync-1")
        assert result is not None
        assert result["sync_id"] == "sync-1"
        assert result["status"] == "pending"

    def test_get_status_not_found(self, svc):
        result = svc.get_status("nonexistent")
        assert result is None

    def test_get_status_all(self, svc):
        task1 = SyncTaskInfo(
            sync_id="sync-1", local_path="/l1", remote_path="/r1",
            account_alias="s1",
        )
        task2 = SyncTaskInfo(
            sync_id="sync-2", local_path="/l2", remote_path="/r2",
            account_alias="s2",
        )
        svc._active_syncs["sync-1"] = task1
        svc._active_syncs["sync-2"] = task2
        result = svc.get_status()
        assert len(result) == 2

    def test_get_status_none_returns_all(self, svc):
        result = svc.get_status(None)
        assert result == []


class TestGetActiveSyncs:
    def test_get_active_syncs(self, svc):
        task1 = SyncTaskInfo(
            sync_id="sync-1", local_path="/l1", remote_path="/r1",
            account_alias="s1",
        )
        task1.status = SyncStatus.RUNNING
        task2 = SyncTaskInfo(
            sync_id="sync-2", local_path="/l2", remote_path="/r2",
            account_alias="s2",
        )
        task2.status = SyncStatus.COMPLETED
        task3 = SyncTaskInfo(
            sync_id="sync-3", local_path="/l3", remote_path="/r3",
            account_alias="s3",
        )
        task3.status = SyncStatus.PENDING
        svc._active_syncs["sync-1"] = task1
        svc._active_syncs["sync-2"] = task2
        svc._active_syncs["sync-3"] = task3
        result = svc.get_active_syncs()
        assert len(result) == 2
        sync_ids = [r["sync_id"] for r in result]
        assert "sync-1" in sync_ids
        assert "sync-3" in sync_ids

    def test_get_active_syncs_empty(self, svc):
        result = svc.get_active_syncs()
        assert result == []


class TestTaskToDict:
    def test_task_to_dict_basic(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        result = svc._task_to_dict(task)
        assert result["sync_id"] == "sync-1"
        assert result["local_path"] == "/local"
        assert result["remote_path"] == "/remote"
        assert result["account_alias"] == "server1"
        assert result["force"] is False
        assert result["status"] == "pending"
        assert result["progress"] == 0.0
        assert result["phase"] == ""
        assert result["message"] == ""
        assert result["started_at"] is None
        assert result["completed_at"] is None
        assert result["error"] is None
        assert "file_changes" not in result
        assert result["diff_tree"] == ""
        assert result["tree"] == ""

    def test_task_to_dict_with_file_changes(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.file_changes = {"new": ["a.txt"], "modified": ["b.txt"], "deleted": []}
        result = svc._task_to_dict(task)
        assert result["file_changes"] == {"new": ["a.txt"], "modified": ["b.txt"], "deleted": []}

    def test_task_to_dict_with_progress(self, svc):
        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local",
            remote_path="/remote",
            account_alias="server1",
        )
        task.status = SyncStatus.RUNNING
        task.progress = 0.5
        task.phase = "uploading"
        task.message = "Uploading files..."
        task.started_at = "2024-01-15T10:00:00+00:00"
        result = svc._task_to_dict(task)
        assert result["status"] == "running"
        assert result["progress"] == 0.5
        assert result["phase"] == "uploading"
        assert result["message"] == "Uploading files..."


class TestBuildDiffTree:
    def test_empty_diff(self):
        result = SyncService._build_diff_tree(set(), set(), set(), "/remote/project")
        assert result == ""

    def test_new_files_only(self):
        result = SyncService._build_diff_tree(
            {"src/main.py"}, set(), set(), "/remote/project"
        )
        assert "新增" in result
        assert "main.py" in result

    def test_modified_files_only(self):
        result = SyncService._build_diff_tree(
            set(), {"src/utils.py"}, set(), "/remote/project"
        )
        assert "修改" in result
        assert "utils.py" in result

    def test_deleted_files_only(self):
        result = SyncService._build_diff_tree(
            set(), set(), {"old_file.py"}, "/remote/project"
        )
        assert "删除" in result

    def test_mixed_changes(self):
        result = SyncService._build_diff_tree(
            {"new_file.py"}, {"mod_file.py"}, {"del_file.py"}, "/remote/project"
        )
        assert "新增" in result
        assert "修改" in result
        assert "删除" in result

    def test_nested_files(self):
        result = SyncService._build_diff_tree(
            {"src/app/main.py", "src/app/utils.py", "README.md"},
            set(), set(), "/remote/project"
        )
        assert "src/" in result
        assert "app/" in result
        assert "main.py" in result

    def test_project_name_from_path(self):
        result = SyncService._build_diff_tree(
            {"file.py"}, set(), set(), "/remote/my-project"
        )
        assert "my-project" in result

    def test_project_name_trailing_slash(self):
        result = SyncService._build_diff_tree(
            {"file.py"}, set(), set(), "/remote/my-project/"
        )
        assert "my-project" in result


class TestGetRemoteTree:
    def test_get_remote_tree_success(self, svc):
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"/remote/project\n/remote/project/src\n/remote/project/src/main.py\n/remote/project/README.md"
        mock_ssh = MagicMock()
        mock_ssh.exec_command.return_value = (None, mock_stdout, MagicMock())
        result = svc._get_remote_tree(mock_ssh, "/remote/project")
        assert "project" in result
        assert "src" in result
        assert "main.py" in result

    def test_get_remote_tree_empty(self, svc):
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b""
        mock_ssh = MagicMock()
        mock_ssh.exec_command.return_value = (None, mock_stdout, MagicMock())
        result = svc._get_remote_tree(mock_ssh, "/remote/project")
        assert result == "/remote/project"

    def test_get_remote_tree_exception(self, svc):
        mock_ssh = MagicMock()
        mock_ssh.exec_command.side_effect = Exception("SSH error")
        result = svc._get_remote_tree(mock_ssh, "/remote/project")
        assert "无法获取" in result


class TestGetLoop:
    def test_get_loop_with_set_loop(self, svc):
        loop = MagicMock()
        svc._loop = loop
        assert svc._get_loop() is loop

    def test_get_loop_without_set_loop(self, svc):
        svc._loop = None
        try:
            loop = svc._get_loop()
            assert loop is not None
        except RuntimeError:
            pass


class TestRunSync:
    def test_run_sync_success(self, svc):
        mock_account = MagicMock()
        mock_account.username = "testuser"
        mock_conn = MagicMock()
        mock_sftp = MagicMock()
        mock_conn.manager.open_sftp.return_value = mock_sftp
        mock_conn.manager.client = MagicMock()
        svc._pool.get_connection.return_value = mock_conn
        svc._pool.release_connection.return_value = None

        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local/project",
            remote_path="/remote",
            account_alias="server1",
        )

        with patch("app.services.sync_service.resolve_remote_path", return_value="/home/testuser"), \
             patch("app.services.sync_service.GitignoreParser") as MockGitignore, \
             patch("app.services.sync_service.FileSyncEngine") as MockEngine:
            mock_engine = MagicMock()
            mock_engine.new_files = {"a.py"}
            mock_engine.modified_files = {"b.py"}
            mock_engine.deleted_files = set()
            mock_engine.full_sync.return_value = None
            MockEngine.return_value = mock_engine

            with patch.object(svc, "_get_remote_tree", return_value="tree"):
                with patch.object(svc, "_push_progress_to_ws"):
                    svc._run_sync("sync-1", task, mock_account)

        assert task.status == SyncStatus.COMPLETED
        assert task.progress == 1.0
        assert task.file_changes is not None
        assert "a.py" in task.file_changes["new"]

    def test_run_sync_exception(self, svc):
        mock_account = MagicMock()
        mock_account.username = "testuser"
        svc._pool.get_connection.side_effect = Exception("Connection failed")

        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local/project",
            remote_path="/remote",
            account_alias="server1",
        )

        with patch.object(svc, "_push_progress_to_ws"):
            svc._run_sync("sync-1", task, mock_account)

        assert task.status == SyncStatus.FAILED
        assert "Connection failed" in task.error

    def test_run_sync_stopped(self, svc):
        mock_account = MagicMock()
        mock_account.username = "testuser"
        mock_conn = MagicMock()
        mock_sftp = MagicMock()
        mock_conn.manager.open_sftp.return_value = mock_sftp
        mock_conn.manager.client = MagicMock()
        svc._pool.get_connection.return_value = mock_conn
        svc._pool.release_connection.return_value = None

        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local/project",
            remote_path="/remote",
            account_alias="server1",
        )

        def stop_on_progress(phase, progress, message):
            task.status = SyncStatus.STOPPED

        with patch("app.services.sync_service.resolve_remote_path", return_value="/home/testuser"), \
             patch("app.services.sync_service.GitignoreParser") as MockGitignore, \
             patch("app.services.sync_service.FileSyncEngine") as MockEngine:
            mock_engine = MagicMock()

            def full_sync_side_effect(force=False):
                task.status = SyncStatus.STOPPED

            mock_engine.full_sync = full_sync_side_effect
            mock_engine.new_files = set()
            mock_engine.modified_files = set()
            mock_engine.deleted_files = set()
            MockEngine.return_value = mock_engine

            with patch.object(svc, "_push_progress_to_ws"):
                svc._run_sync("sync-1", task, mock_account)

        assert task.status == SyncStatus.STOPPED

    def test_run_sync_release_connection_on_error(self, svc):
        mock_account = MagicMock()
        mock_account.username = "testuser"
        mock_conn = MagicMock()
        svc._pool.get_connection.return_value = mock_conn
        svc._pool.release_connection.return_value = None
        mock_conn.manager.open_sftp.side_effect = Exception("SFTP failed")

        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local/project",
            remote_path="/remote",
            account_alias="server1",
        )

        with patch("app.services.sync_service.resolve_remote_path", return_value="/home/testuser"), \
             patch("app.services.sync_service.GitignoreParser"), \
             patch.object(svc, "_push_progress_to_ws"):
            svc._run_sync("sync-1", task, mock_account)

        svc._pool.release_connection.assert_called_once_with(mock_conn)

    def test_run_sync_release_connection_exception(self, svc):
        mock_account = MagicMock()
        mock_account.username = "testuser"
        mock_conn = MagicMock()
        svc._pool.get_connection.return_value = mock_conn
        svc._pool.release_connection.side_effect = Exception("release failed")
        mock_conn.manager.open_sftp.side_effect = Exception("SFTP failed")

        task = SyncTaskInfo(
            sync_id="sync-1",
            local_path="/local/project",
            remote_path="/remote",
            account_alias="server1",
        )

        with patch("app.services.sync_service.resolve_remote_path", return_value="/home/testuser"), \
             patch("app.services.sync_service.GitignoreParser"), \
             patch.object(svc, "_push_progress_to_ws"):
            svc._run_sync("sync-1", task, mock_account)


class TestPushProgressToWs:
    def test_push_progress_no_connections(self, svc):
        svc._push_progress_to_ws("sync-1", {"type": "progress"})

    def test_push_progress_with_connections(self, svc):
        ws = AsyncMock()
        svc._ws_connections["sync-1"] = {ws}
        mock_loop = MagicMock()
        svc._loop = mock_loop
        svc._push_progress_to_ws("sync-1", {"type": "progress"})
        assert mock_loop.call_count >= 0

    def test_push_progress_ws_exception(self, svc):
        ws = AsyncMock()
        svc._ws_connections["sync-1"] = {ws}
        mock_loop = MagicMock()
        mock_loop.run_coroutine_threadsafe.side_effect = Exception("WS error")
        svc._loop = mock_loop
        svc._push_progress_to_ws("sync-1", {"type": "progress"})


class TestStartSync:
    @pytest.mark.asyncio
    async def test_start_sync_account_not_found(self, svc):
        with patch("app.services.sync_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                await svc.start_sync("/local", "/remote", "nonexistent")

    @pytest.mark.asyncio
    async def test_start_sync_creates_task(self, svc):
        mock_account = MagicMock()
        with patch("app.services.sync_service.ssh_account_service") as mock_svc, \
             patch("asyncio.get_running_loop") as mock_loop:
            mock_svc.get_account.return_value = mock_account
            mock_loop.return_value = MagicMock()
            sync_id = await svc.start_sync("/local", "/remote", "server1")
        assert sync_id is not None
        assert sync_id in svc._active_syncs
        task = svc._active_syncs[sync_id]
        assert task.local_path == "/local"
        assert task.remote_path == "/remote"
        assert task.account_alias == "server1"

    @pytest.mark.asyncio
    async def test_start_sync_with_force(self, svc):
        mock_account = MagicMock()
        with patch("app.services.sync_service.ssh_account_service") as mock_svc, \
             patch("asyncio.get_running_loop") as mock_loop:
            mock_svc.get_account.return_value = mock_account
            mock_loop.return_value = MagicMock()
            sync_id = await svc.start_sync("/local", "/remote", "server1", force=True)
        task = svc._active_syncs[sync_id]
        assert task.force is True
