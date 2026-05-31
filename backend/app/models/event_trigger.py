from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventSourceType(str, Enum):
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"
    SYSTEM_METRIC = "system_metric"
    DOCKER_EVENT = "docker_event"
    CUSTOM_SCRIPT = "custom_script"


class FilterOperator(str, Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    REGEX = "regex"
    NOT_EQUALS = "not_equals"


class LogicOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"


class EventStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    TRIGGERED = "triggered"
    IGNORED = "ignored"
    ERROR = "error"


class EventSourceStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class EventFilterCondition(BaseModel):
    field: str = Field(..., description="过滤字段")
    operator: FilterOperator = Field(..., description="过滤操作符")
    value: str = Field(..., description="过滤值")


class EventFilterGroup(BaseModel):
    logic: LogicOperator = Field(default=LogicOperator.AND, description="逻辑操作符")
    conditions: list[EventFilterCondition] = Field(..., description="过滤条件列表")


class EventTransform(BaseModel):
    source_field: str = Field(..., description="源字段")
    target_field: str = Field(..., description="目标字段")
    template: Optional[str] = Field(default=None, description="格式化模板")


class EventRoute(BaseModel):
    id: str = Field(..., description="路由唯一标识")
    source_id: str = Field(..., description="关联事件源 ID")
    workflow_id: str = Field(..., description="关联工作流 ID")
    filter_group: Optional[EventFilterGroup] = Field(default=None, description="过滤条件组")
    transforms: list[EventTransform] = Field(default_factory=list, description="字段转换列表")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class EventSource(BaseModel):
    id: str = Field(..., description="事件源唯一标识")
    name: str = Field(..., description="事件源名称")
    source_type: EventSourceType = Field(..., description="事件源类型")
    config: dict = Field(default_factory=dict, description="类型特定配置")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL（webhook 类型自动生成）")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook 签名密钥")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")
    status: EventSourceStatus = Field(default=EventSourceStatus.ENABLED, description="事件源状态")
    description: Optional[str] = Field(default=None, description="事件源描述")
    last_event_at: Optional[datetime] = Field(default=None, description="最后事件时间")
    event_count: int = Field(default=0, description="事件计数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class EventLog(BaseModel):
    id: str = Field(..., description="日志唯一标识")
    source_id: str = Field(..., description="关联事件源 ID")
    source_name: str = Field(..., description="事件源名称")
    event_type: str = Field(..., description="事件类型")
    raw_data: dict = Field(default_factory=dict, description="原始事件数据")
    filtered: bool = Field(default=False, description="是否经过过滤")
    matched_routes: list[str] = Field(default_factory=list, description="匹配的路由 ID 列表")
    triggered_workflows: list[str] = Field(default_factory=list, description="触发的工作流 ID 列表")
    status: EventStatus = Field(..., description="事件状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    received_at: datetime = Field(default_factory=datetime.now, description="接收时间")


class EventFilterConditionCreate(BaseModel):
    field: str = Field(..., description="过滤字段")
    operator: FilterOperator = Field(..., description="过滤操作符")
    value: str = Field(..., description="过滤值")


class EventFilterGroupCreate(BaseModel):
    logic: LogicOperator = Field(default=LogicOperator.AND, description="逻辑操作符")
    conditions: list[EventFilterConditionCreate] = Field(..., description="过滤条件列表")


class EventTransformCreate(BaseModel):
    source_field: str = Field(..., description="源字段")
    target_field: str = Field(..., description="目标字段")
    template: Optional[str] = Field(default=None, description="格式化模板")


class EventRouteCreate(BaseModel):
    source_id: str = Field(..., description="关联事件源 ID")
    workflow_id: str = Field(..., description="关联工作流 ID")
    filter_group: Optional[EventFilterGroupCreate] = Field(default=None, description="过滤条件组")
    transforms: list[EventTransformCreate] = Field(default_factory=list, description="字段转换列表")
    enabled: bool = Field(default=True, description="是否启用")


class EventRouteUpdate(BaseModel):
    workflow_id: Optional[str] = Field(default=None, description="关联工作流 ID")
    filter_group: Optional[EventFilterGroupCreate] = Field(default=None, description="过滤条件组")
    transforms: Optional[list[EventTransformCreate]] = Field(default=None, description="字段转换列表")
    enabled: Optional[bool] = Field(default=None, description="是否启用")


class EventSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="事件源名称")
    source_type: EventSourceType = Field(..., description="事件源类型")
    config: dict = Field(default_factory=dict, description="类型特定配置")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook 签名密钥")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")
    description: Optional[str] = Field(default=None, description="事件源描述")
    status: EventSourceStatus = Field(default=EventSourceStatus.ENABLED, description="事件源状态")


class EventSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="事件源名称")
    config: Optional[dict] = Field(default=None, description="类型特定配置")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook 签名密钥")
    account_alias: Optional[str] = Field(default=None, description="关联的 SSH 账户别名")
    description: Optional[str] = Field(default=None, description="事件源描述")
    status: Optional[EventSourceStatus] = Field(default=None, description="事件源状态")
