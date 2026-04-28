"""
ATR 动态止损止盈模块 - GTAP 网格交易回测平台

提供平均真实波幅（Average True Range）计算功能，用于动态止损止盈。
ATR 是基于历史波动率的风险度量，比固定百分比更适应市场变化。
"""

from typing import Optional
import pandas as pd
import numpy as np
from .exceptions import MetricsError


def calculate_atr(
    data: pd.DataFrame,
    period: int = 14
) -> pd.Series:
    """
    计算平均真实波幅（ATR）。

    ATR 公式：
    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = TR.rolling(period).mean()

    Args:
        data: 包含 'high', 'low', 'close' 列的 DataFrame
        period: ATR 计算周期（默认 14，建议 14-20）

    Returns:
        每个时间点的 ATR 值（前 period-1 个值为 NaN）

    Raises:
        MetricsError: 当数据不足或缺少必要列时

    Examples:
        >>> df = pd.DataFrame({'high': [10, 11, 12], 'low': [9, 10, 11], 'close': [9.5, 10.5, 11.5]})
        >>> atr = calculate_atr(df, period=2)
        >>> print(atr.tail(1).values[0])  #  doctest: +SKIP
    """
    required_cols = {'high', 'low', 'close'}
    if not required_cols.issubset(data.columns):
        raise MetricsError(f"ATR 计算需要 {required_cols} 列，当前列: {list(data.columns)}")

    if len(data) < period:
        raise MetricsError(f"数据长度 ({len(data)}) 不足 ATR 周期 ({period})")

    if period < 2:
        raise MetricsError("ATR 周期必须 ≥ 2")

    # 计算 True Range
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift(1)).abs()
    low_close = (data['low'] - data['close'].shift(1)).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    # 使用简单移动平均（SMA）作为 ATR，前 period-1 个值为 NaN
    atr = true_range.rolling(window=period, min_periods=period).mean()

    return atr


def calculate_atr_from_ohlc(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    从 OHLC 序列直接计算 ATR（便捷函数）。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: ATR 周期

    Returns:
        ATR 值序列
    """
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    return calculate_atr(df, period=period)


def get_atr_stop_levels(
    entry_price: float,
    atr_value: float,
    stop_multiplier: float = 1.5,
    tp_multiplier: float = 0.5
) -> tuple[float, float]:
    """
    根据入场价格和 ATR 值计算止损止盈价位。

    Args:
        entry_price: 入场价格
        atr_value: 当前 ATR 值
        stop_multiplier: 止损乘数（默认 1.5）
        tp_multiplier: 止盈乘数（默认 0.5）

    Returns:
        (stop_loss_price, take_profit_price) 元组

    Examples:
        >>> get_atr_stop_levels(100.0, 2.0, 1.5, 0.5)
        (97.0, 101.0)
    """
    if atr_value <= 0:
        raise MetricsError(f"ATR 值必须为正数，当前: {atr_value}")

    if stop_multiplier <= 0:
        raise MetricsError("止损乘数必须 > 0")
    if tp_multiplier < 0:
        raise MetricsError("止盈乘数必须 ≥ 0")

    stop_distance = atr_value * stop_multiplier
    tp_distance = atr_value * tp_multiplier

    stop_loss_price = entry_price - stop_distance
    take_profit_price = entry_price + tp_distance

    return stop_loss_price, take_profit_price


def is_atr_stop_triggered(
    current_price: float,
    entry_price: float,
    atr_value: float,
    stop_multiplier: float = 1.5,
    tp_multiplier: float = 0.5,
    position_side: str = "long",
) -> tuple[bool, str]:
    """
    检查当前价格是否触发 ATR 止损或止盈。

    Args:
        current_price: 当前价格
        entry_price: 入场价格
        atr_value: 当前 ATR 值
        stop_multiplier: 止损乘数
        tp_multiplier: 止盈乘数
        position_side: 持仓方向，"long"（多头）或 "short"（空头）

    Returns:
        (是否触发, 触发类型 "stop_loss"/"take_profit"/"")

    Examples:
        >>> is_atr_stop_triggered(96.0, 100.0, 2.0, 1.5, 0.5, "long")
        (True, "stop_loss")
    """
    if atr_value <= 0:
        raise MetricsError(f"ATR 值必须为正数，当前: {atr_value}")

    # 根据持仓方向计算止损/止盈价位
    stop_distance = atr_value * stop_multiplier
    tp_distance = atr_value * tp_multiplier

    if position_side == "long":
        stop_loss_price = entry_price - stop_distance
        take_profit_price = entry_price + tp_distance
        if current_price <= stop_loss_price:
            return True, "stop_loss"
        if tp_multiplier > 0 and current_price >= take_profit_price:
            return True, "take_profit"
        return False, ""
    elif position_side == "short":
        stop_loss_price = entry_price + stop_distance
        take_profit_price = entry_price - tp_distance
        if current_price >= stop_loss_price:
            return True, "stop_loss"
        if tp_multiplier > 0 and current_price <= take_profit_price:
            return True, "take_profit"
        return False, ""
    else:
        raise MetricsError(f"不支持的持仓方向: {position_side}")
