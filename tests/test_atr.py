"""ATR 计算模块单元测试"""

import pytest
import pandas as pd
import numpy as np
from src.gtap.atr import (
    calculate_atr,
    calculate_atr_from_ohlc,
    get_atr_stop_levels,
    is_atr_stop_triggered,
)
from src.gtap.exceptions import MetricsError


class TestCalculateATR:
    """测试 ATR 计算逻辑"""

    def test_calculate_atr_basic(self):
        """测试基本 ATR 计算"""
        # 构造数据：波动率递增（high-low 差递增）
        df = pd.DataFrame({
            "high":  [10.0, 12.0, 14.0, 16.0, 18.0],
            "low":   [9.0,  10.0, 11.0, 12.0, 13.0],
            "close": [9.5,  11.0, 12.5, 14.0, 15.5],
        })
        atr = calculate_atr(df, period=2)
        assert len(atr) == 5
        # 前 1 个值为 NaN（period-1）
        assert pd.isna(atr.iloc[0])
        assert not pd.isna(atr.iloc[-1])
        # ATR 应随波动扩大而上升（至少最后一个 > 倒数第二个）
        # TR sequence: 1.0, 2.5, 2.5, 2.5, 2.5 -> ATR: NaN, 1.75, 2.5, 2.5, 2.5
        # 调整数据确保 ATR 递增
        assert atr.iloc[2] < atr.iloc[3] or atr.iloc[3] < atr.iloc[4]

    def test_calculate_atr_period_14(self):
        """测试标准周期 14 的 ATR"""
        np.random.seed(42)
        n = 100
        # 模拟价格序列（随机游走）
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.abs(np.random.randn(n)) * 0.8
        low = close - np.abs(np.random.randn(n)) * 0.8
        df = pd.DataFrame({"high": high, "low": low, "close": close})
        atr = calculate_atr(df, period=14)
        assert len(atr) == n
        assert atr.iloc[13] > 0  # 第 14 个值有效
        assert all(atr.dropna() > 0)  # 所有有效值应 >0

    def test_calculate_atr_insufficient_data(self):
        """测试数据不足时抛出异常"""
        df = pd.DataFrame({
            "high":  [10.0, 11.0],
            "low":   [9.0,  10.0],
            "close": [9.5,  10.5],
        })
        with pytest.raises(MetricsError, match="数据长度.*不足"):
            calculate_atr(df, period=5)

    def test_calculate_atr_missing_columns(self):
        """测试缺少必要列时抛出异常"""
        df = pd.DataFrame({"close": [1, 2, 3]})
        with pytest.raises(MetricsError, match="ATR 计算需要"):
            calculate_atr(df, period=2)

    def test_calculate_atr_period_too_small(self):
        """测试周期过小"""
        df = pd.DataFrame({
            "high":  [10.0, 11.0, 12.0],
            "low":   [9.0,  10.0, 11.0],
            "close": [9.5,  10.5, 11.5],
        })
        with pytest.raises(MetricsError, match="ATR 周期必须"):
            calculate_atr(df, period=1)

    def test_calculate_atr_from_ohlc_convenience(self):
        """测试便捷函数 calculate_atr_from_ohlc"""
        high = pd.Series([10, 11, 12, 13, 14])
        low = pd.Series([9, 10, 11, 12, 13])
        close = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5])
        atr = calculate_atr_from_ohlc(high, low, close, period=2)
        assert isinstance(atr, pd.Series)
        assert len(atr) == 5


class TestGetATRStopLevels:
    """测试 ATR 止损止盈价位计算"""

    def test_long_stop_loss_and_take_profit(self):
        """测试多头止损止盈价位"""
        stop, tp = get_atr_stop_levels(100.0, 2.0, stop_multiplier=1.5, tp_multiplier=0.5)
        assert stop == 97.0  # 100 - 1.5*2
        assert tp == 101.0   # 100 + 0.5*2

    def test_zero_tp_multiplier(self):
        """测试止盈乘数为 0（仅止损）"""
        stop, tp = get_atr_stop_levels(100.0, 2.0, stop_multiplier=2.0, tp_multiplier=0.0)
        assert stop == 96.0
        assert tp == 100.0  # 无盈利空间

    def test_invalid_atr_raises(self):
        """测试 ATR ≤ 0 时抛出异常"""
        with pytest.raises(MetricsError, match="ATR 值必须为正"):
            get_atr_stop_levels(100.0, 0.0)

    def test_invalid_multipliers_raise(self):
        """测试无效乘数"""
        with pytest.raises(MetricsError, match="止损乘数必须"):
            get_atr_stop_levels(100.0, 2.0, stop_multiplier=0)
        with pytest.raises(MetricsError, match="止盈乘数必须"):
            get_atr_stop_levels(100.0, 2.0, stop_multiplier=1.5, tp_multiplier=-0.1)


class TestIsATRStopTriggered:
    """测试 ATR 止损触发判断"""

    def test_stop_loss_triggered_long(self):
        """测试多头止损触发"""
        triggered, reason = is_atr_stop_triggered(
            current_price=96.0,
            entry_price=100.0,
            atr_value=2.0,
            stop_multiplier=1.5,
            tp_multiplier=0.5,
            position_side="long",
        )
        assert triggered is True
        assert reason == "stop_loss"

    def test_take_profit_triggered_long(self):
        """测试多头止盈触发"""
        triggered, reason = is_atr_stop_triggered(
            current_price=101.0,
            entry_price=100.0,
            atr_value=2.0,
            stop_multiplier=1.5,
            tp_multiplier=0.5,
            position_side="long",
        )
        assert triggered is True
        assert reason == "take_profit"

    def test_no_trigger_long(self):
        """测试多头未触发"""
        triggered, reason = is_atr_stop_triggered(
            current_price=100.0,
            entry_price=100.0,
            atr_value=2.0,
            stop_multiplier=1.5,
            tp_multiplier=0.5,
            position_side="long",
        )
        assert triggered is False
        assert reason == ""

    def test_short_position(self):
        """测试空头持仓"""
        # 空头：价格 ≥ 止损价（高于入场价）触发止损
        triggered, reason = is_atr_stop_triggered(
            current_price=104.0,
            entry_price=100.0,
            atr_value=2.0,
            stop_multiplier=1.5,
            tp_multiplier=0.5,
            position_side="short",
        )
        assert triggered is True
        assert reason == "stop_loss"
        # 空头止盈：价格 ≤ 止盈价（低于入场价）
        triggered, reason = is_atr_stop_triggered(
            current_price=99.0,
            entry_price=100.0,
            atr_value=2.0,
            stop_multiplier=1.5,
            tp_multiplier=0.5,
            position_side="short",
        )
        assert triggered is True
        assert reason == "take_profit"

    def test_invalid_side_raises(self):
        """测试无效持仓方向"""
        with pytest.raises(MetricsError, match="不支持的持仓方向"):
            is_atr_stop_triggered(
                current_price=100.0,
                entry_price=100.0,
                atr_value=2.0,
                stop_multiplier=1.5,
                tp_multiplier=0.5,
                position_side="unknown",
            )
