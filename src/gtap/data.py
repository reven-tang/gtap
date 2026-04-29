"""
数据获取模块 - GTAP 网格交易回测平台

封装 baostock 数据获取逻辑，支持 K线数据、除权除息、基本资料和季频财务数据。
"""

from typing import NamedTuple
import baostock as bs
import pandas as pd
from .exceptions import DataFetchError


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
) -> StockData:
    """
    获取股票数据（K线 + 财务数据）。

    Args:
        code: 股票代码，如 "sh.601398"
        start_date: 开始日期，YYYY-MM-DD
        end_date: 结束日期，YYYY-MM-DD
        frequency: K线频率，"5"（5分钟）/"15"/"30"/"60"/"d"/"w"/"m"
        adjustflag: 复权类型，"1"=前复权 "2"=后复权 "3"=不复权
        show_quarterly: 是否获取季频财务数据

    Returns:
        StockData 命名元组，包含各类数据表

    Raises:
        DataFetchError: 数据获取失败
    """
    try:
        # 登录
        lg = bs.login()
        if lg.error_code != "0":
            raise DataFetchError(f"baostock 登录失败: {lg.error_msg}", code=lg.error_code)

        # 查询 K 线数据
        rs = bs.query_history_k_data_plus(
            code,
            "date,time,code,open,high,low,close,volume",
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
        )
        kline_list = []
        while rs.error_code == "0" and rs.next():
            kline_list.append(rs.get_row_data())
        kline_df = pd.DataFrame(kline_list, columns=rs.fields)

        # 数据清洗：合并日期和时间为 datetime 索引
        if not kline_df.empty:
            # baostock 的 time 字段格式因频率而异：
            # - 日线/周线/月线：time 返回日期字符串 (如 "20250102")
            # - 分钟线：time 返回时间字符串 (如 "09:35:00" 或 "09:35:00.000")
            # pandas 3.x 对日期解析更严格，需要分别处理
            def combine_datetime(row):
                time_str = str(row["time"]) if row["time"] else ""
                # 如果 time 是 8 位数字格式 (YYYYMMDD)，说明这是日期频率数据
                if len(time_str) == 8 and time_str.isdigit():
                    return row["date"]
                # 否则是时间格式，截取前 8 位 (HH:MM:SS)
                return row["date"] + " " + time_str[:8]
            
            kline_df["datetime"] = kline_df.apply(combine_datetime, axis=1)
            kline_df["datetime"] = pd.to_datetime(kline_df["datetime"])
            kline_df = kline_df.set_index("datetime")
            # 数值列转换为 float
            numeric_cols = ["open", "high", "low", "close", "volume"]
            kline_df[numeric_cols] = kline_df[numeric_cols].astype(float)

        # 查询除权除息
        rs_dividend = bs.query_dividend_data(code=code, year="", yearType="report")
        dividend_list = []
        while rs_dividend.error_code == "0" and rs_dividend.next():
            dividend_list.append(rs_dividend.get_row_data())
        dividend_df = pd.DataFrame(dividend_list, columns=rs_dividend.fields)

        # 查询证券基本资料
        rs_basic = bs.query_stock_basic(code=code)
        basic_list = []
        while rs_basic.error_code == "0" and rs_basic.next():
            basic_list.append(rs_basic.get_row_data())
        stock_basic_df = pd.DataFrame(basic_list, columns=rs_basic.fields)

        # 季频财务数据（可选）
        profit_df = pd.DataFrame()
        operation_df = pd.DataFrame()
        growth_df = pd.DataFrame()
        balance_df = pd.DataFrame()
        cash_flow_df = pd.DataFrame()
        dupont_df = pd.DataFrame()
        performance_express_df = pd.DataFrame()
        forecast_df = pd.DataFrame()

        if show_quarterly:
            year = start_date[:4]

            # 盈利能力
            rs_profit = bs.query_profit_data(code=code, year=year, quarter="1")
            profit_list = []
            while rs_profit.error_code == "0" and rs_profit.next():
                profit_list.append(rs_profit.get_row_data())
            profit_df = pd.DataFrame(profit_list, columns=rs_profit.fields)

            # 营运能力
            rs_operation = bs.query_operation_data(code=code, year=year, quarter="1")
            operation_list = []
            while rs_operation.error_code == "0" and rs_operation.next():
                operation_list.append(rs_operation.get_row_data())
            operation_df = pd.DataFrame(operation_list, columns=rs_operation.fields)

            # 成长能力
            rs_growth = bs.query_growth_data(code=code, year=year, quarter="1")
            growth_list = []
            while rs_growth.error_code == "0" and rs_growth.next():
                growth_list.append(rs_growth.get_row_data())
            growth_df = pd.DataFrame(growth_list, columns=rs_growth.fields)

            # 偿债能力
            rs_balance = bs.query_balance_data(code=code, year=year, quarter="1")
            balance_list = []
            while rs_balance.error_code == "0" and rs_balance.next():
                balance_list.append(rs_balance.get_row_data())
            balance_df = pd.DataFrame(balance_list, columns=rs_balance.fields)

            # 现金流量
            rs_cash_flow = bs.query_cash_flow_data(code=code, year=year, quarter="1")
            cash_flow_list = []
            while rs_cash_flow.error_code == "0" and rs_cash_flow.next():
                cash_flow_list.append(rs_cash_flow.get_row_data())
            cash_flow_df = pd.DataFrame(cash_flow_list, columns=rs_cash_flow.fields)

            # 杜邦指数
            rs_dupont = bs.query_dupont_data(code=code, year=year, quarter="1")
            dupont_list = []
            while rs_dupont.error_code == "0" and rs_dupont.next():
                dupont_list.append(rs_dupont.get_row_data())
            dupont_df = pd.DataFrame(dupont_list, columns=rs_dupont.fields)

            # 业绩快报
            rs_performance = bs.query_performance_express_report(
                code=code, start_date=start_date, end_date=end_date
            )
            performance_list = []
            while rs_performance.error_code == "0" and rs_performance.next():
                performance_list.append(rs_performance.get_row_data())
            performance_express_df = pd.DataFrame(performance_list, columns=rs_performance.fields)

            # 业绩预告
            rs_forecast = bs.query_forecast_report(
                code=code, start_date=start_date, end_date=end_date
            )
            forecast_list = []
            while rs_forecast.error_code == "0" and rs_forecast.next():
                forecast_list.append(rs_forecast.get_row_data())
            forecast_df = pd.DataFrame(forecast_list, columns=rs_forecast.fields)

        # 登出
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

    except Exception as e:
        raise DataFetchError(f"数据获取失败: {e}", original_error=e)
