from __future__ import annotations

import json
import os
import re
import shlex
import urllib.request
from pathlib import Path
from string import Template
from typing import Any, Callable, Optional

from app.services.docker_service import DockerCommandError, docker_service
from app.services.ssh_account_service import ssh_account_service


# 动态计算模板目录路径（兼容 Windows 和 Linux）
def _get_store_template_dir() -> Path:
    """获取商店模板目录路径."""
    # 优先使用环境变量
    env_dir = os.environ.get("OPSV_STORE_DIR")
    if env_dir:
        return Path(env_dir)
    # 基于当前文件位置计算（backend/app/services/docker_store_service.py）
    # 向上回溯到 backend 目录，然后找到 store/apps
    current_file = Path(__file__).resolve()
    # backend/app/services/ -> backend/ -> 项目根目录
    project_root = current_file.parents[2]  # backend/
    store_dir = project_root / "store" / "apps"
    if store_dir.is_dir():
        return store_dir
    # 再尝试向上回溯一级（项目根目录）
    project_root = current_file.parents[3]
    store_dir = project_root / "store" / "apps"
    if store_dir.is_dir():
        return store_dir
    # 最后 fallback 到 Linux 默认路径
    return Path("/www/server/panel/store/apps")


STORE_TEMPLATE_DIR = str(_get_store_template_dir())
RUNTIME_APP_DIR = "/www/server/apps"
MANAGED_APP_DIR = "/www/server/apps"
MANAGED_BY_LABEL = "managed-by=opsv-kits-store"

# Docker Hub Registry API 基础 URL
DOCKER_HUB_API = "https://hub.docker.com/v2"
REGISTRY_API = "https://registry.hub.docker.com/v2"


def _human_readable_size(size_bytes: int) -> str:
    """将字节大小转换为人类可读格式."""
    if size_bytes < 0:
        return "未知"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _parse_size_to_bytes(size_str: str) -> int:
    """解析 Docker 返回的大小字符串为字节数."""
    if not size_str or size_str == "N/A":
        return -1
    size_str = size_str.strip().upper()
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[: -len(suffix)].strip()) * mult)
            except ValueError:
                return -1
    try:
        return int(float(size_str))
    except ValueError:
        return -1


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

    def _get_apps_json_path(self) -> Optional[Path]:
        """获取 apps.json 文件路径."""
        # 方法1: 使用 STORE_TEMPLATE_DIR（已动态计算）
        path = Path(STORE_TEMPLATE_DIR) / "apps.json"
        if path.is_file():
            return path

        # 方法2: 基于当前文件位置计算
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[2]  # backend/
        path = project_root / "store" / "apps" / "apps.json"
        if path.is_file():
            return path

        # 方法3: 再向上回溯一级
        project_root = current_file.parents[3]
        path = project_root / "store" / "apps" / "apps.json"
        if path.is_file():
            return path

        return None

    def list_apps(
        self, account_alias: Optional[str] = None, category: Optional[str] = None
    ) -> list[dict[str, Any]]:
        target_path = self._get_apps_json_path()

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

    def _get_template_path(self, app_id: str, template_file: str = "docker-compose.yml") -> str:
        """获取应用模板文件的绝对路径."""
        # 方法1: 使用 STORE_TEMPLATE_DIR（已动态计算）
        template_path = Path(STORE_TEMPLATE_DIR) / app_id / template_file
        if template_path.is_file():
            return str(template_path)

        # 方法2: 基于当前文件位置计算
        current_file = Path(__file__).resolve()
        # backend/app/services/ -> backend/
        project_root = current_file.parents[2]
        template_path = project_root / "store" / "apps" / app_id / template_file
        if template_path.is_file():
            return str(template_path)

        # 方法3: 再向上回溯一级
        project_root = current_file.parents[3]
        template_path = project_root / "store" / "apps" / app_id / template_file
        if template_path.is_file():
            return str(template_path)

        raise ValueError(f"应用模板不存在: {app_id}/{template_file} (已查找: {STORE_TEMPLATE_DIR})")

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

        template_path = self._get_template_path(app_id, template_file)

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

    def install_app_streaming(
        self,
        account_alias: str,
        app_id: str,
        user_config: dict[str, Any],
        on_progress: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """流式安装应用，支持实时进度回调。

        进度事件类型:
        - { "type": "stage", "stage": "prepare", "message": "准备安装..." }
        - { "type": "stage", "stage": "download", "message": "正在下载镜像..." }
        - { "type": "pull_progress", "image": "nginx", "layer": "abc123", "current": 1024, "total": 2048, "progress_percent": 50.0 }
        - { "type": "stage", "stage": "create", "message": "正在创建容器..." }
        - { "type": "stage", "stage": "start", "message": "正在启动容器..." }
        - { "type": "complete", "success": true, "message": "安装完成" }
        - { "type": "error", "message": "错误信息" }
        """
        self._validate_app_id(app_id)

        def _emit(progress: dict[str, Any]) -> None:
            if on_progress:
                on_progress(progress)

        try:
            _emit({"type": "stage", "stage": "prepare", "message": "正在准备安装环境..."})

            app_meta = self.get_app(app_id)
            template_file = app_meta.get("template", "docker-compose.yml")
            volumes = app_meta.get("volumes", [])

            template_path = self._get_template_path(app_id, template_file)
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

            _emit({"type": "stage", "stage": "download", "message": "正在下载并拉取镜像，请稍候..."})

            # 解析 docker-compose.yml 中的镜像列表，用于更精确的进度跟踪
            image_names = self._extract_images_from_compose(rendered)
            total_images = len(image_names)

            pull_buffer = ""
            current_image_progress = {}

            def _parse_pull_output(stdout_chunk: str, stderr_chunk: str) -> None:
                nonlocal pull_buffer
                combined = stdout_chunk + stderr_chunk
                pull_buffer += combined

                # 解析 Docker pull 进度输出
                # 典型格式: "abc123: Downloading [=========> ]  5.123MB/10.456MB"
                # 或: "Pulling from library/nginx"
                # 或: "Digest: sha256:..."
                # 或: "Status: Downloaded newer image for nginx:latest"

                lines = pull_buffer.split("\n")
                # 保留最后一行（可能不完整）
                pull_buffer = lines[-1] if lines else ""

                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue

                    # 检测镜像下载完成
                    if "Status: Downloaded newer image" in line or "Status: Image is up to date" in line:
                        image_match = re.search(r"for\s+(.+)$", line)
                        if image_match:
                            _emit({
                                "type": "pull_complete",
                                "image": image_match.group(1).strip(),
                                "message": f"镜像 {image_match.group(1).strip()} 下载完成",
                            })
                        continue

                    # 检测层下载进度
                    # 格式: "layer_id: Downloading [======> ]  1.23MB/5.67MB"
                    progress_match = re.search(
                        r"([a-f0-9]+):\s+(\w+)\s+.*?([\d.]+\s*[KMGT]?B)\s*/\s*([\d.]+\s*[KMGT]?B)",
                        line,
                        re.IGNORECASE,
                    )
                    if progress_match:
                        layer_id = progress_match.group(1)
                        action = progress_match.group(2).lower()
                        current_str = progress_match.group(3)
                        total_str = progress_match.group(4)
                        current_bytes = self._parse_size_str(current_str)
                        total_bytes = self._parse_size_str(total_str)
                        percent = (current_bytes / total_bytes * 100) if total_bytes > 0 else 0

                        current_image_progress[layer_id] = {
                            "action": action,
                            "current": current_bytes,
                            "total": total_bytes,
                            "percent": round(percent, 1),
                        }

                        # 计算总体进度
                        total_current = sum(v["current"] for v in current_image_progress.values())
                        total_all = sum(v["total"] for v in current_image_progress.values())
                        overall_percent = (total_current / total_all * 100) if total_all > 0 else 0

                        _emit({
                            "type": "pull_progress",
                            "layer": layer_id,
                            "action": action,
                            "current": current_bytes,
                            "total": total_bytes,
                            "progress_percent": round(overall_percent, 1),
                            "message": f"{action}: {current_str}/{total_str}",
                        })
                        continue

                    # 检测提取进度
                    if "Extracting" in line or "extracting" in line:
                        _emit({
                            "type": "pull_progress",
                            "action": "extracting",
                            "message": line,
                            "progress_percent": -1,
                        })
                        continue

                    # 普通日志输出
                    _emit({
                        "type": "log",
                        "message": line,
                    })

            exit_code, stdout, stderr = docker_service.compose_up_streaming(
                account_alias, compose_path, detach=True, on_output=_parse_pull_output
            )

            if exit_code != 0:
                error_msg = stderr.strip() or stdout.strip() or "未知错误"
                _emit({"type": "error", "message": f"安装失败: {error_msg}"})
                raise DockerCommandError(error_msg, exit_code)

            _emit({"type": "stage", "stage": "start", "message": "正在启动容器..."})

            _emit({"type": "complete", "success": True, "message": f"应用 {app_id} 安装并启动成功"})

            return {
                "app_id": app_id,
                "path": app_runtime_path,
                "message": f"应用 {app_id} 已安装并启动",
                "stdout": stdout,
                "stderr": stderr,
            }

        except Exception as e:
            error_msg = str(e)
            _emit({"type": "error", "message": error_msg})
            raise

    @staticmethod
    def _extract_images_from_compose(compose_content: str) -> list[str]:
        """从 docker-compose 内容中提取镜像名称列表。"""
        images = []
        for line in compose_content.split("\n"):
            match = re.search(r"image:\s*['\"]?([^'\"\n]+)['\"]?", line, re.IGNORECASE)
            if match:
                img = match.group(1).strip()
                if img:
                    images.append(img)
        return images

    @staticmethod
    def _parse_size_str(size_str: str) -> int:
        """解析大小字符串为字节数。"""
        size_str = size_str.strip().upper()
        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }
        for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
            if size_str.endswith(suffix):
                try:
                    return int(float(size_str[: -len(suffix)].strip()) * mult)
                except ValueError:
                    return 0
        try:
            return int(float(size_str))
        except ValueError:
            return 0

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

    # ── 大小查询 ──────────────────────────────────────────────────

    def get_app_size_info(
        self,
        account_alias: str,
        app_id: str,
    ) -> dict[str, Any]:
        """获取应用的实际大小信息（镜像、容器、卷、数据目录）.

        返回包含以下字段的字典:
        - image_size: 镜像大小（字节）
        - image_size_human: 镜像大小（人类可读）
        - container_size: 容器层大小（字节）
        - container_size_human: 容器层大小（人类可读）
        - volume_size: 关联卷大小（字节）
        - volume_size_human: 关联卷大小（人类可读）
        - data_dir_size: 数据目录大小（字节）
        - data_dir_size_human: 数据目录大小（人类可读）
        - total_size: 总大小（字节）
        - total_size_human: 总大小（人类可读）
        """
        self._validate_app_id(app_id)

        result = {
            "app_id": app_id,
            "image_size": 0,
            "image_size_human": "0 B",
            "container_size": 0,
            "container_size_human": "0 B",
            "volume_size": 0,
            "volume_size_human": "0 B",
            "data_dir_size": 0,
            "data_dir_size_human": "0 B",
            "total_size": 0,
            "total_size_human": "0 B",
            "components": [],
        }

        project_name = f"panel-{app_id}"
        app_runtime_path = f"{RUNTIME_APP_DIR}/{app_id}"

        # 1. 获取镜像大小
        try:
            image_sizes = self._get_image_sizes(account_alias, app_id)
            result["image_size"] = image_sizes.get("total", 0)
            result["image_size_human"] = _human_readable_size(result["image_size"])
            if image_sizes.get("images"):
                for img in image_sizes["images"]:
                    result["components"].append({
                        "type": "image",
                        "name": img.get("repository", "未知镜像"),
                        "size": img.get("size", 0),
                        "size_human": _human_readable_size(img.get("size", 0)),
                        "id": img.get("id", ""),
                    })
        except Exception:
            pass

        # 2. 获取容器层大小
        try:
            container_sizes = self._get_container_sizes(account_alias, app_id)
            result["container_size"] = container_sizes.get("total", 0)
            result["container_size_human"] = _human_readable_size(result["container_size"])
            if container_sizes.get("containers"):
                for c in container_sizes["containers"]:
                    result["components"].append({
                        "type": "container",
                        "name": c.get("name", "未知容器"),
                        "size": c.get("size", 0),
                        "size_human": _human_readable_size(c.get("size", 0)),
                        "id": c.get("id", ""),
                    })
        except Exception:
            pass

        # 3. 获取卷大小
        try:
            volume_sizes = self._get_volume_sizes(account_alias, app_id)
            result["volume_size"] = volume_sizes.get("total", 0)
            result["volume_size_human"] = _human_readable_size(result["volume_size"])
            if volume_sizes.get("volumes"):
                for vol in volume_sizes["volumes"]:
                    result["components"].append({
                        "type": "volume",
                        "name": vol.get("name", "未知卷"),
                        "size": vol.get("size", 0),
                        "size_human": _human_readable_size(vol.get("size", 0)),
                        "mountpoint": vol.get("mountpoint", ""),
                    })
        except Exception:
            pass

        # 4. 获取数据目录大小
        try:
            data_dir_size = self._get_data_dir_size(account_alias, app_runtime_path)
            result["data_dir_size"] = data_dir_size
            result["data_dir_size_human"] = _human_readable_size(data_dir_size)
            if data_dir_size > 0:
                result["components"].append({
                    "type": "data_dir",
                    "name": f"{app_id}/data",
                    "size": data_dir_size,
                    "size_human": _human_readable_size(data_dir_size),
                    "path": app_runtime_path,
                })
        except Exception:
            pass

        # 计算总大小
        result["total_size"] = (
            result["image_size"]
            + result["container_size"]
            + result["volume_size"]
            + result["data_dir_size"]
        )
        result["total_size_human"] = _human_readable_size(result["total_size"])

        return result

    def _get_image_sizes(
        self, account_alias: str, app_id: str
    ) -> dict[str, Any]:
        """获取与应用关联的镜像大小."""
        # 先获取容器的镜像名称
        stdout, _ = docker_service._exec_docker_simple(
            account_alias,
            [
                "container", "ls", "-a",
                "--filter", f"label={MANAGED_BY_LABEL}",
                "--filter", f"name=panel-{app_id}",
                "--format", "{{.Image}}",
            ],
            timeout=15.0,
        )

        image_names = [line.strip() for line in stdout.split("\n") if line.strip()]
        if not image_names:
            return {"total": 0, "images": []}

        # 获取所有镜像的详细信息
        raw = docker_service._exec_docker_json(
            account_alias,
            ["image", "ls", "--format", "'{{json .}}'"],
            timeout=15.0,
        )

        total_size = 0
        matched_images = []
        for item in raw:
            repo = item.get("Repository", "")
            tag = item.get("Tag", "")
            img_id = item.get("ID", "")
            size_str = item.get("Size", "0B")

            # 匹配镜像名称
            full_name = f"{repo}:{tag}" if tag and tag != "<none>" else repo
            if any(name in full_name or full_name in name for name in image_names):
                size_bytes = _parse_size_to_bytes(size_str)
                if size_bytes > 0:
                    total_size += size_bytes
                    matched_images.append({
                        "repository": repo,
                        "tag": tag,
                        "id": img_id,
                        "size": size_bytes,
                        "size_human": size_str,
                    })

        return {"total": total_size, "images": matched_images}

    def _get_container_sizes(
        self, account_alias: str, app_id: str
    ) -> dict[str, Any]:
        """获取容器层（读写层）大小."""
        raw = docker_service._exec_docker_json(
            account_alias,
            [
                "container", "ls", "-a",
                "--filter", f"label={MANAGED_BY_LABEL}",
                "--filter", f"name=panel-{app_id}",
                "--format", "'{{json .}}'",
            ],
            timeout=15.0,
        )

        containers = [docker_service._map_container(item) for item in raw]
        if not containers:
            return {"total": 0, "containers": []}

        total_size = 0
        container_details = []
        for c in containers:
            cid = c.get("id", "")
            cname = c.get("name", "")
            if not cid:
                continue

            try:
                # 使用 docker inspect 获取容器层大小
                inspect_result = docker_service._exec_docker_json(
                    account_alias,
                    ["container", "inspect", cid],
                    timeout=10.0,
                )
                if inspect_result:
                    graph_driver = inspect_result[0].get("GraphDriver", {})
                    data = graph_driver.get("Data", {})
                    # 获取读写层大小
                    size_rw = inspect_result[0].get("SizeRw", 0) or 0
                    size_root_fs = inspect_result[0].get("SizeRootFs", 0) or 0
                    # 容器层大小 = 总大小 - 镜像大小（这里用 SizeRw 更准确）
                    layer_size = size_rw if size_rw > 0 else 0

                    if layer_size > 0:
                        total_size += layer_size
                        container_details.append({
                            "id": cid,
                            "name": cname,
                            "size": layer_size,
                            "size_human": _human_readable_size(layer_size),
                        })
            except Exception:
                continue

        return {"total": total_size, "containers": container_details}

    def _get_volume_sizes(
        self, account_alias: str, app_id: str
    ) -> dict[str, Any]:
        """获取与应用关联的 Docker 卷大小."""
        # 获取容器使用的卷
        raw = docker_service._exec_docker_json(
            account_alias,
            [
                "container", "ls", "-a",
                "--filter", f"label={MANAGED_BY_LABEL}",
                "--filter", f"name=panel-{app_id}",
                "--format", "'{{json .}}'",
            ],
            timeout=15.0,
        )

        containers = [docker_service._map_container(item) for item in raw]
        if not containers:
            return {"total": 0, "volumes": []}

        # 收集所有卷名
        volume_names = set()
        for c in containers:
            cid = c.get("id", "")
            if not cid:
                continue
            try:
                inspect_result = docker_service._exec_docker_json(
                    account_alias,
                    ["container", "inspect", cid],
                    timeout=10.0,
                )
                if inspect_result:
                    mounts = inspect_result[0].get("Mounts", [])
                    for mount in mounts:
                        if mount.get("Type") == "volume":
                            vol_name = mount.get("Name", "")
                            if vol_name:
                                volume_names.add(vol_name)
            except Exception:
                continue

        if not volume_names:
            return {"total": 0, "volumes": []}

        # 获取卷大小（通过 du 命令）
        total_size = 0
        volume_details = []
        for vol_name in volume_names:
            try:
                # 获取卷挂载点
                vol_info = docker_service._exec_docker_json(
                    account_alias,
                    ["volume", "inspect", vol_name],
                    timeout=10.0,
                )
                if vol_info:
                    mountpoint = vol_info[0].get("Mountpoint", "")
                    if mountpoint:
                        # 使用 du 获取实际大小
                        stdout, _ = docker_service._exec_docker_simple(
                            account_alias,
                            ["run", "--rm", "-v", f"{mountpoint}:/vol", "alpine:latest",
                             "sh", "-c", "du -sb /vol 2>/dev/null || echo 0"],
                            timeout=15.0,
                        )
                        try:
                            vol_size = int(stdout.strip().split()[0])
                        except (ValueError, IndexError):
                            # 备用方案：直接在主机上执行
                            exit_code, stdout2, _ = docker_service._exec_docker(
                                account_alias,
                                ["run", "--rm", "--pid=host", "--privileged", "alpine:latest",
                                 "sh", "-c", f"du -sb '{mountpoint}' 2>/dev/null || echo 0"],
                                timeout=15.0,
                            )
                            if exit_code == 0:
                                try:
                                    vol_size = int(stdout2.strip().split()[0])
                                except (ValueError, IndexError):
                                    vol_size = 0
                            else:
                                vol_size = 0

                        if vol_size > 0:
                            total_size += vol_size
                            volume_details.append({
                                "name": vol_name,
                                "size": vol_size,
                                "size_human": _human_readable_size(vol_size),
                                "mountpoint": mountpoint,
                            })
            except Exception:
                continue

        return {"total": total_size, "volumes": volume_details}

    def _get_data_dir_size(
        self, account_alias: str, app_runtime_path: str
    ) -> int:
        """获取应用数据目录的实际大小."""
        try:
            exit_code, stdout, _ = docker_service._exec_docker(
                account_alias,
                ["run", "--rm", "-v", f"{app_runtime_path}:/app_data", "alpine:latest",
                 "sh", "-c", "du -sb /app_data 2>/dev/null || echo 0"],
                timeout=15.0,
            )
            if exit_code == 0:
                try:
                    return int(stdout.strip().split()[0])
                except (ValueError, IndexError):
                    return 0
        except Exception:
            pass
        return 0


    # ── 镜像版本大小查询 ───────────────────────────────────────────

    def get_image_version_sizes(
        self,
        app_id: str,
    ) -> dict[str, Any]:
        """获取应用镜像各版本的大小信息.

        通过 Docker Hub Registry API 查询镜像标签的压缩大小.
        返回包含各版本大小和总大小的字典.
        """
        self._validate_app_id(app_id)

        # 获取应用元数据
        app = self.get_app(app_id)
        versions = app.get("versions", ["latest"])

        # 从 docker-compose.yml 解析镜像名称
        image_name = self._get_image_name_from_template(app_id)
        if not image_name:
            return {
                "app_id": app_id,
                "image_name": None,
                "versions": [],
                "total_versions": len(versions),
                "message": "无法从模板解析镜像名称",
            }

        # 查询每个版本的大小
        version_sizes = []
        for version in versions:
            size_info = self._query_docker_hub_size(image_name, version)
            version_sizes.append({
                "version": version,
                "size": size_info.get("size", 0),
                "size_human": size_info.get("size_human", "未知"),
                "compressed_size": size_info.get("compressed_size", 0),
                "compressed_size_human": size_info.get("compressed_size_human", "未知"),
                "architecture": size_info.get("architecture", "unknown"),
                "os": size_info.get("os", "unknown"),
                "last_updated": size_info.get("last_updated", ""),
                "status": size_info.get("status", "unknown"),
            })

        return {
            "app_id": app_id,
            "image_name": image_name,
            "versions": version_sizes,
            "total_versions": len(version_sizes),
        }

    def _get_image_name_from_template(self, app_id: str) -> Optional[str]:
        """从 docker-compose.yml 模板中解析镜像名称."""
        try:
            template_path = self._get_template_path(app_id, "docker-compose.yml")
            content = Path(template_path).read_text(encoding="utf-8")
            # 匹配 image: 行
            match = re.search(r'image:\s*["\']?([^"\'\n]+)["\']?', content)
            if match:
                image = match.group(1).strip()
                # 移除变量引用如 ${VERSION}
                image = re.sub(r'\$\{[^}]+\}', 'latest', image)
                # 移除 :latest 或 :版本号，只保留仓库名
                if ':' in image:
                    image = image.rsplit(':', 1)[0]
                return image
        except Exception:
            pass
        return None

    def _query_docker_hub_size(
        self, image_name: str, tag: str
    ) -> dict[str, Any]:
        """查询 Docker Hub 上指定镜像标签的大小信息."""
        result = {
            "size": 0,
            "size_human": "未知",
            "compressed_size": 0,
            "compressed_size_human": "未知",
            "architecture": "unknown",
            "os": "unknown",
            "last_updated": "",
            "status": "unknown",
        }

        # 处理官方镜像（如 nginx, mysql）
        if '/' not in image_name:
            repo_path = f"library/{image_name}"
        else:
            repo_path = image_name

        try:
            # 1. 获取标签的 manifest 信息
            manifest_url = f"{DOCKER_HUB_API}/repositories/{repo_path}/tags/{tag}"
            req = urllib.request.Request(manifest_url)
            req.add_header('Accept', 'application/json')
            req.add_header('User-Agent', 'OpsV-Kits/1.0')

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            # 提取大小信息
            images = data.get("images", [])
            if images:
                # 优先选择 linux/amd64 架构
                target_image = None
                for img in images:
                    if img.get("architecture") == "amd64" and img.get("os") == "linux":
                        target_image = img
                        break
                if not target_image:
                    target_image = images[0]

                size_bytes = target_image.get("size", 0)
                result["size"] = size_bytes
                result["size_human"] = _human_readable_size(size_bytes)
                result["compressed_size"] = size_bytes
                result["compressed_size_human"] = _human_readable_size(size_bytes)
                result["architecture"] = target_image.get("architecture", "unknown")
                result["os"] = target_image.get("os", "unknown")
                result["last_updated"] = data.get("last_updated", "")
                result["status"] = "found"
            else:
                # 尝试从 full_size 获取
                full_size = data.get("full_size", 0)
                if full_size:
                    result["size"] = full_size
                    result["size_human"] = _human_readable_size(full_size)
                    result["compressed_size"] = full_size
                    result["compressed_size_human"] = _human_readable_size(full_size)
                    result["status"] = "found"
                else:
                    result["status"] = "not_found"

        except urllib.error.HTTPError as e:
            if e.code == 404:
                result["status"] = "not_found"
            else:
                result["status"] = f"error_{e.code}"
        except Exception as e:
            result["status"] = f"error: {str(e)[:50]}"

        return result


docker_store_service = DockerStoreService()
