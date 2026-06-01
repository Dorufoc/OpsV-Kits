from __future__ import annotations

import base64
import errno
import struct
import time
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.remote_drive_service import (
    RemoteDriveService,
    _DirCache,
    _WebDAVRequestHandler,
    _SilentThreadingHTTPServer,
    _ntlm_type2_challenge,
    _xml_escape,
    _dir_cache,
)


@pytest.fixture
def dir_cache():
    return _DirCache(ttl=2.0)


@pytest.fixture
def service():
    svc = RemoteDriveService()
    yield svc
    svc.stop()


def _make_handler(path="/", headers=None):
    handler = object.__new__(_WebDAVRequestHandler)
    handler.path = path
    handler.headers = MagicMock()
    if headers:
        handler.headers.get = lambda key, default="": headers.get(key, default)
    else:
        handler.headers.get = lambda key, default="": default
    handler.client_address = ("127.0.0.1", 12345)
    handler.request = MagicMock()
    handler.rfile = MagicMock()
    handler.wfile = MagicMock()
    handler.server = MagicMock()
    handler.close_connection = False
    handler._ntlm_authenticated = False
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.log_message = MagicMock()
    return handler


class TestXmlEscape:
    def test_ampersand(self):
        assert _xml_escape("a&b") == "a&amp;b"

    def test_less_than(self):
        assert _xml_escape("a<b") == "a&lt;b"

    def test_greater_than(self):
        assert _xml_escape("a>b") == "a&gt;b"

    def test_double_quote(self):
        assert _xml_escape('a"b') == "a&quot;b"

    def test_combined(self):
        assert _xml_escape('<a>&"b"') == "&lt;a&gt;&amp;&quot;b&quot;"

    def test_empty(self):
        assert _xml_escape("") == ""

    def test_no_special_chars(self):
        assert _xml_escape("hello world") == "hello world"


class TestNtlmType2Challenge:
    def test_returns_base64_string(self):
        result = _ntlm_type2_challenge()
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert decoded[:8] == b"NTLMSSP\x00"

    def test_message_type_2(self):
        result = _ntlm_type2_challenge()
        decoded = base64.b64decode(result)
        msg_type = struct.unpack_from("<I", decoded, 8)[0]
        assert msg_type == 2

    def test_target_name_length(self):
        result = _ntlm_type2_challenge()
        decoded = base64.b64decode(result)
        target_name_len = struct.unpack_from("<H", decoded, 12)[0]
        assert target_name_len == len(b"OPSV")


class TestDirCache:
    def test_get_dir_cache_miss(self, dir_cache):
        assert dir_cache.get_dir("alias", "/path") is None

    def test_set_and_get_dir(self, dir_cache):
        items = ["file1", "file2"]
        dir_cache.set_dir("alias", "/path", items)
        result = dir_cache.get_dir("alias", "/path")
        assert result == items

    def test_get_dir_trailing_slash(self, dir_cache):
        dir_cache.set_dir("alias", "/path/", "items")
        result = dir_cache.get_dir("alias", "/path")
        assert result == "items"

    def test_get_dir_expired(self, dir_cache):
        dir_cache._ttl = 0.01
        dir_cache.set_dir("alias", "/path", "items")
        time.sleep(0.02)
        assert dir_cache.get_dir("alias", "/path") is None

    def test_get_stat_cache_miss(self, dir_cache):
        assert dir_cache.get_stat("alias", "/path") is None

    def test_set_and_get_stat(self, dir_cache):
        stat_info = MagicMock()
        dir_cache.set_stat("alias", "/path", stat_info)
        result = dir_cache.get_stat("alias", "/path")
        assert result is stat_info

    def test_get_stat_trailing_slash(self, dir_cache):
        dir_cache.set_stat("alias", "/path/", "stat")
        result = dir_cache.get_stat("alias", "/path")
        assert result == "stat"

    def test_get_stat_expired(self, dir_cache):
        dir_cache._ttl = 0.01
        dir_cache.set_stat("alias", "/path", "stat")
        time.sleep(0.02)
        assert dir_cache.get_stat("alias", "/path") is None

    def test_invalidate_specific_path(self, dir_cache):
        dir_cache.set_dir("alias", "/path1", "items1")
        dir_cache.set_dir("alias", "/path2", "items2")
        dir_cache.invalidate("alias", "/path1")
        assert dir_cache.get_dir("alias", "/path1") is None
        assert dir_cache.get_dir("alias", "/path2") == "items2"

    def test_invalidate_all_for_alias(self, dir_cache):
        dir_cache.set_dir("alias1", "/path1", "items1")
        dir_cache.set_dir("alias2", "/path2", "items2")
        dir_cache.invalidate("alias1")
        assert dir_cache.get_dir("alias1", "/path1") is None
        assert dir_cache.get_dir("alias2", "/path2") == "items2"

    def test_invalidate_subpaths(self, dir_cache):
        dir_cache.set_dir("alias", "/path", "items_root")
        dir_cache.set_dir("alias", "/path/sub", "items_sub")
        dir_cache.set_dir("alias", "/other", "items_other")
        dir_cache.invalidate("alias", "/path")
        assert dir_cache.get_dir("alias", "/path") is None
        assert dir_cache.get_dir("alias", "/path/sub") is None
        assert dir_cache.get_dir("alias", "/other") == "items_other"

    def test_invalidate_stats(self, dir_cache):
        dir_cache.set_stat("alias", "/path", "stat")
        dir_cache.invalidate("alias", "/path")
        assert dir_cache.get_stat("alias", "/path") is None

    def test_get_instance_singleton(self):
        inst1 = _DirCache.get()
        inst2 = _DirCache.get()
        assert inst1 is inst2


class TestRemoteDriveService:
    def test_initial_state(self, service):
        assert service.is_running is False

    @patch("app.services.remote_drive_service._SilentThreadingHTTPServer")
    @patch("app.services.remote_drive_service.ssh_account_service")
    def test_start_success(self, mock_ssh, mock_server_cls, service):
        mock_server_instance = MagicMock()
        mock_server_cls.return_value = mock_server_instance
        result = service.start("0.0.0.0", 8081)
        assert result is True
        assert service.is_running is True

    @patch("app.services.remote_drive_service._SilentThreadingHTTPServer")
    @patch("app.services.remote_drive_service.ssh_account_service")
    def test_start_already_running(self, mock_ssh, mock_server_cls, service):
        mock_server_instance = MagicMock()
        mock_server_cls.return_value = mock_server_instance
        service.start("0.0.0.0", 8081)
        result = service.start("0.0.0.0", 8082)
        assert result is True
        assert mock_server_cls.call_count == 1

    @patch("app.services.remote_drive_service._SilentThreadingHTTPServer", side_effect=OSError("port in use"))
    @patch("app.services.remote_drive_service.ssh_account_service")
    def test_start_failure(self, mock_ssh, mock_server_cls, service):
        result = service.start("0.0.0.0", 8081)
        assert result is False
        assert service.is_running is False

    @patch("app.services.remote_drive_service._SilentThreadingHTTPServer")
    @patch("app.services.remote_drive_service.ssh_account_service")
    def test_stop(self, mock_ssh, mock_server_cls, service):
        mock_server_instance = MagicMock()
        mock_server_cls.return_value = mock_server_instance
        service.start("0.0.0.0", 8081)
        service.stop()
        assert service.is_running is False
        mock_server_instance.shutdown.assert_called_once()

    def test_stop_when_not_running(self, service):
        service.stop()
        assert service.is_running is False

    @patch("app.services.remote_drive_service._SilentThreadingHTTPServer")
    @patch("app.services.remote_drive_service.ssh_account_service")
    def test_restart(self, mock_ssh, mock_server_cls, service):
        mock_server_instance = MagicMock()
        mock_server_cls.return_value = mock_server_instance
        result = service.restart("0.0.0.0", 8081)
        assert result is True
        assert service.is_running is True


class TestWebDAVRequestHandlerNormalisePath:
    def test_normal_path(self):
        h = _make_handler()
        assert h._normalise_dav_path("/test/path") == "/test/path"

    def test_dav_www_root(self):
        h = _make_handler()
        assert h._normalise_dav_path("/DavWWWRoot/test") == "/test"

    def test_no_leading_slash(self):
        h = _make_handler()
        assert h._normalise_dav_path("test") == "/test"

    def test_empty_after_strip(self):
        h = _make_handler()
        assert h._normalise_dav_path("/") == "/"

    def test_dav_www_root_only(self):
        h = _make_handler()
        assert h._normalise_dav_path("/DavWWWRoot") == "/"


class TestWebDAVRequestHandlerSplitPath:
    def test_root_path(self):
        h = _make_handler(path="/")
        alias, remote = h._split_dav_path("/")
        assert alias is None
        assert remote == "/"

    def test_alias_only(self):
        h = _make_handler(path="/myserver")
        alias, remote = h._split_dav_path("/myserver")
        assert alias == "myserver"
        assert remote == "/"

    def test_alias_with_path(self):
        h = _make_handler(path="/myserver/home/user")
        alias, remote = h._split_dav_path("/myserver/home/user")
        assert alias == "myserver"
        assert remote == "/home/user"

    def test_url_encoded_alias(self):
        h = _make_handler()
        alias, remote = h._split_dav_path("/my%20server/home")
        assert alias == "my server"
        assert remote == "/home"

    def test_url_encoded_path(self):
        h = _make_handler()
        alias, remote = h._split_dav_path("/srv/path%20with%20spaces")
        assert alias == "srv"
        assert remote == "/path with spaces"


class TestWebDAVRequestHandlerParsePath:
    def test_simple_path(self):
        h = _make_handler(path="/myserver/home")
        alias, remote = h._parse_path()
        assert alias == "myserver"
        assert remote == "/home"

    def test_root(self):
        h = _make_handler(path="/")
        alias, remote = h._parse_path()
        assert alias is None
        assert remote == "/"


class TestWebDAVRequestHandlerParseDestination:
    def test_with_destination(self):
        h = _make_handler(headers={"Destination": "http://localhost:8081/myserver/newpath"})
        alias, remote = h._parse_destination()
        assert alias == "myserver"
        assert remote == "/newpath"

    def test_no_destination(self):
        h = _make_handler()
        alias, remote = h._parse_destination()
        assert alias is None
        assert remote is None


class TestWebDAVRequestHandlerCheckAuth:
    def test_no_auth_header(self):
        h = _make_handler()
        assert h._check_auth() is False

    def test_basic_auth_valid(self):
        creds = base64.b64encode(b"opsv:secret").decode()
        h = _make_handler(headers={"Authorization": f"Basic {creds}"})
        with patch.object(h, "_validate_credentials", return_value=True):
            assert h._check_auth() is True

    def test_basic_auth_invalid(self):
        creds = base64.b64encode(b"opsv:wrong").decode()
        h = _make_handler(headers={"Authorization": f"Basic {creds}"})
        with patch.object(h, "_validate_credentials", return_value=False):
            assert h._check_auth() is False

    def test_basic_auth_malformed(self):
        h = _make_handler(headers={"Authorization": "Basic invalid!!!base64"})
        assert h._check_auth() is False

    def test_ntlm_type3_auth(self):
        token = b"NTLMSSP\x00" + struct.pack("<I", 3) + b"\x00" * 20
        encoded = base64.b64encode(token).decode()
        h = _make_handler(headers={"Authorization": f"NTLM {encoded}"})
        assert h._check_auth() is True

    def test_ntlm_type1_auth(self):
        token = b"NTLMSSP\x00" + struct.pack("<I", 1) + b"\x00" * 20
        encoded = base64.b64encode(token).decode()
        h = _make_handler(headers={"Authorization": f"NTLM {encoded}"})
        assert h._check_auth() is False

    def test_ntlm_invalid_token(self):
        h = _make_handler(headers={"Authorization": "NTLM invalidtoken"})
        assert h._check_auth() is False

    def test_unknown_auth_scheme(self):
        h = _make_handler(headers={"Authorization": "Bearer sometoken"})
        assert h._check_auth() is False


class TestWebDAVRequestHandlerValidateCredentials:
    @patch("app.services.remote_drive_service.settings_service")
    def test_with_configured_password(self, mock_settings):
        mock_settings.get.side_effect = lambda key, default="": {
            "remote_drive_username": "admin",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = "mypass"
        h = _make_handler()
        assert h._validate_credentials("admin", "mypass") is True
        assert h._validate_credentials("admin", "wrong") is False
        assert h._validate_credentials("wrong", "mypass") is False

    @patch("app.services.remote_drive_service.settings_service")
    def test_without_configured_password_fallback_ssh(self, mock_settings):
        mock_settings.get.side_effect = lambda key, default="": {
            "remote_drive_username": "opsv",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = ""
        acct = MagicMock()
        acct.username = "sshuser"
        acct.password = "sshpass"
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = [acct]
        assert h._validate_credentials("sshuser", "sshpass") is True
        assert h._validate_credentials("sshuser", "wrong") is False

    @patch("app.services.remote_drive_service.settings_service")
    def test_without_configured_password_no_match(self, mock_settings):
        mock_settings.get.side_effect = lambda key, default="": {
            "remote_drive_username": "opsv",
        }.get(key, default)
        mock_settings.get_decrypted_password.return_value = ""
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = []
        assert h._validate_credentials("any", "any") is False


class TestWebDAVRequestHandlerRequireAuth:
    def test_already_ntlm_authenticated(self):
        h = _make_handler()
        h._ntlm_authenticated = True
        assert h._require_auth() is True

    def test_basic_auth_passes(self):
        creds = base64.b64encode(b"opsv:secret").decode()
        h = _make_handler(headers={"Authorization": f"Basic {creds}"})
        with patch.object(h, "_validate_credentials", return_value=True):
            assert h._require_auth() is True

    def test_ntlm_type1_sends_challenge(self):
        token = b"NTLMSSP\x00" + struct.pack("<I", 1) + b"\x00" * 20
        encoded = base64.b64encode(token).decode()
        h = _make_handler(headers={"Authorization": f"NTLM {encoded}"})
        with patch.object(h, "_send_ntlm_challenge"):
            result = h._require_auth()
        assert result is False

    def test_no_auth_sends_401(self):
        h = _make_handler()
        with patch.object(h, "_send_auth_required"):
            result = h._require_auth()
        assert result is False


class TestWebDAVRequestHandlerFormatTime:
    def test_format_time(self):
        h = _make_handler()
        result = h._format_time(0)
        assert "GMT" in result
        assert "1970" in result

    def test_format_time_iso(self):
        h = _make_handler()
        result = h._format_time_iso(0)
        assert "1970" in result
        assert "Z" in result


class TestWebDAVRequestHandlerGetSftp:
    def test_account_not_found(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        sftp, conn = h._get_sftp("nonexistent")
        assert sftp is None
        assert conn is None

    def test_connection_failure(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        acct = MagicMock()
        h.SSH_SERVICE.get_account.return_value = acct
        h.SSH_SERVICE.pool.get_connection.side_effect = Exception("conn fail")
        sftp, conn = h._get_sftp("alias")
        assert sftp is None
        assert conn is None

    def test_success(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        acct = MagicMock()
        conn = MagicMock()
        sftp = MagicMock()
        conn.manager.open_sftp.return_value = sftp
        h.SSH_SERVICE.get_account.return_value = acct
        h.SSH_SERVICE.pool.get_connection.return_value = conn
        result_sftp, result_conn = h._get_sftp("alias")
        assert result_sftp is sftp
        assert result_conn is conn


class TestWebDAVRequestHandlerRelease:
    def test_release_none(self):
        h = _make_handler()
        h._release(None)

    def test_release_success(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        conn = MagicMock()
        h._release(conn)
        h.SSH_SERVICE.pool.release_connection.assert_called_once_with(conn)

    def test_release_exception(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.pool.release_connection.side_effect = Exception("err")
        conn = MagicMock()
        h._release(conn)


class TestWebDAVRequestHandlerCloseSftp:
    def test_close_none(self):
        h = _make_handler()
        h._close_sftp(None)

    def test_close_success(self):
        h = _make_handler()
        sftp = MagicMock()
        h._close_sftp(sftp)
        sftp.close.assert_called_once()

    def test_close_exception(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.close.side_effect = Exception("err")
        h._close_sftp(sftp)


class TestWebDAVRequestHandlerParseRange:
    def test_valid_range(self):
        h = _make_handler()
        result = h._parse_range("bytes=0-99", 200)
        assert result == (0, 99)

    def test_suffix_range(self):
        h = _make_handler()
        result = h._parse_range("bytes=-50", 200)
        assert result == (150, 199)

    def test_open_end_range(self):
        h = _make_handler()
        result = h._parse_range("bytes=100-", 200)
        assert result == (100, 199)

    def test_invalid_no_bytes_prefix(self):
        h = _make_handler()
        assert h._parse_range("items=0-99", 200) is None

    def test_invalid_no_dash(self):
        h = _make_handler()
        assert h._parse_range("bytes=100", 200) is None

    def test_negative_file_size(self):
        h = _make_handler()
        assert h._parse_range("bytes=0-99", -1) is None

    def test_start_beyond_file(self):
        h = _make_handler()
        assert h._parse_range("bytes=300-", 200) is None

    def test_suffix_zero(self):
        h = _make_handler()
        assert h._parse_range("bytes=-0", 200) is None

    def test_invalid_start(self):
        h = _make_handler()
        assert h._parse_range("bytes=-1", 0) is None

    def test_value_error(self):
        h = _make_handler()
        assert h._parse_range("bytes=abc-def", 200) is None


class TestWebDAVRequestHandlerIsNotFound:
    def test_enoent(self):
        h = _make_handler()
        exc = OSError(errno.ENOENT, "not found")
        assert h._is_not_found(exc) is True

    def test_enotdir(self):
        h = _make_handler()
        exc = OSError(errno.ENOTDIR, "not dir")
        assert h._is_not_found(exc) is True

    def test_other_errno(self):
        h = _make_handler()
        exc = OSError(errno.EACCES, "denied")
        assert h._is_not_found(exc) is False


class TestWebDAVRequestHandlerEnsureDir:
    def test_creates_missing_dirs(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        h._ensure_dir(sftp, "/a/b/c")
        assert sftp.mkdir.call_count == 3

    def test_existing_dirs(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.stat.return_value = MagicMock()
        h._ensure_dir(sftp, "/a/b")
        sftp.mkdir.assert_not_called()

    def test_mixed_existing_and_missing(self):
        h = _make_handler()
        sftp = MagicMock()
        call_count = [0]

        def stat_side_effect(path):
            call_count[0] += 1
            if path == "/a":
                return MagicMock()
            raise FileNotFoundError

        sftp.stat.side_effect = stat_side_effect
        h._ensure_dir(sftp, "/a/b")
        sftp.mkdir.assert_called_once_with("/a/b")


class TestWebDAVRequestHandlerRmtree:
    def test_rmtree_with_files(self):
        h = _make_handler()
        sftp = MagicMock()
        file_attr = MagicMock()
        file_attr.filename = "file.txt"
        file_attr.st_mode = 0o100644
        sftp.listdir_attr.return_value = [file_attr]
        h._rmtree(sftp, "/test")
        sftp.remove.assert_called_once_with("/test/file.txt")
        sftp.rmdir.assert_called_once_with("/test")

    def test_rmtree_with_subdirs(self):
        h = _make_handler()
        sftp = MagicMock()
        dir_attr = MagicMock()
        dir_attr.filename = "subdir"
        dir_attr.st_mode = 0o40755
        sftp.listdir_attr.side_effect = [
            [dir_attr],
            [],
        ]
        h._rmtree(sftp, "/test")
        sftp.rmdir.assert_any_call("/test/subdir")
        sftp.rmdir.assert_any_call("/test")

    def test_rmtree_empty_dir(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.listdir_attr.return_value = []
        h._rmtree(sftp, "/empty")
        sftp.rmdir.assert_called_once_with("/empty")


class TestWebDAVRequestHandlerCopyPath:
    def test_copy_file(self):
        h = _make_handler()
        sftp = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        sftp.stat.return_value = stat_info
        src_mock = MagicMock()
        dst_mock = MagicMock()
        src_mock.read.return_value = b""
        src_mock.__enter__ = MagicMock(return_value=src_mock)
        src_mock.__exit__ = MagicMock(return_value=False)
        dst_mock.__enter__ = MagicMock(return_value=dst_mock)
        dst_mock.__exit__ = MagicMock(return_value=False)
        sftp.open.side_effect = [src_mock, dst_mock]
        with patch.object(h, "_ensure_dir"):
            h._copy_path(sftp, "/src/file.txt", "/dst/file.txt")
            assert sftp.open.call_count == 2

    def test_copy_directory(self):
        h = _make_handler()
        sftp = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        sftp.stat.return_value = stat_info
        with patch.object(h, "_copy_tree") as mock_copy_tree:
            h._copy_path(sftp, "/src/dir", "/dst/dir")
            mock_copy_tree.assert_called_once_with(sftp, "/src/dir", "/dst/dir")


class TestWebDAVRequestHandlerCopyTree:
    def test_copy_tree_mkdir_not_found_then_create(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.mkdir.side_effect = [OSError(errno.ENOENT, "no parent"), None]
        sftp.listdir_attr.return_value = []
        h._copy_tree(sftp, "/src", "/dst")
        assert sftp.mkdir.call_count == 2

    def test_copy_tree_mkdir_other_error_raises(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.mkdir.side_effect = OSError(errno.EACCES, "denied")
        with pytest.raises(OSError):
            h._copy_tree(sftp, "/src", "/dst")

    def test_copy_tree_with_files(self):
        h = _make_handler()
        sftp = MagicMock()
        file_attr = MagicMock()
        file_attr.filename = "file.txt"
        file_attr.st_mode = 0o100644
        sftp.listdir_attr.return_value = [file_attr]
        src_f = MagicMock()
        src_f.read.side_effect = [b"data", b""]
        dst_f = MagicMock()
        src_file = MagicMock()
        src_file.__enter__ = MagicMock(return_value=src_f)
        src_file.__exit__ = MagicMock(return_value=False)
        dst_file = MagicMock()
        dst_file.__enter__ = MagicMock(return_value=dst_f)
        dst_file.__exit__ = MagicMock(return_value=False)
        sftp.open.side_effect = [src_file, dst_file]
        h._copy_tree(sftp, "/src", "/dst")
        sftp.mkdir.assert_called_once_with("/dst")
        dst_f.write.assert_called_once_with(b"data")


class TestWebDAVRequestHandlerStatToXml:
    def test_directory_stat(self):
        h = _make_handler()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 4096
        result = h._stat_to_xml("alias", "/path", stat_info)
        assert "<D:collection/>" in result
        assert "0x00000010" in result

    def test_file_stat(self):
        h = _make_handler()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 1024
        result = h._stat_to_xml("alias", "/path/file.txt", stat_info)
        assert "application/octet-stream" in result
        assert "1024" in result
        assert "0x00000020" in result

    def test_root_path(self):
        h = _make_handler()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 0
        result = h._stat_to_xml("alias", "/", stat_info, is_root=True)
        assert "alias" in result

    def test_none_mtime(self):
        h = _make_handler()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        stat_info.st_mtime = None
        stat_info.st_atime = None
        stat_info.st_size = 0
        result = h._stat_to_xml("alias", "/path", stat_info)
        assert "D:getlastmodified" in result

    def test_stripped_path_empty(self):
        h = _make_handler()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 0
        result = h._stat_to_xml("alias", "/", stat_info)
        assert "alias" in result


class TestWebDAVRequestHandlerListAccountsXml:
    def test_with_accounts(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        acct1 = MagicMock()
        acct1.alias = "server1"
        acct2 = MagicMock()
        acct2.alias = "server2"
        h.SSH_SERVICE.list_accounts.return_value = [acct1, acct2]
        result = h._list_accounts_xml()
        assert "server1" in result
        assert "server2" in result
        assert "OpsV-Kits" in result

    def test_no_accounts(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = []
        result = h._list_accounts_xml()
        assert "OpsV-Kits" in result
        assert "D:multistatus" in result


class TestWebDAVRequestHandlerHandlePropfindRoot:
    def test_depth_zero(self):
        h = _make_handler(headers={"Depth": "0"})
        h._handle_propfind_root()
        h.send_response.assert_called_with(207)

    def test_depth_infinity(self):
        h = _make_handler(headers={"Depth": "infinity"})
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = []
        h._handle_propfind_root()
        h.send_response.assert_called_with(207)


class TestWebDAVRequestHandlerHandlePropfind:
    def test_sftp_not_available(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_propfind("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_directory_listing(self):
        h = _make_handler(headers={"Depth": "1"})
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 4096
        sftp.stat.return_value = stat_info
        file_attr = MagicMock()
        file_attr.filename = "test.txt"
        file_attr.st_mode = 0o100644
        file_attr.st_mtime = 1000000.0
        file_attr.st_atime = 1000000.0
        file_attr.st_size = 100
        sftp.listdir_attr.return_value = [file_attr]
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_propfind("alias", "/path")
            h.send_response.assert_called_with(207)

    def test_file_listing(self):
        h = _make_handler(headers={"Depth": "0"})
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        stat_info.st_mtime = 1000000.0
        stat_info.st_atime = 1000000.0
        stat_info.st_size = 100
        sftp.stat.return_value = stat_info
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_propfind("alias", "/path")
            h.send_response.assert_called_with(207)

    def test_file_not_found(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_propfind("alias", "/path")
                mock_err.assert_called_once_with(404, "Path not found")

    def test_permission_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_propfind("alias", "/path")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_os_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = OSError("some error")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_propfind("alias", "/path")
                mock_err.assert_called_once_with(404, "some error")

    def test_generic_exception(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = RuntimeError("unexpected")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_propfind("alias", "/path")
                mock_err.assert_called_once_with(500, "unexpected")


class TestWebDAVRequestHandlerHandleGet:
    def test_sftp_not_available(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_get("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_directory_redirect(self):
        h = _make_handler(path="/alias/path")
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_size = 4096
        sftp.stat.return_value = stat_info
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_get("alias", "/path")
            h.send_response.assert_called_with(302)

    def test_directory_with_trailing_slash(self):
        h = _make_handler(path="/alias/path/")
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        stat_info.st_mtime = 1000000.0
        stat_info.st_size = 4096
        sftp.stat.return_value = stat_info
        sftp.listdir_attr.return_value = []
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_get("alias", "/path")
            h.send_response.assert_called_with(200)

    def test_file_not_found(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_get("alias", "/path")
                mock_err.assert_called_once_with(404, "File not found")

    def test_permission_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_get("alias", "/path")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_generic_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = RuntimeError("fail")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_get("alias", "/path")
                mock_err.assert_called_once_with(500, "fail")

    def test_file_invalid_range(self):
        h = _make_handler(headers={"Range": "bytes=999-"})
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        stat_info.st_mtime = 1000000.0
        stat_info.st_size = 10
        sftp.stat.return_value = stat_info
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path/file.txt")
            h._handle_get("alias", "/path/file.txt")
            h.send_response.assert_called_with(416)


class TestWebDAVRequestHandlerHandlePut:
    def test_sftp_not_available(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_put("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_upload_permission_error(self):
        h = _make_handler(headers={"Content-Length": "5"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.open.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_put("alias", "/path/file.txt")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_upload_generic_error(self):
        h = _make_handler(headers={"Content-Length": "5"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.open.side_effect = RuntimeError("fail")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_put("alias", "/path/file.txt")
                mock_err.assert_called_once_with(500, "fail")

    def test_upload_success(self):
        h = _make_handler(headers={"Content-Length": "5"})
        sftp = MagicMock()
        conn = MagicMock()
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.write = MagicMock()
        sftp.open.return_value = mock_file
        h.rfile.read.side_effect = [b"hello", b""]
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"), \
             patch.object(h, "_ensure_dir"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_put("alias", "/path/file.txt")
            h.send_response.assert_called_with(201)


class TestWebDAVRequestHandlerHandleDelete:
    def test_sftp_not_available(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_delete("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_delete_file(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        sftp.stat.return_value = stat_info
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_delete("alias", "/path/file.txt")
            sftp.remove.assert_called_once_with("/path/file.txt")
            h.send_response.assert_called_with(204)

    def test_delete_directory(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o40755
        sftp.stat.return_value = stat_info
        sftp.listdir_attr.return_value = []
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_delete("alias", "/path/dir")
            sftp.rmdir.assert_called_once_with("/path/dir")
            h.send_response.assert_called_with(204)

    def test_delete_not_found(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_delete("alias", "/path")
                mock_err.assert_called_once_with(404, "File not found")

    def test_delete_permission_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_delete("alias", "/path")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_delete_generic_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = RuntimeError("fail")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_delete("alias", "/path")
                mock_err.assert_called_once_with(500, "fail")


class TestWebDAVRequestHandlerHandleMkcol:
    def test_sftp_not_available(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_mkcol("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_create_dir_success(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_mkcol("alias", "/path/newdir")
            sftp.mkdir.assert_called_once_with("/path/newdir")
            h.send_response.assert_called_with(201)

    def test_create_dir_exists(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.mkdir.side_effect = FileExistsError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_mkcol("alias", "/path/exists")
                mock_err.assert_called_once_with(405, "Method Not Allowed")

    def test_create_dir_permission_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.mkdir.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_mkcol("alias", "/path")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_create_dir_generic_error(self):
        h = _make_handler()
        sftp = MagicMock()
        conn = MagicMock()
        sftp.mkdir.side_effect = RuntimeError("fail")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_mkcol("alias", "/path")
                mock_err.assert_called_once_with(500, "fail")


class TestWebDAVRequestHandlerHandleMove:
    def test_no_destination(self):
        h = _make_handler()
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_move("alias", "/path")
            mock_err.assert_called_once_with(400, "Destination header required")

    def test_cross_account_move(self):
        h = _make_handler(headers={"Destination": "http://localhost/other/path"})
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_move("alias", "/path")
            mock_err.assert_called_once_with(400, "Cross-account move not supported")

    def test_sftp_not_available(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_move("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_move_to_new_destination(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath", "Overwrite": "T"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_move("alias", "/path/old")
            sftp.rename.assert_called_once_with("/path/old", "/newpath")
            h.send_response.assert_called_with(201)

    def test_move_overwrite_existing(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath", "Overwrite": "T"})
        sftp = MagicMock()
        conn = MagicMock()
        dest_stat = MagicMock()
        dest_stat.st_mode = 0o100644
        sftp.stat.return_value = dest_stat
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            h._handle_move("alias", "/path/old")
            sftp.remove.assert_called_once_with("/newpath")
            h.send_response.assert_called_with(204)

    def test_move_no_overwrite_existing(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath", "Overwrite": "F"})
        sftp = MagicMock()
        conn = MagicMock()
        dest_stat = MagicMock()
        dest_stat.st_mode = 0o100644
        sftp.stat.return_value = dest_stat
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_move("alias", "/path/old")
                mock_err.assert_called_once_with(412, "Precondition Failed")

    def test_move_permission_error(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        sftp.rename.side_effect = PermissionError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_move("alias", "/path/old")
                mock_err.assert_called_once_with(403, "Permission denied")


class TestWebDAVRequestHandlerHandleCopy:
    def test_no_destination(self):
        h = _make_handler()
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_copy("alias", "/path")
            mock_err.assert_called_once_with(400, "Destination header required")

    def test_cross_account_copy(self):
        h = _make_handler(headers={"Destination": "http://localhost/other/path"})
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_copy("alias", "/path")
            mock_err.assert_called_once_with(400, "Cross-account copy not supported")

    def test_sftp_not_available(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.get_account.return_value = None
        with patch.object(h, "_safe_send_error") as mock_err:
            h._handle_copy("alias", "/path")
            mock_err.assert_called_once_with(404, "Account not found or connection failed")

    def test_copy_no_overwrite_existing(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath", "Overwrite": "F"})
        sftp = MagicMock()
        conn = MagicMock()
        dest_stat = MagicMock()
        dest_stat.st_mode = 0o100644
        sftp.stat.return_value = dest_stat
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_copy("alias", "/path/src")
                mock_err.assert_called_once_with(412, "Precondition Failed")

    def test_copy_to_new_destination(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath", "Overwrite": "T"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"), \
             patch.object(h, "_copy_path") as mock_copy:
            _dir_cache.invalidate("alias", "/path")
            h._handle_copy("alias", "/path/src")
            mock_copy.assert_called_once_with(sftp, "/path/src", "/newpath")
            h.send_response.assert_called_with(201)

    def test_copy_not_found(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"), \
             patch.object(h, "_copy_path", side_effect=FileNotFoundError):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_copy("alias", "/path/src")
                mock_err.assert_called_once_with(404, "Path not found")

    def test_copy_permission_error(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"), \
             patch.object(h, "_copy_path", side_effect=PermissionError):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_copy("alias", "/path/src")
                mock_err.assert_called_once_with(403, "Permission denied")

    def test_copy_generic_error(self):
        h = _make_handler(headers={"Destination": "http://localhost/alias/newpath"})
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"), \
             patch.object(h, "_copy_path", side_effect=RuntimeError("fail")):
            _dir_cache.invalidate("alias", "/path")
            with patch.object(h, "_safe_send_error") as mock_err:
                h._handle_copy("alias", "/path/src")
                mock_err.assert_called_once_with(500, "fail")


class TestWebDAVRequestHandlerDoMethods:
    def test_do_options(self):
        h = _make_handler()
        h.do_OPTIONS()
        h.send_response.assert_called_with(200)

    def test_do_propfind_root(self):
        h = _make_handler(path="/", headers={"Depth": "0"})
        h._ntlm_authenticated = True
        h.do_PROPFIND()
        h.send_response.assert_called_with(207)

    def test_do_proppatch(self):
        h = _make_handler(path="/test")
        h._ntlm_authenticated = True
        h.do_PROPPATCH()
        h.send_response.assert_called_with(207)

    def test_do_get_root(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = []
        h.do_GET()
        h.send_response.assert_called_with(200)

    def test_do_head_root(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        h.do_HEAD()
        h.send_response.assert_called_with(200)

    def test_do_head_with_sftp(self):
        h = _make_handler(path="/alias/path")
        h._ntlm_authenticated = True
        sftp = MagicMock()
        conn = MagicMock()
        stat_info = MagicMock()
        stat_info.st_mode = 0o100644
        stat_info.st_mtime = 1000000.0
        stat_info.st_size = 1024
        sftp.stat.return_value = stat_info
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            h.do_HEAD()
            h.send_response.assert_called_with(200)

    def test_do_head_not_found(self):
        h = _make_handler(path="/alias/path")
        h._ntlm_authenticated = True
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = FileNotFoundError
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            with patch.object(h, "_safe_send_error") as mock_err:
                h.do_HEAD()
                mock_err.assert_called_once_with(404)

    def test_do_head_error(self):
        h = _make_handler(path="/alias/path")
        h._ntlm_authenticated = True
        sftp = MagicMock()
        conn = MagicMock()
        sftp.stat.side_effect = RuntimeError("fail")
        with patch.object(h, "_get_sftp", return_value=(sftp, conn)), \
             patch.object(h, "_close_sftp"), \
             patch.object(h, "_release"):
            with patch.object(h, "_safe_send_error") as mock_err:
                h.do_HEAD()
                mock_err.assert_called_once_with(500)

    def test_do_put_no_alias(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"), \
             patch.object(h, "_safe_send_error") as mock_err:
            h.do_PUT()
            mock_err.assert_called_once_with(400, "Account alias required")

    def test_do_delete_no_alias(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"), \
             patch.object(h, "_safe_send_error") as mock_err:
            h.do_DELETE()
            mock_err.assert_called_once_with(400, "Account alias required")

    def test_do_mkcol_no_alias(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"), \
             patch.object(h, "_safe_send_error") as mock_err:
            h.do_MKCOL()
            mock_err.assert_called_once_with(400, "Account alias required")

    def test_do_move_no_alias(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"), \
             patch.object(h, "_safe_send_error") as mock_err:
            h.do_MOVE()
            mock_err.assert_called_once_with(400, "Account alias required")

    def test_do_copy_no_alias(self):
        h = _make_handler(path="/")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"), \
             patch.object(h, "_safe_send_error") as mock_err:
            h.do_COPY()
            mock_err.assert_called_once_with(400, "Account alias required")

    def test_do_lock(self):
        h = _make_handler(path="/alias/path")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"):
            h.do_LOCK()
            h.send_response.assert_called_with(200)

    def test_do_unlock(self):
        h = _make_handler(path="/alias/path")
        h._ntlm_authenticated = True
        with patch.object(h, "_drain_request_body"):
            h.do_UNLOCK()
            h.send_response.assert_called_with(204)

    def test_do_methods_require_auth(self):
        h = _make_handler()
        with patch.object(h, "_require_auth", return_value=False), \
             patch.object(h, "_send_auth_required"):
            h.do_PROPFIND()
            h.do_GET()
            h.do_HEAD()
            h.do_PUT()
            h.do_DELETE()
            h.do_MKCOL()
            h.do_MOVE()
            h.do_COPY()
            h.do_LOCK()
            h.do_UNLOCK()


class TestWebDAVRequestHandlerDrainRequestBody:
    def test_drain_with_content(self):
        h = _make_handler(headers={"Content-Length": "10"})
        h.rfile.read.side_effect = [b"0123456789"]
        h.rfile._sock = MagicMock()
        h._drain_request_body()

    def test_drain_zero_content(self):
        h = _make_handler(headers={"Content-Length": "0"})
        h._drain_request_body()

    def test_drain_invalid_content_length(self):
        h = _make_handler(headers={"Content-Length": "abc"})
        h._drain_request_body()

    def test_drain_exception(self):
        h = _make_handler(headers={"Content-Length": "10"})
        h.rfile.read.side_effect = OSError("fail")
        h.rfile._sock = MagicMock()
        h._drain_request_body()


class TestWebDAVRequestHandlerSafeSendError:
    def test_with_message(self):
        h = _make_handler()
        h._safe_send_error(404, "Not found")
        h.send_response.assert_called_with(404)

    def test_without_message(self):
        h = _make_handler()
        h._safe_send_error(500)
        h.send_response.assert_called_with(500)

    def test_write_exception(self):
        h = _make_handler()
        h.wfile.write.side_effect = OSError("broken pipe")
        h._safe_send_error(500, "Error")


class TestWebDAVRequestHandlerListDirHtml:
    def test_root_path(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.listdir_attr.return_value = []
        h._list_dir_html("alias", "/", sftp)
        h.send_response.assert_called_with(200)

    def test_subdirectory_with_parent(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.listdir_attr.return_value = []
        h._list_dir_html("alias", "/home/user", sftp)
        h.send_response.assert_called_with(200)
        written = h.wfile.write.call_args[0][0]
        assert b".." in written

    def test_with_files(self):
        h = _make_handler()
        sftp = MagicMock()
        file_attr = MagicMock()
        file_attr.filename = "test.txt"
        file_attr.st_mode = 0o100644
        dir_attr = MagicMock()
        dir_attr.filename = "subdir"
        dir_attr.st_mode = 0o40755
        sftp.listdir_attr.return_value = [file_attr, dir_attr]
        h._list_dir_html("alias", "/path", sftp)
        h.send_response.assert_called_with(200)

    def test_list_error(self):
        h = _make_handler()
        sftp = MagicMock()
        sftp.listdir_attr.side_effect = PermissionError("denied")
        h._list_dir_html("alias", "/path", sftp)
        h.send_response.assert_called_with(200)


class TestWebDAVRequestHandlerListRootHtml:
    def test_with_accounts(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        acct = MagicMock()
        acct.alias = "server1"
        acct.host = "192.168.1.1"
        acct.port = 22
        h.SSH_SERVICE.list_accounts.return_value = [acct]
        h._list_root_html()
        h.send_response.assert_called_with(200)

    def test_no_accounts(self):
        h = _make_handler()
        h.SSH_SERVICE = MagicMock()
        h.SSH_SERVICE.list_accounts.return_value = []
        h._list_root_html()
        h.send_response.assert_called_with(200)


class TestWebDAVRequestHandlerHandle:
    def test_handle_connection_reset(self):
        h = _make_handler()
        with patch.object(h, "handle_one_request", side_effect=ConnectionResetError):
            h.handle()

    def test_handle_broken_pipe(self):
        h = _make_handler()
        with patch.object(h, "handle_one_request", side_effect=BrokenPipeError):
            h.handle()

    def test_handle_os_error(self):
        h = _make_handler()
        with patch.object(h, "handle_one_request", side_effect=OSError):
            h.handle()

    def test_handle_normal(self):
        h = _make_handler()

        def side_effect():
            h.close_connection = True

        with patch.object(h, "handle_one_request", side_effect=side_effect):
            h.handle()


class TestSilentThreadingHTTPServer:
    def test_handle_error(self):
        server = object.__new__(_SilentThreadingHTTPServer)
        server.handle_error("request", ("127.0.0.1", 12345))
