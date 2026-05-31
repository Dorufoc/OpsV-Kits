from __future__ import annotations

import os
from typing import Any

import pytest

from app.core.ssh_client import SSHClientManager
from app.core.ssh_pool import SSHConnectionPool
from app.models.ssh_account import SSHAccount

skip_if_no_ssh = pytest.mark.skipif(
    not os.environ.get("OPSV_SSH_HOST"),
    reason="集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。请设置 OPSV_SSH_HOST 等环境变量以启用 SSH 集成测试。",
)


@pytest.mark.integration
@skip_if_no_ssh
class TestSSHPasswordConnection:
    def test_password_auth_connect(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        manager = SSHClientManager(account)
        try:
            manager.connect(timeout=10.0)
            assert manager.connected is True
        finally:
            manager.close()

    def test_password_auth_test_connection(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        manager = SSHClientManager(account)
        success, message = manager.test_connection(timeout=10.0)
        assert success is True, f"SSH连接测试失败: {message}"


@pytest.mark.integration
@skip_if_no_ssh
class TestSSHCommandExecution:
    def test_echo_command(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        manager = SSHClientManager(account)
        try:
            manager.connect(timeout=10.0)
            exit_code, stdout, stderr = manager.exec_command("echo hello", timeout=10.0)
            assert exit_code == 0, f"命令执行失败, exit_code={exit_code}, stderr={stderr}"
            assert "hello" in stdout, f"命令输出不包含 'hello': stdout={stdout}"
        finally:
            manager.close()

    def test_hostname_command(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        manager = SSHClientManager(account)
        try:
            manager.connect(timeout=10.0)
            exit_code, stdout, stderr = manager.exec_command("hostname", timeout=10.0)
            assert exit_code == 0, f"hostname 命令执行失败: stderr={stderr}"
            assert len(stdout.strip()) > 0, "hostname 输出为空"
        finally:
            manager.close()


@pytest.mark.integration
@skip_if_no_ssh
class TestSSHConnectionPoolReuse:
    def test_pool_reuse_connection(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        pool = SSHConnectionPool(max_connections=5, idle_timeout=60)
        try:
            conn1 = pool.get_connection(account, timeout=10.0)
            try:
                assert conn1.manager.connected is True
                exit_code, stdout, _ = conn1.manager.exec_command("echo first", timeout=10.0)
                assert exit_code == 0
                assert "first" in stdout
            finally:
                pool.release_connection(conn1)

            conn2 = pool.get_connection(account, timeout=10.0)
            try:
                assert conn2.manager.connected is True
                exit_code, stdout, _ = conn2.manager.exec_command("echo second", timeout=10.0)
                assert exit_code == 0
                assert "second" in stdout
            finally:
                pool.release_connection(conn2)
        finally:
            pool.close_all()

    def test_pool_status(self, ssh_config: dict[str, Any]) -> None:
        account = SSHAccount(
            alias=ssh_config["alias"],
            host=ssh_config["host"],
            port=ssh_config["port"],
            username=ssh_config["username"],
            auth_type="password",
            password=ssh_config["password"],
        )
        pool = SSHConnectionPool(max_connections=5, idle_timeout=60)
        try:
            conn = pool.get_connection(account, timeout=10.0)
            try:
                assert pool.get_active_count() == 1
            finally:
                pool.release_connection(conn)

            assert pool.get_idle_count() >= 1
        finally:
            pool.close_all()
