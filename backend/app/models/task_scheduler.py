from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class RetryStrategy(str, Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class AlertChannel(str, Enum):
    WEBHOOK = "webhook"
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECOM = "wecom"


class TriggerMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class RetryPolicy(BaseModel):
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    strategy: RetryStrategy = Field(default=RetryStrategy.FIXED, description="重试策略")
    interval_seconds: int = Field(default=60, ge=1, description="重试间隔（秒）")
    max_interval_seconds: Optional[int] = Field(default=None, description="指数退避最大间隔（秒）")


class AlertConfig(BaseModel):
    channel: AlertChannel = Field(..., description="告警渠道")
    recipients: list[str] = Field(..., description="告警接收人列表")
    template: Optional[str] = Field(default=None, description="告警模板")
    enabled: bool = Field(default=True, description="是否启用")


class ScheduledTask(BaseModel):
    id: str = Field(..., description="任务唯一标识")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(default=None, description="任务描述")
    workflow_id: Optional[str] = Field(default=None, description="关联工作流 ID")
    task_type: str = Field(default="shell", description="任务类型: shell/http")
    command: Optional[str] = Field(default=None, description="执行命令或 URL")
    cron_expression: str = Field(..., description="Cron 表达式")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任务优先级")
    max_concurrent: int = Field(default=1, ge=1, description="最大并发数")
    timeout_seconds: int = Field(default=3600, ge=1, description="超时时间（秒）")
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="重试策略")
    alert_configs: list[AlertConfig] = Field(default_factory=list, description="告警配置列表")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="任务状态")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")
    last_run_at: Optional[datetime] = Field(default=None, description="最后执行时间")
    last_run_status: Optional[ExecutionStatus] = Field(default=None, description="最后执行状态")
    next_run_at: Optional[datetime] = Field(default=None, description="下次执行时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class TaskExecution(BaseModel):
    id: str = Field(..., description="执行记录唯一标识")
    task_id: str = Field(..., description="关联任务 ID")
    task_name: str = Field(..., description="任务名称")
    status: ExecutionStatus = Field(..., description="执行状态")
    trigger_mode: TriggerMode = Field(..., description="触发模式")
    retry_count: int = Field(default=0, description="已重试次数")
    exit_code: Optional[int] = Field(default=None, description="退出码")
    output: Optional[str] = Field(default=None, description="标准输出")
    error: Optional[str] = Field(default=None, description="错误输出")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    duration_seconds: Optional[float] = Field(default=None, description="执行耗时（秒）")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")


class RetryPolicyCreate(BaseModel):
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    strategy: RetryStrategy = Field(default=RetryStrategy.FIXED, description="重试策略")
    interval_seconds: int = Field(default=60, ge=1, description="重试间隔（秒）")
    max_interval_seconds: Optional[int] = Field(default=None, description="指数退避最大间隔（秒）")


class AlertConfigCreate(BaseModel):
    channel: AlertChannel = Field(..., description="告警渠道")
    recipients: list[str] = Field(..., description="告警接收人列表")
    template: Optional[str] = Field(default=None, description="告警模板")
    enabled: bool = Field(default=True, description="是否启用")


class ScheduledTaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    description: Optional[str] = Field(default=None, description="任务描述")
    workflow_id: Optional[str] = Field(default=None, description="关联工作流 ID")
    task_type: str = Field(default="shell", description="任务类型: shell/http")
    command: Optional[str] = Field(default=None, description="执行命令或 URL")
    cron_expression: str = Field(..., min_length=1, description="Cron 表达式")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="任务优先级")
    max_concurrent: int = Field(default=1, ge=1, description="最大并发数")
    timeout_seconds: int = Field(default=3600, ge=1, description="超时时间（秒）")
    retry_policy: RetryPolicyCreate = Field(default_factory=RetryPolicyCreate, description="重试策略")
    alert_configs: list[AlertConfigCreate] = Field(default_factory=list, description="告警配置列表")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="任务状态")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")


class ScheduledTaskUpdate(BaseModel):
    id: str = Field(..., description="任务唯一标识")
    name: Optional[str] = Field(default=None, max_length=100, description="任务名称")
    description: Optional[str] = Field(default=None, description="任务描述")
    workflow_id: Optional[str] = Field(default=None, description="关联工作流 ID")
    task_type: Optional[str] = Field(default=None, description="任务类型")
    command: Optional[str] = Field(default=None, description="执行命令或 URL")
    cron_expression: Optional[str] = Field(default=None, description="Cron 表达式")
    timezone: Optional[str] = Field(default=None, description="时区")
    priority: Optional[TaskPriority] = Field(default=None, description="任务优先级")
    max_concurrent: Optional[int] = Field(default=None, ge=1, description="最大并发数")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="超时时间（秒）")
    retry_policy: Optional[RetryPolicyCreate] = Field(default=None, description="重试策略")
    alert_configs: Optional[list[AlertConfigCreate]] = Field(default=None, description="告警配置列表")
    status: Optional[TaskStatus] = Field(default=None, description="任务状态")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")
