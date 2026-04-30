"""
配置模块 - GTAP 网格交易回测平台

提供配置类、默认参数和参数验证功能。
"""

from dataclasses import dataclass, field
from typing import Literal

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
    grid_center: float = 5.0
    shares_per_grid: int = 100
    initial_shares: int = 100
    current_holding_price: float = 5.0
    total_investment: float = 10000.0

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

        if not (self.grid_lower <= self.grid_center <= self.grid_upper):
            raise ConfigError("网格中心必须在上下限之间")

        if self.initial_shares < 0:
            raise ConfigError("初始持仓股数不能为负")

        if self.commission_rate < 0:
            raise ConfigError("佣金费率不能为负")

        if self.transfer_fee_rate < 0:
            raise ConfigError("过户费费率不能为负")

        if self.stamp_duty_rate < 0:
            raise ConfigError("印花税费率不能为负")

        # ATR 参数验证
        if self.atr_period < 2:
            raise ConfigError("ATR 周期必须 ≥ 2")
        if self.atr_stop_multiplier <= 0:
            raise ConfigError("ATR 止损乘数必须 > 0")
        if self.atr_tp_multiplier < 0:
            raise ConfigError("ATR 止盈乘数必须 ≥ 0")

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
            "current_holding_price": self.current_holding_price,
            "total_investment": self.total_investment,
            "commission_rate": self.commission_rate,
            "transfer_fee_rate": self.transfer_fee_rate,
            "stamp_duty_rate": self.stamp_duty_rate,
            "data_source": self.data_source,
            "frequency": self.frequency,
            "adjustflag": self.adjustflag,
            "show_quarterly_data": self.show_quarterly_data,
            "use_atr_stop": self.use_atr_stop,
            "atr_period": self.atr_period,
            "atr_stop_multiplier": self.atr_stop_multiplier,
            "atr_tp_multiplier": self.atr_tp_multiplier,
        }


# 默认配置实例
DEFAULT_CONFIG = GridTradingConfig()
