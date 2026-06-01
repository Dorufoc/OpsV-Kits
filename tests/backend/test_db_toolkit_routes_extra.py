from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.db_toolkit import DbToolkitError, DetectResult


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_svc():
    with patch("app.api.routes.db_toolkit.db_toolkit_service") as m:
        yield m


@pytest.fixture
def mock_ssh():
    with patch("app.api.routes.db_toolkit.ssh_account_service") as m:
        m.get_account.return_value = {"alias": "srv1"}
        yield m


class TestVerifyAccountNotFound:
    def test_detect_mysql_account_not_found(self, client, mock_svc, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/db-toolkit/detect/mysql", params={"account_alias": "missing"})
        assert resp.status_code == 404

    def test_detect_redis_account_not_found(self, client, mock_svc, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.get("/api/db-toolkit/detect/redis", params={"account_alias": "missing"})
        assert resp.status_code == 404

    def test_mysql_query_account_not_found(self, client, mock_svc, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post("/api/db-toolkit/mysql/query", json={
            "account_alias": "missing",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "sql": "SELECT 1",
        })
        assert resp.status_code == 404

    def test_redis_scan_account_not_found(self, client, mock_svc, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.post("/api/db-toolkit/redis/scan", json={
            "account_alias": "missing",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "pattern": "*",
        })
        assert resp.status_code == 404


class TestDetectMysqlClient:
    def test_detect_mysql_success(self, client, mock_svc, mock_ssh):
        mock_svc.detect_mysql_client.return_value = DetectResult(installed=True, path="/usr/bin/mysql", client_version="8.0")
        resp = client.get("/api/db-toolkit/detect/mysql", params={"account_alias": "srv1"})
        assert resp.status_code == 200
        assert resp.json()["installed"] is True

    def test_detect_mysql_with_container(self, client, mock_svc, mock_ssh):
        mock_svc.detect_mysql_client.return_value = DetectResult(installed=False, path="", client_version="")
        resp = client.get("/api/db-toolkit/detect/mysql", params={"account_alias": "srv1", "container_id": "ctr1"})
        assert resp.status_code == 200
        assert resp.json()["installed"] is False


class TestMysqlQueryDbToolkitError:
    def test_mysql_query_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.execute_mysql_query.side_effect = DbToolkitError("DB_TOOLKIT_4221", "query failed")
        resp = client.post("/api/db-toolkit/mysql/query", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "sql": "BAD SQL",
        })
        assert resp.status_code == 422


class TestMysqlTablesDbToolkitError:
    def test_mysql_tables_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.get_mysql_tables.side_effect = DbToolkitError("DB_TOOLKIT_5041", "timeout")
        resp = client.post("/api/db-toolkit/mysql/tables", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
        })
        assert resp.status_code == 504


class TestMysqlTableStructureDbToolkitError:
    def test_table_structure_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.get_mysql_table_structure.side_effect = DbToolkitError("DB_TOOLKIT_4002", "bad request")
        resp = client.post("/api/db-toolkit/mysql/table-structure", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "table_name": "nonexistent",
        })
        assert resp.status_code == 400


class TestRedisScanDbToolkitError:
    def test_redis_scan_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.scan_redis_keys.side_effect = DbToolkitError("DB_TOOLKIT_4221", "invalid cursor")
        resp = client.post("/api/db-toolkit/redis/scan", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "pattern": "*",
        })
        assert resp.status_code == 422


class TestRedisKeyInfoDbToolkitError:
    def test_redis_key_info_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.get_redis_key_info.side_effect = DbToolkitError("DB_TOOLKIT_5041", "timeout")
        resp = client.post("/api/db-toolkit/redis/key-info", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "key": "test",
        })
        assert resp.status_code == 504


class TestRedisDbStatsDbToolkitError:
    def test_redis_db_stats_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.get_redis_db_stats.side_effect = DbToolkitError("DB_TOOLKIT_4002", "bad params")
        resp = client.post("/api/db-toolkit/redis/db-stats", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
        })
        assert resp.status_code == 400


class TestDeleteRedisKeyDbToolkitError:
    def test_delete_redis_key_toolkit_error(self, client, mock_svc, mock_ssh):
        mock_svc.delete_redis_key.side_effect = DbToolkitError("DB_TOOLKIT_5041", "timeout")
        resp = client.request("DELETE", "/api/db-toolkit/redis/key", params={
            "account_alias": "srv1", "key": "test",
        })
        assert resp.status_code == 504

    def test_delete_redis_key_account_not_found(self, client, mock_svc, mock_ssh):
        mock_ssh.get_account.return_value = None
        resp = client.request("DELETE", "/api/db-toolkit/redis/key", params={
            "account_alias": "missing", "key": "test",
        })
        assert resp.status_code == 404


class TestMysqlTableStructureSuccess:
    def test_table_structure_success(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import MysqlTableStructure
        mock_svc.get_mysql_table_structure.return_value = MysqlTableStructure(table_name="users")
        resp = client.post("/api/db-toolkit/mysql/table-structure", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "table_name": "users",
        })
        assert resp.status_code == 200
        assert resp.json()["table_name"] == "users"


class TestRedisScanSuccess:
    def test_scan_success(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import RedisScanResult
        mock_svc.scan_redis_keys.return_value = RedisScanResult(keys=["k1", "k2"], next_cursor=0)
        resp = client.post("/api/db-toolkit/redis/scan", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "pattern": "*",
        })
        assert resp.status_code == 200
        assert len(resp.json()["keys"]) == 2


class TestRedisKeyInfoSuccess:
    def test_key_info_success(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import RedisKeyInfo
        mock_svc.get_redis_key_info.return_value = RedisKeyInfo(key="test", type="string", ttl=-1)
        resp = client.post("/api/db-toolkit/redis/key-info", json={
            "account_alias": "srv1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "key": "test",
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "string"
