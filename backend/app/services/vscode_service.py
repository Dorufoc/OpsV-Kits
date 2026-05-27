"""
Web VSCode (code-server) 服务管理模块
负责 code-server 的启动、停止、状态监控
"""

from __future__ import annotations

import asyncio
import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.settings_service import settings_service


@dataclass
class VSCodeStatus:
    """VSCode 服务状态"""
    running: bool
    port: int
    pid: Optional[int] = None
    url: Optional[str] = None
    error: Optional[str] = None


class VSCodeService:
    """
    Web VSCode 服务管理器
    封装 code-server 的生命周期管理
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._port: int = 8082  # 默认端口
        self._work_dir: Path = Path.cwd()
        self._config_dir: Optional[Path] = None
        self._auth_token: Optional[str] = None
        self._shutdown_event = asyncio.Event()

    @property
    def port(self) -> int:
        return self._port

    def _find_code_server(self) -> Optional[str]:
        """查找系统上的 code-server 可执行文件"""
        return shutil.which("code-server")

    def _install_code_server(self) -> bool:
        """
        尝试自动安装 code-server
        支持 Windows (通过 npm) 和 Linux (通过官方脚本)
        """
        system = platform.system().lower()

        try:
            if system == "windows":
                # Windows: 使用 npm 安装
                result = subprocess.run(
                    ["npm", "install", "-g", "code-server"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return result.returncode == 0
            else:
                # Linux/macOS: 使用官方安装脚本
                install_script = "curl -fsSL https://code-server.dev/install.sh | sh"
                result = subprocess.run(
                    install_script,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return result.returncode == 0
        except Exception:
            return False

    def _ensure_code_server(self) -> Optional[str]:
        """确保 code-server 可用，如不存在则尝试安装"""
        executable = self._find_code_server()
        if executable:
            return executable

        # 尝试自动安装
        if self._install_code_server():
            return self._find_code_server()

        return None

    def _generate_auth_token(self) -> str:
        """生成随机认证令牌"""
        import secrets
        return secrets.token_urlsafe(32)

    def _create_config(self) -> Path:
        """创建 code-server 配置文件"""
        if self._config_dir is None:
            self._config_dir = Path(tempfile.mkdtemp(prefix="vscode_config_"))

        config_path = self._config_dir / "config.yaml"
        self._auth_token = self._generate_auth_token()

        config_content = f"""bind-addr: 127.0.0.1:{self._port}
auth: password
password: {self._auth_token}
cert: false
"""
        config_path.write_text(config_content, encoding="utf-8")
        return config_path

    def start(
        self,
        port: Optional[int] = None,
        work_dir: Optional[Path] = None,
        enable_auth: bool = True,
    ) -> VSCodeStatus:
        """
        启动 Web VSCode 服务

        Args:
            port: 服务端口，默认 8082
            work_dir: 工作目录，默认当前目录
            enable_auth: 是否启用认证

        Returns:
            VSCodeStatus: 服务状态
        """
        if self._process is not None and self._process.poll() is None:
            return VSCodeStatus(
                running=True,
                port=self._port,
                pid=self._process.pid,
                url=f"http://127.0.0.1:{self._port}",
            )

        # 查找 code-server
        executable = self._ensure_code_server()
        if not executable:
            return VSCodeStatus(
                running=False,
                port=port or self._port,
                error="code-server not found. Please install it:\n"
                      "  Windows: npm install -g code-server\n"
                      "  Linux/macOS: curl -fsSL https://code-server.dev/install.sh | sh",
            )

        # 设置端口和工作目录
        if port:
            self._port = port
        if work_dir:
            self._work_dir = Path(work_dir)

        # 创建配置
        config_path = self._create_config()

        # 构建启动命令
        cmd = [
            executable,
            "--config", str(config_path),
            "--port", str(self._port),
            "--host", "127.0.0.1",
            "--disable-telemetry",
            "--disable-update-check",
        ]

        if not enable_auth:
            cmd.append("--auth")
            cmd.append("none")

        # 添加工作目录
        cmd.append(str(self._work_dir))

        try:
            # 启动进程
            if sys.platform == "win32":
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    cwd=str(self._work_dir),
                )
            else:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,
                    cwd=str(self._work_dir),
                )

            # 等待服务启动
            time.sleep(2)

            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode("utf-8", errors="ignore") if self._process.stderr else ""
                return VSCodeStatus(
                    running=False,
                    port=self._port,
                    error=f"code-server failed to start: {stderr}",
                )

            return VSCodeStatus(
                running=True,
                port=self._port,
                pid=self._process.pid,
                url=f"http://127.0.0.1:{self._port}",
            )

        except Exception as e:
            return VSCodeStatus(
                running=False,
                port=self._port,
                error=f"Failed to start code-server: {str(e)}",
            )

    def stop(self) -> VSCodeStatus:
        """停止 Web VSCode 服务"""
        if self._process is None:
            return VSCodeStatus(
                running=False,
                port=self._port,
            )

        try:
            if sys.platform == "win32":
                self._process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)

            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        except Exception:
            pass
        finally:
            self._process = None

        # 清理临时配置
        if self._config_dir and self._config_dir.exists():
            import shutil
            shutil.rmtree(self._config_dir, ignore_errors=True)
            self._config_dir = None

        return VSCodeStatus(
            running=False,
            port=self._port,
        )

    def get_status(self) -> VSCodeStatus:
        """获取服务状态"""
        if self._process is None:
            return VSCodeStatus(
                running=False,
                port=self._port,
            )

        poll_result = self._process.poll()
        if poll_result is None:
            return VSCodeStatus(
                running=True,
                port=self._port,
                pid=self._process.pid,
                url=f"http://127.0.0.1:{self._port}",
            )
        else:
            self._process = None
            return VSCodeStatus(
                running=False,
                port=self._port,
                error=f"Process exited with code {poll_result}",
            )

    def restart(
        self,
        port: Optional[int] = None,
        work_dir: Optional[Path] = None,
    ) -> VSCodeStatus:
        """重启服务"""
        self.stop()
        time.sleep(1)
        return self.start(port=port, work_dir=work_dir)

    def get_auth_token(self) -> Optional[str]:
        """获取认证令牌"""
        return self._auth_token

    def shutdown(self):
        """关闭服务（用于应用退出时）"""
        self.stop()


# 全局服务实例
vscode_service = VSCodeService()

# 注册退出清理
atexit.register(vscode_service.shutdown)
