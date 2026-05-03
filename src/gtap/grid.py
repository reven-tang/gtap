"""
网格交易回测引擎 - GTAP 网格交易回测平台

核心回测逻辑：根据网格参数在价格区间内自动买卖，计算交易记录和资产价值变化。

已修复的 bug：
- 冗余条件判断（`price < lower and price < lower`）
- grid_center 更新逻辑混乱
- 初始持仓费用计算
"""

from typing import NamedTuple, Optional
import pandas as pd
from .fees import calculate_fees
from .exceptions import GridTradingError
from .config import GridTradingConfig


class Trade(NamedTuple):
    """单笔交易记录"""
    action: str                  # "买入" / "卖出"
    timestamp: pd.Timestamp
    price: float
    shares: int
    total_shares: int
    commission: float
    transfer_fee: float
    stamp_duty: float
    total_fee: float
    avg_price: float             # 交易前的平均持仓价
    atr_value: float = 0.0       # 入场时的 ATR 值（ATR 止损止盈专用）
    stop_loss_price: float = 0.0  # 止损价位
    take_profit_price: float = 0.0  # 止盈价位
    exit_reason: str = "grid"    # 退出原因: grid/stop_loss/take_profit


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
    # ATR 统计（v0.3.0+）
    stop_loss_count: int = 0           # 止损次数
    take_profit_count: int = 0         # 止盈次数
    grid_trade_count: int = 0          # 网格触发次数（非止损/止盈）


def grid_trading(
    data: pd.DataFrame,
    config: GridTradingConfig,
    atr_series: Optional[pd.Series] = None,
) -> GridTradingResult:
    """
    执行网格交易回测。

    Args:
        data: 价格数据（DataFrame，索引为 datetime，包含 'close' 列，可选 'high'/'low'）
        config: 网格交易配置
        atr_series: ATR 序列（可选，长度需与 data 一致；为 None 时不启用 ATR 止损）

    Returns:
        GridTradingResult 回测结果

    Raises:
        GridTradingError: 回测过程出错
    """
    # data 可能是 StockData 对象或 DataFrame，统一转换为 DataFrame
    if hasattr(data, 'kline'):
        data = data.kline
    
    if data.empty:
        raise GridTradingError("输入数据为空")

    required_cols = {"close"}
    if not required_cols.issubset(data.columns):
        missing = required_cols - set(data.columns)
        raise GridTradingError(f"数据缺少必需列: {missing}")

    # 参数解构
    grid_number = config.grid_number
    shares_per_grid = config.shares_per_grid
    initial_shares = config.initial_shares
    total_investment = config.total_investment
    stock_code = config.stock_code
    commission_rate = config.commission_rate
    transfer_fee_rate = config.transfer_fee_rate
    stamp_duty_rate = config.stamp_duty_rate
    # ATR 参数
    use_atr_stop = config.use_atr_stop
    atr_stop_multiplier = config.atr_stop_multiplier
    atr_tp_multiplier = config.atr_tp_multiplier

    # === P1: 策略模式和仓位参数 ===
    strategy_mode = config.strategy_mode
    target_allocation = config.target_allocation
    rebalance_threshold = config.rebalance_threshold
    position_mode = config.position_mode
    amount_per_grid = config.amount_per_grid
    grid_spacing_mode = config.grid_spacing_mode

    # === P0-1 & P0-2: 自动获取起始日收盘价 ===
    entry_price = float(data.iloc[0]['close'])
    current_holding_price = entry_price
    grid_center = config.grid_center if config.grid_center is not None else entry_price

    # === P0-3: ATR 自动网格范围 ===
    if config.auto_grid_range:
        if atr_series is not None:
            valid_atr = atr_series.dropna()
            if len(valid_atr) > 0:
                avg_atr = float(valid_atr.mean())
                atr_mult = config.grid_range_atr_multiplier
                grid_lower = entry_price - avg_atr * atr_mult
                grid_upper = entry_price + avg_atr * atr_mult
            else:
                # ATR全NaN → 用数据标准差作为fallback
                price_std = data["close"].std()
                atr_mult = config.grid_range_atr_multiplier
                grid_lower = entry_price - price_std * atr_mult
                grid_upper = entry_price + price_std * atr_mult
        else:
            # 无ATR数据 → 用数据标准差作为fallback
            price_std = data["close"].std()
            atr_mult = config.grid_range_atr_multiplier
            grid_lower = entry_price - price_std * atr_mult
            grid_upper = entry_price + price_std * atr_mult
    else:
        grid_upper = config.grid_upper
        grid_lower = config.grid_lower

    # 预计算网格线价格
    if grid_spacing_mode == "geometric" and grid_lower > 0 and grid_upper > grid_lower:
        grid_ratio = (grid_upper / grid_lower) ** (1 / (grid_number - 1))
        grid_prices = [grid_lower * (grid_ratio ** i) for i in range(grid_number)]
        grid_step = (grid_upper - grid_lower) / (grid_number - 1)  # 仅用于显示
    else:
        # 等差网格（默认）
        grid_step = (grid_upper - grid_lower) / (grid_number - 1)
        grid_prices = [grid_lower + i * grid_step for i in range(grid_number)]

    # 初始状态
    cash = total_investment - (entry_price * initial_shares)
    shares = initial_shares
    total_buy_volume = initial_shares * entry_price
    total_sell_volume = 0.0
    total_buy_count = 1  # 初次买入计入
    total_sell_count = 0
    trade_profits: list[float] = []
    asset_values: list[float] = []
    total_fees_acc = 0.0
    current_grid_center = grid_center
    avg_price = entry_price
    # ATR 统计
    stop_loss_count = 0
    take_profit_count = 0
    grid_trade_count = 0

    # 计算初次买入费用
    first_buy_amount = initial_shares * entry_price
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
            price=entry_price,
            shares=initial_shares,
            total_shares=initial_shares,
            commission=0.0,
            transfer_fee=0.0,
            stamp_duty=0.0,
            total_fee=first_fee,
            avg_price=entry_price,
            atr_value=0.0,
            stop_loss_price=0.0,
            take_profit_price=0.0,
            exit_reason="grid",
        )
    ]

    # 逐个 K 线回测
    for timestamp, row in data.iterrows():
        price = float(row["close"])

        # --- ATR 动态止损止盈检查（优先于网格交易）---
        exit_reason: str = "grid"  # 默认退出原因
        if use_atr_stop and shares > 0:
            # 获取当前 ATR 值
            try:
                atr_value = float(atr_series.loc[timestamp]) if atr_series is not None else 0.0
            except (KeyError, TypeError):
                atr_value = 0.0

            # 仅在有持仓且 ATR 有效时检查
            if atr_value > 0 and shares > 0:
                # 计算止损止盈价位
                stop_distance = atr_value * atr_stop_multiplier
                stop_loss_price = avg_price - stop_distance  # 多头止损
                take_profit_price = avg_price + (atr_value * atr_tp_multiplier)  # 多头止盈

                # 检查触发
                if price <= stop_loss_price:
                    exit_reason = "stop_loss"
                elif price >= take_profit_price and atr_tp_multiplier > 0:
                    exit_reason = "take_profit"
                else:
                    exit_reason = "grid"

                # 执行强制平仓（止损/止盈触发）
                if exit_reason in ("stop_loss", "take_profit"):
                    sell_shares = shares
                    sell_amount = sell_shares * price

                    commission, transfer_fee, stamp_duty, fee = calculate_fees(
                        sell_amount, False, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                    )

                    cash += sell_amount - fee
                    total_sell_volume += sell_amount
                    total_sell_count += 1
                    total_fees_acc += fee

                    cost_basis = sell_shares * avg_price
                    profit = sell_amount - cost_basis - fee
                    trade_profits.append(profit)

                    # 记录止损/止盈交易
                    trades.append(
                        Trade(
                            action="卖出",
                            timestamp=timestamp,
                            price=price,
                            shares=sell_shares,
                            total_shares=0,
                            commission=commission,
                            transfer_fee=transfer_fee,
                            stamp_duty=stamp_duty,
                            total_fee=fee,
                            avg_price=avg_price,
                            atr_value=atr_value,
                            stop_loss_price=stop_loss_price,
                            take_profit_price=take_profit_price,
                            exit_reason=exit_reason,
                        )
                    )

                    # 更新统计
                    if exit_reason == "stop_loss":
                        stop_loss_count += 1
                    else:
                        take_profit_count += 1

                    # 清仓后跳过后续网格逻辑
                    shares = 0
                    avg_price = 0.0
                    asset_value = cash  # 清仓后资产仅为现金
                    asset_values.append(asset_value)
                    continue

        # 找到当前网格中心对应的上下网格线
        lower_grids = [gp for gp in grid_prices if gp < current_grid_center]
        upper_grids = [gp for gp in grid_prices if gp > current_grid_center]
        current_grid_lower = max(lower_grids) if lower_grids else grid_lower
        current_grid_upper = min(upper_grids) if upper_grids else grid_upper

        # 如果已清仓，检查是否应重新建仓（P2-9）
        if shares == 0:
            # 重新建仓条件：价格回到网格范围内且有足够现金
            rebuy_shares = 0
            if price >= grid_lower and price <= grid_upper:
                # 用当前现金的一部分重新建仓
                rebuy_amount = min(cash * 0.5, cash - 5)  # 预留5元最低
                if rebuy_amount > 5:
                    rebuy_shares = int(rebuy_amount / price)
                    if rebuy_shares > 0:
                        rebuy_total = rebuy_shares * price
                        commission, tf, sd, fee = calculate_fees(
                            rebuy_total, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                        )
                        if cash >= rebuy_total + fee:
                            cash -= rebuy_total + fee
                            shares = rebuy_shares
                            total_buy_volume += rebuy_total
                            total_buy_count += 1
                            total_fees_acc += fee
                            avg_price = price
                            current_grid_center = grid_center
                            # 重新找到最近的网格线
                            lower_grids = [gp for gp in grid_prices if gp < current_grid_center]
                            upper_grids = [gp for gp in grid_prices if gp > current_grid_center]
                            current_grid_lower = max(lower_grids) if lower_grids else grid_lower
                            current_grid_upper = min(upper_grids) if upper_grids else grid_upper

                            trades.append(
                                Trade(
                                    action="买入",
                                    timestamp=timestamp,
                                    price=price,
                                    shares=rebuy_shares,
                                    total_shares=shares,
                                    commission=commission,
                                    transfer_fee=tf,
                                    stamp_duty=sd,
                                    total_fee=fee,
                                    avg_price=avg_price,
                                    atr_value=atr_value if use_atr_stop else 0.0,
                                    stop_loss_price=0.0,
                                    take_profit_price=0.0,
                                    exit_reason="reentry",
                                )
                            )
                            grid_trade_count += 1

            # 如果没有重新建仓，记录纯现金资产
            if shares == 0:
                asset_values.append(cash)
                continue

        # ========== P1-4: 再平衡策略检查 ==========
        # 计算当前资产总值和股票占比
        total_value = cash + shares * price
        current_stock_ratio = (shares * price) / total_value if total_value > 0 else 0.0

        # 再平衡模式：基于阈值偏离触发
        if strategy_mode == "rebalance_threshold":
            deviation = abs(current_stock_ratio - target_allocation)
            if deviation > rebalance_threshold:
                # 需要再平衡
                target_stock_value = total_value * target_allocation
                current_stock_value = shares * price
                diff = target_stock_value - current_stock_value

                if diff > 0:  # 需要买入
                    buy_amount = min(diff, cash)  # 不超过可用现金
                    if buy_amount > 5:  # 至少买 5 元
                        buy_shares = int(buy_amount / price)
                        if buy_shares > 0:
                            # position_mode 处理
                            if position_mode == "fixed_amount":
                                buy_shares = int(amount_per_grid / price)
                                buy_amount = buy_shares * price
                            elif position_mode == "proportional":
                                # proportional: 一次性调整到目标
                                buy_shares = int(diff / price)
                                buy_amount = buy_shares * price

                            commission, tf, sd, fee = calculate_fees(
                                buy_amount, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                            )
                            if cash >= buy_amount + fee:
                                cash -= buy_amount + fee
                                shares += buy_shares
                                total_buy_volume += buy_amount
                                total_buy_count += 1
                                total_fees_acc += fee

                                total_cost = (shares - buy_shares) * avg_price + buy_amount
                                avg_price = total_cost / shares if shares > 0 else 0.0

                                trades.append(
                                    Trade(
                                        action="买入",
                                        timestamp=timestamp,
                                        price=price,
                                        shares=buy_shares,
                                        total_shares=shares,
                                        commission=commission,
                                        transfer_fee=tf,
                                        stamp_duty=sd,
                                        total_fee=fee,
                                        avg_price=avg_price,
                                        atr_value=atr_value if use_atr_stop else 0.0,
                                        stop_loss_price=0.0,
                                        take_profit_price=0.0,
                                        exit_reason="rebalance",
                                    )
                                )
                                grid_trade_count += 1

                elif diff < 0:  # 需要卖出
                    sell_amount = min(-diff, shares * price)  # 不超过持仓市值
                    if sell_amount > 5:
                        sell_shares = int(sell_amount / price)
                        sell_shares = min(sell_shares, shares)
                        if sell_shares > 0:
                            sell_amount = sell_shares * price

                            commission, tf, sd, fee = calculate_fees(
                                sell_amount, False, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                            )

                            cash += sell_amount - fee
                            total_sell_volume += sell_amount
                            total_sell_count += 1
                            total_fees_acc += fee

                            cost_basis = sell_shares * avg_price
                            profit = sell_amount - cost_basis - fee
                            trade_profits.append(profit)

                            shares -= sell_shares
                            if shares > 0:
                                total_cost = (shares + sell_shares) * avg_price - sell_amount
                                avg_price = total_cost / shares
                            else:
                                avg_price = 0.0

                            trades.append(
                                Trade(
                                    action="卖出",
                                    timestamp=timestamp,
                                    price=price,
                                    shares=sell_shares,
                                    total_shares=shares,
                                    commission=commission,
                                    transfer_fee=tf,
                                    stamp_duty=sd,
                                    total_fee=fee,
                                    avg_price=avg_price,
                                    atr_value=atr_value if use_atr_stop else 0.0,
                                    stop_loss_price=0.0,
                                    take_profit_price=0.0,
                                    exit_reason="rebalance",
                                )
                            )
                            grid_trade_count += 1

                # 再平衡后记录资产值并继续
                asset_value = cash + shares * price
                asset_values.append(asset_value)
                continue

        # ========== 经典网格交易模式 ==========
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
                        atr_value=atr_value if use_atr_stop else 0.0,
                        stop_loss_price=0.0,
                        take_profit_price=0.0,
                        exit_reason="grid",
                    )
                )
                grid_trade_count += 1

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
                        atr_value=atr_value if use_atr_stop else 0.0,
                        stop_loss_price=0.0,
                        take_profit_price=0.0,
                        exit_reason="grid",
                    )
                )
                grid_trade_count += 1

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
        stop_loss_count=stop_loss_count,
        take_profit_count=take_profit_count,
        grid_trade_count=grid_trade_count,
    )
