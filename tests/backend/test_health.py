"""健康检查接口测试"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthCheck:
    """健康检查API测试"""

    def test_health_check_success(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "OpsV-Kits API"
        assert "version" in data

    def test_health_check_response_structure(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert isinstance(data, dict)
        assert all(key in data for key in ["status", "service", "version"])
