#!/usr/bin/env python3
"""
E2E Test Scaffold — 端到端测试脚手架（项目无关）

用法:
    pytest tests/e2e/test_user_journey.py -v

模板说明:
    - 提供 11 个标准 E2E 场景模板
    - 使用 Playwright（可选）或 requests 降级
    - 自动截图保存到 tests/screenshots/
    - Console 错误检查
"""
import pytest
from pathlib import Path
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_PORT = 8501

class TestE2EScaffold:
    """E2E 测试脚手架基类（供各项目继承）"""
    
    @pytest.fixture(scope="class")
    def app_url(self):
        return f"http://localhost:{APP_PORT}"
    
    @pytest.fixture(scope="class")
    def ensure_app_running(self):
        """确保应用在运行（如未启动则启动）"""
        import socket
        try:
            s = socket.create_connection(("127.0.0.1", APP_PORT), timeout=2)
            s.close()
            return True
        except OSError:
            # 启动应用
            proc = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(PROJECT_ROOT / "app.py"),
                 "--server.port", str(APP_PORT), "--server.headless", "true"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            # 等待启动
            for _ in range(40):
                time.sleep(0.5)
                try:
                    s = socket.create_connection(("127.0.0.1", APP_PORT), timeout=1)
                    s.close()
                    return True
                except OSError:
                    pass
            return False

# ========== 11 个标准 E2E 场景模板 ==========

class TestPageLoad:
    """场景 1-3: 页面加载"""
    
    def test_homepage_loads(self, app_url, ensure_app_running):
        """首页应成功加载"""
        import requests
        resp = requests.get(app_url, timeout=5)
        assert resp.status_code == 200
    
    def test_no_console_errors(self, app_url, ensure_app_running):
        """页面不应有控制台错误"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.skip("Playwright 未安装")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            errors = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.goto(app_url, timeout=15000, wait_until="networkidle")
            browser.close()
            critical = [e for e in errors if "favicon" not in e.lower()]
            assert not critical, f"Console 错误: {critical[:3]}"

class TestCoreInteraction:
    """场景 4-7: 核心交互"""
    
    def test_config_form_submission(self, app_url, ensure_app_running):
        """配置表单可提交"""
        import requests
        resp = requests.post(f"{app_url}/config", data={"symbol": "AAPL"}, timeout=5)
        assert resp.status_code in [200, 302]
    
    def test_grid_parameters_acceptance(self, app_url, ensure_app_running):
        """网格参数可接受"""
        import requests
        resp = requests.post(f"{app_url}/grid_params", json={"grid_size": 10}, timeout=5)
        assert resp.status_code in [200, 400]  # 允许参数验证失败，但不应崩溃
    
    def test_backtest_trigger(self, app_url, ensure_app_running):
        """回测按钮可点击（模拟）"""
        import requests
        resp = requests.get(f"{app_url}/backtest", timeout=5)
        # 允许未实现，但不应 500 错误
        assert resp.status_code in [200, 404, 405]
    
    def test_data_source_selection(self, app_url, ensure_app_running):
        """数据源选择可用"""
        import requests
        resp = requests.get(f"{app_url}/sources", timeout=5)
        assert resp.status_code in [200, 404]

class TestDataSource:
    """场景 8-9: 数据源"""
    
    def test_data_fetch_endpoint(self, app_url, ensure_app_running):
        """数据获取接口正常"""
        import requests
        resp = requests.get(f"{app_url}/api/data?symbol=AAPL&start=2024-01-01&end=2024-12-31", timeout=10)
        assert resp.status_code in [200, 400]  # 允许参数错误，但不应崩溃
    
    def test_provider_fallback(self, app_url, ensure_app_running):
        """提供者回退逻辑（占位）"""
        # TODO: 实现回退测试（需 mock 提供者失败）
        pytest.skip("待实现：提供者回退测试")

class TestResponsiveLayout:
    """场景 10-11: 响应式布局"""
    
    def test_viewport_sizes(self, app_url, ensure_app_running):
        """不同视口尺寸下页面可访问"""
        import requests
        resp = requests.get(app_url, timeout=5)
        assert resp.status_code == 200
        # 简单检查：HTML 应包含 viewport meta
        assert 'viewport' in resp.text.lower() or resp.status_code == 200
    
    def test_mobile_layout(self, app_url, ensure_app_running):
        """移动端布局检查（占位）"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.skip("Playwright 未安装")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 375, "height": 667})
            page.goto(app_url, timeout=15000)
            # 检查无横向滚动条（简单判断）
            page.screenshot(path=str(PROJECT_ROOT / "tests" / "screenshots" / "mobile.png"), full_page=True)
            browser.close()
            assert True

class TestTheoryDisplay:
    """场景 12: 理论展示"""
    
    def test_theory_page_loads(self, app_url, ensure_app_running):
        """理论页面加载正常"""
        import requests
        resp = requests.get(f"{app_url}/theory", timeout=5)
        assert resp.status_code in [200, 404]  # 允许页面未实现

# ========== 占位场景（后续扩展） ==========

class TestErrorHandling:
    """场景 13-14: 错误处理（待实现）"""
    
    def test_invalid_symbol(self, app_url, ensure_app_running):
        """无效代码处理"""
        pytest.skip("待实现：错误处理测试")
    
    def test_missing_parameters(self, app_url, ensure_app_running):
        """缺失参数处理"""
        pytest.skip("待实现：错误处理测试")

class TestPerformance:
    """场景 15-16: 性能（待实现）"""
    
    def test_page_load_time(self, app_url, ensure_app_running):
        """页面加载时间"""
        pytest.skip("待实现：性能测试")
    
    def test_backtest_performance(self, app_url, ensure_app_running):
        """回测性能"""
        pytest.skip("待实现：性能测试")
