from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.task_scheduler import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
)
from app.services.task_scheduler_service import task_scheduler_service

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/tasks")
async def list_tasks():
    try:
        tasks = task_scheduler_service.list_tasks()
        return {"items": [task.model_dump(mode="json") for task in tasks]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取定时任务列表失败: {e}")


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        task = task_scheduler_service.get_task(task_id)
        return task.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取定时任务失败: {e}")


@router.post("/tasks")
async def create_task(data: ScheduledTaskCreate):
    try:
        task = task_scheduler_service.create_task(data)
        return task.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"创建定时任务失败: {e}")


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, data: ScheduledTaskUpdate):
    try:
        task = task_scheduler_service.update_task(task_id, data)
        return task.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"更新定时任务失败: {e}")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    try:
        task_scheduler_service.delete_task(task_id)
        return {"message": "定时任务已删除"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"删除定时任务失败: {e}")


@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: str, req: ToggleRequest):
    try:
        task = task_scheduler_service.toggle_task(task_id, req.enabled)
        return task.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"切换定时任务状态失败: {e}")


@router.post("/tasks/{task_id}/run")
async def run_task_now(task_id: str):
    try:
        execution = task_scheduler_service.run_task_now(task_id)
        return execution.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"手动触发定时任务失败: {e}")


@router.get("/tasks/{task_id}/executions")
async def list_task_executions(
    task_id: str,
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        executions = task_scheduler_service.list_executions(
            task_id=task_id, limit=limit, offset=offset
        )
        return {"items": [ex.model_dump(mode="json") for ex in executions]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取任务执行记录失败: {e}")


@router.get("/executions")
async def list_executions(
    task_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
):
    try:
        executions = task_scheduler_service.list_executions(
            task_id=task_id, status=status, limit=limit, offset=offset
        )
        return {"items": [ex.model_dump(mode="json") for ex in executions]}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取执行记录列表失败: {e}")


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    try:
        execution = task_scheduler_service.get_execution(execution_id)
        return execution.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取执行记录失败: {e}")


@router.post("/executions/{execution_id}/retry")
async def retry_execution(execution_id: str):
    try:
        execution = task_scheduler_service.retry_execution(execution_id)
        return execution.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"重试执行记录失败: {e}")


@router.get("/status")
async def get_scheduler_status():
    try:
        running = task_scheduler_service._scheduler.running
        job_count = len(task_scheduler_service._scheduler.get_jobs())
        return {"running": running, "job_count": job_count}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"获取调度器状态失败: {e}")
