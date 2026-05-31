from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.log_storage_service import log_storage_service
from app.services.log_alert_service import log_alert_service
from app.services.log_collector_service import log_collector_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/log-analysis", tags=["log-analysis"])


class LogSearchRequest(BaseModel):
    query: str
    filters: Optional[dict] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class LogFilterRequest(BaseModel):
    filters: dict
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class SourceCreateRequest(BaseModel):
    type: str
    alias: str
    path: Optional[str] = None
    container: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    enabled: bool = True
    labels: Optional[dict] = None


class SourceUpdateRequest(BaseModel):
    type: Optional[str] = None
    alias: Optional[str] = None
    path: Optional[str] = None
    container: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    enabled: Optional[bool] = None
    labels: Optional[dict] = None


class AlertRuleCreateRequest(BaseModel):
    name: str
    pattern: str
    pattern_type: str = "keyword"
    time_window: int = 300
    threshold: int = 1
    enabled: bool = True
    silence_period: int = 3600


class AlertRuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    pattern: Optional[str] = None
    pattern_type: Optional[str] = None
    time_window: Optional[int] = None
    threshold: Optional[int] = None
    enabled: Optional[bool] = None
    silence_period: Optional[int] = None


class AlertRuleToggleRequest(BaseModel):
    enabled: bool


@router.post("/search")
async def search_logs(req: LogSearchRequest):
    try:
        return await log_storage_service.search(
            query=req.query,
            filters=req.filters or {},
            page=req.page,
            page_size=req.page_size,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"日志搜索失败: {e}")


@router.post("/filter")
async def filter_logs(req: LogFilterRequest):
    try:
        return await log_storage_service.filter_logs(
            filters=req.filters,
            page=req.page,
            page_size=req.page_size,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"日志过滤失败: {e}")


@router.get("/aggregation")
async def get_aggregation(
    type: str = Query(..., description="聚合类型: trend|source_distribution|level_distribution|keyword_frequency"),
    time_start: float = Query(..., description="起始时间戳"),
    time_end: float = Query(..., description="结束时间戳"),
    granularity: str = Query("hour", description="粒度: minute|hour|day"),
    level: Optional[str] = Query(None, description="日志级别过滤"),
    keyword: Optional[str] = Query(None, description="关键词（keyword_frequency 时必填）"),
    top_n: int = Query(10, ge=1, le=100, description="Top N 数量"),
):
    try:
        if type == "trend":
            data = await log_storage_service.get_trend(
                time_start=time_start,
                time_end=time_end,
                granularity=granularity,
                level=level,
            )
        elif type == "source_distribution":
            data = await log_storage_service.get_source_distribution(
                time_start=time_start,
                time_end=time_end,
                top_n=top_n,
            )
        elif type == "level_distribution":
            data = await log_storage_service.get_level_distribution(
                time_start=time_start,
                time_end=time_end,
            )
        elif type == "keyword_frequency":
            if not keyword:
                raise HTTPException(400, "keyword_frequency 类型必须提供 keyword 参数")
            data = await log_storage_service.get_keyword_frequency(
                keyword=keyword,
                time_start=time_start,
                time_end=time_end,
                granularity=granularity,
            )
        else:
            raise HTTPException(400, f"不支持的聚合类型: {type}")
        return {"data": data}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"日志聚合统计失败: {e}")


@router.get("/sources")
async def get_sources():
    try:
        sources = log_collector_service.get_sources()
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(500, f"获取采集源失败: {e}")


@router.post("/sources")
async def add_source(req: SourceCreateRequest):
    try:
        source_id = log_collector_service.add_source(req.model_dump())
        return {"id": source_id}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"添加采集源失败: {e}")


@router.put("/sources/{source_id}")
async def update_source(source_id: str, req: SourceUpdateRequest):
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(400, "未提供任何更新字段")
        log_collector_service.update_source(source_id, updates)
        return {"message": "更新成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新采集源失败: {e}")


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    try:
        await log_collector_service.delete_source(source_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除采集源失败: {e}")


@router.post("/sources/{source_id}/start")
async def start_source(source_id: str):
    try:
        await log_collector_service.start_source(source_id)
        return {"message": "采集源已启动"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"启动采集源失败: {e}")


@router.post("/sources/{source_id}/stop")
async def stop_source(source_id: str):
    try:
        await log_collector_service.stop_source(source_id)
        return {"message": "采集源已停止"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"停止采集源失败: {e}")


@router.get("/alerts/rules")
async def get_alert_rules():
    try:
        rules = await log_alert_service.get_rules()
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(500, f"获取告警规则失败: {e}")


@router.post("/alerts/rules")
async def create_alert_rule(req: AlertRuleCreateRequest):
    try:
        rule_id = await log_alert_service.create_rule(req.model_dump())
        return {"id": rule_id}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建告警规则失败: {e}")


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: int, req: AlertRuleUpdateRequest):
    try:
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(400, "未提供任何更新字段")
        await log_alert_service.update_rule(rule_id, updates)
        return {"message": "更新成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新告警规则失败: {e}")


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: int):
    try:
        await log_alert_service.delete_rule(rule_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除告警规则失败: {e}")


@router.post("/alerts/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: int, req: AlertRuleToggleRequest):
    try:
        await log_alert_service.toggle_rule(rule_id, req.enabled)
        return {"message": "操作成功"}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"切换告警规则状态失败: {e}")


@router.get("/alerts/events")
async def get_alert_events(
    rule_id: Optional[int] = Query(None, description="规则 ID"),
    hours: int = Query(24, ge=1, description="回溯小时数"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
):
    try:
        if rule_id is not None:
            events = await log_alert_service.get_events(rule_id=rule_id, limit=limit)
        else:
            events = await log_alert_service.get_recent_events(hours=hours, limit=limit)
        return {"events": events}
    except Exception as e:
        raise HTTPException(500, f"获取告警事件失败: {e}")


@router.websocket("/ws/stream")
async def log_stream_websocket(websocket: WebSocket):
    await websocket.accept()
    log_collector_service.subscribe(websocket)
    logger.info("[log-analysis-ws] connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "filter":
                    filters = msg.get("filters", {})
                    log_collector_service.update_filters(websocket, filters)
                elif msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("[log-analysis-ws] disconnected")
    except Exception as e:
        logger.error(f"[log-analysis-ws] error: {e}")
    finally:
        log_collector_service.unsubscribe(websocket)


@router.get("/context")
async def get_log_context(
    log_id: int = Query(..., description="日志 ID"),
    before: int = Query(5, ge=0, le=100, description="向前获取条数"),
    after: int = Query(5, ge=0, le=100, description="向后获取条数"),
):
    try:
        result = await log_storage_service.get_context(
            log_id=log_id,
            before=before,
            after=after,
        )
        if result.get("target") is None:
            raise HTTPException(404, f"日志 {log_id} 不存在")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取日志上下文失败: {e}")
