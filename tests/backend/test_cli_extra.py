from __future__ import annotations

import argparse
import sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.cli import (
    _cmd_deploy_vite,
    _cmd_sync,
    _cmd_build,
    _cmd_start,
    _cmd_account_add,
    _cmd_docker_ps,
    _cmd_docker_images,
    _cmd_docker_network_ls,
    _cmd_docker_volume_ls,
    _cmd_docker_build,
    _cmd_docker_exec,
    _cmd_docker_logs,
    _cmd_docker_info,
    _cmd_docker_install,
    _cmd_docker_start,
    _cmd_docker_stop,
    _cmd_docker_restart,
    _cmd_docker_kill,
    _cmd_docker_rm,
    _cmd_docker_rmi,
    _cmd_docker_prune,
    _cmd_docker_pull,
    _cmd_compose_up,
    _cmd_compose_down,
    _cmd_compose_ps,
    _cmd_compose_logs,
    _cmd_ssh,
    _cmd_remote_chmod,
    _cmd_remote_cp,
    _cmd_remote_exec,
    _cmd_remote_find,
)


class TestCmdDeployVite:
    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_completed(self, mock_alias, mock_lazy, capsys):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-1"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        completed_task = MagicMock()
        completed_task.status = "completed"
        completed_task.url = "http://nginx.example.com"
        completed_task.log = "build done"
        mock_vite.vite_deploy_service.get_task.return_value = completed_task
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            _cmd_deploy_vite(args)
        captured = capsys.readouterr()
        assert "Vite 部署成功" in captured.out

    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_failed(self, mock_alias, mock_lazy, capsys):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-2"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        failed_task = MagicMock()
        failed_task.status = "failed"
        failed_task.error = "build error"
        failed_task.message = ""
        failed_task.url = None
        failed_task.log = ""
        mock_vite.vite_deploy_service.get_task.return_value = failed_task
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            with pytest.raises(SystemExit):
                _cmd_deploy_vite(args)

    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_stopped(self, mock_alias, mock_lazy, capsys):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-3"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        stopped_task = MagicMock()
        stopped_task.status = "stopped"
        stopped_task.url = None
        stopped_task.log = ""
        mock_vite.vite_deploy_service.get_task.return_value = stopped_task
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            with pytest.raises(SystemExit):
                _cmd_deploy_vite(args)

    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_task_lost(self, mock_alias, mock_lazy, capsys):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-4"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        mock_vite.vite_deploy_service.get_task.return_value = None
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            with pytest.raises(SystemExit):
                _cmd_deploy_vite(args)

    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_keyboard_interrupt(self, mock_alias, mock_lazy):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-5"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        call_count = [0]
        def get_task_side_effect(tid):
            call_count[0] += 1
            if call_count[0] > 1:
                raise KeyboardInterrupt
            running = MagicMock()
            running.status = "running"
            running.log = ""
            return running
        mock_vite.vite_deploy_service.get_task.side_effect = get_task_side_effect
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            with pytest.raises(SystemExit):
                _cmd_deploy_vite(args)

    @patch("app.cli._lazy")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_deploy_vite_completed_no_url(self, mock_alias, mock_lazy, capsys):
        mock_vite = MagicMock()
        task = MagicMock()
        task.task_id = "task-6"
        task.log = ""
        task.add_callback = MagicMock()
        mock_vite.vite_deploy_service.full_deploy.return_value = task
        completed_task = MagicMock()
        completed_task.status = "completed"
        completed_task.url = None
        completed_task.log = ""
        mock_vite.vite_deploy_service.get_task.return_value = completed_task
        mock_lazy.return_value = mock_vite
        args = argparse.Namespace(alias=None, path=".", port=8080, force=False, config=None)
        with patch("time.sleep"):
            _cmd_deploy_vite(args)
        captured = capsys.readouterr()
        assert "Vite 部署成功" in captured.out


class TestCmdSyncSuccess:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_sync_completed(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}}
        mock_sync_svc = MagicMock()
        mock_sync_svc.sync_service.start_sync = AsyncMock(return_value="sync-1")
        mock_sync_svc.sync_service.set_event_loop = MagicMock()
        mock_sync_svc.sync_service.get_status.return_value = {"status": "completed", "message": "done"}
        mock_lazy.return_value = mock_sync_svc
        args = argparse.Namespace(config=None, local=None, remote=None, alias=None, force=False)
        _cmd_sync(args)
        captured = capsys.readouterr()
        assert "同步完成" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_sync_in_progress(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}}
        mock_sync_svc = MagicMock()
        mock_sync_svc.sync_service.start_sync = AsyncMock(return_value="sync-2")
        mock_sync_svc.sync_service.set_event_loop = MagicMock()
        mock_sync_svc.sync_service.get_status.return_value = {"status": "running", "message": "in progress"}
        mock_lazy.return_value = mock_sync_svc
        args = argparse.Namespace(config=None, local=None, remote=None, alias=None, force=False)
        _cmd_sync(args)
        captured = capsys.readouterr()
        assert "同步状态" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_sync_no_status(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}}
        mock_sync_svc = MagicMock()
        mock_sync_svc.sync_service.start_sync = AsyncMock(return_value="sync-3")
        mock_sync_svc.sync_service.set_event_loop = MagicMock()
        mock_sync_svc.sync_service.get_status.return_value = None
        mock_lazy.return_value = mock_sync_svc
        args = argparse.Namespace(config=None, local=None, remote=None, alias=None, force=False)
        _cmd_sync(args)
        captured = capsys.readouterr()
        assert "同步任务已启动" in captured.out


class TestCmdBuildStderr:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_build_failure_with_stderr(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "build": {"enabled": True, "command": "make"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (1, "", "compilation error output")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        with pytest.raises(SystemExit):
            _cmd_build(args)
        captured = capsys.readouterr()
        assert "compilation error output" in captured.out


class TestCmdStartOutput:
    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_start_success_with_stdout(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "run": {"mode": "remote", "remote_command": "python main.py"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (0, "Server started on port 8000", "")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        _cmd_start(args)
        captured = capsys.readouterr()
        assert "Server started on port 8000" in captured.out

    @patch("app.cli._get_account_alias", return_value="test-alias")
    @patch("app.cli._load_config")
    @patch("app.cli._lazy")
    def test_start_failure_with_stderr(self, mock_lazy, mock_load, mock_alias, capsys):
        mock_load.return_value = {"sync": {"remote_dir": "/remote"}, "run": {"mode": "remote", "remote_command": "python main.py"}}
        mock_svc = MagicMock()
        conn = MagicMock()
        conn.manager.exec_command.return_value = (1, "", "ImportError: no module")
        mock_svc.ssh_account_service.pool.get_connection.return_value = conn
        mock_svc.ssh_account_service.get_account.return_value = MagicMock()
        mock_lazy.return_value = mock_svc
        args = argparse.Namespace(config=None, alias=None, remote=None)
        with pytest.raises(SystemExit):
            _cmd_start(args)
        captured = capsys.readouterr()
        assert "ImportError" in captured.out


class TestCmdAccountAddAgent:
    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_add_agent(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "agent-acct"
        mock_svc.return_value.create_account.return_value = acct
        mock_lazy.return_value.SSHAccountCreate = MagicMock(return_value=MagicMock())
        inputs = iter(["agent", "1.2.3.4", "22", "root", "3", "n", ""])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_add(argparse.Namespace())
        captured = capsys.readouterr()
        assert "创建成功" in captured.out

    @patch("app.cli._lazy")
    @patch("app.cli._get_ssh_account_service")
    def test_account_add_key_with_passphrase(self, mock_svc, mock_lazy, capsys):
        acct = MagicMock()
        acct.alias = "key-acct"
        mock_svc.return_value.create_account.return_value = acct
        mock_lazy.return_value.SSHAccountCreate = MagicMock(return_value=MagicMock())
        inputs = iter(["key2", "1.2.3.4", "22", "root", "2", "/path/key", "mypass", "y", "mygroup"])
        with patch("builtins.input", lambda *a, **kw: next(inputs)):
            _cmd_account_add(argparse.Namespace())
        captured = capsys.readouterr()
        assert "创建成功" in captured.out


class TestCmdDockerPsLowercase:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_ps_lowercase_keys(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_containers.return_value = [
            {"id": "abc123def456", "name": "web", "image": "nginx", "status": "Up", "ports": "80"}
        ]
        _cmd_docker_ps(argparse.Namespace(alias=None, config=None, all=False))
        captured = capsys.readouterr()
        assert "web" in captured.out


class TestCmdDockerImagesLowercase:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_images_lowercase_keys(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_images.return_value = [
            {"repository": "nginx", "tag": "latest", "id": "abc123", "size": "100MB"}
        ]
        _cmd_docker_images(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "nginx" in captured.out


class TestCmdDockerNetworkLsLowercase:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_network_ls_lowercase_keys(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_networks.return_value = [
            {"id": "net123", "name": "bridge", "driver": "bridge", "scope": "local"}
        ]
        _cmd_docker_network_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "bridge" in captured.out


class TestCmdDockerVolumeLsLowercase:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_volume_ls_lowercase_keys(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.list_volumes.return_value = [
            {"name": "mydata", "driver": "local", "mountpoint": "/var/lib/docker/volumes/mydata"}
        ]
        _cmd_docker_volume_ls(argparse.Namespace(alias=None, config=None))
        captured = capsys.readouterr()
        assert "mydata" in captured.out


class TestCmdDockerBuildWithDockerfile:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_build_with_dockerfile(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.build_image.return_value = "built"
        _cmd_docker_build(argparse.Namespace(tag="myapp:v1", path=".", dockerfile="./Dockerfile.prod", alias=None, config=None))
        mock_ds.return_value.build_image.assert_called_once_with("test-alias", "myapp:v1", "./Dockerfile.prod", ".")
        captured = capsys.readouterr()
        assert "构建完成" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_build_with_result(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.build_image.return_value = "Successfully built abc123"
        _cmd_docker_build(argparse.Namespace(tag="myapp:v1", path=".", dockerfile=None, alias=None, config=None))
        captured = capsys.readouterr()
        assert "Successfully built abc123" in captured.out


class TestCmdDockerExecWithStderr:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_exec_with_stderr(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.exec_in_container.return_value = (0, "", "warning message")
        _cmd_docker_exec(argparse.Namespace(container_id="abc", command="ls", alias=None, config=None))
        captured = capsys.readouterr()
        assert "warning message" in captured.err

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_exec_no_command_default(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.exec_in_container.return_value = (0, "root@abc:/#", "")
        _cmd_docker_exec(argparse.Namespace(container_id="abc", command=None, alias=None, config=None))
        mock_ds.return_value.exec_in_container.assert_called_once_with("test-alias", "abc", "/bin/bash")


class TestCmdDockerLogsError:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_logs_error(self, mock_alias, mock_ds):
        mock_ds.return_value.get_container_logs.side_effect = Exception("container not found")
        with pytest.raises(SystemExit):
            _cmd_docker_logs(argparse.Namespace(container_id="abc", n=100, alias=None, config=None))


class TestCmdDockerErrorPaths:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_info_error(self, mock_alias, mock_ds):
        mock_ds.return_value.check_docker_installed.side_effect = Exception("conn fail")
        with pytest.raises(SystemExit):
            _cmd_docker_info(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_install_error(self, mock_alias, mock_ds):
        mock_ds.return_value.install_docker.side_effect = Exception("install fail")
        with pytest.raises(SystemExit):
            _cmd_docker_install(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_start_error(self, mock_alias, mock_ds):
        mock_ds.return_value.start_container.side_effect = Exception("start fail")
        with pytest.raises(SystemExit):
            _cmd_docker_start(argparse.Namespace(container_id="abc", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_stop_error(self, mock_alias, mock_ds):
        mock_ds.return_value.stop_container.side_effect = Exception("stop fail")
        with pytest.raises(SystemExit):
            _cmd_docker_stop(argparse.Namespace(container_id="abc", timeout=None, alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_restart_error(self, mock_alias, mock_ds):
        mock_ds.return_value.restart_container.side_effect = Exception("restart fail")
        with pytest.raises(SystemExit):
            _cmd_docker_restart(argparse.Namespace(container_id="abc", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_kill_error(self, mock_alias, mock_ds):
        mock_ds.return_value.kill_container.side_effect = Exception("kill fail")
        with pytest.raises(SystemExit):
            _cmd_docker_kill(argparse.Namespace(container_id="abc", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_rm_error(self, mock_alias, mock_ds):
        mock_ds.return_value.remove_container.side_effect = Exception("rm fail")
        with pytest.raises(SystemExit):
            _cmd_docker_rm(argparse.Namespace(container_id="abc", force=False, alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_rmi_error(self, mock_alias, mock_ds):
        mock_ds.return_value.remove_image.side_effect = Exception("rmi fail")
        with pytest.raises(SystemExit):
            _cmd_docker_rmi(argparse.Namespace(image_id="abc123", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_prune_error(self, mock_alias, mock_ds):
        mock_ds.return_value.prune_images.side_effect = Exception("prune fail")
        with pytest.raises(SystemExit):
            _cmd_docker_prune(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_pull_error(self, mock_alias, mock_ds):
        mock_ds.return_value.pull_image.side_effect = Exception("pull fail")
        with pytest.raises(SystemExit):
            _cmd_docker_pull(argparse.Namespace(image="nginx:latest", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_ps_error(self, mock_alias, mock_ds):
        mock_ds.return_value.list_containers.side_effect = Exception("ps fail")
        with pytest.raises(SystemExit):
            _cmd_docker_ps(argparse.Namespace(alias=None, config=None, all=False))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_images_error(self, mock_alias, mock_ds):
        mock_ds.return_value.list_images.side_effect = Exception("images fail")
        with pytest.raises(SystemExit):
            _cmd_docker_images(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_network_ls_error(self, mock_alias, mock_ds):
        mock_ds.return_value.list_networks.side_effect = Exception("net fail")
        with pytest.raises(SystemExit):
            _cmd_docker_network_ls(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_volume_ls_error(self, mock_alias, mock_ds):
        mock_ds.return_value.list_volumes.side_effect = Exception("vol fail")
        with pytest.raises(SystemExit):
            _cmd_docker_volume_ls(argparse.Namespace(alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_docker_build_error(self, mock_alias, mock_ds):
        mock_ds.return_value.build_image.side_effect = Exception("build fail")
        with pytest.raises(SystemExit):
            _cmd_docker_build(argparse.Namespace(tag="myapp:v1", path=".", dockerfile=None, alias=None, config=None))


class TestCmdComposeResultOutput:
    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_up_with_result(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_up.return_value = "Creating network... Done"
        _cmd_compose_up(argparse.Namespace(project_path=".", detach=False, alias=None, config=None))
        captured = capsys.readouterr()
        assert "Creating network" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_up_no_result(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_up.return_value = ""
        _cmd_compose_up(argparse.Namespace(project_path=".", detach=False, alias=None, config=None))
        captured = capsys.readouterr()
        assert "Compose 已启动" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_up_error(self, mock_alias, mock_ds):
        mock_ds.return_value.compose_up.side_effect = Exception("compose fail")
        with pytest.raises(SystemExit):
            _cmd_compose_up(argparse.Namespace(project_path=".", detach=False, alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_down_with_result(self, mock_alias, mock_ds, capsys):
        mock_ds.return_value.compose_down.return_value = "Removing container... Done"
        _cmd_compose_down(argparse.Namespace(project_path=".", alias=None, config=None))
        captured = capsys.readouterr()
        assert "Removing container" in captured.out

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_down_error(self, mock_alias, mock_ds):
        mock_ds.return_value.compose_down.side_effect = Exception("down fail")
        with pytest.raises(SystemExit):
            _cmd_compose_down(argparse.Namespace(project_path=".", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_ps_error(self, mock_alias, mock_ds):
        mock_ds.return_value.compose_ps.side_effect = Exception("ps fail")
        with pytest.raises(SystemExit):
            _cmd_compose_ps(argparse.Namespace(project_path=".", alias=None, config=None))

    @patch("app.cli._get_docker_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_compose_logs_error(self, mock_alias, mock_ds):
        mock_ds.return_value.compose_logs.side_effect = Exception("logs fail")
        with pytest.raises(SystemExit):
            _cmd_compose_logs(argparse.Namespace(project_path=".", alias=None, config=None))


class TestCmdSshExtra:
    @patch("app.cli.webbrowser")
    @patch("app.cli._lazy")
    def test_ssh_with_alias_browser(self, mock_lazy, mock_browser, capsys):
        mock_webssh = MagicMock()
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias="prod", host=None, port=None, user=None, password=None, auth_type=None, browser=True, session_id=None)
        _cmd_ssh(args)
        mock_browser.open.assert_called_once_with("http://localhost:8000/webssh")
        captured = capsys.readouterr()
        assert "在浏览器中打开" in captured.out

    @patch("app.cli._lazy")
    def test_ssh_host_no_user(self, mock_lazy, capsys):
        mock_webssh = MagicMock()
        mock_webssh.WebSSHConnectRequest = MagicMock
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd=None, alias=None, host="1.2.3.4", port=22, user=None, password=None, auth_type=None, browser=False, session_id=None)
        with pytest.raises(SystemExit):
            _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "请指定" in captured.err

    @patch("app.cli._lazy")
    def test_ssh_sessions_with_data(self, mock_lazy, capsys):
        session = MagicMock()
        session.session_id = "abc123456789def"
        session.account_alias = "prod"
        session.host = "1.2.3.4"
        session.username = "root"
        session.status = MagicMock(value="connected")
        mock_webssh = MagicMock()
        mock_webssh.webssh_service.list_sessions.return_value = [session]
        mock_lazy.return_value = mock_webssh
        args = argparse.Namespace(subcmd="sessions", alias=None, host=None, port=None, user=None, password=None, auth_type=None, browser=False, session_id=None)
        _cmd_ssh(args)
        captured = capsys.readouterr()
        assert "abc1" in captured.out


class TestCmdRemoteExtraErrors:
    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_chmod_error(self, mock_alias, mock_fms):
        mock_fms.return_value.chmod.side_effect = Exception("chmod fail")
        with pytest.raises(SystemExit):
            _cmd_remote_chmod(argparse.Namespace(mode="755", path="/tmp/script.sh", alias=None, config=None))

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_cp_error(self, mock_alias, mock_fms):
        mock_fms.return_value.copy.side_effect = Exception("cp fail")
        with pytest.raises(SystemExit):
            _cmd_remote_cp(argparse.Namespace(src="/a", dst="/b", alias=None, config=None))

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_exec_error(self, mock_alias, mock_fms):
        mock_fms.return_value.exec_command.side_effect = Exception("exec fail")
        with pytest.raises(SystemExit):
            _cmd_remote_exec(argparse.Namespace(command="ls", alias=None, config=None))

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_find_error(self, mock_alias, mock_fms):
        mock_fms.return_value.search.side_effect = Exception("find fail")
        with pytest.raises(SystemExit):
            _cmd_remote_find(argparse.Namespace(path="/", name="*.log", alias=None, config=None))

    @patch("app.cli._get_file_manager_service")
    @patch("app.cli._get_account_alias", return_value="test-alias")
    def test_remote_find_with_dir_result(self, mock_alias, mock_fms, capsys):
        result = MagicMock()
        result.path = "/var/log"
        result.is_dir = True
        result.size = 4096
        result.permissions = "rwxr-xr-x"
        mock_fms.return_value.search.return_value = [result]
        _cmd_remote_find(argparse.Namespace(path="/var", name="log", alias=None, config=None))
        captured = capsys.readouterr()
        assert "/var/log" in captured.out
