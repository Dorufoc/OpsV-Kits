from unittest.mock import MagicMock, patch

import pytest

from app.models.db_toolkit import (
    DangerousCheckResult,
    DbToolkitError,
    DetectResult,
    MySqlConnectionParams,
    RedisConnectionParams,
)


@pytest.fixture
def mock_ssh_account_service():
    with patch("app.services.db_toolkit_service.ssh_account_service") as mock_svc:
        account = MagicMock()
        account.alias = "test"
        mock_svc.get_account.return_value = account
        mock_pool = MagicMock()
        mock_svc.pool = mock_pool
        yield mock_svc


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.manager.exec_command.return_value = (0, "ok", "")
    return conn


@pytest.fixture
def service():
    from app.services.db_toolkit_service import DbToolkitService

    return DbToolkitService()


class TestDbToolkitServiceGetConnection:
    def test_get_connection_success(self, service, mock_ssh_account_service):
        account = MagicMock()
        mock_ssh_account_service.get_account.return_value = account
        result = service._get_connection("test")
        mock_ssh_account_service.pool.get_connection.assert_called_with(account)

    def test_get_connection_nonexistent(self, service, mock_ssh_account_service):
        mock_ssh_account_service.get_account.return_value = None
        with pytest.raises(ValueError, match="不存在"):
            service._get_connection("nonexistent")


class TestDbToolkitServiceExec:
    def test_exec_in_container(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec_in_container("test", "abc123", "ls")
        assert code == 0
        mock_ssh_account_service.pool.release_connection.assert_called_once()

    def test_exec_on_host(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec_on_host("test", "ls")
        assert code == 0
        mock_ssh_account_service.pool.release_connection.assert_called_once()

    def test_exec_with_container(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec("test", "abc123", "ls")
        assert code == 0

    def test_exec_without_container(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec("test", None, "ls")
        assert code == 0


class TestDbToolkitServiceCheckAccessible:
    def test_check_container_running(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        service._check_container_running("test", "abc123")

    def test_check_container_not_running(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        with pytest.raises(DbToolkitError, match="未运行"):
            service._check_container_running("test", "abc123")

    def test_check_host_accessible(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        service._check_host_accessible("test")

    def test_check_host_not_accessible(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (1, "", "error")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        with pytest.raises(DbToolkitError, match="主机不可访问"):
            service._check_host_accessible("test")


class TestDetectMysqlClient:
    def test_detect_installed(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "/usr/bin/mysql\n", ""),
            (0, "mysql  Ver 8.0.33\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is True
        assert result.path == "/usr/bin/mysql"

    def test_detect_not_installed(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", "not found"),
            (1, "", "not found"),
            (1, "", "not found"),
            (1, "", "not found"),
            (1, "", "not found"),
            (1, "", "not found"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is False

    def test_detect_in_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "/usr/bin/mysql\n", ""),
            (0, "mysql  Ver 8.0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", "abc123")
        assert result.installed is True


class TestDetectRedisClient:
    def test_detect_installed(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "/usr/bin/redis-cli\n", ""),
            (0, "redis-cli 7.0.0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_redis_client("test", None)
        assert result.installed is True

    def test_detect_not_installed(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_redis_client("test", None)
        assert result.installed is False


class TestCheckDangerousSql:
    def test_drop_table(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("DROP TABLE users")
        assert result.is_dangerous is True
        assert result.level == "critical"

    def test_drop_database(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("DROP DATABASE mydb")
        assert result.is_dangerous is True

    def test_truncate(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("TRUNCATE TABLE users")
        assert result.is_dangerous is True

    def test_delete_no_where(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("DELETE FROM users")
        assert result.is_dangerous is True

    def test_delete_with_where(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("DELETE FROM users WHERE id = 1")
        assert result.is_dangerous is False

    def test_update_no_where(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("UPDATE users SET name = 'a'")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_update_with_where(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("UPDATE users SET name = 'a' WHERE id = 1")
        assert result.is_dangerous is False

    def test_alter_table_drop(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("ALTER TABLE users DROP COLUMN age")
        assert result.is_dangerous is True

    def test_safe_select(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("SELECT * FROM users")
        assert result.is_dangerous is False

    def test_sql_with_comments(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_sql("/* comment */ DROP TABLE users")
        assert result.is_dangerous is True


class TestCheckDangerousRedisCommand:
    def test_flushall(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_redis_command("FLUSHALL")
        assert result.is_dangerous is True
        assert result.level == "critical"

    def test_flushdb(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_redis_command("FLUSHDB")
        assert result.is_dangerous is True

    def test_config_set(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_redis_command("CONFIG SET maxmemory 0")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_debug(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_redis_command("DEBUG SEGFAULT")
        assert result.is_dangerous is True

    def test_safe_get(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService.check_dangerous_redis_command("GET mykey")
        assert result.is_dangerous is False


class TestBuildMysqlCommand:
    def test_basic_command(self, service):
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", password="secret", database="mydb")
        cmd = service._build_mysql_command(None, conn, "SELECT 1")
        assert "mysql" in cmd
        assert "-hlocalhost" in cmd
        assert "-P3306" in cmd
        assert "-uroot" in cmd
        assert "-psecret" in cmd
        assert "mydb" in cmd

    def test_no_password(self, service):
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        cmd = service._build_mysql_command(None, conn, "SELECT 1")
        assert "-p" not in cmd

    def test_no_database(self, service):
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", database="")
        cmd = service._build_mysql_command(None, conn, "SELECT 1")
        assert "mydb" not in cmd


class TestBuildRedisCliCommand:
    def test_basic_command(self, service):
        conn = RedisConnectionParams(host="localhost", port=6379, password="secret", db=1)
        cmd = service._build_redis_cli_command(None, conn, "GET", "mykey")
        assert "redis-cli" in cmd
        assert "-h localhost" in cmd
        assert "-p 6379" in cmd
        assert "-a secret" in cmd
        assert "-n 1" in cmd


class TestParseTsv:
    def test_parse_normal(self, service):
        stdout = "col1\tcol2\nval1\tval2\nval3\tNULL\n"
        cols, rows = service._parse_tsv(stdout)
        assert cols == ["col1", "col2"]
        assert len(rows) == 2
        assert rows[0] == ["val1", "val2"]
        assert rows[1][1] is None

    def test_parse_empty(self, service):
        cols, rows = service._parse_tsv("")
        assert cols == []
        assert rows == []

    def test_parse_header_only(self, service):
        cols, rows = service._parse_tsv("col1\tcol2\n")
        assert cols == ["col1", "col2"]
        assert rows == []


class TestFormatTtl:
    def test_never_expire(self):
        from app.services.db_toolkit_service import DbToolkitService

        assert DbToolkitService._format_ttl(-1) == "永不过期"

    def test_key_not_exist(self):
        from app.services.db_toolkit_service import DbToolkitService

        assert DbToolkitService._format_ttl(-2) == "Key 不存在"

    def test_negative_ttl(self):
        from app.services.db_toolkit_service import DbToolkitService

        assert DbToolkitService._format_ttl(-5) == "-5"

    def test_seconds_only(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService._format_ttl(30)
        assert "30秒" in result

    def test_days_hours_minutes(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService._format_ttl(86400 + 3600 + 60 + 5)
        assert "1天" in result
        assert "1小时" in result
        assert "1分" in result
        assert "5秒" in result

    def test_zero_ttl(self):
        from app.services.db_toolkit_service import DbToolkitService

        result = DbToolkitService._format_ttl(0)
        assert "0秒" in result


class TestExecuteMysqlQuery:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "col1\tcol2\nval1\tval2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        result = service.execute_mysql_query("test", None, conn, "SELECT 1")
        assert result.columns == ["col1", "col2"]
        assert len(result.rows) == 1

    def test_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "SQL error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        result = service.execute_mysql_query("test", None, conn, "BAD SQL")
        assert result.error != ""


class TestGetMysqlTables:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "Tables_in_mydb\nusers\norders\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", database="mydb")
        tables = service.get_mysql_tables("test", None, conn)
        assert "users" in tables
        assert "orders" in tables

    def test_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        with pytest.raises(DbToolkitError):
            service.get_mysql_tables("test", None, conn)


class TestScanRedisKeys:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "0\nkey1\nkey2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.scan_redis_keys("test", None, conn)
        assert len(result.keys) == 2
        assert result.has_more is False

    def test_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        with pytest.raises(DbToolkitError):
            service.scan_redis_keys("test", None, conn)


class TestDeleteRedisKey:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "1\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.delete_redis_key("test", None, conn, "mykey")
        assert result is True

    def test_failure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "error"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.delete_redis_key("test", None, conn, "mykey")
        assert result is False
