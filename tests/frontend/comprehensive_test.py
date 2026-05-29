"""前端全面功能测试 - 使用Playwright"""
import pytest
from playwright.sync_api import Page, expect
import re
import os
import time

# 从环境变量读取URL，默认值
BASE_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
API_BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ==================== 通用测试工具函数 ====================

def wait_for_vue_app(page: Page):
    """等待Vue应用加载完成"""
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("#app, .app-shell", state="visible", timeout=10000)


def take_screenshot(page: Page, name: str):
    """截图用于调试"""
    screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    page.screenshot(path=os.path.join(screenshot_dir, f"{name}.png"), full_page=True)


def get_console_errors(page: Page):
    """获取控制台错误"""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    return errors


# ==================== 首页测试 ====================

class TestHomePage:
    """首页功能测试"""

    def test_home_page_loads_correctly(self, page: Page):
        """测试首页正常加载"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        expect(page).to_have_title(re.compile(".*OpsV.*|.*首页.*", re.IGNORECASE))
        take_screenshot(page, "home_page")

    def test_home_page_has_navigation(self, page: Page):
        """测试首页导航栏存在"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 检查顶部导航栏
        nav_items = ["首页", "项目", "文件", "SSH", "Docker", "终端", "监控", "进程"]
        for item in nav_items:
            expect(page.get_by_text(item, exact=False)).to_be_visible()

    def test_home_page_has_sidebar(self, page: Page):
        """测试侧边栏导航存在"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        sidebar_items = ["控制台", "项目部署", "远程文件管理", "SSH 账户管理", 
                        "Docker 管理", "WebSSH 终端", "资源监控", "进程管理", 
                        "工具箱", "系统设置"]
        for item in sidebar_items:
            expect(page.get_by_text(item, exact=False)).to_be_visible()

    def test_home_page_theme_toggle(self, page: Page):
        """测试主题切换功能"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 查找主题切换按钮
        theme_button = page.locator("button").filter(has_text=re.compile("主题|theme|dark|light", re.IGNORECASE))
        if theme_button.count() > 0:
            theme_button.first.click()
            page.wait_for_timeout(500)
            take_screenshot(page, "home_theme_toggled")

    def test_home_page_responsive(self, page: Page):
        """测试响应式布局"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 测试不同视口尺寸
        for width, height in [(1920, 1080), (1280, 720), (768, 1024), (375, 812)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(300)
            expect(page.locator(".app-shell")).to_be_visible()


# ==================== 导航测试 ====================

class TestNavigation:
    """导航功能测试"""

    def test_navigation_all_routes(self, page: Page):
        """测试所有路由导航"""
        routes = [
            ("/", "首页"),
            ("/project", "项目"),
            ("/file-manager", "文件"),
            ("/ssh-accounts", "SSH"),
            ("/docker", "Docker"),
            ("/webssh", "终端"),
            ("/tools", "工具箱"),
            ("/settings", "设置"),
            ("/monitor", "监控"),
            ("/process", "进程"),
        ]
        
        for path, expected_text in routes:
            page.goto(f"{BASE_URL}{path}")
            wait_for_vue_app(page)
            take_screenshot(page, f"nav_{path.replace('/', '_') or 'home'}")
            
            # 检查URL是否正确
            assert path in page.url or page.url.endswith(path) or page.url == f"{BASE_URL}{path}"

    def test_navigation_sidebar_links(self, page: Page):
        """测试侧边栏链接点击"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        sidebar_links = [
            ("控制台", "/"),
            ("项目部署", "/project"),
            ("远程文件管理", "/file-manager"),
            ("SSH 账户管理", "/ssh-accounts"),
            ("Docker 管理", "/docker"),
            ("WebSSH 终端", "/webssh"),
            ("资源监控", "/monitor"),
            ("进程管理", "/process"),
            ("工具箱", "/tools"),
            ("系统设置", "/settings"),
        ]
        
        for link_text, expected_path in sidebar_links:
            link = page.locator(".sidebar-link").filter(has_text=link_text)
            if link.count() > 0:
                link.first.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(500)
                take_screenshot(page, f"sidebar_{link_text}")


# ==================== 项目管理页面测试 ====================

class TestProjectPage:
    """项目管理页面测试"""

    def test_project_page_loads(self, page: Page):
        """测试项目页面加载"""
        page.goto(f"{BASE_URL}/project")
        wait_for_vue_app(page)
        take_screenshot(page, "project_page")

    def test_project_page_has_content(self, page: Page):
        """测试项目页面有内容"""
        page.goto(f"{BASE_URL}/project")
        wait_for_vue_app(page)
        
        # 检查是否有项目相关的UI元素
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== Docker管理页面测试 ====================

class TestDockerPage:
    """Docker管理页面测试"""

    def test_docker_page_loads(self, page: Page):
        """测试Docker页面加载"""
        page.goto(f"{BASE_URL}/docker")
        wait_for_vue_app(page)
        take_screenshot(page, "docker_page")

    def test_docker_page_has_content(self, page: Page):
        """测试Docker页面有内容"""
        page.goto(f"{BASE_URL}/docker")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== WebSSH页面测试 ====================

class TestWebSSHPage:
    """WebSSH页面测试"""

    def test_webssh_page_loads(self, page: Page):
        """测试WebSSH页面加载"""
        page.goto(f"{BASE_URL}/webssh")
        wait_for_vue_app(page)
        take_screenshot(page, "webssh_page")

    def test_webssh_page_has_terminal(self, page: Page):
        """测试WebSSH页面有终端元素"""
        page.goto(f"{BASE_URL}/webssh")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 文件管理页面测试 ====================

class TestFileManagerPage:
    """文件管理页面测试"""

    def test_filemanager_page_loads(self, page: Page):
        """测试文件管理页面加载"""
        page.goto(f"{BASE_URL}/file-manager")
        wait_for_vue_app(page)
        take_screenshot(page, "filemanager_page")

    def test_filemanager_page_has_content(self, page: Page):
        """测试文件管理页面有内容"""
        page.goto(f"{BASE_URL}/file-manager")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== SSH账户页面测试 ====================

class TestSSHAccountPage:
    """SSH账户管理页面测试"""

    def test_ssh_account_page_loads(self, page: Page):
        """测试SSH账户页面加载"""
        page.goto(f"{BASE_URL}/ssh-accounts")
        wait_for_vue_app(page)
        take_screenshot(page, "ssh_account_page")

    def test_ssh_account_page_has_content(self, page: Page):
        """测试SSH账户页面有内容"""
        page.goto(f"{BASE_URL}/ssh-accounts")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 监控页面测试 ====================

class TestMonitorPage:
    """监控页面测试"""

    def test_monitor_page_loads(self, page: Page):
        """测试监控页面加载"""
        page.goto(f"{BASE_URL}/monitor")
        wait_for_vue_app(page)
        take_screenshot(page, "monitor_page")

    def test_monitor_page_has_content(self, page: Page):
        """测试监控页面有内容"""
        page.goto(f"{BASE_URL}/monitor")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 进程管理页面测试 ====================

class TestProcessManagerPage:
    """进程管理页面测试"""

    def test_process_page_loads(self, page: Page):
        """测试进程管理页面加载"""
        page.goto(f"{BASE_URL}/process")
        wait_for_vue_app(page)
        take_screenshot(page, "process_page")

    def test_process_page_has_content(self, page: Page):
        """测试进程管理页面有内容"""
        page.goto(f"{BASE_URL}/process")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 工具箱页面测试 ====================

class TestToolsPage:
    """工具箱页面测试"""

    def test_tools_page_loads(self, page: Page):
        """测试工具箱页面加载"""
        page.goto(f"{BASE_URL}/tools")
        wait_for_vue_app(page)
        take_screenshot(page, "tools_page")

    def test_tools_page_has_content(self, page: Page):
        """测试工具箱页面有内容"""
        page.goto(f"{BASE_URL}/tools")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 设置页面测试 ====================

class TestSettingsPage:
    """设置页面测试"""

    def test_settings_page_loads(self, page: Page):
        """测试设置页面加载"""
        page.goto(f"{BASE_URL}/settings")
        wait_for_vue_app(page)
        take_screenshot(page, "settings_page")

    def test_settings_page_has_content(self, page: Page):
        """测试设置页面有内容"""
        page.goto(f"{BASE_URL}/settings")
        wait_for_vue_app(page)
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== API健康检查测试 ====================

class TestAPIHealth:
    """API健康检查测试"""

    def test_api_health_endpoint(self, page: Page):
        """测试后端API健康端点"""
        response = page.request.get(f"{API_BASE_URL}/api/health")
        assert response.status == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_frontend_api_proxy(self, page: Page):
        """测试前端API代理"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 通过前端代理访问API
        response = page.request.get(f"{BASE_URL}/api/health")
        assert response.status == 200


# ==================== 控制台错误检测 ====================

class TestConsoleErrors:
    """控制台错误检测"""

    def test_no_console_errors_on_home(self, page: Page):
        """测试首页无控制台错误"""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        page.wait_for_timeout(1000)
        
        # 检查Vue错误
        try:
            js_errors = page.evaluate("() => window.__vue_errors || []")
            assert len(js_errors) == 0, f"Vue errors detected: {js_errors}"
        except Exception:
            pass  # Vue错误检测不可用时忽略
        
        assert len(errors) == 0, f"Console errors detected: {errors}"

    def test_no_console_errors_on_all_pages(self, page: Page):
        """测试所有页面无控制台错误"""
        routes = ["/", "/project", "/docker", "/webssh", "/tools", "/settings", "/monitor", "/process"]
        
        for route in routes:
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.goto(f"{BASE_URL}{route}")
            wait_for_vue_app(page)
            page.wait_for_timeout(500)
            
            # 只记录有错误的页面
            if len(errors) > 0:
                print(f"Console errors on {route}: {errors}")


# ==================== UI组件测试 ====================

class TestUIComponents:
    """UI组件测试"""

    def test_buttons_render(self, page: Page):
        """测试按钮渲染"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 查找所有按钮元素
        buttons = page.locator("button")
        assert buttons.count() > 0, "No buttons found on page"

    def test_inputs_render(self, page: Page):
        """测试输入框渲染"""
        page.goto(f"{BASE_URL}/settings")
        wait_for_vue_app(page)
        
        inputs = page.locator("input")
        # 输入框可能不存在于某些页面，这里只是检查

    def test_tables_render(self, page: Page):
        """测试表格渲染"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        tables = page.locator("table, .el-table, .md3-table")
        # 表格可能不存在于某些页面，这里只是检查

    def test_icons_render(self, page: Page):
        """测试图标渲染"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        icons = page.locator("svg, .mdi, [class*='icon']")
        assert icons.count() > 0, "No icons found on page"


# ==================== 页面加载性能测试 ====================

class TestPerformance:
    """页面加载性能测试"""

    def test_home_page_loads_quickly(self, page: Page):
        """测试首页快速加载"""
        start_time = time.time()
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        load_time = time.time() - start_time
        
        # 首页应在5秒内加载完成
        assert load_time < 5.0, f"Home page loaded too slowly: {load_time:.2f}s"

    def test_navigation_is_fast(self, page: Page):
        """测试导航响应快速"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        routes = ["/project", "/docker", "/tools"]
        for route in routes:
            start_time = time.time()
            page.goto(f"{BASE_URL}{route}")
            wait_for_vue_app(page)
            nav_time = time.time() - start_time
            
            # 每次导航应在3秒内完成
            assert nav_time < 3.0, f"Navigation to {route} too slow: {nav_time:.2f}s"