from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, WebSocket, WebSocketDisconnect, Request, Response
from pydantic import BaseModel, Field

from app.services.git_integration_service import git_integration_service
from app.services.ssh_account_service import ssh_account_service

router = APIRouter(prefix="/git", tags=["git-integration"])
webhook_router = APIRouter(prefix="/git", tags=["git-webhook"])


def _verify_account(account_alias: str) -> None:
    account = ssh_account_service.get_account(account_alias)
    if account is None:
        raise HTTPException(
            status_code=404, detail=f"SSH 账户 '{account_alias}' 不存在"
        )


class RepoInitRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="远程仓库路径")
    gitignore_template: Optional[str] = Field(default=None, description="gitignore 模板: node/java/python")


class RepoCloneRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_url: str = Field(..., description="远程仓库 URL")
    target_path: str = Field(..., description="克隆目标路径")
    branch: Optional[str] = Field(default=None, description="指定分支")
    depth: Optional[int] = Field(default=None, description="克隆深度")


class RemoteConfigRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    remote_name: str = Field(default="origin", description="远程仓库名称")
    remote_url: str = Field(..., description="远程仓库 URL")


class BranchCreateRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    branch_name: str = Field(..., description="新分支名称")
    base_ref: Optional[str] = Field(default=None, description="基于的引用")
    checkout: bool = Field(default=False, description="是否同时切换到新分支")


class BranchSwitchRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    branch_name: str = Field(..., description="目标分支")
    stash_if_dirty: bool = Field(default=False, description="脏工作区是否自动 stash")


class BranchMergeRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    source_branch: str = Field(..., description="源分支")
    target_branch: Optional[str] = Field(default=None, description="目标分支（默认当前分支）")


class BranchDeleteRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    branch_name: str = Field(..., description="要删除的分支")
    force: bool = Field(default=False, description="是否强制删除")


class BranchCompareRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    source: str = Field(..., description="源分支")
    target: str = Field(..., description="目标分支")


class WebhookConfigCreateRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    platform: str = Field(..., description="平台: github/gitlab/gitee")
    events: list[str] = Field(default=["push"], description="监听事件")
    branch_filter: str = Field(default="*", description="分支过滤")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联部署流程 ID")


class WebhookConfigUpdateRequest(BaseModel):
    events: Optional[list[str]] = Field(default=None)
    branch_filter: Optional[str] = Field(default=None)
    deploy_pipeline_id: Optional[str] = Field(default=None)
    enabled: Optional[bool] = Field(default=None)


class DeployPipelineCreateRequest(BaseModel):
    name: str = Field(..., description="流程名称")
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    trigger_branches: list[str] = Field(default=["main"], description="触发分支")
    trigger_tags: str = Field(default="", description="触发标签正则")
    stages: list[dict] = Field(default=[], description="部署阶段列表")
    auto_deploy_on_sync: bool = Field(default=False, description="同步后自动部署")


class DeployPipelineUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None)
    trigger_branches: Optional[list[str]] = Field(default=None)
    trigger_tags: Optional[str] = Field(default=None)
    stages: Optional[list[dict]] = Field(default=None)
    auto_deploy_on_sync: Optional[bool] = Field(default=None)


class SyncConfigCreateRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    repo_path: str = Field(..., description="仓库路径")
    enabled: bool = Field(default=True, description="是否启用")
    check_interval: int = Field(default=1800, description="检查间隔秒数")
    sync_mode: str = Field(default="notify_only", description="同步模式: auto_pull/notify_only/manual")
    auto_deploy: bool = Field(default=False, description="拉取后自动部署")
    deploy_pipeline_id: Optional[str] = Field(default=None, description="关联部署流程")
    branch: str = Field(default="", description="跟踪分支")
    ff_only: bool = Field(default=True, description="仅快进合并")


class SyncConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = Field(default=None)
    check_interval: Optional[int] = Field(default=None)
    sync_mode: Optional[str] = Field(default=None)
    auto_deploy: Optional[bool] = Field(default=None)
    deploy_pipeline_id: Optional[str] = Field(default=None)
    branch: Optional[str] = Field(default=None)
    ff_only: Optional[bool] = Field(default=None)


@router.post("/repo/init")
async def init_repo(data: RepoInitRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.init_repo(data.account_alias, data.repo_path, data.gitignore_template)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化仓库失败: {e}")


@router.post("/repo/clone")
async def clone_repo(data: RepoCloneRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.clone_repo(data.account_alias, data.repo_url, data.target_path, data.branch, data.depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"克隆仓库失败: {e}")


@router.post("/repo/remote")
async def config_remote(data: RemoteConfigRequest):
    _verify_account(data.account_alias)
    try:
        result = git_integration_service.add_remote(data.account_alias, data.repo_path, data.remote_name, data.remote_url)
        if not result.get("success"):
            result = git_integration_service.set_remote_url(data.account_alias, data.repo_path, data.remote_name, data.remote_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置远程仓库失败: {e}")


@router.get("/repo/info")
async def get_repo_info(
    account_alias: str = Query(...),
    repo_path: str = Query(...),
    force_refresh: bool = Query(default=False),
):
    _verify_account(account_alias)
    try:
        return git_integration_service.get_repo_info(account_alias, repo_path, force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仓库信息失败: {e}")


@router.post("/branch/create")
async def create_branch(data: BranchCreateRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.create_branch(data.account_alias, data.repo_path, data.branch_name, data.base_ref, data.checkout)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建分支失败: {e}")


@router.post("/branch/switch")
async def switch_branch(data: BranchSwitchRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.switch_branch(data.account_alias, data.repo_path, data.branch_name, data.stash_if_dirty)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换分支失败: {e}")


@router.post("/branch/merge")
async def merge_branch(data: BranchMergeRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.merge_branch(data.account_alias, data.repo_path, data.source_branch, data.target_branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合并分支失败: {e}")


@router.post("/branch/delete")
async def delete_branch(data: BranchDeleteRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.delete_branch(data.account_alias, data.repo_path, data.branch_name, data.force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除分支失败: {e}")


@router.post("/branch/compare")
async def compare_branches(data: BranchCompareRequest):
    _verify_account(data.account_alias)
    try:
        return git_integration_service.compare_branches(data.account_alias, data.repo_path, data.source, data.target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比较分支失败: {e}")


@router.get("/commit/log")
async def get_commit_log(
    account_alias: str = Query(...),
    repo_path: str = Query(...),
    author: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    _verify_account(account_alias)
    try:
        return git_integration_service.get_commit_log(account_alias, repo_path, author, since, until, keyword, page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提交记录失败: {e}")


@router.get("/commit/detail")
async def get_commit_detail(
    account_alias: str = Query(...),
    repo_path: str = Query(...),
    commit_hash: str = Query(...),
):
    _verify_account(account_alias)
    try:
        return git_integration_service.get_commit_detail(account_alias, repo_path, commit_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提交详情失败: {e}")


@router.get("/commit/diff")
async def get_diff(
    account_alias: str = Query(...),
    repo_path: str = Query(...),
    from_ref: str = Query(...),
    to_ref: str = Query(...),
    file_path: Optional[str] = Query(default=None),
):
    _verify_account(account_alias)
    try:
        return {"diff": git_integration_service.get_diff(account_alias, repo_path, from_ref, to_ref, file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取差异失败: {e}")


@router.post("/webhook/config")
async def create_webhook_config(data: WebhookConfigCreateRequest):
    _verify_account(data.account_alias)
    try:
        config = git_integration_service.create_webhook_config(
            data.account_alias, data.repo_path, data.platform, data.events, data.branch_filter, data.deploy_pipeline_id
        )
        return config.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建 Webhook 配置失败: {e}")


@router.get("/webhook/config")
async def list_webhook_configs(account_alias: Optional[str] = Query(default=None)):
    configs = git_integration_service.list_webhook_configs(account_alias)
    return {"items": [c.model_dump() for c in configs]}


@router.get("/webhook/config/{hook_id}")
async def get_webhook_config(hook_id: str = Path(...)):
    config = git_integration_service.get_webhook_config(hook_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Webhook 配置 '{hook_id}' 不存在")
    return config.model_dump()


@router.put("/webhook/config/{hook_id}")
async def update_webhook_config(hook_id: str = Path(...), data: WebhookConfigUpdateRequest = ...):
    config = git_integration_service.update_webhook_config(hook_id, **data.model_dump(exclude_none=True))
    if config is None:
        raise HTTPException(status_code=404, detail=f"Webhook 配置 '{hook_id}' 不存在")
    return config.model_dump()


@router.delete("/webhook/config/{hook_id}")
async def delete_webhook_config(hook_id: str = Path(...)):
    if not git_integration_service.delete_webhook_config(hook_id):
        raise HTTPException(status_code=404, detail=f"Webhook 配置 '{hook_id}' 不存在")
    return {"success": True}


@webhook_router.post("/webhook/{hook_id}")
async def receive_webhook(hook_id: str = Path(...), request: Request = ...):
    config = git_integration_service.get_webhook_config(hook_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Webhook 配置不存在")
    if not config.enabled:
        return {"status": "ignored", "message": "Webhook 已禁用"}
    body = await request.body()
    headers = dict(request.headers)
    try:
        result = git_integration_service.handle_webhook_event(hook_id, body, headers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理 Webhook 事件失败: {e}")


@router.post("/pipeline")
async def create_deploy_pipeline(data: DeployPipelineCreateRequest):
    _verify_account(data.account_alias)
    try:
        pipeline = git_integration_service.create_deploy_pipeline(
            data.name, data.account_alias, data.repo_path, data.trigger_branches, data.trigger_tags, data.stages, data.auto_deploy_on_sync
        )
        return pipeline.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建部署流程失败: {e}")


@router.get("/pipeline")
async def list_deploy_pipelines(account_alias: Optional[str] = Query(default=None)):
    pipelines = git_integration_service.list_deploy_pipelines(account_alias)
    return {"items": [p.model_dump() for p in pipelines]}


@router.get("/pipeline/{pipeline_id}")
async def get_deploy_pipeline(pipeline_id: str = Path(...)):
    pipeline = git_integration_service.get_deploy_pipeline(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"部署流程 '{pipeline_id}' 不存在")
    return pipeline.model_dump()


@router.put("/pipeline/{pipeline_id}")
async def update_deploy_pipeline(pipeline_id: str = Path(...), data: DeployPipelineUpdateRequest = ...):
    pipeline = git_integration_service.update_deploy_pipeline(pipeline_id, **data.model_dump(exclude_none=True))
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"部署流程 '{pipeline_id}' 不存在")
    return pipeline.model_dump()


@router.delete("/pipeline/{pipeline_id}")
async def delete_deploy_pipeline(pipeline_id: str = Path(...)):
    if not git_integration_service.delete_deploy_pipeline(pipeline_id):
        raise HTTPException(status_code=404, detail=f"部署流程 '{pipeline_id}' 不存在")
    return {"success": True}


@router.post("/pipeline/{pipeline_id}/execute")
async def execute_deploy_pipeline(pipeline_id: str = Path(...)):
    pipeline = git_integration_service.get_deploy_pipeline(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"部署流程 '{pipeline_id}' 不存在")
    record = git_integration_service.execute_deploy_pipeline(pipeline_id, trigger_type="manual")
    return record.model_dump()


@router.get("/deploy/history")
async def list_deploy_history(
    account_alias: Optional[str] = Query(default=None),
    pipeline_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    records = git_integration_service.list_deploy_records(account_alias, pipeline_id, limit)
    return {"items": [r.model_dump() for r in records]}


@router.get("/deploy/history/{record_id}")
async def get_deploy_history(record_id: str = Path(...)):
    record = git_integration_service.get_deploy_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"部署记录 '{record_id}' 不存在")
    return record.model_dump()


@router.post("/deploy/history/{record_id}/rollback")
async def rollback_deploy(record_id: str = Path(...)):
    try:
        record = git_integration_service.rollback_deploy(record_id)
        return record.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回滚失败: {e}")


@router.post("/sync/config")
async def create_sync_config(data: SyncConfigCreateRequest):
    _verify_account(data.account_alias)
    try:
        config = git_integration_service.create_sync_config(
            data.account_alias, data.repo_path, data.enabled, data.check_interval,
            data.sync_mode, data.auto_deploy, data.deploy_pipeline_id, data.branch, data.ff_only
        )
        return config.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建同步配置失败: {e}")


@router.get("/sync/config")
async def list_sync_configs(account_alias: Optional[str] = Query(default=None)):
    configs = git_integration_service.list_sync_configs(account_alias)
    return {"items": [c.model_dump() for c in configs]}


@router.get("/sync/config/{config_id}")
async def get_sync_config(config_id: str = Path(...)):
    config = git_integration_service.get_sync_config(config_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"同步配置 '{config_id}' 不存在")
    return config.model_dump()


@router.put("/sync/config/{config_id}")
async def update_sync_config(config_id: str = Path(...), data: SyncConfigUpdateRequest = ...):
    config = git_integration_service.update_sync_config(config_id, **data.model_dump(exclude_none=True))
    if config is None:
        raise HTTPException(status_code=404, detail=f"同步配置 '{config_id}' 不存在")
    return config.model_dump()


@router.delete("/sync/config/{config_id}")
async def delete_sync_config(config_id: str = Path(...)):
    if not git_integration_service.delete_sync_config(config_id):
        raise HTTPException(status_code=404, detail=f"同步配置 '{config_id}' 不存在")
    return {"success": True}


@router.post("/sync/manual-pull/{config_id}")
async def manual_pull(config_id: str = Path(...)):
    try:
        return git_integration_service.manual_pull(config_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"手动拉取失败: {e}")


@router.get("/sync/status/{config_id}")
async def get_sync_status(config_id: str = Path(...)):
    status = git_integration_service.get_sync_status(config_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"同步配置 '{config_id}' 不存在")
    return status


@router.get("/sync/logs/{config_id}")
async def get_sync_logs(
    config_id: str = Path(...),
    limit: int = Query(default=50, ge=1, le=200),
):
    logs = git_integration_service.get_sync_logs(config_id, limit)
    return {"items": logs}


@router.websocket("/ws/deploy/{record_id}")
async def git_deploy_logs_ws(websocket: WebSocket, record_id: str = Path(...)):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "无效的 JSON"})
                continue
            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "get_status":
                record = git_integration_service.get_deploy_record(record_id)
                if record:
                    await websocket.send_json({"type": "status_update", "data": record.model_dump()})
                else:
                    await websocket.send_json({"type": "error", "message": f"记录 '{record_id}' 不存在"})
            else:
                await websocket.send_json({"type": "error", "message": f"未知消息类型: {msg_type}"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
