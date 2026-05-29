from __future__ import annotations

import re
from typing import Optional

from app.core.remote_executor import RemoteExecutor, RemoteExecutorError


_NGINX_VERSION_PATTERN = re.compile(r"nginx/(\d+(?:\.\d+)*)" )
_PORT_IN_USE_PATTERN = re.compile(r"[:\s](\d+)\s+")


class NginxConfigManagerError(Exception):
    pass


class NginxConfigManager:
    def __init__(self, account_alias: str):
        self._account_alias = account_alias
        self._executor = RemoteExecutor(account_alias)

    def check_nginx(self, account_alias: str | None = None) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        nginx_result = {"installed": False, "version": "", "running": False}

        which_check = executor.exec_command("which nginx 2>/dev/null")
        if not which_check.success:
            which_check = executor.exec_command("nginx -v 2>&1 || true")
            if "nginx" not in which_check.stdout.lower():
                return nginx_result

        version_check = executor.exec_command("nginx -v 2>&1")
        if version_check.success or version_check.stdout:
            match = _NGINX_VERSION_PATTERN.search(version_check.stdout)
            if match:
                nginx_result["installed"] = True
                nginx_result["version"] = match.group(1)

        ps_check = executor.exec_command("ps aux | grep '[n]ginx' 2>/dev/null || true")
        if ps_check.success and ps_check.stdout.strip():
            nginx_result["running"] = True

        return nginx_result

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
        raise NginxConfigManagerError("无法检测系统包管理器")

    def install_nginx(self, account_alias: str | None = None) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        pkg_manager = self._detect_package_manager(executor)

        if pkg_manager in ("dnf", "yum"):
            install_cmd = f"{pkg_manager} install -y nginx"
        elif pkg_manager == "apt":
            install_cmd = "apt-get update && apt-get install -y nginx"
        else:
            raise NginxConfigManagerError(f"不支持的包管理器: {pkg_manager}")

        result = executor.exec_command(install_cmd, timeout=180.0)
        if not result.success:
            sudo_result = executor.exec_command(f"sudo {install_cmd}", timeout=180.0)
            if not sudo_result.success:
                raise NginxConfigManagerError(
                    f"Nginx 安装失败: {sudo_result.stderr[:200]}"
                )

        verify = self.check_nginx(account_alias or self._account_alias)
        return {
            "component": "nginx",
            "installed": verify["installed"],
            "version": verify["version"],
            "message": f"Nginx {verify['version']} 安装{'成功' if verify['installed'] else '失败'}",
        }

    def check_port_conflict(self, port: int, account_alias: str | None = None) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        port_result = {"conflict": False, "processes": []}

        netstat_check = executor.exec_command(
            f"netstat -tlnp 2>/dev/null | grep ':{port} ' || true"
        )
        if netstat_check.success and netstat_check.stdout.strip():
            port_result["conflict"] = True
            for line in netstat_check.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    port_result["processes"].append(line)

        ss_check = executor.exec_command(
            f"ss -tlnp 2>/dev/null | grep ':{port} ' || true"
        )
        if ss_check.success and ss_check.stdout.strip():
            for line in ss_check.stdout.strip().split("\n"):
                line = line.strip()
                if line and line not in port_result["processes"]:
                    port_result["conflict"] = True
                    port_result["processes"].append(line)

        lsof_check = executor.exec_command(
            f"lsof -i :{port} 2>/dev/null || true"
        )
        if lsof_check.success and lsof_check.stdout.strip():
            for line in lsof_check.stdout.strip().split("\n"):
                line = line.strip()
                if line and line not in port_result["processes"]:
                    port_result["conflict"] = True
                    port_result["processes"].append(line)

        return port_result

    def generate_config(
        self,
        project_alias: str,
        port: int,
        server_name: str,
        root_path: str,
        account_alias: str | None = None,
    ) -> str:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        resolved_root = executor.resolve_path(root_path)
        config_path = f"/etc/nginx/conf.d/opsv-vite-{project_alias}.conf"

        config_content = (
            f"server {{\n"
            f"    listen {port};\n"
            f"    server_name {server_name};\n"
            f"\n"
            f"    root {resolved_root};\n"
            f"    index index.html;\n"
            f"\n"
            f"    location / {{\n"
            f"        try_files $uri $uri/ /index.html;\n"
            f"    }}\n"
            f"\n"
            f"    error_page 500 502 503 504 /50x.html;\n"
            f"    location = /50x.html {{\n"
            f"        root /usr/share/nginx/html;\n"
            f"    }}\n"
            f"}}\n"
        )

        escaped = config_content.replace("'", "'\\''")
        write_cmd = f"cat > '{config_path}' << 'EOF'\n{config_content}\nEOF"
        result = executor.exec_command(write_cmd, timeout=15.0)
        if not result.success:
            sudo_result = executor.exec_command(f"sudo bash -c '{write_cmd}'", timeout=15.0)
            if not sudo_result.success:
                raise NginxConfigManagerError(
                    f"无法写入 Nginx 配置: {sudo_result.stderr[:200]}"
                )

        return config_path

    def reload_nginx(self, account_alias: str | None = None) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        test_result = executor.exec_command("nginx -t 2>&1")
        if not test_result.success:
            sudo_test = executor.exec_command("sudo nginx -t 2>&1")
            if not sudo_test.success:
                return {
                    "success": False,
                    "message": f"Nginx 配置测试失败: {sudo_test.stderr[:200]}",
                }

        reload_result = executor.exec_command("nginx -s reload 2>&1")
        if not reload_result.success:
            sudo_reload = executor.exec_command("sudo nginx -s reload 2>&1")
            if not sudo_reload.success:
                return {
                    "success": False,
                    "message": f"Nginx reload 失败: {sudo_reload.stderr[:200]}",
                }

        return {
            "success": True,
            "message": "Nginx 配置已重新加载",
        }

    def remove_config(
        self, project_alias: str, account_alias: str | None = None
    ) -> dict:
        executor = self._executor
        if account_alias and account_alias != self._account_alias:
            executor = RemoteExecutor(account_alias)

        config_path = f"/etc/nginx/conf.d/opsv-vite-{project_alias}.conf"
        result = executor.exec_command(f"rm -f '{config_path}'")
        if not result.success:
            executor.exec_command(f"sudo rm -f '{config_path}'")

        reload = self.reload_nginx(account_alias or self._account_alias)
        return {
            "success": reload["success"],
            "message": f"配置已删除，{'并重载 Nginx' if reload['success'] else '但重载失败'}",
        }
