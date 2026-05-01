"""配置模块单元测试"""

import pytest
from src.gtap.config import GridTradingConfig
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

    def test_negative_initial_shares_raises(self):
        """测试负初始股数"""
        with pytest.raises(ConfigError):
            GridTradingConfig(initial_shares=-10)

    def test_negative_total_investment_raises(self):
        """测试总投资为 0 时抛出 ConfigError"""
        with pytest.raises(ConfigError, match="投入总资金"):
            GridTradingConfig(total_investment=0)

    def test_default_values(self):
        """测试所有默认值合理"""
        config = GridTradingConfig()
        assert config.grid_number == 10
        assert config.initial_shares == 100
        assert config.total_investment == 200000.0
        assert config.commission_rate == 0.0003
        assert config.data_source == "baostock"

    def test_atr_params_stored(self):
        """测试 ATR 参数正确存储"""
        config = GridTradingConfig(
            use_atr_stop=True, atr_period=20,
            atr_stop_multiplier=2.0, atr_tp_multiplier=0.8,
        )
        assert config.use_atr_stop is True
        assert config.atr_period == 20
        assert config.atr_stop_multiplier == 2.0
        assert config.atr_tp_multiplier == 0.8

    def test_data_source_field(self):
        """测试 data_source 字段"""
        config = GridTradingConfig(data_source="yfinance")
        assert config.data_source == "yfinance"

    def test_grid_step_single_grid(self):
        """测试单网格的间距为 0"""
        config = GridTradingConfig(grid_upper=6.0, grid_lower=4.0, grid_number=2)
        assert config.grid_step == pytest.approx(2.0)
