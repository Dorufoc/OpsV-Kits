from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.health_probe import (
    ProbeOverview,
    ProbeResult,
    ProbeStatistics,
    ProbeTarget,
    ProbeTargetCreate,
    ProbeTargetUpdate,
    ProbeType,
)
from app.services.health_probe_service import health_probe_service

router = APIRouter(prefix="/health-probe", tags=["health-probe"])


@router.post("/targets", response_model=ProbeTarget)
async def create_target(data: ProbeTargetCreate):
    try:
        return health_probe_service.create_target(data)
    except Exception as e:
        raise HTTPException(500, f"创建探测目标失败: {e}")


@router.get("/targets", response_model=list[ProbeTarget])
async def list_targets(
    tag: Optional[str] = Query(None, description="按标签筛选"),
    probe_type: Optional[ProbeType] = Query(None, description="按探测类型筛选"),
):
    return health_probe_service.list_targets(tag=tag, probe_type=probe_type)


@router.get("/targets/{target_id}", response_model=ProbeTarget)
async def get_target(target_id: str):
    target = health_probe_service.get_target(target_id)
    if target is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    return target


@router.put("/targets/{target_id}", response_model=ProbeTarget)
async def update_target(target_id: str, data: ProbeTargetUpdate):
    target = health_probe_service.update_target(target_id, data)
    if target is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    return target


@router.delete("/targets/{target_id}")
async def delete_target(target_id: str):
    if not health_probe_service.delete_target(target_id):
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    return {"message": "删除成功"}


@router.post("/targets/{target_id}/probe", response_model=ProbeResult)
async def probe_now(target_id: str):
    result = await health_probe_service.probe_now(target_id)
    if result is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    return result


@router.get("/targets/{target_id}/logs")
async def get_probe_logs(
    target_id: str,
    limit: int = Query(50, ge=1, le=500, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    time_start: Optional[datetime] = Query(None, description="开始时间"),
    time_end: Optional[datetime] = Query(None, description="结束时间"),
    success: Optional[bool] = Query(None, description="按成功/失败筛选"),
):
    target = health_probe_service.get_target(target_id)
    if target is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    results, total = health_probe_service.query_probe_logs(
        target_id=target_id,
        limit=limit,
        offset=offset,
        time_start=time_start,
        time_end=time_end,
        success=success,
    )
    return {"items": results, "total": total, "limit": limit, "offset": offset}


@router.get("/targets/{target_id}/statistics", response_model=ProbeStatistics)
async def get_statistics(
    target_id: str,
    hours: int = Query(24, ge=1, description="统计时间范围（小时）"),
):
    target = health_probe_service.get_target(target_id)
    if target is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 不存在")
    from datetime import timedelta
    time_start = datetime.now() - timedelta(hours=hours)
    stats = health_probe_service.calculate_statistics(target_id, time_start=time_start)
    if stats is None:
        raise HTTPException(404, f"探测目标 '{target_id}' 统计数据不存在")
    return stats


@router.get("/overview", response_model=ProbeOverview)
async def get_overview():
    return health_probe_service.get_overview()
