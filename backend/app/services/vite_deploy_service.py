from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from app.core.node_env_manager import NodeEnvManager
from app.core.nginx_config_manager import NginxConfigManager
from app.core.package_manager import PackageManager
from app.core.remote_executor import RemoteExecutor
from app.core.vite_project_detector import ViteProjectDetector


class ViteDeployTask:
    def __init__(
        self,
        task_id: str,
        account_alias: str,
        project_path: str,
        step: str,
        config: Optional[dict] = None,
    ):
        self.task_id = task_id
        self.account_alias = account_alias
        self.project_path = project_path
        self.step = step
        self.config = config or {}
        self.status: str = "pending"
        self.progress: float = 0.0
        self.message: str = ""
        self.log: str = ""
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self.url: Optional[str] = None
        self._callbacks: list[Callable[[ViteDeployTask], None]] = []
        self._stop_requested = False

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    def request_stop(self) -> None:
        self._stop_requested = True

    def add_callback(self, cb: Callable[[ViteDeployTask], None]) -> None:
        self._callbacks.append(cb)

    def append_log(self, text: str) -> None:
        self.log += text
        self._notify()

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception:
                pass

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "account_alias": self.account_alias,
            "project_path": self.project_path,
            "step": self.step,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "log": self.log,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "url": self.url,
        }


class ViteDeployService:
    def __init__(self):
        self._tasks: dict[str, ViteDeployTask] = {}
        self._tasks_lock = threading.Lock()

    def _new_task_id(self) -> str:
        return uuid4().hex[:12]

    def _create_task(
        self,
        account_alias: str,
        project_path: str,
        step: str,
        config: Optional[dict] = None,
        task_id: Optional[str] = None,
    ) -> ViteDeployTask:
        if task_id is None:
            task_id = self._new_task_id()
        task = ViteDeployTask(
            task_id=task_id,
            account_alias=account_alias,
            project_path=project_path,
            step=step,
            config=config or {},
        )
        with self._tasks_lock:
            self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ViteDeployTask]:
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def get_task_dict(self, task_id: str) -> Optional[dict]:
        task = self.get_task(task_id)
        if task is None:
            return None
        return task.to_dict()

    def list_tasks(
        self, account_alias: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        with self._tasks_lock:
            all_tasks = list(self._tasks.values())
        if account_alias:
            all_tasks = [t for t in all_tasks if t.account_alias == account_alias]
        all_tasks.sort(key=lambda t: t.started_at or "", reverse=True)
        return [t.to_dict() for t in all_tasks[:limit]]

    def check_environment(self, account_alias: str, project_path: str) -> dict:
        node_manager = NodeEnvManager(account_alias)
        nginx_manager = NginxConfigManager(account_alias)
        detector = ViteProjectDetector(account_alias)

        node_info = node_manager.check_node()
        nginx_info = nginx_manager.check_nginx()
        vite_info = detector.is_vite_project(project_path=project_path)
        framework_info = detector.detect_framework(project_path=project_path)

        node_ok = node_info["installed"] and node_info["npm_installed"]
        nginx_ok = nginx_info["installed"]

        return {
            "account_alias": account_alias,
            "project_path": project_path,
            "node": node_info,
            "nginx": nginx_info,
            "vite": vite_info,
            "framework": framework_info,
            "all_ready": node_ok and nginx_ok and vite_info["is_vite"],
        }

    def install_node(
        self,
        account_alias: str,
        project_path: str,
        version: str = "20",
        task_id: Optional[str] = None,
    ) -> ViteDeployTask:
        task = self._create_task(
            account_alias=account_alias,
            project_path=project_path,
            step="install_node",
            config={"version": version},
            task_id=task_id,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.message = f"开始安装 Node.js {version}..."
        task._notify()

        def _run():
            try:
                node_manager = NodeEnvManager(account_alias)

                def _emit(msg: str) -> None:
                    task.append_log(msg + "\n")
                    task.message = msg

                result = node_manager.install_node(
                    version=version,
                    callback=_emit,
                )
                task.progress = 100.0
                if result["installed"]:
                    task.status = "completed"
                    task.message = result["message"]
                else:
                    task.status = "failed"
                    task.error = result["message"]
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.append_log(f"安装 Node.js 出错: {e}\n")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return task

    def install_deps(
        self,
        account_alias: str,
        project_path: str,
        force: bool = False,
        task_id: Optional[str] = None,
    ) -> ViteDeployTask:
        task = self._create_task(
            account_alias=account_alias,
            project_path=project_path,
            step="install_deps",
            config={"force": force},
            task_id=task_id,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.message = "开始安装项目依赖..."
        task._notify()

        def _run():
            try:
                executor = RemoteExecutor(account_alias)
                resolved_path = executor.resolve_path(project_path)
                pkg_manager = PackageManager(account_alias)
                manager = pkg_manager.detect(project_path=resolved_path)
                install_cmd = pkg_manager.get_install_command()
                if force:
                    install_cmd += " --force"

                task.append_log(f"检测到包管理器: {manager}\n")
                task.append_log(f"执行命令: {install_cmd}\n")
                task.message = f"使用 {manager} 安装依赖..."

                def _emit(text: str) -> None:
                    task.append_log(text)

                exit_code = executor.exec_command_stream(
                    f"cd {resolved_path} && {install_cmd} 2>&1",
                    output_callback=_emit,
                    timeout=600.0,
                    stop_check=lambda: task.stop_requested,
                )

                task.exit_code = exit_code
                if task.stop_requested:
                    task.status = "stopped"
                    task.message = "依赖安装已被用户停止"
                elif exit_code == 0:
                    task.status = "completed"
                    task.progress = 100.0
                    task.message = "依赖安装成功"
                else:
                    task.status = "failed"
                    task.error = f"依赖安装失败 (exit_code={exit_code})"
                    task.message = task.error
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.append_log(f"安装依赖出错: {e}\n")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return task

    def build(
        self,
        account_alias: str,
        project_path: str,
        build_command: str = "npm run build",
        task_id: Optional[str] = None,
    ) -> ViteDeployTask:
        task = self._create_task(
            account_alias=account_alias,
            project_path=project_path,
            step="build",
            config={"build_command": build_command},
            task_id=task_id,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.message = "开始构建项目..."
        task._notify()

        def _run():
            try:
                executor = RemoteExecutor(account_alias)
                resolved_path = executor.resolve_path(project_path)

                task.append_log(f"工作目录: {resolved_path}\n")
                task.append_log(f"构建命令: {build_command}\n\n")

                def _emit(text: str) -> None:
                    task.append_log(text)

                exit_code = executor.exec_command_stream(
                    f"cd {resolved_path} && {build_command} 2>&1",
                    output_callback=_emit,
                    timeout=600.0,
                    stop_check=lambda: task.stop_requested,
                )

                task.exit_code = exit_code
                if task.stop_requested:
                    task.status = "stopped"
                    task.message = "构建已被用户停止"
                elif exit_code == 0:
                    task.status = "completed"
                    task.progress = 100.0
                    task.message = "构建成功"
                    task.append_log("\n构建完成\n")
                else:
                    task.status = "failed"
                    task.error = f"构建失败 (exit_code={exit_code})"
                    task.message = task.error
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.append_log(f"构建出错: {e}\n")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return task

    def deploy_nginx(
        self,
        account_alias: str,
        project_alias: str,
        project_path: str,
        port: int = 8080,
        task_id: Optional[str] = None,
    ) -> ViteDeployTask:
        task = self._create_task(
            account_alias=account_alias,
            project_path=project_path,
            step="deploy_nginx",
            config={"project_alias": project_alias, "port": port},
            task_id=task_id,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.message = "开始配置 Nginx..."
        task._notify()

        def _run():
            try:
                executor = RemoteExecutor(account_alias)
                resolved_path = executor.resolve_path(project_path)
                nginx_manager = NginxConfigManager(account_alias)

                task.append_log("检查 Nginx 环境...\n")
                nginx_info = nginx_manager.check_nginx()
                if not nginx_info["installed"]:
                    task.append_log("Nginx 未安装，开始安装...\n")
                    install_result = nginx_manager.install_nginx()
                    task.append_log(install_result["message"] + "\n")
                    if not install_result["installed"]:
                        task.status = "failed"
                        task.error = "Nginx 安装失败"
                        task.message = task.error
                        return

                task.progress = 30.0
                task.append_log(f"检查端口 {port} 冲突...\n")
                port_check = nginx_manager.check_port_conflict(port)
                if port_check["conflict"]:
                    task.append_log(f"警告: 端口 {port} 已被占用\n")
                    for proc in port_check["processes"]:
                        task.append_log(f"  {proc}\n")

                task.progress = 50.0
                dist_path = f"{resolved_path.rstrip('/')}/dist"
                task.append_log(f"生成 Nginx 配置...\n")
                task.append_log(f"根目录: {dist_path}\n")
                config_path = nginx_manager.generate_config(
                    project_alias=project_alias,
                    port=port,
                    server_name="_",
                    root_path=dist_path,
                )
                task.append_log(f"配置文件: {config_path}\n")

                task.progress = 80.0
                task.append_log("重载 Nginx...\n")
                reload_result = nginx_manager.reload_nginx()
                if reload_result["success"]:
                    task.progress = 100.0
                    task.status = "completed"
                    task.message = "Nginx 部署成功"
                    task.url = f"http://{account_alias}:{port}"
                    task.append_log("Nginx 配置已生效\n")
                else:
                    task.status = "failed"
                    task.error = reload_result["message"]
                    task.message = task.error
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.append_log(f"Nginx 部署出错: {e}\n")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return task

    def full_deploy(
        self,
        account_alias: str,
        project_alias: str,
        project_path: str,
        config: Optional[dict] = None,
    ) -> ViteDeployTask:
        cfg = config or {}
        node_version = cfg.get("node_version", "20")
        nginx_port = cfg.get("nginx_port", 8080)
        build_command = cfg.get("build_command", "npm run build")
        force = cfg.get("force", False)

        task = self._create_task(
            account_alias=account_alias,
            project_path=project_path,
            step="full_deploy",
            config=cfg,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.message = "开始一键部署..."
        task._notify()

        def _run():
            try:
                executor = RemoteExecutor(account_alias)
                resolved_path = executor.resolve_path(project_path)

                steps = [
                    ("检查环境", 5.0),
                    ("安装 Node.js", 20.0),
                    ("安装依赖", 40.0),
                    ("构建项目", 70.0),
                    ("配置 Nginx", 90.0),
                    ("完成", 100.0),
                ]

                def _update_step(name: str, progress: float) -> None:
                    task.message = name
                    task.progress = progress
                    task.append_log(f"\n>>> {name}\n")
                    task._notify()

                _update_step("检查环境", 5.0)
                env = self.check_environment(account_alias, project_path)
                task.append_log(f"Node.js: {'已安装' if env['node']['installed'] else '未安装'}\n")
                task.append_log(f"Nginx: {'已安装' if env['nginx']['installed'] else '未安装'}\n")
                task.append_log(f"Vite 项目: {'是' if env['vite']['is_vite'] else '否'}\n")

                if not env["node"]["installed"] or not env["node"]["npm_installed"]:
                    _update_step("安装 Node.js", 20.0)
                    node_manager = NodeEnvManager(account_alias)

                    def _node_emit(msg: str) -> None:
                        task.append_log(msg + "\n")

                    node_result = node_manager.install_node(
                        version=node_version,
                        callback=_node_emit,
                    )
                    if not node_result["installed"]:
                        task.status = "failed"
                        task.error = node_result["message"]
                        task.message = task.error
                        return

                _update_step("安装依赖", 40.0)
                pkg_manager = PackageManager(account_alias)
                manager = pkg_manager.detect(project_path=resolved_path)
                install_cmd = pkg_manager.get_install_command()
                if force:
                    install_cmd += " --force"

                task.append_log(f"使用 {manager}: {install_cmd}\n")

                def _dep_emit(text: str) -> None:
                    task.append_log(text)

                dep_exit = executor.exec_command_stream(
                    f"cd {resolved_path} && {install_cmd} 2>&1",
                    output_callback=_dep_emit,
                    timeout=600.0,
                    stop_check=lambda: task.stop_requested,
                )
                if task.stop_requested:
                    task.status = "stopped"
                    task.message = "部署已被用户停止"
                    return
                if dep_exit != 0:
                    task.status = "failed"
                    task.error = f"依赖安装失败 (exit_code={dep_exit})"
                    task.message = task.error
                    return

                _update_step("构建项目", 70.0)
                task.append_log(f"执行: {build_command}\n")

                def _build_emit(text: str) -> None:
                    task.append_log(text)

                build_exit = executor.exec_command_stream(
                    f"cd {resolved_path} && {build_command} 2>&1",
                    output_callback=_build_emit,
                    timeout=600.0,
                    stop_check=lambda: task.stop_requested,
                )
                if task.stop_requested:
                    task.status = "stopped"
                    task.message = "部署已被用户停止"
                    return
                if build_exit != 0:
                    task.status = "failed"
                    task.error = f"构建失败 (exit_code={build_exit})"
                    task.message = task.error
                    return

                _update_step("配置 Nginx", 90.0)
                nginx_manager = NginxConfigManager(account_alias)
                nginx_info = nginx_manager.check_nginx()
                if not nginx_info["installed"]:
                    task.append_log("安装 Nginx...\n")
                    install_result = nginx_manager.install_nginx()
                    task.append_log(install_result["message"] + "\n")
                    if not install_result["installed"]:
                        task.status = "failed"
                        task.error = "Nginx 安装失败"
                        task.message = task.error
                        return

                dist_path = f"{resolved_path.rstrip('/')}/dist"
                config_path = nginx_manager.generate_config(
                    project_alias=project_alias,
                    port=nginx_port,
                    server_name="_",
                    root_path=dist_path,
                )
                task.append_log(f"配置已写入: {config_path}\n")

                reload_result = nginx_manager.reload_nginx()
                if not reload_result["success"]:
                    task.status = "failed"
                    task.error = reload_result["message"]
                    task.message = task.error
                    return

                task.progress = 100.0
                task.status = "completed"
                task.message = "一键部署完成"
                task.url = f"http://{account_alias}:{nginx_port}"
                task.append_log(f"\n部署成功，访问地址: {task.url}\n")
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.append_log(f"部署出错: {e}\n")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return task


vite_deploy_service = ViteDeployService()
