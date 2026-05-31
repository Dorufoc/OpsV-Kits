from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MySqlConnectionParams(BaseModel):
    host: str = Field(default="localhost", description="MySQL 主机")
    port: int = Field(default=3306, ge=1, le=65535, description="MySQL 端口")
    user: str = Field(default="root", max_length=32, description="MySQL 用户名")
    password: str = Field(default="", max_length=128, description="MySQL 密码")
    database: str = Field(default="", max_length=64, description="数据库名")


class RedisConnectionParams(BaseModel):
    host: str = Field(default="localhost", description="Redis 主机")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis 端口")
    password: str = Field(default="", max_length=128, description="Redis 密码")
    db: int = Field(default=0, ge=0, le=15, description="Redis 数据库编号")


class DetectResult(BaseModel):
    installed: bool = Field(description="客户端是否已安装")
    path: str = Field(default="", description="客户端路径")
    client_version: str = Field(default="", description="客户端版本")
    error: str = Field(default="", description="错误信息")


class MysqlColumnDef(BaseModel):
    field: str = Field(description="字段名")
    type: str = Field(description="字段类型")
    null: str = Field(description="是否允许 NULL")
    key: str = Field(default="", description="键类型")
    default: Optional[str] = Field(default=None, description="默认值")
    extra: str = Field(default="", description="额外信息")


class MysqlIndexDef(BaseModel):
    name: str = Field(description="索引名称")
    column: str = Field(description="索引列")
    unique: bool = Field(description="是否唯一索引")


class MysqlTableStructure(BaseModel):
    table_name: str = Field(description="表名")
    columns: list[MysqlColumnDef] = Field(default_factory=list, description="列定义")
    indexes: list[MysqlIndexDef] = Field(default_factory=list, description="索引信息")
    row_count: int = Field(default=0, description="行数")
    create_ddl: str = Field(default="", description="建表语句")


class MysqlQueryResult(BaseModel):
    columns: list[str] = Field(default_factory=list, description="列名")
    rows: list[list[str]] = Field(default_factory=list, description="数据行")
    total_count: int = Field(default=0, description="总行数")
    truncated: bool = Field(default=False, description="结果是否被截断")
    error: str = Field(default="", description="错误信息")


class RedisScanResult(BaseModel):
    keys: list[str] = Field(default_factory=list, description="Key 列表")
    next_cursor: int = Field(default=0, description="下一页游标")
    has_more: bool = Field(default=False, description="是否还有更多 Key")


class RedisKeyInfo(BaseModel):
    key: str = Field(description="Key 名称")
    type: str = Field(description="Key 类型")
    ttl: int = Field(description="TTL（秒）")
    ttl_display: str = Field(default="", description="TTL 格式化展示")
    value: Any = Field(default=None, description="Value 内容")
    size_bytes: int = Field(default=0, description="Value 大小(字节)")
    truncated: bool = Field(default=False, description="Value 是否被截断")


class RedisDbStats(BaseModel):
    key_count: int = Field(default=0, description="Key 总数")
    used_memory_human: str = Field(default="", description="内存使用(人类可读)")
    used_memory_bytes: int = Field(default=0, description="内存使用(字节)")


class DangerousCheckResult(BaseModel):
    is_dangerous: bool = Field(description="是否为高危操作")
    reason: str = Field(default="", description="危险原因")
    level: str = Field(default="warning", description="危险等级: critical/warning")


class MysqlQueryRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: MySqlConnectionParams = Field(description="MySQL 连接参数")
    sql: str = Field(max_length=4096, description="SQL 语句")


class MysqlTablesRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: MySqlConnectionParams = Field(description="MySQL 连接参数")


class MysqlTableStructureRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: MySqlConnectionParams = Field(description="MySQL 连接参数")
    table_name: str = Field(description="表名")


class RedisScanRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: RedisConnectionParams = Field(description="Redis 连接参数")
    pattern: str = Field(default="*", description="Key 匹配模式")
    count: int = Field(default=100, ge=1, le=500, description="每次 SCAN 数量")
    cursor: int = Field(default=0, ge=0, description="SCAN 游标")


class RedisKeyInfoRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: RedisConnectionParams = Field(description="Redis 连接参数")
    key: str = Field(description="Key 名称")


class RedisDeleteKeyRequest(BaseModel):
    account_alias: str = Field(description="SSH 账户别名")
    container_id: Optional[str] = Field(default=None, description="容器 ID，为空表示主机模式")
    connection: RedisConnectionParams = Field(description="Redis 连接参数")
    key: str = Field(description="Key 名称")


class DangerousSqlCheckRequest(BaseModel):
    sql: str = Field(description="待检测的 SQL 语句")


class DangerousRedisCheckRequest(BaseModel):
    command: str = Field(description="待检测的 Redis 命令")


class DbToolkitError(Exception):
    _STATUS_MAP: dict[str, int] = {
        "DB_TOOLKIT_4001": 400,
        "DB_TOOLKIT_4002": 400,
        "DB_TOOLKIT_4041": 404,
        "DB_TOOLKIT_4042": 404,
        "DB_TOOLKIT_4221": 422,
        "DB_TOOLKIT_5031": 503,
        "DB_TOOLKIT_5032": 503,
        "DB_TOOLKIT_5041": 504,
    }

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

    @property
    def http_status(self) -> int:
        return self._STATUS_MAP.get(self.code, 500)
