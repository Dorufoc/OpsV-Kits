from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BackupType(str, Enum):
    WEBSITE = "website"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    CUSTOM = "custom"


class StorageType(str, Enum):
    LOCAL = "local"
    ALIYUN_OSS = "aliyun_oss"
    TENCENT_COS = "tencent_cos"
    AWS_S3 = "aws_s3"
    FTP = "ftp"
    SFTP = "sftp"


class CompressionType(str, Enum):
    TAR_GZ = "tar.gz"
    ZIP = "zip"
    NONE = "none"


class CleanupAction(str, Enum):
    DELETE = "delete"
    COMPRESS = "compress"
    MOVE = "move"


class TaskStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class CronJob(BaseModel):
    """Cron 任务模型"""
    id: str = Field(..., description="任务唯一标识")
    name: str = Field(..., description="任务名称")
    cron_expression: str = Field(..., description="Cron 表达式")
    task_type: str = Field(default="shell", description="任务类型: shell/url")
    command: str = Field(..., description="执行命令或 URL")
    http_method: Optional[str] = Field(default=None, description="HTTP 方法 (GET/POST)，仅 URL 类型使用")
    http_headers: Optional[dict] = Field(default=None, description="HTTP 请求头")
    http_body: Optional[str] = Field(default=None, description="HTTP 请求体")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="任务状态")
    account_alias: str = Field(..., description="关联的 SSH 账户别名")
    description: Optional[str] = Field(default=None, description="任务描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_run_at: Optional[datetime] = Field(default=None, description="最后执行时间")
    last_run_status: Optional[str] = Field(default=None, description="最后执行状态")


class CronJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    cron_expression: str = Field(..., min_length=1, description="Cron 表达式")
    task_type: str = Field(default="shell", description="任务类型: shell/url")
    command: str = Field(..., min_length=1, description="执行命令或 URL")
    http_method: Optional[str] = Field(default=None, description="HTTP 方法")
    http_headers: Optional[dict] = Field(default=None, description="HTTP 请求头")
    http_body: Optional[str] = Field(default=None, description="HTTP 请求体")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="任务状态")
    description: Optional[str] = Field(default=None, description="任务描述")


class CronJobUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="任务名称")
    cron_expression: Optional[str] = Field(default=None, description="Cron 表达式")
    task_type: Optional[str] = Field(default=None, description="任务类型")
    command: Optional[str] = Field(default=None, description="执行命令或 URL")
    http_method: Optional[str] = Field(default=None, description="HTTP 方法")
    http_headers: Optional[dict] = Field(default=None, description="HTTP 请求头")
    http_body: Optional[str] = Field(default=None, description="HTTP 请求体")
    status: Optional[TaskStatus] = Field(default=None, description="任务状态")
    description: Optional[str] = Field(default=None, description="任务描述")


class BackupPolicy(BaseModel):
    """备份策略模型"""
    id: str = Field(..., description="策略唯一标识")
    name: str = Field(..., description="策略名称")
    backup_type: BackupType = Field(..., description="备份类型")
    source_path: Optional[str] = Field(default=None, description="源路径（网站目录或自定义目录）")
    db_name: Optional[str] = Field(default=None, description="数据库名称")
    db_host: Optional[str] = Field(default="localhost", description="数据库主机")
    db_port: Optional[int] = Field(default=None, description="数据库端口")
    db_username: Optional[str] = Field(default=None, description="数据库用户名")
    db_password_encrypted: Optional[str] = Field(default=None, description="数据库密码（加密）")
    storage_type: StorageType = Field(..., description="存储类型")
    storage_config: dict = Field(default_factory=dict, description="存储配置（根据类型不同）")
    cron_expression: str = Field(..., description="执行周期 Cron 表达式")
    retention_count: int = Field(default=7, ge=1, description="保留份数")
    compression: CompressionType = Field(default=CompressionType.TAR_GZ, description="压缩格式")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="策略状态")
    account_alias: str = Field(..., description="关联的 SSH 账户别名")
    description: Optional[str] = Field(default=None, description="策略描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_backup_at: Optional[datetime] = Field(default=None, description="最后备份时间")
    last_backup_status: Optional[str] = Field(default=None, description="最后备份状态")


class BackupPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    backup_type: BackupType = Field(..., description="备份类型")
    source_path: Optional[str] = Field(default=None, description="源路径")
    db_name: Optional[str] = Field(default=None, description="数据库名称")
    db_host: Optional[str] = Field(default="localhost", description="数据库主机")
    db_port: Optional[int] = Field(default=None, description="数据库端口")
    db_username: Optional[str] = Field(default=None, description="数据库用户名")
    db_password: Optional[str] = Field(default=None, description="数据库密码（明文传入）")
    storage_type: StorageType = Field(..., description="存储类型")
    storage_config: dict = Field(default_factory=dict, description="存储配置")
    cron_expression: str = Field(..., description="执行周期")
    retention_count: int = Field(default=7, ge=1, description="保留份数")
    compression: CompressionType = Field(default=CompressionType.TAR_GZ, description="压缩格式")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="策略状态")
    description: Optional[str] = Field(default=None, description="策略描述")


class BackupPolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="策略名称")
    backup_type: Optional[BackupType] = Field(default=None, description="备份类型")
    source_path: Optional[str] = Field(default=None, description="源路径")
    db_name: Optional[str] = Field(default=None, description="数据库名称")
    db_host: Optional[str] = Field(default=None, description="数据库主机")
    db_port: Optional[int] = Field(default=None, description="数据库端口")
    db_username: Optional[str] = Field(default=None, description="数据库用户名")
    db_password: Optional[str] = Field(default=None, description="数据库密码")
    storage_type: Optional[StorageType] = Field(default=None, description="存储类型")
    storage_config: Optional[dict] = Field(default=None, description="存储配置")
    cron_expression: Optional[str] = Field(default=None, description="执行周期")
    retention_count: Optional[int] = Field(default=None, ge=1, description="保留份数")
    compression: Optional[CompressionType] = Field(default=None, description="压缩格式")
    status: Optional[TaskStatus] = Field(default=None, description="策略状态")
    description: Optional[str] = Field(default=None, description="策略描述")


class BackupHistory(BaseModel):
    """备份历史记录模型"""
    id: str = Field(..., description="记录唯一标识")
    policy_id: str = Field(..., description="关联策略 ID")
    policy_name: str = Field(..., description="策略名称")
    backup_type: BackupType = Field(..., description="备份类型")
    file_path: Optional[str] = Field(default=None, description="本地备份文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小（字节）")
    storage_type: StorageType = Field(..., description="存储类型")
    storage_path: Optional[str] = Field(default=None, description="远程存储路径")
    status: str = Field(..., description="状态: success/failed/running")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    account_alias: str = Field(..., description="关联的 SSH 账户别名")


class LogRetentionPolicy(BaseModel):
    """日志保留策略模型"""
    id: str = Field(..., description="策略唯一标识")
    name: str = Field(..., description="策略名称")
    log_path_pattern: str = Field(..., description="日志路径或通配模式")
    retention_days: int = Field(default=30, ge=1, description="保留天数")
    cleanup_action: CleanupAction = Field(default=CleanupAction.DELETE, description="清理动作")
    archive_path: Optional[str] = Field(default=None, description="归档目录路径")
    cron_expression: str = Field(..., description="执行周期 Cron 表达式")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="策略状态")
    account_alias: str = Field(..., description="关联的 SSH 账户别名")
    description: Optional[str] = Field(default=None, description="策略描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    last_run_at: Optional[datetime] = Field(default=None, description="最后执行时间")
    last_run_status: Optional[str] = Field(default=None, description="最后执行状态")


class LogRetentionPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    log_path_pattern: str = Field(..., min_length=1, description="日志路径或通配模式")
    retention_days: int = Field(default=30, ge=1, description="保留天数")
    cleanup_action: CleanupAction = Field(default=CleanupAction.DELETE, description="清理动作")
    archive_path: Optional[str] = Field(default=None, description="归档目录路径")
    cron_expression: str = Field(..., description="执行周期")
    status: TaskStatus = Field(default=TaskStatus.ENABLED, description="策略状态")
    description: Optional[str] = Field(default=None, description="策略描述")


class LogRetentionPolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100, description="策略名称")
    log_path_pattern: Optional[str] = Field(default=None, description="日志路径或通配模式")
    retention_days: Optional[int] = Field(default=None, ge=1, description="保留天数")
    cleanup_action: Optional[CleanupAction] = Field(default=None, description="清理动作")
    archive_path: Optional[str] = Field(default=None, description="归档目录路径")
    cron_expression: Optional[str] = Field(default=None, description="执行周期")
    status: Optional[TaskStatus] = Field(default=None, description="策略状态")
    description: Optional[str] = Field(default=None, description="策略描述")


class ExecutionLog(BaseModel):
    """任务执行日志模型"""
    id: str = Field(..., description="记录唯一标识")
    task_id: str = Field(..., description="关联任务 ID")
    task_type: str = Field(..., description="任务类型: cron/backup/log_cleanup")
    task_name: str = Field(..., description="任务名称")
    status: str = Field(..., description="状态: success/failed")
    exit_code: Optional[int] = Field(default=None, description="退出码")
    output: Optional[str] = Field(default=None, description="标准输出")
    error: Optional[str] = Field(default=None, description="错误输出")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    duration_seconds: Optional[float] = Field(default=None, description="执行耗时（秒）")
    account_alias: str = Field(..., description="关联的 SSH 账户别名")


class DiskUsageInfo(BaseModel):
    """磁盘使用信息"""
    filesystem: str = Field(..., description="文件系统")
    size: str = Field(..., description="总容量")
    used: str = Field(..., description="已使用")
    available: str = Field(..., description="可用空间")
    use_percent: int = Field(..., ge=0, le=100, description="使用百分比")
    mount_point: str = Field(..., description="挂载点")


class FileInfo(BaseModel):
    """文件信息"""
    path: str = Field(..., description="文件路径")
    size: int = Field(..., description="文件大小（字节）")
    modified_at: datetime = Field(..., description="修改时间")
