"""
数据获取模块 - GTAP 网格交易回测平台

封装多数据源获取逻辑，支持 baostock、yfinance、akshare。
通过 DataProvider 抽象层实现数据源切换。
"""

from typing import NamedTuple, Optional
import pandas as pd
from .exceptions import DataFetchError
from .providers.factory import get_provider


class StockData(NamedTuple):
    """股票数据结构"""
    kline: pd.DataFrame           # K线数据（索引为 datetime）
    dividend: pd.DataFrame        # 除权除息
    stock_basic: pd.DataFrame     # 基本资料
    profit: pd.DataFrame          # 盈利能力
    operation: pd.DataFrame       # 营运能力
    growth: pd.DataFrame          # 成长能力
    balance: pd.DataFrame         # 偿债能力
    cash_flow: pd.DataFrame       # 现金流量
    dupont: pd.DataFrame          # 杜邦指数
    performance_express: pd.DataFrame  # 业绩快报
    forecast: pd.DataFrame        # 业绩预告


def get_stock_data(
    code: str,
    start_date: str,
    end_date: str,
    frequency: str = "5",
    adjustflag: str = "3",
    show_quarterly: bool = False,
    data_source: str = "baostock",
) -> StockData:
    """
    获取股票数据（K线 + 财务数据）。

    通过 data_source 参数选择数据源，内部使用 DataProvider 抽象层。

    Args:
        code: 股票代码，格式因数据源而异
            - baostock: "sh.601398"
            - yfinance: "601398.SS" 或 "AAPL"
            - akshare: "601398"
        start_date: 开始日期，YYYY-MM-DD
        end_date: 结束日期，YYYY-MM-DD
        frequency: K线频率，"5"/"15"/"30"/"60"/"d"/"w"/"m"
        adjustflag: 复权类型，"1"=前复权 "2"=后复权 "3"=不复权
        show_quarterly: 是否获取季频财务数据（仅 baostock 支持）
        data_source: 数据源，"baostock"/"yfinance"/"akshare"

    Returns:
        StockData 命名元组，包含各类数据表

    Raises:
        DataFetchError: 数据获取失败
    """
    try:
        provider = get_provider(data_source)
        normalized_code = provider.normalize_code(code)

        # K线数据
        kline_df = provider.fetch_kline(
            code=normalized_code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )

        # 除权除息
        dividend_df = provider.fetch_dividend(normalized_code)

        # 基本资料
        stock_basic_df = provider.fetch_basic(normalized_code)

        # 季频财务数据（仅 baostock 支持）
        empty_df = pd.DataFrame()
        profit_df = empty_df
        operation_df = empty_df
        growth_df = empty_df
        balance_df = empty_df
        cash_flow_df = empty_df
        dupont_df = empty_df
        performance_express_df = empty_df
        forecast_df = empty_df

        if show_quarterly and data_source == "baostock":
            # 季频财务数据仅 baostock 支持
            import baostock as bs
            lg = bs.login()
            year = start_date[:4]

            def _fetch_baostock_table(query_fn, code, year, quarter="1"):
                rs = query_fn(code=code, year=year, quarter=quarter)
                rows = []
                while rs.error_code == "0" and rs.next():
                    rows.append(rs.get_row_data())
                return pd.DataFrame(rows, columns=rs.fields) if rows else pd.DataFrame()

            profit_df = _fetch_baostock_table(bs.query_profit_data, normalized_code, year)
            operation_df = _fetch_baostock_table(bs.query_operation_data, normalized_code, year)
            growth_df = _fetch_baostock_table(bs.query_growth_data, normalized_code, year)
            balance_df = _fetch_baostock_table(bs.query_balance_data, normalized_code, year)
            cash_flow_df = _fetch_baostock_table(bs.query_cash_flow_data, normalized_code, year)
            dupont_df = _fetch_baostock_table(bs.query_dupont_data, normalized_code, year)

            rs_perf = bs.query_performance_express_report(
                code=normalized_code, start_date=start_date, end_date=end_date
            )
            perf_rows = []
            while rs_perf.error_code == "0" and rs_perf.next():
                perf_rows.append(rs_perf.get_row_data())
            performance_express_df = pd.DataFrame(
                perf_rows, columns=rs_perf.fields
            ) if perf_rows else pd.DataFrame()

            rs_forecast = bs.query_forecast_report(
                code=normalized_code, start_date=start_date, end_date=end_date
            )
            forecast_rows = []
            while rs_forecast.error_code == "0" and rs_forecast.next():
                forecast_rows.append(rs_forecast.get_row_data())
            forecast_df = pd.DataFrame(
                forecast_rows, columns=rs_forecast.fields
            ) if forecast_rows else pd.DataFrame()

            bs.logout()

        elif show_quarterly and data_source != "baostock":
            # 非 baostock 数据源暂不支持季频财务数据
            pass

        return StockData(
            kline=kline_df,
            dividend=dividend_df,
            stock_basic=stock_basic_df,
            profit=profit_df,
            operation=operation_df,
            growth=growth_df,
            balance=balance_df,
            cash_flow=cash_flow_df,
            dupont=dupont_df,
            performance_express=performance_express_df,
            forecast=forecast_df,
        )

    except DataFetchError:
        raise
    except Exception as e:
        raise DataFetchError(f"数据获取失败: {e}", original_error=e)