"""同步接口测试 - 全面覆盖同步API路由

测试范围：
- POST /api/sync/start - 启动同步任务
- POST /api/sync/stop - 停止同步任务
- GET /api/sync/status/{sync_id} - 查询指定任务状态（路径参数）
- GET /api/sync/status?sync_id=xxx - 查询指定任务状态（查询参数）
- GET /api/sync/status - 查询所有任务状态
- WebSocket /api/sync/ws/status - WebSocket 实时状态推送
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from app.main import app


@pytest.fixture
def client():
    """创建FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_sync_service():
    """创建同步服务的mock对象，配置异步方法为AsyncMock"""
    with patch("app.api.routes.sync.sync_service") as mock_svc:
        # 确保异步方法默认可被await
        mock_svc.register_ws = AsyncMock()
        mock_svc.unregister_ws = AsyncMock()
        yield mock_svc


class TestSyncStart:
    """测试启动同步任务接口 POST /api/sync/start"""

    def test_start_sync_success(self, mock_sync_service, client):
        """测试成功启动同步任务"""
        mock_sync_service.start_sync = AsyncMock(return_value="sync-abc-123")

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
                "account_alias": "prod-server",
                "force": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sync_id"] == "sync-abc-123"
        assert data["message"] == "同步任务已启动"

    def test_start_sync_with_force_flag(self, mock_sync_service, client):
        """测试强制全量同步模式"""
        mock_sync_service.start_sync = AsyncMock(return_value="sync-force-001")

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
                "account_alias": "prod-server",
                "force": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sync_id"] == "sync-force-001"
        # 验证force参数被传递
        mock_sync_service.start_sync.assert_called_once_with(
            local_path="E:/projects/myapp",
            remote_path="/home/user/deploy",
            account_alias="prod-server",
            force=True,
        )

    def test_start_sync_with_default_force(self, mock_sync_service, client):
        """测试force参数使用默认值False"""
        mock_sync_service.start_sync = AsyncMock(return_value="sync-default-001")

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
                "account_alias": "test-server",
            },
        )
        assert response.status_code == 200
        # 验证force默认为False
        mock_sync_service.start_sync.assert_called_once_with(
            local_path="E:/projects/myapp",
            remote_path="/home/user/deploy",
            account_alias="test-server",
            force=False,
        )

    def test_start_sync_missing_required_fields(self, client):
        """测试缺少必填字段时返回422错误"""
        response = client.post("/api/sync/start", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_start_sync_missing_local_path(self, client):
        """测试缺少local_path字段"""
        response = client.post(
            "/api/sync/start",
            json={
                "remote_path": "/home/user/deploy",
                "account_alias": "test-server",
            },
        )
        assert response.status_code == 422

    def test_start_sync_missing_remote_path(self, client):
        """测试缺少remote_path字段"""
        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "account_alias": "test-server",
            },
        )
        assert response.status_code == 422

    def test_start_sync_missing_account_alias(self, client):
        """测试缺少account_alias字段"""
        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
            },
        )
        assert response.status_code == 422

    def test_start_sync_account_not_found(self, mock_sync_service, client):
        """测试SSH账户不存在时返回400错误"""
        mock_sync_service.start_sync = AsyncMock(
            side_effect=ValueError("SSH 账户 'nonexistent' 不存在")
        )

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
                "account_alias": "nonexistent",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "SSH 账户" in data["detail"]

    def test_start_sync_internal_error(self, mock_sync_service, client):
        """测试服务层异常时返回500错误"""
        mock_sync_service.start_sync = AsyncMock(
            side_effect=Exception("SSH连接超时")
        )

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/myapp",
                "remote_path": "/home/user/deploy",
                "account_alias": "test-server",
            },
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "启动同步失败" in data["detail"]

    def test_start_sync_with_windows_paths(self, mock_sync_service, client):
        """测试Windows路径格式"""
        mock_sync_service.start_sync = AsyncMock(return_value="sync-win-001")

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:\\projects\\myapp\\src",
                "remote_path": "/home/user/deploy/myapp",
                "account_alias": "windows-server",
                "force": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["sync_id"] == "sync-win-001"

    def test_start_sync_with_unix_paths(self, mock_sync_service, client):
        """测试Unix路径格式"""
        mock_sync_service.start_sync = AsyncMock(return_value="sync-unix-001")

        response = client.post(
            "/api/sync/start",
            json={
                "local_path": "/home/dev/projects/myapp",
                "remote_path": "/var/www/deploy",
                "account_alias": "linux-server",
                "force": True,
            },
        )
        assert response.status_code == 200
        assert response.json()["sync_id"] == "sync-unix-001"


class TestSyncStop:
    """测试停止同步任务接口 POST /api/sync/stop"""

    def test_stop_sync_success(self, mock_sync_service, client):
        """测试成功停止同步任务"""
        mock_sync_service.stop_sync.return_value = True

        response = client.post(
            "/api/sync/stop",
            json={"sync_id": "sync-abc-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "同步已停止"
        mock_sync_service.stop_sync.assert_called_once_with("sync-abc-123")

    def test_stop_sync_task_not_found(self, mock_sync_service, client):
        """测试停止不存在的任务"""
        mock_sync_service.stop_sync.return_value = False

        response = client.post(
            "/api/sync/stop",
            json={"sync_id": "nonexistent-sync-id"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "任务不存在或已完成"

    def test_stop_sync_missing_sync_id(self, client):
        """测试缺少sync_id字段"""
        response = client.post("/api/sync/stop", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_stop_sync_empty_body(self, client):
        """测试空请求体"""
        response = client.post("/api/sync/stop", content="")
        # FastAPI无法解析JSON时返回422
        assert response.status_code == 422

    def test_stop_sync_already_completed(self, mock_sync_service, client):
        """测试停止已完成的任务"""
        mock_sync_service.stop_sync.return_value = False

        response = client.post(
            "/api/sync/stop",
            json={"sync_id": "sync-completed-001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_stop_sync_already_failed(self, mock_sync_service, client):
        """测试停止已失败的任务"""
        mock_sync_service.stop_sync.return_value = False

        response = client.post(
            "/api/sync/stop",
            json={"sync_id": "sync-failed-001"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is False


class TestSyncStatusByPath:
    """测试查询指定任务状态接口 GET /api/sync/status/{sync_id}（路径参数方式）"""

    def test_get_status_success(self, mock_sync_service, client):
        """测试成功获取任务状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-abc-123",
            "status": "running",
            "progress": 45.5,
            "phase": "uploading",
            "message": "正在同步文件...",
            "local_path": "E:/projects/myapp",
            "remote_path": "/home/user/deploy",
            "account_alias": "prod-server",
            "force": False,
            "started_at": "2024-01-01T10:00:00+00:00",
        }

        response = client.get("/api/sync/status/sync-abc-123")
        assert response.status_code == 200
        data = response.json()
        assert data["sync_id"] == "sync-abc-123"
        assert data["status"] == "running"
        assert data["progress"] == 45.5
        mock_sync_service.get_status.assert_called_once_with("sync-abc-123")

    def test_get_status_completed(self, mock_sync_service, client):
        """测试获取已完成任务的状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-done-001",
            "status": "completed",
            "progress": 100.0,
            "message": "同步完成",
            "file_changes": {
                "new": ["file1.txt", "file2.txt"],
                "modified": ["config.yaml"],
                "deleted": [],
            },
            "tree": "myapp/\n  file1.txt\n  file2.txt",
            "diff_tree": "  myapp/\n  new file1.txt",
        }

        response = client.get("/api/sync/status/sync-done-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        assert "file_changes" in data

    def test_get_status_failed(self, mock_sync_service, client):
        """测试获取失败任务的状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-fail-001",
            "status": "failed",
            "progress": 23.0,
            "error": "Connection refused",
            "message": "同步失败: Connection refused",
        }

        response = client.get("/api/sync/status/sync-fail-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Connection refused"

    def test_get_status_pending(self, mock_sync_service, client):
        """测试获取等待中任务的状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-pending-001",
            "status": "pending",
            "progress": 0.0,
            "message": "",
        }

        response = client.get("/api/sync/status/sync-pending-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0.0

    def test_get_status_stopped(self, mock_sync_service, client):
        """测试获取已停止任务的状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-stopped-001",
            "status": "stopped",
            "progress": 67.0,
            "message": "用户已停止同步",
        }

        response = client.get("/api/sync/status/sync-stopped-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_get_status_not_found(self, mock_sync_service, client):
        """测试查询不存在的任务返回404"""
        mock_sync_service.get_status.return_value = None

        response = client.get("/api/sync/status/nonexistent-sync-id")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "同步任务不存在" in data["detail"]


class TestSyncStatusByQuery:
    """测试查询指定任务状态接口 GET /api/sync/status?sync_id=xxx（查询参数方式）"""

    def test_get_status_with_query_param(self, mock_sync_service, client):
        """测试通过查询参数获取任务状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "sync-query-001",
            "status": "running",
            "progress": 78.5,
            "message": "正在同步...",
        }

        response = client.get("/api/sync/status?sync_id=sync-query-001")
        assert response.status_code == 200
        data = response.json()
        assert data["sync_id"] == "sync-query-001"
        assert data["status"] == "running"
        mock_sync_service.get_status.assert_called_once_with("sync-query-001")

    def test_get_status_query_not_found(self, mock_sync_service, client):
        """测试通过查询参数获取不存在的任务"""
        mock_sync_service.get_status.return_value = None

        response = client.get("/api/sync/status?sync_id=nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "同步任务不存在" in data["detail"]

    def test_get_all_status(self, mock_sync_service, client):
        """测试不传sync_id时获取所有任务状态列表"""
        mock_sync_service.get_status.return_value = [
            {
                "sync_id": "sync-001",
                "status": "running",
                "progress": 50.0,
            },
            {
                "sync_id": "sync-002",
                "status": "completed",
                "progress": 100.0,
            },
            {
                "sync_id": "sync-003",
                "status": "pending",
                "progress": 0.0,
            },
        ]

        response = client.get("/api/sync/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["sync_id"] == "sync-001"
        assert data[1]["sync_id"] == "sync-002"
        assert data[2]["sync_id"] == "sync-003"

    def test_get_all_status_empty_list(self, mock_sync_service, client):
        """测试无任务时返回空列表"""
        mock_sync_service.get_status.return_value = []

        response = client.get("/api/sync/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_all_status_mixed_states(self, mock_sync_service, client):
        """测试获取混合状态的任务列表"""
        mock_sync_service.get_status.return_value = [
            {"sync_id": "s1", "status": "running", "progress": 30.0},
            {"sync_id": "s2", "status": "failed", "progress": 45.0, "error": "timeout"},
            {"sync_id": "s3", "status": "stopped", "progress": 60.0},
            {"sync_id": "s4", "status": "completed", "progress": 100.0},
            {"sync_id": "s5", "status": "pending", "progress": 0.0},
        ]

        response = client.get("/api/sync/status")
        assert response.status_code == 200
        data = response.json()
        statuses = {item["sync_id"]: item["status"] for item in data}
        assert statuses == {
            "s1": "running",
            "s2": "failed",
            "s3": "stopped",
            "s4": "completed",
            "s5": "pending",
        }


class TestSyncWebSocket:
    """测试WebSocket实时状态推送接口 GET /api/sync/ws/status"""

    def test_ws_connect_and_receive_initial_status(self, mock_sync_service, client):
        """测试WebSocket连接成功后接收初始状态"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "ws-test-001",
            "status": "running",
            "progress": 50.0,
            "message": "正在同步...",
        }

        with client.websocket_connect("/api/sync/ws/status") as websocket:
            # 发送sync_id进行初始化
            websocket.send_json({"sync_id": "ws-test-001"})

            # 接收连接成功消息
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["sync_id"] == "ws-test-001"
            assert data["status"]["status"] == "running"

    def test_ws_ping_pong(self, mock_sync_service, client):
        """测试WebSocket ping/pong心跳机制"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "ws-ping-001",
            "status": "running",
            "progress": 50.0,
        }

        with client.websocket_connect("/api/sync/ws/status") as websocket:
            # 发送sync_id初始化
            websocket.send_json({"sync_id": "ws-ping-001"})
            # 接收connected消息
            websocket.receive_json()

            # 发送ping
            websocket.send_text("ping")

            # 接收pong响应
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_ws_missing_sync_id(self, mock_sync_service, client):
        """测试WebSocket连接时未提供sync_id"""
        with client.websocket_connect("/api/sync/ws/status") as websocket:
            # 发送空消息，不提供sync_id
            websocket.send_json({})

            # 接收错误消息
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "缺少 sync_id" in data["message"]

    def test_ws_empty_sync_id(self, mock_sync_service, client):
        """测试WebSocket连接时sync_id为空字符串"""
        with client.websocket_connect("/api/sync/ws/status") as websocket:
            websocket.send_json({"sync_id": ""})

            # 应该返回错误（因为空字符串被判断为 falsy）
            data = websocket.receive_json()
            assert data["type"] == "error"

    def test_ws_multiple_pings(self, mock_sync_service, client):
        """测试多次发送ping都能收到pong"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "ws-multi-ping-001",
            "status": "running",
            "progress": 50.0,
        }

        with client.websocket_connect("/api/sync/ws/status") as websocket:
            websocket.send_json({"sync_id": "ws-multi-ping-001"})
            websocket.receive_json()  # 接收connected

            # 发送多次ping
            for i in range(3):
                websocket.send_text("ping")
                data = websocket.receive_json()
                assert data["type"] == "pong"


class TestSyncStatusResponseStructure:
    """测试状态响应数据结构的完整性"""

    def test_status_response_contains_all_fields(self, mock_sync_service, client):
        """测试完整的状态响应包含所有预期字段"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "full-001",
            "local_path": "E:/projects/myapp",
            "remote_path": "/home/user/deploy",
            "account_alias": "prod-server",
            "force": False,
            "status": "running",
            "progress": 75.5,
            "phase": "syncing",
            "message": "正在同步文件...",
            "started_at": "2024-01-01T10:00:00+00:00",
            "completed_at": None,
            "error": None,
            "file_changes": {
                "new": ["new_file.txt"],
                "modified": ["existing.py"],
                "deleted": ["old_file.tmp"],
            },
            "diff_tree": "myapp/\n  new_file.txt [新增]",
            "tree": "myapp/\n  new_file.txt\n  existing.py",
        }

        response = client.get("/api/sync/status/full-001")
        assert response.status_code == 200
        data = response.json()

        # 验证所有核心字段存在
        required_fields = [
            "sync_id", "local_path", "remote_path", "account_alias",
            "force", "status", "progress", "phase", "message",
            "started_at", "completed_at", "error",
            "file_changes", "diff_tree", "tree",
        ]
        for field in required_fields:
            assert field in data, f"响应缺少字段: {field}"

    def test_status_without_optional_fields(self, mock_sync_service, client):
        """测试最小状态响应（仅包含必要字段）"""
        mock_sync_service.get_status.return_value = {
            "sync_id": "minimal-001",
            "status": "pending",
            "progress": 0.0,
            "phase": "",
            "message": "",
        }

        response = client.get("/api/sync/status/minimal-001")
        assert response.status_code == 200
        data = response.json()
        assert data["sync_id"] == "minimal-001"
        assert data["status"] == "pending"


class TestSyncIntegration:
    """集成测试 - 模拟完整工作流程"""

    def test_full_sync_lifecycle(self, mock_sync_service, client):
        """测试同步任务完整生命周期：启动 -> 查询状态 -> 停止"""
        # 1. 启动同步
        mock_sync_service.start_sync = AsyncMock(return_value="lifecycle-001")
        start_response = client.post(
            "/api/sync/start",
            json={
                "local_path": "E:/projects/app",
                "remote_path": "/home/user/app",
                "account_alias": "test-server",
                "force": False,
            },
        )
        assert start_response.status_code == 200
        sync_id = start_response.json()["sync_id"]

        # 2. 查询状态（运行中）
        mock_sync_service.get_status.return_value = {
            "sync_id": sync_id,
            "status": "running",
            "progress": 50.0,
        }
        status_response = client.get(f"/api/sync/status/{sync_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "running"

        # 3. 停止同步
        mock_sync_service.stop_sync.return_value = True
        stop_response = client.post(
            "/api/sync/stop",
            json={"sync_id": sync_id},
        )
        assert stop_response.status_code == 200
        assert stop_response.json()["success"] is True

        # 4. 查询状态（已停止）
        mock_sync_service.get_status.return_value = {
            "sync_id": sync_id,
            "status": "stopped",
            "progress": 50.0,
        }
        final_status = client.get(f"/api/sync/status/{sync_id}")
        assert final_status.status_code == 200
        assert final_status.json()["status"] == "stopped"

    def test_multiple_sync_tasks(self, mock_sync_service, client):
        """测试多个同步任务并行管理"""
        mock_sync_service.start_sync = AsyncMock(side_effect=["multi-001", "multi-002", "multi-003"])

        # 启动三个任务
        for i in range(3):
            resp = client.post(
                "/api/sync/start",
                json={
                    "local_path": f"E:/projects/app{i}",
                    "remote_path": f"/home/user/app{i}",
                    "account_alias": f"server-{i}",
                    "force": i == 0,
                },
            )
            assert resp.status_code == 200

        # 查询所有任务
        mock_sync_service.get_status.return_value = [
            {"sync_id": "multi-001", "status": "running", "progress": 100.0},
            {"sync_id": "multi-002", "status": "running", "progress": 50.0},
            {"sync_id": "multi-003", "status": "pending", "progress": 0.0},
        ]
        all_status = client.get("/api/sync/status")
        assert all_status.status_code == 200
        assert len(all_status.json()) == 3
