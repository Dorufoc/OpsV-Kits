from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.docker_service import DockerCommandError
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docker-store", tags=["docker-store"])


# ── 请求/响应模型 ────────────────────────────────────────────────


class InstallRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    user_config: dict[str, Any] = Field(default_factory=dict, description="用户自定义配置")


class UninstallRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    purge_data: bool = Field(default=False, description="是否同时清除数据")


class RegistryMirrorRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    mirror_url: str = Field(..., description="镜像源地址")


# ── 辅助函数 ─────────────────────────────────────────────────────


def _verify_account(account_alias: str) -> None:
    account = ssh_account_service.get_account(account_alias)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"SSH 账户 '{account_alias}' 不存在",
        )


def _handle_docker_error(e: DockerCommandError, context: str = "") -> None:
    error_msg = str(e)
    error_msg_lower = error_msg.lower()
    ctx = f"[{context}] " if context else ""

    logger.error(f"Docker 命令执行失败 {ctx}(exit_code={e.exit_code}): {error_msg}")

    if "command not found" in error_msg_lower:
        raise HTTPException(
            status_code=503,
            detail=f"Docker 未安装: {error_msg}",
        )
    if "not found" in error_msg_lower or "no such" in error_msg_lower:
        raise HTTPException(
            status_code=404,
            detail=f"资源未找到: {error_msg}",
        )
    if "permission denied" in error_msg_lower or "got permission denied" in error_msg_lower:
        raise HTTPException(
            status_code=403,
            detail=f"Docker 权限不足: {error_msg}",
        )
    if "timeout" in error_msg_lower:
        raise HTTPException(
            status_code=504,
            detail=f"Docker 操作超时: {error_msg}",
        )
    raise HTTPException(status_code=400, detail=f"Docker 操作失败: {error_msg}")


# ── 应用商店 ─────────────────────────────────────────────────────


@router.get("/apps")
async def list_apps(
    account_alias: str = Query(..., description="SSH 账户别名"),
    category: Optional[str] = Query(None, description="应用分类过滤"),
):
    _verify_account(account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.list_apps(account_alias, category=category)
    except DockerCommandError as e:
        _handle_docker_error(e, "list_apps")


@router.get("/apps/{app_id}")
async def get_app_detail(
    app_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.get_app_detail(account_alias, app_id)
    except DockerCommandError as e:
        _handle_docker_error(e, "get_app_detail")


@router.post("/install/{app_id}")
async def install_app(
    app_id: str,
    data: InstallRequest,
):
    _verify_account(data.account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        result = docker_store_service.install_app(
            data.account_alias, app_id, user_config=data.user_config
        )
        return {"message": result}
    except DockerCommandError as e:
        _handle_docker_error(e, "install_app")


@router.post("/uninstall/{app_id}")
async def uninstall_app(
    app_id: str,
    data: UninstallRequest,
):
    _verify_account(data.account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        result = docker_store_service.uninstall_app(
            data.account_alias, app_id, purge_data=data.purge_data
        )
        return {"message": result}
    except DockerCommandError as e:
        _handle_docker_error(e, "uninstall_app")


@router.get("/status")
async def get_all_app_statuses(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.get_all_app_statuses(account_alias)
    except DockerCommandError as e:
        _handle_docker_error(e, "get_all_app_statuses")


@router.get("/status/{app_id}")
async def get_app_status(
    app_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.get_app_status(account_alias, app_id)
    except DockerCommandError as e:
        _handle_docker_error(e, "get_app_status")


# ── 镜像源配置 ───────────────────────────────────────────────────


@router.get("/registry-mirrors")
async def get_registry_mirrors(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        from app.core.docker_registry_mirrors import docker_registry_mirrors
        return docker_registry_mirrors.check_registry_mirrors(account_alias)
    except DockerCommandError as e:
        _handle_docker_error(e, "get_registry_mirrors")


@router.post("/registry-mirrors")
async def set_registry_mirrors(
    data: RegistryMirrorRequest,
):
    _verify_account(data.account_alias)
    try:
        from app.core.docker_registry_mirrors import docker_registry_mirrors
        result = docker_registry_mirrors.configure_registry_mirror(
            data.account_alias, data.mirror_url
        )
        return {"message": result}
    except DockerCommandError as e:
        _handle_docker_error(e, "set_registry_mirrors")
