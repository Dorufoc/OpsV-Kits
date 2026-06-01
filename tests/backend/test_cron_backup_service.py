from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.cron_backup import (
    BackupHistory,
    BackupPolicyCreate,
    BackupPolicyUpdate,
    BackupType,
    CleanupAction,
    CompressionType,
    CronJobCreate,
    CronJobUpdate,
    DiskUsageInfo,
    ExecutionLog,
    LogRetentionPolicyCreate,
    LogRetentionPolicyUpdate,
    StorageType,
    TaskStatus,
)
from app.services.cron_backup_service import CronBackupService


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "cron_backup.db"
    monkeypatch.setattr("app.services.cron_backup_service._PERSIST_DIR", tmp_path)
    monkeypatch.setattr("app.services.cron_backup_service._DB_PATH", db_path)
    svc = CronBackupService.__new__(CronBackupService)
    svc._lock = threading.RLock()
    svc._init_db()
    return svc


@pytest.fixture
def svc_with_mock_exec(tmp_db):
    exec_results = []

    def mock_exec(alias, cmd, timeout=30.0):
        if exec_results:
            return exec_results.pop(0)
        return (0, "", "")

    tmp_db._exec = mock_exec
    tmp_db._get_ssh_conn = MagicMock()
    return tmp_db, exec_results


class TestCronJobCRUD:
    def test_create_cron_job_shell(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(
            name="test-job",
            cron_expression="0 * * * *",
            task_type="shell",
            command="echo hello",
        )
        job = svc.create_cron_job("server1", data)
        assert job.name == "test-job"
        assert job.cron_expression == "0 * * * *"
        assert job.task_type == "shell"
        assert job.command == "echo hello"
        assert job.status == TaskStatus.ENABLED
        assert job.account_alias == "server1"

    def test_create_cron_job_url(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(
            name="url-job",
            cron_expression="*/5 * * * *",
            task_type="url",
            command="http://example.com/api",
            http_method="POST",
            http_headers={"Content-Type": "application/json"},
            http_body='{"key":"val"}',
        )
        job = svc.create_cron_job("server1", data)
        assert job.task_type == "url"
        assert job.http_method == "POST"
        assert job.http_headers == {"Content-Type": "application/json"}
        assert job.http_body == '{"key":"val"}'

    def test_list_cron_jobs(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data1 = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        data2 = CronJobCreate(name="job2", cron_expression="0 0 * * *", command="echo 2")
        svc.create_cron_job("server1", data1)
        svc.create_cron_job("server1", data2)
        jobs = svc.list_cron_jobs("server1")
        assert len(jobs) == 2

    def test_list_cron_jobs_empty(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        jobs = svc.list_cron_jobs("nonexistent")
        assert jobs == []

    def test_get_cron_job(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        found = svc.get_cron_job(created.id)
        assert found is not None
        assert found.name == "job1"

    def test_get_cron_job_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        result = svc.get_cron_job("nonexistent-id")
        assert result is None

    def test_update_cron_job(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        update = CronJobUpdate(name="updated-job", command="echo updated")
        updated = svc.update_cron_job(created.id, update)
        assert updated.name == "updated-job"
        assert updated.command == "echo updated"

    def test_update_cron_job_no_changes(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        update = CronJobUpdate()
        updated = svc.update_cron_job(created.id, update)
        assert updated.name == "job1"

    def test_update_cron_job_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        update = CronJobUpdate(name="x")
        with pytest.raises(ValueError, match="不存在"):
            svc.update_cron_job("nonexistent-id", update)

    def test_update_cron_job_with_headers(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        update = CronJobUpdate(http_headers={"X-Custom": "value"})
        updated = svc.update_cron_job(created.id, update)
        assert updated.http_headers == {"X-Custom": "value"}

    def test_delete_cron_job(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        svc.delete_cron_job(created.id)
        assert svc.get_cron_job(created.id) is None

    def test_delete_cron_job_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.delete_cron_job("nonexistent-id")

    def test_update_cron_job_status(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        created = svc.create_cron_job("server1", data)
        update = CronJobUpdate(status=TaskStatus.DISABLED)
        updated = svc.update_cron_job(created.id, update)
        assert updated.status == TaskStatus.DISABLED


class TestCronJobRemoteSync:
    def test_sync_cron_job_to_remote_enabled(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((0, "existing_crontab", ""))
        results.append((0, "", ""))
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        job = svc.create_cron_job("server1", data)

    def test_sync_cron_job_to_remote_disabled(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((0, "existing", ""))
        data = CronJobCreate(
            name="job1",
            cron_expression="0 * * * *",
            command="echo 1",
            status=TaskStatus.DISABLED,
        )
        job = svc.create_cron_job("server1", data)

    def test_remove_cron_job_from_remote_crontab_fail(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((1, "", "error"))
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        job = svc.create_cron_job("server1", data)

    def test_install_crontab_failure(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((0, "existing", ""))
        results.append((1, "", "crontab error"))
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        with pytest.raises(RuntimeError, match="更新 crontab 失败"):
            svc.create_cron_job("server1", data)

    def test_build_cron_line_shell(self, tmp_db):
        job = MagicMock()
        job.task_type = "shell"
        job.cron_expression = "0 * * * *"
        job.command = "echo hello"
        job.id = "test-id"
        line = tmp_db._build_cron_line(job)
        assert "0 * * * * echo hello" in line
        assert ">> /tmp/opsv_cron_test-id.log 2>&1" in line

    def test_build_cron_line_url(self, tmp_db):
        job = MagicMock()
        job.task_type = "url"
        job.cron_expression = "*/5 * * * *"
        job.command = "http://example.com/api"
        job.http_method = "POST"
        job.http_headers = {"Content-Type": "application/json"}
        job.http_body = '{"key":"val"}'
        job.id = "url-id"
        line = tmp_db._build_cron_line(job)
        assert "curl" in line
        assert "-X POST" in line
        assert "-H 'Content-Type: application/json'" in line
        assert "-d '{\"key\":\"val\"}'" in line

    def test_build_cron_line_url_no_headers(self, tmp_db):
        job = MagicMock()
        job.task_type = "url"
        job.cron_expression = "0 * * * *"
        job.command = "http://example.com"
        job.http_method = None
        job.http_headers = None
        job.http_body = None
        job.id = "url-id2"
        line = tmp_db._build_cron_line(job)
        assert "curl" in line
        assert "-X GET" in line

    def test_build_cron_line_url_with_body_no_headers(self, tmp_db):
        job = MagicMock()
        job.task_type = "url"
        job.cron_expression = "0 * * * *"
        job.command = "http://example.com"
        job.http_method = "PUT"
        job.http_headers = None
        job.http_body = "data"
        job.id = "url-id3"
        line = tmp_db._build_cron_line(job)
        assert "-d 'data'" in line

    def test_sync_empty_crontab(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((0, "", ""))
        results.append((0, "", ""))
        data = CronJobCreate(name="job1", cron_expression="0 * * * *", command="echo 1")
        job = svc.create_cron_job("server1", data)


class TestBackupPolicyCRUD:
    def test_create_backup_policy_website(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="web-backup",
            backup_type=BackupType.WEBSITE,
            source_path="/var/www/html",
            storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"},
            cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        assert policy.name == "web-backup"
        assert policy.backup_type == BackupType.WEBSITE
        assert policy.source_path == "/var/www/html"
        assert policy.storage_type == StorageType.LOCAL

    def test_create_backup_policy_mysql(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        with patch("app.services.cron_backup_service.encrypt", return_value="enc_pwd"), \
             patch("app.services.cron_backup_service.decrypt", return_value="secret"):
            data = BackupPolicyCreate(
                name="mysql-backup",
                backup_type=BackupType.MYSQL,
                db_name="mydb",
                db_host="localhost",
                db_port=3306,
                db_username="root",
                db_password="secret",
                storage_type=StorageType.LOCAL,
                storage_config={"path": "/backup"},
                cron_expression="0 3 * * *",
            )
            policy = svc.create_backup_policy("server1", data)
            assert policy.db_name == "mydb"
            assert policy.db_password_encrypted == "enc_pwd"

    def test_create_backup_policy_no_password(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="mysql-no-pwd",
            backup_type=BackupType.MYSQL,
            db_name="mydb",
            storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"},
            cron_expression="0 3 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        assert policy.db_password_encrypted is None

    def test_list_backup_policies(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", ""), (0, "", "")])
        data1 = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        data2 = BackupPolicyCreate(
            name="p2", backup_type=BackupType.MYSQL,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 0 * * *",
        )
        svc.create_backup_policy("server1", data1)
        svc.create_backup_policy("server1", data2)
        policies = svc.list_backup_policies("server1")
        assert len(policies) == 2

    def test_list_backup_policies_empty(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        policies = svc.list_backup_policies("nonexistent")
        assert policies == []

    def test_get_backup_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        found = svc.get_backup_policy(created.id)
        assert found is not None
        assert found.name == "p1"

    def test_get_backup_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        result = svc.get_backup_policy("nonexistent-id")
        assert result is None

    def test_update_backup_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        update = BackupPolicyUpdate(name="updated-p1")
        updated = svc.update_backup_policy(created.id, update)
        assert updated.name == "updated-p1"

    def test_update_backup_policy_with_password(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.MYSQL,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        with patch("app.services.cron_backup_service.encrypt", return_value="new_enc_pwd"), \
             patch("app.services.cron_backup_service.decrypt", return_value="new_secret"):
            update = BackupPolicyUpdate(db_password="new_secret")
            updated = svc.update_backup_policy(created.id, update)

    def test_update_backup_policy_with_empty_password(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.MYSQL,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        update = BackupPolicyUpdate(db_password="")
        updated = svc.update_backup_policy(created.id, update)

    def test_update_backup_policy_no_changes(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        update = BackupPolicyUpdate()
        updated = svc.update_backup_policy(created.id, update)
        assert updated.name == "p1"

    def test_update_backup_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        update = BackupPolicyUpdate(name="x")
        with pytest.raises(ValueError, match="不存在"):
            svc.update_backup_policy("nonexistent-id", update)

    def test_update_backup_policy_with_storage_config(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        update = BackupPolicyUpdate(storage_config={"path": "/new/backup"})
        updated = svc.update_backup_policy(created.id, update)

    def test_delete_backup_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="p1", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
        )
        created = svc.create_backup_policy("server1", data)
        svc.delete_backup_policy(created.id)
        assert svc.get_backup_policy(created.id) is None

    def test_delete_backup_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.delete_backup_policy("nonexistent-id")

    def test_create_backup_policy_disabled(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.append((0, "", ""))
        data = BackupPolicyCreate(
            name="disabled-p", backup_type=BackupType.WEBSITE,
            storage_type=StorageType.LOCAL, storage_config={},
            cron_expression="0 * * * *",
            status=TaskStatus.DISABLED,
        )
        policy = svc.create_backup_policy("server1", data)
        assert policy.status == TaskStatus.DISABLED


class TestBackupScript:
    def _make_policy(self, **overrides):
        defaults = dict(
            name="web-backup",
            backup_type=BackupType.WEBSITE,
            source_path="/var/www/html",
            compression=CompressionType.TAR_GZ,
            db_name=None,
            db_host=None,
            db_port=None,
            db_username=None,
            db_password_encrypted=None,
            storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"},
            retention_count=7,
        )
        defaults.update(overrides)
        policy = MagicMock()
        for k, v in defaults.items():
            setattr(policy, k, v)
        return policy

    def test_build_backup_script_website_tar_gz(self, tmp_db):
        policy = self._make_policy()
        script = tmp_db._build_backup_script(policy)
        assert "#!/bin/bash" in script
        assert "tar -czf" in script

    def test_build_backup_script_website_zip(self, tmp_db):
        policy = self._make_policy(compression=CompressionType.ZIP)
        script = tmp_db._build_backup_script(policy)
        assert "zip -r" in script

    def test_build_backup_script_website_none(self, tmp_db):
        policy = self._make_policy(compression=CompressionType.NONE)
        script = tmp_db._build_backup_script(policy)
        assert "cp -r" in script

    def test_build_backup_script_mysql_tar_gz(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.MYSQL, db_name="mydb",
            db_host="localhost", db_port=3306, db_username="root",
            db_password_encrypted="enc_pwd", compression=CompressionType.TAR_GZ,
        )
        with patch("app.services.cron_backup_service.decrypt", return_value="secret"):
            script = tmp_db._build_backup_script(policy)
        assert "mysqldump" in script
        assert "gzip" in script

    def test_build_backup_script_mysql_zip(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.MYSQL, db_name="mydb",
            db_host="localhost", db_port=3306, db_username="root",
            db_password_encrypted="enc_pwd", compression=CompressionType.ZIP,
        )
        with patch("app.services.cron_backup_service.decrypt", return_value="secret"):
            script = tmp_db._build_backup_script(policy)
        assert "mysqldump" in script
        assert "zip" in script

    def test_build_backup_script_mysql_none(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.MYSQL, db_name="mydb",
            db_host="localhost", db_port=3306, db_username="root",
            db_password_encrypted="enc_pwd", compression=CompressionType.NONE,
        )
        with patch("app.services.cron_backup_service.decrypt", return_value="secret"):
            script = tmp_db._build_backup_script(policy)
        assert "mysqldump" in script
        assert "$BACKUP_FILE.sql" in script

    def test_build_backup_script_mysql_no_password(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.MYSQL, db_name="mydb",
            db_host="localhost", db_port=3306, db_username="root",
            compression=CompressionType.TAR_GZ,
        )
        script = tmp_db._build_backup_script(policy)
        assert "mysqldump" in script
        assert "-p'" not in script

    def test_build_backup_script_postgresql_tar_gz(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.POSTGRESQL, db_name="pgdb",
            db_host="localhost", db_port=5432, db_username="postgres",
            db_password_encrypted="pg_pwd", compression=CompressionType.TAR_GZ,
        )
        script = tmp_db._build_backup_script(policy)
        assert "pg_dump" in script
        assert "gzip" in script

    def test_build_backup_script_postgresql_zip(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.POSTGRESQL, db_name="pgdb",
            db_host="localhost", db_port=5432, db_username="postgres",
            db_password_encrypted="pg_pwd", compression=CompressionType.ZIP,
        )
        script = tmp_db._build_backup_script(policy)
        assert "pg_dump" in script
        assert "zip" in script

    def test_build_backup_script_postgresql_none(self, tmp_db):
        policy = self._make_policy(
            backup_type=BackupType.POSTGRESQL, db_name="pgdb",
            db_host="localhost", db_port=5432, db_username="postgres",
            db_password_encrypted="pg_pwd", compression=CompressionType.NONE,
        )
        script = tmp_db._build_backup_script(policy)
        assert "pg_dump" in script
        assert "$BACKUP_FILE.dump" in script

    def test_build_backup_script_custom(self, tmp_db):
        policy = self._make_policy(backup_type=BackupType.CUSTOM, source_path="/data")
        script = tmp_db._build_backup_script(policy)
        assert "tar -czf" in script

    def test_build_backup_script_no_retention(self, tmp_db):
        policy = self._make_policy(retention_count=0)
        script = tmp_db._build_backup_script(policy)
        assert "tail -n" not in script

    def test_build_backup_script_website_no_source(self, tmp_db):
        policy = self._make_policy(source_path=None)
        script = tmp_db._build_backup_script(policy)
        assert "/var/www/html" in script


class TestStorageUploadLines:
    def test_local_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.LOCAL
        policy.storage_config = {"path": "/backup"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("mkdir -p '/backup'" in l for l in lines)
        assert any("cp " in l for l in lines)

    def test_aliyun_oss_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.ALIYUN_OSS
        policy.storage_config = {"bucket": "my-bucket", "endpoint": "oss-cn-hangzhou.aliyuncs.com", "prefix": "backups"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("aliyun oss cp" in l for l in lines)

    def test_tencent_cos_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.TENCENT_COS
        policy.storage_config = {"bucket": "my-bucket", "region": "ap-guangzhou", "prefix": "backups"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("coscli cp" in l for l in lines)

    def test_aws_s3_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.AWS_S3
        policy.storage_config = {"bucket": "my-bucket", "prefix": "backups"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("aws s3 cp" in l for l in lines)

    def test_sftp_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.SFTP
        policy.storage_config = {"host": "1.2.3.4", "port": 22, "username": "user", "password": "pass", "remote_dir": "/backup"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("sftp" in l for l in lines)

    def test_ftp_storage(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.FTP
        policy.storage_config = {"host": "1.2.3.4", "port": 21, "username": "user", "password": "pass", "remote_dir": "/backup"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("curl -T" in l for l in lines)

    def test_local_storage_default_path(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.LOCAL
        policy.storage_config = {}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("/backup" in l for l in lines)

    def test_aliyun_oss_default_prefix(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.ALIYUN_OSS
        policy.storage_config = {"bucket": "b", "endpoint": "e"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("opsv-backups" in l for l in lines)

    def test_sftp_default_port(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.SFTP
        policy.storage_config = {"host": "h", "username": "u", "password": "p"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any("-P 22" in l for l in lines)

    def test_ftp_default_port(self, tmp_db):
        policy = MagicMock()
        policy.storage_type = StorageType.FTP
        policy.storage_config = {"host": "h", "username": "u", "password": "p"}
        lines = tmp_db._build_storage_upload_lines(policy)
        assert any(":21" in l for l in lines)


class TestBackupHistory:
    def test_add_and_list_backup_history(self, tmp_db):
        history = BackupHistory(
            id="hist-1", policy_id="pol-1", policy_name="test-policy",
            backup_type=BackupType.WEBSITE, storage_type=StorageType.LOCAL,
            status="success", account_alias="server1",
        )
        tmp_db.add_backup_history(history)
        histories = tmp_db.list_backup_history("server1")
        assert len(histories) == 1
        assert histories[0].policy_name == "test-policy"

    def test_list_backup_history_with_policy_id(self, tmp_db):
        h1 = BackupHistory(
            id="hist-1", policy_id="pol-1", policy_name="p1",
            backup_type=BackupType.WEBSITE, storage_type=StorageType.LOCAL,
            status="success", account_alias="server1",
        )
        h2 = BackupHistory(
            id="hist-2", policy_id="pol-2", policy_name="p2",
            backup_type=BackupType.MYSQL, storage_type=StorageType.LOCAL,
            status="failed", account_alias="server1",
        )
        tmp_db.add_backup_history(h1)
        tmp_db.add_backup_history(h2)
        histories = tmp_db.list_backup_history("server1", policy_id="pol-1")
        assert len(histories) == 1
        assert histories[0].policy_id == "pol-1"

    def test_list_backup_history_empty(self, tmp_db):
        histories = tmp_db.list_backup_history("nonexistent")
        assert histories == []


class TestRunBackupNow:
    def test_run_backup_now_success(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([
            (0, "", ""),
            (0, "", ""),
            (0, "BACKUP_DONE", ""),
            (0, "1024 /tmp/opsv_backups/test_20240101_000000.tar.gz", ""),
        ])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        results.extend([(0, "", ""), (0, "", "")])
        policy = svc.create_backup_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (0, "BACKUP_DONE", ""),
            (0, "1024 /tmp/opsv_backups/test_20240101_000000.tar.gz", ""),
        ])
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "success"

    def test_run_backup_now_failed(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (1, "error output", "some error"),
        ])
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "failed"

    def test_run_backup_now_no_backup_done(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (0, "no marker", ""),
        ])
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "failed"

    def test_run_backup_now_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.run_backup_now("nonexistent-id")

    def test_run_backup_now_exception(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)

        def raise_exec(alias, cmd, timeout=30.0):
            raise Exception("SSH connection lost")

        svc._exec = raise_exec
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "failed"
        assert "SSH connection lost" in result["error"]

    def test_run_backup_now_success_file_size_invalid(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (0, "BACKUP_DONE", ""),
            (0, "invalid output", ""),
        ])
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "success"

    def test_run_backup_now_success_file_size_parse(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = BackupPolicyCreate(
            name="test-backup", backup_type=BackupType.WEBSITE,
            source_path="/var/www/html", storage_type=StorageType.LOCAL,
            storage_config={"path": "/backup"}, cron_expression="0 2 * * *",
        )
        policy = svc.create_backup_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (0, "BACKUP_DONE", ""),
            (0, "2048 /tmp/opsv_backups/test_20240101_000000.tar.gz", ""),
        ])
        result = svc.run_backup_now(policy.id)
        assert result["status"] == "success"


class TestLogPolicyCRUD:
    def test_create_log_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="log-cleanup", log_path_pattern="/var/log/nginx/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        assert policy.name == "log-cleanup"
        assert policy.retention_days == 30
        assert policy.cleanup_action == CleanupAction.DELETE

    def test_list_log_policies(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", ""), (0, "", "")])
        data1 = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log", cron_expression="0 4 * * *",
        )
        data2 = LogRetentionPolicyCreate(
            name="lp2", log_path_pattern="/tmp/*.log", cron_expression="0 5 * * *",
        )
        svc.create_log_policy("server1", data1)
        svc.create_log_policy("server1", data2)
        policies = svc.list_log_policies("server1")
        assert len(policies) == 2

    def test_list_log_policies_empty(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        policies = svc.list_log_policies("nonexistent")
        assert policies == []

    def test_get_log_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log", cron_expression="0 4 * * *",
        )
        created = svc.create_log_policy("server1", data)
        found = svc.get_log_policy(created.id)
        assert found is not None
        assert found.name == "lp1"

    def test_get_log_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        result = svc.get_log_policy("nonexistent-id")
        assert result is None

    def test_update_log_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log", cron_expression="0 4 * * *",
        )
        created = svc.create_log_policy("server1", data)
        update = LogRetentionPolicyUpdate(name="updated-lp", retention_days=60)
        updated = svc.update_log_policy(created.id, update)
        assert updated.name == "updated-lp"
        assert updated.retention_days == 60

    def test_update_log_policy_no_changes(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log", cron_expression="0 4 * * *",
        )
        created = svc.create_log_policy("server1", data)
        update = LogRetentionPolicyUpdate()
        updated = svc.update_log_policy(created.id, update)
        assert updated.name == "lp1"

    def test_update_log_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        update = LogRetentionPolicyUpdate(name="x")
        with pytest.raises(ValueError, match="不存在"):
            svc.update_log_policy("nonexistent-id", update)

    def test_delete_log_policy(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log", cron_expression="0 4 * * *",
        )
        created = svc.create_log_policy("server1", data)
        svc.delete_log_policy(created.id)
        assert svc.get_log_policy(created.id) is None

    def test_delete_log_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.delete_log_policy("nonexistent-id")


class TestLogCleanupScript:
    def test_build_log_cleanup_delete(self, tmp_db):
        policy = MagicMock()
        policy.log_path_pattern = "/var/log/nginx/*.log"
        policy.retention_days = 30
        policy.cleanup_action = CleanupAction.DELETE
        policy.archive_path = None
        script = tmp_db._build_log_cleanup_script(policy)
        assert "find /var/log/nginx/*.log -type f -mtime +30 -delete" in script

    def test_build_log_cleanup_compress(self, tmp_db):
        policy = MagicMock()
        policy.log_path_pattern = "/var/log/*.log"
        policy.retention_days = 14
        policy.cleanup_action = CleanupAction.COMPRESS
        policy.archive_path = "/archive"
        script = tmp_db._build_log_cleanup_script(policy)
        assert "tar -czf" in script
        assert "mkdir -p '/archive'" in script

    def test_build_log_cleanup_compress_default_archive(self, tmp_db):
        policy = MagicMock()
        policy.log_path_pattern = "/var/log/*.log"
        policy.retention_days = 14
        policy.cleanup_action = CleanupAction.COMPRESS
        policy.archive_path = None
        script = tmp_db._build_log_cleanup_script(policy)
        assert "/var/log/archive" in script

    def test_build_log_cleanup_move(self, tmp_db):
        policy = MagicMock()
        policy.log_path_pattern = "/var/log/*.log"
        policy.retention_days = 7
        policy.cleanup_action = CleanupAction.MOVE
        policy.archive_path = "/archive"
        script = tmp_db._build_log_cleanup_script(policy)
        assert "mv" in script
        assert "mkdir -p '/archive'" in script

    def test_build_log_cleanup_move_default_archive(self, tmp_db):
        policy = MagicMock()
        policy.log_path_pattern = "/var/log/*.log"
        policy.retention_days = 7
        policy.cleanup_action = CleanupAction.MOVE
        policy.archive_path = None
        script = tmp_db._build_log_cleanup_script(policy)
        assert "/var/log/archive" in script


class TestLogCleanupPreviewAndRun:
    def test_preview_log_cleanup(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        results.clear()
        results.append((
            0,
            "/var/log/app.log|1024|2024-01-15 10:30:00\n/var/log/old.log|2048|2024-01-10 05:00:00",
            "",
        ))
        files = svc.preview_log_cleanup(policy.id)
        assert len(files) == 2
        assert files[0].path == "/var/log/app.log"
        assert files[0].size == 1024

    def test_preview_log_cleanup_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.preview_log_cleanup("nonexistent-id")

    def test_preview_log_cleanup_invalid_line(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        results.clear()
        results.append((
            0,
            "invalid_line\n/valid/log|100|2024-01-15 10:30:00\nshort",
            "",
        ))
        files = svc.preview_log_cleanup(policy.id)
        assert len(files) == 1

    def test_preview_log_cleanup_empty(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        results.clear()
        results.append((0, "", ""))
        files = svc.preview_log_cleanup(policy.id)
        assert files == []

    def test_run_log_cleanup_now_success(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (0, "LOG_CLEANUP_DONE", ""),
        ])
        result = svc.run_log_cleanup_now(policy.id)
        assert result["status"] == "success"

    def test_run_log_cleanup_now_failed(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([(0, "", ""), (0, "", "")])
        data = LogRetentionPolicyCreate(
            name="lp1", log_path_pattern="/var/log/*.log",
            retention_days=30, cleanup_action=CleanupAction.DELETE,
            cron_expression="0 4 * * *",
        )
        policy = svc.create_log_policy("server1", data)
        results.clear()
        results.extend([
            (0, "", ""),
            (1, "error", "fail"),
        ])
        result = svc.run_log_cleanup_now(policy.id)
        assert result["status"] == "failed"

    def test_run_log_cleanup_now_policy_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        with pytest.raises(ValueError, match="不存在"):
            svc.run_log_cleanup_now("nonexistent-id")


class TestDiskAlert:
    def test_get_disk_alert_with_alerts(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        df_output = (
            "Filesystem     Size  Used Avail Use% Mounted on\n"
            "/dev/sda1       50G   45G    5G  90% /\n"
            "/dev/sda2      100G   30G   70G  30% /home"
        )
        du_output = "4.0G\t/var/log/nginx"
        results.extend([
            (0, df_output, ""),
            (0, du_output, ""),
        ])
        result = svc.get_disk_alert("server1")
        assert result["has_alert"] is True
        assert len(result["alerts"]) == 1
        assert result["alerts"][0].use_percent == 90

    def test_get_disk_alert_no_alerts(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        df_output = (
            "Filesystem     Size  Used Avail Use% Mounted on\n"
            "/dev/sda1       50G   20G   30G  40% /"
        )
        results.extend([
            (0, df_output, ""),
            (1, "", ""),
        ])
        result = svc.get_disk_alert("server1")
        assert result["has_alert"] is False

    def test_get_disk_alert_df_fail(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        results.extend([
            (1, "", "error"),
            (1, "", ""),
        ])
        result = svc.get_disk_alert("server1")
        assert result["has_alert"] is False
        assert result["disk_usage"] == []

    def test_get_disk_alert_malformed_line(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        df_output = (
            "Filesystem     Size  Used Avail Use% Mounted on\n"
            "short line\n"
            "/dev/sda1       50G   45G    5G  90% /"
        )
        results.extend([
            (0, df_output, ""),
            (1, "", ""),
        ])
        result = svc.get_disk_alert("server1")
        assert len(result["disk_usage"]) == 1

    def test_get_disk_alert_log_sizes(self, svc_with_mock_exec):
        svc, results = svc_with_mock_exec
        df_output = "Filesystem     Size  Used Avail Use% Mounted on\n"
        du_output = "4.0G\t/var/log/nginx\n2.0G\t/var/log/mysql"
        results.extend([
            (0, df_output, ""),
            (0, du_output, ""),
        ])
        result = svc.get_disk_alert("server1")
        assert len(result["log_sizes"]) == 2


class TestExecutionLog:
    def test_add_and_list_execution_log(self, tmp_db):
        log = ExecutionLog(
            id="log-1", task_id="task-1", task_type="cron",
            task_name="test-task", status="success", exit_code=0,
            account_alias="server1",
        )
        tmp_db.add_execution_log(log)
        logs = tmp_db.list_execution_logs("server1")
        assert len(logs) == 1
        assert logs[0].task_name == "test-task"

    def test_list_execution_logs_with_task_id(self, tmp_db):
        l1 = ExecutionLog(
            id="log-1", task_id="task-1", task_type="cron",
            task_name="t1", status="success", account_alias="server1",
        )
        l2 = ExecutionLog(
            id="log-2", task_id="task-2", task_type="backup",
            task_name="t2", status="failed", account_alias="server1",
        )
        tmp_db.add_execution_log(l1)
        tmp_db.add_execution_log(l2)
        logs = tmp_db.list_execution_logs("server1", task_id="task-1")
        assert len(logs) == 1
        assert logs[0].task_id == "task-1"

    def test_list_execution_logs_empty(self, tmp_db):
        logs = tmp_db.list_execution_logs("nonexistent")
        assert logs == []


class TestDownloadBackupFile:
    def test_download_backup_file(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        mock_conn = MagicMock()
        mock_sftp = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.read.return_value = b"backup data"
        mock_sftp.file.return_value = mock_file
        mock_conn.manager.open_sftp.return_value = mock_sftp
        svc._get_ssh_conn = MagicMock(return_value=mock_conn)
        data = svc.download_backup_file("server1", "/backup/file.tar.gz")
        assert data == b"backup data"

    def test_download_backup_file_ssh_not_found(self, svc_with_mock_exec):
        svc, _ = svc_with_mock_exec
        svc._get_ssh_conn = MagicMock(side_effect=ValueError("SSH 账户 'nonexistent' 不存在"))
        with pytest.raises(ValueError, match="不存在"):
            svc.download_backup_file("nonexistent", "/backup/file.tar.gz")


class TestSSHExec:
    def test_exec_with_bytes_output(self, tmp_db):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, b"output", b"error")
        with patch("app.services.ssh_account_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = MagicMock()
            mock_svc.pool.get_connection.return_value = mock_conn
            mock_svc.pool.release_connection.return_value = None
            code, stdout, stderr = tmp_db._exec("server1", "ls")
        assert code == 0
        assert stdout == "output"
        assert stderr == "error"

    def test_exec_ssh_account_not_found(self, tmp_db):
        with patch("app.services.ssh_account_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                tmp_db._exec("nonexistent", "ls")

    def test_get_ssh_conn(self, tmp_db):
        mock_conn = MagicMock()
        with patch("app.services.ssh_account_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = MagicMock()
            mock_svc.pool.get_connection.return_value = mock_conn
            conn = tmp_db._get_ssh_conn("server1")
        assert conn is not None
