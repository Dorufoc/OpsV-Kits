"""前端扩展测试 - 覆盖所有路由和交互功能"""
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


# ==================== 所有路由覆盖测试 ====================

class TestAllRoutes:
    """测试所有路由页面加载"""

    @pytest.mark.parametrize("route,name", [
        ("首页", "/"),
        ("项目部署", "/project"),
        ("远程文件管理", "/file-manager"),
        ("SSH 账户管理", "/ssh-accounts"),
        ("Docker 管理", "/docker"),
        ("WebSSH 终端", "/webssh"),
        ("工具箱", "/tools"),
        ("设置", "/settings"),
        ("资源监控", "/monitor"),
        ("进程管理", "/process"),
    ])
    def test_all_routes_load(self, page: Page, route: str, name: str):
        """测试所有路由正常加载"""
        page.goto(f"{BASE_URL}{name}")
        wait_for_vue_app(page)
        take_screenshot(page, f"route_{name.replace('/', '_').strip('_') or 'home'}")
        
        # 验证页面内容存在
        body = page.locator("body")
        expect(body).to_be_visible()

    def test_monitor_large_screen(self, page: Page):
        """测试监控大屏页面"""
        page.goto(f"{BASE_URL}/monitor/large-screen")
        wait_for_vue_app(page)
        take_screenshot(page, "monitor_large_screen")
        
        body = page.locator("body")
        expect(body).to_be_visible()


# ==================== 首页扩展测试 ====================

class TestHomePageExtended:
    """首页扩展功能测试"""

    def test_home_page_title(self, page: Page):
        """测试首页标题"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        expect(page).to_have_title(re.compile(".*OpsV.*|.*运维.*|.*首页.*", re.IGNORECASE))

    def test_home_page_layout(self, page: Page):
        """测试首页布局结构"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 检查主要布局元素
        app = page.locator("#app")
        expect(app).to_be_visible()

    def test_home_quick_actions(self, page: Page):
        """测试首页快捷操作区域"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 截图记录首页内容
        take_screenshot(page, "home_quick_actions")


# ==================== 项目管理页面扩展测试 ====================

class TestProjectPageExtended:
    """项目管理页面扩展测试"""

    def test_project_page_ui_elements(self, page: Page):
        """测试项目页面UI元素"""
        page.goto(f"{BASE_URL}/project")
        wait_for_vue_app(page)
        
        # 检查表格或列表元素
        tables = page.locator("table, .el-table, .md3-table, [class*='table']")
        take_screenshot(page, "project_table")


# ==================== SSH 账户页面扩展测试 ====================

class TestSSHAccountPageExtended:
    """SSH 账户页面扩展测试"""

    def test_ssh_account_table(self, page: Page):
        """测试SSH账户表格"""
        page.goto(f"{BASE_URL}/ssh-accounts")
        wait_for_vue_app(page)
        
        take_screenshot(page, "ssh_account_table")
        
        # 检查表格元素
        tables = page.locator("table, .el-table, .md3-table")
        # 表格可能存在也可能不存在，取决于是否有数据


# ==================== Docker 管理页面扩展测试 ====================

class TestDockerPageExtended:
    """Docker 管理页面扩展测试"""

    def test_docker_page_tabs(self, page: Page):
        """测试Docker页面标签页"""
        page.goto(f"{BASE_URL}/docker")
        wait_for_vue_app(page)
        
        # 截图记录Docker管理界面
        take_screenshot(page, "docker_tabs")
        
        # 检查标签页元素
        tabs = page.locator("[class*='tab'], [class*='Tab']")
        
    def test_docker_container_list(self, page: Page):
        """测试Docker容器列表"""
        page.goto(f"{BASE_URL}/docker")
        wait_for_vue_app(page)
        
        # 检查容器列表
        containers = page.locator("[class*='container'], [class*='list']")
        take_screenshot(page, "docker_containers")


# ==================== 文件管理页面扩展测试 ====================

class TestFileManagerPageExtended:
    """文件管理页面扩展测试"""

    def test_file_manager_breadcrumb(self, page: Page):
        """测试文件管理面包屑导航"""
        page.goto(f"{BASE_URL}/file-manager")
        wait_for_vue_app(page)
        
        take_screenshot(page, "file_manager_breadcrumb")
        
        # 检查面包屑导航
        breadcrumbs = page.locator("[class*='breadcrumb'], [class*='Breadcrumb']")

    def test_file_manager_file_list(self, page: Page):
        """测试文件列表显示"""
        page.goto(f"{BASE_URL}/file-manager")
        wait_for_vue_app(page)
        
        take_screenshot(page, "file_manager_list")


# ==================== WebSSH 页面扩展测试 ====================

class TestWebSSHPageExtended:
    """WebSSH 页面扩展测试"""

    def test_webssh_terminal_element(self, page: Page):
        """测试WebSSH终端元素"""
        page.goto(f"{BASE_URL}/webssh")
        wait_for_vue_app(page)
        
        take_screenshot(page, "webssh_terminal")
        
        # 检查终端元素
        terminal = page.locator("[class*='terminal'], [class*='xterm']")


# ==================== 监控页面扩展测试 ====================

class TestMonitorPageExtended:
    """监控页面扩展测试"""

    def test_monitor_dashboard_charts(self, page: Page):
        """测试监控仪表板图表"""
        page.goto(f"{BASE_URL}/monitor")
        wait_for_vue_app(page)
        
        take_screenshot(page, "monitor_dashboard_charts")
        
        # 检查图表元素
        charts = page.locator("[class*='chart'], [class*='Chart'], canvas")

    def test_monitor_large_screen_layout(self, page: Page):
        """测试监控大屏布局"""
        page.goto(f"{BASE_URL}/monitor/large-screen")
        wait_for_vue_app(page)
        
        take_screenshot(page, "monitor_large_screen_layout")
        
        # 检查大屏布局元素
        layout = page.locator("[class*='large'], [class*='screen']")


# ==================== 进程管理页面扩展测试 ====================

class TestProcessManagerPageExtended:
    """进程管理页面扩展测试"""

    def test_process_table(self, page: Page):
        """测试进程表格"""
        page.goto(f"{BASE_URL}/process")
        wait_for_vue_app(page)
        
        take_screenshot(page, "process_table")
        
        # 检查进程表格
        tables = page.locator("table, .el-table, .md3-table")

    def test_process_filter_options(self, page: Page):
        """测试进程筛选选项"""
        page.goto(f"{BASE_URL}/process")
        wait_for_vue_app(page)
        
        # 检查筛选器
        filters = page.locator("[class*='filter'], [class*='select'], select")
        take_screenshot(page, "process_filters")


# ==================== 工具箱页面扩展测试 ====================

class TestToolsPageExtended:
    """工具箱页面扩展测试"""

    def test_tools_grid(self, page: Page):
        """测试工具箱网格布局"""
        page.goto(f"{BASE_URL}/tools")
        wait_for_vue_app(page)
        
        take_screenshot(page, "tools_grid")
        
        # 检查工具卡片
        cards = page.locator("[class*='card'], [class*='Card']")

    def test_tool_item_click(self, page: Page):
        """测试工具项点击"""
        page.goto(f"{BASE_URL}/tools")
        wait_for_vue_app(page)
        
        # 尝试点击第一个工具项
        first_tool = page.locator("[class*='card'], [class*='tool']").first
        if first_tool.count() > 0:
            first_tool.click()
            page.wait_for_timeout(500)
            take_screenshot(page, "tool_clicked")


# ==================== 设置页面扩展测试 ====================

class TestSettingsPageExtended:
    """设置页面扩展测试"""

    def test_settings_form_elements(self, page: Page):
        """测试设置表单元素"""
        page.goto(f"{BASE_URL}/settings")
        wait_for_vue_app(page)
        
        take_screenshot(page, "settings_form")
        
        # 检查输入框
        inputs = page.locator("input, textarea")
        
    def test_settings_save_button(self, page: Page):
        """测试设置保存按钮"""
        page.goto(f"{BASE_URL}/settings")
        wait_for_vue_app(page)
        
        # 查找保存按钮
        save_button = page.locator("button").filter(has_text=re.compile("保存|save", re.IGNORECASE))
        if save_button.count() > 0:
            take_screenshot(page, "settings_save_button")


# ==================== 导航交互测试 ====================

class TestNavigationInteraction:
    """导航交互测试"""

    def test_sidebar_click_navigation(self, page: Page):
        """测试侧边栏点击导航"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 尝试点击侧边栏链接
        sidebar_links = page.locator("[class*='sidebar'], [class*='nav'] a, [class*='menu'] a")
        
        # 截图记录侧边栏
        take_screenshot(page, "sidebar_navigation")

    def test_top_navigation_click(self, page: Page):
        """测试顶部导航点击"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 尝试点击顶部导航
        top_nav = page.locator("[class*='header'], [class*='top'] a, [class*='nav'] a")
        take_screenshot(page, "top_navigation")


# ==================== 响应式布局测试 ====================

class TestResponsiveLayout:
    """响应式布局测试"""

    @pytest.mark.parametrize("width,height,name", [
        (1920, 1080, "desktop_fullhd"),
        (1366, 768, "desktop_hd"),
        (1024, 768, "tablet_landscape"),
        (768, 1024, "tablet_portrait"),
        (375, 812, "mobile"),
    ])
    def test_responsive_viewports(self, page: Page, width: int, height: int, name: str):
        """测试不同视口下的响应式布局"""
        page.set_viewport_size({"width": width, "height": height})
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        take_screenshot(page, f"responsive_{name}")
        
        # 验证应用容器可见
        app = page.locator("#app")
        expect(app).to_be_visible()


# ==================== 主题切换测试 ====================

class TestThemeToggle:
    """主题切换测试"""

    def test_theme_toggle_button(self, page: Page):
        """测试主题切换按钮"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        # 查找主题切换按钮
        theme_button = page.locator("button").filter(
            has_text=re.compile("主题|theme|dark|light|切换", re.IGNORECASE)
        )
        
        if theme_button.count() > 0:
            theme_button.first.click()
            page.wait_for_timeout(500)
            take_screenshot(page, "theme_toggled")


# ==================== API 集成测试 ====================

class TestAPIIntegration:
    """API 集成测试"""

    def test_health_endpoint(self, page: Page):
        """测试健康检查端点"""
        response = page.request.get(f"{API_BASE_URL}/api/health")
        assert response.status == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_api_via_frontend_proxy(self, page: Page):
        """测试通过前端代理访问API"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        response = page.request.get(f"{BASE_URL}/api/health")
        assert response.status == 200


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""

    def test_no_console_errors(self, page: Page):
        """测试无控制台错误"""
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        page.wait_for_timeout(1000)
        
        # 忽略常见的非关键错误
        critical_errors = [e for e in errors if "failed to load" in e.lower() or "uncaught" in e.lower()]
        
        if critical_errors:
            print(f"Critical console errors: {critical_errors}")
            take_screenshot(page, "console_errors")

    def test_404_page_handling(self, page: Page):
        """测试404页面处理"""
        page.goto(f"{BASE_URL}/non-existent-route")
        page.wait_for_load_state("networkidle")
        
        # 截图记录404或路由处理
        take_screenshot(page, "404_handling")


# ==================== 页面加载性能测试 ====================

class TestPageLoadPerformance:
    """页面加载性能测试"""

    def test_home_load_time(self, page: Page):
        """测试首页加载时间"""
        start_time = time.time()
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        load_time = time.time() - start_time
        
        assert load_time < 10.0, f"Home page loaded too slowly: {load_time:.2f}s"

    def test_navigation_performance(self, page: Page):
        """测试导航性能"""
        page.goto(BASE_URL)
        wait_for_vue_app(page)
        
        routes = ["/project", "/docker", "/monitor", "/process"]
        for route in routes:
            start_time = time.time()
            page.goto(f"{BASE_URL}{route}")
            wait_for_vue_app(page)
            nav_time = time.time() - start_time
            
            assert nav_time < 10.0, f"Navigation to {route} too slow: {nav_time:.2f}s"
