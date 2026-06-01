from __future__ import annotations

import tempfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_BASE_DIR = "/tmp/opsv-integration-test"


@pytest.mark.integration
class TestDirectoryListing:
    def test_list_root_directory(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/files/list",
            params={"alias": alias, "path": "/"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "path" in data

    def test_list_home_directory(
        self,
        api_client: TestClient,
        ensure_ssh_account: SSHAccount,
    ) -> None:
        alias = ensure_ssh_account.alias
        resp = api_client.get(
            "/api/files/list",
            params={"alias": alias, "path": "~"},
        )
        assert resp.status_code == 200


@pytest.mark.integration
class TestFileUploadDownload:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        self._remote_test_dir = f"{TEST_BASE_DIR}/upload"
        yield
        try:
            self._api_client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_upload_and_download_file(self) -> None:
        self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": self._remote_test_dir},
        )

        content = "Hello OpsV-Kits Integration Test!"
        remote_file = f"{self._remote_test_dir}/test_upload.txt"

        save_resp = self._api_client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": remote_file,
                "content": content,
            },
        )
        assert save_resp.status_code == 200
        assert save_resp.json()["status"] == "saved"

        read_resp = self._api_client.get(
            "/api/files/content",
            params={"alias": self._alias, "path": remote_file},
        )
        assert read_resp.status_code == 200
        read_data = read_resp.json()
        assert "content" in read_data
        assert content in read_data["content"]


@pytest.mark.integration
class TestFileDeleteAndDirectoryCreate:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._api_client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_create_directory_and_delete(self) -> None:
        test_dir = f"{TEST_BASE_DIR}/mkdir_test"
        mkdir_resp = self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": test_dir},
        )
        assert mkdir_resp.status_code == 200
        assert mkdir_resp.json()["status"] == "created"

        list_resp = self._api_client.get(
            "/api/files/list",
            params={"alias": self._alias, "path": TEST_BASE_DIR},
        )
        assert list_resp.status_code == 200
        entries = list_resp.json().get("entries", [])
        dir_names = [e["name"] for e in entries]
        assert "mkdir_test" in dir_names

        delete_resp = self._api_client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": test_dir},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "deleted"

    def test_create_file_and_delete(self) -> None:
        test_file = f"{TEST_BASE_DIR}/test_file.txt"
        self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": TEST_BASE_DIR},
        )

        save_resp = self._api_client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": test_file,
                "content": "test content",
            },
        )
        assert save_resp.status_code == 200

        delete_resp = self._api_client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": test_file},
        )
        assert delete_resp.status_code == 200


@pytest.mark.integration
class TestPermissionsAndEncoding:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._api_client = api_client
        self._alias = ensure_ssh_account.alias
        yield
        try:
            self._api_client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_check_permission(self) -> None:
        self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": TEST_BASE_DIR},
        )

        perm_resp = self._api_client.get(
            "/api/permission/check",
            params={"alias": self._alias, "path": TEST_BASE_DIR},
        )
        assert perm_resp.status_code == 200
        data = perm_resp.json()
        assert "exists" in data
        assert "readable" in data
        assert "writable" in data

    def test_chmod_file(self) -> None:
        self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": TEST_BASE_DIR},
        )

        test_file = f"{TEST_BASE_DIR}/chmod_test.txt"
        self._api_client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": test_file,
                "content": "chmod test",
            },
        )

        chmod_resp = self._api_client.post(
            "/api/files/chmod",
            json={
                "alias": self._alias,
                "path": test_file,
                "mode": "644",
            },
        )
        assert chmod_resp.status_code == 200
        assert chmod_resp.json()["status"] == "changed"

    def test_unicode_content(self) -> None:
        self._api_client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": TEST_BASE_DIR},
        )

        unicode_content = "你好世界 🌍 Hello Мир"
        test_file = f"{TEST_BASE_DIR}/unicode_test.txt"

        save_resp = self._api_client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": test_file,
                "content": unicode_content,
            },
        )
        assert save_resp.status_code == 200

        read_resp = self._api_client.get(
            "/api/files/content",
            params={"alias": self._alias, "path": test_file},
        )
        assert read_resp.status_code == 200
        read_data = read_resp.json()
        assert "content" in read_data
