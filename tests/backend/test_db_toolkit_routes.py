from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.db_toolkit import DbToolkitError


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


class TestMysqlCliWsContainer:
    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_ws_missing_account_alias(self, mock_handler, client, mock_ssh):
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli/ctr123") as ws:
            ws.send_text(json.dumps({"connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"}}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_ws_success(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock()
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli/ctr123") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            }))

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_ws_exception(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock(side_effect=RuntimeError("conn failed"))
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli/ctr123") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            }))
            data = ws.receive_json()
            assert data["type"] == "error"


class TestMysqlCliHostWs:
    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_host_ws_missing_account_alias(self, mock_handler, client, mock_ssh):
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli") as ws:
            ws.send_text(json.dumps({"connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"}}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_host_ws_with_container_id(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock()
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
                "container_id": "ctr456",
            }))

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_mysql_cli_host_ws_without_container_id(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock()
        with client.websocket_connect("/api/db-toolkit/ws/mysql-cli") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            }))


class TestRedisCliWsContainer:
    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_redis_cli_ws_missing_account_alias(self, mock_handler, client, mock_ssh):
        with client.websocket_connect("/api/db-toolkit/ws/redis-cli/ctr123") as ws:
            ws.send_text(json.dumps({"connection": {"host": "localhost", "port": 6379, "password": "", "db": 0}}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_redis_cli_ws_success(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock()
        with client.websocket_connect("/api/db-toolkit/ws/redis-cli/ctr123") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            }))


class TestRedisCliHostWs:
    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_redis_cli_host_ws_missing_account_alias(self, mock_handler, client, mock_ssh):
        with client.websocket_connect("/api/db-toolkit/ws/redis-cli") as ws:
            ws.send_text(json.dumps({"connection": {"host": "localhost", "port": 6379, "password": "", "db": 0}}))
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "account_alias" in data["message"]

    @patch("app.core.db_toolkit_ws.db_toolkit_ws_handler")
    def test_redis_cli_host_ws_with_container_id(self, mock_handler, client, mock_ssh):
        mock_handler._handle_cli_direct = AsyncMock()
        with client.websocket_connect("/api/db-toolkit/ws/redis-cli") as ws:
            ws.send_text(json.dumps({
                "account_alias": "srv1",
                "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
                "container_id": "ctr789",
            }))


class TestDetectRedisWithContainer:
    def test_detect_redis_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import DetectResult
        mock_svc.detect_redis_client.return_value = DetectResult(installed=True, path="/usr/bin/redis-cli", client_version="7.0")
        resp = client.get("/api/db-toolkit/detect/redis", params={"account_alias": "srv1", "container_id": "abc123"})
        assert resp.status_code == 200
        assert resp.json()["installed"] is True


class TestExecuteMysqlQueryWithContainer:
    def test_query_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import MysqlQueryResult
        mock_svc.execute_mysql_query.return_value = MysqlQueryResult(
            columns=["id"], rows=[["1"]], total_count=1,
        )
        resp = client.post("/api/db-toolkit/mysql/query", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "sql": "SELECT 1",
        })
        assert resp.status_code == 200


class TestGetMysqlTablesWithContainer:
    def test_tables_with_container_id(self, client, mock_svc, mock_ssh):
        mock_svc.get_mysql_tables.return_value = ["users"]
        resp = client.post("/api/db-toolkit/mysql/tables", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
        })
        assert resp.status_code == 200


class TestGetMysqlTableStructureWithContainer:
    def test_structure_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import MysqlTableStructure
        mock_svc.get_mysql_table_structure.return_value = MysqlTableStructure(table_name="users")
        resp = client.post("/api/db-toolkit/mysql/table-structure", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "test"},
            "table_name": "users",
        })
        assert resp.status_code == 200


class TestScanRedisKeysWithContainer:
    def test_scan_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import RedisScanResult
        mock_svc.scan_redis_keys.return_value = RedisScanResult(keys=["k1"], next_cursor=0)
        resp = client.post("/api/db-toolkit/redis/scan", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "pattern": "*",
        })
        assert resp.status_code == 200


class TestGetRedisKeyInfoWithContainer:
    def test_key_info_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import RedisKeyInfo
        mock_svc.get_redis_key_info.return_value = RedisKeyInfo(key="test", type="string", ttl=-1)
        resp = client.post("/api/db-toolkit/redis/key-info", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
            "key": "test",
        })
        assert resp.status_code == 200


class TestGetRedisDbStatsWithContainer:
    def test_db_stats_with_container_id(self, client, mock_svc, mock_ssh):
        from app.models.db_toolkit import RedisDbStats
        mock_svc.get_redis_db_stats.return_value = RedisDbStats(key_count=50, used_memory_human="5MB", used_memory_bytes=5242880)
        resp = client.post("/api/db-toolkit/redis/db-stats", json={
            "account_alias": "srv1",
            "container_id": "ctr1",
            "connection": {"host": "localhost", "port": 6379, "password": "", "db": 0},
        })
        assert resp.status_code == 200


class TestDeleteRedisKeyWithContainer:
    def test_delete_with_container_id(self, client, mock_svc, mock_ssh):
        mock_svc.delete_redis_key.return_value = True
        resp = client.request("DELETE", "/api/db-toolkit/redis/key", params={
            "account_alias": "srv1", "container_id": "ctr1", "key": "test",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_delete_returns_false(self, client, mock_svc, mock_ssh):
        mock_svc.delete_redis_key.return_value = False
        resp = client.request("DELETE", "/api/db-toolkit/redis/key", params={
            "account_alias": "srv1", "key": "nonexistent",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestHandleToolkitErrorBranches:
    def test_handle_toolkit_error_422(self):
        from app.api.routes.db_toolkit import _handle_toolkit_error
        from fastapi import HTTPException
        err = DbToolkitError("DB_TOOLKIT_4221", "unprocessable")
        with pytest.raises(HTTPException) as exc_info:
            _handle_toolkit_error(err)
        assert exc_info.value.status_code == 422

    def test_handle_toolkit_error_504(self):
        from app.api.routes.db_toolkit import _handle_toolkit_error
        from fastapi import HTTPException
        err = DbToolkitError("DB_TOOLKIT_5041", "timeout")
        with pytest.raises(HTTPException) as exc_info:
            _handle_toolkit_error(err)
        assert exc_info.value.status_code == 504

    def test_handle_toolkit_error_4002(self):
        from app.api.routes.db_toolkit import _handle_toolkit_error
        from fastapi import HTTPException
        err = DbToolkitError("DB_TOOLKIT_4002", "bad request")
        with pytest.raises(HTTPException) as exc_info:
            _handle_toolkit_error(err)
        assert exc_info.value.status_code == 400


class TestCheckDangerousSqlEdgeCases:
    def test_check_dangerous_sql_empty(self, client, mock_svc):
        from app.models.db_toolkit import DangerousCheckResult
        mock_svc.check_dangerous_sql.return_value = DangerousCheckResult(is_dangerous=False)
        resp = client.post("/api/db-toolkit/check-dangerous-sql", json={"sql": ""})
        assert resp.status_code == 200


class TestCheckDangerousRedisEdgeCases:
    def test_check_dangerous_redis_empty(self, client, mock_svc):
        from app.models.db_toolkit import DangerousCheckResult
        mock_svc.check_dangerous_redis_command.return_value = DangerousCheckResult(is_dangerous=False)
        resp = client.post("/api/db-toolkit/check-dangerous-redis", json={"command": ""})
        assert resp.status_code == 200
