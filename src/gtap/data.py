"""
数据获取模块 - GTAP 网格交易回测平台

封装多数据源获取逻辑，支持 baostock、yfinance、akshare。
通过 DataProvider 抽象层实现数据源切换。
集成 DuckDB 本地仓库实现智能缓存。
"""

from typing import Optional, NamedTuple, Callable, List, Tuple
import logging
from datetime import date

import pandas as pd
from .exceptions import DataFetchError
from .providers.factory import get_provider
from .store import get_store, DataStore

logger = logging.getLogger(__name__)


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


def _smart_fetch_kline(
    code: str,
    normalized_code: str,
    start_date: str,
    end_date: str,
    frequency: str,
    adjustflag: str,
    data_source: str,
    store: DataStore,
    progress_callback: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    智能获取 K 线数据：优先本地仓库，缺失部分远程拉取。
    仅对日线数据做本地缓存（分钟级数据量太大，不值得缓存）。
    """
    # 分钟数据不做本地缓存（数据量太大）
    freq_is_intraday = frequency not in ("d", "w", "m", "")

    if freq_is_intraday:
        # 分钟数据直接从 API 拉
        if progress_callback:
            progress_callback("获取分钟级数据...", 50)
        provider = get_provider(data_source)
        return provider.fetch_kline(
            code=normalized_code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )

    # 日线及以上 → 走本地仓库 + 增量更新
    def remote_fetch(c: str, s: str, e: str) -> pd.DataFrame:
        provider = get_provider(data_source)
        return provider.fetch_kline(
            code=c,
            start_date=s,
            end_date=e,
            frequency=frequency,
            adjustflag=adjustflag,
        )

    return store.get_data_smart(
        code=normalized_code,
        start_date=start_date,
        end_date=end_date,
        fetch_fn=remote_fetch,
        progress_callback=progress_callback,
    )


def get_stock_data(
    code: str,
    start_date: str,
    end_date: str,
    frequency: str = "5",
    adjustflag: str = "3",
    show_quarterly: bool = False,
    data_source: str = "baostock",
    use_local_store: bool = True,
    progress_callback: Optional[Callable] = None,
) -> StockData:
    """
    获取股票数据（K线 + 财务数据）。

    通过 data_source 参数选择数据源，内部使用 DataProvider 抽象层。
    默认启用本地 DuckDB 仓库：已拉取过的数据直接从本地读取。

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
        use_local_store: 是否使用本地仓库缓存（默认 True）
        progress_callback: 进度回调 (message, percentage)

    Returns:
        StockData 命名元组，包含各类数据表

    Raises:
        DataFetchError: 数据获取失败
    """
    try:
        provider = get_provider(data_source)
        normalized_code = provider.normalize_code(code)
        store = get_store() if use_local_store else None

        try:
            # K线数据（走智能缓存）
            if store and use_local_store:
                kline_df = _smart_fetch_kline(
                    code=code,
                    normalized_code=normalized_code,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjustflag=adjustflag,
                    data_source=data_source,
                    store=store,
                    progress_callback=progress_callback,
                )
            else:
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
                import baostock as bs
                bs.login()
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

        finally:
            if store:
                store.close()

    except DataFetchError:
        raise
    except Exception as e:
        raise DataFetchError(f"数据获取失败: {e}", original_error=e)


def auto_frequency(
    start_date: str,
    end_date: str,
) -> str:
    """
    根据时间跨度自动推荐 K 线频率。

    规则:
        < 1个月  → 5分钟 (默认不变)
        1-6个月  → 日线
        6月-3年  → 日线
        > 3年    → 周线

    Returns:
        推荐的频率字符串 ("5", "d", "w")
    """
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        days = (end - start).days

        if days <= 30:
            return "5"
        elif days <= 1095:  # 3 years
            return "d"
        else:
            return "w"
    except (ValueError, TypeError):
        return "d"  # fallback


def get_data_overview(store: Optional[DataStore] = None) -> pd.DataFrame:
    """
    获取本地数据仓库概况。

    Returns:
        DataFrame: code, first_date, last_date, total_rows
    """
    if store is None:
        store = get_store()

    overview = store.conn.execute("""
        SELECT
            sm.code,
            sm.first_date,
            sm.last_date,
            COUNT(sd.date) as total_rows
        FROM stock_meta sm
        LEFT JOIN stock_daily sd ON sm.code = sd.code
        GROUP BY sm.code, sm.first_date, sm.last_date
        ORDER BY sm.code
    """).df()
    return overview
