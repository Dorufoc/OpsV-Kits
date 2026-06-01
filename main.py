"""
OpsV-Kits - 项目启动器
用法:
    python main.py                    # 启动后端 + 前端开发服务器
    python main.py --backend-only     # 仅启动后端
    python main.py --frontend-only    # 仅启动前端开发服务器
    python main.py --prod             # 启动后端并服务构建后的前端
    python main.py --no-browser       # 不自动打开浏览器
    python main.py --help             # 显示帮助信息
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
import threading
import time
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path


def find_available_port(start_port: int, max_attempts: int = 10) -> int | None:
    """查找可用端口，从 start_port 开始尝试，最多尝试 max_attempts 个端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return None


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 用于前后端端口通信的临时配置文件
_PORT_CONFIG_PATH = PROJECT_ROOT / ".port_config.json"
_STARTUP_PROGRESS_FILE = PROJECT_ROOT / ".startup_progress.json"

# 后端进程引用，供等待循环检测进程状态
_backend_process: subprocess.Popen | None = None

def _save_backend_port(port: int) -> None:
    """保存后端实际端口到配置文件，供前端读取"""
    try:
        _PORT_CONFIG_PATH.write_text(json.dumps({"backend_port": port}), encoding="utf-8")
    except Exception:
        pass

def _get_backend_port() -> int:
    """从配置文件读取后端实际端口"""
    try:
        if _PORT_CONFIG_PATH.exists():
            data = json.loads(_PORT_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("backend_port", 8000)
    except Exception:
        pass
    return 8000

def _clear_port_config() -> None:
    """清理端口配置和启动进度文件"""
    try:
        if _PORT_CONFIG_PATH.exists():
            _PORT_CONFIG_PATH.unlink()
    except Exception:
        pass
    try:
        if _STARTUP_PROGRESS_FILE.exists():
            _STARTUP_PROGRESS_FILE.unlink()
    except Exception:
        pass


def print_banner():
    print(r"""
<-===============================================->
   ::::::::   :::::::::    ::::::::   :::     ::: 
  :+:    :+:  :+:    :+:  :+:    :+:  :+:     :+: 
  +:+    +:+  +:+    +:+  +:+         +:+     +:+ 
  +#+    +:+  +#++:++#+    +#++:++#   +#+     +:+ 
  +#+    +#+  +#+               +#+    +#+   +#+  
  #+#    #+#  #+#         #+#    #+#    #+#+#+#   
   ########   ###          ########       ###     
<-===============================================->
    """)


def check_python():
    if sys.version_info < (3, 10):
        print(f"  ❌ 需要 Python 3.10+，当前版本: {sys.version.split()[0]}")
        sys.exit(1)
    print(f"  ✅ Python {sys.version.split()[0]}")


def install_nodejs_windows():
    print(f"  ⏳ 正在通过 winget 安装 Node.js...")
    result = subprocess.run(
        ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "--accept-package-agreements", "--accept-source-agreements", "--silent"],
        capture_output=True, text=True,
        timeout=300,
    )
    if result.returncode == 0:
        print("  ✅ Node.js 已通过 winget 安装")
        return True
    print(f"  ⚠ winget 安装失败 (退出码={result.returncode})，尝试直接下载...")
    return False


def install_nodejs_linux():
    print("  ⏳ 正在通过 apt 安装 Node.js...")
    subprocess.run(["sudo", "mkdir", "-p", "/etc/apt/keyrings"], capture_output=True)
    result = subprocess.run(
        "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -",
        shell=True, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print("  ⚠ NodeSource 设置失败，尝试直接使用 apt...")
        result = subprocess.run(["sudo", "apt", "install", "-y", "nodejs"], capture_output=True, text=True, timeout=300)
    else:
        result = subprocess.run(["sudo", "apt", "install", "-y", "nodejs"], capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        print("  ✅ Node.js 已通过 apt 安装")
        return True
    print("  ⚠ Linux 安装失败")
    return False


def _check_skip_key(timeout: float = 3.0) -> bool:
    """检查用户是否在指定时间内按了回车键，返回True表示跳过"""
    if sys.platform == "win32":
        import msvcrt
        import time
        start = time.time()
        while time.time() - start < timeout:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\r' or key == b'\n':
                    return True
            time.sleep(0.1)
    else:
        import select
        import tty
        import termios
        import time
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            start = time.time()
            while time.time() - start < timeout:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key == '\n' or key == '\r':
                        return True
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return False


def ensure_nodejs():
    try:
        node_check = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if node_check.returncode == 0:
            print(f"  ✅ Node.js {node_check.stdout.strip()}")
            return
    except FileNotFoundError:
        pass

    print("  ⚠ 未找到 Node.js，尝试自动安装... (按回车键跳过)", end='', flush=True)

    if _check_skip_key(timeout=3.0):
        print("\r  ⏭️  已跳过 Node.js 自动安装")
        return

    print()
    if sys.platform == "win32":
        ok = install_nodejs_windows()
    elif sys.platform == "linux":
        ok = install_nodejs_linux()
    else:
        ok = False

    if not ok:
        print("  ❌ 自动安装失败。请手动安装 Node.js 18+：")
        print("     Windows: winget install OpenJS.NodeJS.LTS")
        print("     Linux:   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs")
        print("     macOS:   brew install node")
        sys.exit(1)

    node_check = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if node_check.returncode != 0:
        print("  ❌ 安装后仍未找到 Node.js。请手动安装。")
        sys.exit(1)
    print(f"  ✅ Node.js {node_check.stdout.strip()}")


def start_backend(port: int = 8000, reload: bool = True, log_level: str = "info") -> tuple[subprocess.Popen, int]:
    # 检查端口是否可用，如果被占用则自动寻找可用端口
    actual_port = find_available_port(port)
    if actual_port is None:
        print(f"  ❌ 无法找到可用端口（尝试了 {port} 到 {port + 9}）")
        sys.exit(1)

    if actual_port != port:
        print(f"  ⚠ 端口 {port} 已被占用，自动切换到端口 {actual_port}")

    # 保存实际端口到配置文件，供前端读取
    _save_backend_port(actual_port)

    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(actual_port),
        "--log-level", log_level,
    ]
    if reload:
        backend_cmd.append("--reload")

    print(f"  ▶ 后端服务启动中 http://localhost:{actual_port}")
    if reload:
        print(f"    自动重载: 已启用")
    print()

    global _backend_process
    proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        stdout=None,
        stderr=None,
    )
    _backend_process = proc
    return proc, actual_port


def _save_frontend_port(port: int) -> None:
    """保存前端实际端口到配置文件"""
    try:
        data = {}
        if _PORT_CONFIG_PATH.exists():
            data = json.loads(_PORT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["frontend_port"] = port
        _PORT_CONFIG_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def _get_frontend_port() -> int:
    """从配置文件读取前端实际端口"""
    try:
        if _PORT_CONFIG_PATH.exists():
            data = json.loads(_PORT_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("frontend_port", 3000)
    except Exception:
        pass
    return 3000

def start_frontend_dev(port: int = 3000) -> subprocess.Popen:
    actual_backend_port = _get_backend_port()
    print(f"  ▶ 前端开发服务器启动中（默认端口: {port}）")
    print(f"    API 代理: http://localhost:{port} -> http://localhost:{actual_backend_port}")
    print()

    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )

    def _parse_vite_port():
        """从 Vite 输出中解析实际端口并保存"""
        import re as _re
        if not proc.stdout:
            return
        try:
            for line in iter(proc.stdout.readline, b''):
                text = line.decode("utf-8", errors="replace").strip()
                print(text)
                match = _re.search(r"Local:\s+http://localhost:(\d+)", text)
                if match:
                    actual_port = int(match.group(1))
                    _save_frontend_port(actual_port)
                    if actual_port != port:
                        print(f"  ⚠ 端口 {port} 已被占用，前端实际运行在端口 {actual_port}")
                    break
        except Exception:
            pass

    thread = threading.Thread(target=_parse_vite_port, daemon=True)
    thread.start()
    return proc


def install_dependencies():
    print("  ℹ 正在检查依赖... (3秒内按回车键跳过)", end='', flush=True)

    if _check_skip_key(timeout=3.0):
        print("\r  ⏭️  已跳过依赖检查")
        return

    print()

    pip_install_done = False
    if not pip_install_done:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=str(BACKEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("    ✅ 后端依赖已安装")
            pip_install_done = True
        else:
            print("    ⚠ 后端 pip 安装警告（继续执行）")

    npm_install_done = (FRONTEND_DIR / "node_modules").is_dir()
    if not npm_install_done:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(FRONTEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("    ✅ 前端依赖已安装")
        else:
            print("    ⚠ 前端 npm 安装警告（继续执行）")

    print()


def build_frontend():
    print("  ▶ 正在构建前端生产版本...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("    ✅ 前端构建成功")
    else:
        print("    ❌ 前端构建失败:")
        for line in result.stdout.splitlines()[-5:]:
            print(f"      {line}")
        for line in result.stderr.splitlines()[-5:]:
            print(f"      {line}")
    print()


def _read_startup_progress() -> dict | None:
    """读取后端启动进度"""
    try:
        if _STARTUP_PROGRESS_FILE.exists():
            return json.loads(_STARTUP_PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None

def _draw_progress_bar(percent: int, width: int = 20) -> str:
    """绘制文本进度条"""
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return bar

def wait_for_backend_ready(base_url: str, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """轮询后端健康检查接口，等待后端完全就绪，同时显示进度条"""
    health_url = f"{base_url}/api/health"
    start = time.time()
    last_message = ""
    last_percent = 0
    printed = False

    while time.time() - start < timeout:
        # 检测后端进程是否还活着
        global _backend_process
        if _backend_process is not None:
            ret = _backend_process.poll()
            if ret is not None:
                if printed:
                    print()
                print(f"  ❌ 后端进程已退出（退出码={ret}）")
                print(f"     请检查 backend/app/main.py 中是否有导入错误")
                return False
            pid = _backend_process.pid

        try:
            req = urllib.request.Request(health_url, method='GET')
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    if printed:
                        print()
                    print(f"  ✅ 后端服务已就绪 ({time.time() - start:.1f}s)")
                    return True
        except (urllib.error.URLError, OSError, Exception):
            pass

        elapsed = time.time() - start
        progress = _read_startup_progress()
        if progress:
            if progress.get("done", False):
                if printed:
                    print("\033[K", end="\r")
                print(f"  ⏳ 后端模块已加载完毕，等待服务就绪... ({elapsed:.0f}s)", end="\r", flush=True)
                printed = True
            else:
                step = progress.get("step", 0)
                total = progress.get("total", 1)
                message = progress.get("message", "正在启动...")
                percent = min(int(step * 100 / total), 99)
                if percent == 0 and elapsed < 1:
                    bar = _draw_progress_bar(0)
                    line = f"  ⏳ 后端启动中 PID={pid} [{bar}] 0% - {message}"
                else:
                    bar = _draw_progress_bar(percent)
                    line = f"  ⏳ 后端启动中 PID={pid} [{bar}] {percent}% - {message}"
                if line != last_message or percent != last_percent:
                    if printed:
                        print("\033[K", end="\r")
                    print(line, end="\r", flush=True)
                    last_message = line
                    last_percent = percent
                    printed = True
        elif elapsed > 0.5:
            if printed:
                print("\033[K", end="\r")
            line = f"  ⏳ 正在等待后端进程启动... PID={pid} ({elapsed:.0f}s)"
            if line != last_message:
                print(line, end="\r", flush=True)
                last_message = line
                printed = True
        time.sleep(interval)

    if printed:
        print()
    if _backend_process is not None and _backend_process.poll() is None:
        print(f"  ⚠ 后端进程 PID={_backend_process.pid} 仍在运行但健康检查超时")
    return False


def delayed_open_browser(url: str, backend_url: str | None = None, delay: float = 2.0) -> None:
    def _open():
        if backend_url:
            ready = wait_for_backend_ready(backend_url)
        else:
            time.sleep(delay)
        print(f"  正在打开浏览器: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"    ⚠ 无法打开浏览器: {e}")

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def wait_for_shutdown(processes: list[subprocess.Popen]):
    print("  ▶ 所有服务已启动。按 Ctrl+C 停止所有服务。\n")

    def signal_handler(sig, frame):
        print("\n  ⏹ 正在停止所有服务...")
        _clear_port_config()
        for proc in processes:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except Exception:
                    pass
        print("  ✅ 所有服务已停止。")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
            for proc in processes:
                if proc.poll() is not None:
                    print(f"  ⚠ 某个进程意外退出（退出码={proc.returncode}）。")
                    signal_handler(None, None)
    except KeyboardInterrupt:
        signal_handler(None, None)


def main():
    parser = argparse.ArgumentParser(
        description="OpsV-Kits - 远程文件同步与构建工具启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            示例:
              python main.py                    # 启动后端 + 前端
              python main.py --backend-only     # 仅启动后端（端口 8000）
              python main.py --backend-only --port 8080
              python main.py --frontend-only    # 仅启动前端开发服务器
              python main.py --prod             # 后端 + 构建后的前端
              python main.py --no-browser       # 不自动打开浏览器
              python main.py --skip-deps        # 跳过依赖检查
        """),
    )
    parser.add_argument("--backend-only", action="store_true", help="仅启动后端")
    parser.add_argument("--frontend-only", action="store_true", help="仅启动前端开发服务器")
    parser.add_argument("--prod", action="store_true", help="生产模式：启动后端并服务构建后的前端")
    parser.add_argument("--port", type=int, default=8000, help="后端端口（默认: 8000）")
    parser.add_argument("--frontend-port", type=int, default=3000, help="前端开发服务器端口（默认: 3000）")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖安装检查")
    parser.add_argument("--no-reload", action="store_true", help="禁用后端自动重载")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    parser.add_argument("--browser-delay", type=float, default=2.0, help="打开浏览器前的等待秒数（默认: 2.0）")
    parser.add_argument("--skip-node-check", action="store_true", help="跳过 Node.js 版本检查")

    args = parser.parse_args()

    print_banner()

    check_python()

    if not args.skip_node_check:
        ensure_nodejs()

    if not args.skip_deps:
        install_dependencies()

    processes = []

    start_backend_svc = not args.frontend_only
    start_frontend_svc = not args.backend_only

    frontend_url = None
    backend_url = None

    actual_backend_port = args.port
    if start_backend_svc:
        proc, actual_backend_port = start_backend(
            port=args.port,
            reload=not args.no_reload and not args.prod,
            log_level="warning" if args.prod else "info",
        )
        processes.append(proc)
        backend_url = f"http://localhost:{actual_backend_port}"

    if start_frontend_svc and not args.prod:
        proc = start_frontend_dev(port=args.frontend_port)
        processes.append(proc)
        time.sleep(3)
        actual_frontend_port = _get_frontend_port()
        frontend_url = f"http://localhost:{actual_frontend_port}"
    elif args.prod and start_frontend_svc:
        dist_dir = FRONTEND_DIR / "dist"
        if not dist_dir.is_dir():
            build_frontend()
        print(f"  ▶ 前端静态文件由后端服务提供 http://localhost:{actual_backend_port}")
        print()
        frontend_url = backend_url

    if not args.no_browser:
        if frontend_url:
            delayed_open_browser(frontend_url, backend_url=backend_url, delay=args.browser_delay)
        elif backend_url:
            delayed_open_browser(backend_url, backend_url=backend_url, delay=args.browser_delay)

    if processes:
        wait_for_shutdown(processes)
    else:
        print("  没有需要启动的服务。使用 --help 查看用法。")


if __name__ == "__main__":
    main()
