from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket

from app.models.db_toolkit import (
    DangerousCheckResult,
    DangerousRedisCheckRequest,
    DangerousSqlCheckRequest,
    DbToolkitError,
    DetectResult,
    MysqlQueryRequest,
    MysqlQueryResult,
    MysqlTablesRequest,
    MysqlTableStructure,
    MysqlTableStructureRequest,
    RedisDeleteKeyRequest,
    RedisDbStats,
    RedisKeyInfo,
    RedisKeyInfoRequest,
    RedisScanRequest,
    RedisScanResult,
)
from app.services.db_toolkit_service import db_toolkit_service
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/db-toolkit", tags=["db-toolkit"])


def _verify_account(account_alias: str) -> None:
    account = ssh_account_service.get_account(account_alias)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"SSH 账户 '{account_alias}' 不存在",
        )


def _handle_toolkit_error(e: DbToolkitError) -> None:
    logger.error("DB Toolkit 错误 [%s]: %s", e.code, e.message)
    raise HTTPException(status_code=e.http_status, detail=e.message)


# ── 客户端探测 ───────────────────────────────────────────────────


@router.get("/detect/mysql")
async def detect_mysql_client(
    account_alias: str = Query(..., description="SSH 账户别名"),
    container_id: str = Query(..., description="容器 ID"),
) -> DetectResult:
    _verify_account(account_alias)
    return db_toolkit_service.detect_mysql_client(account_alias, container_id)


@router.get("/detect/redis")
async def detect_redis_client(
    account_alias: str = Query(..., description="SSH 账户别名"),
    container_id: str = Query(..., description="容器 ID"),
) -> DetectResult:
    _verify_account(account_alias)
    return db_toolkit_service.detect_redis_client(account_alias, container_id)


# ── MySQL 可视化查询 ─────────────────────────────────────────────


@router.post("/mysql/query")
async def execute_mysql_query(data: MysqlQueryRequest) -> MysqlQueryResult:
    _verify_account(data.account_alias)
    try:
        return db_toolkit_service.execute_mysql_query(
            data.account_alias, data.container_id, data.connection, data.sql
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


@router.post("/mysql/tables")
async def get_mysql_tables(data: MysqlTablesRequest) -> list[str]:
    _verify_account(data.account_alias)
    try:
        return db_toolkit_service.get_mysql_tables(
            data.account_alias, data.container_id, data.connection
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


@router.post("/mysql/table-structure")
async def get_mysql_table_structure(
    data: MysqlTableStructureRequest,
) -> MysqlTableStructure:
    _verify_account(data.account_alias)
    try:
        return db_toolkit_service.get_mysql_table_structure(
            data.account_alias, data.container_id, data.connection, data.table_name
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


# ── Redis 可视化查询 ─────────────────────────────────────────────


@router.post("/redis/scan")
async def scan_redis_keys(data: RedisScanRequest) -> RedisScanResult:
    _verify_account(data.account_alias)
    try:
        return db_toolkit_service.scan_redis_keys(
            data.account_alias, data.container_id, data.connection,
            data.pattern, data.count, data.cursor,
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


@router.post("/redis/key-info")
async def get_redis_key_info(data: RedisKeyInfoRequest) -> RedisKeyInfo:
    _verify_account(data.account_alias)
    try:
        return db_toolkit_service.get_redis_key_info(
            data.account_alias, data.container_id, data.connection, data.key
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


@router.post("/redis/db-stats")
async def get_redis_db_stats(data: MysqlTablesRequest) -> RedisDbStats:
    _verify_account(data.account_alias)
    try:
        from app.models.db_toolkit import RedisConnectionParams
        connection = RedisConnectionParams(**data.connection.model_dump())
        return db_toolkit_service.get_redis_db_stats(
            data.account_alias, data.container_id, connection
        )
    except DbToolkitError as e:
        _handle_toolkit_error(e)


@router.delete("/redis/key")
async def delete_redis_key(
    account_alias: str = Query(..., description="SSH 账户别名"),
    container_id: str = Query(..., description="容器 ID"),
    key: str = Query(..., description="Key 名称"),
    host: str = Query("localhost", description="Redis 主机"),
    port: int = Query(6379, description="Redis 端口"),
    password: str = Query("", description="Redis 密码"),
    db: int = Query(0, description="Redis 数据库编号"),
):
    _verify_account(account_alias)
    try:
        from app.models.db_toolkit import RedisConnectionParams
        connection = RedisConnectionParams(
            host=host, port=port, password=password, db=db
        )
        success = db_toolkit_service.delete_redis_key(
            account_alias, container_id, connection, key
        )
        return {"success": success}
    except DbToolkitError as e:
        _handle_toolkit_error(e)


# ── 安全检测 ─────────────────────────────────────────────────────


@router.post("/check-dangerous-sql")
async def check_dangerous_sql(
    data: DangerousSqlCheckRequest,
) -> DangerousCheckResult:
    return db_toolkit_service.check_dangerous_sql(data.sql)


@router.post("/check-dangerous-redis")
async def check_dangerous_redis_command(
    data: DangerousRedisCheckRequest,
) -> DangerousCheckResult:
    return db_toolkit_service.check_dangerous_redis_command(data.command)


# ── WebSocket CLI 终端 ───────────────────────────────────────────


@router.websocket("/ws/mysql-cli/{container_id}")
async def mysql_cli_ws(websocket: WebSocket, container_id: str):
    from app.core.db_toolkit_ws import db_toolkit_ws_handler
    from app.models.db_toolkit import MySqlConnectionParams
    import asyncio
    import json as _json

    try:
        await websocket.accept()
        init_raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=10.0
        )
        init_msg = _json.loads(init_raw)
        account_alias = init_msg.get("account_alias", "")
        conn_data = init_msg.get("connection", {})

        if not account_alias:
            await websocket.send_json({
                "type": "error",
                "message": "缺少 account_alias 参数",
            })
            await websocket.close()
            return

        connection = MySqlConnectionParams(**conn_data)
        await db_toolkit_ws_handler._handle_cli_direct(
            websocket, account_alias, container_id, connection, "mysql"
        )
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/redis-cli/{container_id}")
async def redis_cli_ws(websocket: WebSocket, container_id: str):
    from app.core.db_toolkit_ws import db_toolkit_ws_handler
    from app.models.db_toolkit import RedisConnectionParams
    import asyncio
    import json as _json

    try:
        await websocket.accept()
        init_raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=10.0
        )
        init_msg = _json.loads(init_raw)
        account_alias = init_msg.get("account_alias", "")
        conn_data = init_msg.get("connection", {})

        if not account_alias:
            await websocket.send_json({
                "type": "error",
                "message": "缺少 account_alias 参数",
            })
            await websocket.close()
            return

        connection = RedisConnectionParams(**conn_data)
        await db_toolkit_ws_handler._handle_cli_direct(
            websocket, account_alias, container_id, connection, "redis"
        )
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
