from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SSHAccount(BaseModel):
    alias: str = Field(..., description="账户别名")
    host: str = Field(..., description="主机地址")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(..., description="登录用户名")
    auth_type: str = Field(
        default="password", description="认证类型: password/key/agent"
    )
    password: Optional[str] = Field(default=None, description="密码（加密存储）")
    private_key: Optional[str] = Field(default=None, description="私钥文件路径")
    key_passphrase: Optional[str] = Field(default=None, description="密钥密码（加密存储）")
    totp_secret: Optional[str] = Field(default=None, description="TOTP 密钥（加密存储）")
    is_default: bool = Field(default=False, description="是否默认账户")
    group: Optional[str] = Field(default=None, description="所属分组")
    workplace_path: str = Field(default="~/projects", description="远程工作目录")


class SSHAccountCreate(BaseModel):
    alias: str = Field(..., description="账户别名")
    host: str = Field(..., description="主机地址")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(..., description="登录用户名")
    auth_type: str = Field(
        default="password", description="认证类型: password/key/agent"
    )
    password: Optional[str] = Field(default=None, description="密码（明文传入，加密存储）")
    private_key: Optional[str] = Field(default=None, description="私钥文件路径")
    key_passphrase: Optional[str] = Field(default=None, description="密钥密码（明文传入，加密存储）")
    totp_secret: Optional[str] = Field(default=None, description="TOTP 密钥")
    is_default: bool = Field(default=False, description="是否默认账户")
    group: Optional[str] = Field(default=None, description="所属分组")
    workplace_path: str = Field(default="~/projects", description="远程工作目录")


class SSHAccountUpdate(BaseModel):
    host: Optional[str] = Field(default=None, description="主机地址")
    port: Optional[int] = Field(default=None, description="SSH 端口")
    username: Optional[str] = Field(default=None, description="登录用户名")
    auth_type: Optional[str] = Field(
        default=None, description="认证类型: password/key/agent"
    )
    password: Optional[str] = Field(default=None, description="密码（明文传入，加密存储）")
    private_key: Optional[str] = Field(default=None, description="私钥文件路径")
    key_passphrase: Optional[str] = Field(default=None, description="密钥密码（明文传入，加密存储）")
    totp_secret: Optional[str] = Field(default=None, description="TOTP 密钥")
    is_default: Optional[bool] = Field(default=None, description="是否默认账户")
    group: Optional[str] = Field(default=None, description="所属分组")
    workplace_path: Optional[str] = Field(default=None, description="远程工作目录")


class AccountGroup(BaseModel):
    name: str = Field(..., description="分组名称")
    accounts: list[str] = Field(default_factory=list, description="分组内账户别名列表")


class AccountGroupCreate(BaseModel):
    name: str = Field(..., description="分组名称")
    accounts: list[str] = Field(default_factory=list, description="分组内账户别名列表")


class AccountGroupUpdate(BaseModel):
    new_name: Optional[str] = Field(default=None, description="新分组名称（重命名）")
    accounts: Optional[list[str]] = Field(default=None, description="分组内账户别名列表")
