from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.models.event_trigger import (
    EventRouteCreate,
    EventRouteUpdate,
    EventSourceCreate,
    EventSourceUpdate,
)
from app.services.event_bus_service import event_bus_service

router = APIRouter(prefix="/event-trigger", tags=["event-trigger"])


@router.get("/sources")
async def list_sources():
    try:
        sources = event_bus_service.list_sources()
        return {"items": [source.model_dump(mode="json") for source in sources]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取事件源列表失败: {e}")


@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    try:
        source = event_bus_service.get_source(source_id)
        if source is None:
            raise HTTPException(404, f"事件源 '{source_id}' 不存在")
        return source.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取事件源失败: {e}")


@router.post("/sources")
async def create_source(data: EventSourceCreate):
    try:
        source = event_bus_service.create_source(data)
        return source.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建事件源失败: {e}")


@router.put("/sources/{source_id}")
async def update_source(source_id: str, data: EventSourceUpdate):
    try:
        source = event_bus_service.update_source(source_id, data)
        return source.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新事件源失败: {e}")


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    try:
        event_bus_service.delete_source(source_id)
        return {"message": "事件源已删除"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除事件源失败: {e}")


@router.get("/routes")
async def list_routes(source_id: Optional[str] = Query(None)):
    try:
        routes = event_bus_service.list_routes(source_id=source_id)
        return {"items": [route.model_dump(mode="json") for route in routes]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取路由规则列表失败: {e}")


@router.post("/routes")
async def create_route(data: EventRouteCreate):
    try:
        route = event_bus_service.create_route(data)
        return route.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建路由规则失败: {e}")


@router.put("/routes/{route_id}")
async def update_route(route_id: str, data: EventRouteUpdate):
    try:
        route = event_bus_service.update_route(route_id, data)
        return route.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新路由规则失败: {e}")


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str):
    try:
        event_bus_service.delete_route(route_id)
        return {"message": "路由规则已删除"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除路由规则失败: {e}")


@router.post("/webhook/{source_id}")
async def receive_webhook(source_id: str, request: Request):
    try:
        headers = dict(request.headers)
        body = await request.body()
        event_log = await event_bus_service.receive_webhook(source_id, headers, body)
        return {"status": "received", "event_id": str(event_log.id)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"处理 Webhook 失败: {e}")


@router.get("/logs")
async def list_event_logs(
    source_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        logs = event_bus_service.list_event_logs(
            source_id=source_id,
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        return {"items": [log.model_dump(mode="json") for log in logs]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取事件日志列表失败: {e}")


@router.post("/logs/{log_id}/replay")
async def replay_event(log_id: str):
    try:
        event_log = await event_bus_service.replay_event(log_id)
        return event_log.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"重放事件失败: {e}")
