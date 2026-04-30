"""
AkShare 数据源提供商 - GTAP 网格交易回测平台

提供更丰富的 A 股数据（基金、期货、债券等）。
需要安装: pip install akshare>=1.12.0
"""

import pandas as pd
from typing import List

from .base import DataProvider
from ..exceptions import DataFetchError

try:
    import akshare as ak
    _AKSHARE_AVAILABLE = True
except ImportError:
    _AKSHARE_AVAILABLE = False


# 频率映射：GTAP 格式 → akshare 格式
_FREQUENCY_MAP = {
    "5": "5",
    "15": "15",
    "30": "30",
    "60": "60",
    "d": "daily",
    "w": "weekly",
    "m": "monthly",
}

# 复权映射
_ADJUSTFLAG_MAP = {
    "1": "hfq",    # 前复权
    "2": "bfq",    # 后复权（akshare 称"不复权"，但实际是后复权）
    "3": "",       # 不复权
}


class AkShareProvider(DataProvider):
    """AkShare 数据源提供商。

    提供更丰富的 A 股数据，包括基金、期货、债券等。
    AkShare 是免费的金融数据接口，数据来源丰富但稳定性不如 baostock。

    Attributes:
        name: "akshare"
    """

    name = "akshare"

    def __init__(self):
        """初始化 AkShare 提供商。

        Raises:
            DataFetchError: akshare 未安装
        """
        if not _AKSHARE_AVAILABLE:
            raise DataFetchError(
                "akshare 未安装。请执行: pip install akshare>=1.12.0",
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
            code: akshare 格式代码，如 "601398"（不带 sh/sz 前缀）
            start_date: 开始日期 YYYYMMDD 或 YYYY-MM-DD
            end_date: 结束日期 YYYYMMDD 或 YYYY-MM-DD
            frequency: "5"/"15"/"30"/"60"/"d"/"w"/"m"
            adjustflag: "1"前复权/"2"后复权/"3"不复权

        Returns:
            DataFrame with columns: open, high, low, close, volume, datetime index
        """
        try:
            # 移除日期中的分隔符（akshare 需要 YYYYMMDD 格式）
            start_clean = start_date.replace("-", "")
            end_clean = end_date.replace("-", "")

            ak_freq = _FREQUENCY_MAP.get(frequency, "daily")
            ak_adjust = _ADJUSTFLAG_MAP.get(adjustflag, "")

            if frequency in ("5", "15", "30", "60"):
                # 分钟级数据
                data = ak.stock_zh_a_hist_min_em(
                    symbol=code,
                    period=ak_freq,
                    start_date=start_clean,
                    end_date=end_clean,
                    adjust=ak_adjust,
                )
            else:
                # 日线/周线/月线
                data = ak.stock_zh_a_hist(
                    symbol=code,
                    period=ak_freq,
                    start_date=start_clean,
                    end_date=end_clean,
                    adjust=ak_adjust,
                )

            if data is None or data.empty:
                raise DataFetchError(
                    f"akshare 未返回数据: {code} ({start_date} ~ {end_date}, {frequency})",
                    code="NO_DATA",
                )

            # 标准化列名（akshare 返回中文列名）
            column_map = {
                "日期": "datetime",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "时间": "datetime",
            }

            result = data.rename(columns=column_map)

            # 设置 datetime 索引
            if "datetime" in result.columns:
                result["datetime"] = pd.to_datetime(result["datetime"], format="mixed")
                result = result.set_index("datetime")

            # 只保留需要的列
            cols = ["open", "high", "low", "close", "volume"]
            available_cols = [c for c in cols if c in result.columns]
            result = result[available_cols]

            # 数值类型转换
            for col in available_cols:
                result[col] = pd.to_numeric(result[col], errors="coerce")

            return result

        except DataFetchError:
            raise
        except Exception as e:
            raise DataFetchError(f"akshare K线数据获取失败: {e}", original_error=e)

    def fetch_dividend(self, code: str) -> pd.DataFrame:
        """获取除权除息数据。

        akshare 通过 stock_dividend_df 获取分红数据。
        """
        try:
            data = ak.stock_dividend_df(symbol=code)
            if data is not None and not data.empty:
                return data
            return pd.DataFrame()
        except Exception as e:
            raise DataFetchError(f"akshare 除权除息数据获取失败: {e}", original_error=e)

    def fetch_basic(self, code: str) -> pd.DataFrame:
        """获取证券基本资料。

        akshare 通过 stock_individual_info_em 获取基本信息。
        """
        try:
            data = ak.stock_individual_info_em(symbol=code)
            if data is not None and not data.empty:
                return data
            return pd.DataFrame()
        except Exception as e:
            raise DataFetchError(f"akshare 基本资料获取失败: {e}", original_error=e)

    def supported_markets(self) -> List[str]:
        """返回支持的市场列表。"""
        return ["A股-沪市", "A股-深市", "基金", "期货", "债券", "指数"]

    def normalize_code(self, code: str) -> str:
        """将代码标准化为 akshare 格式。

        akshare 使用纯数字代码（不带 sh/sz 前缀）。

        Args:
            code: 用户输入代码，如 "sh.601398", "601398"

        Returns:
            纯数字代码，如 "601398"
        """
        # BaoStock 格式转换：去掉前缀
        if code.startswith("sh.") or code.startswith("sz."):
            return code[3:]

        # yfinance 格式转换：去掉后缀
        if code.endswith(".SS") or code.endswith(".SZ"):
            return code[:-3]

        # 已经是纯数字
        if code.isdigit():
            return code

        return code

    def _supported_frequencies(self) -> List[str]:
        """akshare 支持的 K 线频率。"""
        return ["5", "15", "30", "60", "d", "w", "m"]