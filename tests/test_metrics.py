"""绩效指标计算模块单元测试"""

import pytest
from datetime import datetime, timedelta
from src.gtap.metrics import calculate_metrics, calculate_trade_metrics


class TestCalculateMetrics:
    """测试绩效指标计算"""

    def test_basic_metrics(self):
        """测试基础指标计算"""
        # 构造简单的资产价值序列：初始 10000，每天增长 1%，共 30 天
        start = datetime(2024, 1, 1)
        dates = [start + timedelta(days=i) for i in range(30)]
        values = [10000 * (1.01**i) for i in range(30)]
        trades = []  # 无交易
        fees = 0.0

        metrics = calculate_metrics(
        asset_values=values,
        trades=trades,
        total_fees=fees,
            start_date=start,
            end_date=dates[-1],
            risk_free_rate=0.03,
        )

        assert isinstance(metrics, dict)
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert metrics["total_return"] > 0  # 应该盈利

    def test_empty_values_raises(self):
        """测试空资产价值序列"""
        with pytest.raises(Exception):
            calculate_metrics(
                asset_values=[],
                trades=[],
                total_fees=0,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            )

    def test_invalid_date_range(self):
        """测试无效日期范围"""
        values = [10000, 10100]
        with pytest.raises(Exception, match="结束日期必须晚于开始日期"):
            calculate_metrics(
                asset_values=values,
                trades=[],
                total_fees=0,
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 1),
            )

    def test_zero_day_range_raises(self):
        """测试同日期的范围应抛出异常"""
        values = [10000, 10100]
        start = datetime(2024, 1, 1)
        with pytest.raises(Exception):
            calculate_metrics(
                asset_values=values,
                trades=[],
                total_fees=0,
                start_date=start,
                end_date=start,
            )

    def test_metrics_with_atr_trades(self):
        """测试包含 ATR 交易的指标计算"""
        from src.gtap.grid import Trade
        start = datetime(2024, 1, 1)
        dates = [start + timedelta(days=i) for i in range(30)]
        values = [10000 + 100 * i for i in range(30)]

        # 构造包含 ATR 止损/止盈的交易记录
        TradeType = Trade(
            action="", timestamp=start, price=0.0, shares=0,
            total_shares=0, commission=0.0, transfer_fee=0.0,
            stamp_duty=0.0, total_fee=0.0, avg_price=0.0,
        ).__class__

        trades = [
            Trade(action="买入", timestamp=start, price=100.0, shares=100,
                  total_shares=100, commission=3.0, transfer_fee=0.1, stamp_duty=0.0,
                  total_fee=3.1, avg_price=100.0,
                  atr_value=2.0, stop_loss_price=97.0, take_profit_price=101.0, exit_reason="grid"),
            Trade(action="卖出", timestamp=start + timedelta(days=5), price=95.0, shares=100,
                  total_shares=0, commission=2.85, transfer_fee=0.1, stamp_duty=9.5,
                  total_fee=12.45, avg_price=100.0,
                  atr_value=2.5, stop_loss_price=96.0, take_profit_price=101.0, exit_reason="stop_loss"),
        ]

        metrics = calculate_metrics(
            asset_values=values,
            trades=trades,
            total_fees=15.55,
            start_date=start,
            end_date=dates[-1],
        )

        assert "stop_loss_count" in metrics
        assert "take_profit_count" in metrics
        assert "stop_loss_rate" in metrics
        assert "take_profit_rate" in metrics


class TestCalculateTradeMetrics:
    """测试交易指标计算"""

    def test_all_winning_trades(self):
        """测试全胜交易"""
        profits = [100.0, 200.0, 150.0]
        result = calculate_trade_metrics(profits, total_buy_count=3, total_sell_count=3)
        assert result["win_rate"] == 1.0
        assert result["best_trade"] == 200.0
        assert result["avg_trade"] == pytest.approx(150.0)

    def test_all_losing_trades(self):
        """测试全亏交易"""
        profits = [-50.0, -30.0, -20.0]
        result = calculate_trade_metrics(profits, total_buy_count=3, total_sell_count=3)
        assert result["win_rate"] == 0.0
        assert result["worst_trade"] == -50.0

    def test_mixed_trades(self):
        """测试混合盈亏"""
        profits = [100.0, -30.0, 50.0, -10.0]
        result = calculate_trade_metrics(profits, total_buy_count=4, total_sell_count=4)
        assert result["win_rate"] == 0.5
        assert result["best_trade"] == 100.0
        assert result["worst_trade"] == -30.0

    def test_empty_profits(self):
        """测试无交易盈亏"""
        result = calculate_trade_metrics([], total_buy_count=0, total_sell_count=0)
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 0.0
        assert result["best_trade"] == 0.0
