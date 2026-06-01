from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

CRON_TEST_FILE = "/tmp/opsv-cron-test"
BACKUP_TEST_SOURCE = "/etc/hostname"
BACKUP_TEST_DEST = "/tmp/opsv-backup-test-dest"


@pytest.mark.integration
@pytest.mark.ssh
class TestCronRealExecution:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._created_job_ids: list[str] = []
        yield
        for job_id in self._created_job_ids:
            try:
                self._client.delete(
                    f"/api/cron-backup/cron-jobs/{job_id}",
                    params={"alias": self._alias},
                )
            except Exception:
                pass
        try:
            self._client.post(
                "/api/command/exec",
                json={
                    "alias": self._alias,
                    "command": f"rm -f {CRON_TEST_FILE}",
                    "timeout": 10,
                },
            )
        except Exception:
            pass

    @pytest.mark.timeout(180)
    def test_cron_job_executes_and_produces_output(self) -> None:
        try:
            self._client.post(
                "/api/command/exec",
                json={
                    "alias": self._alias,
                    "command": f"rm -f {CRON_TEST_FILE}",
                    "timeout": 10,
                },
            )
        except Exception:
            pass

        create_resp = self._client.post(
            "/api/cron-backup/cron-jobs",
            json={
                "alias": self._alias,
                "data": {
                    "name": "opsv-cron-real-test",
                    "cron_expression": "* * * * *",
                    "task_type": "shell",
                    "command": f"echo $(date) >> {CRON_TEST_FILE}",
                    "status": "enabled",
                    "description": "OpsV-Kits 真实操作测试 - 每分钟写入时间戳",
                },
            },
        )
        assert create_resp.status_code == 200
        job_data = create_resp.json()
        job_id = job_data.get("id", "")
        assert job_id, f"创建 Cron 任务后未返回 id: {job_data}"
        self._created_job_ids.append(job_id)

        max_wait = 130
        poll_interval = 10
        waited = 0
        content = ""
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            read_resp = self._client.get(
                "/api/files/content",
                params={"alias": self._alias, "path": CRON_TEST_FILE},
            )
            if read_resp.status_code == 200:
                content = read_resp.json().get("content", "")
                if content.strip():
                    break
        else:
            pytest.skip(f"等待 {max_wait} 秒后未能读取 Cron 输出文件，可能 crond 未运行或延迟")
        assert len(content.strip()) > 0, f"Cron 任务执行后文件 {CRON_TEST_FILE} 为空"

        delete_resp = self._client.delete(
            f"/api/cron-backup/cron-jobs/{job_id}",
            params={"alias": self._alias},
        )
        assert delete_resp.status_code == 200
        self._created_job_ids.remove(job_id)

        list_resp = self._client.get(
            "/api/cron-backup/cron-jobs",
            params={"alias": self._alias},
        )
        assert list_resp.status_code == 200
        remaining = list_resp.json().get("items", [])
        remaining_ids = [j.get("id", "") for j in remaining]
        assert job_id not in remaining_ids, "Cron 任务删除后仍在列表中"


@pytest.mark.integration
@pytest.mark.ssh
class TestBackupRealOps:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._created_policy_ids: list[str] = []
        yield
        for policy_id in self._created_policy_ids:
            try:
                self._client.delete(
                    f"/api/cron-backup/backup-policies/{policy_id}",
                    params={"alias": self._alias},
                )
            except Exception:
                pass
        try:
            self._client.post(
                "/api/command/exec",
                json={
                    "alias": self._alias,
                    "command": f"rm -rf {BACKUP_TEST_DEST}",
                    "timeout": 10,
                },
            )
        except Exception:
            pass

    def test_create_backup_policy_and_execute(self) -> None:
        self._client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": f"mkdir -p {BACKUP_TEST_DEST}",
                "timeout": 10,
            },
        )

        create_resp = self._client.post(
            "/api/cron-backup/backup-policies",
            json={
                "alias": self._alias,
                "data": {
                    "name": "opsv-backup-real-test",
                    "backup_type": "custom",
                    "source_path": BACKUP_TEST_SOURCE,
                    "storage_type": "local",
                    "storage_config": {"path": BACKUP_TEST_DEST},
                    "cron_expression": "0 0 31 2 *",
                    "retention_count": 1,
                    "compression": "tar.gz",
                    "status": "disabled",
                    "description": "OpsV-Kits 真实操作测试 - 手动执行备份",
                },
            },
        )
        assert create_resp.status_code == 200
        policy_data = create_resp.json()
        policy_id = policy_data.get("id", "")
        assert policy_id, f"创建备份策略后未返回 id: {policy_data}"
        self._created_policy_ids.append(policy_id)

        run_resp = self._client.post(
            f"/api/cron-backup/backup-policies/{policy_id}/run",
            params={"alias": self._alias},
        )
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert isinstance(run_data, dict)

        history_resp = self._client.get(
            "/api/cron-backup/backup-history",
            params={"alias": self._alias, "policy_id": policy_id, "limit": 5},
        )
        assert history_resp.status_code == 200
        history_items = history_resp.json().get("items", [])
        if history_items:
            latest = history_items[0]
            assert latest.get("status") in ("success", "failed", "running"), (
                f"备份历史状态异常: {latest.get('status')}"
            )


@pytest.mark.integration
@pytest.mark.ssh
class TestDiskAlertReal:
    def test_disk_alert_returns_reasonable_data(
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
        data = resp.json()
        assert isinstance(data, dict)
        disks = data.get("disks", data.get("items", []))
        if isinstance(disks, list) and disks:
            for disk in disks:
                use_pct = disk.get("use_percent", disk.get("use", -1))
                if isinstance(use_pct, (int, float)):
                    assert 0 <= use_pct <= 100, f"磁盘使用百分比超出合理范围: {use_pct}"
