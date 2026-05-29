import time
import asyncio
import statistics
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from app.services.monitor_service import monitor_service
from app.services.process_service import process_service


@pytest.fixture(autouse=True)
def reset_services():
    monitor_service._history.clear()
    monitor_service._subscribers.clear()
    monitor_service._tasks.clear()
    monitor_service._cache.clear()
    monitor_service._cache_ttl.clear()
    monitor_service._cpu_prev.clear()
    monitor_service._cpu_core_prev.clear()
    monitor_service._disk_io_prev.clear()
    monitor_service._network_prev.clear()
    process_service._anomaly_history.clear()
    process_service._stream_tasks.clear()
    process_service._stream_subscribers.clear()
    process_service._process_cache.clear()
    yield
    monitor_service._history.clear()
    monitor_service._subscribers.clear()
    monitor_service._tasks.clear()
    monitor_service._cache.clear()
    monitor_service._cache_ttl.clear()
    monitor_service._cpu_prev.clear()
    monitor_service._cpu_core_prev.clear()
    monitor_service._disk_io_prev.clear()
    monitor_service._network_prev.clear()
    process_service._anomaly_history.clear()
    process_service._stream_tasks.clear()
    process_service._stream_subscribers.clear()
    process_service._process_cache.clear()


@pytest.fixture
def mock_ssh_account():
    with patch("app.services.monitor_service.ssh_account_service") as mock_svc:
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_svc.pool = mock_pool
        yield mock_svc


@pytest.fixture
def mock_process_ssh_account():
    with patch("app.services.process_service.ssh_account_service") as mock_svc:
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_svc.pool = mock_pool
        yield mock_svc


class TestWebSocketStability:
    @pytest.mark.asyncio
    async def test_monitor_streaming_interval(self, mock_ssh_account):
        timestamps = []
        send_count = 0
        stop_event = asyncio.Event()

        mock_ws = AsyncMock()

        async def capture_send_json(data):
            nonlocal send_count
            send_count += 1
            timestamps.append(time.time())
            if send_count >= 10:
                stop_event.set()
                raise asyncio.CancelledError("stop")

        mock_ws.send_json.side_effect = capture_send_json
        monitor_service.subscribe("test-alias", mock_ws)

        def fake_exec(alias, cmd, timeout=30.0):
            if "cat /proc/stat | head -1" in cmd:
                return (0, "cpu  1000 0 500 8000 0 0 0 0", "")
            if "grep '^cpu[0-9]'" in cmd:
                return (0, "cpu0  1000 0 500 8000\ncpu1  1000 0 500 8000", "")
            if "free -b" in cmd:
                return (0, "Mem:  16384 8192 4096 1024 1024 8192\nSwap: 4096 0 4096", "")
            if "df -B1" in cmd:
                return (0, "/dev/sda1 1000000000 500000000 500000000 50% /", "")
            if "cat /proc/net/dev" in cmd:
                return (0, "  eth0: 1000 10 0 0 0 0 0 0 500 5 0 0 0 0 0 0", "")
            if "cat /proc/loadavg" in cmd:
                return (0, "0.5 0.3 0.1 2/100 1234", "")
            if "ps aux" in cmd:
                return (0, "1234,root,10.0,5.0,nginx", "")
            if "ss -tan" in cmd:
                return (0, "  10 ESTABLISHED", "")
            if "cat /proc/uptime" in cmd:
                return (0, "3600.0 0.0", "")
            if "docker stats" in cmd:
                return (0, "", "")
            if "hostname" in cmd:
                return (0, "testhost", "")
            if "nproc" in cmd:
                return (0, "2", "")
            return (0, "", "")

        with patch.object(monitor_service, "_exec", side_effect=fake_exec):
            monitor_service._cpu_prev.clear()
            monitor_service._cpu_core_prev.clear()
            monitor_service._network_prev.clear()
            monitor_service._disk_io_prev.clear()

            task = asyncio.create_task(monitor_service.start_streaming("test-alias", interval=0.5))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        assert len(timestamps) >= 5
        if len(timestamps) >= 3:
            intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
            variance = statistics.variance(intervals) if len(intervals) > 1 else 0.0
            assert variance < 0.5

    @pytest.mark.asyncio
    async def test_process_streaming_interval(self, mock_process_ssh_account):
        timestamps = []
        send_count = 0
        stop_event = asyncio.Event()

        mock_ws = AsyncMock()

        async def capture_send_json(data):
            nonlocal send_count
            send_count += 1
            timestamps.append(time.time())
            if send_count >= 10:
                stop_event.set()
                raise asyncio.CancelledError("stop")

        mock_ws.send_json.side_effect = capture_send_json
        process_service.subscribe("test-alias", mock_ws)

        def fake_exec(alias, cmd, timeout=30.0):
            basic = (
                " 1234     1 root   10.0  5.0 102400 51200 pts/0 S+ 10:00 00:00:01 1 nginx\n"
                " 5678  1234 app     5.0  3.0  51200 25600 ?    R  10:01 00:00:02 2 java"
            )
            args = "1234 nginx: worker\n5678 java -jar app.jar"
            cwd = "1234:/var/www\n5678:/opt/app"
            return (0, f"{basic}\n---ARGS---\n{args}\n---CWD---\n{cwd}", "")

        with patch.object(process_service, "_exec", side_effect=fake_exec):
            process_service._process_cache.clear()

            task = asyncio.create_task(process_service.start_streaming("test-alias", interval=0.5))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        assert len(timestamps) >= 5
        if len(timestamps) >= 3:
            intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
            variance = statistics.variance(intervals) if len(intervals) > 1 else 0.0
            assert variance < 0.5
