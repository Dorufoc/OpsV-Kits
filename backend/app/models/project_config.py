from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    alias: str = Field(..., description="项目别名")
    local_path: str = Field(default="", description="本地项目路径")
    remote_path: str = Field(default="", description="远程项目路径")
    ssh_alias: str = Field(default="", description="SSH 账户别名")
    project_type: str = Field(default="java", description="项目类型，java / vite")
    jdk_version: Optional[str] = Field(default="21", description="JDK 版本号，如 8/11/17/21")
    node_version: Optional[str] = Field(default="20", description="Node.js 版本号")
    nginx_port: Optional[int] = Field(default=8080, description="Nginx 监听端口")
    build_command: Optional[str] = Field(default="npm run build", description="构建命令")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProjectConfigCreate(BaseModel):
    alias: str = Field(..., description="项目别名")
    local_path: str = Field(default="", description="本地项目路径")
    remote_path: str = Field(default="", description="远程项目路径")
    ssh_alias: str = Field(default="", description="SSH 账户别名")
    project_type: str = Field(default="java", description="项目类型，java / vite")
    jdk_version: Optional[str] = Field(default="21", description="JDK 版本号，如 8/11/17/21")
    node_version: Optional[str] = Field(default="20", description="Node.js 版本号")
    nginx_port: Optional[int] = Field(default=8080, description="Nginx 监听端口")
    build_command: Optional[str] = Field(default="npm run build", description="构建命令")


class ProjectConfigUpdate(BaseModel):
    local_path: Optional[str] = Field(default=None, description="本地项目路径")
    remote_path: Optional[str] = Field(default=None, description="远程项目路径")
    ssh_alias: Optional[str] = Field(default=None, description="SSH 账户别名")
    project_type: Optional[str] = Field(default=None, description="项目类型，java / vite")
    jdk_version: Optional[str] = Field(default=None, description="JDK 版本号，如 8/11/17/21")
    node_version: Optional[str] = Field(default=None, description="Node.js 版本号")
    nginx_port: Optional[int] = Field(default=None, description="Nginx 监听端口")
    build_command: Optional[str] = Field(default=None, description="构建命令")
