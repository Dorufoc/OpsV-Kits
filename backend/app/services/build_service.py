from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from app.core.remote_executor import RemoteExecutor, RemoteExecutorError
from app.models.build_task import BuildTask, new_build_task

_JAVA_VERSION_PATTERN = re.compile(
    r'(?:openjdk|java)\s+(?:version\s+)?["\']?(1[._])?(\d+)',
    re.IGNORECASE,
)
_MAVEN_VERSION_PATTERN = re.compile(
    r'Apache Maven\s+(\d+(?:\.\d+)*)',
    re.IGNORECASE,
)
_POM_JAVA_PATTERN = re.compile(
    r'<java\.version>\s*(\d+(?:\.\d+)*)\s*</java\.version>',
)
_POM_SOURCE_PATTERN = re.compile(
    r'<maven\.compiler\.source>\s*(\d+(?:\.\d+)*)\s*</maven\.compiler\.source>',
)
_POM_TARGET_PATTERN = re.compile(
    r'<maven\.compiler\.target>\s*(\d+(?:\.\d+)*)\s*</maven\.compiler\.target>',
)


class InstallTaskInfo:
    def __init__(self, task_id: str, account_alias: str, components: list[str]):
        self.task_id = task_id
        self.account_alias = account_alias
        self.components = components
        self.status: str = "pending"
        self.progress: float = 0.0
        self.message: str = ""
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self._callbacks: list[Callable[[InstallTaskInfo], None]] = []

    def add_callback(self, cb: Callable[[InstallTaskInfo], None]) -> None:
        self._callbacks.append(cb)

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
            "components": self.components,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class BuildService:
    def __init__(self):
        self._tasks: dict[str, InstallTaskInfo] = {}
        self._tasks_lock = threading.Lock()
        self._build_tasks: dict[str, BuildTask] = {}
        self._build_tasks_lock = threading.Lock()

    # ── 环境检查方法 ──────────────────────────────────────────────

    def check_java(
        self, account_alias: str, project_path: str
    ) -> dict:
        executor = RemoteExecutor(account_alias)
        java_result = {"installed": False, "version": "", "required": "", "compatible": False}

        java_check = executor.exec_command("java -version 2>&1")
        if java_check.success:
            match = _JAVA_VERSION_PATTERN.search(java_check.stdout)
            if match:
                java_result["installed"] = True
                version_str = match.group(2)
                java_result["version"] = version_str
        else:
            java_check = executor.exec_command("java -version 2>&1 || true")
            match = _JAVA_VERSION_PATTERN.search(java_check.stdout)
            if match:
                java_result["installed"] = True
                java_result["version"] = match.group(2)

        required_version = self._parse_pom_java_version(executor, project_path)
        java_result["required"] = required_version

        if java_result["installed"] and required_version:
            try:
                installed_major = int(java_result["version"].split(".")[0])
                required_major = int(required_version.split(".")[0])
                java_result["compatible"] = installed_major >= required_major
            except (ValueError, IndexError):
                java_result["compatible"] = False

        return java_result

    def check_maven(
        self, account_alias: str, project_path: str
    ) -> dict:
        executor = RemoteExecutor(account_alias)
        maven_result = {"installed": False, "version": "", "compatible": False}

        mvn_check = executor.exec_command("mvn --version 2>&1")
        if mvn_check.success:
            maven_result["installed"] = True
            maven_result["version"] = mvn_check.stdout.split("\n")[0].strip()
        else:
            mvn_check = executor.exec_command("mvn --version 2>&1 || true")
            if mvn_check.success:
                maven_result["installed"] = True
                maven_result["version"] = mvn_check.stdout.split("\n")[0].strip()

        if maven_result["installed"]:
            match = _MAVEN_VERSION_PATTERN.search(maven_result["version"])
            if match:
                try:
                    ver_parts = [int(x) for x in match.group(1).split(".")]
                    maven_result["compatible"] = (
                        len(ver_parts) >= 2
                        and (ver_parts[0] > 3
                             or (ver_parts[0] == 3 and ver_parts[1] >= 6))
                    )
                except (ValueError, IndexError):
                    maven_result["compatible"] = False

        return maven_result

    # ── 自动安装方法 ──────────────────────────────────────────────

    def install_java(
        self,
        account_alias: str,
        version: str = "17",
        dnf_mirror: Optional[str] = None,
        proxy: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        executor = RemoteExecutor(account_alias)

        def _emit(msg: str) -> None:
            if status_callback:
                status_callback(msg)

        _emit(f"正在安装 OpenJDK {version}...")

        base_cmd = "dnf install -y"
        if dnf_mirror:
            base_cmd += f" --setopt=baseurl={dnf_mirror}"
        if proxy:
            base_cmd += f" --setopt=proxy={proxy}"

        dnf_cmd = f"{base_cmd} java-{version}-openjdk"

        self._try_sudo(executor, dnf_cmd, _emit)

        _emit("验证 Java 安装...")
        verify = executor.exec_command("java -version 2>&1")
        installed = verify.success

        version_info = ""
        if installed:
            match = _JAVA_VERSION_PATTERN.search(verify.stdout)
            if match:
                version_info = match.group(2)

        return {
            "component": "java",
            "version": version,
            "installed": installed,
            "version_info": version_info,
            "message": f"Java {version_info} 安装{'成功' if installed else '失败'}",
        }

    def install_maven(
        self,
        account_alias: str,
        dnf_mirror: Optional[str] = None,
        proxy: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        executor = RemoteExecutor(account_alias)

        def _emit(msg: str) -> None:
            if status_callback:
                status_callback(msg)

        _emit("正在安装 Maven...")

        base_cmd = "dnf install -y"
        if dnf_mirror:
            base_cmd += f" --setopt=baseurl={dnf_mirror}"
        if proxy:
            base_cmd += f" --setopt=proxy={proxy}"

        dnf_cmd = f"{base_cmd} maven"

        self._try_sudo(executor, dnf_cmd, _emit)

        _emit("验证 Maven 安装...")
        verify = executor.exec_command("mvn --version 2>&1")
        installed = verify.success

        version_info = ""
        if installed:
            version_info = verify.stdout.split("\n")[0].strip()

        return {
            "component": "maven",
            "installed": installed,
            "version_info": version_info,
            "message": f"Maven 安装{'成功' if installed else '失败'}",
        }

    def install_environment(
        self,
        account_alias: str,
        java_version: Optional[str] = None,
        dnf_mirror: Optional[str] = None,
        proxy: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> InstallTaskInfo:
        if task_id is None:
            task_id = uuid4().hex[:12]

        components = []
        if java_version:
            components.append(f"java-{java_version}")
        components.append("maven")

        task = InstallTaskInfo(
            task_id=task_id,
            account_alias=account_alias,
            components=components,
        )
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()

        with self._tasks_lock:
            self._tasks[task_id] = task

        def _update_status(msg: str) -> None:
            task.message = msg
            if "失败" in msg or "错误" in msg:
                pass
            task._notify()

        def _run_install():
            try:
                results = []
                if java_version:
                    task.progress = 10.0
                    _update_status(f"开始安装 Java {java_version}...")
                    java_result = self.install_java(
                        account_alias,
                        version=java_version,
                        dnf_mirror=dnf_mirror,
                        proxy=proxy,
                        status_callback=_update_status,
                    )
                    results.append(java_result)
                    task.progress = 55.0
                    _update_status("Java 安装完成")

                task.progress = 60.0
                _update_status("开始安装 Maven...")
                maven_result = self.install_maven(
                    account_alias,
                    dnf_mirror=dnf_mirror,
                    proxy=proxy,
                    status_callback=_update_status,
                )
                results.append(maven_result)
                task.progress = 95.0
                _update_status("Maven 安装完成")

                all_ok = all(r["installed"] for r in results)
                task.progress = 100.0
                task.status = "completed" if all_ok else "failed"
                if not all_ok:
                    failed = [r["component"] for r in results if not r["installed"]]
                    task.error = f"以下组件安装失败: {', '.join(failed)}"
                _update_status(
                    "环境安装完成" if all_ok else f"部分组件安装失败: {task.error}"
                )
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                _update_status(f"安装过程出错: {e}")
            finally:
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task._notify()

        t = threading.Thread(target=_run_install, daemon=True)
        t.start()

        return task

    # ── 状态方法 ──────────────────────────────────────────────────

    def check_environment(
        self, account_alias: str, project_path: str
    ) -> dict:
        java_info = self.check_java(account_alias, project_path)
        maven_info = self.check_maven(account_alias, project_path)

        java_ok = java_info["installed"] and java_info["compatible"]
        maven_ok = maven_info["installed"] and maven_info["compatible"]

        return {
            "account_alias": account_alias,
            "project_path": project_path,
            "java": java_info,
            "maven": maven_info,
            "all_ready": java_ok and maven_ok,
        }

    def get_task(self, task_id: str) -> Optional[InstallTaskInfo]:
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

    # ── 编译与打包方法 ──────────────────────────────────────────

    def compile_project(
        self,
        account_alias: str,
        project_path: str,
        command: str = "mvn clean compile",
    ) -> BuildTask:
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="compile",
            config={"command": command},
        )

    def package_project(
        self,
        account_alias: str,
        project_path: str,
        command: str = "mvn clean package -DskipTests",
    ) -> BuildTask:
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="package",
            config={"command": command},
        )

    # ── 运行方法 ────────────────────────────────────────────────

    def run_jar(
        self,
        account_alias: str,
        project_path: str,
        jar_path: str,
        jvm_args: str = "",
        app_args: str = "",
    ) -> BuildTask:
        config = {
            "run_mode": "jar",
            "jar_path": jar_path,
            "jvm_args": jvm_args,
            "app_args": app_args,
        }
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="run",
            config=config,
        )

    def run_spring_boot(
        self,
        account_alias: str,
        project_path: str,
        main_class: Optional[str] = None,
    ) -> BuildTask:
        config: dict = {
            "run_mode": "spring-boot",
        }
        if main_class:
            config["main_class"] = main_class
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="run",
            config=config,
        )

    def run_exec_java(
        self,
        account_alias: str,
        project_path: str,
        main_class: str,
    ) -> BuildTask:
        config = {
            "run_mode": "exec",
            "main_class": main_class,
        }
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="run",
            config=config,
        )

    # ── 任务管理 ────────────────────────────────────────────────

    def create_build_task(
        self,
        account_alias: str,
        project_path: str,
        action: str,
        config: Optional[dict] = None,
    ) -> BuildTask:
        task = new_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action=action,
            config=config,
        )

        with self._build_tasks_lock:
            self._build_tasks[task.task_id] = task

        t = threading.Thread(
            target=self._run_build_task,
            args=(task,),
            daemon=True,
        )
        t.start()

        return task

    def get_build_task(self, task_id: str) -> Optional[BuildTask]:
        with self._build_tasks_lock:
            return self._build_tasks.get(task_id)

    def stop_build_task(self, task_id: str) -> bool:
        task = self.get_build_task(task_id)
        if task is None:
            return False
        if task.status not in ("pending", "running"):
            return False

        task.request_stop()
        return True

    def get_build_history(
        self,
        account_alias: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        with self._build_tasks_lock:
            all_tasks = list(self._build_tasks.values())

        if account_alias:
            all_tasks = [t for t in all_tasks if t.account_alias == account_alias]

        all_tasks.sort(
            key=lambda t: t.started_at or "",
            reverse=True,
        )
        return [t.to_dict() for t in all_tasks[:limit]]

    # ── 内部方法 ────────────────────────────────────────────────

    def _run_build_task(self, task: BuildTask) -> None:
        task.status = "running"
        task.started_at = datetime.now(timezone.utc).isoformat()
        task.append_log(f"[{datetime.now().isoformat()}] 任务已启动\n")

        try:
            action = task.action
            if action in ("compile", "package"):
                self._execute_maven_task(task)
            elif action == "run":
                self._execute_run_task(task)
            else:
                task.status = "failed"
                task.append_log(f"未知的操作类型: {action}\n")
        except Exception as e:
            task.status = "failed"
            task.append_log(f"任务执行异常: {e}\n")
        finally:
            if task.status == "running":
                task.status = "completed"
            task.completed_at = datetime.now(timezone.utc).isoformat()
            task.append_log(f"[{task.completed_at}] 任务结束 (状态: {task.status})\n")
            task._notify()

    def _execute_maven_task(self, task: BuildTask) -> None:
        command = task.config.get("command", "mvn clean compile")
        action_label = "编译" if task.action == "compile" else "打包"
        task.append_log(f"执行 Maven {action_label}: {command}\n")
        task.append_log(f"工作目录: {task.project_path}\n\n")

        full_cmd = f"cd {task.project_path} && {command} 2>&1"

        executor = RemoteExecutor(task.account_alias)

        def _on_output(text: str) -> None:
            task.append_log(text)

        exit_code = executor.exec_command_stream(
            command=full_cmd,
            output_callback=_on_output,
            timeout=600.0,
            stop_check=lambda: task.stop_requested,
        )

        task.exit_code = exit_code

        if task.stop_requested:
            task.status = "stopped"
            task.append_log(f"\nMaven {action_label} 已被用户停止\n")
        elif exit_code == 0:
            task.status = "completed"
            task.append_log(f"\nMaven {action_label} 成功 (exit_code=0)\n")
        else:
            task.status = "failed"
            task.append_log(f"\nMaven {action_label} 失败 (exit_code={exit_code})\n")

    def _execute_run_task(self, task: BuildTask) -> None:
        run_mode = task.config.get("run_mode", "jar")

        if run_mode == "jar":
            self._run_jar_internal(task)
        elif run_mode == "spring-boot":
            self._run_spring_boot_internal(task)
        elif run_mode == "exec":
            self._run_exec_java_internal(task)
        else:
            task.status = "failed"
            task.append_log(f"未知的运行模式: {run_mode}\n")

    def _run_jar_internal(self, task: BuildTask) -> None:
        jar_path = task.config.get("jar_path", "")
        jvm_args = task.config.get("jvm_args", "")
        app_args = task.config.get("app_args", "")

        full_jar_path = jar_path
        if not jar_path.startswith("/"):
            full_jar_path = f"{task.project_path.rstrip('/')}/{jar_path}"

        java_cmd = f"java {jvm_args} -jar {full_jar_path} {app_args}".strip()
        log_file = f"{task.project_path.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log(f"运行模式: java -jar\n")
        task.append_log(f"JAR 路径: {full_jar_path}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        nohup_cmd = f"nohup {java_cmd} > {log_file} 2>&1 & echo $!"

        executor = RemoteExecutor(task.account_alias)
        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.append_log(f"标准输出重定向至: {log_file}\n")
                task.status = "running"
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")

    def _run_spring_boot_internal(self, task: BuildTask) -> None:
        main_class = task.config.get("main_class")
        log_file = f"{task.project_path.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log("运行模式: mvn spring-boot:run\n")
        if main_class:
            task.append_log(f"主类: {main_class}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        mvn_cmd = f"cd {task.project_path} && mvn spring-boot:run"
        nohup_cmd = f"nohup {mvn_cmd} > {log_file} 2>&1 & echo $!"

        executor = RemoteExecutor(task.account_alias)
        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.status = "running"
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")

    def _run_exec_java_internal(self, task: BuildTask) -> None:
        main_class = task.config.get("main_class", "")
        log_file = f"{task.project_path.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log("运行模式: mvn exec:java\n")
        task.append_log(f"主类: {main_class}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        mvn_cmd = (
            f"cd {task.project_path} "
            f"&& mvn exec:java -Dexec.mainClass=\"{main_class}\""
        )
        nohup_cmd = f"nohup {mvn_cmd} > {log_file} 2>&1 & echo $!"

        executor = RemoteExecutor(task.account_alias)
        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.status = "running"
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")

    # ── 内部辅助方法 ──────────────────────────────────────────────

    def _parse_pom_java_version(
        self, executor: RemoteExecutor, project_path: str
    ) -> str:
        pom_path = f"{project_path.rstrip('/')}/pom.xml"
        result = executor.exec_command(f"cat '{pom_path}' 2>&1 || true")
        if not result.success or not result.stdout:
            return ""

        pom_content = result.stdout

        match = _POM_JAVA_PATTERN.search(pom_content)
        if match:
            return match.group(1)

        source_match = _POM_SOURCE_PATTERN.search(pom_content)
        target_match = _POM_TARGET_PATTERN.search(pom_content)
        if source_match:
            ver = source_match.group(1)
            if "." in ver:
                ver = ver.split(".")[-1]
            return ver
        if target_match:
            ver = target_match.group(1)
            if "." in ver:
                ver = ver.split(".")[-1]
            return ver

        return ""

    def _try_sudo(
        self,
        executor: RemoteExecutor,
        command: str,
        emit: Callable[[str], None],
    ) -> None:
        result = executor.exec_command(command, timeout=120.0)
        if result.success:
            emit(result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
            return

        stderr_text = result.stderr
        if isinstance(stderr_text, bytes):
            stderr_text = stderr_text.decode("utf-8", errors="replace")
        stderr_lower = stderr_text.lower()
        if "permission denied" in stderr_lower or "not a root" in stderr_lower:
            emit("权限不足，尝试使用 sudo...")
            sudo_cmd = f"sudo {command}"
            sudo_result = executor.exec_with_pty(sudo_cmd, timeout=180.0)
            if sudo_result.success:
                emit(
                    sudo_result.stdout[-200:]
                    if len(sudo_result.stdout) > 200
                    else sudo_result.stdout
                )
                return
            raise RemoteExecutorError(
                f"sudo 安装失败 (需 root 权限): {sudo_result.stderr[:200]}"
            )

        raise RemoteExecutorError(
            f"安装命令执行失败 (exit_code={result.exit_code}): {result.stderr[:200]}"
        )


build_service = BuildService()
