"""
香农理论计算模块测试
"""
import pytest
import pandas as pd
import numpy as np

from src.gtap.theory import (
    calculate_volatility_drag,
    kelly_criterion,
    estimate_rebalancing_frequency,
    calculate_shannon_insight,
    recommend_grid_params,
    get_market_regime,
    ShannonInsight,
)


def create_price_series(start: float, days: int, volatility: float = 0.02) -> pd.Series:
    """创建模拟价格序列"""
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    returns = np.random.normal(0.0001, volatility, days)
    prices = start * (1 + returns).cumprod()
    return pd.Series(prices, index=dates)


class TestVolatilityDrag:
    def test_zero_volatility(self):
        assert calculate_volatility_drag(0.0) == 0.0

    def test_20_pct(self):
        # σ=0.2 → drag = 0.04/2 = 0.02
        result = calculate_volatility_drag(0.2)
        assert abs(result - 0.02) < 0.001

    def test_40_pct(self):
        # σ=0.4 → drag = 0.16/2 = 0.08
        result = calculate_volatility_drag(0.4)
        assert abs(result - 0.08) < 0.001

    def test_formula(self):
        """验证 σ²/2 公式"""
        for v in [0.1, 0.2, 0.3, 0.5]:
            assert abs(calculate_volatility_drag(v) - v**2 / 2) < 1e-10


class TestKellyCriterion:
    def test_fair_coin(self):
        """胜率50%, 盈亏比1:1 → f*=0"""
        result = kelly_criterion(0.5, 1.0, 1.0)
        assert result == 0.0

    def test_advantageous(self):
        """胜率60%, 盈亏比1:1 → f*=0.2"""
        result = kelly_criterion(0.6, 1.0, 1.0)
        assert abs(result - 0.2) < 0.01

    def test_high_win_rate(self):
        """高胜率 → 高仓位"""
        result = kelly_criterion(0.8, 1.0, 1.0)
        assert result > 0.5

    def test_zero_loss(self):
        """无亏损 → 全仓"""
        result = kelly_criterion(0.5, 0.01, 0.0)
        assert result == 1.0

    def test_negative_edge(self):
        """负期望 → 0"""
        result = kelly_criterion(0.3, 1.0, 1.0)
        assert result == 0.0


class TestRebalancingFrequency:
    def test_flat_price(self):
        """价格不变 → 0 次穿越"""
        prices = pd.Series([10.0] * 30)
        result = estimate_rebalancing_frequency(prices, 10, 5.0, 15.0)
        assert result == 0

    def test_sine_wave(self):
        """正弦波价格 → 多次穿越"""
        t = np.linspace(0, 4 * np.pi, 100)
        prices = pd.Series(10.0 + 3.0 * np.sin(t))
        result = estimate_rebalancing_frequency(prices, 20, 7.0, 13.0)
        assert result > 10

    def test_short_data(self):
        """数据不足 → 0"""
        result = estimate_rebalancing_frequency(pd.Series([10.0]), 10, 5.0, 15.0)
        assert result == 0


class TestShannonInsight:
    def test_basic_insight(self):
        prices = create_price_series(10.0, 100, volatility=0.03)
        insight = calculate_shannon_insight(
            price_data=prices,
            grid_upper=15.0,
            grid_lower=5.0,
            grid_count=10,
        )
        assert insight.volatility > 0
        assert insight.volatility_drag > 0
        assert insight.expected_rebalances >= 0
        assert insight.recommendation != ""

    def test_low_volatility(self):
        prices = create_price_series(10.0, 100, volatility=0.005)
        insight = calculate_shannon_insight(
            price_data=prices,
            grid_upper=12.0,
            grid_lower=8.0,
            grid_count=5,
        )
        assert insight.volatility_drag < 0.01  # 低波动 → 低拖累

    def test_high_volatility(self):
        prices = create_price_series(10.0, 100, volatility=0.05)
        insight = calculate_shannon_insight(
            price_data=prices,
            grid_upper=20.0,
            grid_lower=5.0,
            grid_count=10,
        )
        assert insight.volatility_drag > 0.01  # 高波动 → 高拖累

    def test_empty_data(self):
        insight = calculate_shannon_insight(
            price_data=pd.Series([], dtype=float),
            grid_upper=15.0,
            grid_lower=5.0,
            grid_count=10,
        )
        assert insight.volatility == 0.0
        assert insight.recommendation == "数据不足"


class TestRecommendGridParams:
    def test_basic_recommendation(self):
        prices = create_price_series(10.0, 100)
        params = recommend_grid_params(prices)
        assert "grid_upper" in params
        assert "grid_lower" in params
        assert "grid_count" in params
        assert params["grid_upper"] > params["grid_lower"]
        assert params["grid_count"] >= 5

    def test_with_atr(self):
        prices = create_price_series(10.0, 50)
        params = recommend_grid_params(prices, atr=0.5)
        assert params["atr"] == 0.5
        # ATR=0.5 → range = current_price ± 3*ATR
        # current price varies due to random data
        assert params["grid_upper"] > params["grid_lower"]
        assert abs(params["grid_upper"] - params["grid_lower"] - 6 * 0.5) < 3.0  # ~3.0 range

    def test_empty_data(self):
        params = recommend_grid_params(pd.Series([], dtype=float))
        assert params["grid_count"] == 10  # defaults


class TestMarketRegime:
    def test_oscillating(self):
        """震荡市场"""
        t = np.linspace(0, 6 * np.pi, 60)
        prices = pd.Series(10.0 + 1.0 * np.sin(t))
        regime = get_market_regime(prices)
        assert regime == "震荡"

    def test_uptrend(self):
        """Uptrend market"""
        prices = pd.Series(np.arange(30) * 0.5 + 10)  # 强上涨
        regime = get_market_regime(prices)
        assert regime == "上涨"

    def test_downtrend(self):
        """Downtrend market"""
        prices = pd.Series(20.0 - np.arange(30) * 0.5)  # 强下跌
        regime = get_market_regime(prices)
        assert regime == "下跌"

    def test_short_data(self):
        """Insufficient data"""
        regime = get_market_regime(pd.Series([10.0, 11.0]))
        assert regime == "不确定"