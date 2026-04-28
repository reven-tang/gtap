"""
GTAP 网格交易回测平台 - 包入口

导出公共 API：
- config: GridTradingConfig, DEFAULT_CONFIG
- data: get_stock_data, StockData
- fees: calculate_fees
- grid: grid_trading, GridTradingResult, Trade
- metrics: calculate_metrics, calculate_trade_metrics, PerformanceMetrics
- plot: plot_kline, plot_asset_curve, plot_grid_lines, plot_mplfinance
- exceptions: DataFetchError, GridTradingError, ConfigError, MetricsError, PlotError
"""

from .config import GridTradingConfig, DEFAULT_CONFIG
from .data import get_stock_data, StockData
from .fees import calculate_fees
from .grid import grid_trading, GridTradingResult, Trade
from .metrics import calculate_metrics, calculate_trade_metrics, PerformanceMetrics
from .plot import (
    plot_kline,
    plot_asset_curve,
    plot_grid_lines,
    plot_mplfinance,
)
from .exceptions import (
    DataFetchError,
    GridTradingError,
    ConfigError,
    MetricsError,
    PlotError,
)

__all__ = [
    # config
    "GridTradingConfig",
    "DEFAULT_CONFIG",
    # data
    "get_stock_data",
    "StockData",
    # fees
    "calculate_fees",
    # grid
    "grid_trading",
    "GridTradingResult",
    "Trade",
    # metrics
    "calculate_metrics",
    "calculate_trade_metrics",
    "PerformanceMetrics",
    # plot
    "plot_kline",
    "plot_asset_curve",
    "plot_grid_lines",
    "plot_mplfinance",
    # exceptions
    "DataFetchError",
    "GridTradingError",
    "ConfigError",
    "MetricsError",
    "PlotError",
]
