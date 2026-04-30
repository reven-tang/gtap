"""
数据源抽象层 - GTAP 网格交易回测平台

提供统一的数据获取接口，支持 baostock、yfinance、akshare 等多种数据源。
"""

from .base import DataProvider
from .factory import get_provider, available_providers
from .baostock_provider import BaoStockProvider

# 可选数据源（import 失败不影响核心功能）
try:
    from .yfinance_provider import YFinanceProvider
except ImportError:
    YFinanceProvider = None  # yfinance 未安装

try:
    from .akshare_provider import AkShareProvider
except ImportError:
    AkShareProvider = None  # akshare 未安装

__all__ = [
    "DataProvider",
    "get_provider",
    "BaoStockProvider",
    "YFinanceProvider",
    "AkShareProvider",
]