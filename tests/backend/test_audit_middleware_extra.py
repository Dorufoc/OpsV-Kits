from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.audit_middleware import (
    AuditMiddleware,
    _decode_header_value,
    _determine_action_type,
    _determine_module,
    _extract_ip,
    _extract_user_info,
    _is_sensitive,
    _parse_headers,
    _sanitize_detail,
    _should_exclude,
)
from app.models.audit_log import ActionType


class TestDetermineActionTypeLogout:
    def test_logout_path(self):
        assert _determine_action_type("POST", "/api/auth/logout") == ActionType.LOGOUT


class TestDetermineActionTypeFallbackExecute:
    def test_options_method_returns_execute(self):
        assert _determine_action_type("OPTIONS", "/api/test") == ActionType.EXECUTE

    def test_head_method_returns_execute(self):
        assert _determine_action_type("HEAD", "/api/test") == ActionType.EXECUTE


class TestDecodeHeaderValue:
    def test_tuple_value(self):
        result = _decode_header_value(("a", "b"))
        assert result == "('a', 'b')"

    def test_int_value(self):
        result = _decode_header_value(123)
        assert result == "123"

    def test_bytes_value(self):
        result = _decode_header_value(b"hello")
        assert result == "hello"

    def test_str_value(self):
        result = _decode_header_value("hello")
        assert result == "hello"


class TestParseHeadersBytesItems:
    def test_bytes_item_skipped(self):
        headers = [b"raw-bytes-header"]
        result = _parse_headers(headers)
        assert result == {}

    def test_other_item_skipped(self):
        headers = [42]
        result = _parse_headers(headers)
        assert result == {}

    def test_flat_bytes_headers(self):
        headers = [b"content-type", b"application/json", b"x-user-id", b"user123"]
        result = _parse_headers(headers)
        assert result["content-type"] == "application/json"
        assert result["x-user-id"] == "user123"

    def test_flat_bytes_headers_odd_length(self):
        headers = [b"content-type", b"application/json", b"alone-key"]
        result = _parse_headers(headers)
        assert result["content-type"] == "application/json"
        assert "alone-key" not in result


class TestExtractUserInfo:
    def test_x_user_id_header(self):
        headers = [(b"x-user-id", b"42")]
        uid, uname = _extract_user_info(headers)
        assert uid == "42"

    def test_x_username_header(self):
        headers = [(b"x-username", b"admin")]
        uid, uname = _extract_user_info(headers)
        assert uname == "admin"

    def test_bearer_token_extraction(self):
        headers = [(b"authorization", b"Bearer abcdefghijklmnop")]
        uid, uname = _extract_user_info(headers)
        assert uid == "bearer:abcdefgh..."
        assert uname == "bearer:abcdefgh..."

    def test_bearer_token_empty(self):
        headers = [(b"authorization", b"Bearer ")]
        uid, uname = _extract_user_info(headers)
        assert uid == "anonymous"

    def test_bearer_token_with_user_id(self):
        headers = [(b"x-user-id", b"42"), (b"authorization", b"Bearer abcdefghijklmnop")]
        uid, uname = _extract_user_info(headers)
        assert uid == "42"


class TestExtractIpForwarded:
    def test_x_forwarded_for(self):
        scope = {"client": ("10.0.0.1", 12345)}
        headers = [(b"x-forwarded-for", b"192.168.1.1, 10.0.0.2")]
        ip = _extract_ip(scope, headers)
        assert ip == "192.168.1.1"


class TestAuditMiddlewareAppException:
    @pytest.mark.asyncio
    async def test_app_raises_exception_sets_500(self):
        async def failing_app(scope, receive, send):
            raise RuntimeError("app error")

        middleware = AuditMiddleware(failing_app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }
        received = []

        async def send(msg):
            received.append(msg)

        with patch("app.services.audit_log_service.audit_log_service") as mock_svc:
            mock_svc.enqueue_log = MagicMock()
            with pytest.raises(RuntimeError, match="app error"):
                await middleware(scope, lambda: None, send)

    @pytest.mark.asyncio
    async def test_enqueue_log_exception_logged(self):
        async def ok_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b""})

        middleware = AuditMiddleware(ok_app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }
        received = []

        async def send(msg):
            received.append(msg)

        with patch("app.services.audit_log_service.audit_log_service") as mock_svc:
            mock_svc.enqueue_log.side_effect = Exception("db error")
            await middleware(scope, lambda: None, send)
