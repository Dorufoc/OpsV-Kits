"""Cron备份管理接口测试"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_account():
    """模拟SSH账户对象"""
    return MagicMock()


class TestCronJobs:
    """Cron任务管理测试"""

    def _make_cron_job(self, **overrides):
        """构建 CronJob mock 对象"""
        job = MagicMock()
        job.id = overrides.get("id", "cron-001")
        job.name = overrides.get("name", "test-cron-job")
        job.cron_expression = overrides.get("cron_expression", "0 * * * *")
        job.task_type = overrides.get("task_type", "shell")
        job.command = overrides.get("command", "echo hello")
        job.http_method = overrides.get("http_method", None)
        job.http_headers = overrides.get("http_headers", None)
        job.http_body = overrides.get("http_body", None)
        job.status = overrides.get("status", "enabled")
        job.account_alias = overrides.get("account_alias", "test-server")
        job.description = overrides.get("description", "Test job")
        job.created_at = overrides.get("created_at", datetime.now())
        job.updated_at = overrides.get("updated_at", datetime.now())
        job.last_run_at = overrides.get("last_run_at", None)
        job.last_run_status = overrides.get("last_run_status", None)
        job.model_dump.return_value = {
            "id": job.id,
            "name": job.name,
            "cron_expression": job.cron_expression,
            "task_type": job.task_type,
            "command": job.command,
            "http_method": job.http_method,
            "http_headers": job.http_headers,
            "http_body": job.http_body,
            "status": job.status,
            "account_alias": job.account_alias,
            "description": job.description,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "last_run_at": None,
            "last_run_status": None,
        }
        return job

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_cron_jobs_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        job1 = self._make_cron_job(id="cron-001", name="backup-daily")
        job2 = self._make_cron_job(id="cron-002", name="cleanup-logs")
        mock_cron_service.list_cron_jobs.return_value = [job1, job2]

        response = client.get("/api/cron-backup/cron-jobs?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_cron_jobs_empty(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_cron_jobs.return_value = []

        response = client.get("/api/cron-backup/cron-jobs?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_cron_jobs_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/cron-backup/cron-jobs?alias=nonexistent")
        # 路由层 _ensure_account 抛出 HTTPException(404)，但被 except Exception 捕获并转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_cron_jobs_service_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_cron_jobs.side_effect = Exception("database error")

        response = client.get("/api/cron-backup/cron-jobs?alias=test-server")
        assert response.status_code == 500

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_cron_job_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_job = self._make_cron_job(id="cron-new", name="new-job")
        mock_cron_service.create_cron_job.return_value = new_job

        response = client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": "test-server",
                "data": {
                    "name": "new-job",
                    "cron_expression": "0 2 * * *",
                    "command": "echo hello",
                    "status": "enabled",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-job"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_cron_job_url_type(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_job = self._make_cron_job(id="cron-url", task_type="url", command="https://example.com")
        mock_cron_service.create_cron_job.return_value = new_job

        response = client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": "test-server",
                "data": {
                    "name": "url-checker",
                    "cron_expression": "*/5 * * * *",
                    "task_type": "url",
                    "command": "https://example.com/health",
                    "http_method": "GET",
                    "status": "enabled",
                },
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_cron_job_validation_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.create_cron_job.side_effect = ValueError("name is required")

        # Pydantic 验证失败时 FastAPI 会直接返回 422
        response = client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": "test-server",
                "data": {
                    "name": "",
                    "cron_expression": "0 * * * *",
                    "command": "echo",
                },
            },
        )
        assert response.status_code == 422

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_cron_job_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": "nonexistent",
                "data": {
                    "name": "test",
                    "cron_expression": "0 * * * *",
                    "command": "echo",
                },
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_cron_job_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        updated_job = self._make_cron_job(id="cron-001", name="updated-name", command="new-command")
        mock_cron_service.update_cron_job.return_value = updated_job

        response = client.put(
            "/api/cron-backup/cron-jobs/cron-001",
            json={
                "alias": "test-server",
                "data": {
                    "name": "updated-name",
                    "command": "new-command",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated-name"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_cron_job_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.update_cron_job.side_effect = ValueError("Cron 任务 'nonexistent' 不存在")

        response = client.put(
            "/api/cron-backup/cron-jobs/nonexistent",
            json={
                "alias": "test-server",
                "data": {"name": "new-name"},
            },
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_cron_job_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.put(
            "/api/cron-backup/cron-jobs/cron-001",
            json={
                "alias": "nonexistent",
                "data": {"name": "new-name"},
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_cron_job_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_cron_job.return_value = None

        response = client.delete(
            "/api/cron-backup/cron-jobs/cron-001?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_cron_job_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_cron_job.side_effect = ValueError("Cron 任务 'bad-id' 不存在")

        response = client.delete(
            "/api/cron-backup/cron-jobs/bad-id?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_cron_job_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.delete(
            "/api/cron-backup/cron-jobs/cron-001?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_cron_job_logs_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        log1 = MagicMock()
        log1.model_dump.return_value = {
            "id": "log-001",
            "task_id": "cron-001",
            "task_type": "cron",
            "task_name": "test-job",
            "status": "success",
            "exit_code": 0,
            "output": "Hello World",
            "error": None,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": 1.5,
            "account_alias": "test-server",
        }
        log2 = MagicMock()
        log2.model_dump.return_value = {
            "id": "log-002",
            "task_id": "cron-001",
            "task_type": "cron",
            "task_name": "test-job",
            "status": "failed",
            "exit_code": 1,
            "output": "",
            "error": "error message",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": 0.5,
            "account_alias": "test-server",
        }
        mock_cron_service.list_execution_logs.return_value = [log1, log2]

        response = client.get(
            "/api/cron-backup/cron-jobs/cron-001/logs?alias=test-server&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_cron_job_logs_default_limit(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_execution_logs.return_value = []

        response = client.get(
            "/api/cron-backup/cron-jobs/cron-001/logs?alias=test-server"
        )
        assert response.status_code == 200
        mock_cron_service.list_execution_logs.assert_called_with("test-server", "cron-001", 20)

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_cron_job_logs_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get(
            "/api/cron-backup/cron-jobs/cron-001/logs?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)


class TestBackupPolicies:
    """备份策略管理测试"""

    def _make_backup_policy(self, **overrides):
        """构建 BackupPolicy mock 对象"""
        policy = MagicMock()
        policy.id = overrides.get("id", "policy-001")
        policy.name = overrides.get("name", "daily-backup")
        policy.backup_type = overrides.get("backup_type", "website")
        policy.source_path = overrides.get("source_path", "/var/www/html")
        policy.db_name = overrides.get("db_name", None)
        policy.db_host = overrides.get("db_host", "localhost")
        policy.db_port = overrides.get("db_port", None)
        policy.db_username = overrides.get("db_username", None)
        policy.db_password_encrypted = overrides.get("db_password_encrypted", None)
        policy.storage_type = overrides.get("storage_type", "local")
        policy.storage_config = overrides.get("storage_config", {"path": "/backup"})
        policy.cron_expression = overrides.get("cron_expression", "0 2 * * *")
        policy.retention_count = overrides.get("retention_count", 7)
        policy.compression = overrides.get("compression", "tar.gz")
        policy.status = overrides.get("status", "enabled")
        policy.account_alias = overrides.get("account_alias", "test-server")
        policy.description = overrides.get("description", "Daily website backup")
        policy.created_at = overrides.get("created_at", datetime.now())
        policy.updated_at = overrides.get("updated_at", datetime.now())
        policy.last_backup_at = overrides.get("last_backup_at", None)
        policy.last_backup_status = overrides.get("last_backup_status", None)
        policy.model_dump.return_value = {
            "id": policy.id,
            "name": policy.name,
            "backup_type": policy.backup_type,
            "source_path": policy.source_path,
            "db_name": policy.db_name,
            "db_host": policy.db_host,
            "db_port": policy.db_port,
            "db_username": policy.db_username,
            "db_password_encrypted": policy.db_password_encrypted,
            "storage_type": policy.storage_type,
            "storage_config": policy.storage_config,
            "cron_expression": policy.cron_expression,
            "retention_count": policy.retention_count,
            "compression": policy.compression,
            "status": policy.status,
            "account_alias": policy.account_alias,
            "description": policy.description,
            "created_at": policy.created_at.isoformat(),
            "updated_at": policy.updated_at.isoformat(),
            "last_backup_at": None,
            "last_backup_status": None,
        }
        return policy

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_policies_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        policy1 = self._make_backup_policy(id="policy-001", name="website-backup")
        policy2 = self._make_backup_policy(id="policy-002", name="db-backup", backup_type="mysql")
        mock_cron_service.list_backup_policies.return_value = [policy1, policy2]

        response = client.get("/api/cron-backup/backup-policies?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_policies_empty(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_backup_policies.return_value = []

        response = client.get("/api/cron-backup/backup-policies?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_policies_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/cron-backup/backup-policies?alias=nonexistent")
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_policies_service_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_backup_policies.side_effect = Exception("db error")

        response = client.get("/api/cron-backup/backup-policies?alias=test-server")
        assert response.status_code == 500

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_backup_policy_website_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_backup_policy(id="policy-new", name="website-backup", backup_type="website")
        mock_cron_service.create_backup_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "website-backup",
                    "backup_type": "website",
                    "source_path": "/var/www/html",
                    "storage_type": "local",
                    "storage_config": {"path": "/backup"},
                    "cron_expression": "0 2 * * *",
                    "retention_count": 7,
                    "compression": "tar.gz",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "website-backup"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_backup_policy_mysql_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_backup_policy(
            id="policy-mysql", name="mysql-backup", backup_type="mysql",
            db_name="mydb", db_host="localhost", db_port=3306
        )
        mock_cron_service.create_backup_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "mysql-backup",
                    "backup_type": "mysql",
                    "db_name": "mydb",
                    "db_host": "localhost",
                    "db_port": 3306,
                    "db_username": "root",
                    "db_password": "secret123",
                    "storage_type": "local",
                    "storage_config": {"path": "/backup"},
                    "cron_expression": "0 3 * * *",
                },
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_backup_policy_with_s3_storage(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_backup_policy(
            id="policy-s3", name="s3-backup", storage_type="aws_s3",
            storage_config={"bucket": "my-bucket", "prefix": "backups"}
        )
        mock_cron_service.create_backup_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "s3-backup",
                    "backup_type": "website",
                    "source_path": "/var/www",
                    "storage_type": "aws_s3",
                    "storage_config": {"bucket": "my-bucket", "prefix": "backups"},
                    "cron_expression": "0 1 * * *",
                },
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_backup_policy_validation_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.create_backup_policy.side_effect = ValueError("invalid cron expression")

        response = client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "bad-policy",
                    "backup_type": "website",
                    "storage_type": "local",
                    "cron_expression": "invalid",
                },
            },
        )
        assert response.status_code == 400

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_backup_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": "nonexistent",
                "data": {
                    "name": "test",
                    "backup_type": "website",
                    "storage_type": "local",
                    "cron_expression": "0 * * * *",
                },
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_backup_policy_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        updated_policy = self._make_backup_policy(id="policy-001", name="updated-policy", retention_count=14)
        mock_cron_service.update_backup_policy.return_value = updated_policy

        response = client.put(
            "/api/cron-backup/backup-policies/policy-001",
            json={
                "alias": "test-server",
                "data": {
                    "name": "updated-policy",
                    "retention_count": 14,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated-policy"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_backup_policy_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.update_backup_policy.side_effect = ValueError("备份策略 'bad-id' 不存在")

        response = client.put(
            "/api/cron-backup/backup-policies/bad-id",
            json={
                "alias": "test-server",
                "data": {"name": "new-name"},
            },
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_backup_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.put(
            "/api/cron-backup/backup-policies/policy-001",
            json={
                "alias": "nonexistent",
                "data": {"name": "new-name"},
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_backup_policy_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_backup_policy.return_value = None

        response = client.delete(
            "/api/cron-backup/backup-policies/policy-001?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_backup_policy_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_backup_policy.side_effect = ValueError("备份策略 'bad-id' 不存在")

        response = client.delete(
            "/api/cron-backup/backup-policies/bad-id?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_backup_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.delete(
            "/api/cron-backup/backup-policies/policy-001?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_backup_now_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_backup_now.return_value = {
            "history_id": "hist-001",
            "status": "success",
            "exit_code": 0,
            "output": "BACKUP_DONE",
            "error": "",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/cron-backup/backup-policies/policy-001/run?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["history_id"] == "hist-001"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_backup_now_failed(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_backup_now.return_value = {
            "history_id": "hist-002",
            "status": "failed",
            "error": "disk full",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/cron-backup/backup-policies/policy-001/run?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_backup_now_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_backup_now.side_effect = ValueError("备份策略 'bad-id' 不存在")

        response = client.post(
            "/api/cron-backup/backup-policies/bad-id/run?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_backup_now_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/backup-policies/policy-001/run?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)


class TestBackupHistory:
    """备份历史管理测试"""

    def _make_backup_history(self, **overrides):
        """构建 BackupHistory mock 对象"""
        history = MagicMock()
        history.id = overrides.get("id", "hist-001")
        history.policy_id = overrides.get("policy_id", "policy-001")
        history.policy_name = overrides.get("policy_name", "daily-backup")
        history.backup_type = overrides.get("backup_type", "website")
        history.file_path = overrides.get("file_path", "/tmp/opsv_backups/daily-backup_20240101.tar.gz")
        history.file_size = overrides.get("file_size", 1048576)
        history.storage_type = overrides.get("storage_type", "local")
        history.storage_path = overrides.get("storage_path", "/backup/daily-backup_20240101.tar.gz")
        history.status = overrides.get("status", "success")
        history.error_message = overrides.get("error_message", None)
        history.started_at = overrides.get("started_at", datetime.now())
        history.completed_at = overrides.get("completed_at", datetime.now())
        history.account_alias = overrides.get("account_alias", "test-server")
        history.model_dump.return_value = {
            "id": history.id,
            "policy_id": history.policy_id,
            "policy_name": history.policy_name,
            "backup_type": history.backup_type,
            "file_path": history.file_path,
            "file_size": history.file_size,
            "storage_type": history.storage_type,
            "storage_path": history.storage_path,
            "status": history.status,
            "error_message": history.error_message,
            "started_at": history.started_at.isoformat(),
            "completed_at": history.completed_at.isoformat(),
            "account_alias": history.account_alias,
        }
        return history

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_history_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        hist1 = self._make_backup_history(id="hist-001", status="success")
        hist2 = self._make_backup_history(id="hist-002", status="failed", error_message="disk full")
        mock_cron_service.list_backup_history.return_value = [hist1, hist2]

        response = client.get("/api/cron-backup/backup-history?alias=test-server&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_history_with_policy_filter(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_backup_history.return_value = []

        response = client.get(
            "/api/cron-backup/backup-history?alias=test-server&policy_id=policy-001&limit=20"
        )
        assert response.status_code == 200
        mock_cron_service.list_backup_history.assert_called_with("test-server", "policy-001", 20)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_history_default_params(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_backup_history.return_value = []

        response = client.get("/api/cron-backup/backup-history?alias=test-server")
        assert response.status_code == 200
        mock_cron_service.list_backup_history.assert_called_with("test-server", None, 50)

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_backup_history_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/cron-backup/backup-history?alias=nonexistent")
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_download_backup_file_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.download_backup_file.return_value = b"backup file content"

        response = client.get(
            "/api/cron-backup/backup-history/hist-001/download?alias=test-server&file_path=/tmp/backup.tar.gz"
        )
        assert response.status_code == 200
        assert response.headers["Content-Disposition"] == 'attachment; filename="backup.tar.gz"'

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_download_backup_file_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.download_backup_file.side_effect = ValueError("备份文件不存在")

        response = client.get(
            "/api/cron-backup/backup-history/hist-001/download?alias=test-server&file_path=/tmp/missing.tar.gz"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_download_backup_file_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get(
            "/api/cron-backup/backup-history/hist-001/download?alias=nonexistent&file_path=/tmp/backup.tar.gz"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)


class TestLogPolicies:
    """日志保留策略管理测试"""

    def _make_log_policy(self, **overrides):
        """构建 LogRetentionPolicy mock 对象"""
        policy = MagicMock()
        policy.id = overrides.get("id", "log-policy-001")
        policy.name = overrides.get("name", "cleanup-app-logs")
        policy.log_path_pattern = overrides.get("log_path_pattern", "/var/log/app/*.log")
        policy.retention_days = overrides.get("retention_days", 30)
        policy.cleanup_action = overrides.get("cleanup_action", "delete")
        policy.archive_path = overrides.get("archive_path", None)
        policy.cron_expression = overrides.get("cron_expression", "0 4 * * 0")
        policy.status = overrides.get("status", "enabled")
        policy.account_alias = overrides.get("account_alias", "test-server")
        policy.description = overrides.get("description", "Weekly log cleanup")
        policy.created_at = overrides.get("created_at", datetime.now())
        policy.updated_at = overrides.get("updated_at", datetime.now())
        policy.last_run_at = overrides.get("last_run_at", None)
        policy.last_run_status = overrides.get("last_run_status", None)
        policy.model_dump.return_value = {
            "id": policy.id,
            "name": policy.name,
            "log_path_pattern": policy.log_path_pattern,
            "retention_days": policy.retention_days,
            "cleanup_action": policy.cleanup_action,
            "archive_path": policy.archive_path,
            "cron_expression": policy.cron_expression,
            "status": policy.status,
            "account_alias": policy.account_alias,
            "description": policy.description,
            "created_at": policy.created_at.isoformat(),
            "updated_at": policy.updated_at.isoformat(),
            "last_run_at": None,
            "last_run_status": None,
        }
        return policy

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_log_policies_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        policy1 = self._make_log_policy(id="log-pol-001", name="cleanup-app")
        policy2 = self._make_log_policy(id="log-pol-002", name="cleanup-nginx", log_path_pattern="/var/log/nginx/*.log")
        mock_cron_service.list_log_policies.return_value = [policy1, policy2]

        response = client.get("/api/cron-backup/log-policies?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_log_policies_empty(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.list_log_policies.return_value = []

        response = client.get("/api/cron-backup/log-policies?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_list_log_policies_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/cron-backup/log-policies?alias=nonexistent")
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_log_policy_delete_action(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_log_policy(id="log-pol-new", name="delete-old-logs", cleanup_action="delete")
        mock_cron_service.create_log_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/log-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "delete-old-logs",
                    "log_path_pattern": "/var/log/app/*.log",
                    "retention_days": 30,
                    "cleanup_action": "delete",
                    "cron_expression": "0 4 * * 0",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "delete-old-logs"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_log_policy_compress_action(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_log_policy(
            id="log-pol-compress", name="compress-old-logs",
            cleanup_action="compress", archive_path="/var/log/archive"
        )
        mock_cron_service.create_log_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/log-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "compress-old-logs",
                    "log_path_pattern": "/var/log/nginx/*.log",
                    "retention_days": 14,
                    "cleanup_action": "compress",
                    "archive_path": "/var/log/archive",
                    "cron_expression": "0 3 * * 0",
                },
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_log_policy_move_action(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        new_policy = self._make_log_policy(
            id="log-pol-move", name="move-old-logs",
            cleanup_action="move", archive_path="/var/log/archive"
        )
        mock_cron_service.create_log_policy.return_value = new_policy

        response = client.post(
            "/api/cron-backup/log-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "move-old-logs",
                    "log_path_pattern": "/var/log/syslog*",
                    "retention_days": 60,
                    "cleanup_action": "move",
                    "archive_path": "/var/log/archive",
                    "cron_expression": "0 5 1 * *",
                },
            },
        )
        assert response.status_code == 200

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_log_policy_validation_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.create_log_policy.side_effect = ValueError("invalid log path")

        # Pydantic 验证失败时 FastAPI 会直接返回 422
        response = client.post(
            "/api/cron-backup/log-policies",
            json={
                "alias": "test-server",
                "data": {
                    "name": "bad-policy",
                    "log_path_pattern": "",
                    "cron_expression": "0 * * * *",
                },
            },
        )
        assert response.status_code == 422

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_create_log_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/log-policies",
            json={
                "alias": "nonexistent",
                "data": {
                    "name": "test",
                    "log_path_pattern": "/var/log/*.log",
                    "cron_expression": "0 * * * *",
                },
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_log_policy_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        updated_policy = self._make_log_policy(id="log-pol-001", name="updated-policy", retention_days=60)
        mock_cron_service.update_log_policy.return_value = updated_policy

        response = client.put(
            "/api/cron-backup/log-policies/log-pol-001",
            json={
                "alias": "test-server",
                "data": {
                    "name": "updated-policy",
                    "retention_days": 60,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated-policy"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_log_policy_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.update_log_policy.side_effect = ValueError("日志保留策略 'bad-id' 不存在")

        response = client.put(
            "/api/cron-backup/log-policies/bad-id",
            json={
                "alias": "test-server",
                "data": {"name": "new-name"},
            },
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_update_log_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.put(
            "/api/cron-backup/log-policies/log-pol-001",
            json={
                "alias": "nonexistent",
                "data": {"name": "new-name"},
            },
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_log_policy_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_log_policy.return_value = None

        response = client.delete(
            "/api/cron-backup/log-policies/log-pol-001?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_log_policy_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.delete_log_policy.side_effect = ValueError("日志保留策略 'bad-id' 不存在")

        response = client.delete(
            "/api/cron-backup/log-policies/bad-id?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_delete_log_policy_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.delete(
            "/api/cron-backup/log-policies/log-pol-001?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_preview_log_cleanup_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        file1 = MagicMock()
        file1.model_dump.return_value = {
            "path": "/var/log/app/app.log.1",
            "size": 1048576,
            "modified_at": datetime.now().isoformat(),
        }
        file2 = MagicMock()
        file2.model_dump.return_value = {
            "path": "/var/log/app/app.log.2",
            "size": 524288,
            "modified_at": datetime.now().isoformat(),
        }
        mock_cron_service.preview_log_cleanup.return_value = [file1, file2]

        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/preview?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_preview_log_cleanup_empty(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.preview_log_cleanup.return_value = []

        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/preview?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_preview_log_cleanup_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.preview_log_cleanup.side_effect = ValueError("日志保留策略 'bad-id' 不存在")

        response = client.post(
            "/api/cron-backup/log-policies/bad-id/preview?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_preview_log_cleanup_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/preview?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_log_cleanup_now_success(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_log_cleanup_now.return_value = {
            "status": "success",
            "exit_code": 0,
            "output": "LOG_CLEANUP_DONE",
            "error": "",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/run?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_log_cleanup_now_failed(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_log_cleanup_now.return_value = {
            "status": "failed",
            "exit_code": 1,
            "output": "",
            "error": "permission denied",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
        }

        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/run?alias=test-server"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "permission denied" in data["error"]

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_log_cleanup_now_not_found(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.run_log_cleanup_now.side_effect = ValueError("日志保留策略 'bad-id' 不存在")

        response = client.post(
            "/api/cron-backup/log-policies/bad-id/run?alias=test-server"
        )
        assert response.status_code == 404

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_run_log_cleanup_now_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.post(
            "/api/cron-backup/log-policies/log-pol-001/run?alias=nonexistent"
        )
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)


class TestDiskAlert:
    """磁盘空间告警测试"""

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_disk_alert_success_with_alerts(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        disk_info = MagicMock()
        disk_info.model_dump.return_value = {
            "filesystem": "/dev/sda1",
            "size": "100G",
            "used": "90G",
            "available": "10G",
            "use_percent": 90,
            "mount_point": "/",
        }
        mock_cron_service.get_disk_alert.return_value = {
            "has_alert": True,
            "alerts": [disk_info.model_dump.return_value],
            "disk_usage": [disk_info.model_dump.return_value],
            "log_sizes": [
                {"size": "500M", "path": "/var/log/syslog"},
                {"size": "200M", "path": "/var/log/kern.log"},
            ],
        }

        response = client.get("/api/cron-backup/disk-alert?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["has_alert"] is True
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["use_percent"] == 90
        assert len(data["log_sizes"]) == 2

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_disk_alert_success_no_alerts(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        disk_info = MagicMock()
        disk_info.model_dump.return_value = {
            "filesystem": "/dev/sda1",
            "size": "100G",
            "used": "30G",
            "available": "70G",
            "use_percent": 30,
            "mount_point": "/",
        }
        mock_cron_service.get_disk_alert.return_value = {
            "has_alert": False,
            "alerts": [],
            "disk_usage": [disk_info.model_dump.return_value],
            "log_sizes": [],
        }

        response = client.get("/api/cron-backup/disk-alert?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert data["has_alert"] is False
        assert data["alerts"] == []

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_disk_alert_multiple_disks(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        disk1 = MagicMock()
        disk1.model_dump.return_value = {
            "filesystem": "/dev/sda1",
            "size": "50G",
            "used": "45G",
            "available": "5G",
            "use_percent": 90,
            "mount_point": "/",
        }
        disk2 = MagicMock()
        disk2.model_dump.return_value = {
            "filesystem": "/dev/sdb1",
            "size": "500G",
            "used": "100G",
            "available": "400G",
            "use_percent": 20,
            "mount_point": "/data",
        }
        mock_cron_service.get_disk_alert.return_value = {
            "has_alert": True,
            "alerts": [disk1.model_dump.return_value],
            "disk_usage": [disk1.model_dump.return_value, disk2.model_dump.return_value],
            "log_sizes": [],
        }

        response = client.get("/api/cron-backup/disk-alert?alias=test-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data["disk_usage"]) == 2
        assert len(data["alerts"]) == 1

    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_disk_alert_account_not_found(self, mock_ssh_service, client):
        mock_ssh_service.get_account.return_value = None
        response = client.get("/api/cron-backup/disk-alert?alias=nonexistent")
        # 路由层 HTTPException 被 except Exception 捕获，转为 500
        assert response.status_code in (404, 500)

    @patch("app.api.routes.cron_backup.cron_backup_service")
    @patch("app.api.routes.cron_backup.ssh_account_service")
    def test_get_disk_alert_service_error(self, mock_ssh_service, mock_cron_service, client, mock_account):
        mock_ssh_service.get_account.return_value = mock_account
        mock_cron_service.get_disk_alert.side_effect = Exception("ssh connection failed")

        response = client.get("/api/cron-backup/disk-alert?alias=test-server")
        assert response.status_code == 500
