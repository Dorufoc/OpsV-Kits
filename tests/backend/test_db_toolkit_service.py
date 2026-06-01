from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models.db_toolkit import (
    DbToolkitError,
    DetectResult,
    MySqlConnectionParams,
    RedisConnectionParams,
)
from app.services.db_toolkit_service import DbToolkitService


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
    return DbToolkitService()


class TestExecBytesOutput:
    def test_exec_in_container_bytes_stdout(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, b"output", b"err")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec_in_container("test", "abc", "ls")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)

    def test_exec_on_host_bytes_output(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.return_value = (0, b"host output", b"host err")
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        code, stdout, stderr = service._exec_on_host("test", "ls")
        assert isinstance(stdout, str)
        assert isinstance(stderr, str)


class TestCheckAccessible:
    def test_check_accessible_with_container(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        service._check_accessible("test", "abc123")

    def test_check_accessible_on_host(self, service, mock_ssh_account_service, mock_conn):
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        service._check_accessible("test", None)


class TestDetectMysqlClientCommonPaths:
    def test_detect_via_common_path(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (0, "", ""),
            (0, "mysql  Ver 8.0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is True
        assert result.path == "/usr/bin/mysql"

    def test_detect_apt_install_hint(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (0, "", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is False
        assert "apt-get" in result.error

    def test_detect_yum_install_hint(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (0, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is False
        assert "yum" in result.error

    def test_detect_apk_install_hint(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (0, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is False
        assert "apk" in result.error

    def test_detect_no_package_manager(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", None)
        assert result.installed is False
        assert "手动安装" in result.error

    def test_detect_container_install_hint(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
            (1, "", ""),
            (1, "", ""),
            (1, "", ""),
            (0, "", ""),
            (1, "", ""),
            (1, "", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_mysql_client("test", "container1")
        assert result.installed is False
        assert "容器内" in result.error


class TestDetectRedisClientContainer:
    def test_detect_in_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "/usr/bin/redis-cli\n", ""),
            (0, "redis-cli 7.0.0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_redis_client("test", "abc123")
        assert result.installed is True

    def test_detect_not_installed_container(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "", "not found"),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        result = service.detect_redis_client("test", "abc123")
        assert result.installed is False
        assert "容器内" in result.error


class TestBuildMysqlCommandNoBatch:
    def test_no_batch_mode(self, service):
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", password="pw", database="db")
        cmd = service._build_mysql_command(None, conn, "SELECT 1", batch=False)
        assert "--batch" not in cmd
        assert "--raw" not in cmd

    def test_batch_mode_default(self, service):
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", password="pw", database="db")
        cmd = service._build_mysql_command(None, conn, "SELECT 1")
        assert "--batch" in cmd
        assert "--raw" in cmd


class TestBuildRedisCliCommandNoPassword:
    def test_no_password(self, service):
        conn = RedisConnectionParams(host="localhost", port=6379, password="", db=0)
        cmd = service._build_redis_cli_command(None, conn, "GET", "key")
        assert "-a" not in cmd
        assert "-n 0" in cmd


class TestExecuteMysqlQueryTruncation:
    def test_result_truncated(self, service, mock_ssh_account_service, mock_conn):
        rows = "\n".join(["col1\tcol2"] + [f"val{i}\tval{i}" for i in range(1001)])
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, rows, ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        result = service.execute_mysql_query("test", None, conn, "SELECT * FROM t")
        assert result.truncated is True
        assert len(result.rows) == 1000
        assert result.total_count == 1000

    def test_error_uses_stdout(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (1, "error in stdout", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root")
        result = service.execute_mysql_query("test", None, conn, "BAD SQL")
        assert result.error == "error in stdout"

    def test_no_password_safe_cmd(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "col1\nval1\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", password="")
        result = service.execute_mysql_query("test", None, conn, "SELECT 1")
        assert result.columns == ["col1"]


class TestGetMysqlTableStructure:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        desc_output = "Field\tType\tNull\tKey\tDefault\tExtra\nid\tint\tNO\tPRI\tNULL\tauto_increment\nname\tvarchar(50)\tYES\t\tNULL\t\n"
        idx_output = "Table\tNon_unique\tKey_name\tSeq_in_index\tColumn_name\tCollation\nusers\t0\tPRIMARY\t1\tid\tA\nusers\t1\tidx_name\t1\tname\tA\n"
        count_output = "COUNT(*)\n100\n"
        ddl_output = "Table\tCreate Table\nusers\tCREATE TABLE users (id int, name varchar(50))\n"
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, desc_output, ""),
            (0, idx_output, ""),
            (0, count_output, ""),
            (0, ddl_output, ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", database="mydb")
        result = service.get_mysql_table_structure("test", None, conn, "users")
        assert result.table_name == "users"
        assert len(result.columns) >= 1
        assert result.columns[0].field == "id"
        assert result.columns[0].key == "PRI"
        assert len(result.indexes) == 2
        assert result.indexes[0].name == "PRIMARY"
        assert result.indexes[0].unique is True
        assert result.indexes[1].name == "idx_name"
        assert result.indexes[1].unique is False
        assert result.row_count == 100
        assert "CREATE TABLE" in result.create_ddl

    def test_empty_structure(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "Field\tType\tNull\tKey\tDefault\tExtra\n", ""),
            (0, "Table\tNon_unique\tKey_name\tSeq_in_index\tColumn_name\n", ""),
            (0, "COUNT(*)\n0\n", ""),
            (0, "Table\tCreate Table\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", database="mydb")
        result = service.get_mysql_table_structure("test", None, conn, "empty_table")
        assert len(result.columns) == 0
        assert len(result.indexes) == 0
        assert result.row_count == 0
        assert result.create_ddl == ""

    def test_invalid_count(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "Field\tType\tNull\tKey\tDefault\tExtra\n", ""),
            (0, "Table\tNon_unique\tKey_name\tSeq_in_index\tColumn_name\n", ""),
            (0, "COUNT(*)\nnot_a_number\n", ""),
            (0, "Table\tCreate Table\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = MySqlConnectionParams(host="localhost", port=3306, user="root", database="mydb")
        result = service.get_mysql_table_structure("test", None, conn, "t")
        assert result.row_count == 0


class TestScanRedisKeysWithMore:
    def test_has_more(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "42\nkey1\nkey2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.scan_redis_keys("test", None, conn)
        assert result.has_more is True
        assert result.next_cursor == 42

    def test_warning_lines_filtered(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "0\nWarning: Using a password\nkey1\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.scan_redis_keys("test", None, conn)
        assert len(result.keys) == 1
        assert result.keys[0] == "key1"

    def test_empty_result(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.scan_redis_keys("test", None, conn)
        assert result.keys == []
        assert result.has_more is False

    def test_invalid_cursor(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "invalid\nkey1\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.scan_redis_keys("test", None, conn)
        assert result.next_cursor == 0
        assert result.has_more is False


class TestGetRedisKeyInfo:
    def test_string_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "string\n", ""),
            (0, "3600\n", ""),
            (0, "hello world\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "mykey")
        assert result.type == "string"
        assert result.value == "hello world"
        assert result.ttl == 3600
        assert result.truncated is False

    def test_string_type_truncated(self, service, mock_ssh_account_service, mock_conn):
        long_value = "x" * 2000
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "string\n", ""),
            (0, "3600\n", ""),
            (0, long_value + "\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "bigkey")
        assert result.truncated is True
        assert len(result.value) == 1024

    def test_hash_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "hash\n", ""),
            (0, "3600\n", ""),
            (0, "field1\nvalue1\nfield2\nvalue2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "myhash")
        assert result.type == "hash"
        assert result.value == {"field1": "value1", "field2": "value2"}

    def test_list_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "list\n", ""),
            (0, "3600\n", ""),
            (0, "item1\nitem2\nitem3\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "mylist")
        assert result.type == "list"
        assert result.value == ["item1", "item2", "item3"]

    def test_set_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "set\n", ""),
            (0, "3600\n", ""),
            (0, "member1\nmember2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "myset")
        assert result.type == "set"
        assert result.value == ["member1", "member2"]

    def test_zset_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "zset\n", ""),
            (0, "3600\n", ""),
            (0, "member1\n1.0\nmember2\n2.0\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "myzset")
        assert result.type == "zset"
        assert len(result.value) == 2
        assert result.value[0] == {"member": "member1", "score": "1.0"}

    def test_stream_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "stream\n", ""),
            (0, "3600\n", ""),
            (0, "stream-data\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "mystream")
        assert result.type == "stream"
        assert result.value == "stream-data"

    def test_unsupported_type(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "unknown_type\n", ""),
            (0, "-2\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "mykey")
        assert result.type == "unknown_type"
        assert "不支持的类型" in result.value

    def test_invalid_ttl(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "string\n", ""),
            (0, "not_a_number\n", ""),
            (0, "value\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "mykey")
        assert result.ttl == -2

    def test_non_string_truncated(self, service, mock_ssh_account_service, mock_conn):
        long_value = "x" * 2000
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "list\n", ""),
            (0, "3600\n", ""),
            (0, long_value + "\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_key_info("test", None, conn, "biglist")
        assert result.truncated is True


class TestGetRedisDbStats:
    def test_success(self, service, mock_ssh_account_service, mock_conn):
        info_output = "# Memory\nused_memory:1048576\nused_memory_human:1.00M\n"
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "42\n", ""),
            (0, info_output, ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_db_stats("test", None, conn)
        assert result.key_count == 42
        assert result.used_memory_human == "1.00M"
        assert result.used_memory_bytes == 1048576

    def test_invalid_dbsize(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "not_a_number\n", ""),
            (0, "# Memory\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_db_stats("test", None, conn)
        assert result.key_count == 0

    def test_invalid_memory_bytes(self, service, mock_ssh_account_service, mock_conn):
        info_output = "# Memory\nused_memory:not_a_number\nused_memory_human:1.00M\n"
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "10\n", ""),
            (0, info_output, ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379)
        result = service.get_redis_db_stats("test", None, conn)
        assert result.used_memory_bytes == 0


class TestDeleteRedisKeyWithPassword:
    def test_safe_cmd_with_password(self, service, mock_ssh_account_service, mock_conn):
        mock_conn.manager.exec_command.side_effect = [
            (0, "check\n", ""),
            (0, "1\n", ""),
        ]
        mock_ssh_account_service.pool.get_connection.return_value = mock_conn
        mock_ssh_account_service.pool.release_connection = MagicMock()
        conn = RedisConnectionParams(host="localhost", port=6379, password="secret")
        result = service.delete_redis_key("test", None, conn, "mykey")
        assert result is True


class TestCheckDangerousSqlEdgeCases:
    def test_drop_schema(self):
        result = DbToolkitService.check_dangerous_sql("DROP SCHEMA mydb")
        assert result.is_dangerous is True
        assert result.level == "critical"

    def test_truncate_no_table_keyword(self):
        result = DbToolkitService.check_dangerous_sql("TRUNCATE TABLE users")
        assert result.is_dangerous is True

    def test_sql_with_line_comments(self):
        result = DbToolkitService.check_dangerous_sql("-- comment\nDROP TABLE users")
        assert result.is_dangerous is True

    def test_sql_with_block_comments(self):
        result = DbToolkitService.check_dangerous_sql("/* block */ UPDATE users SET x = 1")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_alter_table_drop_column(self):
        result = DbToolkitService.check_dangerous_sql("ALTER TABLE users DROP COLUMN age")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_safe_insert(self):
        result = DbToolkitService.check_dangerous_sql("INSERT INTO users (name) VALUES ('test')")
        assert result.is_dangerous is False

    def test_empty_sql(self):
        result = DbToolkitService.check_dangerous_sql("")
        assert result.is_dangerous is False


class TestCheckDangerousRedisCommandEdgeCases:
    def test_flushall_lowercase(self):
        result = DbToolkitService.check_dangerous_redis_command("flushall")
        assert result.is_dangerous is True
        assert result.level == "critical"

    def test_flushdb_lowercase(self):
        result = DbToolkitService.check_dangerous_redis_command("flushdb")
        assert result.is_dangerous is True
        assert result.level == "critical"

    def test_config_set_lowercase(self):
        result = DbToolkitService.check_dangerous_redis_command("config set maxmemory 0")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_debug_lowercase(self):
        result = DbToolkitService.check_dangerous_redis_command("debug segfault")
        assert result.is_dangerous is True
        assert result.level == "warning"

    def test_safe_set(self):
        result = DbToolkitService.check_dangerous_redis_command("SET key value")
        assert result.is_dangerous is False

    def test_empty_command(self):
        result = DbToolkitService.check_dangerous_redis_command("")
        assert result.is_dangerous is False


class TestFormatTtlEdgeCases:
    def test_days_only(self):
        result = DbToolkitService._format_ttl(86400)
        assert "1天" in result

    def test_hours_only(self):
        result = DbToolkitService._format_ttl(3600)
        assert "1小时" in result

    def test_minutes_only(self):
        result = DbToolkitService._format_ttl(60)
        assert "1分" in result

    def test_complex_duration(self):
        result = DbToolkitService._format_ttl(90061)
        assert "1天" in result
        assert "1小时" in result
        assert "1分" in result
        assert "1秒" in result


class TestParseTsvEdgeCases:
    def test_multiple_empty_rows(self, service):
        stdout = "col1\tcol2\n\nval1\tval2\n\n"
        cols, rows = service._parse_tsv(stdout)
        assert cols == ["col1", "col2"]
        assert len(rows) == 1

    def test_null_values(self, service):
        stdout = "col1\tcol2\nNULL\tNULL\nval\tNULL\n"
        cols, rows = service._parse_tsv(stdout)
        assert rows[0] == [None, None]
        assert rows[1] == ["val", None]
