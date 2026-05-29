from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from app.services.ssh_account_service import ssh_account_service


class DockerCommandError(RuntimeError):
    def __init__(self, message: str, exit_code: int):
        self.exit_code = exit_code
        super().__init__(message)


class DockerService:
    def _get_connection(self, account_alias: str):
        account = ssh_account_service.get_account(account_alias)
        if account is None:
            raise ValueError(f"SSH 账户 '{account_alias}' 不存在")
        return ssh_account_service.pool.get_connection(account)

    def _exec_docker(
        self, account_alias: str, docker_args: list[str], timeout: float = 60.0
    ) -> tuple[int, str, str]:
        conn = self._get_connection(account_alias)
        try:
            cmd = "docker " + " ".join(docker_args)
            exit_code, stdout, stderr = conn.manager.exec_command(cmd, timeout=timeout)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return exit_code, stdout, stderr
        finally:
            ssh_account_service.pool.release_connection(conn)

    def _exec_docker_json(
        self, account_alias: str, docker_args: list[str], timeout: float = 60.0
    ) -> list[dict[str, Any]]:
        exit_code, stdout, stderr = self._exec_docker(
            account_alias, docker_args, timeout
        )
        if exit_code != 0:
            raise DockerCommandError(stderr.strip(), exit_code)
        result = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return result

    def _exec_docker_simple(
        self, account_alias: str, docker_args: list[str], timeout: float = 60.0
    ) -> tuple[str, str]:
        exit_code, stdout, stderr = self._exec_docker(
            account_alias, docker_args, timeout
        )
        if exit_code != 0:
            raise DockerCommandError(stderr.strip(), exit_code)
        return stdout.strip(), stderr.strip()

    @staticmethod
    def _pascal_to_camel(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            transformed = {}
            for k, v in item.items():
                if not k:
                    continue
                new_key = k[0].lower() + k[1:]
                transformed[new_key] = v
            result.append(transformed)
        return result

    @staticmethod
    def _map_container(item: dict[str, Any]) -> dict[str, Any]:
        mapped = {}
        for k, v in item.items():
            if k == "ID":
                mapped["id"] = v
            elif k == "Names":
                name = v
                if isinstance(name, str) and name.startswith("/"):
                    name = name[1:]
                mapped["name"] = name
            elif k == "CreatedAt":
                mapped["created"] = v
            elif k == "State":
                mapped["state"] = v.lower() if isinstance(v, str) else v
            else:
                new_key = k[0].lower() + k[1:] if k else k
                mapped[new_key] = v
        return mapped

    @staticmethod
    def _map_image(item: dict[str, Any]) -> dict[str, Any]:
        mapped = {}
        for k, v in item.items():
            if k == "ID":
                mapped["id"] = v
            elif k == "CreatedAt":
                mapped["created"] = v
            elif k == "CreatedSince":
                mapped["created_since"] = v
            else:
                new_key = k[0].lower() + k[1:] if k else k
                mapped[new_key] = v
        return mapped

    # ── 环境检测 ──────────────────────────────────────────────────

    def check_docker_installed(self, account_alias: str) -> bool:
        try:
            exit_code, stdout, stderr = self._exec_docker(
                account_alias, ["--version"], timeout=10.0
            )
            return exit_code == 0
        except Exception:
            return False

    def get_docker_version(self, account_alias: str) -> Optional[str]:
        try:
            _, stdout, _ = self._exec_docker(
                account_alias, ["--version"], timeout=10.0
            )
            return stdout.strip()
        except Exception:
            return None

    def check_docker_running(self, account_alias: str) -> bool:
        try:
            exit_code, _, _ = self._exec_docker(
                account_alias, ["info"], timeout=15.0
            )
            return exit_code == 0
        except Exception:
            return False

    def check_docker_permissions(self, account_alias: str) -> dict[str, Any]:
        result = {
            "in_docker_group": False,
            "has_sudo_access": False,
            "can_run_docker": False,
            "details": "",
        }
        conn = self._get_connection(account_alias)
        try:
            mgr = conn.manager
            exit_code, stdout, stderr = mgr.exec_command(
                "groups", timeout=10.0
            )
            groups = stdout.strip()
            if isinstance(groups, bytes):
                groups = groups.decode("utf-8", errors="replace")
            result["in_docker_group"] = "docker" in groups

            exit_code2, _, _ = mgr.exec_command(
                "sudo -n docker info", timeout=15.0
            )
            result["has_sudo_access"] = exit_code2 == 0

            exit_code3, _, _ = mgr.exec_command(
                "docker info", timeout=15.0
            )
            result["can_run_docker"] = exit_code3 == 0

            if result["can_run_docker"]:
                result["details"] = "当前用户有 Docker 权限"
            elif result["in_docker_group"]:
                result["details"] = "用户已在 docker 组，可能需要重新登录"
            elif result["has_sudo_access"]:
                result["details"] = "可通过 sudo 执行 Docker 命令"
            else:
                result["details"] = "当前用户无 Docker 操作权限"
        finally:
            ssh_account_service.pool.release_connection(conn)
        return result

    def install_docker(self, account_alias: str) -> str:
        conn = self._get_connection(account_alias)
        try:
            mgr = conn.manager
            exit_code, stdout, stderr = mgr.exec_command(
                "cat /etc/os-release", timeout=10.0
            )
            if exit_code != 0:
                raise DockerCommandError("无法检测操作系统类型", exit_code)
            os_release = stdout.strip().lower()
            if isinstance(os_release, bytes):
                os_release = os_release.decode("utf-8", errors="replace")

            if "centos" in os_release or "rhel" in os_release or "red hat" in os_release:
                cmd = (
                    "sudo dnf remove -y docker docker-engine docker.io containerd runc 2>/dev/null; "
                    "sudo dnf install -y dnf-plugins-core; "
                    "sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo; "
                    "sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; "
                    "sudo systemctl enable --now docker; "
                    "echo 'DOCKER_INSTALLED'"
                )
            elif "ubuntu" in os_release or "debian" in os_release:
                cmd = (
                    "sudo apt-get update -qq; "
                    "sudo apt-get install -y -qq ca-certificates curl; "
                    "sudo install -m 0755 -d /etc/apt/keyrings; "
                    "sudo curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo \"$ID\")/gpg -o /etc/apt/keyrings/docker.asc; "
                    "sudo chmod a+r /etc/apt/keyrings/docker.asc; "
                    "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$(. /etc/os-release && echo \"$ID\") $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable\" | "
                    "sudo tee /etc/apt/sources.list.d/docker.list > /dev/null; "
                    "sudo apt-get update -qq; "
                    "sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; "
                    "sudo systemctl enable --now docker; "
                    "echo 'DOCKER_INSTALLED'"
                )
            else:
                raise DockerCommandError(
                    f"不支持的操作系统类型: 仅支持 CentOS/RHEL/Ubuntu/Debian", -1
                )

            exit_code2, stdout2, stderr2 = mgr.exec_command(cmd, timeout=300.0)
            if isinstance(stdout2, bytes):
                stdout2 = stdout2.decode("utf-8", errors="replace")
            if isinstance(stderr2, bytes):
                stderr2 = stderr2.decode("utf-8", errors="replace")
            if "DOCKER_INSTALLED" not in stdout2:
                raise DockerCommandError(
                    f"Docker 安装失败: {stderr2.strip()}", exit_code2
                )
            return "Docker 安装成功"
        finally:
            ssh_account_service.pool.release_connection(conn)

    # ── 容器管理 ──────────────────────────────────────────────────

    def list_containers(
        self, account_alias: str, all: bool = False
    ) -> list[dict[str, Any]]:
        args = ["container", "ls", "--no-trunc", "--format", "'{{json .}}'"]
        if all:
            args.insert(2, "-a")
        raw = self._exec_docker_json(account_alias, args)
        return [self._map_container(item) for item in raw]

    def get_container_info(
        self, account_alias: str, container_id: str
    ) -> dict[str, Any]:
        result = self._exec_docker_json(
            account_alias,
            ["container", "inspect", container_id],
        )
        if not result:
            raise DockerCommandError(f"容器 '{container_id}' 未找到", -1)
        return result[0]

    def start_container(
        self, account_alias: str, container_id: str
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["container", "start", container_id]
        )
        return stdout or f"容器 {container_id} 已启动"

    def stop_container(
        self, account_alias: str, container_id: str, timeout: Optional[int] = None
    ) -> str:
        args = ["container", "stop"]
        if timeout is not None:
            args.extend(["-t", str(timeout)])
        args.append(container_id)
        stdout, _ = self._exec_docker_simple(account_alias, args)
        return stdout or f"容器 {container_id} 已停止"

    def restart_container(
        self, account_alias: str, container_id: str
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["container", "restart", container_id]
        )
        return stdout or f"容器 {container_id} 已重启"

    def kill_container(
        self, account_alias: str, container_id: str
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["container", "kill", container_id]
        )
        return stdout or f"容器 {container_id} 已强制停止"

    def remove_container(
        self, account_alias: str, container_id: str, force: bool = False
    ) -> str:
        args = ["container", "rm"]
        if force:
            args.append("-f")
        args.append(container_id)
        stdout, _ = self._exec_docker_simple(account_alias, args)
        return stdout or f"容器 {container_id} 已删除"

    def pause_container(
        self, account_alias: str, container_id: str
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["container", "pause", container_id]
        )
        return stdout or f"容器 {container_id} 已暂停"

    def unpause_container(
        self, account_alias: str, container_id: str
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["container", "unpause", container_id]
        )
        return stdout or f"容器 {container_id} 已恢复"

    def exec_in_container(
        self, account_alias: str, container_id: str, command: str
    ) -> tuple[int, str, str]:
        conn = self._get_connection(account_alias)
        try:
            cmd = f"docker container exec {container_id} {command}"
            return conn.manager.exec_command(cmd, timeout=60.0)
        finally:
            ssh_account_service.pool.release_connection(conn)

    def get_container_logs(
        self,
        account_alias: str,
        container_id: str,
        tail: int = 100,
        timestamps: bool = False,
    ) -> str:
        args = ["container", "logs", "--tail", str(tail)]
        if timestamps:
            args.append("-t")
        args.append(container_id)
        stdout, _ = self._exec_docker_simple(account_alias, args, timeout=30.0)
        return stdout

    def get_container_stats(
        self, account_alias: str, container_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        args = ["container", "stats", "--no-stream", "--format", '"{{json .}}"']
        if container_id:
            args.append(container_id)
        return self._exec_docker_json(account_alias, args, timeout=30.0)

    # ── 镜像管理 ──────────────────────────────────────────────────

    def list_images(self, account_alias: str) -> list[dict[str, Any]]:
        raw = self._exec_docker_json(
            account_alias,
            ["image", "ls", "--format", "'{{json .}}'"],
        )
        return [self._map_image(item) for item in raw]

    def pull_image(self, account_alias: str, image_name: str) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias,
            ["image", "pull", image_name],
            timeout=300.0,
        )
        return stdout or f"镜像 {image_name} 已拉取"

    def remove_image(self, account_alias: str, image_id: str) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["image", "rm", image_id]
        )
        return stdout or f"镜像 {image_id} 已删除"

    def prune_images(self, account_alias: str) -> dict[str, Any]:
        result = self._exec_docker_json(
            account_alias, ["image", "prune", "-f", "--format", "'{{json .}}'"]
        )
        if not result:
            return {"SpaceReclaimed": 0, "ImagesDeleted": []}
        return result[0]

    def build_image(
        self, account_alias: str, tag: str, dockerfile_path: str, context_path: str
    ) -> str:
        stdout, stderr = self._exec_docker_simple(
            account_alias,
            [
                "image", "build",
                "-t", tag,
                "-f", dockerfile_path,
                context_path,
            ],
            timeout=600.0,
        )
        return stdout or stderr

    def search_images(self, account_alias: str, term: str) -> list[dict[str, Any]]:
        return self._exec_docker_json(
            account_alias,
            ["image", "search", "--format", "'{{json .}}'", term],
        )

    # ── 网络管理 ──────────────────────────────────────────────────

    def list_networks(self, account_alias: str) -> list[dict[str, Any]]:
        return self._pascal_to_camel(
            self._exec_docker_json(
                account_alias,
                ["network", "ls", "--format", "'{{json .}}'"],
            )
        )

    def create_network(
        self, account_alias: str, name: str, driver: str = "bridge"
    ) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias,
            ["network", "create", "--driver", driver, name],
        )
        return stdout or f"网络 {name} 已创建"

    def remove_network(self, account_alias: str, network_id: str) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["network", "rm", network_id]
        )
        return stdout or f"网络 {network_id} 已删除"

    def get_network_info(
        self, account_alias: str, network_id: str
    ) -> dict[str, Any]:
        result = self._exec_docker_json(
            account_alias, ["network", "inspect", network_id]
        )
        if not result:
            raise DockerCommandError(f"网络 '{network_id}' 未找到", -1)
        return result[0]

    # ── 卷管理 ────────────────────────────────────────────────────

    def list_volumes(self, account_alias: str) -> list[dict[str, Any]]:
        return self._pascal_to_camel(
            self._exec_docker_json(
                account_alias,
                ["volume", "ls", "--format", "'{{json .}}'"],
            )
        )

    def create_volume(self, account_alias: str, name: str) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["volume", "create", name]
        )
        return stdout or f"卷 {name} 已创建"

    def remove_volume(self, account_alias: str, volume_name: str) -> str:
        stdout, _ = self._exec_docker_simple(
            account_alias, ["volume", "rm", volume_name]
        )
        return stdout or f"卷 {volume_name} 已删除"

    def get_volume_info(
        self, account_alias: str, volume_name: str
    ) -> dict[str, Any]:
        result = self._exec_docker_json(
            account_alias, ["volume", "inspect", volume_name]
        )
        if not result:
            raise DockerCommandError(f"卷 '{volume_name}' 未找到", -1)
        return result[0]

    # ── Compose 管理 ──────────────────────────────────────────────

    def find_compose_projects(
        self, account_alias: str, search_path: str = "/"
    ) -> list[dict[str, Any]]:
        conn = self._get_connection(account_alias)
        try:
            mgr = conn.manager
            exit_code, stdout, stderr = mgr.exec_command(
                f"find {search_path} -maxdepth 4 "
                r"\( -name 'docker-compose.yml' -o -name 'compose.yaml' -o -name 'docker-compose.yaml' \) "
                r"-not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/\.git/*' 2>/dev/null",
                timeout=30.0,
            )
            if exit_code != 0:
                return []
            projects = []
            for file_path in stdout.strip().split("\n"):
                file_path = file_path.strip()
                if not file_path:
                    continue
                exit_code2, stdout2, _ = mgr.exec_command(
                    f"dirname '{file_path}'", timeout=5.0
                )
                project_dir = stdout2.strip() if exit_code2 == 0 else file_path
                name = Path(project_dir).name
                projects.append({
                    "name": name,
                    "path": project_dir,
                    "status": "unknown",
                    "services": [],
                })
            return projects
        finally:
            ssh_account_service.pool.release_connection(conn)

    def compose_up(
        self, account_alias: str, project_path: str, detach: bool = False
    ) -> str:
        args = ["compose"]
        if project_path.endswith(".yml") or project_path.endswith(".yaml"):
            args.extend(["-f", project_path])
        else:
            args.extend(["-f", f"{project_path}/docker-compose.yml"])
        args.append("up")
        if detach:
            args.append("-d")
        stdout, stderr = self._exec_docker_simple(
            account_alias, args, timeout=300.0
        )
        return stdout or stderr

    def compose_down(
        self, account_alias: str, project_path: str
    ) -> str:
        args = ["compose"]
        if project_path.endswith(".yml") or project_path.endswith(".yaml"):
            args.extend(["-f", project_path])
        else:
            args.extend(["-f", f"{project_path}/docker-compose.yml"])
        args.append("down")
        stdout, stderr = self._exec_docker_simple(
            account_alias, args, timeout=120.0
        )
        return stdout or stderr

    def compose_ps(
        self, account_alias: str, project_path: str
    ) -> list[dict[str, Any]]:
        args = ["compose"]
        if project_path.endswith(".yml") or project_path.endswith(".yaml"):
            args.extend(["-f", project_path])
        else:
            args.extend(["-f", f"{project_path}/docker-compose.yml"])
        args.extend(["ps", "--format", "'{{json .}}'"])
        return self._exec_docker_json(account_alias, args)

    def compose_logs(
        self, account_alias: str, project_path: str, tail: int = 50
    ) -> str:
        args = ["compose"]
        if project_path.endswith(".yml") or project_path.endswith(".yaml"):
            args.extend(["-f", project_path])
        else:
            args.extend(["-f", f"{project_path}/docker-compose.yml"])
        args.extend(["logs", "--tail", str(tail)])
        stdout, _ = self._exec_docker_simple(
            account_alias, args, timeout=30.0
        )
        return stdout

    def compose_scale(
        self,
        account_alias: str,
        project_path: str,
        service: str,
        replicas: int,
    ) -> str:
        args = ["compose"]
        if project_path.endswith(".yml") or project_path.endswith(".yaml"):
            args.extend(["-f", project_path])
        else:
            args.extend(["-f", f"{project_path}/docker-compose.yml"])
        args.extend(["up", "--scale", f"{service}={replicas}", "--no-recreate", "-d"])
        stdout, stderr = self._exec_docker_simple(
            account_alias, args, timeout=120.0
        )
        return stdout or stderr


docker_service = DockerService()
