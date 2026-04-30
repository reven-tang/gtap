"""
数据源工厂 - GTAP 网格交易回测平台

根据数据源名称创建对应的数据提供商实例。
"""

from .base import DataProvider
from .baostock_provider import BaoStockProvider
from ..exceptions import DataFetchError

# 可选数据源
_YFinanceProvider = None
_AkShareProvider = None

try:
    from .yfinance_provider import YFinanceProvider
    _YFinanceProvider = YFinanceProvider
except ImportError:
    pass

try:
    from .akshare_provider import AkShareProvider
    _AkShareProvider = AkShareProvider
except ImportError:
    pass


# 已注册的数据源映射
_PROVIDER_MAP = {
    "baostock": BaoStockProvider,
}

if _YFinanceProvider is not None:
    _PROVIDER_MAP["yfinance"] = _YFinanceProvider

if _AkShareProvider is not None:
    _PROVIDER_MAP["akshare"] = _AkShareProvider


def get_provider(source: str = "baostock") -> DataProvider:
    """根据数据源名称创建数据提供商实例。

    Args:
        source: 数据源名称，支持 "baostock", "yfinance", "akshare"

    Returns:
        DataProvider 实例

    Raises:
        DataFetchError: 不支持的数据源，或可选依赖未安装

    Examples:
        >>> provider = get_provider("baostock")
        >>> provider = get_provider("yfinance")  # 需要 yfinance 已安装
    """
    if source not in _PROVIDER_MAP:
        available = list(_PROVIDER_MAP.keys())
        if source == "yfinance":
            raise DataFetchError(
                "yfinance 数据源不可用。请安装: pip install yfinance>=0.2.31",
                code="PROVIDER_NOT_INSTALLED",
            )
        elif source == "akshare":
            raise DataFetchError(
                "akshare 数据源不可用。请安装: pip install akshare>=1.12.0",
                code="PROVIDER_NOT_INSTALLED",
            )
        else:
            raise DataFetchError(
                f"不支持的数据源: {source}。可用数据源: {available}",
                code="PROVIDER_NOT_SUPPORTED",
            )

    return _PROVIDER_MAP[source]()


def available_providers() -> list:
    """返回当前可用数据源列表。

    Returns:
        可用数据源名称列表
    """
    return list(_PROVIDER_MAP.keys())