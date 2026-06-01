import asyncio
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.process_service import DEFAULT_ALERT_CONFIG, ProcessService


@pytest.fixture
def service():
    svc = ProcessService()
    svc._anomaly_history.clear()
    svc._process_cache.clear()
    svc._stream_tasks.clear()
    svc._stream_subscribers.clear()
    return svc


class TestExecMethod:
    def test_exec_bytes_stdout(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, b"output", b"err")
        with patch.object(service, "_conn", return_value=mock_conn):
            code, stdout, stderr = service._exec("test", "ls")
            assert code == 0
            assert stdout == "output"
            assert stderr == "err"
            mock_conn.manager.exec_command.assert_called_once_with("ls", timeout=30.0)

    def test_exec_bytes_stderr(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "out", b"error msg")
        with patch.object(service, "_conn", return_value=mock_conn):
            code, stdout, stderr = service._exec("test", "ls")
            assert stderr == "error msg"

    def test_exec_strips_output(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "  output  ", "  err  ")
        with patch.object(service, "_conn", return_value=mock_conn):
            code, stdout, stderr = service._exec("test", "ls")
            assert stdout == "output"
            assert stderr == "err"

    def test_exec_releases_connection(self, service):
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "out", "")
        with patch.object(service, "_conn", return_value=mock_conn), \
             patch("app.services.process_service.ssh_account_service") as mock_pool:
            mock_pool.pool.release_connection.assert_not_called()
            service._exec("test", "ls")
            mock_pool.pool.release_connection.assert_called_once_with(mock_conn)


class TestExecAsync:
    @pytest.mark.asyncio
    async def test_exec_async_delegates(self, service):
        with patch.object(service, "_exec", return_value=(0, "out", "err")) as mock_exec:
            loop = asyncio.get_event_loop()
            result = await service._exec_async("test", "ls", 10.0)
            assert result == (0, "out", "err")


class TestGetAllProcessesNoCwdPart:
    def test_no_cwd_separator(self, service):
        ps_output = (
            "1 0 root 0.0 0.1 1000 500 ? Ss 10:00 00:00 1 init---ARGS---\n"
            "1 /sbin/init\n"
        )
        with patch.object(service, "_exec", return_value=(0, ps_output, "")):
            result = service.get_all_processes("test")
            assert len(result) == 1
            assert result[0]["cwd"] == ""


class TestGetAllProcessesParseError:
    def test_parse_line_too_few_fields(self, service):
        ps_output = (
            "1 0 root 0.0 0.1 1000 500 ? Ss 10:00---ARGS---\n"
            "1 /sbin/init\n"
            "---CWD---\n"
        )
        with patch.object(service, "_exec", return_value=(0, ps_output, "")):
            result = service.get_all_processes("test")
            assert result == []


class TestGetAllProcessesValueError:
    def test_parse_line_value_error(self, service):
        ps_output = (
            "abc 0 root 0.0 0.1 1000 500 ? Ss 10:00 00:00 1 init---ARGS---\n"
            "abc /sbin/init\n"
            "---CWD---\n"
        )
        with patch.object(service, "_exec", return_value=(0, ps_output, "")):
            result = service.get_all_processes("test")
            assert result == []


class TestGetProcessDetailNotFound:
    @pytest.mark.asyncio
    async def test_process_not_found_direct_query(self, service):
        procs = [{"pid": 2, "name": "other"}]
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                (0, "1 0 root 0.0 0.1 1000 500 ? Ss 10:00 00:00 1 init", ""),
                (0, "/sbin/init", ""),
                (0, "VAR1=val1\nVAR2=val2", ""),
                (0, "5", ""),
                (0, "10", ""),
                (0, "1:name=systemd:/\n", ""),
                (0, "Name:\tinit\nState:\tS\nThreads:\t1\n", ""),
                (0, "/", ""),
            ]
            result = await service.get_process_detail(1, "test")
            assert result["pid"] == 1
            assert result["name"] == "init"

    @pytest.mark.asyncio
    async def test_process_not_found_no_output(self, service):
        procs = []
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (1, "", "")
            result = await service.get_process_detail(9999, "test")
            assert "error" in result

    @pytest.mark.asyncio
    async def test_process_not_found_unparseable(self, service):
        procs = []
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (0, "too few fields", "")
            result = await service.get_process_detail(9999, "test")
            assert "error" in result


class TestGetProcessDetailWithBasic:
    @pytest.mark.asyncio
    async def test_detail_with_environ(self, service):
        procs = [{"pid": 1, "name": "init", "ppid": 0, "user": "root",
                  "cpu_percent": 0.0, "mem_percent": 0.1, "vsz": 1000,
                  "rss": 500, "tty": "?", "status": "sleeping",
                  "start_time": "10:00", "cpu_time": "00:00",
                  "thread_count": 1, "command": "/sbin/init", "cwd": ""}]
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                (0, "HOME=/root\nPATH=/usr/bin", ""),
                (0, "10", ""),
                (0, "5", ""),
                (0, "", ""),
                (0, "", ""),
                (0, "/root", ""),
            ]
            result = await service.get_process_detail(1, "test")
            assert result["environ"] == ["HOME=/root", "PATH=/usr/bin"]
            assert result["fd_count"] == 10
            assert result["net_connections"] == 5
            assert result["cwd"] == "/root"

    @pytest.mark.asyncio
    async def test_detail_environ_exception(self, service):
        procs = [{"pid": 1, "name": "init", "ppid": 0, "user": "root",
                  "cpu_percent": 0.0, "mem_percent": 0.1, "vsz": 1000,
                  "rss": 500, "tty": "?", "status": "sleeping",
                  "start_time": "10:00", "cpu_time": "00:00",
                  "thread_count": 1, "command": "/sbin/init", "cwd": ""}]
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                Exception("fail"),
                Exception("fail"),
                Exception("fail"),
                Exception("fail"),
                Exception("fail"),
                Exception("fail"),
            ]
            result = await service.get_process_detail(1, "test")
            assert result["environ"] == []
            assert result["fd_count"] == 0
            assert result["net_connections"] == 0
            assert result["cgroup"] == ""
            assert result["status_file"] == {}
            assert result["cwd"] == ""

    @pytest.mark.asyncio
    async def test_detail_fd_count_not_digit(self, service):
        procs = [{"pid": 1, "name": "init", "ppid": 0, "user": "root",
                  "cpu_percent": 0.0, "mem_percent": 0.1, "vsz": 1000,
                  "rss": 500, "tty": "?", "status": "sleeping",
                  "start_time": "10:00", "cpu_time": "00:00",
                  "thread_count": 1, "command": "/sbin/init", "cwd": ""}]
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                (0, "", ""),
                (0, "abc", ""),
                (0, "xyz", ""),
                (0, "", ""),
                (0, "", ""),
                (0, "", ""),
            ]
            result = await service.get_process_detail(1, "test")
            assert result["fd_count"] == 0
            assert result["net_connections"] == 0

    @pytest.mark.asyncio
    async def test_detail_status_file_parsing(self, service):
        procs = [{"pid": 1, "name": "init", "ppid": 0, "user": "root",
                  "cpu_percent": 0.0, "mem_percent": 0.1, "vsz": 1000,
                  "rss": 500, "tty": "?", "status": "sleeping",
                  "start_time": "10:00", "cpu_time": "00:00",
                  "thread_count": 1, "command": "/sbin/init", "cwd": ""}]
        status_output = "Name:\tinit\nState:\tS (sleeping)\nThreads:\t1\nVmPeak:\t1000 kB\nVmSize:\t800 kB\nVmRSS:\t500 kB\nVmSwap:\t0 kB\nOtherKey:\tignored\n"
        with patch.object(service, "get_all_processes", return_value=procs), \
             patch.object(service, "_exec_async", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                (0, "", ""),
                (0, "0", ""),
                (0, "0", ""),
                (0, "", ""),
                (0, status_output, ""),
                (0, "", ""),
            ]
            result = await service.get_process_detail(1, "test")
            assert "Name" in result["status_file"]
            assert "State" in result["status_file"]
            assert "Threads" in result["status_file"]
            assert "OtherKey" not in result["status_file"]


class TestDetectAnomaliesHighCpuNoHistory:
    def test_high_cpu_no_prior_history(self, service):
        procs = [{"pid": 1, "cpu_percent": 95, "mem_percent": 0, "status": "running"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 0})
            assert len(result["high_cpu"]) == 1


class TestDetectAnomaliesHighMemNoHistory:
    def test_high_mem_no_prior_history(self, service):
        procs = [{"pid": 1, "cpu_percent": 0, "mem_percent": 95, "status": "running"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 0})
            assert len(result["high_mem"]) == 1


class TestDetectAnomaliesMemRecovers:
    def test_mem_recovers_clears_history(self, service):
        procs = [{"pid": 1, "cpu_percent": 0, "mem_percent": 20, "status": "running"}]
        history = service._anomaly_history["test"]
        history[1] = deque([time.time() - 10])
        with patch.object(service, "get_all_processes", return_value=procs):
            service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 5})
            assert 1 not in history


class TestStreaming:
    @pytest.mark.asyncio
    async def test_start_streaming_already_running(self, service):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        service._stream_tasks["test"] = mock_task
        await service.start_streaming("test")
        assert service._stream_tasks["test"] is mock_task

    @pytest.mark.asyncio
    async def test_stop_streaming_no_task(self, service):
        await service.stop_streaming("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_streaming_cancels_task(self, service):
        async def dummy_coro():
            pass

        task = asyncio.create_task(dummy_coro())
        service._stream_tasks["test"] = task
        await service.stop_streaming("test")
        assert task.cancelled() or task.done()
        assert "test" not in service._stream_tasks

    @pytest.mark.asyncio
    async def test_stream_iteration_with_dead_ws(self, service):
        dead_ws = MagicMock()
        dead_ws.send_json.side_effect = Exception("closed")
        service._stream_subscribers["test"].add(dead_ws)

        sleep_count = [0]
        real_sleep = asyncio.sleep

        async def limited_sleep(seconds):
            sleep_count[0] += 1
            if sleep_count[0] >= 1:
                raise asyncio.CancelledError()
            await real_sleep(seconds)

        with patch.object(service, "get_all_processes", return_value=[]), \
             patch("app.services.process_service.asyncio.sleep", side_effect=limited_sleep):
            await service.start_streaming("test", interval=1.0)
            task = service._stream_tasks["test"]
            try:
                await task
            except asyncio.CancelledError:
                pass
        assert dead_ws not in service._stream_subscribers.get("test", set())

    @pytest.mark.asyncio
    async def test_stream_sends_data_to_subscriber(self, service):
        live_ws = MagicMock()
        service._stream_subscribers["test"].add(live_ws)

        sleep_count = [0]
        real_sleep = asyncio.sleep

        async def limited_sleep(seconds):
            sleep_count[0] += 1
            if sleep_count[0] >= 1:
                raise asyncio.CancelledError()
            await real_sleep(seconds)

        with patch.object(service, "get_all_processes", return_value=[{"pid": 1}]), \
             patch("app.services.process_service.asyncio.sleep", side_effect=limited_sleep):
            await service.start_streaming("test", interval=1.0)
            task = service._stream_tasks["test"]
            try:
                await task
            except asyncio.CancelledError:
                pass
        live_ws.send_json.assert_called_once()
        data = live_ws.send_json.call_args[0][0]
        assert data["type"] == "process_stream"
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_stream_exception_continues(self, service):
        live_ws = MagicMock()
        service._stream_subscribers["test"].add(live_ws)

        sleep_count = [0]
        real_sleep = asyncio.sleep
        exec_count = [0]

        def mock_get_processes(alias):
            exec_count[0] += 1
            if exec_count[0] == 1:
                raise Exception("temp fail")
            return [{"pid": 1}]

        async def limited_sleep(seconds):
            sleep_count[0] += 1
            if sleep_count[0] >= 2:
                raise asyncio.CancelledError()
            await real_sleep(seconds)

        with patch.object(service, "get_all_processes", side_effect=mock_get_processes), \
             patch("app.services.process_service.asyncio.sleep", side_effect=limited_sleep):
            await service.start_streaming("test", interval=0.01)
            task = service._stream_tasks["test"]
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestGetAlertConfigNonDict:
    def test_get_alert_config_non_dict(self, service):
        with patch("app.services.settings_service.settings_service") as mock_settings:
            mock_settings.get.return_value = "not a dict"
            config = service.get_alert_config("test")
            assert config == DEFAULT_ALERT_CONFIG
