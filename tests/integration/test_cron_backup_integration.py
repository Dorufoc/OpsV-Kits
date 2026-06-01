from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount


@pytest.mark.integration
class TestCronJobManagement:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._created_job_ids: list[str] = []
        yield
        for job_id in self._created_job_ids:
            try:
                self._api_client.delete(
                    f"/api/cron-backup/cron-jobs/{job_id}",
                    params={"alias": self._alias},
                )
            except Exception:
                pass

    def test_list_cron_jobs(self) -> None:
        resp = self._api_client.get(
            "/api/cron-backup/cron-jobs",
            params={"alias": self._alias},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_create_and_delete_cron_job(self) -> None:
        create_resp = self._api_client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": self._alias,
                "data": {
                    "name": "opsv-test-cron",
                    "cron_expression": "0 0 31 2 *",
                    "task_type": "shell",
                    "command": "echo hello",
                    "status": "disabled",
                    "description": "OpsV-Kits 集成测试 - 不会实际执行",
                },
            },
        )
        assert create_resp.status_code == 200
        job_data = create_resp.json()
        job_id = job_data.get("id", "")
        assert job_id, f"创建 Cron 任务后未返回 id: {job_data}"
        self._created_job_ids.append(job_id)

        delete_resp = self._api_client.delete(
            f"/api/cron-backup/cron-jobs/{job_id}",
            params={"alias": self._alias},
        )
        assert delete_resp.status_code == 200
        self._created_job_ids.remove(job_id)


@pytest.mark.integration
class TestBackupPolicyManagement:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._created_policy_ids: list[str] = []
        yield
        for policy_id in self._created_policy_ids:
            try:
                self._api_client.delete(
                    f"/api/cron-backup/backup-policies/{policy_id}",
                    params={"alias": self._alias},
                )
            except Exception:
                pass

    def test_list_backup_policies(self) -> None:
        resp = self._api_client.get(
            "/api/cron-backup/backup-policies",
            params={"alias": self._alias},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_create_and_delete_backup_policy(self) -> None:
        create_resp = self._api_client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": self._alias,
                "data": {
                    "name": "opsv-test-backup",
                    "backup_type": "custom",
                    "source_path": "/tmp/opsv-test-backup",
                    "storage_type": "local",
                    "storage_config": {"path": "/tmp/opsv-test-backup-dest"},
                    "cron_expression": "0 0 31 2 *",
                    "retention_count": 1,
                    "compression": "tar.gz",
                    "status": "disabled",
                    "description": "OpsV-Kits 集成测试 - 不会实际执行",
                },
            },
        )
        assert create_resp.status_code == 200
        policy_data = create_resp.json()
        policy_id = policy_data.get("id", "")
        assert policy_id, f"创建备份策略后未返回 id: {policy_data}"
        self._created_policy_ids.append(policy_id)

        delete_resp = self._api_client.delete(
            f"/api/cron-backup/backup-policies/{policy_id}",
            params={"alias": self._alias},
        )
        assert delete_resp.status_code == 200
        self._created_policy_ids.remove(policy_id)


@pytest.mark.integration
class TestBackupHistory:
    def test_list_backup_history(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/cron-backup/backup-history",
            params={"alias": alias, "limit": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


@pytest.mark.integration
class TestDiskAlert:
    def test_get_disk_alert(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/cron-backup/disk-alert",
            params={"alias": alias},
        )
        assert resp.status_code == 200
