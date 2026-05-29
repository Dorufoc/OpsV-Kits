import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.monitor_service import MonitorService


class TestDockerContainerMetrics:
    """测试 Docker 容器指标解析"""

    def test_parse_bytes_gib(self):
        """测试 GiB 单位解析"""
        service = MonitorService()
        
        mock_stdout = json.dumps({
            "Name": "test-container",
            "Container": "abc123def456",
            "CPUPerc": "15.50%",
            "MemPerc": "25.30%",
            "MemUsage": "1.5GiB / 8GiB",
            "NetIO": "100MiB / 50MiB",
            "BlockIO": "1.2GiB / 800MiB",
            "PIDs": "5",
        })
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            
            assert len(result) == 1
            container = result[0]
            
            assert container['name'] == 'test-container'
            assert container['container_id'] == 'abc123def456'
            assert container['cpu_percent'] == 15.50
            assert container['mem_percent'] == 25.30
            
            # 验证内存解析: 1.5GiB = 1.5 * 1024^3 = 1610612736
            assert container['mem_used'] == pytest.approx(1.5 * 1024**3, rel=0.01)
            # 验证内存限制: 8GiB = 8 * 1024^3 = 8589934592
            assert container['mem_total'] == pytest.approx(8 * 1024**3, rel=0.01)
            
            # 验证网络: 100MiB = 100 * 1024^2
            assert container['net_rx'] == pytest.approx(100 * 1024**2, rel=0.01)
            assert container['net_tx'] == pytest.approx(50 * 1024**2, rel=0.01)
            
            # 验证块 IO
            assert container['block_read'] == pytest.approx(1.2 * 1024**3, rel=0.01)
            assert container['block_write'] == pytest.approx(800 * 1024**2, rel=0.01)
            
            assert container['pids'] == 5

    def test_parse_bytes_gb(self):
        """测试 GB 单位解析"""
        service = MonitorService()
        
        mock_stdout = json.dumps({
            "Name": "test-container",
            "Container": "abc123",
            "CPUPerc": "10%",
            "MemPerc": "50%",
            "MemUsage": "2GB / 4GB",
            "NetIO": "500MB / 250MB",
            "BlockIO": "1GB / 500MB",
            "PIDs": "3",
        })
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            
            assert len(result) == 1
            container = result[0]
            
            assert container['mem_used'] == pytest.approx(2 * 1024**3, rel=0.01)
            assert container['mem_total'] == pytest.approx(4 * 1024**3, rel=0.01)
            assert container['net_rx'] == pytest.approx(500 * 1024**2, rel=0.01)
            assert container['net_tx'] == pytest.approx(250 * 1024**2, rel=0.01)

    def test_parse_bytes_kib(self):
        """测试 KiB 单位解析"""
        service = MonitorService()
        
        mock_stdout = json.dumps({
            "Name": "test-container",
            "Container": "abc123",
            "CPUPerc": "5%",
            "MemPerc": "10%",
            "MemUsage": "512KiB / 1MiB",
            "NetIO": "100KiB / 50KiB",
            "BlockIO": "200KiB / 100KiB",
            "PIDs": "1",
        })
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            
            assert len(result) == 1
            container = result[0]
            
            assert container['mem_used'] == pytest.approx(512 * 1024, rel=0.01)
            assert container['mem_total'] == pytest.approx(1 * 1024**2, rel=0.01)

    def test_parse_bytes_multiple_containers(self):
        """测试多容器输出解析"""
        service = MonitorService()
        
        mock_stdout = (
            '{"Name": "container1", "Container": "aaa111", "CPUPerc": "10%", "MemPerc": "20%", '
            '"MemUsage": "512MiB / 2GiB", "NetIO": "10MiB / 5MiB", "BlockIO": "100MiB / 50MiB", "PIDs": "2"}\n'
            '{"Name": "container2", "Container": "bbb222", "CPUPerc": "30%", "MemPerc": "40%", '
            '"MemUsage": "1GiB / 4GiB", "NetIO": "20MiB / 10MiB", "BlockIO": "200MiB / 100MiB", "PIDs": "4"}'
        )
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            
            assert len(result) == 2
            
            assert result[0]['name'] == 'container1'
            assert result[0]['cpu_percent'] == 10
            assert result[0]['mem_percent'] == 20
            assert result[0]['mem_used'] == pytest.approx(512 * 1024**2, rel=0.01)
            assert result[0]['mem_total'] == pytest.approx(2 * 1024**3, rel=0.01)
            
            assert result[1]['name'] == 'container2'
            assert result[1]['cpu_percent'] == 30
            assert result[1]['mem_percent'] == 40
            assert result[1]['mem_used'] == pytest.approx(1 * 1024**3, rel=0.01)
            assert result[1]['mem_total'] == pytest.approx(4 * 1024**3, rel=0.01)

    def test_parse_empty_output(self):
        """测试空输出"""
        service = MonitorService()
        
        with patch.object(service, '_exec', return_value=(0, '', '')):
            result = service.get_docker_container_metrics('test-alias')
            assert result == []

    def test_parse_invalid_json(self):
        """测试无效 JSON 输出"""
        service = MonitorService()
        
        mock_stdout = "not valid json\n"
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            assert result == []

    def test_parse_leading_slash_in_name(self):
        """测试容器名前导斜杠去除"""
        service = MonitorService()
        
        mock_stdout = json.dumps({
            "Name": "/my-container",
            "Container": "abc123",
            "CPUPerc": "0%",
            "MemPerc": "0%",
            "MemUsage": "0B / 0B",
            "NetIO": "0B / 0B",
            "BlockIO": "0B / 0B",
            "PIDs": "0",
        })
        
        with patch.object(service, '_exec', return_value=(0, mock_stdout, '')):
            result = service.get_docker_container_metrics('test-alias')
            assert result[0]['name'] == 'my-container'
