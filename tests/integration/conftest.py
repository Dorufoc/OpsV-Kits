from __future__ import annotations

import os
from typing import Any, Generator, Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.ssh_account import SSHAccount, SSHAccountCreate
from app.services.ssh_account_service import SSHAccountService


def _get_ssh_config() -> dict[str, Any]:
    host = os.environ.get("OPSV_SSH_HOST", "")
    return {
        "host": host,
        "port": int(os.environ.get("OPSV_SSH_PORT", "22")),
        "username": os.environ.get("OPSV_SSH_USERNAME", "root"),
        "password": os.environ.get("OPSV_SSH_PASSWORD", ""),
        "key_file": os.environ.get("OPSV_SSH_KEY_FILE", ""),
        "alias": os.environ.get("OPSV_SSH_ALIAS", "test-server"),
    }


def _is_ssh_configured() -> bool:
    return bool(os.environ.get("OPSV_SSH_HOST"))


skip_if_no_ssh = pytest.mark.skipif(
    not _is_ssh_configured(),
    reason="集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。请设置 OPSV_SSH_HOST 等环境变量以启用 SSH 集成测试。",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: Integration tests that may require external dependencies",
    )
    config.addinivalue_line(
        "markers",
        "docker: Docker integration tests requiring Docker on remote server",
    )
    config.addinivalue_line(
        "markers",
        "ssh: SSH integration tests requiring SSH access to remote server",
    )
    config.addinivalue_line(
        "markers",
        "timeout: Timeout marker for test cases that may take a long time",
    )


@pytest.fixture
def ssh_config() -> dict[str, Any]:
    if not _is_ssh_configured():
        pytest.skip(
            "集成测试跳过：未设置 OPSV_SSH_HOST 环境变量。"
            "请设置 OPSV_SSH_HOST 等环境变量以启用 SSH 集成测试。"
        )
    return _get_ssh_config()


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def ensure_ssh_account(ssh_config: dict[str, Any]) -> Generator[SSHAccount, None, None]:
    service = SSHAccountService()
    alias = ssh_config["alias"]
    auth_type = "password" if ssh_config["password"] else "key"
    create_data = SSHAccountCreate(
        alias=alias,
        host=ssh_config["host"],
        port=ssh_config["port"],
        username=ssh_config["username"],
        auth_type=auth_type,
        password=ssh_config["password"] if auth_type == "password" else None,
        private_key=ssh_config["key_file"] if auth_type == "key" else None,
        is_default=False,
    )
    existing = service.get_account(alias)
    if existing is None:
        account = service.create_account(create_data)
    else:
        account = existing
    try:
        yield account
    finally:
        pass


@pytest.fixture
def cleanup_ssh_account() -> Generator[None, None, None]:
    yield
    service = SSHAccountService()
    alias = os.environ.get("OPSV_SSH_ALIAS", "test-server")
    try:
        service.delete_account(alias)
    except ValueError:
        pass
