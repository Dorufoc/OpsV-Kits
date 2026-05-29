#!/usr/bin/env python3
"""
测试 Docker exec 命令 PTY 嵌套问题

验证修复：docker exec -it 改为 docker exec -i 后，避免了双重 PTY 嵌套导致的输入丢失问题。

问题根因：
- SSH channel 通过 get_pty() 已分配一个 PTY
- docker exec -it 的 -t 参数又分配一个 PTY
- 双重 PTY 导致输入缓冲区混乱，密码无法正确传递

修复方案：
- 移除 docker exec 的 -t 参数
- 仅使用 -i 保持 STDIN 开放
- SSH PTY 已提供终端功能，Docker 无需再分配 PTY
"""

import subprocess
import sys
import time
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

def test_docker_command_format():
    """测试 docker exec 命令格式是否正确"""
    print("=" * 60)
    print("测试 1: 验证 docker exec 命令格式")
    print("=" * 60)
    
    # 读取修复后的代码
    ws_file = BACKEND_DIR / "app" / "core" / "db_toolkit_ws.py"
    content = ws_file.read_text(encoding="utf-8")
    
    # 验证不再使用 -it 参数
    if "docker exec -it" in content:
        print("❌ 失败: 代码中仍存在 'docker exec -it'，应改为 'docker exec -i'")
        return False
    else:
        print("✅ 通过: 代码中已移除 'docker exec -it'")
    
    # 验证使用 -i 参数
    if "docker exec -i" in content:
        print("✅ 通过: 代码中正确使用 'docker exec -i'")
        return True
    else:
        print("❌ 失败: 代码中未找到 'docker exec -i'")
        return False


def test_pty_allocation():
    """测试 PTY 分配逻辑"""
    print("\n" + "=" * 60)
    print("测试 2: 验证 PTY 分配逻辑")
    print("=" * 60)
    
    ws_file = BACKEND_DIR / "app" / "core" / "db_toolkit_ws.py"
    content = ws_file.read_text(encoding="utf-8")
    
    # 验证 SSH channel 仍分配 PTY
    if "chan.get_pty(" in content:
        print("✅ 通过: SSH channel 正确分配 PTY")
        return True
    else:
        print("❌ 失败: 未找到 SSH channel 的 PTY 分配")
        return False


def test_mysql_command_construction():
    """测试 MySQL 命令构建"""
    print("\n" + "=" * 60)
    print("测试 3: 验证 MySQL 命令构建")
    print("=" * 60)
    
    ws_file = BACKEND_DIR / "app" / "core" / "db_toolkit_ws.py"
    content = ws_file.read_text(encoding="utf-8")
    
    checks = [
        ("mysql -h", "MySQL 主机参数"),
        ("-P", "MySQL 端口参数"),
        ("-u", "MySQL 用户参数"),
        ("-p", "MySQL 密码参数"),
    ]
    
    all_passed = True
    for pattern, description in checks:
        if pattern in content:
            print(f"✅ 通过: {description} ({pattern})")
        else:
            print(f"❌ 失败: {description} ({pattern})")
            all_passed = False
    
    return all_passed


def test_input_handling():
    """测试输入处理逻辑"""
    print("\n" + "=" * 60)
    print("测试 4: 验证输入处理逻辑")
    print("=" * 60)
    
    ws_file = BACKEND_DIR / "app" / "core" / "db_toolkit_ws.py"
    content = ws_file.read_text(encoding="utf-8")
    
    # 验证输入处理
    if "chan.send(data)" in content:
        print("✅ 通过: 正确处理 WebSocket 输入并发送到 SSH channel")
        return True
    else:
        print("❌ 失败: 未找到输入处理逻辑")
        return False


def run_all_tests():
    """运行所有测试"""
    print("开始测试 Docker exec PTY 嵌套问题修复")
    print("=" * 60)
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        test_docker_command_format,
        test_pty_allocation,
        test_mysql_command_construction,
        test_input_handling,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("✅ 所有测试通过！修复已正确应用。")
        return 0
    else:
        print("❌ 部分测试失败，请检查修复。")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
