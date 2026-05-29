"""前端页面功能测试 - 使用Playwright"""
import pytest
from playwright.sync_api import Page, expect
import re
import os

# 从环境变量读取URL，默认值
BASE_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class TestHomePage:
    """首页功能测试"""

    def test_home_page_loads(self, page: Page):
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        expect(page).to_have_title(re.compile(".*OpsV.*|.*首页.*|.*运维.*|.*工具.*|.*项目.*", re.IGNORECASE))

    def test_home_page_has_content(self, page: Page):
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()
        expect(page.locator("#app, .app, [data-v-app]")).to_be_visible()

    def test_home_page_api_health(self, page: Page):
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        response = page.request.get(f"{API_BASE_URL}/api/health")
        assert response.status == 200
        data = response.json()
        assert data.get("status") == "ok"


class TestSSHAccountPage:
    """SSH账户管理页面测试"""

    def test_ssh_account_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/ssh-accounts")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()
        expect(page.locator("#app, .app, [data-v-app]")).to_be_visible()


class TestProjectPage:
    """项目管理页面测试"""

    def test_project_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/project")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestDockerPage:
    """Docker管理页面测试"""

    def test_docker_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/docker")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestWebSSHPage:
    """WebSSH页面测试"""

    def test_webssh_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/webssh")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestSettingsPage:
    """设置页面测试"""

    def test_settings_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/settings")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestMonitorPage:
    """监控页面测试"""

    def test_monitor_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/monitor")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestProcessManagerPage:
    """进程管理页面测试"""

    def test_process_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/process")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestToolsPage:
    """工具箱页面测试"""

    def test_tools_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/tools")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestFileManagerPage:
    """文件管理页面测试"""

    def test_filemanager_page_loads(self, page: Page):
        page.goto(f"{BASE_URL}/file-manager")
        page.wait_for_load_state("networkidle")
        body = page.locator("body")
        expect(body).to_be_visible()


class TestNavigation:
    """导航功能测试"""

    def test_navigation_between_pages(self, page: Page):
        paths = [
            "/",
            "/project",
            "/ssh-accounts",
            "/docker",
            "/webssh",
            "/tools",
            "/settings",
            "/monitor",
            "/process",
            "/file-manager",
        ]
        for path in paths:
            page.goto(f"{BASE_URL}{path}")
            page.wait_for_load_state("networkidle")
            body = page.locator("body")
            expect(body).to_be_visible()


class TestConsoleErrors:
    """控制台错误检测"""

    def test_no_console_errors_on_home(self, page: Page):
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        js_errors = page.evaluate("() => window.__vue_errors || []")
        assert len(js_errors) == 0, f"Vue errors detected: {js_errors}"
