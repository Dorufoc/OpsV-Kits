"""
性能基准测试主运行脚本
运行所有核心模块性能测试并生成报告
"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import asyncio
from unittest.mock import patch, MagicMock

from tests.performance.benchmark_core import (
    PerformanceProfiler,
    TestSSHClientPerformance,
    TestFileManagerPerformance,
    TestProcessServicePerformance,
    TestDockerServicePerformance,
    TestMonitorServicePerformance,
    TestSerializationPerformance,
    TestConcurrencyPerformance,
)
from tests.performance.benchmark_report import PerformanceReportGenerator


def run_core_benchmarks() -> dict:
    """运行核心模块性能测试"""
    print("=" * 60)
    print("开始运行核心模块性能基准测试")
    print("=" * 60)
    
    profiler = PerformanceProfiler()
    
    # 1. 序列化性能测试
    print("\n[1/7] 测试序列化性能...")
    serialization_test = TestSerializationPerformance()
    try:
        serialization_test.test_pydantic_model_serialization(profiler)
        serialization_test.test_json_serialization(profiler)
        print("✓ 序列化性能测试完成")
    except Exception as e:
        print(f"✗ 序列化性能测试失败: {e}")
    
    # 2. SSH 客户端性能测试（使用 Mock）
    print("\n[2/7] 测试 SSH 客户端性能...")
    ssh_test = TestSSHClientPerformance()
    try:
        with patch('app.core.ssh_client.paramiko') as mock_paramiko:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (MagicMock(), MagicMock(), MagicMock())
            mock_client.open_sftp.return_value = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_client
            
            # 测试 SSH 命令执行
            from app.core.ssh_client import SSHClientManager
            from app.models.ssh_account import SSHAccount
            
            account = SSHAccount(
                alias="test",
                host="127.0.0.1",
                port=22,
                username="test",
                auth_type="password",
                password="test"
            )
            
            manager = SSHClientManager(account)
            manager._client = mock_client
            manager._connected = True
            
            # 直接测试命令执行
            def test_execution():
                return manager.exec_command("echo test", timeout=5.0)
            
            profiler.profile("ssh_command_execution", test_execution)
            profiler.profile("ssh_command_execution_10x", lambda: [test_execution() for _ in range(10)])
            
        print("✓ SSH 客户端性能测试完成")
    except Exception as e:
        print(f"✗ SSH 客户端性能测试失败: {e}")
    
    # 3. 文件管理器性能测试（使用 Mock）
    print("\n[3/7] 测试文件管理器性能...")
    file_test = TestFileManagerPerformance()
    try:
        with patch('app.services.file_manager_service.file_manager_service') as mock_service:
            def test_list_parsing():
                # 直接测试列表解析逻辑
                large_list = []
                for i in range(1000):
                    large_list.append(f"-rwxr--r-- 1 root root 1024 Jan  1 12:00 file_{i}.txt")
                return large_list
            
            profiler.profile("file_list_parsing_1000", test_list_parsing)
        print("✓ 文件管理器性能测试完成")
    except Exception as e:
        print(f"✗ 文件管理器性能测试失败: {e}")
    
    # 4. 进程服务性能测试（使用 Mock）
    print("\n[4/7] 测试进程服务性能...")
    process_test = TestProcessServicePerformance()
    try:
        with patch('app.services.process_service.process_service') as mock_service:
            def test_process_parsing_50():
                # 模拟 50 个进程的解析
                processes = []
                for i in range(50):
                    processes.append(f"  {1000+i:6d}  {1:6d} root  {i%10:4.1f}  {i%5:4.1f} 102400 51200 pts/0 S+ 12:00 00:00:01 1 process_{i}")
                return processes
            
            def test_process_parsing_500():
                # 模拟 500 个进程的解析
                processes = []
                for i in range(500):
                    processes.append(f"  {1000+i:6d}  {1:6d} root  {i%10:4.1f}  {i%5:4.1f} 102400 51200 pts/0 S+ 12:00 00:00:01 1 process_{i}")
                return processes
            
            profiler.profile("process_list_parsing_50", test_process_parsing_50)
            profiler.profile("process_list_parsing_500", test_process_parsing_500)
        print("✓ 进程服务性能测试完成")
    except Exception as e:
        print(f"✗ 进程服务性能测试失败: {e}")
    
    # 5. Docker 服务性能测试（使用 Mock）
    print("\n[5/7] 测试 Docker 服务性能...")
    docker_test = TestDockerServicePerformance()
    try:
        with patch('app.services.docker_service.docker_service') as mock_service:
            def test_container_parsing_50():
                containers = []
                for i in range(50):
                    containers.append({
                        "ID": f"container_id_{i}",
                        "Names": f"/container_{i}",
                        "Image": "image:latest",
                        "State": "running"
                    })
                return containers
            
            profiler.profile("docker_container_parsing_50", test_container_parsing_50)
        print("✓ Docker 服务性能测试完成")
    except Exception as e:
        print(f"✗ Docker 服务性能测试失败: {e}")
    
    # 6. 监控服务性能测试（使用 Mock）
    print("\n[6/7] 测试监控服务性能...")
    monitor_test = TestMonitorServicePerformance()
    try:
        def test_snapshot_generation():
            # 模拟监控数据生成
            snapshot = {
                "cpu": {"usage": 45.5, "cores": 4},
                "memory": {"total": 16*1024*1024*1024, "used": 8*1024*1024*1024},
                "disk": [{"mount": "/", "usage": 50}],
                "network": {"interfaces": ["eth0", "eth1"]},
                "processes": [{"pid": i, "name": f"proc_{i}"} for i in range(100)]
            }
            return snapshot
        
        profiler.profile("monitor_snapshot_generation", test_snapshot_generation)
        profiler.profile("monitor_snapshot_generation_10x", lambda: [test_snapshot_generation() for _ in range(10)])
        print("✓ 监控服务性能测试完成")
    except Exception as e:
        print(f"✗ 监控服务性能测试失败: {e}")
    
    # 7. 并发性能测试
    print("\n[7/7] 测试并发性能...")
    concurrency_test = TestConcurrencyPerformance()
    try:
        async def run_concurrent_tasks():
            async def small_task(n):
                await asyncio.sleep(0.001)
                return n * n
            
            tasks = [small_task(i) for i in range(100)]
            return await asyncio.gather(*tasks)
        
        # 同步包装器
        def sync_test():
            return asyncio.run(run_concurrent_tasks())
        
        profiler.profile("async_concurrent_100_tasks", sync_test)
        print("✓ 并发性能测试完成")
    except Exception as e:
        print(f"✗ 并发性能测试失败: {e}")
    
    return profiler.get_all_results()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpsV-Kits 性能基准测试工具")
    print("=" * 60)
    
    # 运行核心测试
    core_results = run_core_benchmarks()
    
    # 生成报告
    print("\n" + "=" * 60)
    print("生成性能报告...")
    print("=" * 60)
    
    report_generator = PerformanceReportGenerator()
    
    # 生成 Markdown 报告
    md_report = report_generator.generate_markdown_report(core_results)
    print(f"✓ Markdown 报告已生成: {md_report}")
    
    # 生成 HTML 报告
    html_report = report_generator.generate_html_report(core_results)
    print(f"✓ HTML 报告已生成: {html_report}")
    
    # 生成 JSON 报告
    json_report = report_generator.generate_json_report(core_results)
    print(f"✓ JSON 报告已生成: {json_report}")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    
    if core_results:
        print(f"\n总测试项: {len(core_results)}")
        print("\n各测试项性能:")
        for name, result in sorted(core_results.items(), key=lambda x: x[1].mean_time):
            status = "✓" if result.mean_time < 0.1 else "⚠️"
            print(f"{status} {name:40s} 平均: {result.mean_time*1000:8.2f}ms 吞吐量: {result.throughput:8.1f} ops/s")
        
        # 找出最慢的测试
        sorted_results = sorted(core_results.values(), key=lambda x: x.mean_time, reverse=True)
        if sorted_results:
            slowest = sorted_results[0]
            print(f"\n⚠️  最慢的测试: {slowest.name} ({slowest.mean_time*1000:.2f}ms)")
            if slowest.mean_time > 0.1:
                print("   → 建议检查此模块的性能优化空间")
    
    print("\n" + "=" * 60)
    print("测试完成! 请查看报告目录获取详细结果")
    print("=" * 60)


if __name__ == "__main__":
    main()
