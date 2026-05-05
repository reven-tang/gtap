"""
E2E 测试 conftest — 共享 fixtures

用法: pytest tests/e2e/ -v --tracing=on  # 开启 Playwright tracing
"""
import pytest


def pytest_addoption(parser):
    parser.addoption("--streamlit-port", default="8501",
                     help="Streamlit 端口 (default: 8501)")
    parser.addoption("--headed", action="store_true",
                     help="以可见模式运行浏览器（调试用）")


@pytest.fixture(scope="session")
def streamlit_url(request):
    port = request.config.getoption("--streamlit-port")
    return f"http://localhost:{port}"
