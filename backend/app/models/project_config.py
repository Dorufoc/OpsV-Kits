from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    alias: str = Field(..., description="项目别名")
    local_path: str = Field(default="", description="本地项目路径")
    remote_path: str = Field(default="", description="远程项目路径")
    ssh_alias: str = Field(default="", description="SSH 账户别名")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProjectConfigCreate(BaseModel):
    alias: str = Field(..., description="项目别名")
    local_path: str = Field(default="", description="本地项目路径")
    remote_path: str = Field(default="", description="远程项目路径")
    ssh_alias: str = Field(default="", description="SSH 账户别名")


class ProjectConfigUpdate(BaseModel):
    local_path: Optional[str] = Field(default=None, description="本地项目路径")
    remote_path: Optional[str] = Field(default=None, description="远程项目路径")
    ssh_alias: Optional[str] = Field(default=None, description="SSH 账户别名")
