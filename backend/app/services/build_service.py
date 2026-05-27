from __future__ import annotations

import os
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
        local_path: Optional[str] = None,
        command: str = "mvn clean compile",
        jdk_version: Optional[str] = None,
    ) -> BuildTask:
        config = {"command": command}
        if jdk_version:
            config["jdk_version"] = jdk_version
        if local_path:
            config["local_path"] = local_path
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="compile",
            config=config,
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

    def test_project(
        self,
        account_alias: str,
        project_path: str,
        local_path: Optional[str] = None,
        command: str = "mvn clean test",
        jdk_version: Optional[str] = None,
    ) -> BuildTask:
        config = {"command": command}
        if jdk_version:
            config["jdk_version"] = jdk_version
        if local_path:
            config["local_path"] = local_path
        return self.create_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action="test",
            config=config,
        )

    # ── 运行方法 ────────────────────────────────────────────────

    def run_jar(
        self,
        account_alias: str,
        project_path: str,
        jar_path: str,
        jvm_args: str = "",
        app_args: str = "",
        local_path: Optional[str] = None,
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
            local_path=local_path,
        )

    def run_spring_boot(
        self,
        account_alias: str,
        project_path: str,
        main_class: Optional[str] = None,
        local_path: Optional[str] = None,
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
            local_path=local_path,
        )

    def run_exec_java(
        self,
        account_alias: str,
        project_path: str,
        main_class: str,
        local_path: Optional[str] = None,
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
            local_path=local_path,
        )

    # ── 任务管理 ────────────────────────────────────────────────

    def create_build_task(
        self,
        account_alias: str,
        project_path: str,
        action: str,
        config: Optional[dict] = None,
        local_path: Optional[str] = None,
    ) -> BuildTask:
        final_config = config.copy() if config else {}
        if local_path:
            final_config["local_path"] = local_path
        task = new_build_task(
            account_alias=account_alias,
            project_path=project_path,
            action=action,
            config=final_config,
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
            if action in ("compile", "package", "test"):
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
            if task.action != "run":
                # 只有非运行任务才自动结束
                if task.status == "running":
                    task.status = "completed"
                task.completed_at = datetime.now(timezone.utc).isoformat()
                task.append_log(f"[{task.completed_at}] 任务结束 (状态: {task.status})\n")
            task._notify()

    def _detect_maven_root(self, executor: RemoteExecutor, base_path: str) -> Optional[str]:
        # 首先检查直接路径
        result = executor.exec_command(
            f"bash -c 'if [ -f {base_path}/pom.xml ]; then echo {base_path}; "
            # 如果没有，在 base_path 下最多 3 层深度查找
            f"else d=$(find {base_path} -maxdepth 3 -name pom.xml -not -path \"*/target/*\" 2>/dev/null | head -1); "
            f"if [ -n \"$d\" ]; then dirname \"$d\"; "
            # 如果还没有，检查是否在 base_path 的父目录下有同名文件夹（处理旧同步位置）
            f"else parent=$(dirname {base_path}); folder=$(basename {base_path}); "
            f"d2=$(find \"$parent\" -maxdepth 2 -name pom.xml -path \"*$folder*\" -not -path \"*/target/*\" 2>/dev/null | head -1); "
            f"if [ -n \"$d2\" ]; then dirname \"$d2\"; fi; fi; fi'",
            timeout=10.0,
        )
        if result.success and result.stdout.strip():
            return result.stdout.strip().split("\n")[-1].strip()
        return None

    def _ensure_java(self, executor: RemoteExecutor, task: BuildTask, work_dir: Optional[str] = None) -> bool:
        jdk_version = task.config.get("jdk_version", "")
        if not jdk_version:
            # 使用正确的工作目录来解析 pom.xml
            parse_path = work_dir if work_dir else task.project_path
            required = self._parse_pom_java_version(executor, parse_path)
            jdk_version = required or ""

        check = executor.exec_command("java -version 2>&1", timeout=10.0)
        if check.success:
            match = _JAVA_VERSION_PATTERN.search(check.stdout)
            if match:
                installed = match.group(2)
                if jdk_version:
                    try:
                        if int(installed.split(".")[0]) >= int(jdk_version):
                            task.append_log(f"\x1b[32mJava {installed} 已就绪\x1b[0m\n")
                            return True
                    except (ValueError, IndexError):
                        pass
                else:
                    task.append_log(f"\x1b[32mJava {installed} 已就绪\x1b[0m\n")
                    return True

        target_ver = jdk_version or "17"
        task.append_log(f"\x1b[33m正在安装 OpenJDK {target_ver} (java-{target_ver}-openjdk-devel)...\x1b[0m\n")

        # 使用流式执行来实时显示安装日志
        def _log(t: str) -> None:
            task.append_log(t)

        # 先尝试 dnf
        install_cmd = f"sudo dnf install -y java-{target_ver}-openjdk java-{target_ver}-openjdk-devel 2>&1"
        exit_code = executor.exec_command_stream(install_cmd, output_callback=_log, timeout=300.0)
        
        # 如果 dnf 失败，尝试 yum
        if exit_code != 0:
            task.append_log("\x1b[33mdnf 失败，尝试 yum...\x1b[0m\n")
            install_cmd = f"sudo yum install -y java-{target_ver}-openjdk java-{target_ver}-openjdk-devel 2>&1"
            exit_code = executor.exec_command_stream(install_cmd, output_callback=_log, timeout=300.0)

        # 验证安装
        verify = executor.exec_command("java -version 2>&1", timeout=10.0)
        if verify.success:
            task.append_log(f"\x1b[32mOpenJDK {target_ver} 安装成功\x1b[0m\n")
            return True

        task.append_log(f"\x1b[31mJDK 安装失败，退出码: {exit_code}\x1b[0m\n")
        return False

    def _ensure_maven(self, executor: RemoteExecutor, task: BuildTask) -> bool:
        check = executor.exec_command("mvn --version 2>&1 | head -1", timeout=10.0)
        if check.success and "Apache Maven" in check.stdout:
            task.append_log(f"\x1b[32mMaven 已就绪: {check.stdout.strip()}\x1b[0m\n")
            return True

        def _log(t: str) -> None:
            task.append_log(t)

        task.append_log("\x1b[33mmvn 未安装，正在安装...\x1b[0m\n")

        install_cmd = "sudo dnf install -y maven 2>&1"
        exit_code = executor.exec_command_stream(install_cmd, output_callback=_log, timeout=180.0)
        if exit_code != 0:
            task.append_log("\x1b[33mdnf 失败，尝试 yum...\x1b[0m\n")
            exit_code = executor.exec_command_stream(
                "sudo yum install -y maven 2>&1", output_callback=_log, timeout=180.0
            )

        verify = executor.exec_command("mvn --version 2>&1 | head -1", timeout=10.0)
        if verify.success:
            task.append_log(f"\x1b[32mMaven 安装成功: {verify.stdout.strip()}\x1b[0m\n")
            return True

        task.append_log("\x1b[31mMaven 安装失败，请检查网络或手动安装\x1b[0m\n")
        return False

    def _execute_maven_task(self, task: BuildTask) -> None:
        command = task.config.get("command", "mvn clean compile")
        if task.action == "compile":
            action_label = "编译"
        elif task.action == "package":
            action_label = "打包"
        elif task.action == "test":
            action_label = "测试"
        else:
            action_label = "执行"
        task.append_log(f"执行 Maven {action_label}: {command}\n")

        executor = RemoteExecutor(task.account_alias)
        resolved_path = executor.resolve_path(task.project_path)
        # 添加项目文件夹名称，确保和同步服务使用一致的逻辑
        local_path = task.config.get("local_path")
        if local_path:
            project_folder = os.path.basename(os.path.abspath(local_path))
            resolved_path = resolved_path.rstrip("/") + "/" + project_folder
        work_dir = self._detect_maven_root(executor, resolved_path)

        if work_dir is None:
            # 尝试列出更多位置的目录内容，帮助调试
            debug_info = []
            # 1. 列出配置的远程路径
            ls1 = executor.exec_command(f"ls -LA {resolved_path} 2>&1 | head -30", timeout=10.0)
            debug_info.append(f"--- 配置路径 {resolved_path} 的内容 ---")
            debug_info.append(ls1.stdout.strip() if ls1.success else f"无法列出: {ls1.stderr}")
            
            # 2. 检查父目录
            parent_path = "/".join(resolved_path.rstrip("/").split("/")[:-1])
            if parent_path:
                ls2 = executor.exec_command(f"ls -LA {parent_path} 2>&1 | head -30", timeout=10.0)
                debug_info.append(f"\n--- 父目录 {parent_path} 的内容 ---")
                debug_info.append(ls2.stdout.strip() if ls2.success else f"无法列出: {ls2.stderr}")
            
            task.append_log(
                f"工作目录: {resolved_path}\n"
                f"\x1b[31m未找到 pom.xml (搜索深度 3 层)\x1b[0m\n"
                f"\x1b[33m调试信息:\x1b[0m\n" + "\n".join(debug_info) + "\n"
                f"\x1b[33m请先同步文件，或检查项目路径配置\x1b[0m\n"
            )
            task.status = "failed"
            return

        task.append_log(f"工作目录: {work_dir}\n\n")

        if not self._ensure_java(executor, task, work_dir):
            task.status = "failed"
            task.append_log("Java 环境不可用，编译终止\n")
            return

        if not self._ensure_maven(executor, task):
            task.status = "failed"
            task.append_log("Maven 环境不可用，编译终止\n")
            return

        # 构建完整的命令，确保使用正确的 Java 版本
        cmd_parts = [f"mkdir -p {work_dir}", f"cd {work_dir}"]
        
        # 如果需要特定的 JDK 版本，设置 JAVA_HOME
        jdk_version = task.config.get("jdk_version", "")
        if not jdk_version:
            required = self._parse_pom_java_version(executor, work_dir)
            jdk_version = required or ""
        
        if jdk_version:
            # 检测并设置 JAVA_HOME
            java_home_cmd = (
                f"for dir in '/usr/lib/jvm/java-{jdk_version}-openjdk' "
                f"'/usr/lib/jvm/java-{jdk_version}' "
                f"'/usr/lib/jvm/jre-{jdk_version}-openjdk'; do "
                f"if [ -d \"$dir\" ]; then "
                f"export JAVA_HOME=\"$dir\" && "
                f"export PATH=\"$JAVA_HOME/bin:$PATH\" && "
                f"echo \"使用 JAVA_HOME: $JAVA_HOME\" && "
                f"break; "
                f"fi; "
                f"done"
            )
            cmd_parts.append(java_home_cmd)
            
            # 覆盖 Maven 编译器配置，使用指定的 JDK 版本
            # 这会覆盖 pom.xml 中的 maven.compiler.source 和 maven.compiler.target
            if "mvn " in command:
                # 先移除可能存在的 2>&1
                base_cmd = command
                if base_cmd.strip().endswith(" 2>&1"):
                    base_cmd = base_cmd[:-6].strip()
                
                # 检查是否已有版本参数，如果没有则添加
                if "-Dmaven.compiler.source" not in base_cmd and "-Dmaven.compiler.target" not in base_cmd:
                    base_cmd = f"{base_cmd} -Dmaven.compiler.source={jdk_version} -Dmaven.compiler.target={jdk_version}"
                
                # 重新添加 2>&1
                command = f"{base_cmd} 2>&1"
            else:
                # 非 Maven 命令，确保有 2>&1
                if not command.strip().endswith(" 2>&1"):
                    command = f"{command} 2>&1"
        else:
            # 没有指定 JDK 版本，确保有 2>&1
            if not command.strip().endswith(" 2>&1"):
                command = f"{command} 2>&1"
        
        cmd_parts.append(command)
        full_cmd = " && ".join(cmd_parts)

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

    def _follow_log_file(self, task: BuildTask, log_file: str, duration: int = 30) -> None:
        """后台线程，持续读取日志文件并追加到任务日志中"""
        import time
        last_size = 0
        executor = RemoteExecutor(task.account_alias)
        start_time = time.time()
        
        while time.time() - start_time < duration:
            if task.status not in ["running"] and task.status not in ["pending"]:
                break
            try:
                # 使用 tail 获取新增内容
                if last_size == 0:
                    # 第一次读取整个文件
                    result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
                else:
                    # 读取新增内容
                    result = executor.exec_command(f"tail -c +{last_size + 1} '{log_file}' 2>&1 || true", timeout=5.0)
                
                if result.success and result.stdout:
                    task.append_log(result.stdout)
                
                # 获取文件大小
                size_result = executor.exec_command(f"stat -c %s '{log_file}' 2>/dev/null || echo 0", timeout=3.0)
                if size_result.success and size_result.stdout.strip():
                    try:
                        last_size = int(size_result.stdout.strip())
                    except ValueError:
                        pass
                time.sleep(1)
            except Exception:
                time.sleep(1)

    def _execute_run_task(self, task: BuildTask) -> None:
        import threading
        run_mode = task.config.get("run_mode", "jar")

        if run_mode == "jar":
            log_file = self._run_jar_internal(task)
        elif run_mode == "spring-boot":
            log_file = self._run_spring_boot_internal(task)
        elif run_mode == "exec":
            log_file = self._run_exec_java_internal(task)
        else:
            task.status = "failed"
            task.append_log(f"未知的运行模式: {run_mode}\n")
            return
        
        if log_file and task.status == "running":
            # 先等 3 秒，获取启动日志
            import time
            time.sleep(3)
            
            # 读取初始启动日志
            executor = RemoteExecutor(task.account_alias)
            log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
            if log_result.success and log_result.stdout:
                task.append_log("\n--- 启动日志 ---\n")
                task.append_log(log_result.stdout)
            
            # 启动后台线程持续跟踪日志 30 秒
            t = threading.Thread(
                target=self._follow_log_file,
                args=(task, log_file, 30),
                daemon=True
            )
            t.start()

    def _run_jar_internal(self, task: BuildTask) -> Optional[str]:
        jar_path = task.config.get("jar_path", "")
        jvm_args = task.config.get("jvm_args", "")
        app_args = task.config.get("app_args", "")
        local_path = task.config.get("local_path", "")

        executor = RemoteExecutor(task.account_alias)
        resolved_path = executor.resolve_path(task.project_path)
        if local_path:
            project_folder = os.path.basename(os.path.abspath(local_path))
            resolved_path = resolved_path.rstrip('/') + '/' + project_folder

        full_jar_path = jar_path
        if not jar_path.startswith("/"):
            full_jar_path = f"{resolved_path.rstrip('/')}/{jar_path}"

        java_cmd = f"java {jvm_args} -jar {full_jar_path} {app_args}".strip()
        log_file = f"{resolved_path.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log(f"运行模式: java -jar\n")
        task.append_log(f"JAR 路径: {full_jar_path}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        nohup_cmd = f"mkdir -p {resolved_path} && nohup {java_cmd} > {log_file} 2>&1 & echo $!"

        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.status = "running"
                return log_file
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
                # 读取并显示日志文件内容
                task.append_log("\n--- 启动日志 ---\n")
                log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
                if log_result.success and log_result.stdout:
                    task.append_log(log_result.stdout)
                else:
                    task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
                return None
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")
            # 尝试读取日志文件显示更多错误信息
            task.append_log("\n--- 启动日志 ---\n")
            log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
            if log_result.success and log_result.stdout:
                task.append_log(log_result.stdout)
            else:
                task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
            return None

    def _run_spring_boot_internal(self, task: BuildTask) -> Optional[str]:
        main_class = task.config.get("main_class")
        local_path = task.config.get("local_path", "")
        executor = RemoteExecutor(task.account_alias)
        resolved_path = executor.resolve_path(task.project_path)
        work_dir = self._detect_maven_root(executor, resolved_path)
        if work_dir is None:
            task.status = "failed"
            task.append_log(f"\x1b[31m未找到 pom.xml，请先同步文件\x1b[0m\n")
            return None
        log_file = f"{work_dir.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log("运行模式: mvn spring-boot:run\n")
        if main_class:
            task.append_log(f"主类: {main_class}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        mvn_cmd = f"mkdir -p {work_dir} && cd {work_dir} && mvn spring-boot:run"
        nohup_cmd = f"nohup {mvn_cmd} > {log_file} 2>&1 & echo $!"

        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.status = "running"
                return log_file
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
                # 读取并显示日志文件内容
                task.append_log("\n--- 启动日志 ---\n")
                log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
                if log_result.success and log_result.stdout:
                    task.append_log(log_result.stdout)
                else:
                    task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
                return None
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")
            # 尝试读取日志文件显示更多错误信息
            task.append_log("\n--- 启动日志 ---\n")
            log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
            if log_result.success and log_result.stdout:
                task.append_log(log_result.stdout)
            else:
                task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
            return None

    def _run_exec_java_internal(self, task: BuildTask) -> Optional[str]:
        main_class = task.config.get("main_class", "")
        local_path = task.config.get("local_path", "")
        executor = RemoteExecutor(task.account_alias)
        resolved_path = executor.resolve_path(task.project_path)
        work_dir = self._detect_maven_root(executor, resolved_path)
        if work_dir is None:
            task.status = "failed"
            task.append_log(f"\x1b[31m未找到 pom.xml，请先同步文件\x1b[0m\n")
            return None
        log_file = f"{work_dir.rstrip('/')}/nohup-{task.task_id}.log"

        task.append_log("运行模式: mvn exec:java\n")
        task.append_log(f"主类: {main_class}\n")
        task.append_log(f"日志文件: {log_file}\n\n")

        mvn_cmd = (
            f"mkdir -p {work_dir} && cd {work_dir} "
            f"&& mvn exec:java -Dexec.mainClass=\"{main_class}\""
        )
        nohup_cmd = f"nohup {mvn_cmd} > {log_file} 2>&1 & echo $!"

        result = executor.exec_command(nohup_cmd, timeout=15.0)

        if result.success and result.stdout.strip():
            try:
                pid = int(result.stdout.strip().split("\n")[-1].strip())
                task.pid = pid
                task.append_log(f"进程已启动，PID: {pid}\n")
                task.status = "running"
                return log_file
            except (ValueError, IndexError):
                task.status = "failed"
                task.append_log(f"无法解析 PID: {result.stdout}\n")
                # 读取并显示日志文件内容
                task.append_log("\n--- 启动日志 ---\n")
                log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
                if log_result.success and log_result.stdout:
                    task.append_log(log_result.stdout)
                else:
                    task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
                return None
        else:
            task.status = "failed"
            task.append_log(f"启动失败: {result.stderr}\n")
            # 尝试读取日志文件显示更多错误信息
            task.append_log("\n--- 启动日志 ---\n")
            log_result = executor.exec_command(f"cat '{log_file}' 2>&1 || true", timeout=5.0)
            if log_result.success and log_result.stdout:
                task.append_log(log_result.stdout)
            else:
                task.append_log(f"无法读取日志文件: {log_result.stderr}\n")
            return None

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


    def read_run_log(self, task_id: str, max_lines: int = 500) -> str:
        """读取运行时日志文件"""
        task = self.get_build_task(task_id)
        if task is None:
            return ""
        
        executor = RemoteExecutor(task.account_alias)
        resolved_path = executor.resolve_path(task.project_path)
        
        # 添加项目文件夹名（如果有 local_path）
        local_path = task.config.get("local_path", "")
        if local_path:
            project_folder = os.path.basename(os.path.abspath(local_path))
            resolved_path = resolved_path.rstrip("/") + "/" + project_folder
        
        log_file = f"{resolved_path.rstrip('/')}/nohup-{task_id}.log"
        
        # 使用 tail 命令获取最后几行
        result = executor.exec_command(f"tail -n {max_lines} '{log_file}' 2>&1 || true", timeout=10.0)
        if result.success:
            return result.stdout
        return f"无法读取日志文件: {result.stderr}"


build_service = BuildService()
