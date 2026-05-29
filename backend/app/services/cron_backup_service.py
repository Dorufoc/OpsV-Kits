from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app.core.encryption import decrypt, encrypt
from app.models.cron_backup import (
    BackupHistory,
    BackupPolicy,
    BackupPolicyCreate,
    BackupPolicyUpdate,
    BackupType,
    CleanupAction,
    CompressionType,
    CronJob,
    CronJobCreate,
    CronJobUpdate,
    DiskUsageInfo,
    ExecutionLog,
    FileInfo,
    LogRetentionPolicy,
    LogRetentionPolicyCreate,
    LogRetentionPolicyUpdate,
    StorageType,
    TaskStatus,
)
from app.services.ssh_account_service import ssh_account_service

_PERSIST_DIR = Path.home() / ".opsv-kits"
_DB_PATH = _PERSIST_DIR / "cron_backup.db"

_CRON_MARKER_START = "# === OPSV-KITS CRON JOB START"
_CRON_MARKER_END = "# === OPSV-KITS CRON JOB END"
_BACKUP_MARKER_START = "# === OPSV-KITS BACKUP START"
_BACKUP_MARKER_END = "# === OPSV-KITS BACKUP END"
_LOG_MARKER_START = "# === OPSV-KITS LOG CLEANUP START"
_LOG_MARKER_END = "# === OPSV-KITS LOG CLEANUP END"


class CronBackupService:
    def __init__(self):
        self._lock = threading.RLock()
        self._init_db()

    # ── 数据库初始化 ────────────────────────────────────────────────

    def _init_db(self) -> None:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS cron_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cron_expression TEXT NOT NULL,
                    task_type TEXT DEFAULT 'shell',
                    command TEXT NOT NULL,
                    http_method TEXT,
                    http_headers TEXT,
                    http_body TEXT,
                    status TEXT DEFAULT 'enabled',
                    account_alias TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    last_run_at TEXT,
                    last_run_status TEXT
                );

                CREATE TABLE IF NOT EXISTS backup_policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    source_path TEXT,
                    db_name TEXT,
                    db_host TEXT DEFAULT 'localhost',
                    db_port INTEGER,
                    db_username TEXT,
                    db_password_encrypted TEXT,
                    storage_type TEXT NOT NULL,
                    storage_config TEXT,
                    cron_expression TEXT NOT NULL,
                    retention_count INTEGER DEFAULT 7,
                    compression TEXT DEFAULT 'tar.gz',
                    status TEXT DEFAULT 'enabled',
                    account_alias TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    last_backup_at TEXT,
                    last_backup_status TEXT
                );

                CREATE TABLE IF NOT EXISTS backup_history (
                    id TEXT PRIMARY KEY,
                    policy_id TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    file_path TEXT,
                    file_size INTEGER,
                    storage_type TEXT NOT NULL,
                    storage_path TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    account_alias TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS log_retention_policies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    log_path_pattern TEXT NOT NULL,
                    retention_days INTEGER DEFAULT 30,
                    cleanup_action TEXT DEFAULT 'delete',
                    archive_path TEXT,
                    cron_expression TEXT NOT NULL,
                    status TEXT DEFAULT 'enabled',
                    account_alias TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    last_run_at TEXT,
                    last_run_status TEXT
                );

                CREATE TABLE IF NOT EXISTS execution_logs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    exit_code INTEGER,
                    output TEXT,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    account_alias TEXT NOT NULL
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(_DB_PATH))

    # ── SSH 执行基础 ──────────────────────────────────────────────

    def _get_ssh_conn(self, alias: str):
        from app.services.ssh_account_service import ssh_account_service
        account = ssh_account_service.get_account(alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec(self, alias: str, cmd: str, timeout: float = 30.0) -> tuple[int, str, str]:
        conn = self._get_ssh_conn(alias)
        try:
            code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return code, stdout.strip(), stderr.strip()
        finally:
            ssh_account_service.pool.release_connection(conn)

    # ── Cron 任务管理 ─────────────────────────────────────────────

    def list_cron_jobs(self, alias: str) -> list[CronJob]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM cron_jobs WHERE account_alias = ? ORDER BY created_at DESC",
                    (alias,),
                )
                rows = cursor.fetchall()
                return [self._row_to_cron_job(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_cron_job(self, job_id: str) -> Optional[CronJob]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM cron_jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_cron_job(dict(zip([c[0] for c in cursor.description], row)))
                return None

    def create_cron_job(self, alias: str, data: CronJobCreate) -> CronJob:
        with self._lock:
            job_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            job = CronJob(
                id=job_id,
                name=data.name,
                cron_expression=data.cron_expression,
                task_type=data.task_type,
                command=data.command,
                http_method=data.http_method,
                http_headers=data.http_headers,
                http_body=data.http_body,
                status=data.status,
                account_alias=alias,
                description=data.description,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO cron_jobs (id, name, cron_expression, task_type, command,
                        http_method, http_headers, http_body, status, account_alias,
                        description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.id, job.name, job.cron_expression, job.task_type, job.command,
                        job.http_method,
                        json.dumps(job.http_headers) if job.http_headers else None,
                        job.http_body, job.status.value, job.account_alias,
                        job.description, now, now,
                    ),
                )
            self._sync_cron_job_to_remote(job)
            return job

    def update_cron_job(self, job_id: str, data: CronJobUpdate) -> CronJob:
        with self._lock:
            existing = self.get_cron_job(job_id)
            if not existing:
                raise ValueError(f"Cron 任务 '{job_id}' 不存在")

            updates = data.model_dump(exclude_unset=True)
            if not updates:
                return existing

            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "http_headers" and value is not None:
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value.value if hasattr(value, "value") else value)

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(job_id)

            with self._conn() as conn:
                conn.execute(
                    f"UPDATE cron_jobs SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )

            updated = self.get_cron_job(job_id)
            self._sync_cron_job_to_remote(updated)
            return updated

    def delete_cron_job(self, job_id: str) -> None:
        with self._lock:
            existing = self.get_cron_job(job_id)
            if not existing:
                raise ValueError(f"Cron 任务 '{job_id}' 不存在")
            with self._conn() as conn:
                conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
            self._remove_cron_job_from_remote(existing)

    def _row_to_cron_job(self, row: dict) -> CronJob:
        headers = row.get("http_headers")
        return CronJob(
            id=row["id"],
            name=row["name"],
            cron_expression=row["cron_expression"],
            task_type=row.get("task_type", "shell"),
            command=row["command"],
            http_method=row.get("http_method"),
            http_headers=json.loads(headers) if headers else None,
            http_body=row.get("http_body"),
            status=TaskStatus(row.get("status", "enabled")),
            account_alias=row["account_alias"],
            description=row.get("description"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row.get("last_run_at") else None,
            last_run_status=row.get("last_run_status"),
        )

    # ── 远程 crontab 同步 ─────────────────────────────────────────

    def _sync_cron_job_to_remote(self, job: CronJob) -> None:
        self._remove_cron_job_from_remote(job)
        if job.status == TaskStatus.DISABLED:
            return

        cron_line = self._build_cron_line(job)
        alias = job.account_alias

        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        existing = stdout if code == 0 else ""

        marker_start = f"{_CRON_MARKER_START} {job.id}"
        marker_end = f"{_CRON_MARKER_END} {job.id}"
        block = f"{marker_start}\n# {job.name}\n{cron_line}\n{marker_end}"

        new_crontab = existing + "\n" + block + "\n" if existing.strip() else block + "\n"
        self._install_crontab(alias, new_crontab)

    def _remove_cron_job_from_remote(self, job: CronJob) -> None:
        alias = job.account_alias
        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        if code != 0:
            return
        existing = stdout
        marker_start = f"{_CRON_MARKER_START} {job.id}"
        marker_end = f"{_CRON_MARKER_END} {job.id}"

        pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end) + r"\n?", re.DOTALL)
        new_crontab = pattern.sub("", existing)
        self._install_crontab(alias, new_crontab)

    def _build_cron_line(self, job: CronJob) -> str:
        if job.task_type == "url":
            method = job.http_method or "GET"
            headers = ""
            if job.http_headers:
                for k, v in job.http_headers.items():
                    headers += f" -H '{k}: {v}'"
            body = f" -d '{job.http_body}'" if job.http_body else ""
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' -X {method}{headers}{body} '{job.command}'"
            return f"{job.cron_expression} {cmd} >> /tmp/opsv_cron_{job.id}.log 2>&1"
        return f"{job.cron_expression} {job.command} >> /tmp/opsv_cron_{job.id}.log 2>&1"

    def _install_crontab(self, alias: str, content: str) -> None:
        safe_content = content.replace("'", "'\"'\"'")
        cmd = f"echo '{safe_content}' | crontab -"
        code, _, stderr = self._exec(alias, cmd, 10)
        if code != 0:
            raise RuntimeError(f"更新 crontab 失败: {stderr}")

    # ── 备份策略管理 ──────────────────────────────────────────────

    def list_backup_policies(self, alias: str) -> list[BackupPolicy]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM backup_policies WHERE account_alias = ? ORDER BY created_at DESC",
                    (alias,),
                )
                rows = cursor.fetchall()
                return [self._row_to_backup_policy(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_backup_policy(self, policy_id: str) -> Optional[BackupPolicy]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM backup_policies WHERE id = ?", (policy_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_backup_policy(dict(zip([c[0] for c in cursor.description], row)))
                return None

    def create_backup_policy(self, alias: str, data: BackupPolicyCreate) -> BackupPolicy:
        with self._lock:
            policy_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            db_pwd_encrypted = encrypt(data.db_password) if data.db_password else None

            policy = BackupPolicy(
                id=policy_id,
                name=data.name,
                backup_type=data.backup_type,
                source_path=data.source_path,
                db_name=data.db_name,
                db_host=data.db_host,
                db_port=data.db_port,
                db_username=data.db_username,
                db_password_encrypted=db_pwd_encrypted,
                storage_type=data.storage_type,
                storage_config=data.storage_config,
                cron_expression=data.cron_expression,
                retention_count=data.retention_count,
                compression=data.compression,
                status=data.status,
                account_alias=alias,
                description=data.description,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO backup_policies (id, name, backup_type, source_path, db_name,
                        db_host, db_port, db_username, db_password_encrypted, storage_type,
                        storage_config, cron_expression, retention_count, compression, status,
                        account_alias, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        policy.id, policy.name, policy.backup_type.value, policy.source_path,
                        policy.db_name, policy.db_host, policy.db_port, policy.db_username,
                        policy.db_password_encrypted, policy.storage_type.value,
                        json.dumps(policy.storage_config), policy.cron_expression,
                        policy.retention_count, policy.compression.value,
                        policy.status.value, policy.account_alias, policy.description, now, now,
                    ),
                )

            self._sync_backup_policy_to_remote(policy)
            return policy

    def update_backup_policy(self, policy_id: str, data: BackupPolicyUpdate) -> BackupPolicy:
        with self._lock:
            existing = self.get_backup_policy(policy_id)
            if not existing:
                raise ValueError(f"备份策略 '{policy_id}' 不存在")

            updates = data.model_dump(exclude_unset=True)
            if "db_password" in updates:
                pwd = updates.pop("db_password")
                if pwd:
                    updates["db_password_encrypted"] = encrypt(pwd)

            if not updates:
                return existing

            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "storage_config" and value is not None:
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value.value if hasattr(value, "value") else value)

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(policy_id)

            with self._conn() as conn:
                conn.execute(
                    f"UPDATE backup_policies SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )

            updated = self.get_backup_policy(policy_id)
            self._sync_backup_policy_to_remote(updated)
            return updated

    def delete_backup_policy(self, policy_id: str) -> None:
        with self._lock:
            existing = self.get_backup_policy(policy_id)
            if not existing:
                raise ValueError(f"备份策略 '{policy_id}' 不存在")
            with self._conn() as conn:
                conn.execute("DELETE FROM backup_policies WHERE id = ?", (policy_id,))
            self._remove_backup_policy_from_remote(existing)

    def _row_to_backup_policy(self, row: dict) -> BackupPolicy:
        config = row.get("storage_config")
        return BackupPolicy(
            id=row["id"],
            name=row["name"],
            backup_type=BackupType(row["backup_type"]),
            source_path=row.get("source_path"),
            db_name=row.get("db_name"),
            db_host=row.get("db_host", "localhost"),
            db_port=row.get("db_port"),
            db_username=row.get("db_username"),
            db_password_encrypted=row.get("db_password_encrypted"),
            storage_type=StorageType(row["storage_type"]),
            storage_config=json.loads(config) if config else {},
            cron_expression=row["cron_expression"],
            retention_count=row.get("retention_count", 7),
            compression=CompressionType(row.get("compression", "tar.gz")),
            status=TaskStatus(row.get("status", "enabled")),
            account_alias=row["account_alias"],
            description=row.get("description"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
            last_backup_at=datetime.fromisoformat(row["last_backup_at"]) if row.get("last_backup_at") else None,
            last_backup_status=row.get("last_backup_status"),
        )

    # ── 备份远程 crontab 同步 ─────────────────────────────────────

    def _sync_backup_policy_to_remote(self, policy: BackupPolicy) -> None:
        self._remove_backup_policy_from_remote(policy)
        if policy.status == TaskStatus.DISABLED:
            return

        script = self._build_backup_script(policy)
        alias = policy.account_alias
        script_path = f"/tmp/opsv_backup_{policy.id}.sh"

        encoded_script = script.encode("utf-8").hex()
        self._exec(alias, f"echo {encoded_script} | xxd -r -p > {script_path} && chmod +x {script_path}", 15)

        cron_line = f"{policy.cron_expression} {script_path} >> /tmp/opsv_backup_{policy.id}.log 2>&1"
        marker_start = f"{_BACKUP_MARKER_START} {policy.id}"
        marker_end = f"{_BACKUP_MARKER_END} {policy.id}"
        block = f"{marker_start}\n# {policy.name}\n{cron_line}\n{marker_end}"

        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        existing = stdout if code == 0 else ""
        new_crontab = existing + "\n" + block + "\n" if existing.strip() else block + "\n"
        self._install_crontab(alias, new_crontab)

    def _remove_backup_policy_from_remote(self, policy: BackupPolicy) -> None:
        alias = policy.account_alias
        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        if code != 0:
            return
        existing = stdout
        marker_start = f"{_BACKUP_MARKER_START} {policy.id}"
        marker_end = f"{_BACKUP_MARKER_END} {policy.id}"

        pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end) + r"\n?", re.DOTALL)
        new_crontab = pattern.sub("", existing)
        self._install_crontab(alias, new_crontab)

        script_path = f"/tmp/opsv_backup_{policy.id}.sh"
        self._exec(alias, f"rm -f {script_path}", 5)

    def _build_backup_script(self, policy: BackupPolicy) -> str:
        timestamp = "$(date +%Y%m%d_%H%M%S)"
        backup_dir = "/tmp/opsv_backups"
        lines = [
            "#!/bin/bash",
            f"mkdir -p {backup_dir}",
            f"BACKUP_FILE=\"{backup_dir}/{policy.name}_{timestamp}\"",
        ]

        if policy.backup_type == BackupType.WEBSITE or policy.backup_type == BackupType.CUSTOM:
            src = policy.source_path or "/var/www/html"
            if policy.compression == CompressionType.TAR_GZ:
                lines.append(f"tar -czf \"$BACKUP_FILE.tar.gz\" -C $(dirname '{src}') $(basename '{src}')")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.tar.gz\"")
            elif policy.compression == CompressionType.ZIP:
                lines.append(f"zip -r \"$BACKUP_FILE.zip\" '{src}'")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.zip\"")
            else:
                lines.append(f"cp -r '{src}' \"$BACKUP_FILE\"")
        elif policy.backup_type == BackupType.MYSQL:
            db = policy.db_name or ""
            host = policy.db_host or "localhost"
            port = policy.db_port or 3306
            user = policy.db_username or "root"
            pwd = decrypt(policy.db_password_encrypted) if policy.db_password_encrypted else ""
            pwd_flag = f"-p'{pwd}'" if pwd else ""
            lines.append(f"mysqldump -h {host} -P {port} -u {user} {pwd_flag} --single-transaction --routines --triggers '{db}' > \"$BACKUP_FILE.sql\"")
            if policy.compression == CompressionType.TAR_GZ:
                lines.append(f"gzip -c \"$BACKUP_FILE.sql\" > \"$BACKUP_FILE.sql.gz\"")
                lines.append(f"rm -f \"$BACKUP_FILE.sql\"")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.sql.gz\"")
            elif policy.compression == CompressionType.ZIP:
                lines.append(f"zip \"$BACKUP_FILE.zip\" \"$BACKUP_FILE.sql\"")
                lines.append(f"rm -f \"$BACKUP_FILE.sql\"")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.zip\"")
            else:
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.sql\"")
        elif policy.backup_type == BackupType.POSTGRESQL:
            db = policy.db_name or ""
            host = policy.db_host or "localhost"
            port = policy.db_port or 5432
            user = policy.db_username or "postgres"
            lines.append(f"PGPASSWORD='{policy.db_password_encrypted or ''}' pg_dump -h {host} -p {port} -U {user} -Fc '{db}' > \"$BACKUP_FILE.dump\"")
            if policy.compression == CompressionType.TAR_GZ:
                lines.append(f"gzip -c \"$BACKUP_FILE.dump\" > \"$BACKUP_FILE.dump.gz\"")
                lines.append(f"rm -f \"$BACKUP_FILE.dump\"")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.dump.gz\"")
            elif policy.compression == CompressionType.ZIP:
                lines.append(f"zip \"$BACKUP_FILE.zip\" \"$BACKUP_FILE.dump\"")
                lines.append(f"rm -f \"$BACKUP_FILE.dump\"")
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.zip\"")
            else:
                lines.append(f"BACKUP_FILE=\"$BACKUP_FILE.dump\"")

        # 存储上传逻辑
        lines.extend(self._build_storage_upload_lines(policy))

        # 保留策略清理
        if policy.retention_count > 0:
            lines.append(f"ls -t {backup_dir}/{policy.name}_* 2>/dev/null | tail -n +{policy.retention_count + 1} | xargs -r rm -f")

        lines.append("echo \"BACKUP_DONE\"")
        return "\n".join(lines)

    def _build_storage_upload_lines(self, policy: BackupPolicy) -> list[str]:
        lines = []
        config = policy.storage_config

        if policy.storage_type == StorageType.LOCAL:
            dest = config.get("path", "/backup")
            lines.append(f"mkdir -p '{dest}'")
            lines.append(f"cp \"$BACKUP_FILE\" '{dest}/'")
        elif policy.storage_type == StorageType.ALIYUN_OSS:
            bucket = config.get("bucket", "")
            endpoint = config.get("endpoint", "")
            prefix = config.get("prefix", "opsv-backups")
            lines.append(f"# Upload to Aliyun OSS: {bucket}/{prefix}")
            lines.append(f"aliyun oss cp \"$BACKUP_FILE\" oss://{bucket}/{prefix}/$(basename \"$BACKUP_FILE\") --endpoint {endpoint} 2>/dev/null || echo 'OSS upload requires aliyun CLI'")
        elif policy.storage_type == StorageType.TENCENT_COS:
            bucket = config.get("bucket", "")
            region = config.get("region", "")
            prefix = config.get("prefix", "opsv-backups")
            lines.append(f"# Upload to Tencent COS: {bucket}/{prefix}")
            lines.append(f"coscli cp \"$BACKUP_FILE\" cos://{bucket}/{prefix}/$(basename \"$BACKUP_FILE\") -r {region} 2>/dev/null || echo 'COS upload requires coscli'")
        elif policy.storage_type == StorageType.AWS_S3:
            bucket = config.get("bucket", "")
            prefix = config.get("prefix", "opsv-backups")
            lines.append(f"# Upload to AWS S3: {bucket}/{prefix}")
            lines.append(f"aws s3 cp \"$BACKUP_FILE\" s3://{bucket}/{prefix}/$(basename \"$BACKUP_FILE\") 2>/dev/null || echo 'S3 upload requires aws CLI'")
        elif policy.storage_type == StorageType.FTP or policy.storage_type == StorageType.SFTP:
            host = config.get("host", "")
            port = config.get("port", 22 if policy.storage_type == StorageType.SFTP else 21)
            user = config.get("username", "")
            pwd = config.get("password", "")
            remote_dir = config.get("remote_dir", "/backup")
            if policy.storage_type == StorageType.SFTP:
                lines.append(f"sshpass -p '{pwd}' sftp -o StrictHostKeyChecking=no -P {port} {user}@{host} << EOF")
                lines.append(f"mkdir -p {remote_dir}")
                lines.append(f"put \"$BACKUP_FILE\" {remote_dir}/")
                lines.append("EOF")
            else:
                lines.append(f"curl -T \"$BACKUP_FILE\" ftp://{user}:{pwd}@{host}:{port}{remote_dir}/$(basename \"$BACKUP_FILE\") 2>/dev/null || echo 'FTP upload failed'")

        return lines

    # ── 备份历史 ──────────────────────────────────────────────────

    def list_backup_history(self, alias: str, policy_id: Optional[str] = None, limit: int = 50) -> list[BackupHistory]:
        with self._lock:
            with self._conn() as conn:
                if policy_id:
                    cursor = conn.execute(
                        "SELECT * FROM backup_history WHERE account_alias = ? AND policy_id = ? ORDER BY started_at DESC LIMIT ?",
                        (alias, policy_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM backup_history WHERE account_alias = ? ORDER BY started_at DESC LIMIT ?",
                        (alias, limit),
                    )
                rows = cursor.fetchall()
                return [self._row_to_backup_history(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def _row_to_backup_history(self, row: dict) -> BackupHistory:
        return BackupHistory(
            id=row["id"],
            policy_id=row["policy_id"],
            policy_name=row["policy_name"],
            backup_type=BackupType(row["backup_type"]),
            file_path=row.get("file_path"),
            file_size=row.get("file_size"),
            storage_type=StorageType(row["storage_type"]),
            storage_path=row.get("storage_path"),
            status=row["status"],
            error_message=row.get("error_message"),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            account_alias=row["account_alias"],
        )

    def add_backup_history(self, history: BackupHistory) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO backup_history (id, policy_id, policy_name, backup_type, file_path,
                        file_size, storage_type, storage_path, status, error_message,
                        started_at, completed_at, account_alias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        history.id, history.policy_id, history.policy_name, history.backup_type.value,
                        history.file_path, history.file_size, history.storage_type.value,
                        history.storage_path, history.status, history.error_message,
                        history.started_at.isoformat() if history.started_at else None,
                        history.completed_at.isoformat() if history.completed_at else None,
                        history.account_alias,
                    ),
                )

    # ── 手动执行备份 ──────────────────────────────────────────────

    def run_backup_now(self, policy_id: str) -> dict[str, Any]:
        policy = self.get_backup_policy(policy_id)
        if not policy:
            raise ValueError(f"备份策略 '{policy_id}' 不存在")

        alias = policy.account_alias
        history_id = str(uuid.uuid4())
        started = datetime.now()

        history = BackupHistory(
            id=history_id,
            policy_id=policy_id,
            policy_name=policy.name,
            backup_type=policy.backup_type,
            storage_type=policy.storage_type,
            status="running",
            started_at=started,
            account_alias=alias,
        )
        self.add_backup_history(history)

        try:
            script = self._build_backup_script(policy)
            script_path = f"/tmp/opsv_backup_run_{policy_id}.sh"
            encoded = script.encode("utf-8").hex()
            self._exec(alias, f"echo {encoded} | xxd -r -p > {script_path} && chmod +x {script_path}", 15)

            code, stdout, stderr = self._exec(alias, f"bash {script_path}", 300)

            completed = datetime.now()
            status = "success" if code == 0 and "BACKUP_DONE" in stdout else "failed"

            # 尝试获取备份文件大小
            file_size = None
            file_path = None
            if status == "success":
                code2, out2, _ = self._exec(
                    alias,
                    f"ls -l /tmp/opsv_backups/{policy.name}_* 2>/dev/null | tail -1 | awk '{{print $5, $NF}}'",
                    10,
                )
                if code2 == 0 and out2:
                    parts = out2.split(maxsplit=1)
                    if len(parts) == 2:
                        try:
                            file_size = int(parts[0])
                            file_path = parts[1]
                        except ValueError:
                            pass

            history.status = status
            history.completed_at = completed
            history.error_message = stderr if status == "failed" else None
            history.file_path = file_path
            history.file_size = file_size

            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE backup_history SET status = ?, completed_at = ?, error_message = ?,
                        file_path = ?, file_size = ? WHERE id = ?
                    """,
                    (status, completed.isoformat(), history.error_message, file_path, file_size, history_id),
                )
                conn.execute(
                    "UPDATE backup_policies SET last_backup_at = ?, last_backup_status = ? WHERE id = ?",
                    (completed.isoformat(), status, policy_id),
                )

            return {
                "history_id": history_id,
                "status": status,
                "exit_code": code,
                "output": stdout,
                "error": stderr,
                "started_at": started.isoformat(),
                "completed_at": completed.isoformat(),
            }
        except Exception as e:
            completed = datetime.now()
            with self._conn() as conn:
                conn.execute(
                    "UPDATE backup_history SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
                    ("failed", completed.isoformat(), str(e), history_id),
                )
            return {
                "history_id": history_id,
                "status": "failed",
                "error": str(e),
                "started_at": started.isoformat(),
                "completed_at": completed.isoformat(),
            }

    # ── 日志保留策略管理 ───────────────────────────────────────────

    def list_log_policies(self, alias: str) -> list[LogRetentionPolicy]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM log_retention_policies WHERE account_alias = ? ORDER BY created_at DESC",
                    (alias,),
                )
                rows = cursor.fetchall()
                return [self._row_to_log_policy(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def get_log_policy(self, policy_id: str) -> Optional[LogRetentionPolicy]:
        with self._lock:
            with self._conn() as conn:
                cursor = conn.execute("SELECT * FROM log_retention_policies WHERE id = ?", (policy_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_log_policy(dict(zip([c[0] for c in cursor.description], row)))
                return None

    def create_log_policy(self, alias: str, data: LogRetentionPolicyCreate) -> LogRetentionPolicy:
        with self._lock:
            policy_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            policy = LogRetentionPolicy(
                id=policy_id,
                name=data.name,
                log_path_pattern=data.log_path_pattern,
                retention_days=data.retention_days,
                cleanup_action=data.cleanup_action,
                archive_path=data.archive_path,
                cron_expression=data.cron_expression,
                status=data.status,
                account_alias=alias,
                description=data.description,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO log_retention_policies (id, name, log_path_pattern, retention_days,
                        cleanup_action, archive_path, cron_expression, status, account_alias,
                        description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        policy.id, policy.name, policy.log_path_pattern, policy.retention_days,
                        policy.cleanup_action.value, policy.archive_path, policy.cron_expression,
                        policy.status.value, policy.account_alias, policy.description, now, now,
                    ),
                )
            self._sync_log_policy_to_remote(policy)
            return policy

    def update_log_policy(self, policy_id: str, data: LogRetentionPolicyUpdate) -> LogRetentionPolicy:
        with self._lock:
            existing = self.get_log_policy(policy_id)
            if not existing:
                raise ValueError(f"日志保留策略 '{policy_id}' 不存在")

            updates = data.model_dump(exclude_unset=True)
            if not updates:
                return existing

            set_clauses = []
            params = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value.value if hasattr(value, "value") else value)

            set_clauses.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(policy_id)

            with self._conn() as conn:
                conn.execute(
                    f"UPDATE log_retention_policies SET {', '.join(set_clauses)} WHERE id = ?",
                    params,
                )

            updated = self.get_log_policy(policy_id)
            self._sync_log_policy_to_remote(updated)
            return updated

    def delete_log_policy(self, policy_id: str) -> None:
        with self._lock:
            existing = self.get_log_policy(policy_id)
            if not existing:
                raise ValueError(f"日志保留策略 '{policy_id}' 不存在")
            with self._conn() as conn:
                conn.execute("DELETE FROM log_retention_policies WHERE id = ?", (policy_id,))
            self._remove_log_policy_from_remote(existing)

    def _row_to_log_policy(self, row: dict) -> LogRetentionPolicy:
        return LogRetentionPolicy(
            id=row["id"],
            name=row["name"],
            log_path_pattern=row["log_path_pattern"],
            retention_days=row.get("retention_days", 30),
            cleanup_action=CleanupAction(row.get("cleanup_action", "delete")),
            archive_path=row.get("archive_path"),
            cron_expression=row["cron_expression"],
            status=TaskStatus(row.get("status", "enabled")),
            account_alias=row["account_alias"],
            description=row.get("description"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else datetime.now(),
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row.get("last_run_at") else None,
            last_run_status=row.get("last_run_status"),
        )

    # ── 日志保留远程 crontab 同步 ─────────────────────────────────

    def _sync_log_policy_to_remote(self, policy: LogRetentionPolicy) -> None:
        self._remove_log_policy_from_remote(policy)
        if policy.status == TaskStatus.DISABLED:
            return

        script = self._build_log_cleanup_script(policy)
        alias = policy.account_alias
        script_path = f"/tmp/opsv_logcleanup_{policy.id}.sh"

        encoded = script.encode("utf-8").hex()
        self._exec(alias, f"echo {encoded} | xxd -r -p > {script_path} && chmod +x {script_path}", 15)

        cron_line = f"{policy.cron_expression} {script_path} >> /tmp/opsv_logcleanup_{policy.id}.log 2>&1"
        marker_start = f"{_LOG_MARKER_START} {policy.id}"
        marker_end = f"{_LOG_MARKER_END} {policy.id}"
        block = f"{marker_start}\n# {policy.name}\n{cron_line}\n{marker_end}"

        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        existing = stdout if code == 0 else ""
        new_crontab = existing + "\n" + block + "\n" if existing.strip() else block + "\n"
        self._install_crontab(alias, new_crontab)

    def _remove_log_policy_from_remote(self, policy: LogRetentionPolicy) -> None:
        alias = policy.account_alias
        code, stdout, _ = self._exec(alias, "crontab -l 2>/dev/null || echo ''", 10)
        if code != 0:
            return
        existing = stdout
        marker_start = f"{_LOG_MARKER_START} {policy.id}"
        marker_end = f"{_LOG_MARKER_END} {policy.id}"

        pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end) + r"\n?", re.DOTALL)
        new_crontab = pattern.sub("", existing)
        self._install_crontab(alias, new_crontab)

        script_path = f"/tmp/opsv_logcleanup_{policy.id}.sh"
        self._exec(alias, f"rm -f {script_path}", 5)

    def _build_log_cleanup_script(self, policy: LogRetentionPolicy) -> str:
        lines = ["#!/bin/bash"]
        pattern = policy.log_path_pattern
        days = policy.retention_days

        if policy.cleanup_action == CleanupAction.DELETE:
            lines.append(f"find {pattern} -type f -mtime +{days} -delete 2>/dev/null || true")
        elif policy.cleanup_action == CleanupAction.COMPRESS:
            archive = policy.archive_path or "/var/log/archive"
            lines.append(f"mkdir -p '{archive}'")
            lines.append(
                f"find {pattern} -type f -mtime +{days} -print0 2>/dev/null | "
                f"tar -czf '{archive}/logs_$(date +%Y%m%d).tar.gz' --null -T - 2>/dev/null || true"
            )
            lines.append(f"find {pattern} -type f -mtime +{days} -delete 2>/dev/null || true")
        elif policy.cleanup_action == CleanupAction.MOVE:
            archive = policy.archive_path or "/var/log/archive"
            lines.append(f"mkdir -p '{archive}'")
            lines.append(f"find {pattern} -type f -mtime +{days} -exec mv {{}} '{archive}/' \\; 2>/dev/null || true")

        lines.append("echo 'LOG_CLEANUP_DONE'")
        return "\n".join(lines)

    # ── 日志清理预览与执行 ────────────────────────────────────────

    def preview_log_cleanup(self, policy_id: str) -> list[FileInfo]:
        policy = self.get_log_policy(policy_id)
        if not policy:
            raise ValueError(f"日志保留策略 '{policy_id}' 不存在")

        alias = policy.account_alias
        days = policy.retention_days
        pattern = policy.log_path_pattern

        cmd = f"find {pattern} -type f -mtime +{days} -printf '%p|%s|%TY-%Tm-%Td %TH:%TM:%TM\\n' 2>/dev/null || true"
        code, stdout, _ = self._exec(alias, cmd, 30)

        files = []
        for line in stdout.split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) >= 3:
                try:
                    files.append(FileInfo(
                        path=parts[0],
                        size=int(parts[1]),
                        modified_at=datetime.strptime(parts[2].split(".")[0], "%Y-%m-%d %H:%M:%S"),
                    ))
                except (ValueError, IndexError):
                    continue
        return files

    def run_log_cleanup_now(self, policy_id: str) -> dict[str, Any]:
        policy = self.get_log_policy(policy_id)
        if not policy:
            raise ValueError(f"日志保留策略 '{policy_id}' 不存在")

        alias = policy.account_alias
        script = self._build_log_cleanup_script(policy)
        script_path = f"/tmp/opsv_logcleanup_run_{policy_id}.sh"

        encoded = script.encode("utf-8").hex()
        self._exec(alias, f"echo {encoded} | xxd -r -p > {script_path} && chmod +x {script_path}", 15)

        started = datetime.now()
        code, stdout, stderr = self._exec(alias, f"bash {script_path}", 60)
        completed = datetime.now()

        status = "success" if code == 0 and "LOG_CLEANUP_DONE" in stdout else "failed"

        with self._conn() as conn:
            conn.execute(
                "UPDATE log_retention_policies SET last_run_at = ?, last_run_status = ? WHERE id = ?",
                (completed.isoformat(), status, policy_id),
            )

        return {
            "status": status,
            "exit_code": code,
            "output": stdout,
            "error": stderr,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
        }

    # ── 磁盘空间告警 ──────────────────────────────────────────────

    def get_disk_alert(self, alias: str) -> dict[str, Any]:
        code, stdout, _ = self._exec(alias, "df -h 2>/dev/null || echo ''", 10)
        alerts = []
        usages = []

        if code == 0:
            for line in stdout.split("\n")[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        use_percent = int(parts[4].replace("%", ""))
                        info = DiskUsageInfo(
                            filesystem=parts[0],
                            size=parts[1],
                            used=parts[2],
                            available=parts[3],
                            use_percent=use_percent,
                            mount_point=parts[5],
                        )
                        usages.append(info)
                        if use_percent >= 85:
                            alerts.append(info)
                    except (ValueError, IndexError):
                        continue

        # 获取日志目录大小
        log_sizes = []
        code2, stdout2, _ = self._exec(
            alias,
            "du -sh /var/log/* 2>/dev/null | sort -rh | head -10 || true",
            15,
        )
        if code2 == 0:
            for line in stdout2.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    log_sizes.append({"size": parts[0], "path": parts[1]})

        return {
            "has_alert": len(alerts) > 0,
            "alerts": alerts,
            "disk_usage": usages,
            "log_sizes": log_sizes,
        }

    # ── 执行日志 ──────────────────────────────────────────────────

    def add_execution_log(self, log: ExecutionLog) -> None:
        with self._lock:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_logs (id, task_id, task_type, task_name, status,
                        exit_code, output, error, started_at, completed_at, duration_seconds, account_alias)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log.id, log.task_id, log.task_type, log.task_name, log.status,
                        log.exit_code, log.output, log.error,
                        log.started_at.isoformat() if log.started_at else None,
                        log.completed_at.isoformat() if log.completed_at else None,
                        log.duration_seconds, log.account_alias,
                    ),
                )

    def list_execution_logs(self, alias: str, task_id: Optional[str] = None, limit: int = 20) -> list[ExecutionLog]:
        with self._lock:
            with self._conn() as conn:
                if task_id:
                    cursor = conn.execute(
                        "SELECT * FROM execution_logs WHERE account_alias = ? AND task_id = ? ORDER BY started_at DESC LIMIT ?",
                        (alias, task_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM execution_logs WHERE account_alias = ? ORDER BY started_at DESC LIMIT ?",
                        (alias, limit),
                    )
                rows = cursor.fetchall()
                return [self._row_to_execution_log(dict(zip([c[0] for c in cursor.description], row))) for row in rows]

    def _row_to_execution_log(self, row: dict) -> ExecutionLog:
        return ExecutionLog(
            id=row["id"],
            task_id=row["task_id"],
            task_type=row["task_type"],
            task_name=row["task_name"],
            status=row["status"],
            exit_code=row.get("exit_code"),
            output=row.get("output"),
            error=row.get("error"),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            duration_seconds=row.get("duration_seconds"),
            account_alias=row["account_alias"],
        )

    # ── 下载本地备份文件 ──────────────────────────────────────────

    def download_backup_file(self, alias: str, file_path: str) -> bytes:
        conn = self._get_ssh_conn(alias)
        try:
            sftp = conn.manager.open_sftp()
            with sftp.file(file_path, "rb") as f:
                return f.read()
        finally:
            ssh_account_service.pool.release_connection(conn)


cron_backup_service = CronBackupService()
