from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    connecting = "connecting"
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class WebSSHSession(BaseModel):
    session_id: str = Field(..., description="会话唯一标识")
    account_alias: Optional[str] = Field(default=None, description="关联的SSH账户别名")
    host: str = Field(..., description="主机地址")
    port: int = Field(default=22, description="SSH端口")
    username: str = Field(..., description="登录用户名")
    status: SessionStatus = Field(default=SessionStatus.connecting, description="会话状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_active: datetime = Field(default_factory=datetime.now, description="最后活跃时间")
    group: Optional[str] = Field(default=None, description="所属分组")


class WebSSHConnectRequest(BaseModel):
    account_alias: Optional[str] = Field(default=None, description="SSH账户别名")
    host: Optional[str] = Field(default=None, description="主机地址")
    port: int = Field(default=22, description="SSH端口")
    username: Optional[str] = Field(default=None, description="登录用户名")
    auth_type: str = Field(default="password", description="认证类型: password/key/agent")
    password: Optional[str] = Field(default=None, description="密码")
    private_key: Optional[str] = Field(default=None, description="私钥文件路径")
    key_passphrase: Optional[str] = Field(default=None, description="密钥密码")
    totp_secret: Optional[str] = Field(default=None, description="TOTP密钥")
    group: Optional[str] = Field(default=None, description="会话分组")


class WebSSHResizeRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    width: int = Field(..., ge=10, le=500, description="终端列数")
    height: int = Field(..., ge=5, le=200, description="终端行数")


class WebSSHCommandRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
    command: str = Field(..., description="要发送的命令")


class WebSSHDisconnectRequest(BaseModel):
    session_id: str = Field(..., description="会话ID")
