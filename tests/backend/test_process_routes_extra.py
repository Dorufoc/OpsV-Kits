from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestProcessListValueError:
    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_process_list_value_error(self, mock_ssh, mock_proc, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_proc.get_all_processes.side_effect = ValueError("not found")
        resp = client.get("/api/process/list?alias=srv1")
        assert resp.status_code == 404


class TestProcessDetailValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_process_detail_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        async def _detail(pid, alias):
            raise ValueError("not found")
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.get_process_detail = _detail
            resp = client.get("/api/process/detail?alias=srv1&pid=1234")
            assert resp.status_code == 404


class TestKillProcessValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_kill_process_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.kill_process.side_effect = ValueError("not found")
            resp = client.post("/api/process/kill", json={"alias": "srv1", "pid": 1234, "signal": "SIGTERM"})
            assert resp.status_code == 404


class TestNiceProcessValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_nice_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.set_nice.side_effect = ValueError("not found")
            resp = client.post("/api/process/nice", json={"alias": "srv1", "pid": 1234, "nice_value": 10})
            assert resp.status_code == 404


class TestNiceProcessServerError:
    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_nice_server_error(self, mock_ssh, mock_proc, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_proc.set_nice.side_effect = Exception("SSH error")
        resp = client.post("/api/process/nice", json={"alias": "srv1", "pid": 1234, "nice_value": 10})
        assert resp.status_code == 500


class TestBatchKillValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.batch_kill.side_effect = ValueError("not found")
            resp = client.post("/api/process/batch/kill", json={"alias": "srv1", "pids": [1234], "signal": "SIGTERM"})
            assert resp.status_code == 404


class TestBatchKillServerError:
    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_batch_kill_server_error(self, mock_ssh, mock_proc, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_proc.batch_kill.side_effect = Exception("SSH error")
        resp = client.post("/api/process/batch/kill", json={"alias": "srv1", "pids": [1234], "signal": "SIGTERM"})
        assert resp.status_code == 500


class TestServiceControlValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_control_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.service_control.side_effect = ValueError("not found")
            resp = client.post("/api/process/service/control", json={"alias": "srv1", "service_name": "nginx", "action": "start"})
            assert resp.status_code == 404


class TestServiceControlServerError:
    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_service_control_server_error(self, mock_ssh, mock_proc, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_proc.service_control.side_effect = Exception("SSH error")
        resp = client.post("/api/process/service/control", json={"alias": "srv1", "service_name": "nginx", "action": "start"})
        assert resp.status_code == 500


class TestAlertsValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_alerts_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.get_alert_config.return_value = {"cpu_threshold": 90.0}
            mock_proc.detect_anomalies.side_effect = ValueError("not found")
            resp = client.get("/api/process/alerts?alias=srv1")
            assert resp.status_code == 404


class TestAlertConfigValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_alert_config_get_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.get_alert_config.side_effect = ValueError("not found")
            resp = client.get("/api/process/alert-config?alias=srv1")
            assert resp.status_code == 404


class TestSaveAlertConfigServerError:
    @patch("app.api.routes.process.process_service")
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_server_error(self, mock_ssh, mock_proc, client):
        mock_ssh.get_account.return_value = MagicMock()
        mock_proc.save_alert_config.side_effect = Exception("write failed")
        resp = client.put("/api/process/alert-config", json={"alias": "srv1"})
        assert resp.status_code == 500


class TestSaveAlertConfigValueError:
    @patch("app.api.routes.process.ssh_account_service")
    def test_save_alert_config_value_error(self, mock_ssh, client):
        mock_ssh.get_account.return_value = MagicMock()
        with patch("app.api.routes.process.process_service") as mock_proc:
            mock_proc.save_alert_config.side_effect = ValueError("not found")
            resp = client.put("/api/process/alert-config", json={"alias": "srv1"})
            assert resp.status_code == 404
