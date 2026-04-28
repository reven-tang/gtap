"""网格交易引擎单元测试"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.gtap.grid import grid_trading, GridTradingResult, Trade
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
