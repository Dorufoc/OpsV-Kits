"""数据库工具包接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.db_toolkit import (
    DetectResult,
    MysqlQueryResult,
    MysqlTableStructure,
    MysqlColumnDef,
    RedisScanResult,
    RedisKeyInfo,
)


@pytest.fixture
def client():
    return TestClient(app)


class TestDbToolkitDetect:
    """数据库工具包客户端探测测试"""

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_detect_mysql_client(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.detect_mysql_client.return_value = DetectResult(
            installed=True,
            path="/usr/bin/mysql",
            client_version="8.0",
        )

        response = client.get(
            "/api/db-toolkit/detect/mysql?account_alias=test-server&container_id=abc123"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert "mysql" in data["path"]

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_detect_redis_client(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.detect_redis_client.return_value = DetectResult(
            installed=True,
            path="/usr/bin/redis-cli",
            client_version="7.0",
        )

        response = client.get(
            "/api/db-toolkit/detect/redis?account_alias=test-server&container_id=def456"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert "redis" in data["path"]

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    def test_detect_mysql_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get(
            "/api/db-toolkit/detect/mysql?account_alias=nonexistent&container_id=abc123"
        )
        assert response.status_code == 404


class TestMySQLQuery:
    """MySQL查询接口测试"""

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_execute_mysql_query(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.execute_mysql_query.return_value = MysqlQueryResult(
            columns=["id", "name", "email"],
            rows=[
                ["1", "张三", "zhangsan@example.com"],
                ["2", "李四", "lisi@example.com"],
            ],
            total_count=2,
        )

        response = client.post(
            "/api/db-toolkit/mysql/query",
            json={
                "account_alias": "test-server",
                "container_id": "mysql-container",
                "connection": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "password",
                    "database": "mydb",
                },
                "sql": "SELECT id, name, email FROM users LIMIT 10",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert "rows" in data

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_get_mysql_tables(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.get_mysql_tables.return_value = ["users", "orders", "products"]

        response = client.post(
            "/api/db-toolkit/mysql/tables",
            json={
                "account_alias": "test-server",
                "container_id": "mysql-container",
                "connection": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "password",
                    "database": "mydb",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_get_mysql_table_structure(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.get_mysql_table_structure.return_value = MysqlTableStructure(
            table_name="users",
            columns=[
                MysqlColumnDef(field="id", type="int", null="NO", key="PRI", default=None, extra="auto_increment"),
                MysqlColumnDef(field="name", type="varchar(255)", null="YES", key="", default=None, extra=""),
            ],
        )

        response = client.post(
            "/api/db-toolkit/mysql/table-structure",
            json={
                "account_alias": "test-server",
                "container_id": "mysql-container",
                "connection": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "password",
                    "database": "mydb",
                },
                "table_name": "users",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == "users"
        assert len(data["columns"]) == 2


class TestRedisOperations:
    """Redis操作接口测试"""

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_scan_redis_keys(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.scan_redis_keys.return_value = RedisScanResult(
            keys=["user:1001", "user:1002", "session:abc"],
            next_cursor=0,
            has_more=False,
        )

        response = client.post(
            "/api/db-toolkit/redis/scan",
            json={
                "account_alias": "test-server",
                "container_id": "redis-container",
                "connection": {
                    "host": "localhost",
                    "port": 6379,
                    "password": "",
                    "db": 0,
                },
                "pattern": "user:*",
                "count": 10,
                "cursor": 0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) == 3

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_get_redis_key_info(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.get_redis_key_info.return_value = RedisKeyInfo(
            key="user:1001",
            type="string",
            ttl=-1,
            ttl_display="永久",
            value="张三",
            size_bytes=12,
        )

        response = client.post(
            "/api/db-toolkit/redis/key-info",
            json={
                "account_alias": "test-server",
                "container_id": "redis-container",
                "connection": {
                    "host": "localhost",
                    "port": 6379,
                    "password": "",
                    "db": 0,
                },
                "key": "user:1001",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "string"
        assert data["value"] == "张三"

    @patch("app.api.routes.db_toolkit.ssh_account_service")
    @patch("app.api.routes.db_toolkit.db_toolkit_service")
    def test_delete_redis_key(self, mock_db_service, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = MagicMock()
        mock_db_service.delete_redis_key.return_value = True

        response = client.delete(
            "/api/db-toolkit/redis/key?account_alias=test-server&container_id=redis-container&key=user:1001&host=localhost&port=6379&password=&db=0"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDangerousCheck:
    """危险操作检测测试"""

    def test_check_dangerous_sql(self, client):
        response = client.post(
            "/api/db-toolkit/check-dangerous-sql",
            json={"sql": "DROP TABLE users"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_dangerous" in data

    def test_check_dangerous_redis_command(self, client):
        response = client.post(
            "/api/db-toolkit/check-dangerous-redis",
            json={"command": "FLUSHALL"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_dangerous" in data


class TestDbToolkitValidation:
    """数据库工具包数据验证测试"""

    def test_mysql_query_request(self):
        from app.models.db_toolkit import MysqlQueryRequest
        req = MysqlQueryRequest(
            account_alias="test-server",
            container_id="mysql-container",
            connection={
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "password",
                "database": "mydb",
            },
            sql="SELECT * FROM users",
        )
        assert req.account_alias == "test-server"
        assert req.sql == "SELECT * FROM users"

    def test_redis_scan_request(self):
        from app.models.db_toolkit import RedisScanRequest
        req = RedisScanRequest(
            account_alias="test-server",
            container_id="redis-container",
            connection={
                "host": "localhost",
                "port": 6379,
                "password": "",
                "db": 0,
            },
            pattern="user:*",
            count=10,
            cursor=0,
        )
        assert req.pattern == "user:*"
        assert req.count == 10
