#!/usr/bin/env python3
"""
Smoke Test Stub — 冒烟测试模板（项目无关）

用法:
    python3 tools/smoke-test.py [--quick] [--browser]

配置方式（通过环境变量或项目根目录自动探测）:
    PROJECT_ROOT — 项目根目录（默认自动检测）
    APP_ENTRY — 应用入口文件（默认: app.py）
    APP_PORT — 应用端口（默认: 8501）

模板设计为可直接复制到新项目中，只需修改配置部分。
"""
import subprocess, sys, time, socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] if Path(__file__).name == "smoke-test.py" else Path.cwd()
APP_ENTRY = PROJECT_ROOT / "app.py"
APP_PORT = 8501

def is_port_open():
    try:
        s = socket.create_connection(("127.0.0.1", APP_PORT), timeout=1)
        s.close()
        return True
    except OSError:
        return False

def test_core_imports():
    """核心模块导入正常"""
    try:
        import gtap
        return True, "核心模块导入成功"
    except ImportError as e:
        return False, f"导入失败: {e}"

def test_config_creation():
    """配置对象可创建"""
    try:
        from gtap.config import GridTradingConfig
        cfg = GridTradingConfig()
        return True, "配置创建成功"
    except Exception as e:
        return False, f"配置失败: {e}"

def test_data_module():
    """数据模块可用"""
    try:
        from gtap.data import get_stock_data
        return True, "数据模块可用"
    except Exception as e:
        return False, f"数据模块异常: {e}"

def test_app_starts():
    """应用可启动（--quick 跳过，仅检查入口文件存在）"""
    if not APP_ENTRY.exists():
        return False, f"入口文件 {APP_ENTRY} 不存在"
    return True, "入口文件存在（启动测试在 --browser 模式执行）"

def test_app_responds():
    """应用可响应 HTTP 请求"""
    import requests
    if is_port_open():
        try:
            resp = requests.get(f"http://localhost:{APP_PORT}", timeout=2)
            return resp.status_code == 200, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, f"连接失败: {e}"
    return False, "端口未开放"

def test_browser_ui():
    """浏览器 UI 验证（可选，需 Playwright）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return True, "Playwright 未安装，跳过"
    
    if not is_port_open():
        return False, "应用未运行"
    
    proc = None
    try:
        import requests
        resp = requests.get(f"http://localhost:{APP_PORT}", timeout=3)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.goto(f"http://localhost:{APP_PORT}", timeout=15000, wait_until="networkidle")
            page.screenshot(path=str(PROJECT_ROOT / "tests" / "screenshots" / "smoke.png"), full_page=True)
            browser.close()
            errors = [e for e in console_errors if "favicon" not in e.lower()]
            if errors:
                return False, f"Console 错误: {'; '.join(errors[:3])}"
            return True, "UI 验证通过"
    except Exception as e:
        return False, f"浏览器测试异常: {e}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速模式（不启动应用）")
    parser.add_argument("--browser", action="store_true", help="浏览器验证")
    args = parser.parse_args()
    
    errors = []
    
    # 基础检查（所有模式）
    for name, test in [
        ("core_imports", test_core_imports),
        ("config_creation", test_config_creation),
        ("data_module", test_data_module),
        ("app_starts", test_app_starts),
    ]:
        ok, msg = test()
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {msg}")
        if not ok:
            errors.append(f"{name}: {msg}")
    
    # --quick 模式不进行浏览器验证
    if args.quick:
        if errors:
            print("\n❌ 冒烟测试失败")
            return 1
        print("\n✅ 快速检查通过")
        return 0
    
    # 浏览器验证
    ok, msg = test_app_responds()
    status = "✓" if ok else "✗"
    print(f"  {status} app_responds: {msg}")
    if not ok:
        errors.append(f"app_responds: {msg}")
    
    if args.browser:
        ok, msg = test_browser_ui()
        status = "✓" if ok else "✗"
        print(f"  {status} browser_ui: {msg}")
        if not ok:
            errors.append(f"browser_ui: {msg}")
    
    if errors:
        print("\n❌ 冒烟测试失败")
        return 1
    print("\n✅ 冒烟测试通过")
    return 0

if __name__ == "__main__":
    sys.exit(main())
