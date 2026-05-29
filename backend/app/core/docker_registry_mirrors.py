from __future__ import annotations

import json
from typing import Any, Optional

from app.services.docker_service import DockerCommandError
from app.services.ssh_account_service import ssh_account_service


_DAEMON_JSON_PATH = "/etc/docker/daemon.json"

_PRESET_MIRRORS: dict[str, str] = {
    "阿里云": "https://mirror.aliyuncs.com",
    "网易云": "https://hub-mirror.c.163.com",
    "腾讯云": "https://mirror.ccs.tencentyun.com",
    "DaoCloud": "https://docker.m.daocloud.io",
}


class DockerRegistryMirrors:
    def _get_connection(self, account_alias: str):
        account = ssh_account_service.get_account(account_alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{account_alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec_remote(
        self,
        account_alias: str,
        command: str,
        timeout: float = 60.0,
    ) -> tuple[int, str, str]:
        conn = self._get_connection(account_alias)
        try:
            mgr = conn.manager
            exit_code, stdout, stderr = mgr.exec_command(command, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return exit_code, stdout, stderr
        finally:
            ssh_account_service.pool.release_connection(conn)

    def _exec_remote_simple(
        self,
        account_alias: str,
        command: str,
        timeout: float = 60.0,
    ) -> tuple[str, str]:
        exit_code, stdout, stderr = self._exec_remote(
            account_alias, command, timeout
        )
        if exit_code != 0:
            raise DockerCommandError(stderr.strip(), exit_code)
        return stdout.strip(), stderr.strip()

    # ── 预置镜像源 ────────────────────────────────────────────────

    @staticmethod
    def list_preset_mirrors() -> dict[str, str]:
        return dict(_PRESET_MIRRORS)

    # ── 读取当前配置 ──────────────────────────────────────────────

    def check_registry_mirrors(
        self, account_alias: str
    ) -> dict[str, Any]:
        exit_code, stdout, stderr = self._exec_remote(
            account_alias,
            f"cat {_DAEMON_JSON_PATH} 2>/dev/null || echo '{{}}'",
            timeout=10.0,
        )

        raw = stdout.strip()
        if not raw or raw == "{}":
            return {
                "path": _DAEMON_JSON_PATH,
                "exists": False,
                "mirrors": [],
                "raw": "",
            }

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "path": _DAEMON_JSON_PATH,
                "exists": True,
                "mirrors": [],
                "raw": raw,
                "error": "daemon.json 解析失败",
            }

        mirrors = data.get("registry-mirrors", [])
        if isinstance(mirrors, str):
            mirrors = [mirrors]
        elif not isinstance(mirrors, list):
            mirrors = []

        return {
            "path": _DAEMON_JSON_PATH,
            "exists": True,
            "mirrors": mirrors,
            "raw": raw,
        }

    # ── 配置镜像源 ────────────────────────────────────────────────

    def configure_registry_mirror(
        self,
        account_alias: str,
        mirror_url: str,
    ) -> dict[str, Any]:
        if not mirror_url or not isinstance(mirror_url, str):
            raise ValueError("镜像源地址不能为空")

        if not mirror_url.startswith(("http://", "https://")):
            raise ValueError("镜像源地址必须以 http:// 或 https:// 开头")

        current = self.check_registry_mirrors(account_alias)
        existing_mirrors = list(current.get("mirrors", []))

        if mirror_url in existing_mirrors:
            return {
                "mirror_url": mirror_url,
                "message": "该镜像源已配置",
                "mirrors": existing_mirrors,
                "restarted": False,
            }

        existing_mirrors.append(mirror_url)

        new_config = {"registry-mirrors": existing_mirrors}
        config_json = json.dumps(new_config, indent=2, ensure_ascii=False)

        escaped_config = config_json.replace("'", "'\"'\"'")
        write_cmd = (
            f"echo '{escaped_config}' | sudo tee {_DAEMON_JSON_PATH} > /dev/null"
        )

        self._exec_remote_simple(account_alias, write_cmd, timeout=10.0)

        restarted = False
        restart_msg = ""
        try:
            _, _ = self._exec_remote_simple(
                account_alias,
                "sudo systemctl restart docker",
                timeout=60.0,
            )
            restarted = True
            restart_msg = "Docker 服务已重启"
        except DockerCommandError as e:
            restart_msg = f"Docker 服务重启失败: {e}"

        return {
            "mirror_url": mirror_url,
            "message": f"镜像源 {mirror_url} 已配置" + (
                f"，{restart_msg}" if restart_msg else ""
            ),
            "mirrors": existing_mirrors,
            "restarted": restarted,
        }

    def remove_registry_mirror(
        self,
        account_alias: str,
        mirror_url: str,
    ) -> dict[str, Any]:
        current = self.check_registry_mirrors(account_alias)
        existing_mirrors = list(current.get("mirrors", []))

        if mirror_url not in existing_mirrors:
            return {
                "mirror_url": mirror_url,
                "message": "该镜像源未配置",
                "mirrors": existing_mirrors,
                "restarted": False,
            }

        existing_mirrors.remove(mirror_url)

        if existing_mirrors:
            new_config = {"registry-mirrors": existing_mirrors}
            config_json = json.dumps(new_config, indent=2, ensure_ascii=False)
        else:
            config_json = "{}"

        escaped_config = config_json.replace("'", "'\"'\"'")
        write_cmd = (
            f"echo '{escaped_config}' | sudo tee {_DAEMON_JSON_PATH} > /dev/null"
        )

        self._exec_remote_simple(account_alias, write_cmd, timeout=10.0)

        restarted = False
        restart_msg = ""
        try:
            _, _ = self._exec_remote_simple(
                account_alias,
                "sudo systemctl restart docker",
                timeout=60.0,
            )
            restarted = True
            restart_msg = "Docker 服务已重启"
        except DockerCommandError as e:
            restart_msg = f"Docker 服务重启失败: {e}"

        return {
            "mirror_url": mirror_url,
            "message": f"镜像源 {mirror_url} 已移除" + (
                f"，{restart_msg}" if restart_msg else ""
            ),
            "mirrors": existing_mirrors,
            "restarted": restarted,
        }


docker_registry_mirrors = DockerRegistryMirrors()
