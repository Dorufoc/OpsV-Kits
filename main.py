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
import os
import signal
import subprocess
import sys
import textwrap
import threading
import time
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def print_banner():
    print(r"""


 ::::::::   :::::::::    ::::::::   :::     :::
:+:    :+:  :+:    :+:  :+:    :+:  :+:     :+:
+:+    +:+  +:+    +:+  +:+         +:+     +:+
+#+    +:+  +#++:++#+    +#++:++#   +#+     +:+
+#+    +#+  +#+               +#+    +#+   +#+
#+#    #+#  #+#         #+#    #+#    #+#+#+#
 ########   ###          ########       ###


    """)


def start_backend(port: int = 8000, reload: bool = True, log_level: str = "info") -> subprocess.Popen:
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", log_level,
    ]
    if reload:
        backend_cmd.append("--reload")

    print(f"  \u25b6 Backend starting on http://localhost:{port}")
    if reload:
        print(f"    Auto-reload: enabled")
    print()

    return subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR),
        stdout=None,
        stderr=None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )


def start_frontend_dev(port: int = 3000) -> subprocess.Popen:
    print(f"  \u25b6 Frontend dev server starting on http://localhost:{port}")
    print(f"    API proxy: http://localhost:{port} -> http://localhost:8000")
    print()

    return subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(port)],
        cwd=str(FRONTEND_DIR),
        stdout=None,
        stderr=None,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )


def install_dependencies():
    print("  \u2139\ufe0f Checking dependencies...")

    pip_install_done = False
    if not pip_install_done:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=str(BACKEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("    \u2705 Backend dependencies installed")
            pip_install_done = True
        else:
            print(f"    \u26a0\ufe0f Backend pip install warning (continue anyway)")

    npm_install_done = (FRONTEND_DIR / "node_modules").is_dir()
    if not npm_install_done:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(FRONTEND_DIR),
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("    \u2705 Frontend dependencies installed")
        else:
            print(f"    \u26a0\ufe0f Frontend npm install warning (continue anyway)")

    print()


def build_frontend():
    print("  \u25b6 Building frontend for production...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("    \u2705 Frontend built successfully")
    else:
        print(f"    \u274c Frontend build failed:")
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
            print(f"    \u26a0\ufe0f Could not open browser: {e}")

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def wait_for_shutdown(processes: list[subprocess.Popen]):
    print("  \u25b6 All services started. Press Ctrl+C to stop all services.\n")

    def signal_handler(sig, frame):
        print("\n  \u23f9 Stopping all services...")
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
        print("  \u2705 All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
            for proc in processes:
                if proc.poll() is not None:
                    print(f"  \u26a0\ufe0f A process exited unexpectedly (code={proc.returncode}).")
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

    args = parser.parse_args()

    print_banner()

    if not args.skip_deps:
        install_dependencies()

    processes = []

    start_backend_svc = not args.frontend_only
    start_frontend_svc = not args.backend_only

    frontend_url = None
    backend_url = None

    if start_backend_svc:
        proc = start_backend(
            port=args.port,
            reload=not args.no_reload and not args.prod,
            log_level="warning" if args.prod else "info",
        )
        processes.append(proc)
        backend_url = f"http://localhost:{args.port}"

    if start_frontend_svc and not args.prod:
        proc = start_frontend_dev(port=args.frontend_port)
        processes.append(proc)
        frontend_url = f"http://localhost:{args.frontend_port}"
    elif args.prod and start_frontend_svc:
        dist_dir = FRONTEND_DIR / "dist"
        if not dist_dir.is_dir():
            build_frontend()

        print(f"  \u25b6 Frontend static file served by backend on http://localhost:{args.port}")
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
