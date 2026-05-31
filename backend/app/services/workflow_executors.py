from __future__ import annotations

import ast
import asyncio
import json
import re
from typing import Optional
from urllib import error as urllib_error
from urllib import request

from app.models.workflow import NodeType
from app.services.ssh_account_service import ssh_account_service


class BaseNodeExecutor:
    async def execute(self, config: dict, context: dict) -> dict:
        raise NotImplementedError


class ShellExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        command = config.get("command", "")
        account_alias = config.get("account_alias", "")
        working_dir = config.get("working_dir")
        env_vars = config.get("env_vars", {})

        if not command or not account_alias:
            return {"success": False, "output": {}, "error": "Missing command or account_alias"}

        try:
            result = await asyncio.to_thread(self._exec_ssh, account_alias, command, working_dir, env_vars)
            return result
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}

    def _exec_ssh(self, alias: str, command: str, working_dir: Optional[str], env_vars: dict) -> dict:
        account = ssh_account_service.get_account(alias)
        if account is None:
            return {"success": False, "output": {}, "error": f"SSH account '{alias}' not found"}

        full_command = command
        if working_dir:
            full_command = f"cd {working_dir} && {full_command}"
        if env_vars:
            env_prefix = " ".join(f"{k}={v}" for k, v in env_vars.items())
            full_command = f"export {env_prefix} && {full_command}"

        conn = ssh_account_service.pool.get_connection(account)
        try:
            code, stdout, stderr = conn.manager.exec_command(full_command, timeout=60.0)
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return {
                "success": code == 0,
                "output": {"exit_code": code, "stdout": stdout.strip(), "stderr": stderr.strip()},
                "error": stderr.strip() if code != 0 else None,
            }
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}
        finally:
            ssh_account_service.pool.release_connection(conn)


class HttpExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        url = config.get("url", "")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        timeout = config.get("timeout", 30)

        if not url:
            return {"success": False, "output": {}, "error": "Missing url"}

        try:
            result = await asyncio.to_thread(self._exec_http, url, method, headers, body, timeout)
            return result
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}

    def _exec_http(self, url: str, method: str, headers: dict, body: Optional[str], timeout: int) -> dict:
        try:
            req = request.Request(url, method=method)
            for k, v in headers.items():
                req.add_header(k, str(v))
            if body and method not in ("GET", "HEAD"):
                req.data = body.encode("utf-8")

            with request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                response_body = resp.read().decode("utf-8", errors="replace")
                return {
                    "success": 200 <= status_code < 300,
                    "output": {"status_code": status_code, "body": response_body},
                    "error": None,
                }
        except urllib_error.HTTPError as e:
            resp_body = ""
            try:
                resp_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            return {
                "success": False,
                "output": {"status_code": e.code, "body": resp_body},
                "error": str(e),
            }
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}


class ConditionExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        expression = config.get("expression", "")
        resolved = self._resolve_expression(expression, context)
        try:
            result = self._safe_eval(resolved)
            branch = "true" if result else "false"
            return {"success": True, "output": {"result": result, "branch": branch}, "error": None}
        except Exception as e:
            return {"success": False, "output": {"result": False, "branch": "false"}, "error": str(e)}

    def _resolve_expression(self, expression: str, context: dict) -> str:
        def replacer(match):
            path = match.group(1)
            parts = path.split(".", 1)
            node_id = parts[0]
            key = parts[1] if len(parts) > 1 else None
            node_output = context.get(node_id, {})
            if key and isinstance(node_output, dict):
                value = node_output.get(key)
            else:
                value = node_output
            if value is None:
                return "None"
            if isinstance(value, bool):
                return "True" if value else "False"
            if isinstance(value, (int, float)):
                return str(value)
            return repr(str(value))

        return re.sub(r"\$\{([^}]+)\}", replacer, expression)

    def _safe_eval(self, expression: str) -> bool:
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node) -> bool:
        if isinstance(node, ast.Compare):
            left = self._eval_value(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_value(comparator)
                if isinstance(op, ast.Eq):
                    if left != right:
                        return False
                elif isinstance(op, ast.NotEq):
                    if left == right:
                        return False
                elif isinstance(op, ast.Gt):
                    if not (left > right):
                        return False
                elif isinstance(op, ast.Lt):
                    if not (left < right):
                        return False
                elif isinstance(op, ast.GtE):
                    if not (left >= right):
                        return False
                elif isinstance(op, ast.LtE):
                    if not (left <= right):
                        return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v) for v in node.values)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval_node(node.operand)
        elif isinstance(node, ast.Constant):
            return bool(node.value)
        return False

    def _eval_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_value(node.operand)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return +self._eval_value(node.operand)
        return None


class LoopExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        loop_type = config.get("loop_type", "count")
        count = config.get("count", 0)
        items = config.get("items", [])
        condition_expr = config.get("condition", "")
        body_node_ids = config.get("body_node_ids", [])

        node_map = context.get("_node_map", {})
        executor_registry = context.get("_executors", {})

        iterations = self._build_iterations(loop_type, count, items, condition_expr, context)
        results = []

        for i, iteration_value in enumerate(iterations):
            iteration_context = dict(context)
            iteration_context["_loop_index"] = i
            iteration_context["_loop_value"] = iteration_value
            iteration_result = {}

            for node_id in body_node_ids:
                node_def = node_map.get(node_id, {})
                node_type_str = node_def.get("node_type", "")
                try:
                    node_type = NodeType(node_type_str)
                except ValueError:
                    continue
                executor = executor_registry.get(node_type)
                if not executor:
                    continue
                node_config = node_def.get("config", {})
                try:
                    result = await executor.execute(node_config, iteration_context)
                    iteration_result[node_id] = result.get("output", {})
                    iteration_context[node_id] = result.get("output", {})
                except Exception as e:
                    iteration_result[node_id] = {"error": str(e)}

            results.append(iteration_result)

        return {"success": True, "output": {"iterations": len(results), "results": results}, "error": None}

    def _build_iterations(self, loop_type: str, count: int, items: list, condition_expr: str, context: dict) -> list:
        if loop_type == "count":
            return list(range(count))
        elif loop_type == "iterate":
            return list(items)
        elif loop_type == "while":
            max_iterations = 100
            result = []
            for _ in range(max_iterations):
                if condition_expr:
                    resolved = ConditionExecutor()._resolve_expression(condition_expr, context)
                    try:
                        if not ConditionExecutor()._safe_eval(resolved):
                            break
                    except Exception:
                        break
                result.append(len(result))
            return result
        return []


class WaitExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        seconds = config.get("seconds", 0)
        try:
            await asyncio.sleep(int(seconds))
            return {"success": True, "output": {"waited_seconds": int(seconds)}, "error": None}
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}


class NotifyExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        channel = config.get("channel", "webhook")
        recipients = config.get("recipients", [])
        message = config.get("message", "")
        webhook_url = config.get("webhook_url")

        if channel == "webhook" and webhook_url:
            try:
                result = await asyncio.to_thread(self._send_webhook, webhook_url, message)
                return result
            except Exception as e:
                return {"success": False, "output": {}, "error": str(e)}
        else:
            return {
                "success": True,
                "output": {"channel": channel, "recipients": recipients, "message": message, "sent": False, "note": "placeholder"},
                "error": None,
            }

    def _send_webhook(self, webhook_url: str, message: str) -> dict:
        try:
            payload = json.dumps({"text": message}).encode("utf-8")
            req = request.Request(webhook_url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            with request.urlopen(req, timeout=15) as resp:
                return {
                    "success": 200 <= resp.status < 300,
                    "output": {"status_code": resp.status, "channel": "webhook"},
                    "error": None,
                }
        except urllib_error.HTTPError as e:
            return {"success": False, "output": {"status_code": e.code}, "error": str(e)}
        except Exception as e:
            return {"success": False, "output": {}, "error": str(e)}


class EndExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, context: dict) -> dict:
        return {"success": True, "output": {}, "error": None}


EXECUTOR_REGISTRY: dict[NodeType, BaseNodeExecutor] = {
    NodeType.TRIGGER_CRON: EndExecutor(),
    NodeType.TRIGGER_WEBHOOK: EndExecutor(),
    NodeType.TRIGGER_EVENT: EndExecutor(),
    NodeType.ACTION_SHELL: ShellExecutor(),
    NodeType.ACTION_HTTP: HttpExecutor(),
    NodeType.ACTION_SCRIPT: ShellExecutor(),
    NodeType.CONDITION: ConditionExecutor(),
    NodeType.LOOP: LoopExecutor(),
    NodeType.WAIT: WaitExecutor(),
    NodeType.NOTIFY: NotifyExecutor(),
    NodeType.END: EndExecutor(),
}
