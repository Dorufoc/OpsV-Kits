from __future__ import annotations

import logging
import re
from typing import Any

from app.models.db_toolkit import (
    DangerousCheckResult,
    DetectResult,
    MysqlColumnDef,
    MysqlIndexDef,
    MysqlQueryResult,
    MysqlTableStructure,
    RedisDbStats,
    RedisKeyInfo,
    RedisScanResult,
)
from app.services.ssh_account_service import ssh_account_service

logger = logging.getLogger(__name__)

_MAX_ROWS = 1000
_MAX_VALUE_BYTES = 1024


class DbToolkitService:
    def _get_connection(self, account_alias: str):
        account = ssh_account_service.get_account(account_alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{account_alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec_in_container(
        self, account_alias: str, container_id: str, command: str, timeout: float = 30.0
    ) -> tuple[int, str, str]:
        conn = self._get_connection(account_alias)
        try:
            cmd = f"docker exec {container_id} {command}"
            exit_code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return exit_code, stdout, stderr
        finally:
            ssh_account_service.pool.release_connection(conn)

    def _check_container_running(self, account_alias: str, container_id: str) -> None:
        exit_code, stdout, _ = self._exec_in_container(
            account_alias, container_id, "echo check", timeout=5.0
        )
        if exit_code != 0:
            from app.models.db_toolkit import DbToolkitError
            raise DbToolkitError(
                "DB_TOOLKIT_5032",
                f"容器 '{container_id}' 未运行或不可访问",
            )

    def detect_mysql_client(
        self, account_alias: str, container_id: str
    ) -> DetectResult:
        # 尝试多种方式检测 MySQL 客户端
        # 1. 使用 which 命令
        exit_code, stdout, _ = self._exec_in_container(
            account_alias, container_id, "which mysql", timeout=5.0
        )
        if exit_code == 0:
            path = stdout.strip()
            _, ver_out, _ = self._exec_in_container(
                account_alias, container_id, "mysql --version", timeout=5.0
            )
            return DetectResult(installed=True, path=path, client_version=ver_out.strip())
        
        # 2. 尝试常见路径
        common_paths = ["/usr/bin/mysql", "/usr/local/bin/mysql", "/bin/mysql"]
        for mysql_path in common_paths:
            exit_code, _, _ = self._exec_in_container(
                account_alias, container_id, f"test -x {mysql_path}", timeout=5.0
            )
            if exit_code == 0:
                _, ver_out, _ = self._exec_in_container(
                    account_alias, container_id, f"{mysql_path} --version", timeout=5.0
                )
                return DetectResult(
                    installed=True, 
                    path=mysql_path, 
                    client_version=ver_out.strip()
                )
        
        # 3. 检测容器包管理器类型，提供更精确的安装建议
        exit_code_apt, _, _ = self._exec_in_container(
            account_alias, container_id, "which apt-get", timeout=5.0
        )
        exit_code_yum, _, _ = self._exec_in_container(
            account_alias, container_id, "which yum", timeout=5.0
        )
        exit_code_apk, _, _ = self._exec_in_container(
            account_alias, container_id, "which apk", timeout=5.0
        )
        
        install_hint = ""
        if exit_code_apt == 0:
            install_hint = "请在容器内执行: apt-get update && apt-get install -y default-mysql-client"
        elif exit_code_yum == 0:
            install_hint = "请在容器内执行: yum install -y mysql"
        elif exit_code_apk == 0:
            install_hint = "请在容器内执行: apk add mysql-client"
        else:
            install_hint = "请使用包含 mysql 客户端的镜像，或在容器内手动安装 mysql 客户端"
        
        return DetectResult(
            installed=False,
            error=f"容器内未安装 MySQL 客户端。{install_hint}",
        )

    def detect_redis_client(
        self, account_alias: str, container_id: str
    ) -> DetectResult:
        exit_code, stdout, _ = self._exec_in_container(
            account_alias, container_id, "which redis-cli", timeout=5.0
        )
        if exit_code != 0:
            return DetectResult(
                installed=False,
                error="容器内未安装 Redis 客户端",
            )
        path = stdout.strip()
        _, ver_out, _ = self._exec_in_container(
            account_alias, container_id, "redis-cli --version", timeout=5.0
        )
        return DetectResult(installed=True, path=path, client_version=ver_out.strip())

    @staticmethod
    def check_dangerous_sql(sql: str) -> DangerousCheckResult:
        sql_upper = sql.strip().upper()
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql_upper)
        sql_no_comments = re.sub(r'--.*$', '', sql_no_comments, flags=re.MULTILINE)
        sql_clean = ' '.join(sql_no_comments.split())

        if re.search(r'\bDROP\s+(TABLE|DATABASE|SCHEMA)\b', sql_clean):
            return DangerousCheckResult(
                is_dangerous=True,
                reason="包含 DROP 操作，将删除数据且不可恢复",
                level="critical",
            )
        if re.search(r'\bTRUNCATE\s+TABLE?\b', sql_clean):
            return DangerousCheckResult(
                is_dangerous=True,
                reason="包含 TRUNCATE 操作，将清空表数据且不可恢复",
                level="critical",
            )
        if re.search(r'\bDELETE\s+FROM\b', sql_clean) and 'WHERE' not in sql_clean:
            return DangerousCheckResult(
                is_dangerous=True,
                reason="DELETE 缺少 WHERE 子句，将删除表中所有数据",
                level="critical",
            )
        if re.search(r'\bUPDATE\b', sql_clean) and 'WHERE' not in sql_clean:
            return DangerousCheckResult(
                is_dangerous=True,
                reason="UPDATE 缺少 WHERE 子句，将更新表中所有行",
                level="warning",
            )
        if re.search(r'\bALTER\s+TABLE\b.*\bDROP\b', sql_clean):
            return DangerousCheckResult(
                is_dangerous=True,
                reason="ALTER TABLE DROP 将删除列且不可恢复",
                level="warning",
            )
        return DangerousCheckResult(is_dangerous=False)

    @staticmethod
    def check_dangerous_redis_command(cmd: str) -> DangerousCheckResult:
        cmd_upper = cmd.strip().upper()
        if 'FLUSHALL' in cmd_upper:
            return DangerousCheckResult(
                is_dangerous=True,
                reason="FLUSHALL 将删除所有数据库的所有 Key，不可恢复",
                level="critical",
            )
        if 'FLUSHDB' in cmd_upper:
            return DangerousCheckResult(
                is_dangerous=True,
                reason="FLUSHDB 将删除当前数据库的所有 Key，不可恢复",
                level="critical",
            )
        if re.search(r'\bCONFIG\s+SET\b', cmd_upper):
            return DangerousCheckResult(
                is_dangerous=True,
                reason="CONFIG SET 可能修改 Redis 运行配置，影响服务稳定性",
                level="warning",
            )
        if 'DEBUG' in cmd_upper:
            return DangerousCheckResult(
                is_dangerous=True,
                reason="DEBUG 命令为调试专用，可能影响服务稳定性",
                level="warning",
            )
        return DangerousCheckResult(is_dangerous=False)

    def _build_mysql_command(
        self, container_id: str, connection: Any, sql: str, *, batch: bool = True
    ) -> str:
        parts = [f"mysql -h{connection.host} -P{connection.port} -u{connection.user}"]
        if connection.password:
            parts.append(f"-p{connection.password}")
        if connection.database:
            parts.append(connection.database)
        if batch:
            parts.extend(['-e', f'"{sql}"', "--batch", "--raw"])
        return " ".join(parts)

    def _build_redis_cli_command(
        self, container_id: str, connection: Any, *redis_args: str
    ) -> str:
        parts = [f"redis-cli -h {connection.host} -p {connection.port}"]
        if connection.password:
            parts.append(f"-a {connection.password}")
        parts.append(f"-n {connection.db}")
        parts.extend(redis_args)
        return " ".join(parts)

    @staticmethod
    def _parse_tsv(stdout: str) -> tuple[list[str], list[list[str]]]:
        lines = stdout.strip().split('\n')
        if not lines or not lines[0].strip():
            return [], []
        columns = lines[0].split('\t')
        rows = []
        for line in lines[1:]:
            if not line.strip():
                continue
            row = line.split('\t')
            row = [v if v != 'NULL' else None for v in row]
            rows.append(row)
        return columns, rows

    def execute_mysql_query(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
        sql: str,
        timeout: float = 30.0,
    ) -> MysqlQueryResult:
        self._check_container_running(account_alias, container_id)
        cmd = self._build_mysql_command(container_id, connection, sql)
        safe_cmd = cmd.replace(connection.password, "***") if connection.password else cmd
        logger.info(
            "执行 MySQL 查询 [account=%s, container=%s, cmd=%s]",
            account_alias, container_id, safe_cmd,
        )
        exit_code, stdout, stderr = self._exec_in_container(
            account_alias, container_id, cmd, timeout=timeout
        )
        if exit_code != 0:
            error_msg = stderr.strip() or stdout.strip()
            return MysqlQueryResult(error=error_msg)
        columns, rows = self._parse_tsv(stdout)
        truncated = len(rows) > _MAX_ROWS
        if truncated:
            rows = rows[:_MAX_ROWS]
        return MysqlQueryResult(
            columns=columns,
            rows=rows,
            total_count=len(rows),
            truncated=truncated,
        )

    def get_mysql_tables(
        self, account_alias: str, container_id: str, connection: Any
    ) -> list[str]:
        self._check_container_running(account_alias, container_id)
        cmd = self._build_mysql_command(
            container_id, connection, "SHOW TABLES"
        )
        exit_code, stdout, stderr = self._exec_in_container(
            account_alias, container_id, cmd, timeout=15.0
        )
        if exit_code != 0:
            from app.models.db_toolkit import DbToolkitError
            raise DbToolkitError("DB_TOOLKIT_4001", stderr.strip() or "获取表列表失败")
        lines = stdout.strip().split('\n')
        return [line.strip() for line in lines[1:] if line.strip()]

    def get_mysql_table_structure(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
        table_name: str,
    ) -> MysqlTableStructure:
        self._check_container_running(account_alias, container_id)

        def _exec_sql(sql: str) -> tuple[int, str, str]:
            cmd = self._build_mysql_command(container_id, connection, sql)
            return self._exec_in_container(account_alias, container_id, cmd, timeout=15.0)

        _, desc_out, _ = _exec_sql(f"DESCRIBE `{table_name}`")
        columns = []
        for line in desc_out.strip().split('\n')[1:]:
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) >= 6:
                columns.append(MysqlColumnDef(
                    field=parts[0],
                    type=parts[1],
                    null=parts[2],
                    key=parts[3],
                    default=parts[4] if parts[4] != 'NULL' else None,
                    extra=parts[5],
                ))

        _, idx_out, _ = _exec_sql(f"SHOW INDEX FROM `{table_name}`")
        indexes = []
        seen = set()
        for line in idx_out.strip().split('\n')[1:]:
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                idx_name = parts[2]
                idx_key = (idx_name, parts[4] if len(parts) > 4 else "")
                if idx_name not in seen:
                    seen.add(idx_name)
                    indexes.append(MysqlIndexDef(
                        name=idx_name,
                        column=parts[4] if len(parts) > 4 else "",
                        unique=parts[1] == "0",
                    ))

        _, count_out, _ = _exec_sql(f"SELECT COUNT(*) FROM `{table_name}`")
        row_count = 0
        count_lines = count_out.strip().split('\n')
        if len(count_lines) >= 2:
            try:
                row_count = int(count_lines[1].strip())
            except ValueError:
                pass

        _, ddl_out, _ = _exec_sql(f"SHOW CREATE TABLE `{table_name}`")
        create_ddl = ""
        ddl_lines = ddl_out.strip().split('\n')
        if len(ddl_lines) >= 2:
            parts = ddl_lines[1].split('\t')
            create_ddl = parts[1] if len(parts) >= 2 else ddl_lines[1]

        return MysqlTableStructure(
            table_name=table_name,
            columns=columns,
            indexes=indexes,
            row_count=row_count,
            create_ddl=create_ddl,
        )

    def scan_redis_keys(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
        pattern: str = "*",
        count: int = 100,
        cursor: int = 0,
    ) -> RedisScanResult:
        self._check_container_running(account_alias, container_id)
        cmd = self._build_redis_cli_command(
            container_id, connection,
            "SCAN", str(cursor), "MATCH", pattern, "COUNT", str(count),
        )
        safe_cmd = cmd.replace(connection.password, "***") if connection.password else cmd
        logger.info(
            "Redis SCAN [account=%s, container=%s, cmd=%s]",
            account_alias, container_id, safe_cmd,
        )
        exit_code, stdout, stderr = self._exec_in_container(
            account_alias, container_id, cmd, timeout=15.0
        )
        if exit_code != 0:
            from app.models.db_toolkit import DbToolkitError
            raise DbToolkitError("DB_TOOLKIT_4002", stderr.strip() or "SCAN 执行失败")
        lines = stdout.strip().split('\n')
        filtered = [l for l in lines if l.strip() and not l.strip().startswith("Warning:")]
        if len(filtered) < 2:
            return RedisScanResult(keys=[], next_cursor=0, has_more=False)
        try:
            next_cursor = int(filtered[0].strip())
        except ValueError:
            next_cursor = 0
        keys = [l.strip() for l in filtered[1:] if l.strip()]
        return RedisScanResult(
            keys=keys,
            next_cursor=next_cursor,
            has_more=next_cursor != 0,
        )

    @staticmethod
    def _format_ttl(ttl: int) -> str:
        if ttl == -1:
            return "永不过期"
        if ttl == -2:
            return "Key 不存在"
        if ttl < 0:
            return str(ttl)
        days = ttl // 86400
        hours = (ttl % 86400) // 3600
        minutes = (ttl % 3600) // 60
        seconds = ttl % 60
        parts = []
        if days:
            parts.append(f"{days}天")
        if hours:
            parts.append(f"{hours}小时")
        if minutes:
            parts.append(f"{minutes}分")
        if seconds or not parts:
            parts.append(f"{seconds}秒")
        return "".join(parts)

    def get_redis_key_info(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
        key: str,
    ) -> RedisKeyInfo:
        self._check_container_running(account_alias, container_id)

        def _exec_redis(*args: str) -> str:
            cmd = self._build_redis_cli_command(container_id, connection, *args)
            ec, out, err = self._exec_in_container(
                account_alias, container_id, cmd, timeout=10.0
            )
            result = out.strip()
            lines = result.split('\n')
            filtered = [l for l in lines if not l.strip().startswith("Warning:")]
            return '\n'.join(filtered)

        key_type = _exec_redis("TYPE", key).strip()
        ttl_str = _exec_redis("TTL", key).strip()
        try:
            ttl = int(ttl_str)
        except ValueError:
            ttl = -2
        ttl_display = self._format_ttl(ttl)

        value: Any = None
        truncated = False
        size_bytes = 0

        if key_type == "string":
            raw = _exec_redis("GET", key)
            size_bytes = len(raw.encode("utf-8", errors="replace"))
            if size_bytes > _MAX_VALUE_BYTES:
                value = raw[:_MAX_VALUE_BYTES]
                truncated = True
            else:
                value = raw
        elif key_type == "hash":
            raw = _exec_redis("HGETALL", key)
            lines_h = [l.strip() for l in raw.split('\n') if l.strip()]
            pairs = {}
            for i in range(0, len(lines_h) - 1, 2):
                pairs[lines_h[i]] = lines_h[i + 1]
            value = pairs
            size_bytes = len(raw.encode("utf-8", errors="replace"))
        elif key_type == "list":
            raw = _exec_redis("LRANGE", key, "0", "-1")
            value = [l.strip() for l in raw.split('\n') if l.strip()]
            size_bytes = len(raw.encode("utf-8", errors="replace"))
        elif key_type == "set":
            raw = _exec_redis("SMEMBERS", key)
            value = [l.strip() for l in raw.split('\n') if l.strip()]
            size_bytes = len(raw.encode("utf-8", errors="replace"))
        elif key_type == "zset":
            raw = _exec_redis("ZRANGE", key, "0", "-1", "WITHSCORES")
            lines_z = [l.strip() for l in raw.split('\n') if l.strip()]
            pairs = []
            for i in range(0, len(lines_z) - 1, 2):
                pairs.append({"member": lines_z[i], "score": lines_z[i + 1]})
            value = pairs
            size_bytes = len(raw.encode("utf-8", errors="replace"))
        elif key_type == "stream":
            raw = _exec_redis("XRANGE", key, "-", "+")
            value = raw
            size_bytes = len(raw.encode("utf-8", errors="replace"))
        else:
            value = f"(不支持的类型: {key_type})"

        if size_bytes > _MAX_VALUE_BYTES and not truncated:
            truncated = True

        return RedisKeyInfo(
            key=key,
            type=key_type,
            ttl=ttl,
            ttl_display=ttl_display,
            value=value,
            size_bytes=size_bytes,
            truncated=truncated,
        )

    def get_redis_db_stats(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
    ) -> RedisDbStats:
        self._check_container_running(account_alias, container_id)

        def _exec_redis(*args: str) -> str:
            cmd = self._build_redis_cli_command(container_id, connection, *args)
            _, out, _ = self._exec_in_container(
                account_alias, container_id, cmd, timeout=10.0
            )
            lines = out.strip().split('\n')
            filtered = [l for l in lines if not l.strip().startswith("Warning:")]
            return '\n'.join(filtered)

        dbsize_str = _exec_redis("DBSIZE").strip()
        try:
            key_count = int(dbsize_str)
        except ValueError:
            key_count = 0

        info_raw = _exec_redis("INFO", "memory")
        used_memory_human = ""
        used_memory_bytes = 0
        for line in info_raw.split('\n'):
            line = line.strip()
            if line.startswith("used_memory_human:"):
                used_memory_human = line.split(":", 1)[1].strip()
            elif line.startswith("used_memory:"):
                try:
                    used_memory_bytes = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

        return RedisDbStats(
            key_count=key_count,
            used_memory_human=used_memory_human,
            used_memory_bytes=used_memory_bytes,
        )

    def delete_redis_key(
        self,
        account_alias: str,
        container_id: str,
        connection: Any,
        key: str,
    ) -> bool:
        self._check_container_running(account_alias, container_id)
        cmd = self._build_redis_cli_command(container_id, connection, "DEL", key)
        safe_cmd = cmd.replace(connection.password, "***") if connection.password else cmd
        logger.info(
            "Redis DEL [account=%s, container=%s, key=%s, cmd=%s]",
            account_alias, container_id, key, safe_cmd,
        )
        exit_code, stdout, stderr = self._exec_in_container(
            account_alias, container_id, cmd, timeout=10.0
        )
        return exit_code == 0


db_toolkit_service = DbToolkitService()
