from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.port_service import port_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/port", tags=["port"])


class KillPortRequest(BaseModel):
    port: int = Field(..., ge=1, le=65535, description="端口号")
    force: bool = Field(default=False, description="是否强制终止")


class KillPidRequest(BaseModel):
    pid: int = Field(..., gt=0, description="进程 ID")
    force: bool = Field(default=False, description="是否强制终止")


@router.get("/list")
async def get_port_list():
    """获取本机所有端口占用列表。"""
    try:
        ports = port_service.get_port_list()
        return {
            "ports": ports,
            "count": len(ports),
        }
    except Exception as e:
        logger.error(f"[port-route] list failed: {e}")
        raise HTTPException(500, f"获取端口列表失败: {e}")


@router.get("/check")
async def check_port(port: int = Query(..., ge=1, le=65535, description="端口号")):
    """检测指定端口是否被占用。"""
    try:
        result = port_service.check_port(port)
        return result
    except Exception as e:
        logger.error(f"[port-route] check port {port} failed: {e}")
        raise HTTPException(500, f"检测端口失败: {e}")


@router.post("/kill-by-port")
async def kill_by_port(req: KillPortRequest):
    """终止占用指定端口的进程。"""
    try:
        result = port_service.kill_by_port(req.port, req.force)
        if not result["success"]:
            raise HTTPException(400, result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[port-route] kill port {req.port} failed: {e}")
        raise HTTPException(500, f"终止进程失败: {e}")


@router.post("/kill-by-pid")
async def kill_by_pid(req: KillPidRequest):
    """通过 PID 终止进程。"""
    try:
        result = port_service.kill_by_pid(req.pid, req.force)
        if not result["success"]:
            raise HTTPException(400, result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[port-route] kill pid {req.pid} failed: {e}")
        raise HTTPException(500, f"终止进程失败: {e}")
