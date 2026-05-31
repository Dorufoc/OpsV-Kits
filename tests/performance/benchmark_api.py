"""
API 性能基准测试
使用 Locust 进行 API 负载测试
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from aiohttp import ClientSession


@dataclass
class APIBenchmarkResult:
    """API 性能测试结果"""
    endpoint: str
    method: str
    requests: int
    failures: int
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str]


class APILoadTester:
    """API 负载测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: Dict[str, APIBenchmarkResult] = {}
    
    async def test_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        num_requests: int = 100,
        concurrency: int = 10,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> APIBenchmarkResult:
        """测试单个 API 端点"""
        response_times = []
        failures = 0
        errors = []
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def make_request(session: ClientSession):
            nonlocal failures
            try:
                url = f"{self.base_url}{endpoint}"
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=headers
                ) as response:
                    response_time = time.perf_counter() - start_time
                    if response.status >= 400:
                        failures += 1
                        errors.append(f"HTTP {response.status}")
                    return response_time
            except Exception as e:
                failures += 1
                errors.append(str(e))
                return 0
        
        async with ClientSession() as session:
            tasks = []
            start_time = time.perf_counter()
            
            for _ in range(num_requests):
                task = asyncio.create_task(make_request(session))
                tasks.append(task)
            
            response_times = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.perf_counter() - start_time
            
            # 过滤掉异常结果
            valid_times = [t for t in response_times if isinstance(t, (int, float))]
            
            if not valid_times:
                return APIBenchmarkResult(
                    endpoint=endpoint,
                    method=method,
                    requests=num_requests,
                    failures=num_requests,
                    min_response_time=0,
                    max_response_time=0,
                    avg_response_time=0,
                    median_response_time=0,
                    p95_response_time=0,
                    p99_response_time=0,
                    requests_per_second=0,
                    errors=errors
                )
            
            sorted_times = sorted(valid_times)
            count = len(valid_times)
            
            return APIBenchmarkResult(
                endpoint=endpoint,
                method=method,
                requests=num_requests,
                failures=failures,
                min_response_time=min(sorted_times),
                max_response_time=max(sorted_times),
                avg_response_time=sum(sorted_times) / count,
                median_response_time=sorted_times[count // 2] if count % 2 else (sorted_times[count // 2 - 1] + sorted_times[count // 2]) / 2,
                p95_response_time=sorted_times[int(count * 0.95)] if count > 0 else 0,
                p99_response_time=sorted_times[int(count * 0.99)] if count > 0 else 0,
                requests_per_second=count / total_time if total_time > 0 else 0,
                errors=errors
            )
    
    async def run_benchmark_suite(self, test_endpoints: List[Dict]) -> Dict[str, APIBenchmarkResult]:
        """运行完整的 API 基准测试套件"""
        results = {}
        for test_config in test_endpoints:
            result = await self.test_endpoint(**test_config)
            results[test_config["endpoint"]] = result
        return results


# ==================== Mock API 测试 ====================

class TestMockAPIPerformance:
    """Mock API 性能测试（不依赖真实后端）"""
    
    @pytest.fixture
    def mock_fastapi_app(self):
        """模拟 FastAPI 应用"""
        with patch("app.main.app") as mock_app:
            yield mock_app
    
    def test_mock_health_endpoint(self, profiler):
        """测试健康检查端点性能（模拟）"""
        from app.main import app
        
        # 使用模拟的方式测试内部处理逻辑
        def mock_health_check():
            return {"status": "healthy"}
        
        profiler.profile("api_health_check", mock_health_check)


class TestEndpointPerformance:
    """端点性能测试（使用 pytest-benchmark）"""
    
    def test_json_response_serialization(self, benchmark):
        """测试 JSON 响应序列化性能"""
        from fastapi.responses import JSONResponse
        
        test_data = {
            "status": "success",
            "data": [
                {
                    "id": i,
                    "name": f"Item {i}",
                    "value": i * 1.5,
                    "nested": {
                        "key": f"value_{i}",
                        "list": list(range(10))
                    }
                }
                for i in range(100)
            ],
            "metadata": {
                "total": 100,
                "page": 1,
                "per_page": 100
            }
        }
        
        def create_response():
            return JSONResponse(content=test_data)
        
        benchmark(create_response)
    
    def test_path_parameter_parsing(self, benchmark):
        """测试路径参数解析性能"""
        from fastapi.routing import compile_path
        
        def parse_path():
            pattern, param_convertors, _ = compile_path("/api/{resource}/{id}")
            return pattern, param_convertors
        
        benchmark(parse_path)


class TestWebSocketPerformance:
    """WebSocket 性能测试"""
    
    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, profiler):
        """测试 WebSocket 消息吞吐量"""
        import websockets
        
        # 模拟 WebSocket 消息处理
        async def simulate_message_processing():
            num_messages = 100
            start_time = time.perf_counter()
            
            for _ in range(num_messages):
                # 模拟消息处理
                message = {"type": "data", "content": "test message"}
            
            elapsed = time.perf_counter() - start_time
            return num_messages / elapsed if elapsed > 0 else 0
        
        result = await simulate_message_processing()
        # 记录性能指标
        print(f"WebSocket throughput: {result:.2f} msg/s")


# ==================== 测试端点配置 ====================

TEST_ENDPOINTS = [
    {
        "endpoint": "/api/health",
        "method": "GET",
        "num_requests": 1000,
        "concurrency": 50
    },
    {
        "endpoint": "/api/docker/containers",
        "method": "GET",
        "num_requests": 500,
        "concurrency": 20
    },
    {
        "endpoint": "/api/monitor/snapshot",
        "method": "GET",
        "num_requests": 300,
        "concurrency": 10
    }
]
