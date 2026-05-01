"""
BaoStock 数据源提供商 - GTAP 网格交易回测平台

将现有 baostock 数据获取逻辑封装为 DataProvider 接口实现。
"""

import baostock as bs
import numpy as np
import pandas as pd
from typing import List

from .base import DataProvider
from ..exceptions import DataFetchError


class BaoStockProvider(DataProvider):
    """BaoStock 数据源提供商。

    支持 A 股沪市和深市数据获取。BaoStock 是免费的 A 股数据源，
    提供日线/分钟线 K 线数据、除权除息、基本资料和季频财务数据。

    Attributes:
        name: "baostock"
    """

    name = "baostock"

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
            code: BaoStock 格式代码，如 "sh.601398"
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            frequency: "5"/"15"/"30"/"60"/"d"/"w"/"m"
            adjustflag: "1"前复权/"2"后复权/"3"不复权

        Returns:
            DataFrame with columns: open, high, low, close, volume, datetime index

        Raises:
            DataFetchError: 数据获取失败
        """
        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise DataFetchError(f"baostock 登录失败: {lg.error_msg}", code=lg.error_code)

            # 日线/周线/月线不包含 time 字段（只有分钟线才有）
            is_intraday = frequency in ("5", "15", "30", "60")
            fields = "date,time,code,open,high,low,close,volume" if is_intraday \
                else "date,code,open,high,low,close,volume"

            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag,
            )
            kline_list = []
            while rs.error_code == "0" and rs.next():
                kline_list.append(rs.get_row_data())

            kline_df = pd.DataFrame(kline_list, columns=rs.fields)

            # 数据清洗
            if not kline_df.empty:
                if is_intraday:
                    # 分钟线: 拼接 date + time
                    time_series = kline_df["time"].fillna("").astype(str)
                    is_date_fmt = time_series.str.match(r"^\d+$")
                    kline_df["datetime"] = np.where(
                        is_date_fmt,
                        kline_df["date"].astype(str),
                        kline_df["date"].astype(str) + " " + time_series.str[:8],
                    )
                else:
                    # 日线/周线/月线: 只用 date
                    kline_df["datetime"] = kline_df["date"].astype(str)
                kline_df["datetime"] = pd.to_datetime(kline_df["datetime"], format="mixed")
                kline_df = kline_df.set_index("datetime")

                numeric_cols = ["open", "high", "low", "close", "volume"]
                kline_df[numeric_cols] = kline_df[numeric_cols].astype(float)

            bs.logout()
            return kline_df

        except DataFetchError:
            raise
        except Exception as e:
            try:
                bs.logout()
            except Exception:
                pass
            raise DataFetchError(f"BaoStock K线数据获取失败: {e}", original_error=e)

    def fetch_dividend(self, code: str) -> pd.DataFrame:
        """获取除权除息数据。"""
        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise DataFetchError(f"baostock 登录失败: {lg.error_msg}")

            rs = bs.query_dividend_data(code=code, year="", yearType="report")
            dividend_list = []
            while rs.error_code == "0" and rs.next():
                dividend_list.append(rs.get_row_data())

            bs.logout()
            return pd.DataFrame(dividend_list, columns=rs.fields)

        except DataFetchError:
            raise
        except Exception as e:
            try:
                bs.logout()
            except Exception:
                pass
            raise DataFetchError(f"除权除息数据获取失败: {e}", original_error=e)

    def fetch_basic(self, code: str) -> pd.DataFrame:
        """获取证券基本资料。"""
        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise DataFetchError(f"baostock 登录失败: {lg.error_msg}")

            rs = bs.query_stock_basic(code=code)
            basic_list = []
            while rs.error_code == "0" and rs.next():
                basic_list.append(rs.get_row_data())

            bs.logout()
            return pd.DataFrame(basic_list, columns=rs.fields)

        except DataFetchError:
            raise
        except Exception as e:
            try:
                bs.logout()
            except Exception:
                pass
            raise DataFetchError(f"基本资料获取失败: {e}", original_error=e)

    def supported_markets(self) -> List[str]:
        """返回支持的市场列表。"""
        return ["A股-沪市", "A股-深市"]

    def normalize_code(self, code: str) -> str:
        """将代码标准化为 BaoStock 格式。

        BaoStock 使用 "sh." 前缀表示沪市，"sz." 前缀表示深市。

        Args:
            code: 用户输入代码，如 "601398", "sh.601398", "000001"

        Returns:
            "sh.601398" 或 "sz.000001" 格式
        """
        # 已经是 BaoStock 格式
        if code.startswith("sh.") or code.startswith("sz."):
            return code

        # 纯数字代码：6开头=沪市，0/3开头=深市
        if code.isdigit():
            if code[0] in ("6", "9"):
                return f"sh.{code}"
            elif code[0] in ("0", "3"):
                return f"sz.{code}"

        # yfinance 格式转换
        if code.endswith(".SS"):
            return f"sh.{code[:-3]}"
        if code.endswith(".SZ"):
            return f"sz.{code[:-3]}"

        # 无法识别，原样返回
        return code

    def _supported_frequencies(self) -> List[str]:
        """BaoStock 支持的 K 线频率。"""
        return ["5", "15", "30", "60", "d", "w", "m"]