from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.settings_service import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    session_ttl_hours: int = Field(default=72, ge=1, le=720, description="会话历史保留时间（小时）")


@router.get("")
async def get_settings():
    return settings_service.get_all()


@router.put("")
async def update_settings(data: SettingsUpdate):
    settings_service.update(data.model_dump(exclude_unset=True))
    return settings_service.get_all()
