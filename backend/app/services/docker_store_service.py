from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from string import Template
from typing import Any, Optional

from app.services.docker_service import DockerCommandError, docker_service
from app.services.ssh_account_service import ssh_account_service


STORE_TEMPLATE_DIR = "/www/server/panel/store/apps"
RUNTIME_APP_DIR = "/www/server/apps"
MANAGED_BY_LABEL = "managed-by=opsv-kits-store"


class DockerStoreService:
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

    # ── 校验辅助 ──────────────────────────────────────────────────

    @staticmethod
    def _validate_app_id(app_id: str) -> None:
        if not app_id or not isinstance(app_id, str):
            raise ValueError("应用 ID 不能为空")
        if ".." in app_id:
            raise ValueError("非法的应用 ID: 包含路径穿越字符 '..'")
        if app_id.startswith("/"):
            raise ValueError("非法的应用 ID: 不能以 '/' 开头")
        if re.search(r"[\\<>:\"|?*\x00-\x1f]", app_id):
            raise ValueError("非法的应用 ID: 包含非法字符")

    @staticmethod
    def _validate_path(path: str) -> None:
        if not path or not isinstance(path, str):
            raise ValueError("路径不能为空")
        normalized = Path(path).resolve().as_posix()
        allowed_prefix = Path(RUNTIME_APP_DIR).resolve().as_posix()
        if not normalized.startswith(allowed_prefix):
            raise ValueError(f"非法路径: 必须在 '{RUNTIME_APP_DIR}' 下")

    # ── 模板渲染 ──────────────────────────────────────────────────

    @staticmethod
    def _render_compose_template(
        template_path: str,
        user_config: dict[str, Any],
    ) -> str:
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise ValueError(f"模板文件不存在: {template_path}")
        except OSError as e:
            raise ValueError(f"读取模板失败: {e}")

        safe_config = {}
        for k, v in user_config.items():
            if isinstance(v, (str, int, float, bool)):
                safe_config[k] = str(v)
            else:
                safe_config[k] = json.dumps(v, ensure_ascii=False)

        try:
            rendered = Template(content).safe_substitute(safe_config)
        except Exception as e:
            raise ValueError(f"模板渲染失败: {e}")
        return rendered

    # ── 目录创建 ──────────────────────────────────────────────────

    def _ensure_runtime_dirs(
        self,
        account_alias: str,
        app_id: str,
        volumes: Optional[list[str]] = None,
    ) -> None:
        app_path = f"{RUNTIME_APP_DIR}/{app_id}"
        dirs = [app_path, f"{app_path}/data"]
        if volumes:
            for vol in volumes:
                vol = vol.strip()
                if not vol:
                    continue
                if vol.startswith("/"):
                    dirs.append(vol)
                else:
                    dirs.append(f"{app_path}/{vol}")

        for d in dirs:
            self._validate_path(d)

        cmd_parts = []
        for d in dirs:
            escaped = shlex.quote(d)
            cmd_parts.append(f"mkdir -p {escaped} && chmod 755 {escaped}")
        cmd = " && ".join(cmd_parts)
        self._exec_remote_simple(account_alias, cmd, timeout=30.0)

    # ── 商店应用列表 ──────────────────────────────────────────────

    def list_apps(
        self, account_alias: Optional[str] = None, category: Optional[str] = None
    ) -> list[dict[str, Any]]:
        apps_json_path = Path(STORE_TEMPLATE_DIR) / "apps.json"
        fallback_path = Path(__file__).resolve().parents[2] / "store" / "apps" / "apps.json"

        target_path = None
        if apps_json_path.is_file():
            target_path = apps_json_path
        elif fallback_path.is_file():
            target_path = fallback_path

        if target_path is None:
            return []

        try:
            raw = target_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            return []

        if isinstance(data, dict):
            apps = data.get("apps", [])
        elif isinstance(data, list):
            apps = data
        else:
            return []
        if not isinstance(apps, list):
            return []

        if category:
            apps = [app for app in apps if app.get("category") == category]

        return apps

    def get_app(self, app_id: str) -> dict[str, Any]:
        self._validate_app_id(app_id)
        apps = self.list_apps()
        for app in apps:
            if app.get("id") == app_id:
                return app
        raise ValueError(f"应用 '{app_id}' 未找到")

    def get_app_detail(self, account_alias: str, app_id: str) -> dict[str, Any]:
        self._validate_app_id(app_id)
        app = self.get_app(app_id)

        result = dict(app)
        result["account_alias"] = account_alias

        try:
            status = self.get_app_status(account_alias, app_id)
            result["status"] = status
        except Exception:
            result["status"] = {
                "app_id": app_id,
                "running": False,
                "containers": [],
                "message": "应用未运行或不存在",
            }

        return result

    # ── 安装 ──────────────────────────────────────────────────────

    def install_app(
        self,
        account_alias: str,
        app_id: str,
        user_config: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_app_id(app_id)

        app_meta = self.get_app(app_id)
        template_file = app_meta.get("template", "docker-compose.yml")
        volumes = app_meta.get("volumes", [])

        template_path_local = Path(STORE_TEMPLATE_DIR) / app_id / template_file
        fallback_template_path = (
            Path(__file__).resolve().parents[3] / "store" / "apps" / app_id / template_file
        )

        if template_path_local.is_file():
            template_path = str(template_path_local)
        elif fallback_template_path.is_file():
            template_path = str(fallback_template_path)
        else:
            raise ValueError(f"应用模板不存在: {app_id}/{template_file}")

        rendered = self._render_compose_template(template_path, user_config)

        app_runtime_path = f"{RUNTIME_APP_DIR}/{app_id}"
        compose_path = f"{app_runtime_path}/docker-compose.yml"

        self._validate_path(app_runtime_path)
        self._validate_path(compose_path)
        self._ensure_runtime_dirs(account_alias, app_id, volumes)

        conn = self._get_connection(account_alias)
        try:
            mgr = conn.manager
            escaped_path = shlex.quote(app_runtime_path)
            exit_code, _, stderr = mgr.exec_command(
                f"mkdir -p {escaped_path}", timeout=10.0
            )
            if exit_code != 0:
                raise DockerCommandError(
                    f"创建应用目录失败: {stderr}", exit_code
                )

            sftp = mgr.open_sftp()
            try:
                with sftp.file(compose_path, "w") as f:
                    f.write(rendered.encode("utf-8"))
            finally:
                mgr.close_sftp()
        finally:
            ssh_account_service.pool.release_connection(conn)

        stdout = docker_service.compose_up(
            account_alias, compose_path, detach=True
        )

        return {
            "app_id": app_id,
            "path": app_runtime_path,
            "message": f"应用 {app_id} 已安装并启动",
            "stdout": stdout,
            "stderr": "",
        }

    # ── 卸载 ──────────────────────────────────────────────────────

    def uninstall_app(
        self,
        account_alias: str,
        app_id: str,
        purge_data: bool = False,
    ) -> dict[str, Any]:
        self._validate_app_id(app_id)

        app_runtime_path = f"{RUNTIME_APP_DIR}/{app_id}"
        compose_path = f"{app_runtime_path}/docker-compose.yml"

        self._validate_path(app_runtime_path)
        self._validate_path(compose_path)

        stdout = docker_service.compose_down(account_alias, compose_path)

        if purge_data:
            self._validate_path(app_runtime_path)
            self._exec_remote_simple(
                account_alias,
                f"rm -rf {shlex.quote(app_runtime_path)}",
                timeout=60.0,
            )
            message = f"应用 {app_id} 已卸载并清理数据"
        else:
            message = f"应用 {app_id} 已卸载，数据保留"

        return {
            "app_id": app_id,
            "message": message,
            "stdout": stdout,
            "stderr": "",
        }

    # ── 状态查询 ──────────────────────────────────────────────────

    def get_all_app_statuses(
        self,
        account_alias: str,
    ) -> list[dict[str, Any]]:
        apps = self.list_apps()
        if not apps:
            return []

        raw = docker_service._exec_docker_json(
            account_alias,
            ["container", "ls", "-a", "--no-trunc", "--format", "'{{json .}}'", "--filter", f"label={MANAGED_BY_LABEL}"],
            timeout=30.0,
        )
        containers = [docker_service._map_container(item) for item in raw]

        result = []
        for app in apps:
            app_id = app.get("id")
            if not app_id:
                continue
            app_containers = [
                c for c in containers
                if c.get("name", "").startswith(f"panel-{app_id}") or c.get("name", "").startswith(f"{app_id}-")
            ]
            running_count = sum(1 for c in app_containers if c.get("state") == "running")
            total_count = len(app_containers)

            if total_count == 0:
                state = "not_installed"
            elif running_count == total_count:
                state = "running"
            elif running_count > 0:
                state = "running"
            else:
                state = "stopped"

            result.append({
                "app_id": app_id,
                "state": state,
                "running_count": running_count,
                "total_count": total_count,
                "containers": [c.get("id", "") for c in app_containers],
            })

        return result

    def get_app_status(
        self,
        account_alias: str,
        app_id: str,
    ) -> dict[str, Any]:
        self._validate_app_id(app_id)

        project_name = f"panel-{app_id}"
        filters = [
            "--filter",
            f"label={MANAGED_BY_LABEL}",
            "--filter",
            f"name={project_name}",
        ]

        raw = docker_service._exec_docker_json(
            account_alias,
            ["container", "ls", "-a", "--no-trunc", "--format", "'{{json .}}'"]
            + filters,
            timeout=30.0,
        )

        containers = [docker_service._map_container(item) for item in raw]

        if not containers:
            return {
                "app_id": app_id,
                "running": False,
                "containers": [],
                "message": "应用未运行或不存在",
            }

        running_count = sum(
            1 for c in containers if c.get("state") == "running"
        )
        total_count = len(containers)

        return {
            "app_id": app_id,
            "running": running_count > 0,
            "running_count": running_count,
            "total_count": total_count,
            "containers": containers,
            "message": f"运行中 {running_count}/{total_count}",
        }


docker_store_service = DockerStoreService()
