import time
from collections import deque
from unittest.mock import MagicMock, patch

import pytest

from app.services.process_service import DEFAULT_ALERT_CONFIG, SIGNAL_MAP, STATUS_MAP, ProcessService


@pytest.fixture
def service():
    svc = ProcessService()
    svc._anomaly_history.clear()
    svc._process_cache.clear()
    return svc


class TestSignalMap:
    def test_supported_signals(self):
        assert SIGNAL_MAP["SIGTERM"] == 15
        assert SIGNAL_MAP["SIGKILL"] == 9
        assert SIGNAL_MAP["SIGHUP"] == 1
        assert SIGNAL_MAP["SIGSTOP"] == 19
        assert SIGNAL_MAP["SIGCONT"] == 18


class TestStatusMap:
    def test_status_mapping(self):
        assert STATUS_MAP["R"] == "running"
        assert STATUS_MAP["S"] == "sleeping"
        assert STATUS_MAP["Z"] == "zombie"
        assert STATUS_MAP["T"] == "stopped"
        assert STATUS_MAP["X"] == "dead"


class TestKillProcess:
    def test_kill_success(self, service):
        with patch.object(service, "_exec", return_value=(0, "", "")):
            result = service.kill_process(1234, "SIGTERM", "test")
            assert result["success"] is True
            assert "SIGTERM" in result["message"]

    def test_kill_unsupported_signal(self, service):
        result = service.kill_process(1234, "SIGFOO", "test")
        assert result["success"] is False
        assert "不支持" in result["message"]

    def test_kill_failure(self, service):
        with patch.object(service, "_exec", return_value=(1, "", "no such process")):
            result = service.kill_process(1234, "SIGTERM", "test")
            assert result["success"] is False

    def test_kill_exception(self, service):
        with patch.object(service, "_exec", side_effect=Exception("conn fail")):
            result = service.kill_process(1234, "SIGTERM", "test")
            assert result["success"] is False


class TestSetNice:
    def test_set_nice_success(self, service):
        with patch.object(service, "_exec", return_value=(0, "OK", "")):
            result = service.set_nice(1234, 10, "test")
            assert result["success"] is True

    def test_set_nice_invalid_low(self, service):
        result = service.set_nice(1234, -21, "test")
        assert result["success"] is False
        assert "-20" in result["message"]

    def test_set_nice_invalid_high(self, service):
        result = service.set_nice(1234, 20, "test")
        assert result["success"] is False

    def test_set_nice_failure(self, service):
        with patch.object(service, "_exec", return_value=(1, "", "error")):
            result = service.set_nice(1234, 10, "test")
            assert result["success"] is False

    def test_set_nice_exception(self, service):
        with patch.object(service, "_exec", side_effect=Exception("fail")):
            result = service.set_nice(1234, 10, "test")
            assert result["success"] is False


class TestBatchKill:
    def test_batch_kill(self, service):
        with patch.object(service, "kill_process", return_value={"success": True, "message": "ok"}):
            results = service.batch_kill([1, 2, 3], "SIGTERM", "test")
            assert len(results) == 3
            assert all(r["success"] for r in results)


class TestGetAllProcesses:
    def test_get_all_processes_cached(self, service):
        cached_procs = [{"pid": 1, "name": "init"}]
        service._process_cache["test"] = (cached_procs, time.time())
        result = service.get_all_processes("test")
        assert result == cached_procs

    def test_get_all_processes_expired_cache(self, service):
        cached_procs = [{"pid": 1}]
        service._process_cache["test"] = (cached_procs, time.time() - 2)
        with patch.object(service, "_exec", return_value=(1, "", "error")):
            result = service.get_all_processes("test")
            assert result == []

    def test_get_all_processes_parse_output(self, service):
        ps_output = (
            "1 0 root 0.0 0.1 1000 500 ? Ss 10:00 00:00 1 init---ARGS---\n"
            "1 /sbin/init\n"
            "---CWD---\n"
            "1:/\n"
        )
        with patch.object(service, "_exec", return_value=(0, ps_output, "")):
            result = service.get_all_processes("test")
            assert len(result) == 1
            assert result[0]["pid"] == 1
            assert result[0]["name"] == "init"

    def test_get_all_processes_failure(self, service):
        with patch.object(service, "_exec", return_value=(1, "", "error")):
            result = service.get_all_processes("test")
            assert result == []


class TestDetectAnomalies:
    def test_detect_zombie(self, service):
        procs = [{"pid": 1, "cpu_percent": 0, "mem_percent": 0, "status": "zombie"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 5})
            assert 1 in result["zombies"]

    def test_detect_high_cpu(self, service):
        procs = [{"pid": 1, "cpu_percent": 95, "mem_percent": 0, "status": "running"}]
        history = service._anomaly_history["test"]
        history[1] = deque([time.time() - 10])
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 5})
            assert len(result["high_cpu"]) == 1

    def test_detect_high_mem(self, service):
        procs = [{"pid": 1, "cpu_percent": 0, "mem_percent": 95, "status": "running"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 0})
            assert len(result["high_mem"]) == 1

    def test_detect_no_anomalies(self, service):
        procs = [{"pid": 1, "cpu_percent": 10, "mem_percent": 20, "status": "running"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 5})
            assert result["total_anomalies"] == 0

    def test_detect_recovers_clears_history(self, service):
        procs = [{"pid": 1, "cpu_percent": 10, "mem_percent": 20, "status": "running"}]
        history = service._anomaly_history["test"]
        history[1] = deque([time.time() - 10])
        with patch.object(service, "get_all_processes", return_value=procs):
            service.detect_anomalies("test", {"cpu_threshold": 90, "mem_threshold": 80, "duration_seconds": 5})
            assert 1 not in history

    def test_detect_default_thresholds(self, service):
        procs = [{"pid": 1, "cpu_percent": 0, "mem_percent": 0, "status": "running"}]
        with patch.object(service, "get_all_processes", return_value=procs):
            result = service.detect_anomalies("test", {})
            assert result["total_anomalies"] == 0


class TestSystemdService:
    def test_is_systemd_service_from_cgroup(self, service):
        cgroup_output = "1:name=systemd:/system.slice/nginx.service\n"
        with patch.object(service, "_exec", return_value=(0, cgroup_output, "")):
            result = service.is_systemd_service(1234, "test")
            assert result["is_service"] is True
            assert result["service_name"] == "nginx"

    def test_is_systemd_service_from_systemctl(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "1:name=systemd:/user.slice\n", ""),
            (0, "nginx.service  nginx  running  1234\n", ""),
        ]):
            result = service.is_systemd_service(1234, "test")
            assert result["is_service"] is True

    def test_is_not_systemd_service(self, service):
        with patch.object(service, "_exec", side_effect=[
            (0, "1:name=systemd:/user.slice\n", ""),
            (0, "", ""),
        ]):
            result = service.is_systemd_service(1234, "test")
            assert result["is_service"] is False

    def test_is_systemd_service_exception(self, service):
        with patch.object(service, "_exec", side_effect=Exception("fail")):
            result = service.is_systemd_service(1234, "test")
            assert result["is_service"] is False


class TestServiceControl:
    def test_service_start(self, service):
        with patch.object(service, "_exec", return_value=(0, "started", "")):
            result = service.service_control("nginx", "start", "test")
            assert result["success"] is True

    def test_service_stop(self, service):
        with patch.object(service, "_exec", return_value=(0, "stopped", "")):
            result = service.service_control("nginx", "stop", "test")
            assert result["success"] is True

    def test_service_restart(self, service):
        with patch.object(service, "_exec", return_value=(0, "restarted", "")):
            result = service.service_control("nginx", "restart", "test")
            assert result["success"] is True

    def test_service_unsupported_action(self, service):
        result = service.service_control("nginx", "explode", "test")
        assert result["success"] is False
        assert "不支持" in result["message"]

    def test_service_empty_name(self, service):
        result = service.service_control(";", "start", "test")
        assert "不能为空" in result.get("message", "") or result["success"] is False

    def test_service_failure(self, service):
        with patch.object(service, "_exec", return_value=(1, "failed", "")):
            result = service.service_control("nginx", "start", "test")
            assert result["success"] is False

    def test_service_exception(self, service):
        with patch.object(service, "_exec", side_effect=Exception("fail")):
            result = service.service_control("nginx", "start", "test")
            assert result["success"] is False


class TestAlertConfig:
    def test_get_alert_config_default(self, service):
        with patch("app.services.settings_service.settings_service") as mock_settings:
            mock_settings.get.return_value = None
            config = service.get_alert_config("test")
            assert config == DEFAULT_ALERT_CONFIG

    def test_get_alert_config_custom(self, service):
        with patch("app.services.settings_service.settings_service") as mock_settings:
            mock_settings.get.return_value = {"cpu_threshold": 95.0}
            config = service.get_alert_config("test")
            assert config["cpu_threshold"] == 95.0

    def test_save_alert_config(self, service):
        with patch("app.services.settings_service.settings_service") as mock_settings:
            result = service.save_alert_config("test", {"cpu_threshold": 95.0})
            assert result is True
            mock_settings.set.assert_called_once()

    def test_save_alert_config_failure(self, service):
        with patch("app.services.settings_service.settings_service") as mock_settings:
            mock_settings.set.side_effect = Exception("fail")
            result = service.save_alert_config("test", {"cpu_threshold": 95.0})
            assert result is False


class TestSubscribe:
    def test_subscribe(self, service):
        ws = MagicMock()
        service.subscribe("test", ws)
        assert ws in service._stream_subscribers["test"]

    def test_unsubscribe(self, service):
        ws = MagicMock()
        service.subscribe("test", ws)
        service.unsubscribe("test", ws)
        assert ws not in service._stream_subscribers["test"]


class TestConn:
    def test_conn_nonexistent_account(self, service):
        with patch("app.services.process_service.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                service._conn("nonexistent")
