from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.services.sync_service import sync_service

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncStartRequest(BaseModel):
    local_path: str = Field(..., description="本地同步目录路径")
    remote_path: str = Field(..., description="远程同步目录路径")
    account_alias: str = Field(..., description="SSH 账户别名")
    force: bool = Field(default=False, description="是否强制全量同步")


class SyncStartResponse(BaseModel):
    sync_id: str = Field(..., description="同步任务 ID")
    message: str = Field(default="同步任务已启动", description="提示信息")


class SyncStopRequest(BaseModel):
    sync_id: str = Field(..., description="要停止的同步任务 ID")


class SyncStopResponse(BaseModel):
    success: bool = Field(..., description="是否成功停止")
    message: str = Field(..., description="提示信息")


@router.post("/start", response_model=SyncStartResponse)
async def start_sync(data: SyncStartRequest):
    try:
        sync_id = await sync_service.start_sync(
            local_path=data.local_path,
            remote_path=data.remote_path,
            account_alias=data.account_alias,
            force=data.force,
        )
        return SyncStartResponse(sync_id=sync_id, message="同步任务已启动")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动同步失败: {e}")


@router.post("/stop", response_model=SyncStopResponse)
async def stop_sync(data: SyncStopRequest):
    success = sync_service.stop_sync(data.sync_id)
    if success:
        return SyncStopResponse(success=True, message="同步已停止")
    return SyncStopResponse(success=False, message="任务不存在或已完成")


@router.get("/status/{sync_id}")
async def get_sync_status_path(
    sync_id: str,
):
    result = sync_service.get_status(sync_id)
    if result is None:
        raise HTTPException(status_code=404, detail="同步任务不存在")
    return result


@router.get("/status")
async def get_sync_status(
    sync_id: Optional[str] = Query(None, description="同步任务 ID"),
):
    result = sync_service.get_status(sync_id)
    if result is None:
        raise HTTPException(status_code=404, detail="同步任务不存在")
    return result


@router.websocket("/ws/status")
async def sync_status_ws(websocket: WebSocket):
    await websocket.accept()
    sync_id: Optional[str] = None
    try:
        data = await websocket.receive_json()
        sync_id = data.get("sync_id")
        if not sync_id:
            await websocket.send_json({
                "type": "error",
                "message": "缺少 sync_id 参数",
            })
            await websocket.close(code=1008)
            return

        await sync_service.register_ws(sync_id, websocket)

        status = sync_service.get_status(sync_id)
        if status:
            await websocket.send_json({
                "type": "connected",
                "sync_id": sync_id,
                "status": status,
            })

        while True:
            try:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if sync_id:
            await sync_service.unregister_ws(sync_id, websocket)
