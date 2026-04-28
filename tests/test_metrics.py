"""绩效指标计算模块单元测试"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.gtap.metrics import calculate_metrics, calculate_trade_metrics, PerformanceMetrics


class TestCalculateMetrics:
    """测试绩效指标计算"""

    def test_basic_metrics(self):
        """测试基础指标计算"""
        # 构造简单的资产价值序列：初始 10000，每天增长 1%，共 30 天
        start = datetime(2024, 1, 1)
        dates = [start + timedelta(days=i) for i in range(30)]
        values = [10000 * (1.01**i) for i in range(30)]
        trades = []  # 无交易
        initial = 10000.0
        total_invest = 10000.0
        fees = 0.0

        metrics = calculate_metrics(
            asset_values=values,
            trades=trades,
            initial_investment=initial,
            total_investment=total_invest,
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
                initial_investment=10000,
                total_investment=10000,
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
                initial_investment=10000,
                total_investment=10000,
                total_fees=0,
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 1),
            )


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
