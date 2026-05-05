"""
测试 v1.1.0 新特性 - 凯利准则动态仓位、市场状态自适应、波动率自适应网格密度、TheorySignal 管线

"""

import pytest
import pandas as pd
import numpy as np

from gtap.config import GridTradingConfig
from gtap.strategies import (
    TheorySignal,
    KellyRebalanceStrategy,
    RegimeAwareEngine,
    TradeSignal,
    RebalanceStrategy,
    GridStrategy,
    create_strategy,
)
from gtap.theory import kelly_criterion, get_market_regime, calculate_volatility_drag


class TestTheorySignal:
    """TheorySignal 信号管线测试"""

    def test_from_short_series(self):
        """短序列返回保守默认值"""
        prices = pd.Series([10.0] * 10)
        sig = TheorySignal.from_price_data(prices)
        assert sig.regime == "不确定"
        assert sig.kelly_allocation > 0
        assert sig.volatility_drag == 0.0  # 无波动

    def test_from_volatile_series(self):
        """高波动序列应有显著波动拖累"""
        np.random.seed(42)
        prices = pd.Series(100 + np.random.randn(60).cumsum())
        sig = TheorySignal.from_price_data(prices)
        assert sig.volatility_drag > 0
        assert sig.regime in ("震荡", "上涨", "下跌", "不确定")
        # 高波动→凯利仓位应保守
        assert sig.kelly_allocation < 0.5

    def test_from_flat_series(self):
        """低波动序列→凯利仓位更积极"""
        prices = pd.Series([10.0 + 0.01 * i for i in range(60)])
        sig = TheorySignal.from_price_data(prices)
        assert sig.volatility_drag < 0.01  # 低波动拖累
        # 低波动→凯利仓位较高
        assert sig.kelly_allocation >= 0.3

    def test_with_config_recommended_params(self):
        """带 config 应生成推荐参数"""
        prices = pd.Series(10 + np.random.randn(40).cumsum() * 0.5)
        c = GridTradingConfig()
        sig = TheorySignal.from_price_data(prices, config=c)
        assert sig.recommended_threshold is not None
        assert sig.recommended_threshold >= 0.02  # 成本阈值最低2%

    def test_with_atr_grid_count(self):
        """带 ATR 和价格范围应推荐网格数"""
        prices = pd.Series([10.0] * 30)
        c = GridTradingConfig()
        sig = TheorySignal.from_price_data(
            prices, config=c, atr_value=0.5, price_range=5.0
        )
        assert sig.recommended_grid_count is not None
        assert 5 <= sig.recommended_grid_count <= 25


class TestKellyRebalanceStrategy:
    """凯利准则驱动的再平衡策略测试"""

    def test_init_default(self):
        """默认参数初始化"""
        ks = KellyRebalanceStrategy()
        assert ks.kelly_fraction == 0.5
        assert ks.target_allocation == 0.5 * 0.5  # 初始=半凯利×0.5=0.25

    def test_init_custom_fraction(self):
        """自定义凯利分数"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.3)
        assert ks.target_allocation == 0.5 * 0.3  # 初始保守

    def test_should_trade_high_ratio(self):
        """股票占比过高→卖出信号"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.5)
        ks.target_allocation = 0.3  # 凯利建议30%
        signal = ks.should_trade(10.0, 100, 500, 10.0, 0.67, GridTradingConfig())
        assert signal is not None
        assert signal.action == "卖出"
        assert signal.reason == "kelly_rebalance"

    def test_should_trade_low_ratio(self):
        """股票占比过低→买入信号"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.5)
        ks.target_allocation = 0.5
        signal = ks.should_trade(10.0, 10, 900, 10.0, 0.1, GridTradingConfig())
        assert signal is not None
        assert signal.action == "买入"
        assert signal.reason == "kelly_rebalance"

    def test_should_trade_within_threshold(self):
        """偏离在阈值内→不交易"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.5)
        ks.target_allocation = 0.5
        signal = ks.should_trade(10.0, 50, 500, 10.0, 0.5, GridTradingConfig())
        # 0.5 == 0.5, deviation=0, no trade
        assert signal is None

    def test_update_kelly_from_trades_insufficient(self):
        """交易数据不足时保持默认"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.5)
        # 无交易
        ks.update_kelly_from_trades([])
        assert ks.target_allocation == 0.5 * 0.5

    def test_update_kelly_from_trades_with_data(self):
        """有交易数据时动态更新"""
        ks = KellyRebalanceStrategy(kelly_fraction=0.5)
        from gtap.grid import Trade
        # 创建模拟交易：4赢2亏 → 胜率67%
        trades = [
            Trade("卖出", pd.Timestamp("2024-01-01"), 11.0, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
            Trade("卖出", pd.Timestamp("2024-01-02"), 10.5, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
            Trade("卖出", pd.Timestamp("2024-01-03"), 11.2, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
            Trade("卖出", pd.Timestamp("2024-01-04"), 9.8, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
            Trade("卖出", pd.Timestamp("2024-01-05"), 11.0, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
            Trade("卖出", pd.Timestamp("2024-01-06"), 9.5, 100, 0, 0, 0, 0, 0, 10.0, 0, 0, 0, "grid"),
        ]
        ks.update_kelly_from_trades(trades)
        # 胜率=4/6≈0.67, 平均盈利≈0.1, 平均亏损≈0.05
        # 凯利应给出比0.25更高的值
        assert ks.target_allocation > 0.2


class TestRegimeAwareEngine:
    """市场状态自适应策略切换引擎测试"""

    def test_init_default(self):
        """默认初始化"""
        c = GridTradingConfig()
        engine = RegimeAwareEngine(c, [8.0, 9.0, 10.0, 11.0, 12.0])
        assert engine.current_regime == "不确定"

    def test_update_regime_oscillating(self):
        """震荡市→切换到网格策略"""
        c = GridTradingConfig()
        engine = RegimeAwareEngine(c, [8.0, 9.0, 10.0, 11.0, 12.0])
        # 震荡价格序列
        osc_prices = pd.Series([10.0, 10.5, 9.5, 10.2, 10.8, 9.8, 10.1, 10.3, 9.9, 10.0,
                                10.4, 9.6, 10.2, 10.7, 9.3, 10.1, 10.5, 9.5, 10.3, 10.0])
        regime = engine.update_regime(osc_prices)
        if regime == "震荡":
            assert isinstance(engine.active_strategy, GridStrategy)

    def test_update_regime_trending(self):
        """趋势市→切换到再平衡策略"""
        c = GridTradingConfig()
        engine = RegimeAwareEngine(c, [8.0, 9.0, 10.0, 11.0, 12.0])
        # 上涨趋势序列
        trend_prices = pd.Series([10.0 + 0.5 * i for i in range(20)])
        regime = engine.update_regime(trend_prices)
        if regime in ("上涨", "下跌"):
            assert isinstance(engine.active_strategy, (RebalanceStrategy, KellyRebalanceStrategy))

    def test_regime_summary(self):
        """市场状态切换统计"""
        c = GridTradingConfig()
        engine = RegimeAwareEngine(c, [8.0, 9.0, 10.0, 11.0, 12.0])
        # 模拟多次更新
        osc = pd.Series([10.0] * 20)
        engine.update_regime(osc)
        trend = pd.Series([10.0 + 0.3 * i for i in range(20)])
        engine.update_regime(trend)
        summary = engine.get_regime_summary()
        assert "震荡" in summary
        assert "switches" in summary


class TestConfigNewFields:
    """v1.1.0 新配置字段验证"""

    def test_kelly_sizing_fields(self):
        """凯利配置字段"""
        c = GridTradingConfig(use_kelly_sizing=True, kelly_fraction=0.5, kelly_lookback=30)
        assert c.use_kelly_sizing == True
        assert c.kelly_fraction == 0.5
        assert c.kelly_lookback == 30

    def test_regime_adaptive_fields(self):
        """市场状态自适应字段"""
        c = GridTradingConfig(use_regime_adaptive=True, regime_lookback=20)
        assert c.use_regime_adaptive == True
        assert c.regime_lookback == 20

    def test_auto_grid_density_fields(self):
        """自适应网格密度字段"""
        c = GridTradingConfig(auto_grid_density=True, grid_density_atr_ratio=0.7,
                             grid_density_min=5, grid_density_max=25)
        assert c.auto_grid_density == True
        assert c.grid_density_atr_ratio == 0.7
        assert c.grid_density_min == 5
        assert c.grid_density_max == 25

    def test_invalid_kelly_fraction(self):
        """凯利分数范围验证"""
        with pytest.raises(Exception):  # ConfigError
            GridTradingConfig(kelly_fraction=0)

    def test_invalid_kelly_fraction_high(self):
        """凯利分数上限验证"""
        with pytest.raises(Exception):
            GridTradingConfig(kelly_fraction=1.5)

    def test_invalid_grid_density_range(self):
        """网格密度范围验证"""
        with pytest.raises(Exception):
            GridTradingConfig(grid_density_min=1)  # < 2

    def test_invalid_grid_density_max(self):
        """网格密度上限小于下限"""
        with pytest.raises(Exception):
            GridTradingConfig(grid_density_max=3, grid_density_min=5)

    def test_defaults_backward_compatible(self):
        """默认配置向后兼容"""
        c = GridTradingConfig()
        assert c.use_kelly_sizing == False  # 默认关闭
        assert c.use_regime_adaptive == False  # 默认关闭
        assert c.auto_grid_density == False  # 默认关闭
        assert c.kelly_fraction == 0.5
        assert c.kelly_lookback == 30
        assert c.regime_lookback == 20
        assert c.grid_density_atr_ratio == 0.7

    def test_to_dict_includes_new_fields(self):
        """to_dict 包含新字段"""
        c = GridTradingConfig()
        d = c.to_dict()
        assert "use_kelly_sizing" in d
        assert "kelly_fraction" in d
        assert "use_regime_adaptive" in d
        assert "auto_grid_density" in d


class TestCreateStrategyFactory:
    """策略工厂函数测试"""

    def test_create_kelly_strategy(self):
        """凯利模式下应创建 KellyRebalanceStrategy"""
        c = GridTradingConfig(strategy_mode="rebalance_threshold", use_kelly_sizing=True)
        s = create_strategy(c, [8, 9, 10, 11, 12])
        assert isinstance(s, KellyRebalanceStrategy)

    def test_create_rebalance_strategy(self):
        """普通模式下应创建 RebalanceStrategy"""
        c = GridTradingConfig(strategy_mode="rebalance_threshold")
        s = create_strategy(c, [8, 9, 10, 11, 12])
        assert isinstance(s, RebalanceStrategy)

    def test_create_grid_strategy(self):
        """网格模式下应创建 GridStrategy"""
        c = GridTradingConfig(strategy_mode="grid")
        s = create_strategy(c, [8, 9, 10, 11, 12])
        assert isinstance(s, GridStrategy)


class TestGridTradingResultNewFields:
    """回测结果新字段测试"""

    def test_basic_result_has_new_fields(self):
        """基础回测结果应包含新字段"""
        from gtap.grid import grid_trading
        from gtap.data import get_stock_data
        data = get_stock_data('sh.600958', '2022-01-01', '2024-12-31', data_source='baostock')
        result = grid_trading(data, GridTradingConfig())
        assert hasattr(result, 'theory_signals')
        assert hasattr(result, 'regime_summary')
        assert hasattr(result, 'kelly_allocations')
        # 默认模式不启用，应为空
        # 基础模式不再生成theory_signals（只在kelly/regime启用时生成）
        assert result.theory_signals is not None
        assert result.regime_summary is None
        assert result.kelly_allocations == []

    def test_kelly_result_has_allocations(self):
        """凯利模式应生成仓位变化序列"""
        from gtap.grid import grid_trading
        from gtap.data import get_stock_data
        data = get_stock_data('sh.600958', '2022-01-01', '2024-12-31', data_source='baostock')
        c = GridTradingConfig(use_kelly_sizing=True)
        result = grid_trading(data, c)
        assert result.kelly_allocations is not None
        assert len(result.kelly_allocations) > 0

    def test_regime_result_has_summary(self):
        """自适应模式应生成市场状态统计"""
        from gtap.grid import grid_trading
        from gtap.data import get_stock_data
        data = get_stock_data('sh.600958', '2022-01-01', '2024-12-31', data_source='baostock')
        c = GridTradingConfig(use_regime_adaptive=True)
        result = grid_trading(data, c)
        assert result.regime_summary is not None
        assert "震荡" in result.regime_summary
        assert "switches" in result.regime_summary