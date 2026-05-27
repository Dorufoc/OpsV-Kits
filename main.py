"""
OpsV-Kits - Project Launcher
Usage:
    python main.py                    # Start backend + frontend dev server
    python main.py --backend-only     # Start backend only
    python main.py --frontend-only    # Start frontend dev server only
    python main.py --prod             # Start backend and serve built frontend
    python main.py --no-browser       # Don't auto-open browser
    python main.py --help             # Show this help
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
    """清理端口配置文件"""
    try:
        if _PORT_CONFIG_PATH.exists():
            _PORT_CONFIG_PATH.unlink()
    except Exception:
        pass


def print_banner():
    print(r"""
================================================
 ::::::::   :::::::::    ::::::::   :::     :::
:+:    :+:  :+:    :+:  :+:    :+:  :+:     :+:
+:+    +:+  +:+    +:+  +:+         +:+     +:+
+#+    +:+  +#++:++#+    +#++:++#   +#+     +:+
+#+    +#+  +#+               +#+    +#+   +#+
#+#    #+#  #+#         #+#    #+#    #+#+#+#
 ########   ###          ########       ###
================================================
    """)


def check_python():
    if sys.version_info < (3, 10):
        print(f"  ❌ Python 3.10+ required, current: {sys.version.split()[0]}")
        sys.exit(1)
    print(f"  ✅ Python {sys.version.split()[0]}")


def install_nodejs_windows():
    print("  ⏳ Installing Node.js via winget...")
    result = subprocess.run(
        ["winget", "install", "--id", "OpenJS.NodeJS.LTS", "--accept-package-agreements", "--accept-source-agreements", "--silent"],
        capture_output=True, text=True,
        timeout=300,
    )
    if result.returncode == 0:
        print("  ✅ Node.js installed via winget")
        return True
    print(f"  ⚠ winget install failed (exit={result.returncode}), trying direct download...")
    return False


def install_nodejs_linux():
    print("  ⏳ Installing Node.js via apt...")
    subprocess.run(["sudo", "mkdir", "-p", "/etc/apt/keyrings"], capture_output=True)
    result = subprocess.run(
        "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -",
        shell=True, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print("  ⚠ NodeSource setup failed, trying apt directly...")
        result = subprocess.run(["sudo", "apt", "install", "-y", "nodejs"], capture_output=True, text=True, timeout=300)
    else:
        result = subprocess.run(["sudo", "apt", "install", "-y", "nodejs"], capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        print("  ✅ Node.js installed via apt")
        return True
    print("  ⚠ Linux install failed")
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

    print("  ⚠ Node.js not found, attempting auto-install... (按回车键跳过)", end='', flush=True)

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
        print("  ❌ Auto-install failed. Please install Node.js 18+ manually:")
        print("     Windows: winget install OpenJS.NodeJS.LTS")
        print("     Linux:   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs")
        print("     macOS:   brew install node")
        sys.exit(1)

    node_check = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if node_check.returncode != 0:
        print("  ❌ Node.js still not found after install. Please install manually.")
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

    print(f"  ▶ Backend starting on http://localhost:{actual_port}")
    if reload:
        print(f"    Auto-reload: enabled")
    print()

    proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        stdout=None,
        stderr=None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc, actual_port


def start_frontend_dev(port: int = 3000) -> subprocess.Popen:
    # 读取后端实际端口
    actual_backend_port = _get_backend_port()
    print(f"  ▶ Frontend dev server starting (default port: {port})")
    print(f"    API proxy: http://localhost:{port} -> http://localhost:{actual_backend_port}")
    print()

    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=None,
        stderr=None,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )


def install_dependencies():
    print("  ℹ Checking dependencies... (3s内按回车键跳过)", end='', flush=True)

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
            print("    ✅ Backend dependencies installed")
            pip_install_done = True
        else:
            print("    ⚠ Backend pip install warning (continue anyway)")

    npm_install_done = (FRONTEND_DIR / "node_modules").is_dir()
    if not npm_install_done:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(FRONTEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("    ✅ Frontend dependencies installed")
        else:
            print("    ⚠ Frontend npm install warning (continue anyway)")

    print()


def build_frontend():
    print("  ▶ Building frontend for production...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("    ✅ Frontend built successfully")
    else:
        print("    ❌ Frontend build failed:")
        for line in result.stdout.splitlines()[-5:]:
            print(f"      {line}")
        for line in result.stderr.splitlines()[-5:]:
            print(f"      {line}")
    print()


def delayed_open_browser(url: str, delay: float = 2.0) -> None:
    def _open():
        time.sleep(delay)
        print(f"  Opening browser: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"    ⚠ Could not open browser: {e}")

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def wait_for_shutdown(processes: list[subprocess.Popen]):
    print("  ▶ All services started. Press Ctrl+C to stop all services.\n")

    def signal_handler(sig, frame):
        print("\n  ⏹ Stopping all services...")
        # 清理端口配置文件
        _clear_port_config()
        for proc in processes:
            if proc and proc.poll() is None:
                if sys.platform == "win32":
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("  ✅ All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
            for proc in processes:
                if proc.poll() is not None:
                    print(f"  ⚠ A process exited unexpectedly (code={proc.returncode}).")
                    signal_handler(None, None)
    except KeyboardInterrupt:
        signal_handler(None, None)


def main():
    parser = argparse.ArgumentParser(
        description="OpsV-Kits - Remote File Sync & Build Tool Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python main.py                    # Start backend + frontend
              python main.py --backend-only     # Backend only on port 8000
              python main.py --backend-only --port 8080
              python main.py --frontend-only    # Frontend dev server only
              python main.py --prod             # Backend + built frontend
              python main.py --no-browser       # Don't auto-open browser
              python main.py --skip-deps        # Skip dependency check
        """),
    )
    parser.add_argument("--backend-only", action="store_true", help="Start backend only")
    parser.add_argument("--frontend-only", action="store_true", help="Start frontend dev server only")
    parser.add_argument("--prod", action="store_true", help="Production mode: start backend and serve built frontend")
    parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend dev server port (default: 3000)")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation check")
    parser.add_argument("--no-reload", action="store_true", help="Disable backend auto-reload")
    parser.add_argument("--no-browser", action="store_true", help="Don't automatically open browser on startup")
    parser.add_argument("--browser-delay", type=float, default=2.0, help="Seconds to wait before opening browser (default: 2.0)")
    parser.add_argument("--skip-node-check", action="store_true", help="Skip Node.js version check")

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
        frontend_url = f"http://localhost:{args.frontend_port}"
    elif args.prod and start_frontend_svc:
        dist_dir = FRONTEND_DIR / "dist"
        if not dist_dir.is_dir():
            build_frontend()
        print(f"  ▶ Frontend static file served by backend on http://localhost:{actual_backend_port}")
        print()
        frontend_url = backend_url

    if not args.no_browser:
        if frontend_url:
            delayed_open_browser(frontend_url, delay=args.browser_delay)
        elif backend_url:
            delayed_open_browser(backend_url, delay=args.browser_delay)

    if processes:
        wait_for_shutdown(processes)
    else:
        print("  Nothing to start. Use --help for usage.")


if __name__ == "__main__":
    main()
