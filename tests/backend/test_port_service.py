from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.services.port_service import PortService


@pytest.fixture
def svc():
    return PortService()


class TestExtractPort:
    def test_ipv4_with_port(self):
        assert PortService._extract_port("127.0.0.1:8080") == 8080

    def test_ipv4_wildcard(self):
        assert PortService._extract_port("0.0.0.0:80") == 80

    def test_ipv6_with_brackets(self):
        assert PortService._extract_port("[::1]:8080") == 8080

    def test_ipv6_wildcard_with_brackets(self):
        assert PortService._extract_port("[::]:443") == 443

    def test_ipv6_without_brackets(self):
        assert PortService._extract_port(":::8080") == 8080

    def test_asterisk_port(self):
        assert PortService._extract_port("*:3000") == 3000

    def test_no_port(self):
        assert PortService._extract_port("nocolon") is None

    def test_invalid_port_negative(self):
        assert PortService._extract_port("127.0.0.1:-1") is None

    def test_invalid_port_zero(self):
        assert PortService._extract_port("127.0.0.1:0") is None

    def test_invalid_port_too_large(self):
        assert PortService._extract_port("127.0.0.1:70000") is None

    def test_ipv6_brackets_no_port(self):
        assert PortService._extract_port("[::1]") is None

    def test_ipv6_brackets_empty_after(self):
        assert PortService._extract_port("[::1]:") is None

    def test_ipv6_multiple_colons(self):
        assert PortService._extract_port("fe80::1%eth0:9090") == 9090


class TestMapTcpState:
    def test_listen(self):
        assert PortService._map_tcp_state("LISTEN", "TCP") == "LISTEN"

    def test_listening(self):
        assert PortService._map_tcp_state("LISTENING", "TCP") == "LISTEN"

    def test_established(self):
        assert PortService._map_tcp_state("ESTABLISHED", "TCP") == "ESTABLISHED"

    def test_estab(self):
        assert PortService._map_tcp_state("ESTAB", "TCP") == "ESTABLISHED"

    def test_time_wait(self):
        assert PortService._map_tcp_state("TIME_WAIT", "TCP") == "TIME_WAIT"

    def test_close_wait(self):
        assert PortService._map_tcp_state("CLOSE_WAIT", "TCP") == "CLOSE_WAIT"

    def test_closed(self):
        assert PortService._map_tcp_state("CLOSED", "TCP") == "CLOSED"

    def test_close(self):
        assert PortService._map_tcp_state("CLOSE", "TCP") == "CLOSED"

    def test_fin_wait1(self):
        assert PortService._map_tcp_state("FIN_WAIT1", "TCP") == "FIN_WAIT"

    def test_fin_wait2(self):
        assert PortService._map_tcp_state("FIN_WAIT2", "TCP") == "FIN_WAIT"

    def test_syn_sent(self):
        assert PortService._map_tcp_state("SYN_SENT", "TCP") == "SYN_SENT"

    def test_syn_recv(self):
        assert PortService._map_tcp_state("SYN_RECV", "TCP") == "SYN_RECV"

    def test_last_ack(self):
        assert PortService._map_tcp_state("LAST_ACK", "TCP") == "LAST_ACK"

    def test_closing(self):
        assert PortService._map_tcp_state("CLOSING", "TCP") == "CLOSING"

    def test_unknown_state(self):
        assert PortService._map_tcp_state("UNKNOWN_STATE", "TCP") == "UNKNOWN_STATE"

    def test_udp_empty_state(self):
        assert PortService._map_tcp_state("", "UDP") == ""

    def test_empty_state_tcp(self):
        assert PortService._map_tcp_state("", "TCP") == ""

    def test_case_insensitive(self):
        assert PortService._map_tcp_state("listen", "TCP") == "LISTEN"


class TestParseSsProcess:
    def test_with_pid_and_name(self):
        parts = ["tcp", "LISTEN", "0", "128", "*:80", "users:((\"nginx\",pid=1234,fd=6))"]
        pid, name = PortService._parse_ss_process(parts)
        assert pid == 1234
        assert name == "nginx"

    def test_no_pid(self):
        parts = ["tcp", "LISTEN", "0", "128", "*:80"]
        pid, name = PortService._parse_ss_process(parts)
        assert pid == 0
        assert name == "unknown"

    def test_pid_only(self):
        parts = ["tcp", "LISTEN", "0", "128", "*:80", "pid=5678"]
        pid, name = PortService._parse_ss_process(parts)
        assert pid == 5678
        assert name == "unknown"


class TestGetPortsWindows:
    def test_parse_netstat_output(self, svc):
        output = (
            "Active Connections\n\n"
            "  Proto  Local Address          Foreign Address        State           PID\n"
            "  TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       1234\n"
            "  TCP    127.0.0.1:3306         127.0.0.1:54321        ESTABLISHED     5678\n"
            "  UDP    0.0.0.0:53             *:*                    9012\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = output
        mock_result.returncode = 0

        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result), \
             patch.object(svc, "_get_process_name", return_value="test_proc"):
            ports = svc.get_port_list()
        tcp_ports = [p for p in ports if p["protocol"] == "TCP"]
        assert len(tcp_ports) == 2

    def test_netstat_failure(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", side_effect=Exception("netstat failed")):
            ports = svc._get_ports_windows()
        assert ports == []

    def test_skip_non_tcp_udp(self, svc):
        output = "  ICMP   something   something   something   1234\n"
        mock_result = MagicMock()
        mock_result.stdout = output
        with patch("app.services.port_service.subprocess.run", return_value=mock_result):
            ports = svc._get_ports_windows()
        assert ports == []

    def test_skip_non_numeric_pid(self, svc):
        output = "  TCP    0.0.0.0:80    0.0.0.0:0    LISTENING    abc\n"
        mock_result = MagicMock()
        mock_result.stdout = output
        with patch("app.services.port_service.subprocess.run", return_value=mock_result):
            ports = svc._get_ports_windows()
        assert ports == []

    def test_skip_no_port(self, svc):
        output = "  TCP    nocolon    0.0.0.0:0    LISTENING    1234\n"
        mock_result = MagicMock()
        mock_result.stdout = output
        with patch("app.services.port_service.subprocess.run", return_value=mock_result):
            ports = svc._get_ports_windows()
        assert ports == []


class TestGetPortsUnix:
    def test_ss_success(self, svc):
        ss_output = (
            "Netid State  Recv-Q Send-Q Local Address:Port  Peer Address:Port  Process\n"
            "tcp   LISTEN 0      128    *:80               *:*                users:((\"nginx\",pid=1234,fd=6))\n"
            "udp   UNCONN 0      0      *:53               *:*                users:((\"dns\",pid=5678,fd=5))\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = ss_output
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result):
            ports = svc._try_ss()
        assert len(ports) == 2

    def test_ss_file_not_found(self, svc):
        with patch("app.services.port_service.subprocess.run", side_effect=FileNotFoundError):
            ports = svc._try_ss()
        assert ports == []

    def test_ss_exception(self, svc):
        with patch("app.services.port_service.subprocess.run", side_effect=Exception("error")):
            ports = svc._try_ss()
        assert ports == []

    def test_lsof_success(self, svc):
        lsof_output = (
            "COMMAND   PID  USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
            "nginx    1234  root   6u  IPv4  12345      0t0  TCP *:80 (LISTEN)\n"
            "named    5678  bind  20u  IPv4  67890      0t0  UDP *:53\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = lsof_output
        with patch("app.services.port_service.subprocess.run", return_value=mock_result):
            ports = svc._try_lsof()
        assert len(ports) == 2

    def test_lsof_file_not_found(self, svc):
        with patch("app.services.port_service.subprocess.run", side_effect=FileNotFoundError):
            ports = svc._try_lsof()
        assert ports == []

    def test_lsof_exception(self, svc):
        with patch("app.services.port_service.subprocess.run", side_effect=Exception("error")):
            ports = svc._try_lsof()
        assert ports == []

    def test_unix_fallback_to_lsof(self, svc):
        ss_output = ""
        lsof_output = (
            "COMMAND   PID  USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\n"
            "nginx    1234  root   6u  IPv4  12345      0t0  TCP *:80 (LISTEN)\n"
        )
        ss_result = MagicMock()
        ss_result.stdout = ss_output
        lsof_result = MagicMock()
        lsof_result.stdout = lsof_output
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("app.services.port_service.subprocess.run", side_effect=[ss_result, lsof_result]):
            ports = svc._get_ports_unix()
        assert len(ports) == 1


class TestCheckPort:
    def test_port_occupied(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
            {"protocol": "TCP", "port": 443, "local_address": "0.0.0.0:443", "pid": 5678, "process_name": "apache", "status": "LISTEN"},
        ]
        with patch.object(svc, "get_port_list", return_value=mock_ports):
            result = svc.check_port(80)
        assert result["occupied"] is True
        assert len(result["details"]) == 1

    def test_port_not_occupied(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
        ]
        with patch.object(svc, "get_port_list", return_value=mock_ports):
            result = svc.check_port(8080)
        assert result["occupied"] is False
        assert result["details"] == []


class TestKillByPort:
    def test_kill_occupied_port(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
        ]
        with patch.object(svc, "check_port", return_value={"occupied": True, "details": mock_ports}), \
             patch.object(svc, "_kill_process", return_value={"success": True, "message": "已终止"}):
            result = svc.kill_by_port(80)
        assert result["success"] is True
        assert len(result["killed"]) == 1

    def test_kill_not_occupied_port(self, svc):
        with patch.object(svc, "check_port", return_value={"occupied": False, "details": []}):
            result = svc.kill_by_port(8080)
        assert result["success"] is False
        assert "未被占用" in result["message"]

    def test_kill_all_failed(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
        ]
        with patch.object(svc, "check_port", return_value={"occupied": True, "details": mock_ports}), \
             patch.object(svc, "_kill_process", return_value={"success": False, "message": "拒绝访问"}):
            result = svc.kill_by_port(80)
        assert result["success"] is False
        assert len(result["failed"]) == 1

    def test_kill_partial_success(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 5678, "process_name": "apache", "status": "LISTEN"},
        ]
        kill_results = [
            {"success": True, "message": "已终止"},
            {"success": False, "message": "拒绝访问"},
        ]
        with patch.object(svc, "check_port", return_value={"occupied": True, "details": mock_ports}), \
             patch.object(svc, "_kill_process", side_effect=kill_results):
            result = svc.kill_by_port(80)
        assert result["success"] is True
        assert len(result["killed"]) == 1
        assert len(result["failed"]) == 1

    def test_kill_by_port_force(self, svc):
        mock_ports = [
            {"protocol": "TCP", "port": 80, "local_address": "0.0.0.0:80", "pid": 1234, "process_name": "nginx", "status": "LISTEN"},
        ]
        with patch.object(svc, "check_port", return_value={"occupied": True, "details": mock_ports}), \
             patch.object(svc, "_kill_process", return_value={"success": True, "message": "已终止"}) as mock_kill:
            result = svc.kill_by_port(80, force=True)
        mock_kill.assert_called_once_with(1234, True)


class TestKillByPid:
    def test_kill_by_pid_success(self, svc):
        with patch.object(svc, "_get_process_name", return_value="nginx"), \
             patch.object(svc, "_kill_process", return_value={"success": True, "message": "已终止"}):
            result = svc.kill_by_pid(1234)
        assert result["success"] is True
        assert result["process_name"] == "nginx"

    def test_kill_by_pid_failure(self, svc):
        with patch.object(svc, "_get_process_name", return_value="nginx"), \
             patch.object(svc, "_kill_process", return_value={"success": False, "message": "拒绝访问"}):
            result = svc.kill_by_pid(1234)
        assert result["success"] is False
        assert "process_name" not in result

    def test_kill_by_pid_force(self, svc):
        with patch.object(svc, "_get_process_name", return_value="nginx"), \
             patch.object(svc, "_kill_process", return_value={"success": True, "message": "已终止"}) as mock_kill:
            result = svc.kill_by_pid(1234, force=True)
        mock_kill.assert_called_once_with(1234, True)


class TestKillProcess:
    def test_kill_windows_success(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result):
            result = svc._kill_process(1234)
        assert result["success"] is True

    def test_kill_windows_force(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result) as mock_run:
            result = svc._kill_process(1234, force=True)
        args = mock_run.call_args[0][0]
        assert "/F" in args

    def test_kill_windows_no_force(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result) as mock_run:
            result = svc._kill_process(1234, force=False)
        args = mock_run.call_args[0][0]
        assert "/F" not in args

    def test_kill_windows_failure(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Access denied"
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result):
            result = svc._kill_process(1234)
        assert result["success"] is False

    def test_kill_unix_success(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result) as mock_run:
            result = svc._kill_process(1234)
        args = mock_run.call_args[0][0]
        assert "-15" in args

    def test_kill_unix_force(self, svc):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result) as mock_run:
            result = svc._kill_process(1234, force=True)
        args = mock_run.call_args[0][0]
        assert "-9" in args

    def test_kill_exception(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", side_effect=Exception("error")):
            result = svc._kill_process(1234)
        assert result["success"] is False
        assert "error" in result["message"]


class TestGetProcessName:
    def test_windows_success(self, svc):
        output = '"nginx.exe","1234","Services","0","1,234 K"'
        mock_result = MagicMock()
        mock_result.stdout = output
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result):
            name = svc._get_process_name(1234)
        assert name == "nginx.exe"

    def test_windows_empty_output(self, svc):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", return_value=mock_result):
            name = svc._get_process_name(1234)
        assert name == "unknown"

    def test_windows_exception(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Windows"), \
             patch("app.services.port_service.subprocess.run", side_effect=Exception("error")):
            name = svc._get_process_name(1234)
        assert name == "unknown"

    def test_unix_proc_comm(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("builtins.open", MagicMock()):
            mock_file = MagicMock()
            mock_file.read.return_value = "nginx\n"
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=False)
            with patch("builtins.open", return_value=mock_file):
                name = svc._get_process_name(1234)
        assert name == "nginx"

    def test_unix_proc_comm_not_found(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("builtins.open", side_effect=FileNotFoundError):
            mock_result = MagicMock()
            mock_result.stdout = "apache2"
            with patch("app.services.port_service.subprocess.run", return_value=mock_result):
                name = svc._get_process_name(1234)
        assert name == "apache2"

    def test_unix_ps_fallback(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("builtins.open", side_effect=FileNotFoundError):
            mock_result = MagicMock()
            mock_result.stdout = "  myapp  "
            with patch("app.services.port_service.subprocess.run", return_value=mock_result):
                name = svc._get_process_name(1234)
        assert name == "myapp"

    def test_unix_all_fail(self, svc):
        with patch("app.services.port_service.platform.system", return_value="Linux"), \
             patch("builtins.open", side_effect=FileNotFoundError), \
             patch("app.services.port_service.subprocess.run", side_effect=Exception("error")):
            name = svc._get_process_name(1234)
        assert name == "unknown"
