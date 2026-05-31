from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXECUTE = "execute"
    EXPORT = "export"
    IMPORT = "import"
    CONFIG = "config"


class AuditModule(str, Enum):
    SSH = "ssh"
    DOCKER = "docker"
    MONITOR = "monitor"
    PROCESS = "process"
    SECURITY = "security"
    SETTINGS = "settings"
    PROJECT = "project"
    BUILD = "build"
    CRON_BACKUP = "cron-backup"
    FILE_MANAGER = "file-manager"
    DB_TOOLKIT = "db-toolkit"
    WEBSSH = "webssh"
    REMOTE_DRIVE = "remote-drive"
    VITE_DEPLOY = "vite-deploy"
    AUDIT = "audit"


class AuditLog(BaseModel):
    id: str = Field(..., description="唯一标识 UUID")
    user_id: str = Field(default="anonymous", description="操作用户ID")
    username: str = Field(default="anonymous", description="操作用户名")
    timestamp: datetime = Field(default_factory=datetime.now, description="操作时间戳(精确到毫秒)")
    ip_address: str = Field(default="", description="操作来源IP地址")
    action_type: ActionType = Field(..., description="操作类型")
    module: AuditModule = Field(..., description="操作模块")
    detail: Optional[Dict[str, Any]] = Field(default=None, description="操作内容详情(JSON)")
    status: str = Field(default="success", description="操作结果状态: success/failure")
    client_info: str = Field(default="", description="客户端设备信息(User-Agent)")
    request_path: str = Field(default="", description="请求路径")
    request_method: str = Field(default="", description="请求方法")
    response_code: int = Field(default=200, description="HTTP响应状态码")
    duration_ms: float = Field(default=0.0, description="请求处理耗时(毫秒)")
    hash: str = Field(default="", description="数据完整性校验哈希(SHA-256)")
    sensitive: bool = Field(default=False, description="是否为敏感操作")


class AuditLogQuery(BaseModel):
    user_id: Optional[str] = Field(default=None, description="用户ID(模糊匹配)")
    username: Optional[str] = Field(default=None, description="用户名(模糊匹配)")
    time_start: Optional[datetime] = Field(default=None, description="起始时间")
    time_end: Optional[datetime] = Field(default=None, description="结束时间")
    action_types: Optional[List[ActionType]] = Field(default=None, description="操作类型(多选)")
    modules: Optional[List[AuditModule]] = Field(default=None, description="操作模块(多选)")
    status: Optional[str] = Field(default=None, description="操作结果状态")
    request_path: Optional[str] = Field(default=None, description="请求路径(模糊匹配)")
    keyword: Optional[str] = Field(default=None, description="关键词搜索(detail全文检索)")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")
    order_by: str = Field(default="timestamp", description="排序字段")
    order_dir: str = Field(default="desc", description="排序方向: asc/desc")


class AuditLogPageResult(BaseModel):
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页条数")
    total_pages: int = Field(default=0, description="总页数")
    items: List[AuditLog] = Field(default_factory=list, description="日志记录列表")


class AuditLogExportRequest(BaseModel):
    query: AuditLogQuery = Field(..., description="查询条件")
    format: str = Field(default="xlsx", description="导出格式: xlsx/csv/pdf")


class AuditLogStatistics(BaseModel):
    trend: List[Dict[str, Any]] = Field(default_factory=list, description="操作趋势数据")
    module_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="模块分布数据")
    action_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="操作类型分布数据")
    user_ranking: List[Dict[str, Any]] = Field(default_factory=list, description="用户操作排行")
    anomalies: List[Dict[str, Any]] = Field(default_factory=list, description="异常操作列表")


class AuditLogVerifyResult(BaseModel):
    total: int = Field(default=0, description="校验总数")
    passed: int = Field(default=0, description="通过数")
    failed: int = Field(default=0, description="未通过数")
    failed_ids: List[str] = Field(default_factory=list, description="未通过的记录ID列表")


class AuditArchiveInfo(BaseModel):
    filename: str = Field(..., description="归档文件名")
    size_bytes: int = Field(default=0, description="文件大小(字节)")
    record_count: int = Field(default=0, description="记录数")
    period_start: str = Field(default="", description="归档起始时间")
    period_end: str = Field(default="", description="归档结束时间")
