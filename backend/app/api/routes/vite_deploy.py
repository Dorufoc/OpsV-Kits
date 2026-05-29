from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.ssh_account_service import ssh_account_service
from app.services.vite_deploy_service import vite_deploy_service

router = APIRouter(prefix="/deploy/vite", tags=["vite-deploy"])
deploy_router = APIRouter(prefix="/deploy/vite", tags=["vite-deploy"])


class SetupRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    node_version: str = Field(default="20", description="Node.js 版本号")


class InstallDepsRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    force: bool = Field(default=False, description="是否强制重新安装依赖")


class BuildRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_path: str = Field(..., description="远程项目路径")
    build_command: str = Field(default="npm run build", description="构建命令")


class NginxRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_alias: str = Field(..., description="项目别名，用于 Nginx 配置命名")
    project_path: str = Field(..., description="远程项目路径")
    port: int = Field(default=8080, description="Nginx 监听端口")


class DeployRequest(BaseModel):
    account_alias: str = Field(..., description="SSH 账户别名")
    project_alias: str = Field(..., description="项目别名")
    project_path: str = Field(..., description="远程项目路径")
    node_version: str = Field(default="20", description="Node.js 版本号")
    nginx_port: int = Field(default=8080, description="Nginx 监听端口")
    build_command: str = Field(default="npm run build", description="构建命令")
    force: bool = Field(default=False, description="是否强制重新安装依赖")


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    message: str = ""
    step: str = ""
    log: str = ""
    url: Optional[str] = None


class EnvironmentCheckResponse(BaseModel):
    account_alias: str
    project_path: str
    node: dict
    nginx: dict
    vite: dict
    framework: dict
    all_ready: bool


def _verify_account(account_alias: str) -> None:
    account = ssh_account_service.get_account(account_alias)
    if account is None:
        raise HTTPException(
            status_code=404, detail=f"SSH 账户 '{account_alias}' 不存在"
        )


@router.get("/check", response_model=EnvironmentCheckResponse)
async def check_environment(
    account_alias: str = Query(..., description="SSH 账户别名"),
    project_path: str = Query(..., description="远程项目路径"),
):
    _verify_account(account_alias)
    try:
        result = vite_deploy_service.check_environment(account_alias, project_path)
        return EnvironmentCheckResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"环境检查失败: {e}")


@router.post("/setup", response_model=TaskStatusResponse)
async def setup_node(data: SetupRequest):
    _verify_account(data.account_alias)
    try:
        task = vite_deploy_service.install_node(
            account_alias=data.account_alias,
            project_path=data.project_path,
            version=data.node_version,
        )
        return TaskStatusResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 Node.js 安装失败: {e}")


@router.post("/install-deps", response_model=TaskStatusResponse)
async def install_dependencies(data: InstallDepsRequest):
    _verify_account(data.account_alias)
    try:
        task = vite_deploy_service.install_deps(
            account_alias=data.account_alias,
            project_path=data.project_path,
            force=data.force,
        )
        return TaskStatusResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动依赖安装失败: {e}")


@router.post("/build", response_model=TaskStatusResponse)
async def build_project(data: BuildRequest):
    _verify_account(data.account_alias)
    try:
        task = vite_deploy_service.build(
            account_alias=data.account_alias,
            project_path=data.project_path,
            build_command=data.build_command,
        )
        return TaskStatusResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动构建失败: {e}")


@router.post("/nginx", response_model=TaskStatusResponse)
async def deploy_ginx(data: NginxRequest):
    _verify_account(data.account_alias)
    try:
        task = vite_deploy_service.deploy_nginx(
            account_alias=data.account_alias,
            project_alias=data.project_alias,
            project_path=data.project_path,
            port=data.port,
        )
        return TaskStatusResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动 Nginx 部署失败: {e}")


@deploy_router.post("/deploy", response_model=TaskStatusResponse)
async def full_deploy(data: DeployRequest):
    _verify_account(data.account_alias)
    try:
        task = vite_deploy_service.full_deploy(
            account_alias=data.account_alias,
            project_alias=data.project_alias,
            project_path=data.project_path,
            config={
                "node_version": data.node_version,
                "nginx_port": data.nginx_port,
                "build_command": data.build_command,
                "force": data.force,
            },
        )
        return TaskStatusResponse(**task.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动一键部署失败: {e}")


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="部署任务 ID"),
):
    task_dict = vite_deploy_service.get_task_dict(task_id)
    if task_dict is None:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")
    return TaskStatusResponse(**task_dict)


@router.get("/history")
async def get_task_history(
    account_alias: Optional[str] = Query(default=None, description="SSH 账户别名"),
    limit: int = Query(default=20, ge=1, le=200, description="返回记录数量上限"),
):
    tasks = vite_deploy_service.list_tasks(account_alias=account_alias, limit=limit)
    return {"tasks": [TaskStatusResponse(**t) for t in tasks]}


@router.websocket("/ws/logs/{task_id}")
async def vite_deploy_logs_ws(
    websocket: WebSocket,
    task_id: str = Path(..., description="部署任务 ID"),
):
    await websocket.accept()

    task = vite_deploy_service.get_task(task_id)
    if task is None:
        await websocket.send_json({
            "type": "error",
            "message": f"任务 '{task_id}' 不存在",
        })
        await websocket.close()
        return

    await websocket.send_json({
        "type": "task_info",
        "data": task.to_dict(),
    })

    stopped = False

    def _push_update(t: object) -> None:
        nonlocal stopped
        if stopped:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({
                    "type": "log_update",
                    "data": t.to_dict(),
                }),
                asyncio.get_event_loop(),
            )
        except Exception:
            stopped = True

    task.add_callback(_push_update)

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
            elif msg_type == "get_log":
                await websocket.send_json({
                    "type": "log_update",
                    "data": task.to_dict(),
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知消息类型: {msg_type}",
                })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
