from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.process_service import SIGNAL_MAP, process_service
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["process"])


async def _ensure_account(alias: str) -> None:
    """校验 SSH 账户是否存在。"""
    if not ssh_account_service.get_account(alias):
        raise HTTPException(404, f"SSH 账户 '{alias}' 不存在")


# ── Pydantic 请求模型 ────────────────────────────────────────────

class KillRequest(BaseModel):
    alias: str
    pid: int = Field(..., gt=0, description="进程 ID")
    signal: str = Field(default="SIGTERM", description="信号名称")


class NiceRequest(BaseModel):
    alias: str
    pid: int = Field(..., gt=0, description="进程 ID")
    nice_value: int = Field(..., ge=-20, le=19, description="Nice 值 (-20 ~ 19)")


class BatchKillRequest(BaseModel):
    alias: str
    pids: list[int] = Field(..., min_length=1, description="进程 ID 列表")
    signal: str = Field(default="SIGTERM", description="信号名称")


class ServiceControlRequest(BaseModel):
    alias: str
    service_name: str = Field(..., min_length=1, description="服务名称")
    action: str = Field(..., description="操作: start/stop/restart/reload/status")


class AlertConfigRequest(BaseModel):
    alias: str
    cpu_threshold: float = Field(default=90.0, ge=0, le=100, description="CPU 阈值")
    mem_threshold: float = Field(default=80.0, ge=0, le=100, description="内存阈值")
    duration_seconds: int = Field(default=5, ge=1, description="持续时间阈值(秒)")


# ── HTTP 路由 ────────────────────────────────────────────────────

@router.get("/list")
async def get_process_list(alias: str = Query(..., description="SSH 账户别名")):
    """获取所有进程列表。"""
    try:
        await _ensure_account(alias)
        processes = process_service.get_all_processes(alias)
        return {
            "processes": processes,
            "count": len(processes),
            "timestamp": time.time(),
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取进程列表失败: {e}")


@router.get("/detail")
async def get_process_detail(
    alias: str = Query(..., description="SSH 账户别名"),
    pid: int = Query(..., gt=0, description="进程 ID"),
):
    """获取单个进程的详细信息。"""
    try:
        await _ensure_account(alias)
        detail = await process_service.get_process_detail(pid, alias)
        if "error" in detail:
            raise HTTPException(404, detail["error"])
        return detail
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"获取进程详情失败: {e}")


@router.post("/kill")
async def kill_process(req: KillRequest):
    """终止进程。"""
    try:
        await _ensure_account(req.alias)
        signal = req.signal.upper()
        if signal not in SIGNAL_MAP:
            raise HTTPException(400, f"不支持的信号: {signal}，支持的信号: {', '.join(SIGNAL_MAP.keys())}")
        result = process_service.kill_process(req.pid, signal, req.alias)
        if not result["success"]:
            raise HTTPException(500, result["message"])
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"终止进程失败: {e}")


@router.post("/nice")
async def set_nice(req: NiceRequest):
    """调整进程优先级。"""
    try:
        await _ensure_account(req.alias)
        result = process_service.set_nice(req.pid, req.nice_value, req.alias)
        if not result["success"]:
            raise HTTPException(500, result["message"])
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"调整优先级失败: {e}")


@router.post("/batch/kill")
async def batch_kill(req: BatchKillRequest):
    """批量终止进程。"""
    try:
        await _ensure_account(req.alias)
        signal = req.signal.upper()
        if signal not in SIGNAL_MAP:
            raise HTTPException(400, f"不支持的信号: {signal}")
        results = process_service.batch_kill(req.pids, signal, req.alias)
        return {"results": results}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"批量终止失败: {e}")


@router.post("/service/control")
async def service_control(req: ServiceControlRequest):
    """控制 systemd 服务。"""
    try:
        await _ensure_account(req.alias)
        result = process_service.service_control(req.service_name, req.action, req.alias)
        if not result["success"]:
            raise HTTPException(500, result["message"])
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"服务控制失败: {e}")


@router.get("/alerts")
async def get_alerts(alias: str = Query(..., description="SSH 账户别名")):
    """获取当前异常进程检测结果。"""
    try:
        await _ensure_account(alias)
        thresholds = process_service.get_alert_config(alias)
        anomalies = process_service.detect_anomalies(alias, thresholds)
        return anomalies
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"异常检测失败: {e}")


@router.get("/alert-config")
async def get_alert_config(alias: str = Query(..., description="SSH 账户别名")):
    """获取告警阈值配置。"""
    try:
        await _ensure_account(alias)
        config = process_service.get_alert_config(alias)
        return config
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取告警配置失败: {e}")


@router.put("/alert-config")
async def save_alert_config(req: AlertConfigRequest):
    """保存告警阈值配置。"""
    try:
        await _ensure_account(req.alias)
        config = {
            "cpu_threshold": req.cpu_threshold,
            "mem_threshold": req.mem_threshold,
            "duration_seconds": req.duration_seconds,
        }
        success = process_service.save_alert_config(req.alias, config)
        if not success:
            raise HTTPException(500, "保存告警配置失败")
        return {"success": True}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"保存告警配置失败: {e}")


# ── WebSocket 流式推送 ──────────────────────────────────────────

@router.websocket("/ws/stream")
async def process_stream_websocket(websocket: WebSocket, alias: str = Query(...)):
    """实时进程流推送。

    客户端连接后，服务端定期推送进程列表。
    支持 ping/pong 心跳消息。
    """
    await websocket.accept()
    process_service.subscribe(alias, websocket)
    await process_service.start_streaming(alias, interval=3.0)
    logger.info(f"[process-ws] connected: alias={alias}")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info(f"[process-ws] disconnected: alias={alias}")
    except Exception as e:
        logger.error(f"[process-ws] error: {e}")
    finally:
        process_service.unsubscribe(alias, websocket)
        await process_service.stop_streaming(alias)
