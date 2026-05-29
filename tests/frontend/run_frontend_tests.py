"""
前端测试运行脚本 - 自动启动前后端服务并执行Playwright测试
用法: python tests/frontend/run_frontend_tests.py
"""
import subprocess
import sys
import os
import time
import signal
import socket
import urllib.request


def wait_for_port(port, timeout=60):
    """等待指定端口可用"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def wait_for_http(url, timeout=60):
    """等待HTTP服务可用"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.urlopen(url, timeout=2)
            if req.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def find_available_port(start=3000):
    """查找可用端口"""
    for port in range(start, start + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            continue
    return None


def main():
    print("=" * 60)
    print("OpsV-Kits 前端测试启动中...")
    print("=" * 60)

    # 设置环境变量
    os.chdir(os.path.join(os.path.dirname(__file__), "..", ".."))
    backend_dir = os.path.join(os.getcwd(), "backend")
    frontend_dir = os.path.join(os.getcwd(), "frontend")

    # 查找可用端口
    frontend_port = find_available_port(3000)
    backend_port = 8000

    print(f"前端端口: {frontend_port}")
    print(f"后端端口: {backend_port}")

    # 设置环境变量
    frontend_url = f"http://localhost:{frontend_port}"
    backend_url = f"http://localhost:{backend_port}"
    os.environ["FRONTEND_URL"] = frontend_url
    os.environ["BACKEND_URL"] = backend_url

    # 启动后端服务
    print("\n[1/3] 启动后端服务...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", str(backend_port),
        "--log-level", "error"
    ]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )

    # 等待后端启动
    if wait_for_http(f"{backend_url}/api/health", timeout=30):
        print("  ✓ 后端服务已启动")
    else:
        print("  ✗ 后端服务启动失败")
        backend_proc.kill()
        sys.exit(1)

    # 启动前端服务
    print("\n[2/3] 启动前端服务...")

    # 修改vite配置使用指定端口
    vite_config_path = os.path.join(frontend_dir, "vite.config.ts")
    original_config = None

    # 尝试读取原始配置
    try:
        with open(vite_config_path, "r", encoding="utf-8") as f:
            original_config = f.read()
    except Exception:
        pass

    # 启动npm run dev (它会使用vite配置的端口查找逻辑)
    # Windows下npm是.cmd文件，需要shell=True
    frontend_cmd = "npm run dev"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        shell=True,
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )

    # 等待前端启动并检测实际端口
    print("  等待前端服务启动...", end="", flush=True)
    actual_frontend_port = None

    # 通过日志检测端口
    if frontend_proc.stdout:
        for _ in range(60):  # 最多等待60秒
            line = frontend_proc.stdout.readline()
            if not line:
                break
            print(".", end="", flush=True)
            if "Local:" in line or "localhost:" in line:
                # 提取端口号
                import re
                match = re.search(r'localhost:(\d+)', line)
                if match:
                    actual_frontend_port = int(match.group(1))
                    break
            if "ready" in line.lower() or "Local" in line:
                match = re.search(r'(\d{4})', line)
                if match:
                    actual_frontend_port = int(match.group(1))
                    break
            time.sleep(1)

    if actual_frontend_port is None:
        # 尝试常见端口
        for port in [3000, 3001, 3002, 5173, 5174, 5175]:
            if wait_for_port(port, timeout=5):
                actual_frontend_port = port
                break

    if actual_frontend_port is None:
        print("\n  ✗ 前端服务启动失败或未检测到端口")
        frontend_proc.kill()
        backend_proc.kill()
        sys.exit(1)

    actual_frontend_url = f"http://localhost:{actual_frontend_port}"
    print(f"\n  ✓ 前端服务已启动 (端口: {actual_frontend_port})")

    # 更新环境变量
    os.environ["FRONTEND_URL"] = actual_frontend_url

    # 执行测试
    print(f"\n[3/3] 执行前端测试...")
    print(f"  前端URL: {actual_frontend_url}")
    print(f"  后端URL: {backend_url}")
    print("-" * 60)

    try:
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/frontend/test_pages.py", "-v", "--tb=short"],
            cwd=os.getcwd(),
            env={**os.environ, "FRONTEND_URL": actual_frontend_url, "BACKEND_URL": backend_url}
        )
        exit_code = test_result.returncode
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit_code = 130
    except Exception as e:
        print(f"\n测试执行异常: {e}")
        exit_code = 1

    # 清理服务
    print("\n" + "=" * 60)
    print("清理服务...")
    frontend_proc.kill()
    backend_proc.kill()
    frontend_proc.wait()
    backend_proc.wait()
    print("  ✓ 所有服务已停止")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
