import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestVerifyAccount:
    @patch("app.api.routes.git_integration.ssh_account_service")
    def test_account_not_found(self, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post(
            "/api/git/repo/init",
            json={"account_alias": "missing", "repo_path": "/repo"},
        )
        assert resp.status_code == 404


class TestRepoInit:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_init_repo_success(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.init_repo.return_value = {"success": True, "path": "/repo"}
        resp = client.post(
            "/api/git/repo/init",
            json={"account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_init_repo_with_gitignore(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.init_repo.return_value = {"success": True}
        resp = client.post(
            "/api/git/repo/init",
            json={"account_alias": "srv1", "repo_path": "/repo", "gitignore_template": "python"},
        )
        assert resp.status_code == 200
        mock_git.init_repo.assert_called_with("srv1", "/repo", "python")

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_init_repo_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.init_repo.side_effect = Exception("init failed")
        resp = client.post(
            "/api/git/repo/init",
            json={"account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 500


class TestRepoClone:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_clone_repo_success(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.clone_repo.return_value = {"success": True}
        resp = client.post(
            "/api/git/repo/clone",
            json={"account_alias": "srv1", "repo_url": "https://github.com/test/repo.git", "target_path": "/repo"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_clone_repo_with_branch_and_depth(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.clone_repo.return_value = {"success": True}
        resp = client.post(
            "/api/git/repo/clone",
            json={
                "account_alias": "srv1",
                "repo_url": "https://github.com/test/repo.git",
                "target_path": "/repo",
                "branch": "main",
                "depth": 1,
            },
        )
        assert resp.status_code == 200
        mock_git.clone_repo.assert_called_with("srv1", "https://github.com/test/repo.git", "/repo", "main", 1)

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_clone_repo_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.clone_repo.side_effect = Exception("clone failed")
        resp = client.post(
            "/api/git/repo/clone",
            json={"account_alias": "srv1", "repo_url": "https://github.com/test/repo.git", "target_path": "/repo"},
        )
        assert resp.status_code == 500


class TestConfigRemote:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_config_remote_add_success(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.add_remote.return_value = {"success": True}
        resp = client.post(
            "/api/git/repo/remote",
            json={"account_alias": "srv1", "repo_path": "/repo", "remote_name": "origin", "remote_url": "https://github.com/test/repo.git"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_config_remote_fallback_to_set_url(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.add_remote.return_value = {"success": False}
        mock_git.set_remote_url.return_value = {"success": True}
        resp = client.post(
            "/api/git/repo/remote",
            json={"account_alias": "srv1", "repo_path": "/repo", "remote_name": "origin", "remote_url": "https://github.com/test/repo.git"},
        )
        assert resp.status_code == 200
        mock_git.set_remote_url.assert_called_once()

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_config_remote_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.add_remote.side_effect = Exception("remote error")
        resp = client.post(
            "/api/git/repo/remote",
            json={"account_alias": "srv1", "repo_path": "/repo", "remote_name": "origin", "remote_url": "https://github.com/test/repo.git"},
        )
        assert resp.status_code == 500


class TestRepoInfo:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_repo_info_success(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_repo_info.return_value = {"branch": "main"}
        resp = client.get("/api/git/repo/info?account_alias=srv1&repo_path=/repo")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_repo_info_with_force_refresh(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_repo_info.return_value = {"branch": "main"}
        resp = client.get("/api/git/repo/info?account_alias=srv1&repo_path=/repo&force_refresh=true")
        assert resp.status_code == 200
        mock_git.get_repo_info.assert_called_with("srv1", "/repo", True)

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_repo_info_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_repo_info.side_effect = Exception("info error")
        resp = client.get("/api/git/repo/info?account_alias=srv1&repo_path=/repo")
        assert resp.status_code == 500


class TestBranchOperations:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_branch(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.create_branch.return_value = {"success": True}
        resp = client.post(
            "/api/git/branch/create",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "feature", "checkout": True},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_branch_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.create_branch.side_effect = Exception("branch error")
        resp = client.post(
            "/api/git/branch/create",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "feature"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_switch_branch(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.switch_branch.return_value = {"success": True}
        resp = client.post(
            "/api/git/branch/switch",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "dev", "stash_if_dirty": True},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_switch_branch_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.switch_branch.side_effect = Exception("switch error")
        resp = client.post(
            "/api/git/branch/switch",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "dev"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_merge_branch(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.merge_branch.return_value = {"success": True}
        resp = client.post(
            "/api/git/branch/merge",
            json={"account_alias": "srv1", "repo_path": "/repo", "source_branch": "dev", "target_branch": "main"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_merge_branch_no_target(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.merge_branch.return_value = {"success": True}
        resp = client.post(
            "/api/git/branch/merge",
            json={"account_alias": "srv1", "repo_path": "/repo", "source_branch": "dev"},
        )
        assert resp.status_code == 200
        mock_git.merge_branch.assert_called_with("srv1", "/repo", "dev", None)

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_merge_branch_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.merge_branch.side_effect = Exception("merge conflict")
        resp = client.post(
            "/api/git/branch/merge",
            json={"account_alias": "srv1", "repo_path": "/repo", "source_branch": "dev"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_branch(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.delete_branch.return_value = {"success": True}
        resp = client.post(
            "/api/git/branch/delete",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "old", "force": True},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_branch_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.delete_branch.side_effect = Exception("delete error")
        resp = client.post(
            "/api/git/branch/delete",
            json={"account_alias": "srv1", "repo_path": "/repo", "branch_name": "old"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_compare_branches(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.compare_branches.return_value = {"ahead": 3, "behind": 1}
        resp = client.post(
            "/api/git/branch/compare",
            json={"account_alias": "srv1", "repo_path": "/repo", "source": "dev", "target": "main"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_compare_branches_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.compare_branches.side_effect = Exception("compare error")
        resp = client.post(
            "/api/git/branch/compare",
            json={"account_alias": "srv1", "repo_path": "/repo", "source": "dev", "target": "main"},
        )
        assert resp.status_code == 500


class TestCommitOperations:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_commit_log(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_commit_log.return_value = {"commits": [], "total": 0}
        resp = client.get("/api/git/commit/log?account_alias=srv1&repo_path=/repo")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_commit_log_with_filters(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_commit_log.return_value = {"commits": [], "total": 0}
        resp = client.get("/api/git/commit/log?account_alias=srv1&repo_path=/repo&author=john&keyword=fix&page=2&page_size=10")
        assert resp.status_code == 200
        mock_git.get_commit_log.assert_called_with("srv1", "/repo", "john", None, None, "fix", 2, 10)

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_commit_log_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_commit_log.side_effect = Exception("log error")
        resp = client.get("/api/git/commit/log?account_alias=srv1&repo_path=/repo")
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_commit_detail(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_commit_detail.return_value = {"hash": "abc123", "message": "fix bug"}
        resp = client.get("/api/git/commit/detail?account_alias=srv1&repo_path=/repo&commit_hash=abc123")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_commit_detail_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_commit_detail.side_effect = Exception("detail error")
        resp = client.get("/api/git/commit/detail?account_alias=srv1&repo_path=/repo&commit_hash=abc123")
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_diff(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_diff.return_value = "diff content"
        resp = client.get("/api/git/commit/diff?account_alias=srv1&repo_path=/repo&from_ref=main&to_ref=dev")
        assert resp.status_code == 200
        assert "diff" in resp.json()

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_diff_with_file_path(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_diff.return_value = "diff content"
        resp = client.get("/api/git/commit/diff?account_alias=srv1&repo_path=/repo&from_ref=main&to_ref=dev&file_path=src/main.py")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_diff_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.get_diff.side_effect = Exception("diff error")
        resp = client.get("/api/git/commit/diff?account_alias=srv1&repo_path=/repo&from_ref=main&to_ref=dev")
        assert resp.status_code == 500


class TestWebhookConfig:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_webhook_config(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "hook1", "platform": "github"}
        mock_git.create_webhook_config.return_value = mock_config
        resp = client.post(
            "/api/git/webhook/config",
            json={"account_alias": "srv1", "repo_path": "/repo", "platform": "github", "events": ["push"]},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_webhook_config_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.create_webhook_config.side_effect = Exception("create error")
        resp = client.post(
            "/api/git/webhook/config",
            json={"account_alias": "srv1", "repo_path": "/repo", "platform": "github", "events": ["push"]},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_list_webhook_configs(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "hook1"}
        mock_git.list_webhook_configs.return_value = [mock_config]
        resp = client.get("/api/git/webhook/config")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_webhook_config_found(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "hook1"}
        mock_git.get_webhook_config.return_value = mock_config
        resp = client.get("/api/git/webhook/config/hook1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_webhook_config_not_found(self, mock_git):
        mock_git.get_webhook_config.return_value = None
        resp = client.get("/api/git/webhook/config/hook1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_webhook_config_found(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "hook1", "events": ["push"]}
        mock_git.update_webhook_config.return_value = mock_config
        resp = client.put("/api/git/webhook/config/hook1", json={"events": ["push"]})
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_webhook_config_not_found(self, mock_git):
        mock_git.update_webhook_config.return_value = None
        resp = client.put("/api/git/webhook/config/hook1", json={"events": ["push"]})
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_webhook_config_found(self, mock_git):
        mock_git.delete_webhook_config.return_value = True
        resp = client.delete("/api/git/webhook/config/hook1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_webhook_config_not_found(self, mock_git):
        mock_git.delete_webhook_config.return_value = False
        resp = client.delete("/api/git/webhook/config/hook1")
        assert resp.status_code == 404


class TestReceiveWebhook:
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_receive_webhook_success(self, mock_git):
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_git.get_webhook_config.return_value = mock_config
        mock_git.handle_webhook_event.return_value = {"status": "ok"}
        resp = client.post("/api/git/webhook/hook1", content=b'{"ref": "refs/heads/main"}', headers={"content-type": "application/json"})
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_receive_webhook_config_not_found(self, mock_git):
        mock_git.get_webhook_config.return_value = None
        resp = client.post("/api/git/webhook/hook1", content=b'{}', headers={"content-type": "application/json"})
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_receive_webhook_disabled(self, mock_git):
        mock_config = MagicMock()
        mock_config.enabled = False
        mock_git.get_webhook_config.return_value = mock_config
        resp = client.post("/api/git/webhook/hook1", content=b'{}', headers={"content-type": "application/json"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_receive_webhook_event_error(self, mock_git):
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_git.get_webhook_config.return_value = mock_config
        mock_git.handle_webhook_event.side_effect = Exception("handle error")
        resp = client.post("/api/git/webhook/hook1", content=b'{}', headers={"content-type": "application/json"})
        assert resp.status_code == 500


class TestDeployPipeline:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_deploy_pipeline(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.model_dump.return_value = {"id": "pipe1", "name": "deploy"}
        mock_git.create_deploy_pipeline.return_value = mock_pipeline
        resp = client.post(
            "/api/git/pipeline",
            json={"name": "deploy", "account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_deploy_pipeline_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.create_deploy_pipeline.side_effect = Exception("pipeline error")
        resp = client.post(
            "/api/git/pipeline",
            json={"name": "deploy", "account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_list_deploy_pipelines(self, mock_git):
        mock_pipeline = MagicMock()
        mock_pipeline.model_dump.return_value = {"id": "pipe1"}
        mock_git.list_deploy_pipelines.return_value = [mock_pipeline]
        resp = client.get("/api/git/pipeline")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_deploy_pipeline_found(self, mock_git):
        mock_pipeline = MagicMock()
        mock_pipeline.model_dump.return_value = {"id": "pipe1"}
        mock_git.get_deploy_pipeline.return_value = mock_pipeline
        resp = client.get("/api/git/pipeline/pipe1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_deploy_pipeline_not_found(self, mock_git):
        mock_git.get_deploy_pipeline.return_value = None
        resp = client.get("/api/git/pipeline/pipe1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_deploy_pipeline_found(self, mock_git):
        mock_pipeline = MagicMock()
        mock_pipeline.model_dump.return_value = {"id": "pipe1", "name": "updated"}
        mock_git.update_deploy_pipeline.return_value = mock_pipeline
        resp = client.put("/api/git/pipeline/pipe1", json={"name": "updated"})
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_deploy_pipeline_not_found(self, mock_git):
        mock_git.update_deploy_pipeline.return_value = None
        resp = client.put("/api/git/pipeline/pipe1", json={"name": "updated"})
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_deploy_pipeline_found(self, mock_git):
        mock_git.delete_deploy_pipeline.return_value = True
        resp = client.delete("/api/git/pipeline/pipe1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_deploy_pipeline_not_found(self, mock_git):
        mock_git.delete_deploy_pipeline.return_value = False
        resp = client.delete("/api/git/pipeline/pipe1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_execute_deploy_pipeline_found(self, mock_git):
        mock_pipeline = MagicMock()
        mock_git.get_deploy_pipeline.return_value = mock_pipeline
        mock_record = MagicMock()
        mock_record.model_dump.return_value = {"id": "rec1", "status": "running"}
        mock_git.execute_deploy_pipeline.return_value = mock_record
        resp = client.post("/api/git/pipeline/pipe1/execute")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_execute_deploy_pipeline_not_found(self, mock_git):
        mock_git.get_deploy_pipeline.return_value = None
        resp = client.post("/api/git/pipeline/pipe1/execute")
        assert resp.status_code == 404


class TestDeployHistory:
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_list_deploy_history(self, mock_git):
        mock_record = MagicMock()
        mock_record.model_dump.return_value = {"id": "rec1"}
        mock_git.list_deploy_records.return_value = [mock_record]
        resp = client.get("/api/git/deploy/history")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_list_deploy_history_with_filters(self, mock_git):
        mock_git.list_deploy_records.return_value = []
        resp = client.get("/api/git/deploy/history?account_alias=srv1&pipeline_id=pipe1&limit=10")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_deploy_history_found(self, mock_git):
        mock_record = MagicMock()
        mock_record.model_dump.return_value = {"id": "rec1"}
        mock_git.get_deploy_record.return_value = mock_record
        resp = client.get("/api/git/deploy/history/rec1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_deploy_history_not_found(self, mock_git):
        mock_git.get_deploy_record.return_value = None
        resp = client.get("/api/git/deploy/history/rec1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_rollback_deploy_success(self, mock_git):
        mock_record = MagicMock()
        mock_record.model_dump.return_value = {"id": "rec1", "status": "rolled_back"}
        mock_git.rollback_deploy.return_value = mock_record
        resp = client.post("/api/git/deploy/history/rec1/rollback")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_rollback_deploy_error(self, mock_git):
        mock_git.rollback_deploy.side_effect = Exception("rollback error")
        resp = client.post("/api/git/deploy/history/rec1/rollback")
        assert resp.status_code == 500


class TestSyncConfig:
    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_sync_config(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "sync1"}
        mock_git.create_sync_config.return_value = mock_config
        resp = client.post(
            "/api/git/sync/config",
            json={"account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.ssh_account_service")
    @patch("app.api.routes.git_integration.git_integration_service")
    def test_create_sync_config_error(self, mock_git, mock_ssh):
        mock_ssh.get_account.return_value = MagicMock()
        mock_git.create_sync_config.side_effect = Exception("sync error")
        resp = client.post(
            "/api/git/sync/config",
            json={"account_alias": "srv1", "repo_path": "/repo"},
        )
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_list_sync_configs(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "sync1"}
        mock_git.list_sync_configs.return_value = [mock_config]
        resp = client.get("/api/git/sync/config")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_config_found(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "sync1"}
        mock_git.get_sync_config.return_value = mock_config
        resp = client.get("/api/git/sync/config/sync1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_config_not_found(self, mock_git):
        mock_git.get_sync_config.return_value = None
        resp = client.get("/api/git/sync/config/sync1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_sync_config_found(self, mock_git):
        mock_config = MagicMock()
        mock_config.model_dump.return_value = {"id": "sync1", "enabled": True}
        mock_git.update_sync_config.return_value = mock_config
        resp = client.put("/api/git/sync/config/sync1", json={"enabled": True})
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_update_sync_config_not_found(self, mock_git):
        mock_git.update_sync_config.return_value = None
        resp = client.put("/api/git/sync/config/sync1", json={"enabled": True})
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_sync_config_found(self, mock_git):
        mock_git.delete_sync_config.return_value = True
        resp = client.delete("/api/git/sync/config/sync1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_delete_sync_config_not_found(self, mock_git):
        mock_git.delete_sync_config.return_value = False
        resp = client.delete("/api/git/sync/config/sync1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_manual_pull_success(self, mock_git):
        mock_git.manual_pull.return_value = {"success": True}
        resp = client.post("/api/git/sync/manual-pull/sync1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_manual_pull_error(self, mock_git):
        mock_git.manual_pull.side_effect = Exception("pull error")
        resp = client.post("/api/git/sync/manual-pull/sync1")
        assert resp.status_code == 500

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_status_found(self, mock_git):
        mock_git.get_sync_status.return_value = {"last_sync": "2024-01-01"}
        resp = client.get("/api/git/sync/status/sync1")
        assert resp.status_code == 200

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_status_not_found(self, mock_git):
        mock_git.get_sync_status.return_value = None
        resp = client.get("/api/git/sync/status/sync1")
        assert resp.status_code == 404

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_logs(self, mock_git):
        mock_git.get_sync_logs.return_value = ["log1", "log2"]
        resp = client.get("/api/git/sync/logs/sync1")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    @patch("app.api.routes.git_integration.git_integration_service")
    def test_get_sync_logs_with_limit(self, mock_git):
        mock_git.get_sync_logs.return_value = ["log1"]
        resp = client.get("/api/git/sync/logs/sync1?limit=10")
        assert resp.status_code == 200
        mock_git.get_sync_logs.assert_called_with("sync1", 10)
