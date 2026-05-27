"""
Web VSCode API 路由
提供 code-server 的启动、停止、状态查询接口
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.vscode_service import vscode_service

router = APIRouter()


class VSCodeStartRequest(BaseModel):
    """启动 Web VSCode 请求"""
    port: Optional[int] = Field(None, description="服务端口，默认 8082")
    work_dir: Optional[str] = Field(None, description="工作目录路径")
    enable_auth: bool = Field(True, description="是否启用认证")


class VSCodeStatusResponse(BaseModel):
    """Web VSCode 状态响应"""
    running: bool = Field(..., description="服务是否运行中")
    port: int = Field(..., description="服务端口")
    pid: Optional[int] = Field(None, description="进程ID")
    url: Optional[str] = Field(None, description="访问URL")
    error: Optional[str] = Field(None, description="错误信息")


class VSCodeStartResponse(BaseModel):
    """启动 Web VSCode 响应"""
    success: bool = Field(..., description="是否启动成功")
    status: VSCodeStatusResponse = Field(..., description="服务状态")
    auth_token: Optional[str] = Field(None, description="认证令牌（仅启动时返回）")


@router.get("/vscode/status", response_model=VSCodeStatusResponse)
async def get_vscode_status():
    """
    获取 Web VSCode 服务状态
    """
    status = vscode_service.get_status()
    return VSCodeStatusResponse(
        running=status.running,
        port=status.port,
        pid=status.pid,
        url=status.url,
        error=status.error,
    )


@router.post("/vscode/start", response_model=VSCodeStartResponse)
async def start_vscode(request: Optional[VSCodeStartRequest] = None):
    """
    启动 Web VSCode 服务

    - **port**: 服务端口（可选，默认 8082）
    - **work_dir**: 工作目录路径（可选，默认当前目录）
    - **enable_auth**: 是否启用认证（可选，默认 true）
    """
    if request is None:
        request = VSCodeStartRequest()

    work_dir = Path(request.work_dir) if request.work_dir else None

    status = vscode_service.start(
        port=request.port,
        work_dir=work_dir,
        enable_auth=request.enable_auth,
    )

    return VSCodeStartResponse(
        success=status.running,
        status=VSCodeStatusResponse(
            running=status.running,
            port=status.port,
            pid=status.pid,
            url=status.url,
            error=status.error,
        ),
        auth_token=vscode_service.get_auth_token() if status.running else None,
    )


@router.post("/vscode/stop", response_model=VSCodeStatusResponse)
async def stop_vscode():
    """
    停止 Web VSCode 服务
    """
    status = vscode_service.stop()
    return VSCodeStatusResponse(
        running=status.running,
        port=status.port,
        pid=status.pid,
        url=status.url,
        error=status.error,
    )


@router.post("/vscode/restart", response_model=VSCodeStartResponse)
async def restart_vscode(request: Optional[VSCodeStartRequest] = None):
    """
    重启 Web VSCode 服务

    - **port**: 服务端口（可选）
    - **work_dir**: 工作目录路径（可选）
    """
    if request is None:
        request = VSCodeStartRequest()

    work_dir = Path(request.work_dir) if request.work_dir else None

    status = vscode_service.restart(
        port=request.port,
        work_dir=work_dir,
    )

    return VSCodeStartResponse(
        success=status.running,
        status=VSCodeStatusResponse(
            running=status.running,
            port=status.port,
            pid=status.pid,
            url=status.url,
            error=status.error,
        ),
        auth_token=vscode_service.get_auth_token() if status.running else None,
    )


@router.get("/vscode/proxy-url")
async def get_vscode_proxy_url():
    """
    获取 Web VSCode 代理 URL
    用于前端通过代理访问 code-server
    """
    status = vscode_service.get_status()
    if not status.running:
        raise HTTPException(status_code=503, detail="Web VSCode is not running")

    return {
        "url": f"/api/vscode/proxy",
        "port": status.port,
    }
