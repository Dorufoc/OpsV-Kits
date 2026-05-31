from __future__ import annotations

import asyncio
import concurrent.futures
import fnmatch
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from app.core.git_operations import GitOperationError, GitOperations
from app.core.git_sync_scheduler import git_sync_scheduler
from app.core.remote_executor import RemoteExecutor
from app.core.webhook_handler import (
    WebhookVerificationError,
    parse_webhook_event,
    verify_webhook,
)
from app.models.git_integration import (
    DeployPipeline,
    DeployRecord,
    DeployStage,
    GitBranch,
    GitCommit,
    GitDiff,
    GitRepo,
    GitSyncConfig,
    GitSyncLog,
    WebhookConfig,
)


class GitIntegrationService:
    def __init__(self):
        self._webhook_configs: dict[str, WebhookConfig] = {}
        self._deploy_pipelines: dict[str, DeployPipeline] = {}
        self._deploy_records: dict[str, DeployRecord] = {}
        self._sync_configs: dict[str, GitSyncConfig] = {}
        self._sync_logs: dict[str, list[GitSyncLog]] = {}
        self._cache: dict[str, tuple[float, object]] = {}
        self._cache_ttl: float = 30.0
        self._lock = threading.Lock()

    def _new_id(self) -> str:
        return uuid4().hex[:12]

    def _get_git(self, account_alias: str) -> GitOperations:
        return GitOperations(account_alias)

    def _get_cached(self, key: str):
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.time() - ts > self._cache_ttl:
                del self._cache[key]
                return None
            return value

    def _set_cached(self, key: str, value: object):
        with self._lock:
            self._cache[key] = (time.time(), value)

    def _invalidate_cache(self, account_alias: str, repo_path: str):
        prefix = f"{account_alias}:{repo_path}:"
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]

    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=30)

    def init_repo(self, account_alias: str, repo_path: str, gitignore_template: Optional[str] = None) -> dict:
        git = self._get_git(account_alias)
        result = git.init(repo_path, gitignore_template=gitignore_template)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def clone_repo(self, account_alias: str, repo_url: str, target_path: str, branch: Optional[str] = None, depth: Optional[int] = None) -> dict:
        git = self._get_git(account_alias)
        result = git.clone(repo_url, target_path, branch=branch, depth=depth)
        self._invalidate_cache(account_alias, target_path)
        return result

    def add_remote(self, account_alias: str, repo_path: str, remote_name: str, remote_url: str) -> dict:
        git = self._get_git(account_alias)
        result = git.add_remote(repo_path, remote_name, remote_url)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def set_remote_url(self, account_alias: str, repo_path: str, remote_name: str, remote_url: str) -> dict:
        git = self._get_git(account_alias)
        result = git.set_remote_url(repo_path, remote_name, remote_url)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def get_repo_info(self, account_alias: str, repo_path: str, force_refresh: bool = False) -> dict:
        cache_key = f"{account_alias}:{repo_path}:repo_info"
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        git = self._get_git(account_alias)
        result = git.get_repo_info(repo_path)
        self._set_cached(cache_key, result)
        return result

    def list_branches(self, account_alias: str, repo_path: str, force_refresh: bool = False) -> list[dict]:
        cache_key = f"{account_alias}:{repo_path}:branches"
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        git = self._get_git(account_alias)
        result = git.list_branches(repo_path)
        self._set_cached(cache_key, result)
        return result

    def create_branch(self, account_alias: str, repo_path: str, branch_name: str, base_ref: Optional[str] = None, checkout: bool = False) -> dict:
        git = self._get_git(account_alias)
        result = git.create_branch(repo_path, branch_name, base_ref=base_ref, checkout=checkout)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def switch_branch(self, account_alias: str, repo_path: str, branch_name: str, stash_if_dirty: bool = False) -> dict:
        git = self._get_git(account_alias)
        if git.has_uncommitted_changes(repo_path):
            if stash_if_dirty:
                stash_result = git.stash(repo_path)
                if not stash_result["success"]:
                    return stash_result
                switch_result = git.switch_branch(repo_path, branch_name)
                if not switch_result["success"]:
                    return switch_result
                pop_result = git.stash_pop(repo_path)
                self._invalidate_cache(account_alias, repo_path)
                if not pop_result["success"]:
                    return {"success": False, "message": f"分支已切换但恢复暂存失败: {pop_result['message']}"}
                return {"success": True, "message": f"已切换到分支 '{branch_name}'，暂存变更已恢复"}
            else:
                return {"success": False, "message": "工作区有未提交变更，请先提交或使用 stash_if_dirty=True"}
        result = git.switch_branch(repo_path, branch_name)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def merge_branch(self, account_alias: str, repo_path: str, source_branch: str, target_branch: Optional[str] = None) -> dict:
        git = self._get_git(account_alias)
        result = git.merge_branch(repo_path, source_branch, target_branch=target_branch)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def delete_branch(self, account_alias: str, repo_path: str, branch_name: str, force: bool = False) -> dict:
        git = self._get_git(account_alias)
        if not force:
            if not git.is_branch_merged(repo_path, branch_name):
                return {"success": False, "message": f"分支 '{branch_name}' 尚未合并，如需强制删除请使用 force=True"}
        result = git.delete_branch(repo_path, branch_name, force=force)
        self._invalidate_cache(account_alias, repo_path)
        return result

    def compare_branches(self, account_alias: str, repo_path: str, source: str, target: str) -> dict:
        git = self._get_git(account_alias)
        return git.compare_branches(repo_path, source, target)

    def get_commit_log(self, account_alias: str, repo_path: str, author: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None, keyword: Optional[str] = None, page: int = 1, page_size: int = 20) -> dict:
        git = self._get_git(account_alias)
        return git.log(repo_path, author=author, since=since, until=until, keyword=keyword, page=page, page_size=page_size)

    def get_commit_detail(self, account_alias: str, repo_path: str, commit_hash: str) -> dict:
        git = self._get_git(account_alias)
        return git.show_commit(repo_path, commit_hash)

    def get_diff(self, account_alias: str, repo_path: str, from_ref: str, to_ref: str, file_path: Optional[str] = None) -> str:
        git = self._get_git(account_alias)
        return git.diff(repo_path, from_ref, to_ref, file_path=file_path)

    def create_webhook_config(self, account_alias: str, repo_path: str, platform: str, events: list[str], branch_filter: str = "*", deploy_pipeline_id: Optional[str] = None) -> WebhookConfig:
        hook_id = self._new_id()
        secret = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        config = WebhookConfig(
            hook_id=hook_id,
            account_alias=account_alias,
            repo_path=repo_path,
            platform=platform,
            secret=secret,
            events=events,
            branch_filter=branch_filter,
            deploy_pipeline_id=deploy_pipeline_id,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        self._webhook_configs[hook_id] = config
        return config

    def get_webhook_config(self, hook_id: str) -> Optional[WebhookConfig]:
        return self._webhook_configs.get(hook_id)

    def list_webhook_configs(self, account_alias: Optional[str] = None) -> list[WebhookConfig]:
        configs = list(self._webhook_configs.values())
        if account_alias:
            configs = [c for c in configs if c.account_alias == account_alias]
        return configs

    def update_webhook_config(self, hook_id: str, **kwargs) -> Optional[WebhookConfig]:
        config = self._webhook_configs.get(hook_id)
        if config is None:
            return None
        update_data = config.model_dump()
        for k, v in kwargs.items():
            if v is not None and k in update_data:
                update_data[k] = v
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        config = WebhookConfig(**update_data)
        self._webhook_configs[hook_id] = config
        return config

    def delete_webhook_config(self, hook_id: str) -> bool:
        return self._webhook_configs.pop(hook_id, None) is not None

    def handle_webhook_event(self, hook_id: str, body: bytes, headers: dict[str, str]) -> dict:
        config = self._webhook_configs.get(hook_id)
        if config is None:
            return {"success": False, "message": f"Webhook 配置 {hook_id} 不存在"}
        if not config.enabled:
            return {"success": False, "message": "Webhook 已禁用"}
        try:
            verify_webhook(config.platform, body, headers, config.secret)
        except WebhookVerificationError as e:
            return {"success": False, "message": str(e)}
        try:
            event = parse_webhook_event(config.platform, body, headers)
        except WebhookVerificationError as e:
            return {"success": False, "message": str(e)}
        branch = event.branch
        if branch and config.branch_filter != "*":
            if not fnmatch.fnmatch(branch, config.branch_filter):
                return {"success": True, "message": f"分支 '{branch}' 不匹配过滤器 '{config.branch_filter}'", "matched": False}
        result = {
            "success": True,
            "message": "Webhook 事件处理成功",
            "matched": True,
            "event": event.to_dict(),
        }
        if config.deploy_pipeline_id:
            pipeline = self._deploy_pipelines.get(config.deploy_pipeline_id)
            if pipeline:
                record = self.execute_deploy_pipeline(
                    pipeline_id=config.deploy_pipeline_id,
                    trigger_type="webhook",
                    trigger_info=f"{event.platform}:{event.event_type}:{branch or event.tag or 'unknown'}",
                )
                result["deploy_record_id"] = record.record_id
        return result

    def create_deploy_pipeline(self, name: str, account_alias: str, repo_path: str, trigger_branches: list[str], trigger_tags: str, stages: list[dict], auto_deploy_on_sync: bool = False) -> DeployPipeline:
        pipeline_id = self._new_id()
        now = datetime.now(timezone.utc).isoformat()
        stage_models = [DeployStage(**s) for s in stages]
        pipeline = DeployPipeline(
            pipeline_id=pipeline_id,
            name=name,
            account_alias=account_alias,
            repo_path=repo_path,
            trigger_branches=trigger_branches,
            trigger_tags=trigger_tags,
            stages=stage_models,
            auto_deploy_on_sync=auto_deploy_on_sync,
            created_at=now,
            updated_at=now,
        )
        self._deploy_pipelines[pipeline_id] = pipeline
        return pipeline

    def get_deploy_pipeline(self, pipeline_id: str) -> Optional[DeployPipeline]:
        return self._deploy_pipelines.get(pipeline_id)

    def list_deploy_pipelines(self, account_alias: Optional[str] = None) -> list[DeployPipeline]:
        pipelines = list(self._deploy_pipelines.values())
        if account_alias:
            pipelines = [p for p in pipelines if p.account_alias == account_alias]
        return pipelines

    def update_deploy_pipeline(self, pipeline_id: str, **kwargs) -> Optional[DeployPipeline]:
        pipeline = self._deploy_pipelines.get(pipeline_id)
        if pipeline is None:
            return None
        update_data = pipeline.model_dump()
        for k, v in kwargs.items():
            if v is not None and k in update_data:
                update_data[k] = v
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "stages" in kwargs and kwargs["stages"] is not None:
            update_data["stages"] = [DeployStage(**s) if isinstance(s, dict) else s for s in kwargs["stages"]]
        pipeline = DeployPipeline(**update_data)
        self._deploy_pipelines[pipeline_id] = pipeline
        return pipeline

    def delete_deploy_pipeline(self, pipeline_id: str) -> bool:
        return self._deploy_pipelines.pop(pipeline_id, None) is not None

    def execute_deploy_pipeline(self, pipeline_id: str, trigger_type: str = "manual", trigger_info: str = "") -> DeployRecord:
        pipeline = self._deploy_pipelines.get(pipeline_id)
        if pipeline is None:
            raise ValueError(f"部署流程 {pipeline_id} 不存在")
        git = self._get_git(pipeline.account_alias)
        repo_info = git.get_repo_info(pipeline.repo_path)
        current_branch = repo_info.get("current_branch", "unknown")
        latest_commit = repo_info.get("latest_commit") or {}
        commit_hash = latest_commit.get("hash", "unknown")
        record_id = self._new_id()
        now = datetime.now(timezone.utc).isoformat()
        record = DeployRecord(
            record_id=record_id,
            pipeline_id=pipeline_id,
            account_alias=pipeline.account_alias,
            repo_path=pipeline.repo_path,
            trigger_type=trigger_type,
            trigger_info=trigger_info,
            branch=current_branch,
            commit_hash=commit_hash,
            status="pending",
            started_at=now,
            log="",
            stages_result=[],
        )
        self._deploy_records[record_id] = record

        def _append_output(rec, stage_res, text):
            stage_res["output"] += text
            rec.log += text

        def _run():
            record.status = "running"
            executor = RemoteExecutor(pipeline.account_alias)
            for idx, stage in enumerate(pipeline.stages):
                stage_result = {
                    "name": stage.name,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                    "exit_code": None,
                    "output": "",
                }
                record.stages_result.append(stage_result)
                resolved_dir = executor.resolve_path(stage.work_dir)
                env_prefix = " ".join(f"{k}={v}" for k, v in stage.env_vars.items()) if stage.env_vars else ""
                all_ok = True
                for cmd in stage.commands:
                    full_cmd = f"cd {resolved_dir}"
                    if env_prefix:
                        full_cmd += f" && {env_prefix}"
                    full_cmd += f" && {cmd} 2>&1"
                    try:
                        exit_code = executor.exec_command_stream(
                            full_cmd,
                            output_callback=lambda text, r=record, s=stage_result: _append_output(r, s, text),
                            timeout=float(stage.timeout),
                        )
                        stage_result["exit_code"] = exit_code
                        if exit_code != 0:
                            all_ok = False
                            if not stage.continue_on_error:
                                stage_result["status"] = "failed"
                                stage_result["completed_at"] = datetime.now(timezone.utc).isoformat()
                                record.status = "failed"
                                record.completed_at = datetime.now(timezone.utc).isoformat()
                                return
                    except Exception as e:
                        all_ok = False
                        stage_result["output"] += str(e)
                        if not stage.continue_on_error:
                            stage_result["status"] = "failed"
                            stage_result["completed_at"] = datetime.now(timezone.utc).isoformat()
                            record.status = "failed"
                            record.completed_at = datetime.now(timezone.utc).isoformat()
                            return
                stage_result["status"] = "completed" if all_ok else "completed_with_errors"
                stage_result["completed_at"] = datetime.now(timezone.utc).isoformat()
            record.status = "completed"
            record.completed_at = datetime.now(timezone.utc).isoformat()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return record

    def list_deploy_records(self, account_alias: Optional[str] = None, pipeline_id: Optional[str] = None, limit: int = 20) -> list[DeployRecord]:
        records = list(self._deploy_records.values())
        if account_alias:
            records = [r for r in records if r.account_alias == account_alias]
        if pipeline_id:
            records = [r for r in records if r.pipeline_id == pipeline_id]
        records.sort(key=lambda r: r.started_at or "", reverse=True)
        return records[:limit]

    def get_deploy_record(self, record_id: str) -> Optional[DeployRecord]:
        return self._deploy_records.get(record_id)

    def rollback_deploy(self, record_id: str) -> DeployRecord:
        original = self._deploy_records.get(record_id)
        if original is None:
            raise ValueError(f"部署记录 {record_id} 不存在")
        git = self._get_git(original.account_alias)
        revert_result = git.revert_commit(original.repo_path, original.commit_hash)
        if not revert_result["success"]:
            checkout_result = git.checkout_commit(original.repo_path, original.commit_hash)
            if not checkout_result["success"]:
                raise GitOperationError(f"回滚失败: {revert_result['message']}; 检出也失败: {checkout_result['message']}")
        pipeline = self._deploy_pipelines.get(original.pipeline_id)
        if pipeline is None:
            raise ValueError(f"关联部署流程 {original.pipeline_id} 不存在")
        return self.execute_deploy_pipeline(
            pipeline_id=original.pipeline_id,
            trigger_type="rollback",
            trigger_info=f"回滚自 {record_id} (commit: {original.commit_hash})",
        )

    def create_sync_config(self, account_alias: str, repo_path: str, enabled: bool = True, check_interval: int = 1800, sync_mode: str = "notify_only", auto_deploy: bool = False, deploy_pipeline_id: Optional[str] = None, branch: str = "", ff_only: bool = True) -> GitSyncConfig:
        config_id = self._new_id()
        now = datetime.now(timezone.utc).isoformat()
        config = GitSyncConfig(
            config_id=config_id,
            account_alias=account_alias,
            repo_path=repo_path,
            enabled=enabled,
            check_interval=check_interval,
            sync_mode=sync_mode,
            auto_deploy=auto_deploy,
            deploy_pipeline_id=deploy_pipeline_id,
            branch=branch,
            ff_only=ff_only,
            created_at=now,
            updated_at=now,
        )
        self._sync_configs[config_id] = config
        if enabled:
            self._run_async(git_sync_scheduler.add_task({
                "config_id": config_id,
                "account_alias": account_alias,
                "repo_path": repo_path,
                "check_interval": check_interval,
                "sync_mode": sync_mode,
                "auto_deploy": auto_deploy,
                "deploy_pipeline_id": deploy_pipeline_id,
                "branch": branch,
                "ff_only": ff_only,
            }))
        return config

    def get_sync_config(self, config_id: str) -> Optional[GitSyncConfig]:
        return self._sync_configs.get(config_id)

    def list_sync_configs(self, account_alias: Optional[str] = None) -> list[GitSyncConfig]:
        configs = list(self._sync_configs.values())
        if account_alias:
            configs = [c for c in configs if c.account_alias == account_alias]
        return configs

    def update_sync_config(self, config_id: str, **kwargs) -> Optional[GitSyncConfig]:
        config = self._sync_configs.get(config_id)
        if config is None:
            return None
        update_data = config.model_dump()
        for k, v in kwargs.items():
            if v is not None and k in update_data:
                update_data[k] = v
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        config = GitSyncConfig(**update_data)
        self._sync_configs[config_id] = config
        need_reschedule = any(
            k in kwargs for k in ("enabled", "check_interval", "sync_mode", "auto_deploy", "branch", "ff_only", "deploy_pipeline_id")
        )
        if need_reschedule:
            if config.enabled:
                self._run_async(git_sync_scheduler.update_task(config_id, {
                    "config_id": config_id,
                    "account_alias": config.account_alias,
                    "repo_path": config.repo_path,
                    "check_interval": config.check_interval,
                    "sync_mode": config.sync_mode,
                    "auto_deploy": config.auto_deploy,
                    "deploy_pipeline_id": config.deploy_pipeline_id,
                    "branch": config.branch,
                    "ff_only": config.ff_only,
                }))
            else:
                self._run_async(git_sync_scheduler.remove_task(config_id))
        return config

    def delete_sync_config(self, config_id: str) -> bool:
        config = self._sync_configs.pop(config_id, None)
        if config is None:
            return False
        if config.enabled:
            self._run_async(git_sync_scheduler.remove_task(config_id))
        return True

    def manual_pull(self, config_id: str) -> dict:
        config = self._sync_configs.get(config_id)
        if config is None:
            return {"success": False, "message": f"同步配置 {config_id} 不存在"}
        result = self._run_async(git_sync_scheduler.trigger_manual_pull(config_id))
        action = "pull"
        if result.get("success"):
            self._add_sync_log(
                config_id=config_id,
                action=action,
                result="success",
                message=result.get("message", ""),
            )
        else:
            msg = result.get("message", "")
            if "conflict" in msg.lower():
                self._add_sync_log(
                    config_id=config_id,
                    action=action,
                    result="conflict",
                    message=msg,
                )
            else:
                self._add_sync_log(
                    config_id=config_id,
                    action=action,
                    result="error",
                    message=msg,
                )
        return result

    def get_sync_status(self, config_id: str) -> Optional[dict]:
        config = self._sync_configs.get(config_id)
        if config is None:
            return None
        status = git_sync_scheduler.get_task_status(config_id)
        result = config.model_dump()
        if status:
            result.update(status)
        return result

    def get_sync_logs(self, config_id: str, limit: int = 50) -> list[dict]:
        logs = self._sync_logs.get(config_id, [])
        return [log.model_dump() for log in logs[-limit:]]

    def _add_sync_log(self, config_id: str, action: str, result: str, message: str, commits_behind: int = 0, commits_ahead: int = 0, changed_files: Optional[list[str]] = None):
        config = self._sync_configs.get(config_id)
        if config is None:
            return
        log_id = self._new_id()
        now = datetime.now(timezone.utc).isoformat()
        log = GitSyncLog(
            log_id=log_id,
            config_id=config_id,
            account_alias=config.account_alias,
            repo_path=config.repo_path,
            action=action,
            result=result,
            message=message,
            commits_behind=commits_behind,
            commits_ahead=commits_ahead,
            changed_files=changed_files or [],
            timestamp=now,
        )
        if config_id not in self._sync_logs:
            self._sync_logs[config_id] = []
        self._sync_logs[config_id].append(log)
        if len(self._sync_logs[config_id]) > 50:
            self._sync_logs[config_id] = self._sync_logs[config_id][-50:]


git_integration_service = GitIntegrationService()
