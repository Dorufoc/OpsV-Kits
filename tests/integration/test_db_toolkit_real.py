from __future__ import annotations

import os
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

skip_if_no_ssh = pytest.mark.skipif(
    not os.environ.get("OPSV_SSH_HOST"),
    reason="集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。",
)

skip_if_no_mysql = pytest.mark.skipif(
    not os.environ.get("OPSV_MYSQL_HOST"),
    reason="MySQL 测试跳过：未设置 OPSV_MYSQL_HOST 环境变量。请设置 OPSV_MYSQL_HOST/OPSV_MYSQL_PORT/OPSV_MYSQL_USER/OPSV_MYSQL_PASSWORD。",
)

skip_if_no_redis = pytest.mark.skipif(
    not os.environ.get("OPSV_REDIS_HOST"),
    reason="Redis 测试跳过：未设置 OPSV_REDIS_HOST 环境变量。请设置 OPSV_REDIS_HOST/OPSV_REDIS_PORT/OPSV_REDIS_PASSWORD。",
)

TEST_DB_NAME = "opsv_test_db"
TEST_KEY_PREFIX = "opsv:test:"


def _get_mysql_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("OPSV_MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("OPSV_MYSQL_PORT", "3306")),
        "user": os.environ.get("OPSV_MYSQL_USER", "root"),
        "password": os.environ.get("OPSV_MYSQL_PASSWORD", ""),
    }


def _get_redis_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("OPSV_REDIS_HOST", "localhost"),
        "port": int(os.environ.get("OPSV_REDIS_PORT", "6379")),
        "password": os.environ.get("OPSV_REDIS_PASSWORD", ""),
        "db": int(os.environ.get("OPSV_REDIS_DB", "0")),
    }


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_mysql
class TestMySQLConnection:
    def test_mysql_show_databases(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        mysql = _get_mysql_config()
        resp = api_client.post(
            "/api/db-toolkit/mysql/query",
            json={
                "account_alias": alias,
                "container_id": None,
                "connection": {
                    "host": mysql["host"],
                    "port": mysql["port"],
                    "user": mysql["user"],
                    "password": mysql["password"],
                    "database": "",
                },
                "sql": "SHOW DATABASES",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("error", "") == "", f"MySQL 连接失败: {data.get('error')}"
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        assert len(columns) > 0, "SHOW DATABASES 返回列为空"
        assert len(rows) > 0, "SHOW DATABASES 返回行为空"
        db_names = [row[0] for row in rows if row]
        assert any("mysql" in name.lower() or "information_schema" in name.lower() for name in db_names), (
            f"SHOW DATABASES 结果中未找到系统数据库: {db_names}"
        )


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_mysql
class TestMySQLCRUD:
    @pytest.fixture(autouse=True)
    def _cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._mysql = _get_mysql_config()
        yield
        self._api_client.post(
            "/db-toolkit/mysql/query",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._mysql["host"],
                    "port": self._mysql["port"],
                    "user": self._mysql["user"],
                    "password": self._mysql["password"],
                    "database": "",
                },
                "sql": f"DROP DATABASE IF EXISTS `{TEST_DB_NAME}`",
            },
        )

    def _exec_sql(self, sql: str, database: str = "") -> dict[str, Any]:
        resp = self._api_client.post(
            "/db-toolkit/mysql/query",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._mysql["host"],
                    "port": self._mysql["port"],
                    "user": self._mysql["user"],
                    "password": self._mysql["password"],
                    "database": database,
                },
                "sql": sql,
            },
        )
        assert resp.status_code == 200
        return resp.json()

    def test_create_database_and_table(self) -> None:
        result = self._exec_sql(f"CREATE DATABASE `{TEST_DB_NAME}` CHARACTER SET utf8mb4")
        assert result.get("error", "") == "", f"创建数据库失败: {result.get('error')}"

        result = self._exec_sql(
            f"CREATE TABLE `users` ("
            f"`id` INT AUTO_INCREMENT PRIMARY KEY, "
            f"`name` VARCHAR(100) NOT NULL, "
            f"`email` VARCHAR(200)"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            database=TEST_DB_NAME,
        )
        assert result.get("error", "") == "", f"创建表失败: {result.get('error')}"

    def test_insert_chinese_data_and_query(self) -> None:
        self._exec_sql(f"CREATE DATABASE IF NOT EXISTS `{TEST_DB_NAME}` CHARACTER SET utf8mb4")

        self._exec_sql(
            f"CREATE TABLE IF NOT EXISTS `users` ("
            f"`id` INT AUTO_INCREMENT PRIMARY KEY, "
            f"`name` VARCHAR(100) NOT NULL, "
            f"`email` VARCHAR(200)"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            database=TEST_DB_NAME,
        )

        insert_result = self._exec_sql(
            f"INSERT INTO `users` (`name`, `email`) VALUES "
            f"('张三', 'zhangsan@example.com'), "
            f"('李四', 'lisi@example.com'), "
            f"('王五', 'wangwu@example.com')",
            database=TEST_DB_NAME,
        )
        assert insert_result.get("error", "") == "", f"插入中文数据失败: {insert_result.get('error')}"

        query_result = self._exec_sql(
            "SELECT `name`, `email` FROM `users` ORDER BY `id`",
            database=TEST_DB_NAME,
        )
        assert query_result.get("error", "") == "", f"查询中文数据失败: {query_result.get('error')}"
        rows = query_result.get("rows", [])
        assert len(rows) >= 3, f"查询结果行数不足: {len(rows)}"

        names = [row[0] for row in rows]
        assert "张三" in names, f"查询结果中未找到 '张三': {names}"
        assert "李四" in names, f"查询结果中未找到 '李四': {names}"
        assert "王五" in names, f"查询结果中未找到 '王五': {names}"

    def test_get_mysql_tables(self) -> None:
        self._exec_sql(f"CREATE DATABASE IF NOT EXISTS `{TEST_DB_NAME}` CHARACTER SET utf8mb4")
        self._exec_sql(
            f"CREATE TABLE IF NOT EXISTS `users` ("
            f"`id` INT AUTO_INCREMENT PRIMARY KEY, "
            f"`name` VARCHAR(100) NOT NULL"
            f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4",
            database=TEST_DB_NAME,
        )

        resp = self._api_client.post(
            "/api/db-toolkit/mysql/tables",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._mysql["host"],
                    "port": self._mysql["port"],
                    "user": self._mysql["user"],
                    "password": self._mysql["password"],
                    "database": TEST_DB_NAME,
                },
            },
        )
        assert resp.status_code == 200
        tables = resp.json()
        assert isinstance(tables, list)
        assert "users" in tables, f"表列表中未找到 'users': {tables}"


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_redis
class TestRedisConnection:
    @pytest.fixture(autouse=True)
    def _cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._redis = _get_redis_config()
        yield
        self._cleanup_test_keys()

    def _cleanup_test_keys(self) -> None:
        keys_to_delete = [
            f"{TEST_KEY_PREFIX}string",
            f"{TEST_KEY_PREFIX}list",
            f"{TEST_KEY_PREFIX}hash",
            f"{TEST_KEY_PREFIX}set",
        ]
        for key in keys_to_delete:
            self._api_client.delete(
                "/api/db-toolkit/redis/key",
                params={
                    "account_alias": self._alias,
                    "key": key,
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
            )

    def _build_redis_cli_prefix(self) -> str:
        pwd = self._redis["password"]
        auth_part = f"-a {pwd}" if pwd else ""
        return (
            f"redis-cli -h {self._redis['host']} -p {self._redis['port']} "
            f"{auth_part} -n {self._redis['db']}"
        )

    def test_redis_set_and_get(self) -> None:
        test_key = f"{TEST_KEY_PREFIX}string"
        test_value = "hello_opsv_测试值"

        set_resp = self._api_client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": f"{self._build_redis_cli_prefix()} SET {test_key} '{test_value}'",
                "timeout": 10.0,
            },
        )
        assert set_resp.status_code == 200
        assert "OK" in set_resp.json().get("stdout", ""), "Redis SET 命令失败"

        get_resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": self._alias,
                "command": f"{self._build_redis_cli_prefix()} GET {test_key}",
                "timeout": 10.0,
            },
        )
        assert get_resp.status_code == 200
        stdout = get_resp.json().get("stdout", "")
        assert test_value in stdout, f"Redis GET 结果不匹配: 期望 '{test_value}', 实际 '{stdout}'"

    def test_redis_db_stats(self) -> None:
        resp = self._api_client.post(
            "/api/db-toolkit/redis/db-stats",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "database": "",
                },
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "key_count" in data
            assert isinstance(data["key_count"], int)


@pytest.mark.integration
@skip_if_no_ssh
@skip_if_no_redis
class TestRedisDataTypes:
    @pytest.fixture(autouse=True)
    def _setup_and_cleanup(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._redis = _get_redis_config()
        self._setup_test_data()
        yield
        self._cleanup_test_keys()

    def _build_redis_cli_prefix(self) -> str:
        pwd = self._redis["password"]
        auth_part = f"-a {pwd}" if pwd else ""
        return (
            f"redis-cli -h {self._redis['host']} -p {self._redis['port']} "
            f"{auth_part} -n {self._redis['db']}"
        )

    def _redis_cli(self, command: str) -> str:
        resp = self._api_client.post(
            "/command/exec",
            json={
                "alias": self._alias,
                "command": f"{self._build_redis_cli_prefix()} {command}",
                "timeout": 10.0,
            },
        )
        if resp.status_code == 200:
            return resp.json().get("stdout", "")
        return ""

    def _setup_test_data(self) -> None:
        self._redis_cli(f"DEL {TEST_KEY_PREFIX}list {TEST_KEY_PREFIX}hash {TEST_KEY_PREFIX}set")
        self._redis_cli(f"RPUSH {TEST_KEY_PREFIX}list 'item1' 'item2' 'item3'")
        self._redis_cli(f"HSET {TEST_KEY_PREFIX}hash field1 'value1' field2 '值2'")
        self._redis_cli(f"SADD {TEST_KEY_PREFIX}set 'member1' 'member2' 'member3'")

    def _cleanup_test_keys(self) -> None:
        keys = [
            f"{TEST_KEY_PREFIX}list",
            f"{TEST_KEY_PREFIX}hash",
            f"{TEST_KEY_PREFIX}set",
            f"{TEST_KEY_PREFIX}string",
        ]
        for key in keys:
            self._api_client.delete(
                "/db-toolkit/redis/key",
                params={
                    "account_alias": self._alias,
                    "key": key,
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
            )

    def test_list_operations(self) -> None:
        key = f"{TEST_KEY_PREFIX}list"
        resp = self._api_client.post(
            "/api/db-toolkit/redis/key-info",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
                "key": key,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("type") == "list", f"Key 类型应为 list, 实际为 {data.get('type')}"
        value = data.get("value", [])
        assert len(value) >= 3, f"List 元素数量不足: {value}"

    def test_hash_operations(self) -> None:
        key = f"{TEST_KEY_PREFIX}hash"
        resp = self._api_client.post(
            "/db-toolkit/redis/key-info",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
                "key": key,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("type") == "hash", f"Key 类型应为 hash, 实际为 {data.get('type')}"
        value = data.get("value", {})
        assert isinstance(value, dict), f"Hash 值应为 dict, 实际为 {type(value)}"
        assert "field1" in value, f"Hash 中未找到 field1: {value}"
        assert "field2" in value, f"Hash 中未找到 field2: {value}"

    def test_set_operations(self) -> None:
        key = f"{TEST_KEY_PREFIX}set"
        resp = self._api_client.post(
            "/db-toolkit/redis/key-info",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
                "key": key,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("type") == "set", f"Key 类型应为 set, 实际为 {data.get('type')}"
        value = data.get("value", [])
        assert len(value) >= 3, f"Set 元素数量不足: {value}"

    def test_scan_keys(self) -> None:
        resp = self._api_client.post(
            "/api/db-toolkit/redis/scan",
            json={
                "account_alias": self._alias,
                "container_id": None,
                "connection": {
                    "host": self._redis["host"],
                    "port": self._redis["port"],
                    "password": self._redis["password"],
                    "db": self._redis["db"],
                },
                "pattern": f"{TEST_KEY_PREFIX}*",
                "count": 100,
                "cursor": 0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        keys = data.get("keys", [])
        assert len(keys) >= 3, f"SCAN 结果中测试 Key 数量不足: {keys}"
