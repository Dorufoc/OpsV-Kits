from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    TRIGGER_CRON = "trigger_cron"
    TRIGGER_WEBHOOK = "trigger_webhook"
    TRIGGER_EVENT = "trigger_event"
    ACTION_SHELL = "action_shell"
    ACTION_HTTP = "action_http"
    ACTION_SCRIPT = "action_script"
    CONDITION = "condition"
    LOOP = "loop"
    WAIT = "wait"
    NOTIFY = "notify"
    END = "end"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TriggerType(str, Enum):
    CRON = "cron"
    WEBHOOK = "webhook"
    EVENT = "event"


class WorkflowNode(BaseModel):
    id: str = Field(..., description="节点唯一标识")
    workflow_id: str = Field(..., description="所属工作流 ID")
    node_type: NodeType = Field(..., description="节点类型")
    name: str = Field(..., description="节点名称")
    config: dict = Field(default_factory=dict, description="节点配置")
    position_x: int = Field(..., description="画布 X 坐标")
    position_y: int = Field(..., description="画布 Y 坐标")
    description: Optional[str] = Field(default=None, description="节点描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class WorkflowEdge(BaseModel):
    id: str = Field(..., description="边唯一标识")
    workflow_id: str = Field(..., description="所属工作流 ID")
    source_node_id: str = Field(..., description="源节点 ID")
    target_node_id: str = Field(..., description="目标节点 ID")
    source_port: Optional[str] = Field(default=None, description="源端口")
    target_port: Optional[str] = Field(default=None, description="目标端口")
    label: Optional[str] = Field(default=None, description="边标签")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class Workflow(BaseModel):
    id: str = Field(..., description="工作流唯一标识")
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT, description="工作流状态")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="节点列表")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="边列表")
    version: int = Field(default=1, description="版本号")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class WorkflowVersion(BaseModel):
    id: str = Field(..., description="版本唯一标识")
    workflow_id: str = Field(..., description="所属工作流 ID")
    version: int = Field(..., description="版本号")
    snapshot: dict = Field(default_factory=dict, description="工作流完整快照 JSON")
    change_note: Optional[str] = Field(default=None, description="变更说明")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class WorkflowExecution(BaseModel):
    id: str = Field(..., description="执行记录唯一标识")
    workflow_id: str = Field(..., description="关联工作流 ID")
    workflow_name: str = Field(..., description="工作流名称")
    version: int = Field(..., description="执行的工作流版本")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="执行状态")
    trigger_type: TriggerType = Field(..., description="触发类型")
    trigger_source: Optional[str] = Field(default=None, description="触发来源")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    duration_seconds: Optional[float] = Field(default=None, description="执行耗时（秒）")
    total_nodes: int = Field(default=0, description="总节点数")
    success_nodes: int = Field(default=0, description="成功节点数")
    failed_nodes: int = Field(default=0, description="失败节点数")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class NodeExecution(BaseModel):
    id: str = Field(..., description="节点执行记录唯一标识")
    execution_id: str = Field(..., description="关联工作流执行 ID")
    node_id: str = Field(..., description="节点 ID")
    node_name: str = Field(..., description="节点名称")
    node_type: NodeType = Field(..., description="节点类型")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="执行状态")
    input_data: Optional[dict] = Field(default=None, description="输入数据")
    output_data: Optional[dict] = Field(default=None, description="输出数据")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    duration_seconds: Optional[float] = Field(default=None, description="执行耗时（秒）")


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    nodes: list[dict] = Field(default_factory=list, description="节点列表")
    edges: list[dict] = Field(default_factory=list, description="边列表")


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    status: Optional[WorkflowStatus] = Field(default=None, description="工作流状态")
    nodes: Optional[list[dict]] = Field(default=None, description="节点列表")
    edges: Optional[list[dict]] = Field(default=None, description="边列表")


class WorkflowNodeCreate(BaseModel):
    node_type: NodeType = Field(..., description="节点类型")
    name: str = Field(..., min_length=1, max_length=100, description="节点名称")
    config: dict = Field(default_factory=dict, description="节点配置")
    position_x: int = Field(..., description="画布 X 坐标")
    position_y: int = Field(..., description="画布 Y 坐标")
    description: Optional[str] = Field(default=None, description="节点描述")


class WorkflowNodeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="节点名称")
    config: Optional[dict] = Field(default=None, description="节点配置")
    position_x: Optional[int] = Field(default=None, description="画布 X 坐标")
    position_y: Optional[int] = Field(default=None, description="画布 Y 坐标")
    description: Optional[str] = Field(default=None, description="节点描述")


class WorkflowEdgeCreate(BaseModel):
    source_node_id: str = Field(..., description="源节点 ID")
    target_node_id: str = Field(..., description="目标节点 ID")
    source_port: Optional[str] = Field(default=None, description="源端口")
    target_port: Optional[str] = Field(default=None, description="目标端口")
    label: Optional[str] = Field(default=None, description="边标签")


class WorkflowEdgeUpdate(BaseModel):
    source_port: Optional[str] = Field(default=None, description="源端口")
    target_port: Optional[str] = Field(default=None, description="目标端口")
    label: Optional[str] = Field(default=None, description="边标签")


class WorkflowTemplate(BaseModel):
    id: str = Field(..., description="模板唯一标识")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(default=None, description="模板描述")
    category: str = Field(..., description="模板分类")
    nodes: list[dict] = Field(default_factory=list, description="节点列表")
    edges: list[dict] = Field(default_factory=list, description="边列表")
    icon: Optional[str] = Field(default=None, description="模板图标")
