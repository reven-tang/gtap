"""
YFinance 数据源提供商 - GTAP 网格交易回测平台

支持港股、美股、外汇、加密货币数据获取。
需要安装: pip install yfinance>=0.2.31
"""

import pandas as pd
from typing import List, Optional

from .base import DataProvider
from ..exceptions import DataFetchError

try:
    import yfinance as yf
    _YFINANCE_AVAILABLE = True
except ImportError:
    _YFINANCE_AVAILABLE = False


# 频率映射：GTAP 格式 → yfinance 格式
_FREQUENCY_MAP = {
    "5": "5m",
    "15": "15m",
    "30": "30m",
    "60": "60m",
    "d": "1d",
    "w": "1wk",
    "m": "1mo",
}

# 复权映射
_ADJUSTFLAG_MAP = {
    "1": True,    # 前复权 → auto_adjust=True
    "2": "back_adjust",
    "3": False,   # 不复权 → auto_adjust=False
}


class YFinanceProvider(DataProvider):
    """YFinance 数据源提供商。

    支持港股、美股、外汇、加密货币。YFinance 通过 Yahoo Finance API
    获取数据，覆盖范围广但分钟级数据仅支持最近 7 天。

    Attributes:
        name: "yfinance"
    """

    name = "yfinance"

    def __init__(self):
        """初始化 YFinance 提供商。

        Raises:
            DataFetchError: yfinance 未安装
        """
        if not _YFINANCE_AVAILABLE:
            raise DataFetchError(
                "yfinance 未安装。请执行: pip install yfinance>=0.2.31",
                code="PROVIDER_NOT_INSTALLED",
            )

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
            code: yfinance 格式代码，如 "601398.SS", "AAPL", "0700.HK"
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            frequency: "5"/"15"/"30"/"60"/"d"/"w"/"m"
            adjustflag: "1"前复权/"2"后复权/"3"不复权

        Returns:
            DataFrame with columns: open, high, low, close, volume, datetime index

        Note:
            yfinance 分钟级数据仅支持最近 7 天。
        """
        try:
            yf_freq = _FREQUENCY_MAP.get(frequency, "1d")
            auto_adjust = _ADJUSTFLAG_MAP.get(adjustflag, False)

            ticker = yf.Ticker(code)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=yf_freq,
                auto_adjust=auto_adjust if isinstance(auto_adjust, bool) else False,
            )

            if data.empty:
                raise DataFetchError(
                    f"yfinance 未返回数据: {code} ({start_date} ~ {end_date}, {frequency})",
                    code="NO_DATA",
                )

            # 标准化列名
            result = data.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            })

            # 只保留需要的列
            cols = ["open", "high", "low", "close", "volume"]
            available_cols = [c for c in cols if c in result.columns]
            result = result[available_cols]

            # 后复权处理
            if adjustflag == "2":
                # yfinance 不直接支持后复权，需要手动调整
                pass  # 返回原始数据，由上层处理

            return result

        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"yfinance K线数据获取失败: {e}", original_error=e)

    def fetch_dividend(self, code: str) -> pd.DataFrame:
        """获取除权除息数据。

        yfinance 通过 dividends 属性获取分红数据。
        """
        try:
            ticker = yf.Ticker(code)
            dividends = ticker.dividends
            if dividends is not None and not dividends.empty:
                df = dividends.reset_index()
                df.columns = ["Date", "Dividends"]
                return df
            return pd.DataFrame()
        except Exception as e:
            raise DataFetchError(f"yfinance 除权除息数据获取失败: {e}", original_error=e)

    def fetch_basic(self, code: str) -> pd.DataFrame:
        """获取证券基本资料。

        yfinance 通过 info 属性获取基本信息。
        """
        try:
            ticker = yf.Ticker(code)
            info = ticker.info
            if info:
                # 转为单行 DataFrame
                return pd.DataFrame([info])
            return pd.DataFrame()
        except Exception as e:
            raise DataFetchError(f"yfinance 基本资料获取失败: {e}", original_error=e)

    def supported_markets(self) -> List[str]:
        """返回支持的市场列表。"""
        return ["A股-沪市", "A股-深市", "港股", "美股", "ETF", "外汇", "加密货币"]

    def normalize_code(self, code: str) -> str:
        """将代码标准化为 yfinance 格式。

        yfinance 使用 Yahoo Finance 代码格式：
        - 沪市: 601398.SS
        - 深市: 000001.SZ
        - 港股: 0700.HK
        - 美股: AAPL

        Args:
            code: 用户输入代码，如 "sh.601398", "601398", "AAPL"

        Returns:
            yfinance 格式代码
        """
        # BaoStock 格式转换
        if code.startswith("sh."):
            return f"{code[3:]}.SS"
        if code.startswith("sz."):
            return f"{code[3:]}.SZ"

        # 已经是 yfinance 格式
        if any(code.endswith(suffix) for suffix in [".SS", ".SZ", ".HK", ".US"]):
            return code

        # 纯数字代码（可能是中国 A 股）
        if code.isdigit():
            if code[0] in ("6", "9"):
                return f"{code}.SS"  # 沪市
            elif code[0] in ("0", "3"):
                return f"{code}.SZ"  # 深市
            return code

        # 非数字代码（可能是美股/港股代码）
        return code

    def _supported_frequencies(self) -> List[str]:
        """yfinance 支持的 K 线频率。

        Note: 分钟级数据仅支持最近 7 天。
        """
        return ["5", "15", "30", "60", "d", "w", "m"]