
#!/usr/bin/env python3
"""
OpsV-Kits 项目内存使用分析脚本
分析项目运行时的内存消耗情况
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

import gc
import json
import random
import string
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# 项目模块导入
from app.models.ssh_account import SSHAccount, SSHAccountCreate, AccountGroup
from app.models.audit_log import AuditLog


@dataclass
class MemorySnapshot:
    """内存快照数据"""
    timestamp: float
    total_allocated: int
    peak_allocated: int
    allocations: int
    description: str


@dataclass
class MemoryUsageAnalysis:
    """内存使用分析结果"""
    module_name: str
    base_memory: int
    peak_memory: int
    memory_increase: int
    allocations: int
    top_allocations: List[Dict[str, Any]]


class MemoryAnalyzer:
    """内存分析器"""
    
    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.allocations_by_module: Dict[str, List[int]] = defaultdict(list)
        
    def take_snapshot(self, description: str = "") -> MemorySnapshot:
        """获取当前内存快照"""
        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics('lineno')
        current, peak = tracemalloc.get_traced_memory()
        
        snapshot_data = MemorySnapshot(
            timestamp=time.time(),
            total_allocated=current,
            peak_allocated=peak,
            allocations=len(stats),
            description=description
        )
        
        self.snapshots.append(snapshot_data)
        return snapshot_data
    
    def analyze_function(
        self,
        func: Callable,
        description: str = "",
        *args,
        **kwargs
    ) -> MemoryUsageAnalysis:
        """分析单个函数的内存使用情况"""
        gc.collect()
        tracemalloc.start()
        
        # 基准测量
        self.take_snapshot(f"{description} - before")
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 测量之后
        snapshot = self.take_snapshot(f"{description} - after")
        
        # 获取详细信息
        snapshot_obj = tracemalloc.take_snapshot()
        top_stats = snapshot_obj.statistics('lineno')
        
        tracemalloc.stop()
        
        # 计算增量
        if len(self.snapshots) >= 2:
            base = self.snapshots[-2]
            peak = snapshot
            increase = peak.total_allocated - base.total_allocated
        else:
            base = snapshot
            peak = snapshot
            increase = 0
            
        return MemoryUsageAnalysis(
            module_name=description,
            base_memory=base.total_allocated,
            peak_memory=peak.peak_allocated,
            memory_increase=increase,
            allocations=snapshot.allocations,
            top_allocations=[
                {
                    "traceback": str(stat.traceback),
                    "size": stat.size,
                    "count": stat.count
                }
                for stat in top_stats[:10]
            ]
        )


# 测试数据生成
def generate_random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_mock_ssh_account(alias: Optional[str] = None) -> SSHAccount:
    """生成模拟的 SSH 账户"""
    return SSHAccount(
        alias=alias or f"test-account-{generate_random_string(8)}",
        host=f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
        port=random.randint(1, 65535),
        username=f"user-{generate_random_string(6)}",
        auth_type=random.choice(["password", "key"]),
        password=generate_random_string(20),
        private_key=None,
        key_passphrase=None,
        totp_secret=None,
        is_default=False,
        group=random.choice(["production", "staging", "test"])
    )


def generate_mock_audit_log() -> AuditLog:
    """生成模拟的审计日志"""
    return AuditLog(
        timestamp=datetime.now(),
        account_alias=f"test-account-{random.randint(1, 100)}",
        action=random.choice(["create", "update", "delete", "connect"]),
        status=random.choice(["success", "failure"]),
        detail=generate_random_string(50)
    )


def generate_large_history_data(n: int = 3600) -> deque:
    """生成大型历史数据（模拟监控数据）"""
    data = deque(maxlen=n)
    for _ in range(n):
        data.append({
            "timestamp": time.time() - random.randint(0, 3600),
            "cpu": {"usage": random.uniform(0, 100), "cores": random.randint(1, 16)},
            "memory": {
                "total": random.randint(1024**3, 16 * 1024**3),
                "used": random.randint(0, 16 * 1024**3),
                "free": random.randint(0, 16 * 1024**3)
            },
            "network": {
                "eth0": {
                    "rx_bytes": random.randint(0, 10**9),
                    "tx_bytes": random.randint(0, 10**9)
                }
            },
            "processes": [
                {
                    "pid": random.randint(1, 65535),
                    "name": f"process-{i}",
                    "cpu": random.uniform(0, 100),
                    "mem": random.uniform(0, 50)
                }
                for i in range(random.randint(10, 200))
            ]
        })
    return data


# 内存使用测试函数
def test_ssh_account_creation_memory() -> MemoryUsageAnalysis:
    """测试 SSH 账户创建的内存使用"""
    analyzer = MemoryAnalyzer()
    accounts = []
    
    def create_accounts():
        for _ in range(1000):
            accounts.append(generate_mock_ssh_account())
    
    return analyzer.analyze_function(create_accounts, "SSH Account Creation")


def test_account_group_management_memory() -> MemoryUsageAnalysis:
    """测试账户分组管理的内存使用"""
    analyzer = MemoryAnalyzer()
    
    def manage_groups():
        groups = []
        for i in range(100):
            group = AccountGroup(name=f"group-{i}", accounts=[])
            for j in range(50):
                account = generate_mock_ssh_account(f"account-{i}-{j}")
                group.accounts.append(account.alias)
            groups.append(group)
        return groups
    
    return analyzer.analyze_function(manage_groups, "Account Group Management")


def test_audit_log_memory() -> MemoryUsageAnalysis:
    """测试审计日志存储的内存使用"""
    analyzer = MemoryAnalyzer()
    
    def store_logs():
        logs = []
        for _ in range(10000):
            logs.append(generate_mock_audit_log())
        return logs
    
    return analyzer.analyze_function(store_logs, "Audit Log Storage")


def test_monitoring_history_memory() -> MemoryUsageAnalysis:
    """测试监控历史数据存储的内存使用"""
    analyzer = MemoryAnalyzer()
    
    def store_history():
        # 模拟多个账户的监控数据
        histories = {}
        for account_idx in range(10):
            histories[f"account-{account_idx}"] = generate_large_history_data(3600)
        return histories
    
    return analyzer.analyze_function(store_history, "Monitoring History Storage")


def test_json_serialization_memory() -> MemoryUsageAnalysis:
    """测试 JSON 序列化的内存使用"""
    analyzer = MemoryAnalyzer()
    
    data = {
        "accounts": [generate_mock_ssh_account().model_dump() for _ in range(100)],
        "history": [
            {
                "timestamp": time.time(),
                "data": [random.random() for _ in range(100)]
            }
            for _ in range(1000)
        ]
    }
    
    def serialize_data():
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        return parsed
    
    return analyzer.analyze_function(serialize_data, "JSON Serialization")


def test_large_data_processing_memory() -> MemoryUsageAnalysis:
    """测试大数据处理的内存使用"""
    analyzer = MemoryAnalyzer()
    
    def process_large_data():
        # 生成大量数据并进行处理
        large_dataset = []
        for i in range(100000):
            large_dataset.append({
                "id": i,
                "value": random.random(),
                "name": generate_random_string(20),
                "tags": [generate_random_string(5) for _ in range(10)]
            })
        
        # 进行一些处理操作
        processed = [
            item for item in large_dataset if item["value"] > 0.5
        ]
        return processed
    
    return analyzer.analyze_function(process_large_data, "Large Data Processing")


def format_bytes(size: int) -> str:
    """格式化字节大小为可读格式"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def run_memory_analysis():
    """运行完整的内存分析"""
    print("=" * 70)
    print("OpsV-Kits 项目内存使用分析")
    print("=" * 70)
    
    analyses: List[MemoryUsageAnalysis] = []
    
    # 运行所有内存测试
    print("\n[1/6] 测试 SSH 账户创建内存使用...")
    analyses.append(test_ssh_account_creation_memory())
    
    print("\n[2/6] 测试账户分组管理内存使用...")
    analyses.append(test_account_group_management_memory())
    
    print("\n[3/6] 测试审计日志存储内存使用...")
    analyses.append(test_audit_log_memory())
    
    print("\n[4/6] 测试监控历史数据存储内存使用...")
    analyses.append(test_monitoring_history_memory())
    
    print("\n[5/6] 测试 JSON 序列化内存使用...")
    analyses.append(test_json_serialization_memory())
    
    print("\n[6/6] 测试大数据处理内存使用...")
    analyses.append(test_large_data_processing_memory())
    
    # 生成报告
    print("\n" + "=" * 70)
    print("内存分析结果报告")
    print("=" * 70)
    
    for analysis in analyses:
        print(f"\n{analysis.module_name}:")
        print(f"  基础内存: {format_bytes(analysis.base_memory)}")
        print(f"  峰值内存: {format_bytes(analysis.peak_memory)}")
        print(f"  内存增量: {format_bytes(analysis.memory_increase)}")
        print(f"  分配数: {analysis.allocations}")
        
        # 打印最大内存使用者
        if analysis.top_allocations:
            print(f"  主要分配源:")
            for i, alloc in enumerate(analysis.top_allocations[:3]):
                print(f"    [{i+1}] {format_bytes(alloc['size'])} ({alloc['count']} allocations)")
    
    # 总体评估
    print("\n" + "=" * 70)
    print("总体内存使用评估")
    print("=" * 70)
    
    total_peak_memory = sum(a.peak_memory for a in analyses)
    avg_increase = sum(a.memory_increase for a in analyses) / len(analyses)
    
    print(f"\n总峰值内存（所有测试）: {format_bytes(total_peak_memory)}")
    print(f"平均内存增量: {format_bytes(avg_increase)}")
    
    # 识别最高内存使用
    sorted_analyses = sorted(analyses, key=lambda x: x.memory_increase, reverse=True)
    print(f"\n最高内存使用模块:")
    for i, analysis in enumerate(sorted_analyses[:3]):
        print(f"  [{i+1}] {analysis.module_name}: {format_bytes(analysis.memory_increase)}")
    
    # 内存优化建议
    print("\n" + "=" * 70)
    print("内存优化建议")
    print("=" * 70)
    print("\n1. 监控数据存储:")
    print("   - 当前保留 3600 条历史数据（约 1 小时）")
    print("   - 考虑实现数据聚合或滚动窗口机制")
    print("   - 对长时间历史数据考虑采样或压缩")
    print("\n2. 审计日志:")
    print("   - 建议实现日志滚动或持久化到数据库/文件")
    print("   - 避免内存中保留过多日志")
    print("\n3. SSH 连接池:")
    print("   - 限制最大连接数，避免连接泄漏")
    print("   - 考虑连接超时和空闲连接清理机制")
    print("\n4. JSON 处理:")
    print("   - 对于大 JSON 使用流式处理")
    print("   - 考虑使用更高效的序列化库如 ujson 或 orjson")
    print("\n5. 数据结构优化:")
    print("   - 使用更紧凑的数据结构（如 NamedTuple 或 dataclass）")
    print("   - 考虑使用数组替代列表存储数值型数据")
    print("   - 对于大规模数据考虑使用 numpy 或 pandas")


if __name__ == "__main__":
    try:
        run_memory_analysis()
    except KeyboardInterrupt:
        print("\n分析被用户中断")
    except Exception as e:
        print(f"\n分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

