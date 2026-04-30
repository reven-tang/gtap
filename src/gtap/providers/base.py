"""
数据源抽象基类 - GTAP 网格交易回测平台

所有数据源必须实现此接口，确保上层代码可以无缝切换数据源。
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import List


class DataProvider(ABC):
    """数据源抽象基类。

    所有数据源提供商必须实现此接口。上层代码通过 DataProvider 统一访问
    不同数据源，无需关心底层实现差异。

    Attributes:
        name: 数据源名称（如 "baostock", "yfinance", "akshare"）
    """

    name: str = "unknown"

    @abstractmethod
    def fetch_kline(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "3",
    ) -> pd.DataFrame:
        """获取 K 线数据。

        Args:
            code: 标准化后的股票代码
            start_date: 开始日期，YYYY-MM-DD 格式
            end_date: 结束日期，YYYY-MM-DD 格式
            frequency: K 线频率
                - 分钟: "5"/"15"/"30"/"60"
                - 日线: "d"
                - 周线: "w"
                - 月线: "m"
            adjustflag: 复权类型
                - "1": 前复权
                - "2": 后复权
                - "3": 不复权

        Returns:
            DataFrame，包含列：open, high, low, close, volume
            索引为 datetime 类型。

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def fetch_dividend(self, code: str) -> pd.DataFrame:
        """获取除权除息数据。

        Args:
            code: 标准化后的股票代码

        Returns:
            DataFrame，包含除权除息信息。

        Raises:
            DataFetchError: 数据获取失败或不支持
        """
        pass

    @abstractmethod
    def fetch_basic(self, code: str) -> pd.DataFrame:
        """获取证券基本资料。

        Args:
            code: 标准化后的股票代码

        Returns:
            DataFrame，包含证券基本信息。

        Raises:
            DataFetchError: 数据获取失败或不支持
        """
        pass

    @abstractmethod
    def supported_markets(self) -> List[str]:
        """返回支持的市场列表。

        Returns:
            市场代码列表，如 ["A股-沪", "A股-深", "港股", "美股"]
        """
        pass

    @abstractmethod
    def normalize_code(self, code: str) -> str:
        """将用户输入代码标准化为该数据源格式。

        Args:
            code: 用户输入的股票代码，如 "sh.601398", "AAPL", "0700.HK"

        Returns:
            标准化后的代码，适合该数据源 API 调用。

        Examples:
            BaoStockProvider: "601398" → "sh.601398"
            YFinanceProvider: "sh.601398" → "601398.SS"
            AkShareProvider: "sh.601398" → "601398"
        """
        pass

    def supports_frequency(self, frequency: str) -> bool:
        """检查是否支持指定 K 线频率。

        Args:
            frequency: K 线频率代码

        Returns:
            True 表示支持，False 表示不支持
        """
        return frequency in self._supported_frequencies()

    @abstractmethod
    def _supported_frequencies(self) -> List[str]:
        """返回支持的 K 线频率列表。"""
        pass