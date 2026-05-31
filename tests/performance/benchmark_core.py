"""
核心模块性能基准测试
测试 SSH 连接、文件同步、Docker 管理等核心功能的性能
"""
from __future__ import annotations

import time
import asyncio
import random
import string
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest
import psutil


@dataclass
class BenchmarkResult:
    """性能基准测试结果"""
    name: str
    iterations: int
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    std_dev: float
    throughput: float  # ops/sec
    memory_usage: Optional[float] = None  # MB
    cpu_usage: Optional[float] = None  # %


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.results: Dict[str, List[float]] = defaultdict(list)
        self.memory_snapshots: Dict[str, List[float]] = defaultdict(list)
        self.cpu_snapshots: Dict[str, List[float]] = defaultdict(list)
        self.process = psutil.Process()
    
    def profile(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """执行性能分析"""
        times = []
        mem_usages = []
        cpu_usages = []
        
        # 预热
        func(*args, **kwargs)
        
        # 正式测试
        for _ in range(10):
            # 记录初始状态
            mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
            self.process.cpu_percent(interval=None)  # 重置 CPU 计数器
            
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            
            # 记录结束状态
            mem_after = self.process.memory_info().rss / 1024 / 1024
            cpu_after = self.process.cpu_percent(interval=None)
            
            times.append(elapsed)
            mem_usages.append(mem_after - mem_before)
            cpu_usages.append(cpu_after)
        
        self.results[name].extend(times)
        self.memory_snapshots[name].extend(mem_usages)
        self.cpu_snapshots[name].extend(cpu_usages)
        
        return result
    
    async def profile_async(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """异步函数性能分析"""
        times = []
        mem_usages = []
        cpu_usages = []
        
        # 预热
        await func(*args, **kwargs)
        
        # 正式测试
        for _ in range(10):
            mem_before = self.process.memory_info().rss / 1024 / 1024
            self.process.cpu_percent(interval=None)
            
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            
            mem_after = self.process.memory_info().rss / 1024 / 1024
            cpu_after = self.process.cpu_percent(interval=None)
            
            times.append(elapsed)
            mem_usages.append(mem_after - mem_before)
            cpu_usages.append(cpu_after)
        
        self.results[name].extend(times)
        self.memory_snapshots[name].extend(mem_usages)
        self.cpu_snapshots[name].extend(cpu_usages)
        
        return result
    
    def get_result(self, name: str) -> BenchmarkResult:
        """获取测试结果"""
        times = sorted(self.results[name])
        n = len(times)
        
        mean = sum(times) / n
        median = times[n // 2] if n % 2 else (times[n // 2 - 1] + times[n // 2]) / 2
        variance = sum((t - mean) ** 2 for t in times) / n
        std_dev = variance ** 0.5
        
        mem_avg = sum(self.memory_snapshots[name]) / n if self.memory_snapshots[name] else None
        cpu_avg = sum(self.cpu_snapshots[name]) / n if self.cpu_snapshots[name] else None
        
        return BenchmarkResult(
            name=name,
            iterations=n,
            min_time=min(times),
            max_time=max(times),
            mean_time=mean,
            median_time=median,
            std_dev=std_dev,
            throughput=n / sum(times) if sum(times) > 0 else 0,
            memory_usage=mem_avg,
            cpu_usage=cpu_avg
        )
    
    def get_all_results(self) -> Dict[str, BenchmarkResult]:
        """获取所有测试结果"""
        return {name: self.get_result(name) for name in self.results}


# ==================== Mock 数据生成器 ====================

def generate_random_string(length: int) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_mock_ssh_account():
    """生成模拟 SSH 账户"""
    account = MagicMock()
    account.alias = f"test-server-{generate_random_string(8)}"
    account.host = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
    account.port = 22
    account.username = "root"
    account.auth_type = "password"
    account.password = generate_random_string(16)
    account.private_key = None
    account.key_passphrase = None
    return account


def generate_mock_process_list(count: int = 100):
    """生成模拟进程列表输出"""
    processes = []
    for i in range(count):
        pid = random.randint(1000, 65535)
        ppid = random.randint(1, 1000) if i > 0 else 1
        user = random.choice(["root", "www-data", "mysql", "nginx", "redis"])
        pcpu = random.uniform(0, 100)
        pmem = random.uniform(0, 50)
        vsz = random.randint(10000, 1000000)
        rss = random.randint(1000, 500000)
        tty = random.choice(["?", "pts/0", "pts/1", "tty1"])
        stat = random.choice(["R", "S", "D", "Z", "T"])
        start = f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}"
        time = f"00:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
        nlwp = random.randint(1, 100)
        comm = random.choice(["nginx", "mysql", "redis-server", "python3", "java", "node"])
        
        processes.append(f"{pid:6d} {ppid:6d} {user:8} {pcpu:4.1f} {pmem:4.1f} {vsz:7d} {rss:6d} {tty:5} {stat:1} {start:5} {time:8} {nlwp:3} {comm}")
    
    return "\n".join(processes)


# ==================== 核心模块测试 ====================

@pytest.fixture
def profiler():
    """性能分析器 fixture"""
    return PerformanceProfiler()


class TestSSHClientPerformance:
    """SSH 客户端性能测试"""
    
    @pytest.fixture
    def mock_ssh_client(self):
        """模拟 SSH 客户端"""
        with patch("app.core.ssh_client.paramiko") as mock_paramiko:
            mock_client = MagicMock()
            mock_paramiko.SSHClient.return_value = mock_client
            
            # 模拟 exec_command
            def mock_exec_command(cmd, timeout=None):
                stdout = MagicMock()
                stdout.read.return_value = b"test output"
                stderr = MagicMock()
                stderr.read.return_value = b""
                return MagicMock(), stdout, stderr
            
            mock_client.exec_command.side_effect = mock_exec_command
            
            # 模拟 SFTP
            mock_sftp = MagicMock()
            mock_client.open_sftp.return_value = mock_sftp
            
            yield mock_client
    
    def test_ssh_connection_establishment(self, profiler, mock_ssh_client):
        """测试 SSH 连接建立性能"""
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
        
        def connect():
            manager = SSHClientManager(account)
            manager.connect(timeout=5.0)
            return manager
        
        profiler.profile("ssh_connection_establishment", connect)
    
    def test_ssh_command_execution(self, profiler, mock_ssh_client):
        """测试 SSH 命令执行性能"""
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
        manager._client = mock_ssh_client
        manager._connected = True
        
        def execute_command():
            return manager.exec_command("echo test", timeout=5.0)
        
        profiler.profile("ssh_command_execution", execute_command)
    
    def test_ssh_concurrent_commands(self, profiler, mock_ssh_client):
        """测试 SSH 并发命令执行"""
        from app.core.ssh_client import SSHClientManager
        from app.models.ssh_account import SSHAccount
        import threading
        
        account = SSHAccount(
            alias="test",
            host="127.0.0.1",
            port=22,
            username="test",
            auth_type="password",
            password="test"
        )
        
        manager = SSHClientManager(account)
        manager._client = mock_ssh_client
        manager._connected = True
        
        def concurrent_execution():
            threads = []
            results = []
            
            def worker():
                result = manager.exec_command("echo test", timeout=5.0)
                results.append(result)
            
            for _ in range(10):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            return len(results)
        
        profiler.profile("ssh_concurrent_commands", concurrent_execution)


class TestFileManagerPerformance:
    """文件管理性能测试"""
    
    def test_file_list_parsing_large(self, profiler):
        """测试大文件列表解析性能"""
        from app.services.file_manager_service import file_manager_service
        
        # 生成大型文件列表
        large_file_list = []
        for i in range(1000):
            perms = f"-rwxr--r--"
            links = random.randint(1, 10)
            owner = random.choice(["root", "user", "www-data"])
            group = random.choice(["root", "user", "www-data"])
            size = random.randint(100, 1000000000)
            month = random.choice(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            day = random.randint(1, 31)
            time = f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}"
            name = f"file_{i}_{generate_random_string(10)}.txt"
            large_file_list.append(f"{perms} {links:2d} {owner:8} {group:8} {size:10d} {month} {day:2d} {time} {name}")
        
        with patch.object(file_manager_service, "_exec") as mock_exec:
            mock_exec.return_value = (0, "\n".join(large_file_list), "")
            
            def parse_large_list():
                return file_manager_service.list_files("test-alias", "/")
            
            profiler.profile("file_list_parsing_large", parse_large_list)


class TestProcessServicePerformance:
    """进程服务性能测试"""
    
    def test_process_list_parsing(self, profiler):
        """测试进程列表解析性能"""
        from app.services.process_service import process_service
        
        process_output = generate_mock_process_list(500)
        args_output = "\n".join([f"{i} {generate_random_string(20)}" for i in range(500)])
        cwd_output = "\n".join([f"{i}:/home/user" for i in range(500)])
        full_output = f"{process_output}\n---ARGS---\n{args_output}\n---CWD---\n{cwd_output}"
        
        with patch.object(process_service, "_exec") as mock_exec:
            mock_exec.return_value = (0, full_output, "")
            
            def parse_processes():
                return process_service.get_all_processes("test-alias")
            
            profiler.profile("process_list_parsing_500", parse_processes)
    
    def test_process_list_parsing_small(self, profiler):
        """测试小规模进程列表解析性能"""
        from app.services.process_service import process_service
        
        process_output = generate_mock_process_list(50)
        args_output = "\n".join([f"{i} {generate_random_string(20)}" for i in range(50)])
        cwd_output = "\n".join([f"{i}:/home/user" for i in range(50)])
        full_output = f"{process_output}\n---ARGS---\n{args_output}\n---CWD---\n{cwd_output}"
        
        with patch.object(process_service, "_exec") as mock_exec:
            mock_exec.return_value = (0, full_output, "")
            
            def parse_processes():
                return process_service.get_all_processes("test-alias")
            
            profiler.profile("process_list_parsing_50", parse_processes)


class TestDockerServicePerformance:
    """Docker 服务性能测试"""
    
    def test_container_list_parsing(self, profiler):
        """测试容器列表解析性能"""
        from app.services.docker_service import docker_service
        
        # 生成多个容器的 JSON 输出
        containers = []
        for i in range(50):
            container = {
                "ID": generate_random_string(64),
                "Names": f"/container-{i}",
                "Image": f"image-{i}:latest",
                "Command": "/bin/sh -c 'sleep 3600'",
                "CreatedAt": "2024-01-01T00:00:00Z",
                "Ports": "",
                "State": "running",
                "Status": "Up 2 hours",
                "Size": "0B",
                "Labels": "",
                "Mounts": "",
                "Networks": "bridge"
            }
            containers.append(container)
        
        docker_output = "\n".join([f"'{c}'" for c in containers])
        
        with patch.object(docker_service, "_exec_docker_json") as mock_exec:
            mock_exec.return_value = containers
            
            def list_containers():
                return docker_service.list_containers("test-alias")
            
            profiler.profile("docker_container_list_parsing", list_containers)


class TestMonitorServicePerformance:
    """监控服务性能测试"""
    
    def test_full_snapshot_generation(self, profiler):
        """测试完整监控快照生成性能"""
        from app.services.monitor_service import monitor_service
        
        with patch.object(monitor_service, "_exec") as mock_exec:
            def mock_exec_result(cmd):
                if "cat /proc/stat | head -1" in cmd:
                    return (0, "cpu  1000 0 500 8000 0 0 0 0", "")
                elif "grep '^cpu[0-9]'" in cmd:
                    return (0, "cpu0  1000 0 500 8000\ncpu1  1000 0 500 8000\ncpu2  1000 0 500 8000\ncpu3  1000 0 500 8000", "")
                elif "free -b" in cmd:
                    return (0, "Mem:  16777216 8388608 4194304 1048576 1048576 8388608\nSwap: 4194304 0 4194304", "")
                elif "df -B1" in cmd:
                    return (0, "/dev/sda1 100000000000 50000000000 50000000000 50% /\n/dev/sdb1 200000000000 100000000000 100000000000 50% /data", "")
                elif "cat /proc/net/dev" in cmd:
                    return (0, "  eth0: 1000000 1000 0 0 0 0 0 0 500000 500 0 0 0 0 0 0\n  eth1: 2000000 2000 0 0 0 0 0 0 1000000 1000 0 0 0 0 0 0", "")
                elif "cat /proc/loadavg" in cmd:
                    return (0, "0.5 0.3 0.1 2/100 1234", "")
                elif "cat /proc/uptime" in cmd:
                    return (0, "3600.0 7200.0", "")
                elif "hostname" in cmd:
                    return (0, "testhost", "")
                elif "nproc" in cmd:
                    return (0, "4", "")
                return (0, "", "")
            
            mock_exec.side_effect = mock_exec_result
            
            def generate_snapshot():
                monitor_service._cpu_prev.clear()
                monitor_service._cpu_core_prev.clear()
                monitor_service._network_prev.clear()
                monitor_service._disk_io_prev.clear()
                return monitor_service.get_snapshot("test-alias")
            
            profiler.profile("monitor_full_snapshot", generate_snapshot)


class TestSerializationPerformance:
    """数据序列化性能测试"""
    
    def test_pydantic_model_serialization(self, profiler):
        """测试 Pydantic 模型序列化性能"""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            id: int
            name: str
            value: float
            tags: List[str]
            metadata: Dict[str, Any]
        
        # 创建大量模型实例
        models = []
        for i in range(1000):
            models.append(TestModel(
                id=i,
                name=f"item-{i}",
                value=random.random(),
                tags=[generate_random_string(5) for _ in range(5)],
                metadata={"key1": "value1", "key2": random.randint(0, 100)}
            ))
        
        def serialize_models():
            return [model.model_dump() for model in models]
        
        profiler.profile("pydantic_serialization_1000", serialize_models)
    
    def test_json_serialization(self, profiler):
        """测试 JSON 序列化性能"""
        import json
        
        data = []
        for i in range(1000):
            data.append({
                "id": i,
                "name": f"item-{i}",
                "value": random.random(),
                "tags": [generate_random_string(5) for _ in range(5)],
                "metadata": {"key1": "value1", "key2": random.randint(0, 100)}
            })
        
        def json_serialize():
            return json.dumps(data)
        
        profiler.profile("json_serialization_1000", json_serialize)


class TestConcurrencyPerformance:
    """并发性能测试"""
    
    @pytest.mark.asyncio
    async def test_async_task_execution(self, profiler):
        """测试异步任务执行性能"""
        
        async def small_task(n):
            await asyncio.sleep(0.001)
            return n * n
        
        async def run_concurrent_tasks():
            tasks = [small_task(i) for i in range(100)]
            return await asyncio.gather(*tasks)
        
        await profiler.profile_async("async_concurrent_tasks_100", run_concurrent_tasks)
