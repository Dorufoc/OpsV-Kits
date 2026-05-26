from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间戳")
    account_alias: str = Field(..., description="账户别名")
    action: str = Field(..., description="操作类型")
    status: str = Field(..., description="状态: success/failure")
    detail: Optional[str] = Field(default=None, description="详情描述")
