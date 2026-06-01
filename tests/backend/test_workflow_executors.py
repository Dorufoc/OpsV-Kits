import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.models.workflow import NodeType


class TestBaseNodeExecutor:
    @pytest.mark.asyncio
    async def test_execute_not_implemented(self):
        from app.services.workflow_executors import BaseNodeExecutor
        executor = BaseNodeExecutor()
        with pytest.raises(NotImplementedError):
            await executor.execute({}, {})


class TestShellExecutor:
    @pytest.mark.asyncio
    async def test_missing_command(self):
        from app.services.workflow_executors import ShellExecutor
        executor = ShellExecutor()
        result = await executor.execute({"account_alias": "test"}, {})
        assert result["success"] is False
        assert "Missing" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_account_alias(self):
        from app.services.workflow_executors import ShellExecutor
        executor = ShellExecutor()
        result = await executor.execute({"command": "ls"}, {})
        assert result["success"] is False
        assert "Missing" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_command(self):
        from app.services.workflow_executors import ShellExecutor
        executor = ShellExecutor()
        result = await executor.execute({"command": "", "account_alias": "test"}, {})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_empty_account_alias(self):
        from app.services.workflow_executors import ShellExecutor
        executor = ShellExecutor()
        result = await executor.execute({"command": "ls", "account_alias": ""}, {})
        assert result["success"] is False

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_success(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "ls", None, {})
        assert result["success"] is True
        assert result["output"]["exit_code"] == 0
        mock_svc.pool.release_connection.assert_called_once_with(mock_conn)

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_account_not_found(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_svc.get_account.return_value = None

        executor = ShellExecutor()
        result = executor._exec_ssh("missing", "ls", None, {})
        assert result["success"] is False
        assert "not found" in result["error"]

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_with_working_dir(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "ls", "/home/user", {})
        assert result["success"] is True
        cmd = mock_conn.manager.exec_command.call_args[0][0]
        assert cmd.startswith("cd /home/user &&")

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_with_env_vars(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "output", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "ls", None, {"FOO": "bar", "BAZ": "1"})
        assert result["success"] is True
        cmd = mock_conn.manager.exec_command.call_args[0][0]
        assert "export" in cmd
        assert "FOO=bar" in cmd

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_nonzero_exit(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (1, "", "error msg")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "bad_cmd", None, {})
        assert result["success"] is False
        assert result["error"] == "error msg"

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_bytes_output(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, b"output", b"err")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "ls", None, {})
        assert result["success"] is True
        assert result["output"]["stdout"] == "output"

    @patch("app.services.workflow_executors.ssh_account_service")
    def test_exec_ssh_exception(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.side_effect = Exception("exec fail")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = executor._exec_ssh("test", "ls", None, {})
        assert result["success"] is False
        assert "exec fail" in result["error"]

    @pytest.mark.asyncio
    @patch("app.services.workflow_executors.ssh_account_service")
    async def test_execute_success(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.return_value = (0, "ok", "")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = await executor.execute({"command": "ls", "account_alias": "test"}, {})
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("app.services.workflow_executors.ssh_account_service")
    async def test_execute_exception(self, mock_svc):
        from app.services.workflow_executors import ShellExecutor
        mock_account = MagicMock()
        mock_svc.get_account.return_value = mock_account
        mock_conn = MagicMock()
        mock_conn.manager.exec_command.side_effect = Exception("exec error")
        mock_svc.pool.get_connection.return_value = mock_conn

        executor = ShellExecutor()
        result = await executor.execute({"command": "ls", "account_alias": "test"}, {})
        assert result["success"] is False


class TestHttpExecutor:
    @pytest.mark.asyncio
    async def test_missing_url(self):
        from app.services.workflow_executors import HttpExecutor
        executor = HttpExecutor()
        result = await executor.execute({}, {})
        assert result["success"] is False
        assert "Missing url" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_url(self):
        from app.services.workflow_executors import HttpExecutor
        executor = HttpExecutor()
        result = await executor.execute({"url": ""}, {})
        assert result["success"] is False

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_get_success(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "GET", {}, None, 30)
        assert result["success"] is True
        assert result["output"]["status_code"] == 200

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_post_with_body(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.read.return_value = b"created"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "POST", {}, '{"key":"val"}', 30)
        assert result["success"] is True

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_get_with_body_ignored(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "GET", {}, "body", 30)
        req_call = mock_urlopen.call_args
        req_obj = req_call[0][0]
        assert req_obj.data is None

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_head_with_body_ignored(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "HEAD", {}, "body", 30)
        req_call = mock_urlopen.call_args
        req_obj = req_call[0][0]
        assert req_obj.data is None

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_server_error(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        from urllib import error as urllib_error
        mock_urlopen.side_effect = urllib_error.HTTPError(
            "http://example.com", 500, "Server Error", {}, None
        )

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "GET", {}, None, 30)
        assert result["success"] is False
        assert result["output"]["status_code"] == 500

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_connection_error(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_urlopen.side_effect = Exception("connection refused")

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "GET", {}, None, 30)
        assert result["success"] is False
        assert "connection refused" in result["error"]

    @patch("app.services.workflow_executors.request.urlopen")
    def test_exec_http_with_headers(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = executor._exec_http("http://example.com", "GET", {"Authorization": "Bearer token"}, None, 30)
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("app.services.workflow_executors.request.urlopen")
    async def test_execute_success(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"ok"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = HttpExecutor()
        result = await executor.execute({"url": "http://example.com"}, {})
        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("app.services.workflow_executors.request.urlopen")
    async def test_execute_exception(self, mock_urlopen):
        from app.services.workflow_executors import HttpExecutor
        mock_urlopen.side_effect = Exception("network error")

        executor = HttpExecutor()
        result = await executor.execute({"url": "http://example.com"}, {})
        assert result["success"] is False


class TestConditionExecutor:
    @pytest.mark.asyncio
    async def test_true_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 == 1"}, {})
        assert result["success"] is True
        assert result["output"]["branch"] == "true"

    @pytest.mark.asyncio
    async def test_false_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 == 2"}, {})
        assert result["success"] is True
        assert result["output"]["branch"] == "false"

    @pytest.mark.asyncio
    async def test_gt_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "5 > 3"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_lt_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "3 < 5"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_gte_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "5 >= 5"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_lte_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "3 <= 3"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_neq_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 != 2"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_and_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 == 1 and 2 == 2"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_or_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 == 2 or 2 == 2"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_not_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "not 1 == 2"}, {})
        assert result["success"] is True
        assert result["output"]["result"] is True

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": "1 = 2"}, {})
        assert result["success"] is False
        assert result["output"]["branch"] == "false"

    @pytest.mark.asyncio
    async def test_empty_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = await executor.execute({"expression": ""}, {})
        assert result["success"] is False

    def test_resolve_expression_simple(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.status_code} == 200", {"n1": {"status_code": 200}})
        assert "200" in result

    def test_resolve_expression_none_value(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.missing} == 1", {"n1": {}})
        assert "None" in result

    def test_resolve_expression_bool_value(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.active} == True", {"n1": {"active": True}})
        assert "True" in result

    def test_resolve_expression_int_value(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.count} > 0", {"n1": {"count": 5}})
        assert "5" in result

    def test_resolve_expression_string_value(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.name} == 'test'", {"n1": {"name": "test"}})
        assert "'test'" in result

    def test_resolve_expression_no_key(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1} == True", {"n1": True})
        assert "True" in result

    def test_resolve_expression_no_match(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("1 == 1", {})
        assert result == "1 == 1"

    def test_safe_eval_constant_true(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._safe_eval("True")
        assert result is True

    def test_safe_eval_constant_false(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._safe_eval("False")
        assert result is False

    def test_safe_eval_chained_comparison(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._safe_eval("1 < 2 < 3")
        assert result is True

    def test_safe_eval_negative_number(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._safe_eval("-1 < 0")
        assert result is True

    def test_safe_eval_positive_unary(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._safe_eval("+1 == 1")
        assert result is True

    def test_eval_value_none(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._eval_value(MagicMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_float_expression(self):
        from app.services.workflow_executors import ConditionExecutor
        executor = ConditionExecutor()
        result = executor._resolve_expression("${n1.value} > 0.5", {"n1": {"value": 0.8}})
        assert "0.8" in result


class TestLoopExecutor:
    @pytest.mark.asyncio
    async def test_count_loop(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {"loop_type": "count", "count": 3, "body_node_ids": []},
            {},
        )
        assert result["success"] is True
        assert result["output"]["iterations"] == 3

    @pytest.mark.asyncio
    async def test_iterate_loop(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {"loop_type": "iterate", "items": ["a", "b", "c"], "body_node_ids": []},
            {},
        )
        assert result["success"] is True
        assert result["output"]["iterations"] == 3

    @pytest.mark.asyncio
    async def test_while_loop(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {"loop_type": "while", "condition": "1 == 2", "body_node_ids": []},
            {},
        )
        assert result["success"] is True
        assert result["output"]["iterations"] == 0

    @pytest.mark.asyncio
    async def test_while_loop_max_iterations(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {"loop_type": "while", "condition": "1 == 1", "body_node_ids": []},
            {},
        )
        assert result["success"] is True
        assert result["output"]["iterations"] == 100

    @pytest.mark.asyncio
    async def test_unknown_loop_type(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {"loop_type": "unknown", "body_node_ids": []},
            {},
        )
        assert result["success"] is True
        assert result["output"]["iterations"] == 0

    @pytest.mark.asyncio
    async def test_loop_with_body_nodes(self):
        from app.services.workflow_executors import LoopExecutor
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = {"success": True, "output": {"result": "ok"}, "error": None}

        executor = LoopExecutor()
        result = await executor.execute(
            {
                "loop_type": "count",
                "count": 2,
                "body_node_ids": ["n1"],
            },
            {
                "_node_map": {"n1": {"node_type": "action_shell", "config": {"command": "ls"}}},
                "_executors": {NodeType.ACTION_SHELL: mock_executor},
            },
        )
        assert result["success"] is True
        assert mock_executor.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_loop_body_node_unknown_type(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {
                "loop_type": "count",
                "count": 1,
                "body_node_ids": ["n1"],
            },
            {
                "_node_map": {"n1": {"node_type": "unknown_type", "config": {}}},
                "_executors": {},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_loop_body_node_no_executor(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = await executor.execute(
            {
                "loop_type": "count",
                "count": 1,
                "body_node_ids": ["n1"],
            },
            {
                "_node_map": {"n1": {"node_type": "action_shell", "config": {}}},
                "_executors": {},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_loop_body_node_exception(self):
        from app.services.workflow_executors import LoopExecutor
        mock_executor = AsyncMock()
        mock_executor.execute.side_effect = Exception("exec fail")

        executor = LoopExecutor()
        result = await executor.execute(
            {
                "loop_type": "count",
                "count": 1,
                "body_node_ids": ["n1"],
            },
            {
                "_node_map": {"n1": {"node_type": "action_shell", "config": {}}},
                "_executors": {NodeType.ACTION_SHELL: mock_executor},
            },
        )
        assert result["success"] is True
        assert any("error" in r for r in result["output"]["results"][0].values())

    def test_build_iterations_count(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = executor._build_iterations("count", 5, [], "", {})
        assert result == [0, 1, 2, 3, 4]

    def test_build_iterations_iterate(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = executor._build_iterations("iterate", 0, ["x", "y"], "", {})
        assert result == ["x", "y"]

    def test_build_iterations_while_condition_false(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = executor._build_iterations("while", 0, [], "1 == 2", {})
        assert result == []

    def test_build_iterations_while_condition_exception(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = executor._build_iterations("while", 0, [], "invalid ###", {})
        assert result == []

    def test_build_iterations_while_empty_condition(self):
        from app.services.workflow_executors import LoopExecutor
        executor = LoopExecutor()
        result = executor._build_iterations("while", 0, [], "", {})
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_loop_iteration_context(self):
        from app.services.workflow_executors import LoopExecutor
        captured_contexts = []
        mock_executor = AsyncMock()
        async def capture_execute(config, context):
            captured_contexts.append(dict(context))
            return {"success": True, "output": {}, "error": None}
        mock_executor.execute.side_effect = capture_execute

        executor = LoopExecutor()
        result = await executor.execute(
            {
                "loop_type": "iterate",
                "items": ["a", "b"],
                "body_node_ids": ["n1"],
            },
            {
                "_node_map": {"n1": {"node_type": "action_shell", "config": {}}},
                "_executors": {NodeType.ACTION_SHELL: mock_executor},
            },
        )
        assert captured_contexts[0]["_loop_index"] == 0
        assert captured_contexts[0]["_loop_value"] == "a"
        assert captured_contexts[1]["_loop_index"] == 1
        assert captured_contexts[1]["_loop_value"] == "b"


class TestWaitExecutor:
    @pytest.mark.asyncio
    async def test_wait_success(self):
        from app.services.workflow_executors import WaitExecutor
        executor = WaitExecutor()
        result = await executor.execute({"seconds": 0}, {})
        assert result["success"] is True
        assert result["output"]["waited_seconds"] == 0

    @pytest.mark.asyncio
    async def test_wait_default_seconds(self):
        from app.services.workflow_executors import WaitExecutor
        executor = WaitExecutor()
        result = await executor.execute({}, {})
        assert result["success"] is True
        assert result["output"]["waited_seconds"] == 0

    @pytest.mark.asyncio
    async def test_wait_exception(self):
        from app.services.workflow_executors import WaitExecutor
        executor = WaitExecutor()
        with patch("asyncio.sleep", side_effect=Exception("interrupted")):
            result = await executor.execute({"seconds": 5}, {})
            assert result["success"] is False
            assert "interrupted" in result["error"]


class TestNotifyExecutor:
    @pytest.mark.asyncio
    async def test_webhook_success(self):
        from app.services.workflow_executors import NotifyExecutor
        with patch.object(NotifyExecutor, "_send_webhook", return_value={"success": True, "output": {"status_code": 200, "channel": "webhook"}, "error": None}):
            executor = NotifyExecutor()
            result = await executor.execute(
                {"channel": "webhook", "webhook_url": "http://hook.example.com", "message": "hello"},
                {},
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_webhook_exception(self):
        from app.services.workflow_executors import NotifyExecutor
        with patch.object(NotifyExecutor, "_send_webhook", side_effect=Exception("send fail")):
            executor = NotifyExecutor()
            result = await executor.execute(
                {"channel": "webhook", "webhook_url": "http://hook.example.com", "message": "hello"},
                {},
            )
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_non_webhook_channel(self):
        from app.services.workflow_executors import NotifyExecutor
        executor = NotifyExecutor()
        result = await executor.execute(
            {"channel": "email", "recipients": ["user@example.com"], "message": "hello"},
            {},
        )
        assert result["success"] is True
        assert result["output"]["sent"] is False
        assert result["output"]["note"] == "placeholder"

    @pytest.mark.asyncio
    async def test_webhook_no_url(self):
        from app.services.workflow_executors import NotifyExecutor
        executor = NotifyExecutor()
        result = await executor.execute(
            {"channel": "webhook", "message": "hello"},
            {},
        )
        assert result["success"] is True
        assert result["output"]["sent"] is False

    @patch("app.services.workflow_executors.request.urlopen")
    def test_send_webhook_success(self, mock_urlopen):
        from app.services.workflow_executors import NotifyExecutor
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        executor = NotifyExecutor()
        result = executor._send_webhook("http://hook.example.com", "hello")
        assert result["success"] is True

    @patch("app.services.workflow_executors.request.urlopen")
    def test_send_webhook_http_error(self, mock_urlopen):
        from app.services.workflow_executors import NotifyExecutor
        from urllib import error as urllib_error
        mock_urlopen.side_effect = urllib_error.HTTPError(
            "http://hook.example.com", 500, "Error", {}, None
        )

        executor = NotifyExecutor()
        result = executor._send_webhook("http://hook.example.com", "hello")
        assert result["success"] is False
        assert result["output"]["status_code"] == 500

    @patch("app.services.workflow_executors.request.urlopen")
    def test_send_webhook_exception(self, mock_urlopen):
        from app.services.workflow_executors import NotifyExecutor
        mock_urlopen.side_effect = Exception("connection fail")

        executor = NotifyExecutor()
        result = executor._send_webhook("http://hook.example.com", "hello")
        assert result["success"] is False
        assert "connection fail" in result["error"]

    @pytest.mark.asyncio
    async def test_default_channel(self):
        from app.services.workflow_executors import NotifyExecutor
        executor = NotifyExecutor()
        result = await executor.execute({"message": "hello"}, {})
        assert result["success"] is True
        assert result["output"]["channel"] == "webhook"


class TestEndExecutor:
    @pytest.mark.asyncio
    async def test_end_executor(self):
        from app.services.workflow_executors import EndExecutor
        executor = EndExecutor()
        result = await executor.execute({}, {})
        assert result["success"] is True
        assert result["output"] == {}
        assert result["error"] is None


class TestExecutorRegistry:
    def test_registry_has_all_types(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY
        expected_types = [
            NodeType.TRIGGER_CRON,
            NodeType.TRIGGER_WEBHOOK,
            NodeType.TRIGGER_EVENT,
            NodeType.ACTION_SHELL,
            NodeType.ACTION_HTTP,
            NodeType.ACTION_SCRIPT,
            NodeType.CONDITION,
            NodeType.LOOP,
            NodeType.WAIT,
            NodeType.NOTIFY,
            NodeType.END,
        ]
        for nt in expected_types:
            assert nt in EXECUTOR_REGISTRY

    def test_trigger_types_use_end_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, EndExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.TRIGGER_CRON], EndExecutor)
        assert isinstance(EXECUTOR_REGISTRY[NodeType.TRIGGER_WEBHOOK], EndExecutor)
        assert isinstance(EXECUTOR_REGISTRY[NodeType.TRIGGER_EVENT], EndExecutor)

    def test_shell_and_script_use_same_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, ShellExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.ACTION_SHELL], ShellExecutor)
        assert isinstance(EXECUTOR_REGISTRY[NodeType.ACTION_SCRIPT], ShellExecutor)

    def test_http_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, HttpExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.ACTION_HTTP], HttpExecutor)

    def test_condition_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, ConditionExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.CONDITION], ConditionExecutor)

    def test_loop_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, LoopExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.LOOP], LoopExecutor)

    def test_wait_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, WaitExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.WAIT], WaitExecutor)

    def test_notify_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, NotifyExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.NOTIFY], NotifyExecutor)

    def test_end_executor(self):
        from app.services.workflow_executors import EXECUTOR_REGISTRY, EndExecutor
        assert isinstance(EXECUTOR_REGISTRY[NodeType.END], EndExecutor)
