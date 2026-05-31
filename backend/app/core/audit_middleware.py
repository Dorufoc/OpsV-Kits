import asyncio
import logging
import time
import uuid
from datetime import datetime
from urllib.parse import parse_qs

from app.models.audit_log import ActionType, AuditModule

logger = logging.getLogger(__name__)

_EXCLUDED_PATHS = (
    "/api/health",
    "/assets/",
    "/docs",
    "/redoc",
    "/openapi.json",
)

_MODULE_MAP = [
    ("/api/ssh-accounts", "ssh"),
    ("/api/docker", "docker"),
    ("/api/monitor", "monitor"),
    ("/api/process", "process"),
    ("/api/security", "security"),
    ("/api/settings", "settings"),
    ("/api/projects", "project"),
    ("/api/build", "build"),
    ("/api/cron-backup", "cron-backup"),
    ("/api/file-manager", "file-manager"),
    ("/api/db-toolkit", "db-toolkit"),
    ("/api/webssh", "webssh"),
    ("/api/remote-drive", "remote-drive"),
    ("/api/deploy", "vite-deploy"),
    ("/api/audit-log", "audit"),
]

_SENSITIVE_PATHS = (
    "/api/ssh-accounts/test-connection",
    "/api/webssh/test",
    "/api/webssh/connect",
    "/api/webssh/command",
    "/api/security/ssh/",
    "/api/security/firewall/",
    "/api/system/reboot",
    "/api/system/shutdown",
)

_SENSITIVE_KEYWORDS = ("password", "key", "secret", "token")

_SANITIZED_KEYS = ("password", "passwd", "secret", "token", "key", "credential")


def _determine_action_type(method: str, path: str) -> str:
    lower_path = path.lower()
    if "login" in lower_path:
        return ActionType.LOGIN
    if "logout" in lower_path:
        return ActionType.LOGOUT
    if "export" in lower_path:
        return ActionType.EXPORT
    if "import" in lower_path:
        return ActionType.IMPORT
    method_upper = method.upper()
    if method_upper == "POST":
        return ActionType.CREATE
    if method_upper in ("PUT", "PATCH"):
        return ActionType.UPDATE
    if method_upper == "DELETE":
        return ActionType.DELETE
    if method_upper == "GET":
        if any(kw in lower_path for kw in ("action", "execute", "run", "trigger", "test", "connect")):
            return ActionType.EXECUTE
        return ActionType.CONFIG
    return ActionType.EXECUTE


def _determine_module(path: str) -> str:
    for prefix, module in _MODULE_MAP:
        if path.startswith(prefix):
            return module
    return "security"


def _is_sensitive(path: str) -> bool:
    lower_path = path.lower()
    for sensitive_path in _SENSITIVE_PATHS:
        if lower_path.startswith(sensitive_path.lower()):
            return True
    for keyword in _SENSITIVE_KEYWORDS:
        if keyword in lower_path:
            return True
    return False


def _sanitize_detail(detail: dict) -> dict:
    sanitized = {}
    for k, v in detail.items():
        lower_key = k.lower()
        if any(s in lower_key for s in _SANITIZED_KEYS):
            sanitized[k] = "***"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_detail(v)
        else:
            sanitized[k] = v
    return sanitized


def _should_exclude(path: str) -> bool:
    if path == "/api/health" or path.startswith("/api/health/"):
        return True
    if path.startswith("/assets/"):
        return True
    if path in ("/docs", "/redoc", "/openapi.json"):
        return True
    if path.startswith("/api/audit-log/") and "export" not in path.lower() and "verify" not in path.lower():
        return True
    return False


def _decode_header_value(val) -> str:
    if isinstance(val, bytes):
        return val.decode("latin-1")
    if isinstance(val, str):
        return val
    if isinstance(val, tuple):
        return str(val)
    return str(val)


def _parse_headers(headers) -> dict:
    result = {}
    for item in headers:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            key = _decode_header_value(item[0]).lower()
            val = _decode_header_value(item[1])
            result[key] = val
        elif isinstance(item, bytes):
            pass
        else:
            pass
    if not result and len(headers) > 0 and isinstance(headers[0], bytes):
        for i in range(0, len(headers), 2):
            if i + 1 < len(headers):
                key = _decode_header_value(headers[i]).lower()
                val = _decode_header_value(headers[i + 1])
                result[key] = val
    return result


def _extract_user_info(headers: list) -> tuple:
    user_id = "anonymous"
    username = "anonymous"
    headers_dict = _parse_headers(headers)

    x_user_id = headers_dict.get("x-user-id", "")
    x_username = headers_dict.get("x-username", "")
    if x_user_id:
        user_id = x_user_id
    if x_username:
        username = x_username

    auth_header = headers_dict.get("authorization", "")
    if auth_header.startswith("Bearer ") and user_id == "anonymous":
        token_part = auth_header[7:]
        if token_part:
            user_id = f"bearer:{token_part[:8]}..."
            username = user_id

    return user_id, username


def _extract_ip(scope: dict, headers: list) -> str:
    ip = scope.get("client", ("unknown", 0))[0]
    headers_dict = _parse_headers(headers)
    forwarded_for = headers_dict.get("x-forwarded-for", "")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    return ip


def _extract_user_agent(headers: list) -> str:
    headers_dict = _parse_headers(headers)
    return headers_dict.get("user-agent", "")


def _extract_query_params(scope: dict) -> dict:
    query_string = scope.get("query_string", b"")
    if isinstance(query_string, bytes):
        query_string = query_string.decode("utf-8", errors="replace")
    if not query_string:
        return {}
    parsed = parse_qs(query_string)
    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}


def _extract_path_params(scope: dict) -> dict:
    path_params = scope.get("path_params")
    if path_params:
        return dict(path_params)
    return {}


class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        if _should_exclude(path):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        headers = scope.get("headers", [])
        start_time = time.time()

        response_status = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                response_status[0] = status_code
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            response_status[0] = 500
            raise
        finally:
            try:
                end_time = time.time()
                duration_ms = round((end_time - start_time) * 1000, 2)

                ip_address = _extract_ip(scope, headers)
                user_agent = _extract_user_agent(headers)
                user_id, username = _extract_user_info(headers)
                action_type = _determine_action_type(method, path)
                module = _determine_module(path)
                sensitive = _is_sensitive(path)

                query_params = _extract_query_params(scope)
                path_params = _extract_path_params(scope)
                detail = {}
                if query_params:
                    detail["query_params"] = query_params
                if path_params:
                    detail["path_params"] = path_params

                if sensitive:
                    detail = _sanitize_detail(detail)

                status = "success" if response_status[0] < 400 else "failure"

                entry = {
                    "id": uuid.uuid4().hex,
                    "user_id": user_id,
                    "username": username,
                    "timestamp": datetime.now().isoformat(),
                    "ip_address": ip_address,
                    "action_type": action_type,
                    "module": module,
                    "detail": detail if detail else None,
                    "status": status,
                    "client_info": user_agent,
                    "request_path": path,
                    "request_method": method,
                    "response_code": response_status[0],
                    "duration_ms": duration_ms,
                    "hash": "",
                    "sensitive": sensitive,
                }

                from app.services.audit_log_service import audit_log_service
                asyncio.ensure_future(audit_log_service.enqueue_log(entry))
            except Exception:
                logger.exception("Failed to enqueue audit log entry")
