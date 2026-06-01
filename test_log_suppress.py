import asyncio
import sys
sys.path.insert(0, 'backend')

from app.services.event_bus_service import EventBusService, _file_watcher_error_counts, _file_watcher_suppressed

# 模拟错误日志输出
def test_error_suppression():
    source_id = "test-source-123"

    print("Testing error suppression logic...")

    # 模拟5次错误
    for i in range(5):
        err_key = source_id
        _file_watcher_error_counts[err_key] = _file_watcher_error_counts.get(err_key, 0) + 1
        err_count = _file_watcher_error_counts[err_key]

        if err_count <=