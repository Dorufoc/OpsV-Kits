from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.settings_service import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    session_ttl_hours: int = Field(default=72, ge=1, le=720, description="会话历史保留时间（小时）")
    remote_drive_enabled: bool | None = Field(default=None, description="远程硬盘功能开关")
    remote_drive_port: int | None = Field(default=None, ge=1024, le=65535, description="远程硬盘 WebDAV 端口")


@router.get("")
async def get_settings():
    return settings_service.get_all()


@router.put("")
async def update_settings(data: SettingsUpdate):
    data_dict = data.model_dump(exclude_unset=True)
    settings_service.update(data_dict)

    if "remote_drive_enabled" in data_dict:
        from app.services.remote_drive_service import remote_drive_service
        enabled = settings_service.get("remote_drive_enabled", True)
        port = settings_service.get("remote_drive_port", 8081)
        if enabled and not remote_drive_service.is_running:
            remote_drive_service.start(port=port)
        elif not enabled and remote_drive_service.is_running:
            remote_drive_service.stop()

    return settings_service.get_all()
