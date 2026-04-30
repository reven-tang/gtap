"""
策略引擎抽象层 - GTAP 网格交易回测平台

定义策略 ABC 和基础实现，为后续多策略扩展提供接口。
当前阶段：定义接口 + GridStrategy 实现，RebalanceStrategy 实现。
grid.py 的逻辑保持不变（通过 strategy_mode 分支），后续逐步迁移到此模块。
"""

from abc import ABC, abstractmethod
from typing import Optional, NamedTuple
import pandas as pd

from .config import GridTradingConfig
from .fees import calculate_fees


class TradeSignal(NamedTuple):
    """策略产生的交易信号"""
    action: str  # "买入" / "卖出" / "hold"
    shares: int  # 交易数量
    reason: str  # "grid" / "rebalance" / "stop_loss" / "take_profit"


class StrategyEngine(ABC):
    """策略引擎抽象基类

    所有交易策略必须实现此接口。核心方法：
    - should_trade(): 判断是否应该交易
    - calculate_trade_size(): 计算交易数量

    这使得 grid.py 的逻辑可以逐步迁移到独立的策略类中，
    同时保持向后兼容。
    """

    @abstractmethod
    def should_trade(
        self,
        price: float,
        shares: int,
        cash: float,
        avg_price: float,
        position_ratio: float,
        config: GridTradingConfig,
    ) -> Optional[TradeSignal]:
        """判断是否应该交易，返回交易信号或 None"""
        ...

    @abstractmethod
    def calculate_trade_size(
        self,
        price: float,
        signal: TradeSignal,
        cash: float,
        shares: int,
        config: GridTradingConfig,
    ) -> int:
        """计算交易数量"""
        ...

    def get_name(self) -> str:
        """策略名称"""
        return self.__class__.__name__


class GridStrategy(StrategyEngine):
    """经典网格策略

    价格低于网格线 → 买入
    价格高于网格线 → 卖出
    网格间距可以是等差或等比
    """

    def __init__(self, grid_prices: list[float], shares_per_grid: int = 100):
        self.grid_prices = grid_prices
        self.shares_per_grid = shares_per_grid
        self.current_grid_center = grid_prices[len(grid_prices) // 2] if grid_prices else 0.0

    def should_trade(
        self,
        price: float,
        shares: int,
        cash: float,
        avg_price: float,
        position_ratio: float,
        config: GridTradingConfig,
    ) -> Optional[TradeSignal]:
        # 找到当前网格中心对应的上下网格线
        lower_grids = [gp for gp in self.grid_prices if gp < self.current_grid_center]
        upper_grids = [gp for gp in self.grid_prices if gp > self.current_grid_center]
        current_grid_lower = max(lower_grids) if lower_grids else self.grid_prices[0]
        current_grid_upper = min(upper_grids) if upper_grids else self.grid_prices[-1]

        if price < current_grid_lower and shares == 0:
            # 清仓时不交易
            return None

        if price < current_grid_lower:
            grid_step = (self.grid_prices[-1] - self.grid_prices[0]) / (len(self.grid_prices) - 1) if len(self.grid_prices) > 1 else 0.0
            grids = int((self.current_grid_center - price) // grid_step) if grid_step > 0 else 1
            if grids == 0:
                grids = 1
            return TradeSignal(action="买入", shares=grids * self.shares_per_grid, reason="grid")
        elif price > current_grid_upper and shares > 0:
            grid_step = (self.grid_prices[-1] - self.grid_prices[0]) / (len(self.grid_prices) - 1) if len(self.grid_prices) > 1 else 0.0
            grids = int((price - self.current_grid_center) // grid_step) if grid_step > 0 else 1
            if grids == 0:
                grids = 1
            return TradeSignal(action="卖出", shares=grids * self.shares_per_grid, reason="grid")

        return None

    def calculate_trade_size(
        self,
        price: float,
        signal: TradeSignal,
        cash: float,
        shares: int,
        config: GridTradingConfig,
    ) -> int:
        if config.position_mode == "fixed_shares":
            return signal.shares
        elif config.position_mode == "fixed_amount":
            return int(config.amount_per_grid / price)
        elif config.position_mode == "proportional":
            # 比例仓位：根据信号调整到目标比例
            return signal.shares  # 由 should_trade 计算
        return signal.shares

    def update_grid_center(self, action: str, price: float):
        """更新网格中心位置"""
        if action == "买入":
            self.current_grid_center = min(
                [gp for gp in self.grid_prices if gp > price],
                default=self.grid_prices[-1],
            )
        elif action == "卖出":
            self.current_grid_center = max(
                [gp for gp in self.grid_prices if gp < price],
                default=self.grid_prices[0],
            )


class RebalanceStrategy(StrategyEngine):
    """再平衡策略（香农的恶魔核心）

    当股票配置比例偏离目标超过阈值时，触发再平衡交易。
    再平衡的方向：股票占比过高 → 卖出；过低 → 买入。
    """

    def __init__(
        self,
        target_allocation: float = 0.5,
        rebalance_threshold: float = 0.05,
    ):
        self.target_allocation = target_allocation
        self.rebalance_threshold = rebalance_threshold

    def should_trade(
        self,
        price: float,
        shares: int,
        cash: float,
        avg_price: float,
        position_ratio: float,
        config: GridTradingConfig,
    ) -> Optional[TradeSignal]:
        deviation = abs(position_ratio - self.target_allocation)
        if deviation > self.rebalance_threshold:
            if position_ratio > self.target_allocation:
                # 股票占比过高，需要卖出
                return TradeSignal(action="卖出", shares=0, reason="rebalance")
            else:
                # 股票占比过低，需要买入
                return TradeSignal(action="买入", shares=0, reason="rebalance")
        return None

    def calculate_trade_size(
        self,
        price: float,
        signal: TradeSignal,
        cash: float,
        shares: int,
        config: GridTradingConfig,
    ) -> int:
        total_value = cash + shares * price
        target_stock_value = total_value * self.target_allocation
        current_stock_value = shares * price
        diff = target_stock_value - current_stock_value

        if signal.action == "买入":
            buy_amount = min(diff, cash)
            return int(buy_amount / price)
        elif signal.action == "卖出":
            sell_amount = min(-diff, shares * price)
            return int(sell_amount / price)
        return 0


# 策略工厂函数
def create_strategy(config: GridTradingConfig, grid_prices: list[float]) -> StrategyEngine:
    """根据配置创建策略引擎

    Args:
        config: 网格交易配置
        grid_prices: 网格价格列表

    Returns:
        StrategyEngine 实例
    """
    if config.strategy_mode == "rebalance_threshold":
        return RebalanceStrategy(
            target_allocation=config.target_allocation,
            rebalance_threshold=config.rebalance_threshold,
        )
    elif config.strategy_mode == "grid":
        return GridStrategy(
            grid_prices=grid_prices,
            shares_per_grid=config.shares_per_grid,
        )
    elif config.strategy_mode == "rebalance_periodic":
        # 周期性再平衡（暂用 threshold 策略模拟）
        return RebalanceStrategy(
            target_allocation=config.target_allocation,
            rebalance_threshold=config.rebalance_threshold,
        )
    else:
        raise ValueError(f"未知策略模式: {config.strategy_mode}")


__all__ = [
    "StrategyEngine",
    "TradeSignal",
    "GridStrategy",
    "RebalanceStrategy",
    "create_strategy",
]