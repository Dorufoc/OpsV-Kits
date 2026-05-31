from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProbeType(str, Enum):
    HTTP = "http"
    TCP = "tcp"
    ICMP = "icmp"


class ProbeStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class HttpProbeConfig(BaseModel):
    expected_status_codes: list[int] = Field(default_factory=lambda: [200], description="期望的 HTTP 状态码列表")
    content_match: Optional[str] = Field(default=None, description="响应体内容匹配正则表达式")
    method: str = Field(default="GET", description="HTTP 方法")
    headers: Optional[dict[str, str]] = Field(default=None, description="自定义请求头")
    follow_redirects: bool = Field(default=True, description="是否跟随重定向")


class ProbeTarget(BaseModel):
    id: str = Field(..., description="唯一标识")
    name: str = Field(..., min_length=1, max_length=100, description="目标名称")
    probe_type: ProbeType = Field(..., description="探测类型")
    target: str = Field(..., min_length=1, description="目标地址")
    interval_seconds: int = Field(default=60, ge=10, description="探测频率（秒）")
    timeout_seconds: int = Field(default=10, ge=1, description="探测超时时间（秒）")
    enabled: bool = Field(default=True, description="是否启用")
    failure_threshold: int = Field(default=3, ge=1, description="连续失败阈值")
    recovery_threshold: int = Field(default=2, ge=1, description="连续成功恢复阈值")
    http_config: Optional[HttpProbeConfig] = Field(default=None, description="HTTP 探测专属配置")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    current_status: ProbeStatus = Field(default=ProbeStatus.UNKNOWN, description="当前可用性状态")
    consecutive_failures: int = Field(default=0, description="连续失败次数")
    consecutive_successes: int = Field(default=0, description="连续成功次数")
    last_probe_time: Optional[datetime] = Field(default=None, description="最近一次探测时间")
    last_success_time: Optional[datetime] = Field(default=None, description="最近一次成功时间")
    last_failure_time: Optional[datetime] = Field(default=None, description="最近一次失败时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class HttpProbeConfigCreate(BaseModel):
    expected_status_codes: list[int] = Field(default_factory=lambda: [200], description="期望的 HTTP 状态码列表")
    content_match: Optional[str] = Field(default=None, description="响应体内容匹配正则表达式")
    method: str = Field(default="GET", description="HTTP 方法")
    headers: Optional[dict[str, str]] = Field(default=None, description="自定义请求头")
    follow_redirects: bool = Field(default=True, description="是否跟随重定向")


class ProbeTargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="目标名称")
    probe_type: ProbeType = Field(..., description="探测类型")
    target: str = Field(..., min_length=1, description="目标地址")
    interval_seconds: int = Field(default=60, ge=10, description="探测频率（秒）")
    timeout_seconds: int = Field(default=10, ge=1, description="探测超时时间（秒）")
    enabled: bool = Field(default=True, description="是否启用")
    failure_threshold: int = Field(default=3, ge=1, description="连续失败阈值")
    recovery_threshold: int = Field(default=2, ge=1, description="连续成功恢复阈值")
    http_config: Optional[HttpProbeConfigCreate] = Field(default=None, description="HTTP 探测专属配置")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class ProbeTargetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="目标名称")
    probe_type: Optional[ProbeType] = Field(default=None, description="探测类型")
    target: Optional[str] = Field(default=None, min_length=1, description="目标地址")
    interval_seconds: Optional[int] = Field(default=None, ge=10, description="探测频率（秒）")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, description="探测超时时间（秒）")
    enabled: Optional[bool] = Field(default=None, description="是否启用")
    failure_threshold: Optional[int] = Field(default=None, ge=1, description="连续失败阈值")
    recovery_threshold: Optional[int] = Field(default=None, ge=1, description="连续成功恢复阈值")
    http_config: Optional[HttpProbeConfigCreate] = Field(default=None, description="HTTP 探测专属配置")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")


class ProbeResult(BaseModel):
    id: str = Field(..., description="日志唯一标识")
    target_id: str = Field(..., description="关联的探测目标 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="探测时间戳")
    probe_type: ProbeType = Field(..., description="探测类型")
    target: str = Field(..., description="目标地址")
    success: bool = Field(..., description="是否成功")
    response_time_ms: Optional[float] = Field(default=None, description="响应时间（毫秒）")
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    error_message: Optional[str] = Field(default=None, description="失败原因")
    content_matched: Optional[bool] = Field(default=None, description="内容是否匹配")


class ProbeStatistics(BaseModel):
    target_id: str = Field(..., description="探测目标 ID")
    uptime_percent: float = Field(default=0.0, description="可用率百分比")
    avg_response_time_ms: Optional[float] = Field(default=None, description="平均响应时间（毫秒）")
    max_response_time_ms: Optional[float] = Field(default=None, description="最大响应时间（毫秒）")
    min_response_time_ms: Optional[float] = Field(default=None, description="最小响应时间（毫秒）")
    total_probes: int = Field(default=0, description="总探测次数")
    success_count: int = Field(default=0, description="成功次数")
    failure_count: int = Field(default=0, description="失败次数")
    current_status: ProbeStatus = Field(default=ProbeStatus.UNKNOWN, description="当前可用性状态")
    last_probe_time: Optional[datetime] = Field(default=None, description="最近一次探测时间")
    last_success_time: Optional[datetime] = Field(default=None, description="最近一次成功时间")
    last_failure_time: Optional[datetime] = Field(default=None, description="最近一次失败时间")


class ProbeOverview(BaseModel):
    total_targets: int = Field(default=0, description="总目标数")
    available_count: int = Field(default=0, description="可用数")
    unavailable_count: int = Field(default=0, description="不可用数")
    unknown_count: int = Field(default=0, description="未知状态数")
    targets: list[ProbeTarget] = Field(default_factory=list, description="所有探测目标")
