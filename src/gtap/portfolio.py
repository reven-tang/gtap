"""
多资产组合回测模块 - GTAP 网格交易回测平台

支持同时交易多个资产，实现跨资产再平衡。
核心思路：对每个资产独立运行 grid_trading()，再汇总组合级指标。

Parrondo 模块见 parrondo.py。
"""

from dataclasses import dataclass, field
from typing import NamedTuple, Optional
import numpy as np
import pandas as pd

from .config import GridTradingConfig
from .grid import grid_trading, GridTradingResult
from .metrics import calculate_metrics, PerformanceMetrics
from .exceptions import PortfolioError


@dataclass
class PortfolioAssetConfig:
    """组合中单个资产的配置"""
    stock_code: str = "sh.601398"
    target_weight: float = 0.5  # 目标权重（所有资产权重之和应为1）
    grid_config: Optional[GridTradingConfig] = None  # 可独立配置网格参数，None 则用默认


@dataclass
class PortfolioConfig:
    """多资产组合配置"""
    assets: list[PortfolioAssetConfig] = field(default_factory=list)
    total_investment: float = 100000.0  # 组合总投入
    rebalance_threshold: float = 0.05  # 组合再平衡阈值
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    data_source: str = "baostock"

    def __post_init__(self):
        """验证组合配置"""
        if len(self.assets) < 2:
            raise PortfolioError("组合至少需要 2 个资产")
        total_weight = sum(a.target_weight for a in self.assets)
        if abs(total_weight - 1.0) > 0.01:
            raise PortfolioError(f"资产权重之和必须为1，当前={total_weight:.2f}")
        if self.total_investment <= 0:
            raise PortfolioError("组合总投入必须 > 0")


class PortfolioResult(NamedTuple):
    """组合回测结果"""
    asset_results: dict[str, GridTradingResult]  # 各资产的独立回测结果
    asset_metrics: dict[str, PerformanceMetrics]  # 各资产的独立指标
    portfolio_returns: list[float]  # 组合每日收益率序列
    portfolio_value_curve: list[float]  # 组合总资产价值曲线
    portfolio_total_return: float  # 组合总收益率
    portfolio_annual_return: float  # 组合年化收益率
    portfolio_sharpe: float  # 组合夏普比率
    portfolio_volatility: float  # 组合年化波动率
    portfolio_max_drawdown: float  # 组合最大回撤
    cross_correlation: dict[str, dict[str, float]]  # 跨资产相关性矩阵
    rebalancing_premium: float  # 再平衡溢价（组合收益 - 加权单资产收益）


def portfolio_backtest(
    portfolio_config: PortfolioConfig,
    data_dict: dict[str, pd.DataFrame],
    atr_dict: Optional[dict[str, pd.Series]] = None,
) -> PortfolioResult:
    """执行多资产组合回测

    Args:
        portfolio_config: 组合配置
        data_dict: 各资产的行情数据 {stock_code: DataFrame}
        atr_dict: 各资产的 ATR 数据（可选）

    Returns:
        PortfolioResult 组合回测结果

    Raises:
        PortfolioError: 配置错误或数据缺失
    """
    if atr_dict is None:
        atr_dict = {}

    asset_results = {}
    asset_metrics = {}

    for asset_cfg in portfolio_config.assets:
        code = asset_cfg.stock_code
        if code not in data_dict:
            raise PortfolioError(f"缺少 {code} 的行情数据")

        # 为每个资产构建独立的 GridTradingConfig
        if asset_cfg.grid_config is not None:
            grid_cfg = asset_cfg.grid_config
        else:
            # 默认配置：按权重分配投入
            investment = portfolio_config.total_investment * asset_cfg.target_weight
            grid_cfg = GridTradingConfig(
                stock_code=code,
                start_date=portfolio_config.start_date,
                end_date=portfolio_config.end_date,
                total_investment=investment,
                data_source=portfolio_config.data_source,
            )

        # 确保投入金额按权重分配
        grid_cfg = GridTradingConfig(
            stock_code=grid_cfg.stock_code,
            start_date=grid_cfg.start_date if grid_cfg.start_date != "2024-01-01" else portfolio_config.start_date,
            end_date=grid_cfg.end_date if grid_cfg.end_date != "2024-12-31" else portfolio_config.end_date,
            grid_upper=grid_cfg.grid_upper,
            grid_lower=grid_cfg.grid_lower,
            grid_number=grid_cfg.grid_number,
            grid_center=grid_cfg.grid_center,
            shares_per_grid=grid_cfg.shares_per_grid,
            initial_shares=grid_cfg.initial_shares,
            total_investment=portfolio_config.total_investment * asset_cfg.target_weight,
            auto_grid_range=grid_cfg.auto_grid_range,
            grid_range_atr_multiplier=grid_cfg.grid_range_atr_multiplier,
            commission_rate=grid_cfg.commission_rate,
            transfer_fee_rate=grid_cfg.transfer_fee_rate,
            stamp_duty_rate=grid_cfg.stamp_duty_rate,
            data_source=grid_cfg.data_source if grid_cfg.data_source != "baostock" else portfolio_config.data_source,
            frequency=grid_cfg.frequency,
            adjustflag=grid_cfg.adjustflag,
        )

        # 运行单资产回测
        result = grid_trading(
            data_dict[code],
            grid_cfg,
            atr_series=atr_dict.get(code),
        )
        asset_results[code] = result

        # 计算单资产指标
        metrics = calculate_metrics(
            asset_values=result.asset_values,
            trades=result.trades,
            total_fees=result.total_fees,
            start_date=pd.Timestamp(grid_cfg.start_date),
            end_date=pd.Timestamp(grid_cfg.end_date),
            trade_profits=result.trade_profits,
        )
        asset_metrics[code] = metrics

    # ========== 组合级指标计算 ==========

    # 1. 组合总资产价值曲线（各资产加权累加）
    # 对齐各资产的 asset_values 到相同长度
    min_len = min(len(r.asset_values) for r in asset_results.values())
    portfolio_value_curve = []
    for i in range(min_len):
        total_value = 0.0
        for asset_cfg in portfolio_config.assets:
            code = asset_cfg.stock_code
            total_value += asset_results[code].asset_values[i]
        portfolio_value_curve.append(total_value)

    # 2. 组合每日收益率
    portfolio_returns = []
    for i in range(1, len(portfolio_value_curve)):
        prev = portfolio_value_curve[i - 1]
        curr = portfolio_value_curve[i]
        if prev > 0:
            portfolio_returns.append((curr - prev) / prev)
        else:
            portfolio_returns.append(0.0)

    # 3. 组合基础指标
    total_investment = portfolio_config.total_investment
    final_value = portfolio_value_curve[-1] if portfolio_value_curve else 0.0
    portfolio_total_return = ((final_value - total_investment) / total_investment) * 100 if total_investment > 0 else 0.0

    # 年化收益率
    total_days = (pd.Timestamp(portfolio_config.end_date) - pd.Timestamp(portfolio_config.start_date)).days
    years = total_days / 365.0 if total_days > 0 else 1.0
    portfolio_annual_return = (
        ((final_value / total_investment) ** (1 / years) - 1) * 100
        if total_investment > 0 and years > 0
        else 0.0
    )

    # 年化波动率
    if len(portfolio_returns) > 1:
        daily_vol = np.std(portfolio_returns)
        portfolio_volatility = daily_vol * np.sqrt(252) * 100
    else:
        portfolio_volatility = 0.0

    # 夏普比率
    risk_free_daily = 0.03 / 252
    if portfolio_volatility > 0:
        excess_return = np.mean(portfolio_returns) - risk_free_daily
        portfolio_sharpe = (excess_return / (daily_vol if daily_vol > 0 else 0.001)) * np.sqrt(252)
    else:
        portfolio_sharpe = 0.0

    # 最大回撤
    max_dd = 0.0
    peak = portfolio_value_curve[0] if portfolio_value_curve else 0.0
    for v in portfolio_value_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    portfolio_max_drawdown = max_dd

    # 4. 跨资产相关性矩阵
    cross_correlation = {}
    codes = [a.stock_code for a in portfolio_config.assets]
    returns_dict = {}
    for code in codes:
        result = asset_results[code]
        values = result.asset_values[:min_len]
        rets = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                rets.append((values[i] - values[i - 1]) / values[i - 1])
            else:
                rets.append(0.0)
        returns_dict[code] = np.array(rets)

    for c1 in codes:
        cross_correlation[c1] = {}
        for c2 in codes:
            if len(returns_dict[c1]) > 1 and len(returns_dict[c2]) > 1:
                min_ret_len = min(len(returns_dict[c1]), len(returns_dict[c2]))
                corr = np.corrcoef(returns_dict[c1][:min_ret_len], returns_dict[c2][:min_ret_len])[0, 1]
                cross_correlation[c1][c2] = round(float(corr), 4)
            else:
                cross_correlation[c1][c2] = 0.0

    # 5. 再平衡溢价（组合收益 - 加权单资产收益）
    weighted_single_return = 0.0
    for asset_cfg in portfolio_config.assets:
        code = asset_cfg.stock_code
        weighted_single_return += asset_metrics[code]["total_return"] * asset_cfg.target_weight

    rebalancing_premium = portfolio_total_return - weighted_single_return

    return PortfolioResult(
        asset_results=asset_results,
        asset_metrics=asset_metrics,
        portfolio_returns=portfolio_returns,
        portfolio_value_curve=portfolio_value_curve,
        portfolio_total_return=round(portfolio_total_return, 2),
        portfolio_annual_return=round(portfolio_annual_return, 2),
        portfolio_sharpe=round(portfolio_sharpe, 2),
        portfolio_volatility=round(portfolio_volatility, 2),
        portfolio_max_drawdown=round(portfolio_max_drawdown, 2),
        cross_correlation=cross_correlation,
        rebalancing_premium=round(rebalancing_premium, 2),
    )


__all__ = [
    "PortfolioAssetConfig",
    "PortfolioConfig",
    "PortfolioResult",
    "portfolio_backtest",
    "PortfolioError",
]