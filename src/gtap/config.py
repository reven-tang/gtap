"""
配置模块 - GTAP 网格交易回测平台

提供配置类、默认参数和参数验证功能。
"""

from dataclasses import dataclass
from typing import Literal, Optional

from .exceptions import ConfigError


@dataclass
class GridTradingConfig:
    """网格交易配置参数"""

    # 股票代码
    stock_code: str = "sh.601398"

    # 日期范围
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"

    # 网格参数
    grid_upper: float = 6.0
    grid_lower: float = 4.0
    grid_number: int = 10
    grid_center: Optional[float] = None  # None = 自动（起始日收盘价）
    shares_per_grid: int = 100
    initial_shares: int = 100
    total_investment: float = 10000.0

    # 网格范围自动计算（P0-3）
    auto_grid_range: bool = False  # 是否基于 ATR 自动计算网格范围
    grid_range_atr_multiplier: float = 2.0  # ATR × 此倍数 = 网格偏移量

    # 策略模式（P1-4）
    strategy_mode: Literal["grid", "rebalance_threshold", "rebalance_periodic"] = "grid"
    target_allocation: float = 0.5  # 目标股票配置比例（再平衡模式核心参数）
    rebalance_threshold: float = 0.05  # 偏离目标比例多少时触发再平衡

    # 仓位管理模式（P1-5）
    position_mode: Literal["fixed_shares", "fixed_amount", "proportional"] = "fixed_shares"
    amount_per_grid: float = 1000.0  # fixed_amount 模式下每格交易金额

    # 网格间距模式（P1-6）
    grid_spacing_mode: Literal["arithmetic", "geometric"] = "arithmetic"

    # 交易费用（A股标准）
    commission_rate: float = 0.0003      # 佣金费率（默认 0.03%，最低 5 元）
    transfer_fee_rate: float = 0.00001  # 过户费（沪市 0.001%）
    stamp_duty_rate: float = 0.001      # 印花税（卖出 0.1%）

    # 数据源选项
    data_source: Literal["baostock", "yfinance", "akshare"] = "baostock"  # 数据源
    frequency: Literal["5", "15", "30", "60", "d", "w", "m"] = "5"  # K线频率
    adjustflag: Literal["1", "2", "3"] = "3"  # 复权类型 1:前复权 2:后复权 3:不复权
    show_quarterly_data: bool = False  # 是否显示季频财务数据

    # ATR 动态止损止盈
    use_atr_stop: bool = False             # 是否启用 ATR 止损止盈
    atr_period: int = 14                   # ATR 计算周期
    atr_stop_multiplier: float = 1.5       # 止损乘数 (sl_atr = atr * multiplier)
    atr_tp_multiplier: float = 0.5         # 止盈乘数 (tp_atr = atr * multiplier)

    def __post_init__(self):
        """参数验证"""
        self._validate()

    def _validate(self) -> None:
        """验证配置参数的有效性"""
        if self.grid_upper <= self.grid_lower:
            raise ConfigError("网格上限必须大于网格下限")

        if self.grid_number < 2:
            raise ConfigError("网格数量必须 ≥ 2")

        # grid_center=None 表示自动模式，不验证范围
        # 只有手动设定时才验证
        if self.grid_center is not None and not (self.grid_lower <= self.grid_center <= self.grid_upper):
            raise ConfigError("网格中心必须在上下限之间")

        if self.initial_shares < 0:
            raise ConfigError("初始持仓股数不能为负")

        if self.commission_rate < 0:
            raise ConfigError("佣金费率不能为负")

        if self.transfer_fee_rate < 0:
            raise ConfigError("过户费费率不能为负")

        if self.stamp_duty_rate < 0:
            raise ConfigError("印花税费率不能为负")

        if self.grid_range_atr_multiplier <= 0:
            raise ConfigError("网格范围 ATR 乘数必须 > 0")

        if self.total_investment <= 0:
            raise ConfigError("投入总资金必须 > 0")

        # P1 再平衡参数验证
        if self.target_allocation < 0 or self.target_allocation > 1:
            raise ConfigError("目标配置比例必须在 0-1 之间")
        if self.rebalance_threshold < 0 or self.rebalance_threshold > 1:
            raise ConfigError("再平衡阈值必须在 0-1 之间")
        if self.amount_per_grid <= 0:
            raise ConfigError("每格交易金额必须 > 0")

        # ATR 参数验证
        if self.atr_period < 2:
            raise ConfigError("ATR 周期必须 ≥ 2")
        if self.atr_stop_multiplier <= 0:
            raise ConfigError("ATR 止损乘数必须 > 0")
        if self.atr_tp_multiplier < 0:
            raise ConfigError("ATR 止盈乘数必须 ≥ 0")

        # 策略与模式验证
        if self.strategy_mode not in ("grid", "rebalance_threshold", "rebalance_periodic"):
            raise ConfigError(f"未知策略模式: {self.strategy_mode}")
        if self.position_mode not in ("fixed_shares", "fixed_amount", "proportional"):
            raise ConfigError(f"未知仓位模式: {self.position_mode}")
        if self.grid_spacing_mode not in ("arithmetic", "geometric"):
            raise ConfigError(f"未知网格间距模式: {self.grid_spacing_mode}")

    @property
    def grid_step(self) -> float:
        """计算网格间距"""
        return (self.grid_upper - self.grid_lower) / (self.grid_number - 1)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "stock_code": self.stock_code,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "grid_upper": self.grid_upper,
            "grid_lower": self.grid_lower,
            "grid_number": self.grid_number,
            "grid_center": self.grid_center,
            "shares_per_grid": self.shares_per_grid,
            "initial_shares": self.initial_shares,
            "total_investment": self.total_investment,
            "commission_rate": self.commission_rate,
            "transfer_fee_rate": self.transfer_fee_rate,
            "stamp_duty_rate": self.stamp_duty_rate,
            "data_source": self.data_source,
            "frequency": self.frequency,
            "adjustflag": self.adjustflag,
            "show_quarterly_data": self.show_quarterly_data,
            "auto_grid_range": self.auto_grid_range,
            "grid_range_atr_multiplier": self.grid_range_atr_multiplier,
            "grid_spacing_mode": self.grid_spacing_mode,
            "strategy_mode": self.strategy_mode,
            "target_allocation": self.target_allocation,
            "rebalance_threshold": self.rebalance_threshold,
            "position_mode": self.position_mode,
            "amount_per_grid": self.amount_per_grid,
            "use_atr_stop": self.use_atr_stop,
            "atr_period": self.atr_period,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "atr_tp_multiplier": self.atr_tp_multiplier,
        }


# 默认配置实例
DEFAULT_CONFIG = GridTradingConfig()
