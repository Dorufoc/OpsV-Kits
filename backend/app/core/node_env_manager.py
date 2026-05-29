from __future__ import annotations

import re
from typing import Callable, Optional

from app.core.remote_executor import CommandResult, RemoteExecutor, RemoteExecutorError


_NODE_VERSION_PATTERN = re.compile(r"v?(\d+(?:\.\d+)*)" )
_NPM_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)*)")


class NodeEnvManagerError(Exception):
    pass


class NodeEnvManager:
    def __init__(self, account_alias: str):
        self._account_alias = account_alias
        self._executor = RemoteExecutor(account_alias)

    def check_node(self, account_alias: str | None = None) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        node_result = {"installed": False, "version": "", "npm_installed": False, "npm_version": ""}

        node_check = executor.exec_command("node --version 2>&1")
        if node_check.success:
            match = _NODE_VERSION_PATTERN.search(node_check.stdout)
            if match:
                node_result["installed"] = True
                node_result["version"] = match.group(1)
        else:
            node_check = executor.exec_command("node --version 2>&1 || true")
            match = _NODE_VERSION_PATTERN.search(node_check.stdout)
            if match:
                node_result["installed"] = True
                node_result["version"] = match.group(1)

        npm_check = executor.exec_command("npm --version 2>&1")
        if npm_check.success:
            match = _NPM_VERSION_PATTERN.search(npm_check.stdout)
            if match:
                node_result["npm_installed"] = True
                node_result["npm_version"] = match.group(1)
        else:
            npm_check = executor.exec_command("npm --version 2>&1 || true")
            match = _NPM_VERSION_PATTERN.search(npm_check.stdout)
            if match:
                node_result["npm_installed"] = True
                node_result["npm_version"] = match.group(1)

        return node_result

    def _detect_package_manager(self, executor: RemoteExecutor) -> str:
        os_release = executor.exec_command("cat /etc/os-release 2>&1 || true")
        if os_release.success and os_release.stdout:
            stdout_lower = os_release.stdout.lower()
            if any(dist in stdout_lower for dist in ("debian", "ubuntu", "deepin", "uos", "kali")):
                return "apt"
            if any(dist in stdout_lower for dist in ("fedora", "centos", "rhel", "rocky", "almalinux", "oracle")):
                if executor.exec_command("which dnf 2>/dev/null").success:
                    return "dnf"
                return "yum"
        if executor.exec_command("which apt 2>/dev/null").success:
            return "apt"
        if executor.exec_command("which dnf 2>/dev/null").success:
            return "dnf"
        if executor.exec_command("which yum 2>/dev/null").success:
            return "yum"
        raise NodeEnvManagerError("无法检测系统包管理器")

    def install_node(
        self,
        account_alias: str | None = None,
        version: str = "20",
        callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        def _emit(msg: str) -> None:
            if callback:
                callback(msg)

        _emit(f"正在检测系统包管理器...")
        pkg_manager = self._detect_package_manager(executor)
        _emit(f"检测到包管理器: {pkg_manager}")

        _emit(f"开始安装 Node.js {version} LTS...")

        if pkg_manager in ("dnf", "yum"):
            setup_script = f"https://rpm.nodesource.com/setup_{version}.x"
            install_cmd = (
                f"curl -fsSL {setup_script} | bash - && "
                f"{pkg_manager} install -y nodejs"
            )
        elif pkg_manager == "apt":
            setup_script = f"https://deb.nodesource.com/setup_{version}.x"
            install_cmd = (
                f"curl -fsSL {setup_script} | bash - && "
                f"apt-get install -y nodejs"
            )
        else:
            raise NodeEnvManagerError(f"不支持的包管理器: {pkg_manager}")

        exit_code = executor.exec_command_stream(
            install_cmd,
            output_callback=_emit,
            timeout=300.0,
        )

        if exit_code != 0:
            _emit(f"NodeSource 安装失败，尝试系统仓库...")
            if pkg_manager in ("dnf", "yum"):
                fallback_cmd = f"{pkg_manager} install -y nodejs npm"
            else:
                fallback_cmd = "apt-get install -y nodejs npm"
            exit_code = executor.exec_command_stream(
                fallback_cmd,
                output_callback=_emit,
                timeout=180.0,
            )

        _emit("验证 Node.js 安装...")
        verify = self.check_node(account_alias or self._account_alias)
        installed = verify["installed"] and verify["npm_installed"]

        return {
            "component": "nodejs",
            "version": version,
            "installed": installed,
            "node_version": verify["version"],
            "npm_version": verify["npm_version"],
            "message": f"Node.js {verify['version']} (npm {verify['npm_version']}) 安装{'成功' if installed else '失败'}",
        }
