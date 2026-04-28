"""
网格交易回测引擎 - GTAP 网格交易回测平台

核心回测逻辑：根据网格参数在价格区间内自动买卖，计算交易记录和资产价值变化。

已修复的 bug：
- 冗余条件判断（`price < lower and price < lower`）
- grid_center 更新逻辑混乱
- 初始持仓费用计算
"""

from typing import NamedTuple
import pandas as pd
from .fees import calculate_fees
from .exceptions import GridTradingError
from .config import GridTradingConfig


class Trade(NamedTuple):
    """单笔交易记录"""
    action: str          # "买入" / "卖出"
    timestamp: pd.Timestamp
    price: float
    shares: int
    total_shares: int
    commission: float
    transfer_fee: float
    stamp_duty: float
    total_fee: float
    avg_price: float     # 交易前的平均持仓价


class GridTradingResult(NamedTuple):
    """网格交易回测结果"""
    trades: list[Trade]                # 交易记录
    total_buy_volume: float            # 总买入金额
    total_sell_volume: float           # 总卖出金额
    total_buy_count: int               # 买入次数
    total_sell_count: int              # 卖出次数
    trade_profits: list[float]         # 每笔卖出盈利列表
    asset_values: list[float]          # 每个时间点的资产价值
    total_fees: float                  # 总费用


def grid_trading(
    data: pd.DataFrame,
    config: GridTradingConfig,
) -> GridTradingResult:
    """
    执行网格交易回测。

    Args:
        data: 价格数据（DataFrame，索引为 datetime，包含 'close' 列）
        config: 网格交易配置

    Returns:
        GridTradingResult 回测结果

    Raises:
        GridTradingError: 回测过程出错
    """
    if data.empty:
        raise GridTradingError("输入数据为空")

    required_cols = {"close"}
    if not required_cols.issubset(data.columns):
        missing = required_cols - set(data.columns)
        raise GridTradingError(f"数据缺少必需列: {missing}")

    # 参数解构
    grid_upper = config.grid_upper
    grid_lower = config.grid_lower
    grid_number = config.grid_number
    grid_center = config.grid_center
    shares_per_grid = config.shares_per_grid
    initial_shares = config.initial_shares
    current_holding_price = config.current_holding_price
    total_investment = config.total_investment
    stock_code = config.stock_code
    commission_rate = config.commission_rate
    transfer_fee_rate = config.transfer_fee_rate
    stamp_duty_rate = config.stamp_duty_rate

    # 预计算网格线价格
    grid_step = (grid_upper - grid_lower) / (grid_number - 1)
    grid_prices = [grid_lower + i * grid_step for i in range(grid_number)]

    # 初始状态
    cash = total_investment - (current_holding_price * initial_shares)
    shares = initial_shares
    total_buy_volume = initial_shares * current_holding_price
    total_sell_volume = 0.0
    total_buy_count = 1  # 初次买入计入
    total_sell_count = 0
    trade_profits: list[float] = []
    asset_values: list[float] = []
    total_fees_acc = 0.0
    current_grid_center = grid_center
    avg_price = current_holding_price

    # 计算初次买入费用
    first_buy_amount = initial_shares * current_holding_price
    _, _, _, first_fee = calculate_fees(
        first_buy_amount, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
    )
    cash -= first_fee
    total_fees_acc += first_fee

    # 记录初次买入交易
    trades: list[Trade] = [
        Trade(
            action="买入",
            timestamp=data.index[0],
            price=current_holding_price,
            shares=initial_shares,
            total_shares=initial_shares,
            commission=0.0,
            transfer_fee=0.0,
            stamp_duty=0.0,
            total_fee=first_fee,
            avg_price=current_holding_price,
        )
    ]

    # 逐个 K 线回测
    for timestamp, row in data.iterrows():
        price = float(row["close"])

        # 找到当前网格中心对应的上下网格线
        lower_grids = [gp for gp in grid_prices if gp < current_grid_center]
        upper_grids = [gp for gp in grid_prices if gp > current_grid_center]
        current_grid_lower = max(lower_grids) if lower_grids else grid_lower
        current_grid_upper = min(upper_grids) if upper_grids else grid_upper

        # 如果已清仓，提前结束
        if shares == 0:
            break

        # ========== 买入逻辑 ==========
        if price < current_grid_lower:
            # 计算跨越的网格数（整除向下取整，至少 1 格）
            grids = int((current_grid_center - price) // grid_step) if grid_step > 0 else 0
            if grids == 0:
                grids = 1

            buy_shares = grids * shares_per_grid
            buy_amount = buy_shares * price

            commission, transfer_fee, stamp_duty, fee = calculate_fees(
                buy_amount, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
            )

            if cash >= buy_amount + fee and grids > 0:
                cash -= buy_amount + fee
                shares += buy_shares
                total_buy_volume += buy_amount
                total_buy_count += 1
                total_fees_acc += fee

                # 更新平均成本（加权平均）
                total_cost = (shares - buy_shares) * avg_price + buy_amount
                avg_price = total_cost / shares if shares > 0 else 0.0

                # 更新网格中心：买入后向上移动
                current_grid_center = min([gp for gp in grid_prices if gp > price], default=grid_upper)

                trades.append(
                    Trade(
                        action="买入",
                        timestamp=timestamp,
                        price=price,
                        shares=buy_shares,
                        total_shares=shares,
                        commission=commission,
                        transfer_fee=transfer_fee,
                        stamp_duty=stamp_duty,
                        total_fee=fee,
                        avg_price=avg_price,
                    )
                )

        # ========== 卖出逻辑 ==========
        elif price > current_grid_upper:
            grids = int((price - current_grid_center) // grid_step) if grid_step > 0 else 0
            if grids == 0:
                grids = 1

            sell_shares = min(grids * shares_per_grid, shares)
            if sell_shares > 0 and grids > 0:
                sell_amount = sell_shares * price

                commission, transfer_fee, stamp_duty, fee = calculate_fees(
                    sell_amount, False, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                )

                cash += sell_amount - fee
                total_sell_volume += sell_amount
                total_sell_count += 1
                total_fees_acc += fee

                # 计算这笔卖出的盈亏（基于卖出前的平均成本）
                cost_basis = sell_shares * avg_price
                profit = sell_amount - cost_basis - fee
                trade_profits.append(profit)

                shares -= sell_shares
                # 更新平均成本
                if shares > 0:
                    total_cost = (shares + sell_shares) * avg_price - sell_amount
                    avg_price = total_cost / shares
                else:
                    avg_price = 0.0

                # 更新网格中心：卖出后向下移动
                current_grid_center = max([gp for gp in grid_prices if gp < price], default=grid_lower)

                trades.append(
                    Trade(
                        action="卖出",
                        timestamp=timestamp,
                        price=price,
                        shares=sell_shares,
                        total_shares=shares,
                        commission=commission,
                        transfer_fee=transfer_fee,
                        stamp_duty=stamp_duty,
                        total_fee=fee,
                        avg_price=avg_price,
                    )
                )

        # 记录资产价值
        asset_value = cash + shares * price
        asset_values.append(asset_value)

    return GridTradingResult(
        trades=trades,
        total_buy_volume=total_buy_volume,
        total_sell_volume=total_sell_volume,
        total_buy_count=total_buy_count,
        total_sell_count=total_sell_count,
        trade_profits=trade_profits,
        asset_values=asset_values,
        total_fees=total_fees_acc,
    )
