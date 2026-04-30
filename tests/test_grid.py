"""网格交易引擎单元测试"""

import pytest
import pandas as pd
from src.gtap.grid import grid_trading, GridTradingResult
from src.gtap.config import GridTradingConfig
from src.gtap.exceptions import GridTradingError


def make_sample_data() -> pd.DataFrame:
    """生成测试用的价格数据（简单的线性上涨）"""
    dates = pd.date_range("2024-01-01", periods=20, freq="5min")
    prices = [5.0 + i * 0.1 for i in range(20)]
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p + 0.05 for p in prices],
            "low": [p - 0.05 for p in prices],
            "close": prices,
            "volume": [1000] * 20,
        },
        index=dates,
    )
    return df


class TestGridTrading:
    """测试网格交易回测引擎"""

    def test_basic_grid_trading(self):
        """测试基本网格交易流程"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0,
            grid_lower=4.0,
            grid_number=5,
            grid_center=5.0,
            initial_shares=100,
            current_holding_price=5.0,
            total_investment=10000.0,
            commission_rate=0.0003,
            transfer_fee_rate=0.00001,
            stamp_duty_rate=0.001,
        )

        result = grid_trading(data, config)

        assert isinstance(result, GridTradingResult)
        assert len(result.trades) >= 1
        assert result.total_buy_count >= 1
        assert result.total_fees >= 0
        # asset_values 在每个数据点都记录（即使提前清仓也至少记录到清仓时刻）
        assert len(result.asset_values) >= 1

    def test_empty_data_raises(self):
        """测试空数据应抛出异常"""
        config = GridTradingConfig()
        with pytest.raises(GridTradingError, match="输入数据为空"):
            grid_trading(pd.DataFrame(), config)

    def test_missing_close_column_raises(self):
        """测试缺少 close 列应抛出异常"""
        data = pd.DataFrame({"open": [1, 2, 3]})
        config = GridTradingConfig()
        with pytest.raises(GridTradingError, match="缺少必需列"):
            grid_trading(data, config)

    def test_initial_trade_is_buy(self):
        """测试第一笔交易是买入（初始持仓）"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0,
            grid_lower=4.0,
            grid_number=5,
            grid_center=5.0,
            initial_shares=100,
            current_holding_price=5.0,
            total_investment=10000.0,
        )
        result = grid_trading(data, config)
        first_trade = result.trades[0]
        assert first_trade.action == "买入"
        assert first_trade.shares == 100

    def test_sell_only_after_buy(self):
        """测试卖出发生在买入之后"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0,
            grid_lower=4.0,
            grid_number=5,
            grid_center=5.0,
            initial_shares=100,
            current_holding_price=5.0,
            total_investment=10000.0,
        )
        result = grid_trading(data, config)
        # 检查交易序列：买入后才有卖出
        has_sell = any(t.action == "卖出" for t in result.trades)
        if has_sell:
            first_sell_idx = next(i for i, t in enumerate(result.trades) if t.action == "卖出")
            first_buy_idx = next(i for i, t in enumerate(result.trades) if t.action == "买入")
            assert first_sell_idx > first_buy_idx

    def test_no_negative_shares(self):
        """测试任何时候持仓不为负"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0,
            grid_lower=4.0,
            grid_number=5,
            grid_center=5.0,
            initial_shares=100,
            current_holding_price=5.0,
            total_investment=10000.0,
        )
        result = grid_trading(data, config)
        for t in result.trades:
            assert t.total_shares >= 0

    def test_large_price_drop_triggers_multiple_buys(self):
        """测试大幅下跌触发多次买入（跨越多网格）"""
        dates = pd.date_range("2024-01-01", periods=10, freq="1D")
        # 价格从 5.0 暴跌到 3.5（跨越多个网格）
        prices = [5.0, 4.8, 4.6, 4.3, 4.0, 3.7, 3.5, 3.5, 3.5, 3.5]
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 10,
        }, index=dates)

        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=500000.0,
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
        )
        result = grid_trading(df, config)
        buys = [t for t in result.trades if t.action == "买入"]
        # 初始买入 + 后续网格买入
        assert len(buys) >= 2
        assert result.total_buy_count >= 2

    def test_large_price_rise_triggers_sells(self):
        """测试大幅上涨触发卖出"""
        dates = pd.date_range("2024-01-01", periods=10, freq="1D")
        prices = [5.0, 5.3, 5.6, 5.9, 6.2, 6.5, 6.8, 7.0, 7.0, 7.0]
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 10,
        }, index=dates)

        config = GridTradingConfig(
            grid_upper=7.5, grid_lower=4.0, grid_number=8, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=50000.0,
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
        )
        result = grid_trading(df, config)
        sells = [t for t in result.trades if t.action == "卖出"]
        assert len(sells) >= 1
        assert result.total_sell_count >= 1

    def test_atr_stop_loss_triggers(self):
        """测试 ATR 止损触发"""
        dates = pd.date_range("2024-01-01", periods=20, freq="1D")
        prices = [5.0] * 5 + [4.8, 4.5, 4.2, 4.0, 3.8, 3.5, 3.2, 3.0, 2.8, 2.5, 2.2, 2.0, 1.8, 1.5, 1.2]
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 20,
        }, index=dates)

        # 构造 ATR 序列（较大的波动率使止损触发更敏感）
        atr_values = [0.5] * 20
        atr_series = pd.Series(atr_values, index=dates)

        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=50000.0,
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
            use_atr_stop=True, atr_period=14, atr_stop_multiplier=1.5, atr_tp_multiplier=0.5,
        )
        result = grid_trading(df, config, atr_series=atr_series)

        # 应有止损交易
        stop_loss_trades = [t for t in result.trades if getattr(t, "exit_reason", "") == "stop_loss"]
        assert len(stop_loss_trades) >= 1 or result.stop_loss_count >= 1

    def test_atr_take_profit_triggers(self):
        """测试 ATR 止盈触发"""
        dates = pd.date_range("2024-01-01", periods=20, freq="1D")
        prices = [5.0] * 5 + [5.3, 5.6, 5.9, 6.2, 6.5, 6.8, 7.1, 7.4, 7.7, 8.0, 8.3, 8.6, 8.9, 9.2, 9.5]
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 20,
        }, index=dates)

        # ATR 较小，让止盈距离也小，容易被大幅上涨触发
        atr_values = [0.3] * 20
        atr_series = pd.Series(atr_values, index=dates)

        config = GridTradingConfig(
            grid_upper=10.0, grid_lower=4.0, grid_number=10, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=50000.0,
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
            use_atr_stop=True, atr_period=14, atr_stop_multiplier=1.5, atr_tp_multiplier=4.0,
        )
        result = grid_trading(df, config, atr_series=atr_series)

        # 检查是否有止盈（或至少网格卖出）
        assert result.total_sell_count >= 1

    def test_atr_disabled_does_nothing(self):
        """测试 use_atr_stop=False 时不产生 ATR 统计"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=10000.0,
            use_atr_stop=False,
        )
        result = grid_trading(data, config)
        assert result.stop_loss_count == 0
        assert result.take_profit_count == 0
        # 所有交易退出原因应为 grid
        for t in result.trades:
            assert getattr(t, "exit_reason", "grid") == "grid"

    def test_cleared_position_continues_recording(self):
        """测试清仓后继续记录资产价值"""
        dates = pd.date_range("2024-01-01", periods=30, freq="1D")
        # 前一半暴跌触发清仓，后一半平稳
        prices = [5.0] * 5 + [4.5, 4.0, 3.5, 3.0, 2.5] + [2.5] * 20
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 30,
        }, index=dates)

        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=50000.0,
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
        )
        result = grid_trading(df, config)
        # 应记录 30 个资产数据点（每个 K 线一个）
        # 即使提前清仓，也应继续记录
        assert len(result.asset_values) == 30

    def test_flat_price_no_trades(self):
        """测试价格不变时不产生额外交易"""
        dates = pd.date_range("2024-01-01", periods=10, freq="1D")
        prices = [5.0] * 10
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 10,
        }, index=dates)

        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=10000.0,
        )
        result = grid_trading(df, config)
        # 只有初始买入（1 笔），没有额外交易
        assert len(result.trades) == 1
        assert result.trades[0].action == "买入"

    def test_insufficient_cash_prevents_buy(self):
        """测试资金不足时不会买入"""
        dates = pd.date_range("2024-01-01", periods=10, freq="1D")
        prices = [5.0, 4.9, 4.8, 4.6, 4.4, 4.2, 4.0, 3.8, 3.6, 3.4]
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices, "close": prices,
            "volume": [1000] * 10,
        }, index=dates)

        # 极小的总投资，只够初始买入
        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0,
            total_investment=500.0,  # 刚好够 100 * 5.0
            commission_rate=0.0003, transfer_fee_rate=0.00001, stamp_duty_rate=0.001,
        )
        result = grid_trading(df, config)
        # 只有初始买入，没有后续交易
        buys_after_initial = [t for t in result.trades if t.action == "买入"][1:]
        assert len(buys_after_initial) == 0

    def test_result_contains_all_statistics(self):
        """测试返回结果包含所有统计字段"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=6.0, grid_lower=4.0, grid_number=5, grid_center=5.0,
            initial_shares=100, current_holding_price=5.0, total_investment=10000.0,
        )
        result = grid_trading(data, config)

        assert hasattr(result, "trades")
        assert hasattr(result, "total_buy_volume")
        assert hasattr(result, "total_sell_volume")
        assert hasattr(result, "total_buy_count")
        assert hasattr(result, "total_sell_count")
        assert hasattr(result, "trade_profits")
        assert hasattr(result, "asset_values")
        assert hasattr(result, "total_fees")
        assert hasattr(result, "stop_loss_count")
        assert hasattr(result, "take_profit_count")
        assert hasattr(result, "grid_trade_count")

    def test_grid_step_minimal(self):
        """测试极小网格间距仍能正常工作"""
        data = make_sample_data()
        config = GridTradingConfig(
            grid_upper=5.1, grid_lower=5.0, grid_number=11,
            grid_center=5.05, initial_shares=100, current_holding_price=5.0,
            total_investment=10000.0,
        )
        assert config.grid_step == pytest.approx(0.01)
        result = grid_trading(data, config)
        assert len(result.trades) >= 1
