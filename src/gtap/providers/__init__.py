"""
数据源抽象层 - GTAP 网格交易回测平台

提供统一的数据获取接口，支持 baostock、yfinance、akshare 等多种数据源。
"""

from .base import DataProvider
from .factory import get_provider, available_providers
from .baostock_provider import BaoStockProvider

# 可选数据源（import 失败不影响核心功能）
try:
    from .yfinance_provider import YFinanceProvider  # type: ignore[assignment]
except ImportError:
    YFinanceProvider = None  # type: ignore[assignment,misc]  # yfinance 未安装

try:
    from .akshare_provider import AkShareProvider  # type: ignore[assignment]
except ImportError:
    AkShareProvider = None  # type: ignore[assignment,misc]  # akshare 未安装

__all__ = [
    "DataProvider",
    "get_provider",
    "available_providers",
    "BaoStockProvider",
    "YFinanceProvider",
    "AkShareProvider",
]