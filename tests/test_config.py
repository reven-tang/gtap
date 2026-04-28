"""配置模块单元测试"""

import pytest
from src.gtap.config import GridTradingConfig, DEFAULT_CONFIG
from src.gtap.exceptions import ConfigError


class TestGridTradingConfig:
    """测试配置类"""

    def test_default_config_is_valid(self):
        """测试默认配置有效"""
        config = GridTradingConfig()
        assert config.grid_upper > config.grid_lower
        assert config.grid_number >= 2

    def test_invalid_grid_range(self):
        """测试网格上限小于等于下限"""
        with pytest.raises(ConfigError, match="网格上限必须大于网格下限"):
            GridTradingConfig(grid_upper=4.0, grid_lower=6.0)

    def test_invalid_grid_number(self):
        """测试网格数量小于 2"""
        with pytest.raises(ConfigError, match="网格数量必须"):
            GridTradingConfig(grid_number=1)

    def test_grid_center_out_of_range(self):
        """测试网格中心超出上下限"""
        with pytest.raises(ConfigError, match="网格中心必须在上下限之间"):
            GridTradingConfig(grid_upper=6.0, grid_lower=4.0, grid_center=7.0)

    def test_negative_commission_raises(self):
        """测试负佣金费率"""
        with pytest.raises(ConfigError, match="佣金费率不能为负"):
            GridTradingConfig(commission_rate=-0.001)

    def test_grid_step_property(self):
        """测试网格间距计算"""
        config = GridTradingConfig(grid_upper=10.0, grid_lower=0.0, grid_number=11)
        assert config.grid_step == pytest.approx(1.0)

    def test_to_dict(self):
        """测试配置转字典"""
        config = GridTradingConfig(stock_code="sh.601398")
        d = config.to_dict()
        assert d["stock_code"] == "sh.601398"
        assert "grid_upper" in d
