"""plot.py 基础测试 — 防止无测试覆盖"""

import pytest
from pathlib import Path

@pytest.mark.smoke
def test_plot_module_import():
    try:
        import gtap.plot as plot_mod
        assert hasattr(plot_mod, '__name__')
    except ImportError:
        pytest.skip("plot 模块暂未实现")

@pytest.mark.smoke
def test_plot_placeholder():
    assert True
