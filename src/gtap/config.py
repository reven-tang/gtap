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
    stock_code: str = "sh.600958"

    # 日期范围
    start_date: str = "2022-01-01"
    end_date: str = "2024-12-31"

    # 网格参数
    grid_upper: float = 12.0  # 默认值仅作占位，auto_grid_range=True 时自动覆盖
    grid_lower: float = 8.0   # 默认值仅作占位，auto_grid_range=True 时自动覆盖
    grid_number: int = 10
    grid_center: Optional[float] = None  # None = 自动（起始日收盘价）
    shares_per_grid: int = 100
    initial_shares: int = 100
    total_investment: float = 200000.0

    # 网格范围自动计算（P0-3）—— 默认开启，基于 ATR 自动适配
    auto_grid_range: bool = True  # 香农策略核心：网格范围应跟随数据波动
    grid_range_atr_multiplier: float = 2.0  # ATR × 此倍数 = 网格偏移量

    # 策略模式（P1-4）—— 香农再平衡是核心策略，默认启用
    strategy_mode: Literal["grid", "rebalance_threshold", "rebalance_periodic"] = "rebalance_threshold"
    target_allocation: float = 0.5  # 目标股票配置比例（再平衡模式核心参数）
    rebalance_threshold: float = 0.05  # 偏离目标比例多少时触发再平衡

    # 仓位管理模式（P1-5）—— 再平衡模式下 proportional 更合理
    position_mode: Literal["fixed_shares", "fixed_amount", "proportional"] = "proportional"
    amount_per_grid: float = 1000.0  # fixed_amount 模式下每格交易金额

    # 网格间距模式（P1-6）—— 香农策略更适合等比网格
    grid_spacing_mode: Literal["arithmetic", "geometric"] = "geometric"

    # 交易费用（A股标准）
    commission_rate: float = 0.0003      # 佣金费率（默认 0.03%，最低 5 元）
    transfer_fee_rate: float = 0.00001  # 过户费（沪市 0.001%）
    stamp_duty_rate: float = 0.001      # 印花税（卖出 0.1%）

    # 数据源选项
    data_source: Literal["baostock", "yfinance", "akshare"] = "baostock"  # 数据源
    frequency: Literal["5", "15", "30", "60", "d", "w", "m"] = "d"  # K线频率 — 默认日线，香农策略适用日频数据
    adjustflag: Literal["1", "2", "3"] = "3"  # 复权类型 1:前复权 2:后复权 3:不复权
    show_quarterly_data: bool = False  # 是否显示季频财务数据

    # ATR 动态止损止盈
    use_atr_stop: bool = False             # 是否启用 ATR 止损止盈
    atr_period: int = 14                   # ATR 计算周期
    atr_stop_multiplier: float = 1.5       # 止损乘数 (sl_atr = atr * multiplier)
    atr_tp_multiplier: float = 0.5         # 止盈乘数 (tp_atr = atr * multiplier)

    # 凯利准则动态仓位（v1.1.0 P0）—— 香农恶魔核心：仓位跟随赔率动态调整
    use_kelly_sizing: bool = False          # 是否启用凯利准则动态调整 target_allocation
    kelly_fraction: float = 0.5            # 凯利分数（半凯利默认，安全系数）
    kelly_lookback: int = 30               # 凯利参数回看窗口（交易日）

    # 市场状态自适应策略（v1.1.0 P0）—— 震荡用网格，趋势用再平衡
    use_regime_adaptive: bool = False      # 是否启用市场状态自适应策略切换
    regime_lookback: int = 20              # 市场状态判断回看窗口

    # 波动率自适应网格密度（v1.1.0 P1）—— 网格数量跟随波动率自动调整
    auto_grid_density: bool = False        # 是否启用波动率自适应网格密度
    grid_density_atr_ratio: float = 0.7    # 每格间距 = ATR × 此比例
    grid_density_min: int = 5              # 自适应网格数下限
    grid_density_max: int = 25             # 自适应网格数上限

    def __post_init__(self):
        """参数验证"""
        self._validate()

    def _validate(self) -> None:
        """验证配置参数的有效性"""
        # auto_grid_range=True 时，grid_upper/lower 只是占位值，跳过范围验证
        if not self.auto_grid_range and self.grid_upper <= self.grid_lower:
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

        # 凯利准则参数验证
        if self.kelly_fraction <= 0 or self.kelly_fraction > 1:
            raise ConfigError("凯利分数必须在 0-1 之间（推荐0.5=半凯利）")
        if self.kelly_lookback < 5:
            raise ConfigError("凯利回看窗口必须 ≥ 5")

        # 市场状态参数验证
        if self.regime_lookback < 10:
            raise ConfigError("市场状态回看窗口必须 ≥ 10")

        # 网格密度参数验证
        if self.grid_density_atr_ratio <= 0:
            raise ConfigError("网格密度ATR比例必须 > 0")
        if self.grid_density_min < 2:
            raise ConfigError("网格数下限必须 ≥ 2")
        if self.grid_density_max < self.grid_density_min:
            raise ConfigError("网格数上限必须 ≥ 下限")

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
            "use_kelly_sizing": self.use_kelly_sizing,
            "kelly_fraction": self.kelly_fraction,
            "kelly_lookback": self.kelly_lookback,
            "use_regime_adaptive": self.use_regime_adaptive,
            "regime_lookback": self.regime_lookback,
            "auto_grid_density": self.auto_grid_density,
            "grid_density_atr_ratio": self.grid_density_atr_ratio,
            "grid_density_min": self.grid_density_min,
            "grid_density_max": self.grid_density_max,
        }


# 默认配置实例
DEFAULT_CONFIG = GridTradingConfig()
