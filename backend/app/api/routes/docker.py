from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.docker_service import DockerCommandError, docker_service
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docker", tags=["docker"])


# ── 请求/响应模型 ────────────────────────────────────────────────


class AccountAliasMixin(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")


class InstallRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")


class PullImageRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    image_name: str = Field(..., description="镜像名称 (如 nginx:latest)")


class BuildImageRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    tag: str = Field(..., description="镜像标签 (如 myapp:latest)")
    dockerfile_path: str = Field(..., description="Dockerfile 路径")
    context_path: str = Field(..., description="构建上下文路径")


class ExecCommandRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    command: str = Field(..., description="要在容器中执行的命令")


class CreateNetworkRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    name: str = Field(..., description="网络名称")
    driver: str = Field(default="bridge", description="网络驱动类型")


class CreateVolumeRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    name: str = Field(..., description="卷名称")


class ComposeUpRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="Compose 项目路径或 compose 文件路径")
    detach: bool = Field(default=False, description="是否后台运行")


class ComposeDownRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="Compose 项目路径或 compose 文件路径")


class ContainerActionRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    timeout: Optional[int] = Field(default=None, description="停止超时时间(秒)")


class RemoveContainerRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    force: bool = Field(default=False, description="是否强制删除运行中容器")


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
    if "is already running" in error_msg_lower:
        raise HTTPException(
            status_code=409,
            detail=f"容器已在运行中",
        )
    if "is already paused" in error_msg_lower:
        raise HTTPException(
            status_code=409,
            detail=f"容器已暂停，请先恢复再操作",
        )
    if "timeout" in error_msg_lower:
        raise HTTPException(
            status_code=504,
            detail=f"Docker 操作超时: {error_msg}",
        )
    raise HTTPException(status_code=400, detail=f"Docker 操作失败: {error_msg}")


# ── 环境检测 ─────────────────────────────────────────────────────


@router.get("/info")
async def get_docker_info(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    installed = docker_service.check_docker_installed(account_alias)
    version = docker_service.get_docker_version(account_alias) if installed else None
    running = docker_service.check_docker_running(account_alias) if installed else False
    permissions = docker_service.check_docker_permissions(account_alias) if installed else {}

    return {
        "installed": installed,
        "version": version,
        "running": running,
        "permissions": permissions,
    }


@router.post("/install")
async def install_docker(data: InstallRequest):
    _verify_account(data.account_alias)
    try:
        message = docker_service.install_docker(data.account_alias)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "install_docker")


# ── 容器管理 ─────────────────────────────────────────────────────


@router.get("/containers")
async def list_containers(
    account_alias: str = Query(..., description="SSH 账户别名"),
    all: bool = Query(False, description="是否列出所有容器（包括已停止的）"),
):
    _verify_account(account_alias)
    try:
        return docker_service.list_containers(account_alias, all=all)
    except DockerCommandError as e:
        _handle_docker_error(e, "list_containers")


@router.get("/containers/{container_id}")
async def get_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.get_container_info(account_alias, container_id)
    except DockerCommandError as e:
        if "No such object" in str(e):
            raise HTTPException(status_code=404, detail=f"容器 '{container_id}' 未找到")
        _handle_docker_error(e, "get_container")


@router.post("/containers/{container_id}/start")
async def start_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        info = docker_service.get_container_info(account_alias, container_id)
        state = info.get("State", {})
        if state.get("Status") == "running":
            logger.info(
                "容器已在运行中 [account=%s, container=%s]",
                account_alias, container_id,
            )
            return {"message": f"容器 {container_id} 已在运行中"}
    except DockerCommandError:
        pass

    try:
        message = docker_service.start_container(account_alias, container_id)
        return {"message": message}
    except DockerCommandError as e:
        if "already running" in str(e).lower():
            logger.info(
                "容器已在运行中（竞争条件）[account=%s, container=%s]",
                account_alias, container_id,
            )
            return {"message": f"容器 {container_id} 已在运行中"}
        _handle_docker_error(e, f"start_container({account_alias})")


@router.post("/containers/{container_id}/stop")
async def stop_container(
    container_id: str,
    data: ContainerActionRequest,
):
    _verify_account(data.account_alias)
    try:
        message = docker_service.stop_container(
            data.account_alias, container_id, timeout=data.timeout
        )
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "stop_container")


@router.post("/containers/{container_id}/restart")
async def restart_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.restart_container(account_alias, container_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "restart_container")


@router.post("/containers/{container_id}/kill")
async def kill_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.kill_container(account_alias, container_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "kill_container")


@router.delete("/containers/{container_id}")
async def remove_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
    force: bool = Query(False, description="是否强制删除运行中容器"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.remove_container(
            account_alias, container_id, force=force
        )
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "remove_container")


@router.post("/containers/{container_id}/pause")
async def pause_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.pause_container(account_alias, container_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "pause_container")


@router.post("/containers/{container_id}/unpause")
async def unpause_container(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.unpause_container(account_alias, container_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "unpause_container")


@router.get("/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
    tail: int = Query(100, description="返回最近 N 行日志"),
    timestamps: bool = Query(False, description="是否显示时间戳"),
):
    _verify_account(account_alias)
    try:
        logs = docker_service.get_container_logs(
            account_alias, container_id, tail=tail, timestamps=timestamps
        )
        return {"logs": logs.splitlines() if logs else []}
    except DockerCommandError as e:
        if "No such object" in str(e):
            raise HTTPException(status_code=404, detail=f"容器 '{container_id}' 未找到")
        _handle_docker_error(e, "get_container_logs")


@router.websocket("/ws/containers/{container_id}/logs")
async def container_logs_ws(
    websocket: WebSocket,
    container_id: str,
):
    await websocket.accept()
    account_alias = None
    try:
        data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        msg = json.loads(data)
        account_alias = msg.get("account_alias")
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

    stop_event = threading.Event()

    def _stream_logs():
        conn = None
        try:
            account = ssh_account_service.get_account(account_alias)
            if account is None:
                raise ValueError("SSH 账户不存在")
            conn = ssh_account_service.pool.get_connection(account)
            transport = conn.manager._transport
            if transport is None:
                raise RuntimeError("SSH 传输通道未建立")
            chan = transport.open_session()
            chan.exec_command(f"docker logs -f --tail 100 {container_id} 2>&1")
            buf = ""
            while not stop_event.is_set():
                if chan.recv_ready():
                    raw = chan.recv(4096)
                    if not raw:
                        break
                    text = raw.decode("utf-8", errors="replace")
                    _safe_ws_send(websocket, {
                        "type": "log",
                        "data": text,
                    })
                elif chan.exit_status_ready():
                    break
                else:
                    time.sleep(0.05)
            chan.close()
        except Exception as e:
            _safe_ws_send(websocket, {
                "type": "error",
                "message": str(e),
            })
        finally:
            if conn is not None:
                ssh_account_service.pool.release_connection(conn)

    thread = threading.Thread(target=_stream_logs, daemon=True)
    thread.start()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("action") == "stop":
                stop_event.set()
                break
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        stop_event.set()


@router.get("/containers/{container_id}/stats")
async def get_container_stats(
    container_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        stats = docker_service.get_container_stats(account_alias, container_id)
        return stats
    except DockerCommandError as e:
        if "No such object" in str(e):
            raise HTTPException(status_code=404, detail=f"容器 '{container_id}' 未找到")
        _handle_docker_error(e, "get_container_stats")


@router.post("/containers/{container_id}/exec")
async def exec_in_container(
    container_id: str,
    data: ExecCommandRequest,
):
    _verify_account(data.account_alias)
    try:
        exit_code, stdout, stderr = docker_service.exec_in_container(
            data.account_alias, container_id, data.command
        )
        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }
    except DockerCommandError as e:
        _handle_docker_error(e, "exec_in_container")


# ── 镜像管理 ─────────────────────────────────────────────────────


@router.get("/images")
async def list_images(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.list_images(account_alias)
    except DockerCommandError as e:
        _handle_docker_error(e, "list_images")


@router.delete("/images/{image_id}")
async def remove_image(
    image_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.remove_image(account_alias, image_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "remove_image")


@router.post("/images/pull")
async def pull_image(data: PullImageRequest):
    _verify_account(data.account_alias)
    try:
        message = docker_service.pull_image(data.account_alias, data.image_name)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "pull_image")


@router.post("/images/build")
async def build_image(data: BuildImageRequest):
    _verify_account(data.account_alias)
    try:
        message = docker_service.build_image(
            data.account_alias, data.tag, data.dockerfile_path, data.context_path
        )
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "build_image")


@router.post("/images/prune")
async def prune_images(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        result = docker_service.prune_images(account_alias)
        return result
    except DockerCommandError as e:
        _handle_docker_error(e, "prune_images")


@router.get("/images/search")
async def search_images(
    account_alias: str = Query(..., description="SSH 账户别名"),
    term: str = Query(..., description="搜索关键词"),
):
    _verify_account(account_alias)
    try:
        return docker_service.search_images(account_alias, term)
    except DockerCommandError as e:
        _handle_docker_error(e, "search_images")


# ── 网络管理 ─────────────────────────────────────────────────────


@router.get("/networks")
async def list_networks(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.list_networks(account_alias)
    except DockerCommandError as e:
        _handle_docker_error(e, "list_networks")


@router.post("/networks", status_code=201)
async def create_network(data: CreateNetworkRequest):
    _verify_account(data.account_alias)
    try:
        network_id = docker_service.create_network(
            data.account_alias, data.name, data.driver
        )
        return {"network_id": network_id, "name": data.name, "driver": data.driver}
    except DockerCommandError as e:
        _handle_docker_error(e, "create_network")


@router.delete("/networks/{network_id}")
async def remove_network(
    network_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.remove_network(account_alias, network_id)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "remove_network")


@router.get("/networks/{network_id}")
async def get_network_info(
    network_id: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.get_network_info(account_alias, network_id)
    except DockerCommandError as e:
        if "network" in str(e).lower() and "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"网络 '{network_id}' 未找到")
        _handle_docker_error(e, "get_network_info")


# ── 卷管理 ───────────────────────────────────────────────────────


@router.get("/volumes")
async def list_volumes(
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.list_volumes(account_alias)
    except DockerCommandError as e:
        _handle_docker_error(e, "list_volumes")


@router.post("/volumes", status_code=201)
async def create_volume(data: CreateVolumeRequest):
    _verify_account(data.account_alias)
    try:
        volume_name = docker_service.create_volume(data.account_alias, data.name)
        return {"volume_name": volume_name}
    except DockerCommandError as e:
        _handle_docker_error(e, "create_volume")


@router.delete("/volumes/{volume_name}")
async def remove_volume(
    volume_name: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        message = docker_service.remove_volume(account_alias, volume_name)
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "remove_volume")


@router.get("/volumes/{volume_name}")
async def get_volume_info(
    volume_name: str,
    account_alias: str = Query(..., description="SSH 账户别名"),
):
    _verify_account(account_alias)
    try:
        return docker_service.get_volume_info(account_alias, volume_name)
    except DockerCommandError as e:
        if "volume" in str(e).lower() and "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"卷 '{volume_name}' 未找到")
        _handle_docker_error(e, "get_volume_info")


# ── Compose 管理 ────────────────────────────────────────────────


@router.get("/compose/projects")
async def list_compose_projects(
    account_alias: str = Query(..., description="SSH 账户别名"),
    search_path: str = Query("/", description="搜索路径"),
):
    _verify_account(account_alias)
    try:
        return docker_service.find_compose_projects(
            account_alias, search_path=search_path
        )
    except DockerCommandError as e:
        _handle_docker_error(e, "list_compose_projects")


@router.post("/compose/up")
async def compose_up(data: ComposeUpRequest):
    _verify_account(data.account_alias)
    try:
        message = docker_service.compose_up(
            data.account_alias, data.project_path, detach=data.detach
        )
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "compose_up")


@router.post("/compose/down")
async def compose_down(data: ComposeDownRequest):
    _verify_account(data.account_alias)
    try:
        message = docker_service.compose_down(
            data.account_alias, data.project_path
        )
        return {"message": message}
    except DockerCommandError as e:
        _handle_docker_error(e, "compose_down")


def _safe_ws_send(websocket: WebSocket, data: dict[str, Any]) -> None:
    try:
        loop = _get_running_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                websocket.send_json(data), loop
            )
    except Exception:
        pass


def _get_running_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None