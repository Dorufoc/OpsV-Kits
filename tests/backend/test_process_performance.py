import time
from unittest.mock import patch, MagicMock
import pytest

from app.services.process_service import process_service


@pytest.fixture(autouse=True)
def reset_process_state():
    process_service._anomaly_history.clear()
    process_service._stream_tasks.clear()
    process_service._stream_subscribers.clear()
    process_service._process_cache.clear()
    yield
    process_service._anomaly_history.clear()
    process_service._stream_tasks.clear()
    process_service._stream_subscribers.clear()
    process_service._process_cache.clear()


@pytest.fixture
def mock_ssh_account():
    with patch("app.services.process_service.ssh_account_service") as mock_svc:
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "", "")
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_svc.pool = mock_pool
        yield mock_svc


class TestProcessPerformance:
    def test_process_list_response_time(self, mock_ssh_account):
        call_count = 0
        def fake_exec(alias, cmd, timeout=30.0):
            nonlocal call_count
            call_count += 1
            basic = (
                " 1234     1 root   10.0  5.0 102400 51200 pts/0 S+ 10:00 00:00:01 1 nginx\n"
                " 5678  1234 app     5.0  3.0  51200 25600 ?    R  10:01 00:00:02 2 java"
            )
            args = "1234 nginx: worker\n5678 java -jar app.jar"
            cwd = "1234:/var/www\n5678:/opt/app"
            return (0, f"{basic}\n---ARGS---\n{args}\n---CWD---\n{cwd}", "")

        with patch.object(process_service, "_exec", side_effect=fake_exec):
            start = time.perf_counter()
            result = process_service.get_all_processes("test-alias")
            elapsed = time.perf_counter() - start

            assert len(result) == 2
            assert elapsed < 3.0
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_process_detail_response_time(self, mock_ssh_account):
        call_times = []
        def fake_exec(alias, cmd, timeout=30.0):
            call_times.append((cmd, time.perf_counter()))
            if "ps -eo pid,ppid,user,pcpu,pmem,vsz,rss,tty,stat,start,time,nlwp,comm" in cmd:
                basic = (
                    " 1234     1 root   10.0  5.0 102400 51200 pts/0 S+ 10:00 00:00:01 1 nginx\n"
                    " 5678  1234 app     5.0  3.0  51200 25600 ?    R  10:01 00:00:02 2 java"
                )
                args = "1234 nginx: worker\n5678 java -jar app.jar"
                cwd = "1234:/var/www\n5678:/opt/app"
                return (0, f"{basic}\n---ARGS---\n{args}\n---CWD---\n{cwd}", "")
            if "cat /proc/1234/environ" in cmd:
                return (0, "PATH=/usr/bin\nHOME=/root", "")
            if "ls /proc/1234/fd" in cmd:
                return (0, "10", "")
            if "cat /proc/1234/net/tcp" in cmd:
                return (0, "  sl  local_address rem_address   st tx_queue:rx_queue tr:tm->when retrnsmt   uid  timeout inode\n", "")
            if "cat /proc/1234/cgroup" in cmd:
                return (0, "0::/system.slice/nginx.service", "")
            if "cat /proc/1234/status" in cmd:
                return (
                    0,
                    "Name:\tnginx\nState:\tS (sleeping)\nThreads:\t1\nVmPeak:\t  102400 kB\nVmSize:\t  102400 kB\nVmRSS:\t   51200 kB\nVmSwap:\t       0 kB\n",
                    "",
                )
            if "readlink /proc/1234/cwd" in cmd:
                return (0, "/var/www", "")
            if "ps -p 1234 -o pid,ppid,user,pcpu,pmem,vsz,rss,tty,stat,start,time,nlwp,comm" in cmd:
                return (0, " 1234     1 root   10.0  5.0 102400 51200 pts/0 S+ 10:00 00:00:01 1 nginx", "")
            if "ps -p 1234 -o args" in cmd:
                return (0, "nginx: worker", "")
            return (0, "", "")

        with patch.object(process_service, "_exec", side_effect=fake_exec):
            start = time.perf_counter()
            detail = await process_service.get_process_detail(1234, "test-alias")
            elapsed = time.perf_counter() - start

            assert detail["pid"] == 1234
            assert elapsed < 2.0

            detail_cmd_times = [t for c, t in call_times if "cat /proc/1234/" in c or "readlink /proc/1234/" in c or "ls /proc/1234/" in c]
            assert len(detail_cmd_times) >= 4
            if len(detail_cmd_times) >= 2:
                first = min(detail_cmd_times)
                spread = max(detail_cmd_times) - first
                assert spread < 0.5

    def test_process_list_cache(self, mock_ssh_account):
        call_count = 0
        def fake_exec(alias, cmd, timeout=30.0):
            nonlocal call_count
            call_count += 1
            basic = (
                " 1234     1 root   10.0  5.0 102400 51200 pts/0 S+ 10:00 00:00:01 1 nginx"
            )
            args = "1234 nginx: worker"
            cwd = "1234:/var/www"
            return (0, f"{basic}\n---ARGS---\n{args}\n---CWD---\n{cwd}", "")

        with patch.object(process_service, "_exec", side_effect=fake_exec):
            first = process_service.get_all_processes("test-alias")
            assert call_count == 1

            second = process_service.get_all_processes("test-alias")
            assert call_count == 1
            assert second == first
