from __future__ import annotations

import re
from typing import Optional

from app.core.remote_executor import RemoteExecutor, CommandResult


class GitOperationError(Exception):
    pass


class GitOperations:
    def __init__(self, account_alias: str):
        self._alias = account_alias
        self._executor = RemoteExecutor(account_alias)

    def _exec(self, cmd: str, timeout: float = 30.0) -> CommandResult:
        result = self._executor.exec_command(cmd, timeout=timeout)
        return result

    def _exec_in_repo(self, repo_path: str, git_cmd: str, timeout: float = 30.0) -> CommandResult:
        resolved = self._executor.resolve_path(repo_path)
        full_cmd = f"cd {resolved} && git {git_cmd}"
        return self._exec(full_cmd, timeout=timeout)

    def init(self, repo_path: str, gitignore_template: Optional[str] = None) -> dict:
        resolved = self._executor.resolve_path(repo_path)
        result = self._exec(f"cd {resolved} && git init")
        if not result.success:
            return {"success": False, "message": f"初始化仓库失败: {result.stderr}", "repo_path": repo_path}
        if gitignore_template:
            escaped = gitignore_template.replace("'", "'\\''")
            write_result = self._exec(f"cd {resolved} && printf '%s' '{escaped}' > .gitignore")
            if not write_result.success:
                return {"success": True, "message": "仓库已初始化，但写入 .gitignore 失败", "repo_path": repo_path}
        return {"success": True, "message": "仓库初始化成功", "repo_path": repo_path}

    def clone(self, repo_url: str, target_path: str, branch: Optional[str] = None, depth: Optional[int] = None) -> dict:
        resolved = self._executor.resolve_path(target_path)
        parts = ["git clone"]
        if branch:
            parts.append(f"--branch {branch}")
        if depth is not None:
            parts.append(f"--depth {depth}")
        parts.append(f"'{repo_url}'")
        parts.append(f"{resolved}")
        cmd = " ".join(parts)
        result = self._exec(cmd, timeout=120.0)
        if not result.success:
            return {"success": False, "message": f"克隆仓库失败: {result.stderr}", "repo_path": target_path}
        return {"success": True, "message": "仓库克隆成功", "repo_path": target_path}

    def add_remote(self, repo_path: str, remote_name: str, remote_url: str) -> dict:
        result = self._exec_in_repo(repo_path, f"remote add {remote_name} '{remote_url}'")
        if not result.success:
            return {"success": False, "message": f"添加远程仓库失败: {result.stderr}"}
        return {"success": True, "message": f"远程仓库 '{remote_name}' 添加成功"}

    def set_remote_url(self, repo_path: str, remote_name: str, remote_url: str) -> dict:
        result = self._exec_in_repo(repo_path, f"remote set-url {remote_name} '{remote_url}'")
        if not result.success:
            return {"success": False, "message": f"设置远程仓库地址失败: {result.stderr}"}
        return {"success": True, "message": f"远程仓库 '{remote_name}' 地址已更新"}

    def list_remotes(self, repo_path: str) -> dict[str, str]:
        result = self._exec_in_repo(repo_path, "remote -v")
        remotes: dict[str, str] = {}
        if not result.success:
            return remotes
        for line in result.stdout.splitlines():
            match = re.match(r'^(\S+)\s+(\S+)\s+\(fetch\)', line)
            if match:
                remotes[match.group(1)] = match.group(2)
        return remotes

    def get_repo_info(self, repo_path: str) -> dict:
        info: dict = {"repo_path": repo_path}

        branch_result = self._exec_in_repo(repo_path, "rev-parse --abbrev-ref HEAD", timeout=10.0)
        info["current_branch"] = branch_result.stdout if branch_result.success else None

        branches_result = self._exec_in_repo(repo_path, "branch -a", timeout=10.0)
        info["branches"] = self._parse_branches(branches_result.stdout) if branches_result.success else []

        info["remotes"] = self.list_remotes(repo_path)

        info["size"] = self.get_repo_size(repo_path)

        info["has_uncommitted_changes"] = self.has_uncommitted_changes(repo_path)

        log_result = self._exec_in_repo(repo_path, 'log -1 --format="%H|%h|%an|%ae|%aI|%s"', timeout=10.0)
        if log_result.success and log_result.stdout:
            parts = log_result.stdout.split("|", 5)
            if len(parts) == 6:
                info["latest_commit"] = {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author": parts[2],
                    "email": parts[3],
                    "date": parts[4],
                    "message": parts[5],
                }
            else:
                info["latest_commit"] = None
        else:
            info["latest_commit"] = None

        return info

    def get_repo_size(self, repo_path: str) -> str:
        resolved = self._executor.resolve_path(repo_path)
        result = self._exec(f"du -sh {resolved}", timeout=10.0)
        if result.success:
            parts = result.stdout.split()
            if parts:
                return parts[0]
        return "未知"

    def has_uncommitted_changes(self, repo_path: str) -> bool:
        result = self._exec_in_repo(repo_path, "status --porcelain", timeout=10.0)
        if result.success:
            return bool(result.stdout.strip())
        return False

    def list_branches(self, repo_path: str, include_remote: bool = True) -> list[dict]:
        flag = "-a" if include_remote else ""
        result = self._exec_in_repo(repo_path, f"branch {flag}".strip(), timeout=10.0)
        if not result.success:
            return []
        return self._parse_branches(result.stdout)

    def _parse_branches(self, raw: str) -> list[dict]:
        branches: list[dict] = []
        if not raw:
            return branches
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            is_current = line.startswith("*")
            name = line.lstrip("* ").strip()
            is_remote = name.startswith("remotes/")
            upstream = None
            if not is_remote and "[" in name:
                match = re.match(r'^(.+?)\s+\[(.+?)\]', name)
                if match:
                    name = match.group(1).strip()
                    upstream = match.group(2).strip()
            branches.append({
                "name": name,
                "is_current": is_current,
                "is_remote": is_remote,
                "upstream": upstream,
            })
        return branches

    def create_branch(self, repo_path: str, branch_name: str, base_ref: Optional[str] = None, checkout: bool = False) -> dict:
        if checkout:
            if base_ref:
                result = self._exec_in_repo(repo_path, f"checkout -b {branch_name} {base_ref}")
            else:
                result = self._exec_in_repo(repo_path, f"checkout -b {branch_name}")
        else:
            if base_ref:
                result = self._exec_in_repo(repo_path, f"branch {branch_name} {base_ref}")
            else:
                result = self._exec_in_repo(repo_path, f"branch {branch_name}")
        if not result.success:
            return {"success": False, "message": f"创建分支失败: {result.stderr}"}
        return {"success": True, "message": f"分支 '{branch_name}' 创建成功"}

    def switch_branch(self, repo_path: str, branch_name: str) -> dict:
        result = self._exec_in_repo(repo_path, f"checkout {branch_name}")
        if not result.success:
            return {"success": False, "message": f"切换分支失败: {result.stderr}"}
        return {"success": True, "message": f"已切换到分支 '{branch_name}'"}

    def merge_branch(self, repo_path: str, source_branch: str, target_branch: Optional[str] = None) -> dict:
        if target_branch:
            switch_result = self._exec_in_repo(repo_path, f"checkout {target_branch}")
            if not switch_result.success:
                return {"success": False, "message": f"切换到目标分支失败: {switch_result.stderr}", "has_conflicts": False, "conflict_files": []}
        result = self._exec_in_repo(repo_path, f"merge {source_branch}", timeout=60.0)
        has_conflicts = "CONFLICT" in result.stdout or "CONFLICT" in result.stderr
        conflict_files: list[str] = []
        if has_conflicts:
            conflict_result = self._exec_in_repo(repo_path, "diff --name-only --diff-filter=U")
            if conflict_result.success:
                conflict_files = [f for f in conflict_result.stdout.splitlines() if f.strip()]
        if not result.success and not has_conflicts:
            return {"success": False, "message": f"合并失败: {result.stderr}", "has_conflicts": False, "conflict_files": []}
        if has_conflicts:
            return {"success": False, "message": f"合并存在冲突，请手动解决", "has_conflicts": True, "conflict_files": conflict_files}
        return {"success": True, "message": f"分支 '{source_branch}' 合并成功", "has_conflicts": False, "conflict_files": []}

    def delete_branch(self, repo_path: str, branch_name: str, force: bool = False) -> dict:
        flag = "-D" if force else "-d"
        result = self._exec_in_repo(repo_path, f"branch {flag} {branch_name}")
        if not result.success:
            return {"success": False, "message": f"删除分支失败: {result.stderr}"}
        return {"success": True, "message": f"分支 '{branch_name}' 已删除"}

    def is_branch_merged(self, repo_path: str, branch_name: str, target: str = "main") -> bool:
        result = self._exec_in_repo(repo_path, f"branch --merged {target}", timeout=10.0)
        if not result.success:
            return False
        merged_branches = [line.lstrip("* ").strip() for line in result.stdout.splitlines() if line.strip()]
        return branch_name in merged_branches

    def compare_branches(self, repo_path: str, source: str, target: str) -> dict:
        result = self._exec_in_repo(repo_path, f"diff --name-status {source}...{target}", timeout=30.0)
        files: list[dict] = []
        if result.success and result.stdout.strip():
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    files.append({"file_path": parts[1], "change_type": parts[0]})
                elif len(parts) == 1:
                    files.append({"file_path": parts[0], "change_type": "M"})
        return {"files": files, "total_changes": len(files)}

    def log(self, repo_path: str, author: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None, keyword: Optional[str] = None, page: int = 1, page_size: int = 20) -> dict:
        parts = ['log --format="%H|%h|%an|%ae|%aI|%s"']
        if author:
            parts.append(f"--author='{author}'")
        if since:
            parts.append(f"--since='{since}'")
        if until:
            parts.append(f"--until='{until}'")
        if keyword:
            parts.append(f"--grep='{keyword}'")
        skip = (page - 1) * page_size
        parts.append(f"--skip={skip}")
        parts.append(f"--max-count={page_size}")
        cmd = " ".join(parts)
        result = self._exec_in_repo(repo_path, cmd, timeout=30.0)

        count_parts = ['log --oneline']
        if author:
            count_parts.append(f"--author='{author}'")
        if since:
            count_parts.append(f"--since='{since}'")
        if until:
            count_parts.append(f"--until='{until}'")
        if keyword:
            count_parts.append(f"--grep='{keyword}'")
        count_parts.append("--count")
        count_cmd = " ".join(count_parts)
        count_result = self._exec_in_repo(repo_path, count_cmd, timeout=30.0)

        total = 0
        if count_result.success and count_result.stdout.strip():
            try:
                total = int(count_result.stdout.strip())
            except ValueError:
                total_result = self._exec_in_repo(repo_path, " ".join(count_parts[:-1]) + " --oneline", timeout=30.0)
                if total_result.success:
                    total = len([l for l in total_result.stdout.splitlines() if l.strip()])
        else:
            total_result = self._exec_in_repo(repo_path, " ".join(count_parts[:-1]) + " --oneline", timeout=30.0)
            if total_result.success:
                total = len([l for l in total_result.stdout.splitlines() if l.strip()])

        commits: list[dict] = []
        if result.success and result.stdout.strip():
            for line in result.stdout.splitlines():
                line = line.strip().strip('"')
                if not line:
                    continue
                fields = line.split("|", 5)
                if len(fields) == 6:
                    commits.append({
                        "hash": fields[0],
                        "short_hash": fields[1],
                        "author": fields[2],
                        "email": fields[3],
                        "date": fields[4],
                        "message": fields[5],
                    })
        return {"commits": commits, "total": total, "page": page, "page_size": page_size}

    def show_commit(self, repo_path: str, commit_hash: str) -> dict:
        result = self._exec_in_repo(repo_path, f'show {commit_hash} --format="%H|%h|%an|%ae|%aI|%s" --stat', timeout=30.0)
        if not result.success:
            raise GitOperationError(f"获取提交详情失败: {result.stderr}")
        lines = result.stdout.splitlines()
        commit_info: dict = {
            "hash": "",
            "short_hash": "",
            "author": "",
            "email": "",
            "date": "",
            "message": "",
            "changed_files": [],
            "diff_content": "",
        }
        if lines:
            header = lines[0].strip().strip('"')
            fields = header.split("|", 5)
            if len(fields) == 6:
                commit_info["hash"] = fields[0]
                commit_info["short_hash"] = fields[1]
                commit_info["author"] = fields[2]
                commit_info["email"] = fields[3]
                commit_info["date"] = fields[4]
                commit_info["message"] = fields[5]

        stat_section = False
        diff_section = False
        stat_lines: list[str] = []
        diff_lines: list[str] = []
        for line in lines[1:]:
            if not stat_section and not diff_section:
                if re.match(r'^\s+[\w\-./]+\s*\|', line):
                    stat_section = True
            if stat_section:
                if re.match(r'^\s+[\w\-./]+\s*\|', line):
                    file_match = re.match(r'^\s+([\w\-./]+)\s*\|', line)
                    if file_match:
                        commit_info["changed_files"].append(file_match.group(1))
                    stat_lines.append(line)
                elif line.strip() == "" or re.match(r'^\s+\d+ file', line):
                    stat_lines.append(line)
                else:
                    stat_section = False
                    diff_section = True
                    diff_lines.append(line)
            else:
                diff_section = True
                diff_lines.append(line)

        if not stat_section and not diff_section and len(lines) > 1:
            diff_lines = lines[1:]

        commit_info["diff_content"] = "\n".join(diff_lines)
        return commit_info

    def diff(self, repo_path: str, from_ref: str, to_ref: str, file_path: Optional[str] = None) -> str:
        if file_path:
            result = self._exec_in_repo(repo_path, f"diff {from_ref} {to_ref} -- {file_path}", timeout=30.0)
        else:
            result = self._exec_in_repo(repo_path, f"diff {from_ref} {to_ref}", timeout=30.0)
        if not result.success:
            raise GitOperationError(f"获取差异失败: {result.stderr}")
        return result.stdout

    def fetch(self, repo_path: str, remote: str = "origin") -> dict:
        result = self._exec_in_repo(repo_path, f"fetch {remote}", timeout=60.0)
        if not result.success:
            return {"success": False, "message": f"拉取远程数据失败: {result.stderr}"}
        return {"success": True, "message": f"已从 '{remote}' 拉取最新数据"}

    def pull(self, repo_path: str, remote: str = "origin", branch: Optional[str] = None, ff_only: bool = True) -> dict:
        parts = ["pull"]
        if ff_only:
            parts.append("--ff-only")
        parts.append(remote)
        if branch:
            parts.append(branch)
        cmd = " ".join(parts)
        result = self._exec_in_repo(repo_path, cmd, timeout=60.0)
        has_conflicts = "CONFLICT" in result.stdout or "CONFLICT" in result.stderr
        conflict_files: list[str] = []
        if has_conflicts:
            conflict_result = self._exec_in_repo(repo_path, "diff --name-only --diff-filter=U")
            if conflict_result.success:
                conflict_files = [f for f in conflict_result.stdout.splitlines() if f.strip()]
        if not result.success and not has_conflicts:
            return {"success": False, "message": f"拉取失败: {result.stderr}", "has_conflicts": False, "conflict_files": []}
        if has_conflicts:
            return {"success": False, "message": "拉取存在冲突，请手动解决", "has_conflicts": True, "conflict_files": conflict_files}
        return {"success": True, "message": "拉取成功", "has_conflicts": False, "conflict_files": []}

    def get_ahead_behind(self, repo_path: str, branch: str, remote_branch: str) -> dict:
        result = self._exec_in_repo(repo_path, f"rev-list --left-right --count {branch}...{remote_branch}", timeout=10.0)
        if not result.success:
            raise GitOperationError(f"获取领先/落后信息失败: {result.stderr}")
        parts = result.stdout.strip().split()
        ahead = int(parts[0]) if len(parts) >= 1 else 0
        behind = int(parts[1]) if len(parts) >= 2 else 0
        return {"ahead": ahead, "behind": behind}

    def stash(self, repo_path: str) -> dict:
        result = self._exec_in_repo(repo_path, "stash")
        if not result.success:
            return {"success": False, "message": f"暂存变更失败: {result.stderr}"}
        if "No local changes to save" in result.stdout:
            return {"success": True, "message": "没有本地变更需要暂存"}
        return {"success": True, "message": "变更已暂存"}

    def stash_pop(self, repo_path: str) -> dict:
        result = self._exec_in_repo(repo_path, "stash pop", timeout=30.0)
        if not result.success:
            has_conflicts = "CONFLICT" in result.stdout or "CONFLICT" in result.stderr
            if has_conflicts:
                return {"success": False, "message": "恢复暂存存在冲突，请手动解决"}
            return {"success": False, "message": f"恢复暂存失败: {result.stderr}"}
        return {"success": True, "message": "暂存变更已恢复"}

    def checkout_commit(self, repo_path: str, commit_hash: str) -> dict:
        result = self._exec_in_repo(repo_path, f"checkout {commit_hash}")
        if not result.success:
            return {"success": False, "message": f"检出提交失败: {result.stderr}"}
        return {"success": True, "message": f"已检出提交 '{commit_hash}'"}

    def revert_commit(self, repo_path: str, commit_hash: str, no_commit: bool = False) -> dict:
        parts = ["revert"]
        if no_commit:
            parts.append("--no-commit")
        parts.append(commit_hash)
        cmd = " ".join(parts)
        result = self._exec_in_repo(repo_path, cmd, timeout=30.0)
        if not result.success:
            has_conflicts = "CONFLICT" in result.stdout or "CONFLICT" in result.stderr
            if has_conflicts:
                return {"success": False, "message": "回退提交存在冲突，请手动解决"}
            return {"success": False, "message": f"回退提交失败: {result.stderr}"}
        return {"success": True, "message": f"提交 '{commit_hash}' 已回退"}
