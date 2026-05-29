"""
前端功能测试脚本 - 使用 Playwright 进行浏览器自动化测试
此脚本会：
1. 打开浏览器并导航到前端页面
2. 遍历所有主要路由
3. 截图记录每个页面的状态
4. 检测控制台错误
5. 测试基本的交互功能
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright, Page, expect
import re

# 配置
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3001")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "test_results")

# 所有需要测试的路由
ROUTES = [
    {"path": "/", "name": "首页", "expected_elements": ["控制台", "SSH账户", "Docker容器"]},
    {"path": "/project", "name": "项目部署", "expected_elements": ["项目"]},
    {"path": "/file-manager", "name": "远程文件管理", "expected_elements": ["文件管理"]},
    {"path": "/ssh-accounts", "name": "SSH账户管理", "expected_elements": ["SSH", "账户"]},
    {"path": "/docker", "name": "Docker管理", "expected_elements": ["Docker", "容器"]},
    {"path": "/webssh", "name": "WebSSH终端", "expected_elements": ["WebSSH", "终端"]},
    {"path": "/tools", "name": "工具箱", "expected_elements": ["工具箱", "工具"]},
    {"path": "/settings", "name": "系统设置", "expected_elements": ["设置", "主题"]},
    {"path": "/monitor", "name": "资源监控", "expected_elements": ["监控", "CPU", "内存"]},
    {"path": "/monitor/large-screen", "name": "监控大屏", "expected_elements": ["监控"]},
    {"path": "/process", "name": "进程管理", "expected_elements": ["进程", "管理"]},
]


def wait_for_app_ready(page: Page, timeout: int = 15000):
    """等待 Vue 应用加载完成"""
    page.wait_for_load_state("domcontentloaded", timeout=timeout)
    page.wait_for_load_state("networkidle", timeout=timeout)
    # 等待应用容器出现
    try:
        page.wait_for_selector("#app", state="visible", timeout=timeout)
    except Exception:
        # 尝试其他可能的选择器
        try:
            page.wait_for_selector(".app-shell", state="visible", timeout=5000)
        except Exception:
            pass
    time.sleep(1)  # 等待 Vue 渲染完成


def capture_screenshot(page: Page, filename: str):
    """保存截图"""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    page.screenshot(path=filepath, full_page=True)
    return filepath


def collect_console_errors(page: Page):
    """收集控制台错误"""
    errors = []
    
    def handle_console(msg):
        if msg.type == "error":
            errors.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            })
    
    page.on("console", handle_console)
    return errors


def test_page_load(page: Page, route: dict) -> dict:
    """测试单个页面加载"""
    result = {
        "route": route["name"],
        "path": route["path"],
        "status": "pending",
        "errors": [],
        "screenshot": None,
        "page_title": None,
        "load_time": 0
    }
    
    try:
        url = f"{FRONTEND_URL}{route['path']}"
        print(f"\n📄 测试页面: {route['name']} ({url})")
        
        # 记录加载时间
        start_time = time.time()
        
        # 导航到页面
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 等待应用就绪
        wait_for_app_ready(page)
        
        # 计算加载时间
        result["load_time"] = round(time.time() - start_time, 2)
        
        # 获取页面标题
        result["page_title"] = page.title()
        
        # 收集控制台错误
        console_errors = collect_console_errors(page)
        result["errors"] = console_errors
        
        # 截图
        screenshot_name = f"page_{route['name']}.png".replace(" ", "_")
        result["screenshot"] = capture_screenshot(page, screenshot_name)
        
        # 检查预期元素
        found_elements = []
        for element_text in route.get("expected_elements", []):
            try:
                locator = page.get_by_text(element_text, exact=False)
                if locator.count() > 0:
                    found_elements.append(element_text)
            except Exception:
                pass
        
        result["found_elements"] = found_elements
        result["status"] = "passed"
        
        print(f"   ✅ 加载成功 (耗时: {result['load_time']}s)")
        print(f"   📌 标题: {result['page_title']}")
        print(f"   🔍 找到元素: {', '.join(found_elements)}")
        
        if console_errors:
            print(f"   ⚠️  控制台错误: {len(console_errors)} 个")
            for err in console_errors[:3]:
                print(f"      - {err['text'][:100]}")
        
    except Exception as e:
        result["status"] = "failed"
        result["error_message"] = str(e)
        print(f"   ❌ 测试失败: {str(e)[:100]}")
        
        # 即使失败也尝试截图
        try:
            screenshot_name = f"page_{route['name']}_error.png".replace(" ", "_")
            result["screenshot"] = capture_screenshot(page, screenshot_name)
        except Exception:
            pass
    
    return result


def test_navigation_flow(page: Page) -> dict:
    """测试导航流程"""
    result = {
        "test": "navigation_flow",
        "status": "pending",
        "steps": []
    }
    
    try:
        print(f"\n 测试导航流程...")
        
        # 从首页开始
        page.goto(f"{FRONTEND_URL}/", wait_until="domcontentloaded", timeout=15000)
        wait_for_app_ready(page)
        
        # 查找侧边栏导航项
        nav_items = page.locator("[class*='sidebar'], [class*='menu'] a, [class*='nav'] a, [class*='link']")
        nav_count = nav_items.count()
        
        result["steps"].append({
            "action": "find_navigation_items",
            "found": nav_count
        })
        
        # 截图首页
        capture_screenshot(page, "navigation_home.png")
        
        # 尝试点击导航项
        clicked_count = 0
        for i in range(min(3, nav_count)):
            try:
                nav_item = nav_items.nth(i)
                if nav_item.is_visible():
                    nav_item.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    time.sleep(0.5)
                    clicked_count += 1
                    
                    # 截图当前页面
                    capture_screenshot(page, f"navigation_click_{i+1}.png")
            except Exception as e:
                result["steps"].append({
                    "action": f"click_nav_item_{i}",
                    "status": "failed",
                    "error": str(e)[:50]
                })
        
        result["steps"].append({
            "action": "click_navigation_items",
            "clicked": clicked_count
        })
        
        result["status"] = "passed"
        print(f"   ✅ 导航测试完成 (点击了 {clicked_count} 个导航项)")
        
    except Exception as e:
        result["status"] = "failed"
        result["error_message"] = str(e)
        print(f"   ❌ 导航测试失败: {str(e)[:100]}")
    
    return result


def test_api_health(page: Page) -> dict:
    """测试后端 API 健康状态"""
    result = {
        "test": "api_health",
        "status": "pending"
    }
    
    try:
        print(f"\n 测试 API 健康状态...")
        
        # 直接请求健康检查端点
        response = page.request.get(f"{BACKEND_URL}/api/health", timeout=10000)
        
        result["status_code"] = response.status
        result["response_data"] = response.json()
        
        if response.status == 200:
            data = response.json()
            if data.get("status") == "ok":
                result["status"] = "passed"
                print(f"   ✅ API 健康检查通过")
            else:
                result["status"] = "failed"
                result["error_message"] = f"API 返回异常状态: {data}"
                print(f"   ❌ API 状态异常: {data}")
        else:
            result["status"] = "failed"
            result["error_message"] = f"HTTP {response.status}"
            print(f"   ❌ API 返回 HTTP {response.status}")
            
    except Exception as e:
        result["status"] = "failed"
        result["error_message"] = str(e)
        print(f"   ❌ API 测试失败: {str(e)[:100]}")
    
    return result


def test_responsive_layout(page: Page) -> dict:
    """测试响应式布局"""
    result = {
        "test": "responsive_layout",
        "status": "pending",
        "viewports": []
    }
    
    viewports = [
        {"width": 1920, "height": 1080, "name": "desktop_fullhd"},
        {"width": 1366, "height": 768, "name": "desktop_hd"},
        {"width": 768, "height": 1024, "name": "tablet"},
        {"width": 375, "height": 812, "name": "mobile"},
    ]
    
    try:
        print(f"\n 测试响应式布局...")
        
        for vp in viewports:
            page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            page.goto(f"{FRONTEND_URL}/", wait_until="domcontentloaded", timeout=15000)
            wait_for_app_ready(page)
            
            # 截图
            screenshot_name = f"responsive_{vp['name']}.png"
            capture_screenshot(page, screenshot_name)
            
            # 检查应用是否可见
            app_visible = False
            try:
                app = page.locator("#app")
                app_visible = app.count() > 0 and app.is_visible()
            except Exception:
                pass
            
            result["viewports"].append({
                "name": vp["name"],
                "width": vp["width"],
                "height": vp["height"],
                "app_visible": app_visible,
                "screenshot": screenshot_name
            })
            
            print(f"   📐 {vp['name']} ({vp['width']}x{vp['height']}): {'✅' if app_visible else '❌'}")
        
        result["status"] = "passed"
        
    except Exception as e:
        result["status"] = "failed"
        result["error_message"] = str(e)
        print(f"   ❌ 响应式测试失败: {str(e)[:100]}")
    
    return result


def main():
    """主测试函数"""
    print("=" * 60)
    print("OpsV-Kits 前端功能测试")
    print("=" * 60)
    print(f"前端地址: {FRONTEND_URL}")
    print(f"后端地址: {BACKEND_URL}")
    print(f"截图目录: {SCREENSHOT_DIR}")
    print("=" * 60)
    
    all_results = {
        "page_loads": [],
        "navigation": None,
        "api_health": None,
        "responsive": None,
        "summary": {}
    }
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        # 创建上下文
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # 创建页面
        page = context.new_page()
        
        try:
            # 1. 测试 API 健康
            all_results["api_health"] = test_api_health(page)
            
            # 2. 测试所有页面加载
            print("\n" + "=" * 60)
            print("测试所有页面加载")
            print("=" * 60)
            for route in ROUTES:
                result = test_page_load(page, route)
                all_results["page_loads"].append(result)
            
            # 3. 测试导航流程
            all_results["navigation"] = test_navigation_flow(page)
            
            # 4. 测试响应式布局
            all_results["responsive"] = test_responsive_layout(page)
            
        finally:
            browser.close()
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    # 统计结果
    total_pages = len(all_results["page_loads"])
    passed_pages = sum(1 for r in all_results["page_loads"] if r["status"] == "passed")
    failed_pages = total_pages - passed_pages
    
    print(f"\n📊 页面加载测试: {passed_pages}/{total_pages} 通过")
    
    for result in all_results["page_loads"]:
        status_icon = "✅" if result["status"] == "passed" else ""
        print(f"   {status_icon} {result['route']}: {result['load_time']}s")
    
    # 其他测试结果
    if all_results["api_health"]:
        status_icon = "✅" if all_results["api_health"]["status"] == "passed" else "❌"
        print(f"\n API 健康检查: {status_icon}")
    
    if all_results["navigation"]:
        status_icon = "✅" if all_results["navigation"]["status"] == "passed" else "❌"
        print(f"\n🧭 导航流程测试: {status_icon}")
    
    if all_results["responsive"]:
        status_icon = "✅" if all_results["responsive"]["status"] == "passed" else "❌"
        print(f"\n📱 响应式布局测试: {status_icon}")
    
    # 总结
    all_tests = [
        all_results["api_health"],
        all_results["navigation"],
        all_results["responsive"]
    ] + all_results["page_loads"]
    
    total_tests = len(all_tests)
    passed_tests = sum(1 for t in all_tests if t and t.get("status") == "passed")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed_tests}/{total_tests} 测试通过")
    print("=" * 60)
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  有 {total_tests - passed_tests} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
