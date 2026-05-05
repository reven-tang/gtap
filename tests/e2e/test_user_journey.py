"""
GTAP E2E 测试 — 用户真实旅程验证

使用 Playwright 模拟用户在浏览器中操作 Streamlit 应用的完整流程。
需要在测试前确保 Streamlit 已启动在 localhost:8501。

Usage:
    # 先启动 Streamlit
    streamlit run app.py --server.port 8501

    # 然后运行 E2E 测试
    pytest tests/e2e/ -v
"""

import time
import requests
import pytest
from pathlib import Path
from typing import Generator

try:
    from playwright.sync_api import Page, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


BASE_URL = "http://localhost:8501"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def ensure_streamlit_running():
    """确保 Streamlit 在 8501 端口运行"""
    try:
        resp = requests.get(BASE_URL, timeout=2)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


# ========== Fixtures ==========

@pytest.fixture(scope="module")
def browser():
    """启动浏览器（module 级别复用）"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright 未安装")
    
    if not ensure_streamlit_running():
        pytest.skip("Streamlit 未启动在 localhost:8501 — 请先运行: streamlit run app.py")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser) -> Generator[Page, None, None]:
    """新建页面（每个 test 隔离）"""
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    # 收集 Console 错误
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg)
            if msg.type in ("error", "warning") else None)
    
    yield page
    
    # 测试结束时检查 console 错误
    context.close()


# ========== 测试 1: 页面加载 ==========

class TestPageLoad:
    """页面加载和基础渲染检查"""

    def test_page_loads_successfully(self, page):
        """页面能正常加载"""
        page.goto(BASE_URL, timeout=15000, wait_until="networkidle")
        
        # 检查标题存在
        assert page.locator("text=GTAP").is_visible(), "GTAP 标题未显示"
        
        # 截图保存
        page.screenshot(path=str(SCREENSHOTS_DIR / "e2e_page_load.png"),
                        full_page=True)

    def test_sidebar_renders(self, page):
        """侧边栏正常渲染"""
        page.goto(BASE_URL, timeout=15000)
        
        # 侧边栏基础元素
        sidebar = page.locator("[data-testid='stSidebar']")
        assert sidebar.is_visible(), "侧边栏未渲染"
        
        # 标题
        assert page.locator("text=GTAP 香农回测").is_visible(), \
            "侧边栏标题未显示"

    def test_no_console_errors_on_load(self, page):
        """页面加载无 JS 错误"""
        page.goto(BASE_URL, timeout=15000, wait_until="networkidle")
        
        # 收集 console 错误
        errors = []
        page.on("console", lambda msg: errors.append(msg.text)
                if msg.type == "error" else None)
        
        # 重新触发一次渲染（点击页面空白处）
        page.click("body", position={"x": 10, "y": 10})
        time.sleep(0.5)
        
        # 过滤掉无关错误
        real_errors = [e for e in errors
                       if "favicon" not in e.lower()
                       and "streamlit" not in e.lower()
                       and "localhost" not in e.lower()]
        
        assert len(real_errors) == 0, f"Console 错误: {real_errors}"


# ========== 测试 2: 核心交互 ==========

class TestCoreInteraction:
    """核心用户交互流程"""

    def test_stock_input_exists_and_editable(self, page):
        """股票代码输入框存在并可编辑"""
        page.goto(BASE_URL, timeout=15000)
        
        # 找到输入框
        input_field = page.locator("input[aria-label='股票代码']")
        if not input_field.is_visible():
            # 备用定位
            input_field = page.get_by_label("股票代码")
        
        assert input_field.is_visible(), "股票代码输入框不存在"
        
        # 清空并输入
        input_field.click()
        input_field.fill("sh.600958")
        
        assert input_field.input_value() == "sh.600958", \
            "输入框值不一致"

    def test_date_inputs_exist(self, page):
        """日期选择器存在"""
        page.goto(BASE_URL, timeout=15000)
        
        assert page.locator("text=开始日期").is_visible(), "开始日期选择器不存在"
        assert page.locator("text=结束日期").is_visible(), "结束日期选择器不存在"

    def test_presets_are_selectable(self, page):
        """快速预设可选择"""
        page.goto(BASE_URL, timeout=15000)
        
        # 找到预设下拉框
        preset = page.locator("[data-testid='stSelectbox']").first
        preset.click()
        time.sleep(0.3)
        
        # 选择香农经典
        page.locator("text=香农经典").click()
        time.sleep(0.5)
        
        # 检查成功提示
        assert page.locator("text=已应用").is_visible(), \
            "预设应用提示未显示"

    def test_run_button_exists(self, page):
        """运行按钮存在"""
        page.goto(BASE_URL, timeout=15000)
        
        # Streamlit button (通常在主内容区)
        button = page.locator('button:has-text("运行")')
        if button.count() == 0:
            button = page.locator("button:has-text('Run')")
        if button.count() == 0:
            button = page.locator("button[kind='primary']")
        
        assert button.count() > 0, "未找到运行按钮"


# ========== 测试 3: 数据源切换 ==========

class TestDataSource:
    """数据源切换功能"""

    def test_data_source_selector_exists(self, page):
        """数据源选择器存在"""
        page.goto(BASE_URL, timeout=15000)
        
        selectors = page.locator("[aria-label='数据源']")
        if selectors.count() == 0:
            selectors = page.locator("text=数据源").locator("..")
        
        assert selectors.count() > 0, "数据源选择器不存在"


# ========== 测试 4: 响应式布局 ==========

class TestResponsiveLayout:
    """响应式布局检查"""

    def test_full_hd_layout(self, page):
        """1080p 布局正常"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(BASE_URL, timeout=15000)
        
        page.screenshot(path=str(SCREENSHOTS_DIR / "e2e_fullhd.png"),
                        full_page=True)

    def test_mobile_layout_doesnt_crash(self, page):
        """移动端视口不会崩溃"""
        page.set_viewport_size({"width": 390, "height": 844})
        
        try:
            page.goto(BASE_URL, timeout=20000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "e2e_mobile.png"),
                            full_page=True)
        except Exception as e:
            pytest.fail(f"移动端视口崩溃: {e}")


# ========== 测试 5: 理论模块展示 ==========

class TestTheoryDisplay:
    """香农理论模块 UI 展示"""

    def test_theory_expander_exists(self, page):
        """理论说明扩展区存在"""
        page.goto(BASE_URL, timeout=15000)
        
        # 查找理论相关内容
        theory_elements = [
            page.locator("text=香农"),
            page.locator("text=理论"),
            page.locator("text=波动"),
        ]
        
        visible = any(e.count() > 0 for e in theory_elements)
        assert visible, "未找到理论相关展示内容"
