from unittest.mock import MagicMock, patch

import pytest

from app.core.docker_registry_mirrors import DockerRegistryMirrors, docker_registry_mirrors


@pytest.fixture
def mirrors():
    return DockerRegistryMirrors()


def _mock_ssh_account_service():
    mock_svc = MagicMock()
    account = MagicMock()
    account.alias = "test"
    mock_svc.get_account.return_value = account
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.get_connection.return_value = mock_conn
    mock_svc.pool = mock_pool
    return mock_svc, mock_conn


class TestListPresetMirrors:
    def test_returns_preset_mirrors(self):
        result = DockerRegistryMirrors.list_preset_mirrors()
        assert isinstance(result, dict)
        assert "阿里云" in result
        assert "网易云" in result
        assert "腾讯云" in result
        assert "DaoCloud" in result

    def test_returns_copy(self):
        r1 = DockerRegistryMirrors.list_preset_mirrors()
        r2 = DockerRegistryMirrors.list_preset_mirrors()
        assert r1 == r2
        r1["new"] = "value"
        assert "new" not in r2


class TestGetConnection:
    def test_account_not_found(self, mirrors):
        with patch("app.core.docker_registry_mirrors.ssh_account_service") as mock_svc:
            mock_svc.get_account.return_value = None
            with pytest.raises(ValueError, match="不存在"):
                mirrors._get_connection("missing")

    def test_account_found(self, mirrors):
        with patch("app.core.docker_registry_mirrors.ssh_account_service") as mock_svc:
            account = MagicMock()
            mock_svc.get_account.return_value = account
            mock_conn = MagicMock()
            mock_svc.pool.get_connection.return_value = mock_conn
            result = mirrors._get_connection("test")
            assert result == mock_conn


class TestExecRemote:
    def test_exec_remote_string_output(self, mirrors):
        with patch("app.core.docker_registry_mirrors.ssh_account_service") as mock_svc:
            account = MagicMock()
            mock_svc.get_account.return_value = account
            mock_conn = MagicMock()
            mock_conn.manager.exec_command.return_value = (0, "stdout", "stderr")
            mock_svc.pool.get_connection.return_value = mock_conn

            exit_code, stdout, stderr = mirrors._exec_remote("test", "ls")
            assert exit_code == 0
            assert stdout == "stdout"
            assert stderr == "stderr"
            mock_svc.pool.release_connection.assert_called_once_with(mock_conn)

    def test_exec_remote_bytes_output(self, mirrors):
        with patch("app.core.docker_registry_mirrors.ssh_account_service") as mock_svc:
            account = MagicMock()
            mock_svc.get_account.return_value = account
            mock_conn = MagicMock()
            mock_conn.manager.exec_command.return_value = (0, b"bytes stdout", b"bytes stderr")
            mock_svc.pool.get_connection.return_value = mock_conn

            exit_code, stdout, stderr = mirrors._exec_remote("test", "ls")
            assert stdout == "bytes stdout"
            assert stderr == "bytes stderr"

    def test_exec_remote_releases_connection_on_error(self, mirrors):
        with patch("app.core.docker_registry_mirrors.ssh_account_service") as mock_svc:
            account = MagicMock()
            mock_svc.get_account.return_value = account
            mock_conn = MagicMock()
            mock_conn.manager.exec_command.side_effect = Exception("conn error")
            mock_svc.pool.get_connection.return_value = mock_conn

            with pytest.raises(Exception, match="conn error"):
                mirrors._exec_remote("test", "ls")
            mock_svc.pool.release_connection.assert_called_once_with(mock_conn)


class TestExecRemoteSimple:
    def test_success(self, mirrors):
        with patch.object(mirrors, "_exec_remote", return_value=(0, "ok", "")):
            stdout, stderr = mirrors._exec_remote_simple("test", "ls")
            assert stdout == "ok"
            assert stderr == ""

    def test_nonzero_exit_raises(self, mirrors):
        from app.services.docker_service import DockerCommandError

        with patch.object(mirrors, "_exec_remote", return_value=(1, "", "error msg")):
            with pytest.raises(DockerCommandError, match="error msg"):
                mirrors._exec_remote_simple("test", "bad_cmd")


class TestCheckRegistryMirrors:
    def test_empty_config(self, mirrors):
        with patch.object(mirrors, "_exec_remote", return_value=(0, "{}", "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["exists"] is False
            assert result["mirrors"] == []
            assert result["raw"] == ""

    def test_blank_output(self, mirrors):
        with patch.object(mirrors, "_exec_remote", return_value=(0, "  ", "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["exists"] is False

    def test_valid_config_with_mirrors(self, mirrors):
        import json
        config = json.dumps({"registry-mirrors": ["https://mirror.example.com"]})
        with patch.object(mirrors, "_exec_remote", return_value=(0, config, "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["exists"] is True
            assert result["mirrors"] == ["https://mirror.example.com"]

    def test_invalid_json(self, mirrors):
        with patch.object(mirrors, "_exec_remote", return_value=(0, "not json{", "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["exists"] is True
            assert result["mirrors"] == []
            assert "error" in result

    def test_mirrors_as_string(self, mirrors):
        import json
        config = json.dumps({"registry-mirrors": "https://mirror.example.com"})
        with patch.object(mirrors, "_exec_remote", return_value=(0, config, "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["mirrors"] == ["https://mirror.example.com"]

    def test_mirrors_as_invalid_type(self, mirrors):
        import json
        config = json.dumps({"registry-mirrors": 123})
        with patch.object(mirrors, "_exec_remote", return_value=(0, config, "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["mirrors"] == []

    def test_no_mirrors_key(self, mirrors):
        import json
        config = json.dumps({"other-key": "value"})
        with patch.object(mirrors, "_exec_remote", return_value=(0, config, "")):
            result = mirrors.check_registry_mirrors("test")
            assert result["exists"] is True
            assert result["mirrors"] == []


class TestConfigureRegistryMirror:
    def test_empty_mirror_url_raises(self, mirrors):
        with pytest.raises(ValueError, match="不能为空"):
            mirrors.configure_registry_mirror("test", "")

    def test_non_string_mirror_url_raises(self, mirrors):
        with pytest.raises(ValueError, match="不能为空"):
            mirrors.configure_registry_mirror("test", None)

    def test_invalid_protocol_raises(self, mirrors):
        with pytest.raises(ValueError, match="http://"):
            mirrors.configure_registry_mirror("test", "ftp://mirror.example.com")

    def test_already_configured(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": ["https://mirror.example.com"],
            "exists": True,
        }):
            result = mirrors.configure_registry_mirror("test", "https://mirror.example.com")
            assert result["message"] == "该镜像源已配置"
            assert result["restarted"] is False

    def test_configure_success_with_restart(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": [],
            "exists": True,
        }):
            with patch.object(mirrors, "_exec_remote_simple", return_value=("ok", "")):
                result = mirrors.configure_registry_mirror("test", "https://mirror.example.com")
                assert result["restarted"] is True
                assert "已配置" in result["message"]

    def test_configure_success_restart_fails(self, mirrors):
        from app.services.docker_service import DockerCommandError

        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": [],
            "exists": True,
        }):
            call_count = [0]

            def mock_exec_simple(alias, cmd, timeout=60.0):
                call_count[0] += 1
                if call_count[0] == 1:
                    return ("ok", "")
                raise DockerCommandError("restart failed", 1)

            with patch.object(mirrors, "_exec_remote_simple", side_effect=mock_exec_simple):
                result = mirrors.configure_registry_mirror("test", "https://mirror.example.com")
                assert result["restarted"] is False
                assert "重启失败" in result["message"]

    def test_configure_appends_to_existing(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": ["https://mirror1.example.com"],
            "exists": True,
        }):
            with patch.object(mirrors, "_exec_remote_simple", return_value=("ok", "")):
                result = mirrors.configure_registry_mirror("test", "https://mirror2.example.com")
                assert len(result["mirrors"]) == 2
                assert "https://mirror2.example.com" in result["mirrors"]

    def test_http_protocol_accepted(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": [],
            "exists": True,
        }):
            with patch.object(mirrors, "_exec_remote_simple", return_value=("ok", "")):
                result = mirrors.configure_registry_mirror("test", "http://mirror.example.com")
                assert "已配置" in result["message"]


class TestRemoveRegistryMirror:
    def test_mirror_not_configured(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": [],
            "exists": True,
        }):
            result = mirrors.remove_registry_mirror("test", "https://mirror.example.com")
            assert result["message"] == "该镜像源未配置"
            assert result["restarted"] is False

    def test_remove_success_with_restart(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": ["https://mirror1.example.com", "https://mirror2.example.com"],
            "exists": True,
        }):
            with patch.object(mirrors, "_exec_remote_simple", return_value=("ok", "")):
                result = mirrors.remove_registry_mirror("test", "https://mirror1.example.com")
                assert result["restarted"] is True
                assert "已移除" in result["message"]
                assert len(result["mirrors"]) == 1

    def test_remove_last_mirror_writes_empty_json(self, mirrors):
        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": ["https://mirror.example.com"],
            "exists": True,
        }):
            with patch.object(mirrors, "_exec_remote_simple", return_value=("ok", "")):
                result = mirrors.remove_registry_mirror("test", "https://mirror.example.com")
                assert result["mirrors"] == []

    def test_remove_restart_fails(self, mirrors):
        from app.services.docker_service import DockerCommandError

        with patch.object(mirrors, "check_registry_mirrors", return_value={
            "mirrors": ["https://mirror.example.com"],
            "exists": True,
        }):
            call_count = [0]

            def mock_exec_simple(alias, cmd, timeout=60.0):
                call_count[0] += 1
                if call_count[0] == 1:
                    return ("ok", "")
                raise DockerCommandError("restart failed", 1)

            with patch.object(mirrors, "_exec_remote_simple", side_effect=mock_exec_simple):
                result = mirrors.remove_registry_mirror("test", "https://mirror.example.com")
                assert result["restarted"] is False
                assert "重启失败" in result["message"]


class TestModuleInstance:
    def test_module_instance_exists(self):
        assert docker_registry_mirrors is not None
        assert isinstance(docker_registry_mirrors, DockerRegistryMirrors)
