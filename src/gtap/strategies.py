"""
策略引擎抽象层 + 理论信号管线 - GTAP 网格交易回测平台

定义策略 ABC 和基础实现，为后续多策略扩展提供接口。
核心新增：
- TheorySignal: 理论计算→策略执行的信号管线
- KellyRebalanceStrategy: 凯利准则驱动的动态仓位再平衡
- RegimeAwareEngine: 市场状态自适应策略切换
- AdaptiveGridStrategy: 波动率自适应网格策略
"""

from abc import ABC, abstractmethod
from typing import Optional, NamedTuple
from dataclasses import dataclass
import pandas as pd

from .config import GridTradingConfig
from .fees import calculate_fees
from .theory import kelly_criterion, get_market_regime, calculate_volatility_drag


class TradeSignal(NamedTuple):
    """策略产生的交易信号"""
    action: str  # "买入" / "卖出" / "hold"
    shares: int  # 交易数量
    reason: str  # "grid" / "rebalance" / "kelly_rebalance" / "regime_switch" / "stop_loss" / "take_profit"


@dataclass
class TheorySignal:
    """理论计算→策略执行的信号管线

    核心设计：让 theory.py 的计算结果驱动 strategies.py 的执行决策。
    这是从「理论计算器」到「理论驱动的策略引擎」的关键转变。
    """
    # 市场状态 → 策略选择
    regime: str           # "震荡" / "上涨" / "下跌" / "不确定"

    # 凯利最优 → target_allocation
    kelly_allocation: float  # 凯利准则最优仓位比例

    # 波动拖累 → 参数调整依据
    volatility_drag: float   # σ²/2 波动拖累

    # 推荐参数
    recommended_grid_count: Optional[int] = None  # 波动率自适应网格数
    recommended_threshold: Optional[float] = None  # 成本敏感阈值

    # 来源追踪
    source: str = "theory_signal"  # 信号来源标识

    @classmethod
    def from_price_data(
        cls,
        price_data: pd.Series,
        trades: Optional[list] = None,
        config: Optional[GridTradingConfig] = None,
        atr_value: Optional[float] = None,
        price_range: Optional[float] = None,
    ) -> "TheorySignal":
        """从价格数据计算完整的理论信号

        Args:
            price_data: 价格序列（需要足够长度）
            trades: 已完成的交易列表（用于凯利参数估计）
            config: 配置（用于获取回看窗口等参数）
            atr_value: ATR值（用于网格密度推荐）
            price_range: 网格价格范围（用于网格密度推荐）
        """
        if len(price_data) < 20:
            return cls(regime="不确定", kelly_allocation=0.5, volatility_drag=0.0)

        # 1. 市场状态判断
        regime = get_market_regime(price_data)

        # 2. 波动拖累计算
        returns = price_data.pct_change().dropna()
        annual_vol = returns.std() * (252 ** 0.5) if len(returns) > 0 else 0.0
        vol_drag = calculate_volatility_drag(annual_vol)

        # 3. 凯利准则仓位
        kelly_frac = 0.5  # 默认半凯利
        if config is not None:
            kelly_frac = config.kelly_fraction

        # 从历史交易估算胜率和盈亏比
        if trades is not None and len(trades) >= 5:
            sell_trades = [t for t in trades if t.action == "卖出"]
            if len(sell_trades) >= 3:
                # 简化：用最近的卖出交易估算胜率
                wins = sum(1 for t in sell_trades if t.price > t.avg_price)
                win_rate = wins / len(sell_trades)
                # 盈亏比估算
                avg_win_ratio = 0.05  # 默认5%盈利
                avg_loss_ratio = 0.03  # 默认3%亏损
                winning_trades = [t for t in sell_trades if t.price > t.avg_price]
                losing_trades = [t for t in sell_trades if t.price <= t.avg_price]
                if winning_trades:
                    avg_win_ratio = sum((t.price - t.avg_price) / (t.avg_price if t.avg_price > 0 else t.price) for t in winning_trades) / len(winning_trades)
                if losing_trades:
                    avg_loss_ratio = sum((t.avg_price - t.price) / (t.avg_price if t.avg_price > 0 else t.price) for t in losing_trades) / len(losing_trades)
                kelly_raw = kelly_criterion(win_rate, avg_win_ratio, avg_loss_ratio)
                kelly_allocation = min(kelly_raw * kelly_frac, 0.9)  # 上限90%
            else:
                kelly_allocation = 0.5 * kelly_frac  # 交易太少，保守估计
        else:
            # 无交易历史：基于波动率估算
            # 高波动→低仓位，低波动→高仓位
            if annual_vol > 0.4:
                kelly_allocation = 0.3 * kelly_frac  # 高波动保守
            elif annual_vol > 0.25:
                kelly_allocation = 0.5 * kelly_frac  # 中波动
            else:
                kelly_allocation = 0.7 * kelly_frac  # 低波动积极

        # 4. 推荐网格数（波动率自适应）
        recommended_grid_count = None
        if atr_value is not None and price_range is not None and atr_value > 0:
            density_ratio = 0.7  # 默认每格间距 = 0.7×ATR
            if config is not None:
                density_ratio = config.grid_density_atr_ratio
            optimal_spacing = atr_value * density_ratio
            recommended_grid_count = max(5, min(25, int(price_range / optimal_spacing)))

        # 5. 推荐阈值（成本敏感）
        recommended_threshold = None
        if config is not None:
            total_fee_rate = config.commission_rate * 2 + config.stamp_duty_rate  # 买卖各一次
            min_threshold = total_fee_rate * 8  # 8×总费率
            recommended_threshold = max(min_threshold, 0.02)  # 最低2%

        return cls(
            regime=regime,
            kelly_allocation=kelly_allocation,
            volatility_drag=vol_drag,
            recommended_grid_count=recommended_grid_count,
            recommended_threshold=recommended_threshold,
        )


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
                return TradeSignal(action="卖出", shares=0, reason="rebalance")
            else:
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


class KellyRebalanceStrategy(RebalanceStrategy):
    """凯利准则驱动的再平衡策略

    香农恶魔的核心：不是固定50%仓位，而是根据赔率动态调整。
    - 波动率高时自动减仓（凯利仓位低）
    - 波动率低时自动加仓（凯利仓位高）
    - 实际仓位 = kelly_criterion() × kelly_fraction（半凯利更安全）

    这是一个闭环：理论计算(kelly) → 信号(allocation) → 策略执行(rebalance)
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,  # 半凯利默认
        kelly_lookback: int = 30,
        rebalance_threshold: float = 0.05,
    ):
        self.kelly_fraction = kelly_fraction
        self.kelly_lookback = kelly_lookback
        self.rebalance_threshold = rebalance_threshold
        self.target_allocation = 0.5 * kelly_fraction  # 初始值（半凯利安全估计）
        # 追踪最近的卖出交易用于估算胜率/盈亏比
        self._recent_sell_results: list[tuple[float, float]] = []  # (sell_price, avg_price)

    def update_kelly_from_trades(self, trades: list) -> None:
        """从最近交易更新凯利参数

        在回测主循环中调用，传入最近kelly_lookback个交易。
        """
        sell_trades = [t for t in trades if t.action == "卖出"]
        recent = sell_trades[-self.kelly_lookback:] if len(sell_trades) > self.kelly_lookback else sell_trades

        if len(recent) >= 3:
            wins = sum(1 for t in recent if t.price > t.avg_price)
            win_rate = wins / len(recent)

            winning = [t for t in recent if t.price > t.avg_price]
            losing = [t for t in recent if t.price <= t.avg_price]

            avg_win = 0.05
            avg_loss = 0.03
            if winning:
                avg_win = sum((t.price - t.avg_price) / (t.avg_price if t.avg_price > 0 else t.price) for t in winning) / len(winning)
            if losing:
                avg_loss = sum((t.avg_price - t.price) / (t.avg_price if t.avg_price > 0 else t.price) for t in losing) / len(losing)

            kelly_raw = kelly_criterion(win_rate, avg_win, avg_loss)
            self.target_allocation = min(kelly_raw * self.kelly_fraction, 0.9)
        else:
            # 交易数据不足时，保持初始值
            self.target_allocation = 0.5 * self.kelly_fraction

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
                return TradeSignal(action="卖出", shares=0, reason="kelly_rebalance")
            else:
                return TradeSignal(action="买入", shares=0, reason="kelly_rebalance")
        return None


class RegimeAwareEngine:
    """市场状态自适应策略切换引擎

    香农恶魔不是万能药：震荡市用网格最好，趋势市用再平衡更稳。
    这个引擎在每个时间步判断市场状态，自动切换策略。

    这是真正的「理论驱动」：
    - get_market_regime() → 判断震荡/趋势
    - regime → 选择最优策略
    - strategy → 执行交易
    """

    def __init__(
        self,
        config: GridTradingConfig,
        grid_prices: list[float],
        lookback: int = 20,
    ):
        self.config = config
        self.lookback = lookback

        # 预创建所有策略实例
        self.grid_strategy = GridStrategy(grid_prices, config.shares_per_grid)
        self.rebalance_strategy = RebalanceStrategy(
            target_allocation=config.target_allocation,
            rebalance_threshold=config.rebalance_threshold,
        )
        self.kelly_strategy = KellyRebalanceStrategy(
            kelly_fraction=config.kelly_fraction,
            kelly_lookback=config.kelly_lookback,
            rebalance_threshold=config.rebalance_threshold,
        )

        # 当前激活策略
        self.active_strategy: StrategyEngine = self.rebalance_strategy  # 默认
        self.current_regime: str = "不确定"
        self.regime_history: list[str] = []

    def update_regime(self, price_series: pd.Series) -> str:
        """更新市场状态判断，并切换策略

        Args:
            price_series: 最近的价格序列（至少 lookback 长）

        Returns:
            当前市场状态
        """
        if len(price_series) < self.lookback:
            self.current_regime = "不确定"
            return self.current_regime

        recent = price_series.iloc[-self.lookback:]  if len(price_series) > self.lookback else price_series
        regime = get_market_regime(recent)
        self.current_regime = regime
        self.regime_history.append(regime)

        # 根据市场状态切换策略
        if regime == "震荡":
            self.active_strategy = self.grid_strategy
        elif regime in ("上涨", "下跌"):
            if self.config.use_kelly_sizing:
                self.active_strategy = self.kelly_strategy
            else:
                self.active_strategy = self.rebalance_strategy
        else:  # 不确定
            # 保守模式：低比例再平衡
            self.rebalance_strategy.target_allocation = 0.3  # 保守30%
            self.active_strategy = self.rebalance_strategy

        return regime

    def should_trade(
        self,
        price: float,
        shares: int,
        cash: float,
        avg_price: float,
        position_ratio: float,
        config: GridTradingConfig,
    ) -> Optional[TradeSignal]:
        """委托给当前激活策略"""
        return self.active_strategy.should_trade(
            price, shares, cash, avg_price, position_ratio, config
        )

    def calculate_trade_size(
        self,
        price: float,
        signal: TradeSignal,
        cash: float,
        shares: int,
        config: GridTradingConfig,
    ) -> int:
        """委托给当前激活策略"""
        return self.active_strategy.calculate_trade_size(
            price, signal, cash, shares, config
        )

    def get_regime_summary(self) -> dict:
        """获取市场状态切换统计"""
        if not self.regime_history:
            return {"震荡": 0, "上涨": 0, "下跌": 0, "不确定": 0, "switches": 0}
        counts = {"震荡": 0, "上涨": 0, "下跌": 0, "不确定": 0}
        for r in self.regime_history:
            counts[r] = counts.get(r, 0) + 1
        switches = sum(1 for i in range(1, len(self.regime_history)) if self.regime_history[i] != self.regime_history[i-1])
        counts["switches"] = switches
        return counts


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
        if config.use_kelly_sizing:
            return KellyRebalanceStrategy(
                kelly_fraction=config.kelly_fraction,
                kelly_lookback=config.kelly_lookback,
                rebalance_threshold=config.rebalance_threshold,
            )
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
        return RebalanceStrategy(
            target_allocation=config.target_allocation,
            rebalance_threshold=config.rebalance_threshold,
        )
    else:
        raise ValueError(f"未知策略模式: {config.strategy_mode}")


__all__ = [
    "StrategyEngine",
    "TradeSignal",
    "TheorySignal",
    "GridStrategy",
    "RebalanceStrategy",
    "KellyRebalanceStrategy",
    "RegimeAwareEngine",
    "create_strategy",
]