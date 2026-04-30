"""策略引擎单元测试"""

import pytest
from src.gtap.strategies import (
    StrategyEngine,
    TradeSignal,
    GridStrategy,
    RebalanceStrategy,
    create_strategy,
)
from src.gtap.config import GridTradingConfig


class TestGridStrategy:
    """测试经典网格策略"""

    def test_price_below_grid_triggers_buy(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0], shares_per_grid=100)
        config = GridTradingConfig()
        signal = grid.should_trade(4.2, 100, 5000, 5.0, 0.5, config)
        assert signal is not None
        assert signal.action == "买入"
        assert signal.reason == "grid"

    def test_price_above_grid_triggers_sell(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0], shares_per_grid=100)
        config = GridTradingConfig()
        signal = grid.should_trade(5.8, 100, 5000, 5.0, 0.5, config)
        assert signal is not None
        assert signal.action == "卖出"
        assert signal.reason == "grid"

    def test_price_at_center_no_trade(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0], shares_per_grid=100)
        config = GridTradingConfig()
        signal = grid.should_trade(5.0, 100, 5000, 5.0, 0.5, config)
        assert signal is None

    def test_update_grid_center_on_buy(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0])
        grid.update_grid_center("买入", 4.2)
        assert grid.current_grid_center == 4.5

    def test_update_grid_center_on_sell(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0])
        grid.update_grid_center("卖出", 5.8)
        assert grid.current_grid_center == 5.5

    def test_cleared_position_no_trade(self):
        grid = GridStrategy(grid_prices=[4.0, 4.5, 5.0, 5.5, 6.0])
        config = GridTradingConfig()
        signal = grid.should_trade(4.2, 0, 5000, 0, 0, config)
        assert signal is None


class TestRebalanceStrategy:
    """测试再平衡策略"""

    def test_high_ratio_triggers_sell(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        # 股票占比 80% > 目标 50% + 阈值 5%
        signal = rebalance.should_trade(5.0, 100, 1000, 5.0, 0.8, config)
        assert signal is not None
        assert signal.action == "卖出"
        assert signal.reason == "rebalance"

    def test_low_ratio_triggers_buy(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        # 股票占比 20% < 目标 50% - 阈值 5%
        signal = rebalance.should_trade(5.0, 100, 10000, 5.0, 0.2, config)
        assert signal is not None
        assert signal.action == "买入"
        assert signal.reason == "rebalance"

    def test_ratio_at_target_no_trade(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        signal = rebalance.should_trade(5.0, 100, 5000, 5.0, 0.5, config)
        assert signal is None

    def test_ratio_within_threshold_no_trade(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        signal = rebalance.should_trade(5.0, 100, 5000, 5.0, 0.52, config)
        assert signal is None

    def test_calculate_buy_size(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        signal = TradeSignal(action="买入", shares=0, reason="rebalance")
        size = rebalance.calculate_trade_size(5.0, signal, 4000, 100, config)
        assert size > 0

    def test_calculate_sell_size(self):
        rebalance = RebalanceStrategy(target_allocation=0.5, rebalance_threshold=0.05)
        config = GridTradingConfig()
        signal = TradeSignal(action="卖出", shares=0, reason="rebalance")
        # 股票占比过高：950/(950+100)=95%，需卖到50%
        size = rebalance.calculate_trade_size(5.0, signal, 100, 190, config)
        assert size > 0


class TestCreateStrategy:
    """测试策略工厂"""

    def test_grid_mode_creates_grid_strategy(self):
        config = GridTradingConfig(strategy_mode="grid")
        strategy = create_strategy(config, [4.0, 5.0, 6.0])
        assert isinstance(strategy, GridStrategy)

    def test_rebalance_mode_creates_rebalance_strategy(self):
        config = GridTradingConfig(strategy_mode="rebalance_threshold")
        strategy = create_strategy(config, [4.0, 5.0, 6.0])
        assert isinstance(strategy, RebalanceStrategy)

    def test_invalid_mode_raises(self):
        config = GridTradingConfig(strategy_mode="invalid")
        with pytest.raises(ValueError):
            create_strategy(config, [4.0, 5.0, 6.0])

    def test_strategy_has_name(self):
        config = GridTradingConfig(strategy_mode="grid")
        strategy = create_strategy(config, [4.0, 5.0, 6.0])
        assert strategy.get_name() == "GridStrategy"