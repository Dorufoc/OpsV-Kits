from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
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


@router.get("/size/{app_id}")
async def get_app_size(
    app_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    """获取应用的实际磁盘占用大小（镜像 + 容器层 + 卷 + 数据目录）."""
    _verify_account(account_alias)
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.get_app_size_info(account_alias, app_id)
    except DockerCommandError as e:
        _handle_docker_error(e, "get_app_size")


@router.get("/image-sizes/{app_id}")
async def get_image_version_sizes(
    app_id: str,
):
    """获取应用镜像各版本的 Docker Hub 大小信息.

    无需 SSH 账户，直接查询 Docker Hub Registry API.
    """
    try:
        from app.services.docker_store_service import docker_store_service
        return docker_store_service.get_image_version_sizes(app_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"查询镜像版本大小失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


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


# ── WebSocket 实时安装进度 ──────────────────────────────────────


@router.websocket("/ws/install/{app_id}")
async def install_app_ws(
    websocket: WebSocket,
    app_id: str,
):
    """WebSocket 端点：实时推送应用安装进度.

    连接后客户端需发送 JSON 消息:
    {
        "account_alias": "my-server",
        "user_config": { "PORT": 8080, "PASSWORD": "secret" }
    }

    服务端推送进度事件:
    - { "type": "stage", "stage": "prepare", "message": "..." }
    - { "type": "pull_progress", "progress_percent": 45.5, "message": "..." }
    - { "type": "pull_complete", "image": "nginx:latest", "message": "..." }
    - { "type": "complete", "success": true, "message": "..." }
    - { "type": "error", "message": "..." }
    """
    await websocket.accept()

    # 等待客户端发送安装参数
    account_alias = None
    user_config = {}
    try:
        data = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
        msg = json.loads(data)
        account_alias = msg.get("account_alias")
        user_config = msg.get("user_config", {})
        if not account_alias:
            await websocket.send_json({
                "type": "error",
                "message": "缺少 account_alias 参数",
            })
            await websocket.close()
            return
    except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        await websocket.close()
        return

    try:
        _verify_account(account_alias)
    except HTTPException as e:
        await websocket.send_json({"type": "error", "message": e.detail})
        await websocket.close()
        return

    from app.services.docker_store_service import docker_store_service

    # 用于线程间通信的队列
    progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    install_done = threading.Event()
    install_result: dict[str, Any] = {"success": False, "error": ""}

    def _on_progress(progress: dict[str, Any]) -> None:
        try:
            loop = _get_running_loop()
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    progress_queue.put(progress), loop
                )
        except Exception:
            pass

    def _do_install() -> None:
        try:
            result = docker_store_service.install_app_streaming(
                account_alias, app_id, user_config, on_progress=_on_progress
            )
            install_result["success"] = True
            install_result["result"] = result
        except Exception as e:
            install_result["success"] = False
            install_result["error"] = str(e)
            logger.error(f"应用安装失败 [app_id={app_id}]: {e}")
        finally:
            install_done.set()

    # 在后台线程执行安装
    install_thread = threading.Thread(target=_do_install, daemon=True)
    install_thread.start()

    # 推送进度事件
    try:
        while not install_done.is_set() or not progress_queue.empty():
            try:
                progress = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                await websocket.send_json(progress)
            except asyncio.TimeoutError:
                continue

        # 发送最终结果
        if install_result["success"]:
            await websocket.send_json({
                "type": "complete",
                "success": True,
                "message": install_result.get("result", {}).get("message", "安装完成"),
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": install_result.get("error", "安装失败"),
            })

        await websocket.close()
    except (WebSocketDisconnect, Exception):
        pass


def _get_running_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None
