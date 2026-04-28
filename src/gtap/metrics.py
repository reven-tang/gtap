"""
绩效指标计算模块 - GTAP 网格交易回测平台

计算网格交易回测的各项绩效指标：总收益、年化收益、波动率、Sharpe、Sortino、
最大回撤、Calmar、盈亏比、恢复因子等。
"""

from typing import TypedDict, Union
import pandas as pd
import numpy as np
from .exceptions import MetricsError


class PerformanceMetrics(TypedDict):
    """绩效指标字典类型"""
    total_return: float          # 总收益率（%）
    total_return_after_fees: float  # 扣除费用后总收益率（%）
    annual_return: float         # 年化收益率（%）
    annual_return_after_fees: float  # 扣除费用后年化收益率（%）
    annual_volatility: float     # 年化波动率（%）
    annual_volatility_after_fees: float  # 扣除费用后年化波动率（%）
    sharpe_ratio: float          # 夏普比率
    sortino_ratio: float         # 索提诺比率
    max_drawdown: float          # 最大回撤（%）
    calmar_ratio: float          # 卡尔玛比率
    profit_factor: float         # 盈亏比
    recovery_factor: float       # 恢复因子
    win_rate: float              # 胜率
    total_trades: int            # 总交易次数
    best_trade: float            # 最佳单笔收益
    worst_trade: float           # 最差单笔亏损
    avg_trade: float             # 平均交易收益


def calculate_metrics(
    asset_values: list[float],
    trades: list,
    initial_investment: float,
    total_investment: float,
    total_fees: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    risk_free_rate: float = 0.03,  # 无风险利率 3%
) -> PerformanceMetrics:
    """
    计算网格交易回测的绩效指标。

    Args:
        asset_values: 资产价值序列（每个时间点的总资产）
        trades: 交易记录列表
        initial_investment: 初始投资金额
        total_investment: 总投入资金
        total_fees: 总费用
        start_date: 回测开始日期
        end_date: 回测结束日期
        risk_free_rate: 年化无风险利率（默认 3%）

    Returns:
        PerformanceMetrics 字典，包含各项指标

    Raises:
        MetricsError: 计算失败
    """
    if not asset_values or initial_investment <= 0:
        raise MetricsError("无效的输入数据：资产价值为空或初始投资 ≤ 0")

    # 转换为 numpy 数组便于计算
    values = np.array(asset_values, dtype=float)

    # ---------- 基础收益指标 ----------
    final_value = values[-1]
    profit = final_value - total_investment
    profit_pct = (profit / total_investment) * 100

    profit_after_fees = profit - total_fees
    profit_pct_after_fees = (profit_after_fees / total_investment) * 100

    # 年化参数
    total_days = (end_date - start_date).days
    if total_days <= 0:
        raise MetricsError("结束日期必须晚于开始日期")

    years = total_days / 365.0
    if years <= 0:
        raise MetricsError("回测周期必须大于 0 天")

    # 年化收益率（简单复利）
    annual_return = ((final_value / total_investment) ** (1 / years) - 1) * 100
    annual_return_after_fees = (((final_value - total_fees) / total_investment) ** (1 / years) - 1) * 100

    # ---------- 波动率 ----------
    # 从 asset_values 推算日收益率（假设数据点为日频或可视为日频）
    # 注意：如果原始数据是分钟级，此处需按实际频率调整
    returns = np.diff(values) / values[:-1]
    if len(returns) == 0:
        raise MetricsError("收益率序列为空")

    daily_vol = np.std(returns, ddof=1)
    annual_vol = daily_vol * np.sqrt(252) * 100  # 年化波动率（%）

    # 扣除费用后的近似收益率序列（均匀分摊费用）
    fee_per_period = total_fees / len(returns) if len(returns) > 0 else 0.0
    returns_after_fees = returns - (fee_per_period / values[:-1])
    annual_vol_after_fees = np.std(returns_after_fees, ddof=1) * np.sqrt(252) * 100

    # ---------- 夏普比率 ----------
    # 日化无风险利率
    rf_daily = (1 + risk_free_rate) ** (1 / 252) - 1
    excess_returns = returns - rf_daily
    if np.std(excess_returns, ddof=1) > 0:
        sharpe = np.mean(excess_returns) / np.std(excess_returns, ddof=1) * np.sqrt(252)
    else:
        sharpe = 0.0

    # ---------- 索提诺比率 ----------
    # 下行标准差（仅负收益）
    negative_returns = returns[returns < 0]
    if len(negative_returns) > 0 and np.std(negative_returns, ddof=1) > 0:
        sortino = np.mean(returns) / np.std(negative_returns, ddof=1) * np.sqrt(252)
    else:
        sortino = 0.0 if np.mean(returns) >= 0 else -np.inf

    # ---------- 最大回撤 ----------
    # 计算累计最大值序列
    cummax = np.maximum.accumulate(values)
    drawdown = (values - cummax) / cummax
    max_dd = np.min(drawdown) * 100  # 转为百分比

    # ---------- 卡尔玛比率 ----------
    calmar = (annual_return / 100) / (-max_dd / 100) if max_dd < 0 else 0.0

    # ---------- 交易指标 ----------
    total_trades = len(trades)
    sell_profits = [t for t in trades if t.action == "卖出"]
    buy_profits = [t for t in trades if t.action == "买入"]

    if sell_profits:
        profits = [s.avg_price for s in sell_profits]  # 这里需要从 Trade 中提取盈亏
        # 由于 Trade 中直接存 avg_price，我们从 grid.py 的 trade_profits 列表计算
        pass

    # win_rate 和 avg_trade 需要外部传入 trade_profits 列表
    # 本函数仅从 trades 计算次数，盈亏需另外传递

    return PerformanceMetrics(
        total_return=round(profit_pct, 2),
        total_return_after_fees=round(profit_pct_after_fees, 2),
        annual_return=round(annual_return, 2),
        annual_return_after_fees=round(annual_return_after_fees, 2),
        annual_volatility=round(annual_vol, 2),
        annual_volatility_after_fees=round(annual_vol_after_fees, 2),
        sharpe_ratio=round(sharpe, 2),
        sortino_ratio=round(sortino, 2),
        max_drawdown=round(max_dd, 2),
        calmar_ratio=round(calmar, 2),
        profit_factor=0.0,      # 待补充
        recovery_factor=0.0,    # 待补充
        win_rate=0.0,           # 待补充
        total_trades=total_trades,
        best_trade=0.0,         # 待补充
        worst_trade=0.0,        # 待补充
        avg_trade=0.0,          # 待补充
    )


def calculate_trade_metrics(
    trade_profits: list[float],
    total_buy_count: int,
    total_sell_count: int,
) -> dict[str, Union[float, int]]:
    """
    计算交易相关指标（盈亏比、胜率等）。

    Args:
        trade_profits: 每笔卖出交易的盈利列表
        total_buy_count: 总买入次数
        total_sell_count: 总卖出次数

    Returns:
        包含 win_rate、profit_factor、best/worst/avg trade 的字典
    """
    if not trade_profits:
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "avg_trade": 0.0,
        }

    wins = [p for p in trade_profits if p > 0]
    losses = [abs(p) for p in trade_profits if p < 0]

    win_rate = len(wins) / len(trade_profits) if trade_profits else 0.0
    total_wins = sum(wins)
    total_losses = sum(losses)
    profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")
    best_trade = max(trade_profits) if trade_profits else 0.0
    worst_trade = min(trade_profits) if trade_profits else 0.0
    avg_trade = sum(trade_profits) / len(trade_profits) if trade_profits else 0.0

    return {
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else float("inf"),
        "best_trade": round(best_trade, 2),
        "worst_trade": round(worst_trade, 2),
        "avg_trade": round(avg_trade, 2),
        "total_buy_count": total_buy_count,
        "total_sell_count": total_sell_count,
    }
