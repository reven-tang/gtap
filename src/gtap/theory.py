"""
香农理论计算模块 - GTAP 理论可视化支持

提供基于香农恶魔理论的实时计算和预测：
- 波动拖累计算
- 再平衡溢价预估
- 凯利准则最优仓位
- 理论再平衡频率预测
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class ShannonInsight:
    """香农理论洞察结果"""
    # 波动分析
    volatility: float                    # 年化波动率
    volatility_drag: float              # 波动拖累

    # 再平衡分析
    expected_rebalances: int            # 预期再平衡次数
    rebalancing_premium: float         # 预期再平衡溢价
    optimal_allocation: float           # 凯利准则最优比例

    # 对比分析
    buy_hold_return: float              # 买入持有预期收益
    rebalanced_return: float            # 再平衡预期收益
    net_benefit: float                  # 净收益（再平衡 - 买入持有 - 摩擦）

    # 建议
    recommendation: str                 # 配置建议
    confidence: str                     # 信心等级 (高/中/低)


def calculate_volatility_drag(annual_volatility: float) -> float:
    """
    计算波动拖累：σ²/2

    Args:
        annual_volatility: 年化波动率 (如 0.2 表示 20%)

    Returns:
        波动拖累百分比 (如 0.02 表示 2%)
    """
    return annual_volatility ** 2 / 2


def kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    """
    凯利准则：计算最优仓位比例

    f* = (bp - q) / b
    其中:
    b = 平均盈利/平均亏损 (赔率)
    p = 胜率
    q = 败率 = 1-p

    Args:
        win_rate: 胜率 (0-1)
        avg_win: 平均盈利比例
        avg_loss: 平均亏损比例

    Returns:
        最优仓位比例 (0-1)，可能 >1 表示可以加杠杆
    """
    if avg_loss == 0:
        return 1.0  # 无亏损，全仓

    b = avg_win / avg_loss  # 赔率
    p = win_rate
    q = 1 - win_rate

    f_star = (b * p - q) / b
    return max(0.0, min(1.0, f_star))  # 限制在 0-1 之间


def estimate_rebalancing_frequency(
    price_data: pd.Series,
    grid_count: int,
    grid_upper: float,
    grid_lower: float,
) -> int:
    """
    估算给定网格配置下的预期再平衡次数

    基于价格穿越网格线的频率估算

    Args:
        price_data: 价格序列
        grid_count: 网格数量
        grid_upper: 网格上限
        grid_lower: 网格下限

    Returns:
        预期再平衡次数
    """
    if len(price_data) < 2:
        return 0

    # 计算网格线
    grid_step = (grid_upper - grid_lower) / grid_count
    grid_lines = [grid_lower + i * grid_step for i in range(grid_count + 1)]

    # 计算价格穿越网格线的次数
    crossings = 0
    prev_bucket = None

    for price in price_data:
        # 找到当前价格所在的网格区间
        bucket = int((price - grid_lower) / grid_step)
        bucket = max(0, min(grid_count - 1, bucket))

        if prev_bucket is not None and bucket != prev_bucket:
            crossings += 1

        prev_bucket = bucket

    return crossings


def calculate_shannon_insight(
    price_data: pd.Series,
    grid_upper: float,
    grid_lower: float,
    grid_count: int,
    target_allocation: float = 0.5,
    commission_rate: float = 0.0003,
    rebalance_threshold: float = 0.05,
) -> ShannonInsight:
    """
    计算香农理论洞察

    Args:
        price_data: 价格序列
        grid_upper: 网格上限
        grid_lower: 网格下限
        grid_count: 网格数量
        target_allocation: 目标股票比例
        commission_rate: 佣金费率
        rebalance_threshold: 再平衡阈值

    Returns:
        ShannonInsight 包含各项理论指标
    """
    if len(price_data) < 2:
        return ShannonInsight(
            volatility=0.0,
            volatility_drag=0.0,
            expected_rebalances=0,
            rebalancing_premium=0.0,
            optimal_allocation=0.5,
            buy_hold_return=0.0,
            rebalanced_return=0.0,
            net_benefit=0.0,
            recommendation="数据不足",
            confidence="低",
        )

    # 1. 计算波动率
    returns = price_data.pct_change().dropna()
    daily_vol = returns.std()
    annual_vol = daily_vol * np.sqrt(252)  # 假设252个交易日

    # 2. 波动拖累
    vol_drag = calculate_volatility_drag(annual_vol)

    # 3. 预期再平衡次数
    expected_rebalances = estimate_rebalancing_frequency(
        price_data, grid_count, grid_upper, grid_lower
    )

    # 4. 买入持有预期收益（简化：基于历史年化）
    total_return = (price_data.iloc[-1] / price_data.iloc[0]) - 1
    years = len(price_data) / 252
    if years > 0:
        annual_return = (1 + total_return) ** (1/years) - 1
    else:
        annual_return = total_return

    buy_hold_return = annual_return

    # 5. 再平衡溢价估算
    # 简化模型：再平衡可以减少约 50% 的波动拖累
    rebalancing_premium = vol_drag * 0.5

    # 6. 交易成本估算
    avg_trade_value = price_data.mean() * 100  # 假设每格100股
    cost_per_trade = avg_trade_value * commission_rate * 2  # 买卖各一次
    total_cost = expected_rebalances * cost_per_trade
    cost_drag = total_cost / (price_data.iloc[0] * 100) if price_data.iloc[0] > 0 else 0

    # 7. 净收益
    rebalanced_return = buy_hold_return + rebalancing_premium - cost_drag
    net_benefit = rebalancing_premium - cost_drag

    # 8. 凯利准则最优仓位（简化：假设胜率为50%，盈亏比为1）
    optimal_allocation = 0.5  # 保守估计

    # 9. 生成建议
    if net_benefit > 0.02:
        recommendation = f"当前配置优秀，预期再平衡溢价 {net_benefit*100:.1f}%"
        confidence = "高"
    elif net_benefit > 0:
        recommendation = f"当前配置可行，再平衡溢价 {net_benefit*100:.1f}% 可覆盖成本"
        confidence = "中"
    else:
        recommendation = f"当前配置可能亏损，建议调整网格密度或阈值"
        confidence = "低"

    return ShannonInsight(
        volatility=annual_vol,
        volatility_drag=vol_drag,
        expected_rebalances=expected_rebalances,
        rebalancing_premium=rebalancing_premium,
        optimal_allocation=optimal_allocation,
        buy_hold_return=buy_hold_return,
        rebalanced_return=rebalanced_return,
        net_benefit=net_benefit,
        recommendation=recommendation,
        confidence=confidence,
    )


def recommend_grid_params(
    price_data: pd.Series,
    atr: Optional[float] = None,
) -> Dict[str, float]:
    """
    基于ATR和价格数据推荐网格参数

    Args:
        price_data: 价格序列
        atr: ATR值（可选）

    Returns:
        推荐参数字典
    """
    if len(price_data) == 0:
        return {
            "grid_upper": 10.0,
            "grid_lower": 5.0,
            "grid_count": 10,
            "grid_spacing": 0.5,
        }

    current_price = price_data.iloc[-1]

    # 如果没有提供ATR，估算一个
    if atr is None:
        returns = price_data.pct_change().dropna()
        daily_vol = returns.std()
        atr = current_price * daily_vol * 14  # 粗略估计14日ATR

    # 推荐网格范围：当前价格 ± 3×ATR
    grid_upper = current_price + 3 * atr
    grid_lower = max(current_price - 3 * atr, current_price * 0.5)  # 不低于50%

    # 推荐网格数量：基于ATR和范围
    price_range = grid_upper - grid_lower
    if price_range > 0 and atr > 0:
        # 每格间距 ≈ 0.5-1 × ATR
        optimal_spacing = 0.7 * atr
        grid_count = max(5, min(20, int(price_range / optimal_spacing)))
    else:
        grid_count = 10

    grid_spacing = (grid_upper - grid_lower) / grid_count

    return {
        "grid_upper": round(grid_upper, 2),
        "grid_lower": round(grid_lower, 2),
        "grid_count": grid_count,
        "grid_spacing": round(grid_spacing, 2),
        "atr": round(atr, 4) if atr else None,
    }


def get_market_regime(price_data: pd.Series) -> str:
    """判断市场状态：震荡、趋势、或不确定

    v1.1.1: 改进阈值，减少"不确定"的比例
    - 动态阈值基于数据本身的波动率
    - 加入趋势方向一致性判断
    - 多层级判断逻辑

    Args:
        price_data: 价格序列

    Returns:
        "震荡", "上涨", "下跌", 或 "不确定"
    """
    if len(price_data) < 20:
        return "不确定"

    n = len(price_data)

    # 1. 趋势方向
    long_window = max(20, n // 3)
    long_ma = price_data.rolling(long_window).mean().iloc[-1]
    current = price_data.iloc[-1]
    trend_pct = (current - long_ma) / long_ma if long_ma > 0 else 0

    # 2. 趋势强度：回归斜率
    try:
        x = np.arange(n)
        y = price_data.values
        slope = np.polyfit(x, y, 1)[0]
        normalized_slope = slope / price_data.mean() * n
    except Exception:
        normalized_slope = 0

    # 3. 波动率
    returns = price_data.pct_change().dropna()
    if len(returns) < 5:
        return "不确定"
    volatility = returns.std()

    # 4. 方向一致性
    diffs = price_data.diff().dropna()
    if len(diffs) == 0:
        return "不确定"
    up_pct = (diffs > 0).sum() / len(diffs)
    directionality = max(up_pct, 1 - up_pct)

    # 5. 动态阈值
    trend_threshold = max(0.02, volatility * 3)

    # 6. 判断逻辑
    if normalized_slope > trend_threshold and directionality > 0.55:
        return "上涨"
    elif normalized_slope < -trend_threshold and directionality > 0.55:
        return "下跌"
    elif directionality < 0.55 and abs(normalized_slope) < trend_threshold:
        return "震荡"
    elif trend_pct > trend_threshold:
        return "上涨"
    elif trend_pct < -trend_threshold:
        return "下跌"
    elif abs(trend_pct) < trend_threshold:
        return "震荡"
    return "不确定"
