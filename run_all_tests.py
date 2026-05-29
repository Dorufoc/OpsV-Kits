"""
OpsV-Kits 统一测试运行脚本
用法: python run_all_tests.py [--backend] [--frontend] [--all]
"""
import subprocess
import sys
import os
import time
import argparse


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run_backend_tests(verbose=False):
    """运行后端测试"""
    print_header("后端单元测试")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/backend/",
        "-v",
        "--tb=short",
        "--ignore=tests/backend/test_mysql_password_flag.py",
    ]
    
    if verbose:
        cmd.append("-s")
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    return result.returncode


def run_frontend_unit_tests():
    """运行前端单元测试"""
    print_header("前端单元测试")
    
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("安装前端测试依赖...")
        subprocess.run(["npm", "install", "--save-dev", "vitest", "@vue/test-utils", "jsdom", "@vitejs/plugin-vue", "happy-dom"], 
                      cwd=frontend_dir, shell=True)
    
    cmd = ["npx", "vitest", "run", "--reporter=verbose"]
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=frontend_dir, shell=True)
    return result.returncode


def run_frontend_e2e_tests():
    """运行前端E2E测试 (需要前后端服务运行)"""
    print_header("前端E2E测试 (Playwright)")
    
    # 检查Playwright是否已安装
    try:
        subprocess.run([sys.executable, "-m", "playwright", "--version"], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("安装Playwright浏览器...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    
    print("\n注意: E2E测试需要前后端服务运行")
    print("请先启动前后端服务，然后运行: python tests/frontend/run_frontend_tests.py")
    return 0


def generate_test_report():
    """生成测试覆盖率报告"""
    print_header("生成测试覆盖率报告")
    
    # 后端覆盖率
    print("后端覆盖率:")
    subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/backend/",
        "--cov=backend/app",
        "--cov-report=html:tests/backend/coverage",
        "--cov-report=term-missing",
        "--ignore=tests/backend/test_mysql_password_flag.py",
    ], cwd=os.getcwd())
    
    print("\n覆盖率报告已生成: tests/backend/coverage/index.html")


def main():
    parser = argparse.ArgumentParser(description="OpsV-Kits 统一测试运行脚本")
    parser.add_argument("--backend", action="store_true", help="仅运行后端测试")
    parser.add_argument("--frontend", action="store_true", help="仅运行前端单元测试")
    parser.add_argument("--frontend-e2e", action="store_true", help="运行前端E2E测试")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 如果没有任何参数，默认运行所有测试
    if not any([args.backend, args.frontend, args.frontend_e2e, args.all]):
        args.all = True
    
    os.chdir(os.path.join(os.path.dirname(__file__)))
    
    start_time = time.time()
    exit_code = 0
    
    if args.backend or args.all:
        code = run_backend_tests(args.verbose)
        if code != 0:
            exit_code = code
    
    if args.frontend or args.all:
        code = run_frontend_unit_tests()
        if code != 0 and exit_code == 0:
            exit_code = code
    
    if args.frontend_e2e:
        code = run_frontend_e2e_tests()
        if code != 0 and exit_code == 0:
            exit_code = code
    
    if args.coverage:
        generate_test_report()
    
    elapsed = time.time() - start_time
    
    print_header("测试完成")
    print(f"总耗时: {elapsed:.2f} 秒")
    print(f"退出码: {exit_code}")
    if exit_code == 0:
        print("✓ 所有测试通过")
    else:
        print("✗ 部分测试失败")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
