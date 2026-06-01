from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.ssh_account import SSHAccount

TEST_BASE_DIR = "/tmp/opsv-real-test"
LARGE_FILE_SIZE = 10 * 1024 * 1024


@pytest.mark.integration
@pytest.mark.ssh
class TestFileOpsReal:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._test_dir = f"{TEST_BASE_DIR}/file_ops"
        yield
        try:
            self._client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_create_dir_upload_chmod_download_delete(self) -> None:
        mkdir_resp = self._client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": self._test_dir},
        )
        assert mkdir_resp.status_code == 200
        assert mkdir_resp.json()["status"] == "created"

        test_content = "OpsV-Kits real integration test content - 你好世界"
        remote_file = f"{self._test_dir}/test_upload.txt"

        save_resp = self._client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": remote_file,
                "content": test_content,
            },
        )
        assert save_resp.status_code == 200
        assert save_resp.json()["status"] == "saved"

        read_resp = self._client.get(
            "/api/files/content",
            params={"alias": self._alias, "path": remote_file},
        )
        assert read_resp.status_code == 200
        assert test_content in read_resp.json()["content"]

        chmod_resp = self._client.post(
            "/api/files/chmod",
            json={
                "alias": self._alias,
                "path": remote_file,
                "mode": "755",
            },
        )
        assert chmod_resp.status_code == 200
        assert chmod_resp.json()["status"] == "changed"

        stat_resp = self._client.get(
            "/api/files/stat",
            params={"alias": self._alias, "path": remote_file},
        )
        assert stat_resp.status_code == 200
        stat_data = stat_resp.json()
        perm_mode = stat_data.get("permission_mode", 0)
        perm_str = stat_data.get("permissions", "")
        assert perm_mode == 0o755 or oct(perm_mode) == "0o755" or "755" in str(perm_str), (
            f"权限不匹配: permission_mode={perm_mode}, permissions={perm_str}"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp_path = tmp.name
        try:
            dl_resp = self._client.get(
                "/api/files/download",
                params={
                    "alias": self._alias,
                    "remote_path": remote_file,
                    "local_path": tmp_path,
                },
            )
            assert dl_resp.status_code == 200
            with open(tmp_path, "r", encoding="utf-8") as f:
                downloaded = f.read()
            assert test_content in downloaded
        finally:
            os.unlink(tmp_path)

        delete_resp = self._client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": remote_file},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "deleted"

        verify_resp = self._client.get(
            "/api/files/stat",
            params={"alias": self._alias, "path": remote_file},
        )
        assert verify_resp.status_code in (404, 500)


@pytest.mark.integration
@pytest.mark.ssh
class TestUnicodeFileName:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._test_dir = f"{TEST_BASE_DIR}/unicode"
        yield
        try:
            self._client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_chinese_filename_create_list_delete(self) -> None:
        self._client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": self._test_dir},
        )

        chinese_name = "测试文件.txt"
        remote_file = f"{self._test_dir}/{chinese_name}"
        content = "这是一个中文文件名测试"

        save_resp = self._client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": remote_file,
                "content": content,
            },
        )
        assert save_resp.status_code == 200

        read_resp = self._client.get(
            "/api/files/content",
            params={"alias": self._alias, "path": remote_file},
        )
        assert read_resp.status_code == 200
        assert content in read_resp.json()["content"]

        list_resp = self._client.get(
            "/api/files/list",
            params={"alias": self._alias, "path": self._test_dir},
        )
        assert list_resp.status_code == 200
        entries = list_resp.json().get("entries", [])
        names = [e["name"] for e in entries]
        assert chinese_name in names, f"中文文件名未在目录列表中找到: {names}"

        delete_resp = self._client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": remote_file},
        )
        assert delete_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.ssh
class TestLargeFileTransfer:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._test_dir = f"{TEST_BASE_DIR}/large_file"
        self._local_large: str | None = None
        yield
        try:
            self._client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass
        if self._local_large and os.path.exists(self._local_large):
            os.unlink(self._local_large)

    @pytest.mark.timeout(120)
    def test_upload_download_10mb_file(self) -> None:
        self._client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": self._test_dir},
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            self._local_large = tmp.name
            chunk = b"\x00\x01\x02\x03" * 4096
            written = 0
            while written < LARGE_FILE_SIZE:
                to_write = min(len(chunk), LARGE_FILE_SIZE - written)
                tmp.write(chunk[:to_write])
                written += to_write

        remote_file = f"{self._test_dir}/large_test_10mb.bin"

        upload_resp = self._client.post(
            "/api/files/upload",
            params={
                "alias": self._alias,
                "remote_path": remote_file,
                "local_path": self._local_large,
            },
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["status"] == "uploaded"

        stat_resp = self._client.get(
            "/api/files/stat",
            params={"alias": self._alias, "path": remote_file},
        )
        assert stat_resp.status_code == 200
        remote_size = stat_resp.json().get("size", 0)
        assert remote_size == LARGE_FILE_SIZE, (
            f"远程文件大小不匹配: 期望 {LARGE_FILE_SIZE}, 实际 {remote_size}"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp_dl:
            dl_path = tmp_dl.name
        try:
            dl_resp = self._client.get(
                "/api/files/download",
                params={
                    "alias": self._alias,
                    "remote_path": remote_file,
                    "local_path": dl_path,
                },
            )
            assert dl_resp.status_code == 200
            dl_size = os.path.getsize(dl_path)
            assert dl_size == LARGE_FILE_SIZE, (
                f"下载文件大小不匹配: 期望 {LARGE_FILE_SIZE}, 实际 {dl_size}"
            )
        finally:
            os.unlink(dl_path)

        delete_resp = self._client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": remote_file},
        )
        assert delete_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.ssh
class TestSymlink:
    @pytest.fixture(autouse=True)
    def _cleanup(self, api_client: TestClient, ensure_ssh_account: SSHAccount) -> Any:
        self._client = api_client
        self._alias = ensure_ssh_account.alias
        self._test_dir = f"{TEST_BASE_DIR}/symlink"
        yield
        try:
            self._client.post(
                "/api/files/delete",
                json={"alias": self._alias, "path": TEST_BASE_DIR},
            )
        except Exception:
            pass

    def test_create_symlink_and_navigate(self) -> None:
        self._client.post(
            "/api/files/mkdir",
            json={"alias": self._alias, "path": self._test_dir},
        )

        target_file = f"{self._test_dir}/target.txt"
        self._client.post(
            "/api/files/content",
            json={
                "alias": self._alias,
                "path": target_file,
                "content": "symlink target",
            },
        )

        link_path = f"{self._test_dir}/link_to_target"
        self._client.post(
            "/api/command/exec",
            json={
                "alias": self._alias,
                "command": f"ln -s {target_file} {link_path}",
                "timeout": 10,
            },
        )

        stat_resp = self._client.get(
            "/api/files/stat",
            params={"alias": self._alias, "path": link_path},
        )
        assert stat_resp.status_code == 200
        stat_data = stat_resp.json()
        assert stat_data.get("is_link") is True, f"符号链接未被识别: {stat_data}"
        assert stat_data.get("link_target") == target_file, (
            f"链接目标不匹配: 期望 {target_file}, 实际 {stat_data.get('link_target')}"
        )

        list_resp = self._client.get(
            "/api/files/list",
            params={"alias": self._alias, "path": self._test_dir},
        )
        assert list_resp.status_code == 200
        entries = list_resp.json().get("entries", [])
        names = [e["name"] for e in entries]
        assert "link_to_target" in names

        read_resp = self._client.get(
            "/api/files/content",
            params={"alias": self._alias, "path": link_path},
        )
        assert read_resp.status_code == 200
        assert "symlink target" in read_resp.json()["content"]

        self._client.post(
            "/api/files/delete",
            json={"alias": self._alias, "path": link_path},
        )
