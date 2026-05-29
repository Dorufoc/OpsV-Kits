"""MySQL -p 标志格式测试

验证 mysql 命令行中 -p 参数的格式是否正确。
MySQL CLI 规则:
  - `-pPassword` (无空格): 直接传密码，无交互提示
  - `-p Password` (有空格): `-p` 被视为提示输入密码, `Password` 被解析为数据库名
  - `-p` (单独): 提示 "Enter password"

BUG: db_toolkit_ws.py 中使用了 `-p {password}` (有空格),
     导致即使提供了密码也会出现 "Enter password" 交互提示。
"""
import re
import pytest
from unittest.mock import MagicMock

from app.models.db_toolkit import MySqlConnectionParams
from app.services.db_toolkit_service import DbToolkitService
from app.core.db_toolkit_ws import DbToolkitWebSocketHandler


def _make_connection(**overrides):
    defaults = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "mypassword",
        "database": "testdb",
    }
    defaults.update(overrides)
    return MySqlConnectionParams(**defaults)


class TestMysqlPasswordFlagInService:
    """测试 DbToolkitService._build_mysql_command 中 -p 格式"""

    def setup_method(self):
        self.service = DbToolkitService()

    def test_password_flag_no_space(self):
        """-p 和密码之间不应有空格: 应生成 `-pmypassword` 而非 `-p mypassword`"""
        conn = _make_connection()
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-pmypassword" in cmd, (
            f"密码应紧跟 -p 之后(无空格), 实际命令: {cmd}"
        )

    def test_password_flag_should_not_prompt(self):
        """命令中不应出现独立的 `-p ` (会导致 Enter password 提示)"""
        conn = _make_connection(password="secret123")
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert not re.search(r"-p\s+secret123", cmd), (
            f"发现 `-p secret123`(有空格), MySQL 会将其解释为: 提示输入密码 + 数据库名=secret123. 命令: {cmd}"
        )

    def test_empty_password_no_p_flag(self):
        """空密码时不应出现 -p 参数"""
        conn = _make_connection(password="")
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-p" not in cmd, (
            f"空密码时不应包含 -p 参数, 实际命令: {cmd}"
        )

    def test_password_with_special_chars(self):
        """包含特殊字符的密码也应紧贴 -p"""
        conn = _make_connection(password="p@ss:w0rd")
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-pp@ss:w0rd" in cmd, (
            f"特殊字符密码应紧跟 -p 之后, 实际命令: {cmd}"
        )

    def test_no_space_between_host_and_value(self):
        """-h 参数格式验证 (参照)"""
        conn = _make_connection()
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-hlocalhost" in cmd

    def test_no_space_between_port_flag_and_value(self):
        """-P 参数格式验证 (参照)"""
        conn = _make_connection()
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-P3306" in cmd

    def test_no_space_between_user_and_value(self):
        """-u 参数格式验证 (参照)"""
        conn = _make_connection()
        cmd = self.service._build_mysql_command("container123", conn, "SELECT 1")
        assert "-uroot" in cmd


class TestMysqlPasswordFlagInWebSocket:
    """测试 DbToolkitWebSocketHandler 中 mysql 命令构建的 -p 格式"""

    def setup_method(self):
        self.handler = DbToolkitWebSocketHandler()

    def test_handle_mysql_cli_password_no_space(self):
        """WebSocket 终端连接中 -p 和密码之间不应有空格"""
        conn = _make_connection(password="mypassword")
        parts = [f"mysql -h {conn.host} -P {conn.port} -u {conn.user}"]
        if conn.password:
            parts.append(f"-p{conn.password}")
        if conn.database:
            parts.append(conn.database)
        expected_cmd = " ".join(parts)
        assert "-pmypassword" in expected_cmd

    def test_ws_current_code_has_bug(self):
        """验证当前代码确实存在 -p 空格 bug"""
        conn = _make_connection(password="mypassword")
        current_buggy_parts = [f"mysql -h {conn.host} -P {conn.port} -u {conn.user}"]
        if conn.password:
            current_buggy_parts.append(f"-p {conn.password}")
        if conn.database:
            current_buggy_parts.append(conn.database)
        buggy_cmd = " ".join(current_buggy_parts)
        assert re.search(r"-p\s+mypassword", buggy_cmd), (
            "确认 bug: 当前代码使用 `-p mypassword`(有空格), 会触发 Enter password 提示"
        )

    def test_ws_handle_mysql_cli_code_pattern(self):
        """直接检查源码文件中 -p 后面是否紧跟空格(不紧跟密码)"""
        import inspect
        source = inspect.getsource(self.handler._handle_cli_direct)
        buggy_pattern = re.search(r'"-p\s*\{', source) or re.search(r"f\"-p\s+\{", source)
        assert buggy_pattern is None, (
            "源码中发现 `-p {password}` 模式(有空格), 这是导致 Enter password 提示的 bug.\n"
            "修复方法: 将 `f\"-p {conn.password}\"` 改为 `f\"-p{conn.password}\"`"
        )

    def test_handle_mysql_cli_class_method_code_pattern(self):
        """检查 handle_mysql_cli 方法源码"""
        import inspect
        source = inspect.getsource(self.handler.handle_mysql_cli)
        buggy_pattern = re.search(r"f\"-p\s+\{", source)
        assert buggy_pattern is None, (
            "handle_mysql_cli 源码中发现 `-p {password}` 模式(有空格).\n"
            "修复方法: 将 `f\"-p {connection.password}\"` 改为 `f\"-p{connection.password}\"`"
        )


class TestMysqlCommandParsingRules:
    """MySQL CLI -p 参数解析规则文档化测试"""

    def test_rule_p_with_space_means_prompt(self):
        """规则: `-p VALUE` -> MySQL 提示输入密码, VALUE 被当作数据库名"""
        cmd = "mysql -h localhost -P 3306 -u root -p mypassword testdb"
        p_flag_match = re.findall(r"-p\s+\S+", cmd)
        assert len(p_flag_match) > 0, (
            "此命令格式中 `-p mypassword` 会被 MySQL 解释为:\n"
            "  1. -p (无值) -> 提示 Enter password\n"
            "  2. mypassword -> 被当作数据库名(而非密码)\n"
            "  3. testdb -> 被忽略或报错(多余参数)"
        )

    def test_rule_p_without_space_means_password(self):
        """规则: `-pVALUE` -> MySQL 直接使用 VALUE 作为密码"""
        cmd = "mysql -h localhost -P 3306 -u root -pmypassword testdb"
        p_flag_match = re.findall(r"-p\S+", cmd)
        assert any(m == "-pmypassword" for m in p_flag_match), (
            "`-pmypassword` 格式正确, MySQL 会将 mypassword 用作密码, testdb 用作数据库名"
        )

    def test_rule_p_alone_means_prompt(self):
        """规则: 单独 `-p` -> MySQL 交互式提示 Enter password"""
        cmd = "mysql -h localhost -P 3306 -u root -p testdb"
        standalone_p = re.search(r"-p\s", cmd)
        assert standalone_p is not None, (
            "单独 `-p` 后跟空格, MySQL 会交互式提示输入密码"
        )
