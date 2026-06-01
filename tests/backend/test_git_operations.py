from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.git_operations import GitOperationError, GitOperations
from app.core.remote_executor import CommandResult


def make_result(exit_code=0, stdout="", stderr=""):
    return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


@pytest.fixture
def git():
    with patch("app.core.git_operations.RemoteExecutor") as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.resolve_path = lambda p: f"/resolved/{p}" if not p.startswith("/resolved/") else p
        MockExecutor.return_value = mock_executor
        ops = GitOperations("test-server")
        ops._executor = mock_executor
        return ops


class TestInit:
    def test_init_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Initialized empty Git repository")
        result = git.init("/repo")
        assert result["success"] is True
        assert "初始化成功" in result["message"]

    def test_init_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "already exists")
        result = git.init("/repo")
        assert result["success"] is False
        assert "初始化仓库失败" in result["message"]

    def test_init_with_gitignore(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, "Initialized empty Git repository"),
            make_result(0, ""),
        ]
        result = git.init("/repo", gitignore_template="node_modules/\n*.log")
        assert result["success"] is True

    def test_init_gitignore_write_fail(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, "Initialized empty Git repository"),
            make_result(1, "", "permission denied"),
        ]
        result = git.init("/repo", gitignore_template="node_modules/")
        assert result["success"] is True
        assert ".gitignore" in result["message"]


class TestClone:
    def test_clone_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Cloning into...")
        result = git.clone("https://github.com/test/repo.git", "/target")
        assert result["success"] is True

    def test_clone_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "Repository not found")
        result = git.clone("https://github.com/test/repo.git", "/target")
        assert result["success"] is False

    def test_clone_with_branch(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.clone("https://github.com/test/repo.git", "/target", branch="develop")
        call_args = git._executor.exec_command.call_args[0][0]
        assert "--branch develop" in call_args

    def test_clone_with_depth(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.clone("https://github.com/test/repo.git", "/target", depth=1)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "--depth 1" in call_args

    def test_clone_with_branch_and_depth(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.clone("https://github.com/test/repo.git", "/target", branch="main", depth=10)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "--branch main" in call_args
        assert "--depth 10" in call_args


class TestRemote:
    def test_add_remote_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.add_remote("/repo", "origin", "https://github.com/test/repo.git")
        assert result["success"] is True

    def test_add_remote_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "already exists")
        result = git.add_remote("/repo", "origin", "https://github.com/test/repo.git")
        assert result["success"] is False

    def test_set_remote_url_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.set_remote_url("/repo", "origin", "https://github.com/new/repo.git")
        assert result["success"] is True

    def test_set_remote_url_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "No such remote")
        result = git.set_remote_url("/repo", "origin", "https://github.com/new/repo.git")
        assert result["success"] is False

    def test_list_remotes(self, git):
        output = "origin  https://github.com/test/repo.git (fetch)\norigin  https://github.com/test/repo.git (push)\nupstream  https://github.com/upstream/repo.git (fetch)"
        git._executor.exec_command.return_value = make_result(0, output)
        remotes = git.list_remotes("/repo")
        assert remotes["origin"] == "https://github.com/test/repo.git"
        assert remotes["upstream"] == "https://github.com/upstream/repo.git"

    def test_list_remotes_empty(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "fatal: not a git repository")
        remotes = git.list_remotes("/repo")
        assert remotes == {}


class TestGetRepoInfo:
    def test_get_repo_info(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, "main"),
            make_result(0, "* main\n  remotes/origin/main\n  remotes/origin/develop"),
            make_result(0, "origin  https://github.com/test/repo.git (fetch)\norigin  https://github.com/test/repo.git (push)"),
            make_result(0, "2.5M\t/repo"),
            make_result(0, "M file.txt"),
            make_result(0, "abc123|abc1|John|john@test.com|2024-01-15T10:00:00+08:00|Initial commit"),
        ]
        info = git.get_repo_info("/repo")
        assert info["current_branch"] == "main"
        assert len(info["branches"]) == 3
        assert info["has_uncommitted_changes"] is True
        assert info["latest_commit"]["hash"] == "abc123"

    def test_get_repo_info_no_commit(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, "main"),
            make_result(0, "* main"),
            make_result(0, ""),
            make_result(0, "1.0K\t/repo"),
            make_result(0, ""),
            make_result(1, "", "no commits yet"),
        ]
        info = git.get_repo_info("/repo")
        assert info["latest_commit"] is None
        assert info["has_uncommitted_changes"] is False


class TestGetRepoSize:
    def test_get_repo_size(self, git):
        git._executor.exec_command.return_value = make_result(0, "2.5M\t/repo")
        size = git.get_repo_size("/repo")
        assert size == "2.5M"

    def test_get_repo_size_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        size = git.get_repo_size("/repo")
        assert size == "未知"


class TestHasUncommittedChanges:
    def test_has_changes(self, git):
        git._executor.exec_command.return_value = make_result(0, "M file.txt\n?? new.txt")
        assert git.has_uncommitted_changes("/repo") is True

    def test_no_changes(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        assert git.has_uncommitted_changes("/repo") is False

    def test_command_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        assert git.has_uncommitted_changes("/repo") is False


class TestBranches:
    def test_list_branches(self, git):
        git._executor.exec_command.return_value = make_result(0, "* main\n  develop\n  remotes/origin/main")
        branches = git.list_branches("/repo")
        assert len(branches) == 3
        assert branches[0]["is_current"] is True
        assert branches[0]["name"] == "main"

    def test_list_branches_local_only(self, git):
        git._executor.exec_command.return_value = make_result(0, "* main\n  develop")
        branches = git.list_branches("/repo", include_remote=False)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "branch -a" not in call_args

    def test_list_branches_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        branches = git.list_branches("/repo")
        assert branches == []

    def test_create_branch(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.create_branch("/repo", "feature")
        assert result["success"] is True

    def test_create_branch_with_base(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.create_branch("/repo", "feature", base_ref="main")
        assert result["success"] is True

    def test_create_branch_with_checkout(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.create_branch("/repo", "feature", checkout=True)
        assert result["success"] is True

    def test_create_branch_checkout_with_base(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.create_branch("/repo", "feature", base_ref="develop", checkout=True)
        assert result["success"] is True

    def test_create_branch_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "already exists")
        result = git.create_branch("/repo", "feature")
        assert result["success"] is False

    def test_switch_branch(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.switch_branch("/repo", "develop")
        assert result["success"] is True

    def test_switch_branch_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "not found")
        result = git.switch_branch("/repo", "nonexistent")
        assert result["success"] is False

    def test_delete_branch(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.delete_branch("/repo", "feature")
        assert result["success"] is True

    def test_delete_branch_force(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.delete_branch("/repo", "feature", force=True)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "-D" in call_args

    def test_delete_branch_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "not found")
        result = git.delete_branch("/repo", "feature")
        assert result["success"] is False

    def test_is_branch_merged_true(self, git):
        git._executor.exec_command.return_value = make_result(0, "  main\n* develop\n  feature")
        assert git.is_branch_merged("/repo", "develop", "main") is True

    def test_is_branch_merged_false(self, git):
        git._executor.exec_command.return_value = make_result(0, "  main\n* develop")
        assert git.is_branch_merged("/repo", "feature", "main") is False

    def test_is_branch_merged_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        assert git.is_branch_merged("/repo", "feature", "main") is False


class TestMergeBranch:
    def test_merge_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Merge made by the 'ort' strategy.")
        result = git.merge_branch("/repo", "feature")
        assert result["success"] is True
        assert result["has_conflicts"] is False

    def test_merge_with_target(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, "Switched to branch 'develop'"),
            make_result(0, "Merge made by the 'ort' strategy."),
        ]
        result = git.merge_branch("/repo", "feature", target_branch="develop")
        assert result["success"] is True

    def test_merge_target_switch_fail(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.merge_branch("/repo", "feature", target_branch="develop")
        assert result["success"] is False
        assert result["has_conflicts"] is False

    def test_merge_conflicts(self, git):
        git._executor.exec_command.side_effect = [
            make_result(1, "CONFLICT (content): Merge conflict in file.txt", "Automatic merge failed"),
            make_result(0, "file.txt"),
        ]
        result = git.merge_branch("/repo", "feature")
        assert result["success"] is False
        assert result["has_conflicts"] is True
        assert "file.txt" in result["conflict_files"]

    def test_merge_failure_no_conflict(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "fatal: not possible to fast-forward")
        result = git.merge_branch("/repo", "feature")
        assert result["success"] is False
        assert result["has_conflicts"] is False


class TestCompareBranches:
    def test_compare_with_changes(self, git):
        output = "M\tfile1.txt\nA\tfile2.txt\nD\tfile3.txt"
        git._executor.exec_command.return_value = make_result(0, output)
        result = git.compare_branches("/repo", "main", "develop")
        assert result["total_changes"] == 3

    def test_compare_no_changes(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.compare_branches("/repo", "main", "develop")
        assert result["total_changes"] == 0

    def test_compare_single_part_line(self, git):
        output = "file1.txt"
        git._executor.exec_command.return_value = make_result(0, output)
        result = git.compare_branches("/repo", "main", "develop")
        assert len(result["files"]) == 1
        assert result["files"][0]["change_type"] == "M"


class TestLog:
    def test_log_basic(self, git):
        log_output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Initial commit\ndef456|def4|Jane|jane@test.com|2024-01-16T11:00:00|Add feature'
        count_output = "2"
        git._executor.exec_command.side_effect = [
            make_result(0, log_output),
            make_result(0, count_output),
        ]
        result = git.log("/repo")
        assert result["total"] == 2
        assert len(result["commits"]) == 2

    def test_log_with_filters(self, git):
        log_output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Fix bug'
        count_output = "1"
        git._executor.exec_command.side_effect = [
            make_result(0, log_output),
            make_result(0, count_output),
        ]
        result = git.log("/repo", author="John", since="2024-01-01", until="2024-01-31", keyword="bug")
        assert len(result["commits"]) == 1

    def test_log_empty(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, ""),
            make_result(0, "0"),
        ]
        result = git.log("/repo")
        assert result["commits"] == []
        assert result["total"] == 0

    def test_log_count_fallback(self, git):
        log_output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Commit'
        git._executor.exec_command.side_effect = [
            make_result(0, log_output),
            make_result(0, "not_a_number"),
            make_result(0, "abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Commit"),
        ]
        result = git.log("/repo")
        assert result["total"] == 1

    def test_log_count_empty_fallback(self, git):
        log_output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Commit'
        git._executor.exec_command.side_effect = [
            make_result(0, log_output),
            make_result(1, "", "error"),
            make_result(0, "abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Commit"),
        ]
        result = git.log("/repo")
        assert result["total"] == 1

    def test_log_pagination(self, git):
        git._executor.exec_command.side_effect = [
            make_result(0, ""),
            make_result(0, "0"),
        ]
        result = git.log("/repo", page=3, page_size=10)
        assert result["page"] == 3
        assert result["page_size"] == 10


class TestShowCommit:
    def test_show_commit(self, git):
        output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Initial commit\n file1.txt | 10 +++++-----\n 1 file changed, 5 insertions(+), 5 deletions(-)\n\ndiff --git a/file1.txt b/file1.txt\n--- a/file1.txt\n+++ b/file1.txt\n@@ -1,5 +1,5 @@'
        git._executor.exec_command.return_value = make_result(0, output)
        result = git.show_commit("/repo", "abc123")
        assert result["hash"] == "abc123"
        assert result["author"] == "John"
        assert "file1.txt" in result["changed_files"]
        assert "diff --git" in result["diff_content"]

    def test_show_commit_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "not found")
        with pytest.raises(GitOperationError, match="获取提交详情失败"):
            git.show_commit("/repo", "nonexistent")

    def test_show_commit_no_stat(self, git):
        output = 'abc123|abc1|John|john@test.com|2024-01-15T10:00:00|Initial commit\n\ndiff --git a/file.txt b/file.txt'
        git._executor.exec_command.return_value = make_result(0, output)
        result = git.show_commit("/repo", "abc123")
        assert result["hash"] == "abc123"
        assert "diff" in result["diff_content"]

    def test_show_commit_malformed_header(self, git):
        output = "malformed_header\n\ndiff content"
        git._executor.exec_command.return_value = make_result(0, output)
        result = git.show_commit("/repo", "abc123")
        assert result["hash"] == ""


class TestDiff:
    def test_diff(self, git):
        git._executor.exec_command.return_value = make_result(0, "diff content here")
        result = git.diff("/repo", "main", "develop")
        assert result == "diff content here"

    def test_diff_with_file(self, git):
        git._executor.exec_command.return_value = make_result(0, "file diff")
        result = git.diff("/repo", "main", "develop", file_path="src/main.py")
        call_args = git._executor.exec_command.call_args[0][0]
        assert "-- src/main.py" in call_args

    def test_diff_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        with pytest.raises(GitOperationError, match="获取差异失败"):
            git.diff("/repo", "main", "develop")


class TestFetch:
    def test_fetch_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.fetch("/repo")
        assert result["success"] is True

    def test_fetch_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.fetch("/repo")
        assert result["success"] is False

    def test_fetch_custom_remote(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.fetch("/repo", remote="upstream")
        call_args = git._executor.exec_command.call_args[0][0]
        assert "upstream" in call_args


class TestPull:
    def test_pull_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Already up to date.")
        result = git.pull("/repo")
        assert result["success"] is True
        assert result["has_conflicts"] is False

    def test_pull_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "fatal: error")
        result = git.pull("/repo")
        assert result["success"] is False

    def test_pull_conflicts(self, git):
        git._executor.exec_command.side_effect = [
            make_result(1, "CONFLICT (content): Merge conflict", "Automatic merge failed"),
            make_result(0, "file1.txt\nfile2.txt"),
        ]
        result = git.pull("/repo")
        assert result["success"] is False
        assert result["has_conflicts"] is True
        assert len(result["conflict_files"]) == 2

    def test_pull_with_branch(self, git):
        git._executor.exec_command.return_value = make_result(0, "Already up to date.")
        result = git.pull("/repo", branch="main")
        call_args = git._executor.exec_command.call_args[0][0]
        assert "main" in call_args

    def test_pull_no_ff_only(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.pull("/repo", ff_only=False)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "--ff-only" not in call_args


class TestGetAheadBehind:
    def test_ahead_behind(self, git):
        git._executor.exec_command.return_value = make_result(0, "3   1")
        result = git.get_ahead_behind("/repo", "main", "origin/main")
        assert result["ahead"] == 3
        assert result["behind"] == 1

    def test_ahead_behind_only_ahead(self, git):
        git._executor.exec_command.return_value = make_result(0, "5")
        result = git.get_ahead_behind("/repo", "main", "origin/main")
        assert result["ahead"] == 5
        assert result["behind"] == 0

    def test_ahead_behind_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        with pytest.raises(GitOperationError, match="获取领先/落后信息失败"):
            git.get_ahead_behind("/repo", "main", "origin/main")


class TestStash:
    def test_stash_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Saved working directory and index state")
        result = git.stash("/repo")
        assert result["success"] is True
        assert "暂存" in result["message"]

    def test_stash_no_changes(self, git):
        git._executor.exec_command.return_value = make_result(0, "No local changes to save")
        result = git.stash("/repo")
        assert result["success"] is True
        assert "没有" in result["message"]

    def test_stash_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.stash("/repo")
        assert result["success"] is False


class TestStashPop:
    def test_stash_pop_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "Changes restored")
        result = git.stash_pop("/repo")
        assert result["success"] is True

    def test_stash_pop_conflict(self, git):
        git._executor.exec_command.return_value = make_result(1, "CONFLICT", "merge conflict")
        result = git.stash_pop("/repo")
        assert result["success"] is False
        assert "冲突" in result["message"]

    def test_stash_pop_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.stash_pop("/repo")
        assert result["success"] is False


class TestCheckoutCommit:
    def test_checkout_commit_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.checkout_commit("/repo", "abc123")
        assert result["success"] is True

    def test_checkout_commit_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.checkout_commit("/repo", "nonexistent")
        assert result["success"] is False


class TestRevertCommit:
    def test_revert_success(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.revert_commit("/repo", "abc123")
        assert result["success"] is True

    def test_revert_no_commit(self, git):
        git._executor.exec_command.return_value = make_result(0, "")
        result = git.revert_commit("/repo", "abc123", no_commit=True)
        call_args = git._executor.exec_command.call_args[0][0]
        assert "--no-commit" in call_args

    def test_revert_conflict(self, git):
        git._executor.exec_command.return_value = make_result(1, "CONFLICT", "merge conflict")
        result = git.revert_commit("/repo", "abc123")
        assert result["success"] is False
        assert "冲突" in result["message"]

    def test_revert_failure(self, git):
        git._executor.exec_command.return_value = make_result(1, "", "error")
        result = git.revert_commit("/repo", "abc123")
        assert result["success"] is False


class TestParseBranches:
    def test_parse_current_branch(self, git):
        raw = "* main\n  develop\n  remotes/origin/main"
        branches = git._parse_branches(raw)
        assert len(branches) == 3
        assert branches[0]["is_current"] is True
        assert branches[0]["name"] == "main"
        assert branches[2]["is_remote"] is True

    def test_parse_empty(self, git):
        assert git._parse_branches("") == []
        assert git._parse_branches(None) == []

    def test_parse_with_upstream(self, git):
        raw = "* main [origin/main]\n  develop [origin/develop: ahead 2]"
        branches = git._parse_branches(raw)
        assert branches[0]["upstream"] == "origin/main"
        assert branches[1]["upstream"] == "origin/develop: ahead 2"
