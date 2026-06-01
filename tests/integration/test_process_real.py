from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount


@pytest.mark.integration
@pytest.mark.ssh
class TestProcessRealOps:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._started_pids: list[int] = []
        yield
        for pid in self._started_pids:
            try:
                self._client.post(
                    "/api/process/kill",
                    json={
                        "alias": self._alias,
                        "pid": pid,
                        "signal": "SIGKILL",
                    },
                )
            except Exception:
                pass

    def _find_process_by_name(self, name: str) -> dict | None:
        resp = self._client.get(
            "/api/process/list",
            params={"alias": self._alias},
        )
        if resp.status_code != 200:
            return None
        processes = resp.json().get("processes", [])
        for proc in processes:
            cmd = proc.get("command", proc.get("CMD", proc.get("name", "")))
            if name in str(cmd):
                return proc
        return None

    @pytest.mark.timeout(60)
    def test_start_find_nice_terminate_process(self) -> None:
        start_resp = self._client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": "nohup sleep 300 > /dev/null 2>&1 & echo $!",
                "timeout": 10,
            },
        )
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        stdout = start_data.get("stdout", "").strip()
        pid_str = stdout.split("\n")[-1].strip()
        assert pid_str.isdigit(), f"无法从输出中解析 PID: {stdout}"
        pid = int(pid_str)
        self._started_pids.append(pid)

        time.sleep(2)

        proc = self._find_process_by_name("sleep 300")
        assert proc is not None, "在进程列表中未找到 sleep 300 进程"

        found_pid = proc.get("pid", proc.get("PID", 0))
        if isinstance(found_pid, str):
            found_pid = int(found_pid)

        nice_resp = self._client.post(
            "/api/process/nice",
            json={
                "alias": self._alias,
                "pid": found_pid if found_pid else pid,
                "nice_value": 10,
            },
        )
        assert nice_resp.status_code == 200
        nice_data = nice_resp.json()
        assert nice_data.get("success") is True, f"修改 nice 值失败: {nice_data}"

        kill_resp = self._client.post(
            "/api/process/kill",
            json={
                "alias": self._alias,
                "pid": found_pid if found_pid else pid,
                "signal": "SIGTERM",
            },
        )
        assert kill_resp.status_code == 200
        kill_data = kill_resp.json()
        assert kill_data.get("success") is True, f"终止进程失败: {kill_data}"

        time.sleep(2)

        terminated_proc = self._find_process_by_name("sleep 300")
        assert terminated_proc is None, "进程终止后仍在进程列表中找到"
        if pid in self._started_pids:
            self._started_pids.remove(pid)


@pytest.mark.integration
@pytest.mark.ssh
class TestProcessListReal:
    def test_list_processes_contains_common_daemons(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get("/api/process/list", params={"alias": alias})
        assert resp.status_code == 200
        data = resp.json()
        processes = data.get("processes", [])
        assert len(processes) > 0, "进程列表为空"

        all_commands = " ".join(
            str(p.get("command", p.get("CMD", p.get("name", ""))))
            for p in processes
        )
        has_daemon = "sshd" in all_commands or "systemd" in all_commands
        assert has_daemon, f"进程列表中未找到 sshd 或 systemd: 前5个进程={processes[:5]}"


@pytest.mark.integration
@pytest.mark.ssh
class TestServiceRealOps:
    def test_docker_service_status(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.post(
            "/api/process/service/control",
            json={
                "alias": alias,
                "service_name": "docker",
                "action": "status",
            },
        )
        if resp.status_code == 500:
            pytest.skip("远程服务器上未安装 docker 服务，跳过此测试")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True, f"获取 docker 服务状态失败: {data}"
        output = data.get("message", data.get("output", ""))
        assert isinstance(output, str)
        assert len(output) > 0, "docker 服务状态输出为空"
