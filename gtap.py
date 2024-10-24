import streamlit as st  # 用于创建Web应用界面
import baostock as bs  # 用于获取股票数据
import pandas as pd  # 用于数据处理和分析
import plotly.graph_objects as go  # 用于创建交互式图表
import matplotlib.pyplot as plt  # 用于创建静态图表
import mplfinance as mpf  # 用于创建金融图表
import numpy as np  # 用于数值计算

def get_stock_data(code, start_date, end_date, show_quarterly_data):
    # 登录系统
    lg = bs.login()
    
    # 获取股票数据
    rs = bs.query_history_k_data_plus(code,
        "date,time,code,open,high,low,close,volume",
        start_date=start_date, end_date=end_date,
        frequency="5", adjustflag="3")
    
    # 将数据转换为DataFrame
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)
    
    # 获取除权除息信息
    rs_dividend = bs.query_dividend_data(code=code, year="", yearType="report")
    dividend_data = []
    while (rs_dividend.error_code == '0') & rs_dividend.next():
        dividend_data.append(rs_dividend.get_row_data())
    dividend_df = pd.DataFrame(dividend_data, columns=rs_dividend.fields)
    
    # 获取证券基本资料
    rs_stock_basic = bs.query_stock_basic(code=code)
    stock_basic_list = []
    while (rs_stock_basic.error_code == '0') & rs_stock_basic.next():
        stock_basic_list.append(rs_stock_basic.get_row_data())
    stock_basic_df = pd.DataFrame(stock_basic_list, columns=rs_stock_basic.fields)
    
    # 获取季频财务数据
    profit_df = pd.DataFrame()
    operation_df = pd.DataFrame()
    growth_df = pd.DataFrame()
    balance_df = pd.DataFrame()
    cash_flow_df = pd.DataFrame()
    dupont_df = pd.DataFrame()
    performance_express_df = pd.DataFrame()
    forecast_df = pd.DataFrame()
    
    if show_quarterly_data:
        # 季频盈利能力
        profit_data = []
        rs_profit = bs.query_profit_data(code=code, year=start_date[:4], quarter="1")
        while (rs_profit.error_code == '0') & rs_profit.next():
            profit_data.append(rs_profit.get_row_data())
        profit_df = pd.DataFrame(profit_data, columns=rs_profit.fields)
        
        # 将列名更改为中文
        profit_df = profit_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'roeAvg': '平均净资产收益率(%)',
            'npMargin': '销售净利率(%)',
            'gpMargin': '销售毛利率(%)',
            'netProfit': '净利润(元)',
            'epsTTM': '每股收益',
            'MBRevenue': '主营营业收入(元)',
            'totalShare': '总股本',
            'liqaShare': '流通股本'
        })
        
        # 季频营运能力
        operation_data = []
        rs_operation = bs.query_operation_data(code=code, year=start_date[:4], quarter="1")
        while (rs_operation.error_code == '0') & rs_operation.next():
            operation_data.append(rs_operation.get_row_data())
        operation_df = pd.DataFrame(operation_data, columns=rs_operation.fields)
        
        # 将列名更改为中文
        operation_df = operation_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'NRTurnRatio': '应收账款周转率(次)',
            'NRTurnDays': '应收账款周转天数(天)',
            'INVTurnRatio': '存货周转率(次)',
            'INVTurnDays': '存货周转天数(天)',
            'CATurnRatio': '流动资产周转率(次)',
            'AssetTurnRatio': '总资产周转率'
        })
        
        # 季频成长能力
        growth_data = []
        rs_growth = bs.query_growth_data(code=code, year=start_date[:4], quarter="1")
        while (rs_growth.error_code == '0') & rs_growth.next():
            growth_data.append(rs_growth.get_row_data())
        growth_df = pd.DataFrame(growth_data, columns=rs_growth.fields)
        
        # 将列名更改为中文
        growth_df = growth_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'YOYEquity': '净资产同比增长率',
            'YOYAsset': '总资产同比增长率',
            'YOYNI': '净利润同比增长率',
            'YOYEPSBasic': '基本每股收益同比增长率',
            'YOYPNI': '归属母公司股东的净利润同比增长率'
        })
        
        # 季频偿债能力
        balance_data = []
        rs_balance = bs.query_balance_data(code=code, year=start_date[:4], quarter="1")
        while (rs_balance.error_code == '0') & rs_balance.next():
            balance_data.append(rs_balance.get_row_data())
        balance_df = pd.DataFrame(balance_data, columns=rs_balance.fields)
        
        # 将列名更改为中文
        balance_df = balance_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'currentRatio': '流动比率',
            'quickRatio': '速动比率',
            'cashRatio': '现金比率',
            'YOYLiability': '总负债同比增长率',
            'liabilityToAsset': '资产负债率',
            'assetToEquity': '权益乘数'
        })
        
        # 季频现金流量
        cash_flow_data = []
        rs_cash_flow = bs.query_cash_flow_data(code=code, year=start_date[:4], quarter="1")
        while (rs_cash_flow.error_code == '0') & rs_cash_flow.next():
            cash_flow_data.append(rs_cash_flow.get_row_data())
        cash_flow_df = pd.DataFrame(cash_flow_data, columns=rs_cash_flow.fields)
        
        # 将列名更改为中文
        cash_flow_df = cash_flow_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'CAToAsset': '流动资产除以总资产',
            'NCAToAsset': '非流动资产除以总资产',
            'tangibleAssetToAsset': '有形资产除以总资产',
            'ebitToInterest': '已获利息倍数',
            'CFOToOR': '经营活动产生的现金流量净额除以营业收入',
            'CFOToNP': '经营性现金净流量除以净利润',
            'CFOToGr': '经营性现金净流量除以营业总收入'
        })
        
        # 季频杜邦指数
        dupont_data = []
        rs_dupont = bs.query_dupont_data(code=code, year=start_date[:4], quarter="1")
        while (rs_dupont.error_code == '0') & rs_dupont.next():
            dupont_data.append(rs_dupont.get_row_data())
        dupont_df = pd.DataFrame(dupont_data, columns=rs_dupont.fields)
        
        # 将列名更改为中文
        dupont_df = dupont_df.rename(columns={
            'code': '证券代码',
            'pubDate': '公司发布日期',
            'statDate': '统计截止日期',
            'dupontROE': '净资产收益率',
            'dupontAssetStoEquity': '权益乘数',
            'dupontAssetTurn': '总资产周转率',
            'dupontAssetTurnover': '总资产周转率',
            'dupontPnitoni': '归属母公司股东的净利润/净利润',
            'dupontNitogr': '净利润/营业总收入',
            'dupontTaxBurden': '净利润/利润总额',
            'dupontIntburden': '利润总额/息税前利润',
            'dupontEbittogr': '息税前利润/营业总收入'
        })
        
        # 季频公司业绩快报
        performance_express_data = []
        rs_performance_express = bs.query_performance_express_report(code=code, start_date=start_date, end_date=end_date)
        while (rs_performance_express.error_code == '0') & rs_performance_express.next():
            performance_express_data.append(rs_performance_express.get_row_data())
        performance_express_df = pd.DataFrame(performance_express_data, columns=rs_performance_express.fields)
        
        # 将列名更改为中文
        performance_express_df = performance_express_df.rename(columns={
            'code': '证券代码',
            'performanceExpPubDate': '业绩快报披露日',
            'performanceExpStatDate': '业绩快报统计日期',
            'performanceExpUpdateDate': '业绩快报披露日(最新)',
            'performanceExpressTotalAsset': '业绩快报总资产',
            'performanceExpressNetAsset': '业绩快报净资产',
            'performanceExpressEPSChgPct': '业绩每股收益增长率',
            'performanceExpressROEWa': '业绩快报净资产收益率ROE-加权',
            'performanceExpressEPSDiluted': '业绩快报每股收益EPS-摊薄',
            'performanceExpressGRYOY': '业绩快报营业总收入同比',
            'performanceExpressOPYOY': '业绩快报营业利润同比'
        })
        
        # 季频公司业绩预告
        forecast_data = []
        rs_forecast = bs.query_forecast_report(code=code, start_date=start_date, end_date=end_date)
        while (rs_forecast.error_code == '0') & rs_forecast.next():
            forecast_data.append(rs_forecast.get_row_data())
        forecast_df = pd.DataFrame(forecast_data, columns=rs_forecast.fields)
        
        # 将列名更改为中文
        forecast_df = forecast_df.rename(columns={
            'code': '证券代码',
            'profitForcastExpPubDate': '业绩预告发布日期',
            'profitForcastExpStatDate': '业绩预告统计日期',
            'profitForcastType': '业绩预告类型',
            'profitForcastAbstract': '业绩预告摘要',
            'profitForcastChgPctUp': '预告归属于母公司的净利润增长上限(%)',
            'profitForcastChgPctDwn': '预告归属于母公司的净利润增长下限(%)'
        })
    
    # 登出系统
    bs.logout()
    
    # 将日期和时间合并为一个datetime列
    result['datetime'] = pd.to_datetime(result['date'] + ' ' + result['time'].str[-9:-3], format='%Y-%m-%d %H%M%S%f')
    result = result.set_index('datetime')
    
    return result, dividend_df, stock_basic_df, profit_df, operation_df, growth_df, balance_df, cash_flow_df, dupont_df, performance_express_df, forecast_df

def calculate_fees(amount, is_buy, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate):
    commission = max(amount * commission_rate, 5)  # 佣金，最低5元
    transfer_fee = amount * transfer_fee_rate if stock_code.startswith('sh') else 0  # 过户费，仅沪市收取
    stamp_duty = amount * stamp_duty_rate if not is_buy else 0  # 印花税，仅卖出时收取
    total_fee = commission + transfer_fee + stamp_duty
    return commission, transfer_fee, stamp_duty, total_fee

def grid_trading(data, grid_upper, grid_lower, grid_number, grid_center, shares_per_grid, initial_shares, current_holding_price, total_investment, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate):
    # 计算剩余资金
    cash = total_investment - (current_holding_price * initial_shares)
    # 计算网格间距
    grid_step = (grid_upper - grid_lower) / (grid_number - 1)  # 每个网格的价格间隔
    # 计算每个网格线的价格
    grid_prices = [grid_lower + i * grid_step for i in range(grid_number)]
    # 定义网格中心价格
    current_grid_center = grid_center
    
    # 初始化变量
    shares = initial_shares  # 持有的股票数量
    total_buy_volume = initial_shares * current_holding_price  # 总买入金额
    commission, transfer_fee, stamp_duty, total_fee = calculate_fees(total_buy_volume, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate)
    total_sell_volume = 0  # 总卖出金额
    total_buy_count = 1  # 总买入次数
    total_sell_count = 0  # 总卖出次数
    trade_profits = []  # 每笔交易的盈利
    asset_values = []  # 资产价值变化
    avg_price = current_holding_price  # 平均持仓价格
    total_fees = 0  # 总费用
    cash -= total_fee  # 更新现金余额
    trades = [('初次买入', data.index[0], current_holding_price, initial_shares, current_holding_price, commission, transfer_fee, stamp_duty, total_fee, shares)]  # 交易记录，添加初始持仓价格和费用

    # 执行网格交易回测
    for i, row in data.iterrows():
        price = float(row['close'])  # 当前收盘价

        # 定义两个变量用于查找网格中心价格在grid_prices里面的上下网格线价格
        current_grid_lower = max([gp for gp in grid_prices if gp < current_grid_center], default=grid_lower)
        current_grid_upper = min([gp for gp in grid_prices if gp > current_grid_center], default=grid_upper)

        # 如果持有股票数量为0，则退出循环
        if shares == 0:
            break

        # 检查是否需要买入
        if price < current_grid_lower and price < current_grid_lower:
            grids = (current_grid_center - price) // grid_step if grid_step != 0 else 0  # 计算跨越的网格数，采用整除避免除以零错误
            # 如果价格低于当前网格下限但计算的网格数为0，则强制设置为1个网格
            # 这确保即使价格下跌幅度小于一个完整的网格，也会触发买入操作
            if grids == 0 and price < current_grid_lower:
                grids = 1
            buy_shares = grids * shares_per_grid  # 买入的股票数量
            buy_amount = buy_shares * price  # 计算买入金额：买入股数乘以当前价格
            commission, transfer_fee, stamp_duty, total_fee = calculate_fees(buy_amount, True, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate)
            if cash >= buy_amount + total_fee and grids > 0:
                total_buy_volume = shares * price  # 更新所持股票的价值
                cash -= buy_amount + total_fee  # 更新现金余额
                shares += buy_shares  # 更新持有的股票数量
                total_buy_volume += buy_amount  # 更新总买入金额
                total_buy_count += 1  # 更新总买入次数
                avg_price = total_buy_volume / shares if shares != 0 else 0  # 更新平均持仓价格，避免除以零错误
                current_grid_center = min([gp for gp in grid_prices if gp > price], default=grid_upper)  # 更新当前网格中心价格
                total_fees += total_fee
                trades.append(('买入', i, price, buy_shares, avg_price, commission, transfer_fee, stamp_duty, total_fee, shares))  # 记录交易，包括交易前的平均持仓价格和费用
        
        # 检查是否需要卖出
        elif price > current_grid_upper and price > current_grid_upper:
            grids = (price - current_grid_center) // grid_step if grid_step != 0 else 0  # 计算跨越的网格数，采用整除避免除以零错误
            # 如果价格高于当前网格上限但计算的网格数为0，则强制设置为1个网格
            # 这确保即使价格上涨幅度小于一个完整的网格，也会触发卖出操作
            if grids == 0 and price > current_grid_upper:
                grids = 1
            sell_shares = min(grids * shares_per_grid, shares)  # 卖出的股票数量，不能超过持有的股票数量
            if sell_shares > 0 and grids > 0:
                total_buy_volume = shares * price  # 更新所持股票的价值
                sell_amount = sell_shares * price  # 计算卖出金额：卖出股数乘以当前价格
                commission, transfer_fee, stamp_duty, total_fee = calculate_fees(sell_amount, False, stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate)
                cash += sell_amount - total_fee  # 更新现金余额
                trade_profit = sell_amount - (sell_shares * avg_price) - total_fee  # 计算交易盈利
                trade_profits.append(trade_profit)  # 记录交易盈利
                shares -= sell_shares  # 更新持有的股票数量
                total_sell_volume += sell_amount  # 更新总卖出金额
                total_sell_count += 1  # 更新总卖出次数
                avg_price = (total_buy_volume - sell_amount) / shares if shares > 0 else 0  # 更新平均持仓价格，避免除以零错误
                current_grid_center = max([gp for gp in grid_prices if gp < price], default=grid_lower)  # 更新当前网格中心价格
                total_fees += total_fee
                trades.append(('卖出', i, price, sell_shares, avg_price, commission, transfer_fee, stamp_duty, total_fee, shares))  # 记录交易，包括交易前的平均持仓价格和费用

        # 计算当前资产价值
        asset_value = cash + shares * price
        asset_values.append(asset_value)

    return trades, total_buy_volume, total_sell_volume, total_buy_count, total_sell_count, trade_profits, asset_values, total_fees

def main():
    # 创建左侧边栏
    with st.sidebar:
        st.title("Grid Trading Analysis Platform")
        st.markdown("<style>h1{text-align: center;}</style>", unsafe_allow_html=True)
        # 添加一条横线
        st.markdown("---")

        # 股票代码及周期
        st.subheader('股票代码及周期参数')
        stock_code = st.text_input('请输入股票代码（例如：sh.601398。sh：上海；sz：深圳）：', value='sh.601398')  # 股票代码输入框
        start_date = st.date_input('开始日期')  # 开始日期选择器
        end_date = st.date_input('结束日期')  # 结束日期选择器

        # 网格交易参数
        st.subheader('网格交易参数')
        grid_upper = st.number_input('网格上限', value=0.0, step=0.01)  # 网格交易的上限价格
        grid_lower = st.number_input('网格下限', value=0.0, step=0.01)  # 网格交易的下限价格
        grid_number = st.number_input('网格数量', value=10, min_value=2, step=1)  # 网格的数量
        grid_center = st.number_input('网格中心价格', value=0.0, step=0.01)  # 网格交易的中心价格
        # 计算网格价差
        grid_step = (grid_upper - grid_lower) / grid_number if grid_number != 0 else 0
        # 显示网格价差（不可编辑）
        st.text_input('网格价差', value=f'{grid_step:.4f}', disabled=True)
        current_holding_price = st.number_input('当前持仓价格', value=0.0, step=0.01)  # 当前持仓价格
        initial_shares = st.number_input('初次买入股数', value=100, min_value=1, step=1)  # 初始购买的股票数量
        shares_per_grid = st.number_input('每个网格交易股数', value=100, min_value=1, step=1)  # 每个网格交易的股票数量
        total_investment = st.number_input('预计投入总资金', value=10000.0, min_value=0.0, step=100.0)  # 预计投入的总资金
        # 计算剩余资金
        remaining_funds = total_investment - current_holding_price * initial_shares
        st.text_input('剩余资金(未扣除手续费)', value=f'{remaining_funds:.2f}', disabled=True)

        # 交易费用参数
        st.subheader('交易费用参数')
        commission_rate = st.number_input('佣金费率', value=0.0003, format='%f')  # 佣金费率
        transfer_fee_rate = st.number_input('过户费费率', value=0.0002, format='%f')  # 过户费费率
        stamp_duty_rate = st.number_input('印花税费率', value=0.0001, format='%f')  # 印花税费率

        # 季频财务数据选项
        st.subheader('季频财务数据选项')
        show_quarterly_data = st.checkbox('显示季频财务数据', value=False)

        # 插入一行空行
        st.write("")

        col1, col2, col3 = st.columns([1, 1, 3])
        with col3:
            run_backtest = st.button('运行网格交易回测')  # 运行回测的按钮
    
    # 主要内容区
    if run_backtest:
        if stock_code:
            data, dividend_df, stock_basic_df, profit_df, operation_df, growth_df, \
            balance_df, cash_flow_df, dupont_df, performance_express_df, forecast_df = \
            get_stock_data(stock_code, start_date.strftime('%Y-%m-%d'), \
            end_date.strftime('%Y-%m-%d'), show_quarterly_data)
            
            if not data.empty:
                st.markdown(f"<h2 style='text-align: center;'>{stock_code} 的分析信息</h2>", unsafe_allow_html=True)
                # 添加一条横线
                st.markdown("---")
                
                # 将数据转换为适合mplfinance的格式
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                data[numeric_columns] = data[numeric_columns].astype(float)

                # 显示最新交易日数据
                st.subheader('股票历史K线数据')
                latest_data = data.iloc[-1]  # 最新一天的交易数据
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("开盘", f"{latest_data['open']:.2f}", delta=None, delta_color="normal")  # 开盘价
                col2.metric("收盘", f"{latest_data['close']:.2f}", delta=None, delta_color="normal")  # 收盘价
                col3.metric("最高", f"{latest_data['high']:.2f}", delta=None, delta_color="normal")  # 最高价
                col4.metric("最低", f"{latest_data['low']:.2f}", delta=None, delta_color="normal")  # 最低价
                
                col5, col6 = st.columns(2)
                col5.metric("成交量", f"{latest_data['volume']:.0f}", delta=None, delta_color="normal")  # 成交量
                col6.metric("涨跌幅", f"{(latest_data['close'] / data.iloc[-2]['close'] - 1) * 100:.2f}%", delta=None, delta_color="normal")  # 涨跌幅

                # 计算均线
                data['MA5'] = data['close'].rolling(window=5).mean()  # 5日移动平均线
                data['MA10'] = data['close'].rolling(window=10).mean()  # 10日移动平均线
                data['MA20'] = data['close'].rolling(window=20).mean()  # 20日移动平均线

                # 创建Plotly图表以支持交互功能
                fig = go.Figure()

                # 添加K线图
                fig.add_trace(go.Candlestick(x=data.index,
                                   open=data['open'],
                                   high=data['high'],
                                   low=data['low'],
                                   close=data['close'],
                                   name='K线'))

                # 添加均线
                fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], name='MA5', line=dict(color='blue', width=1)))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA10'], name='MA10', line=dict(color='orange', width=1)))
                fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], name='MA20', line=dict(color='green', width=1)))

                # 添加成交量图表
                fig.add_trace(go.Bar(x=data.index, y=data['volume'], name='成交量', yaxis='y2', visible='legendonly'))

                # 设置图表布局
                fig.update_layout(
                    title=f'{stock_code}的5分钟K线图和成交量',
                    yaxis_title='价格',
                    xaxis_rangeslider_visible=True,
                    height=800,  # 增加图表高度以容纳成交量
                    dragmode='zoom',
                    yaxis2=dict(
                        title='成交量',
                        overlaying='y',
                        side='right',
                        showgrid=False
                    ),
                    xaxis_rangeslider=dict(
                        visible=True,
                        yaxis=dict(rangemode='auto')
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )

                # 设置子图布局
                fig.update_layout(
                    yaxis=dict(domain=[0.3, 1]),  # 主图（K线和均线）占70%
                    yaxis2=dict(domain=[0, 0.2])  # 成交量图占20%
                )

                # 在Streamlit中显示交互式图表
                st.plotly_chart(fig, use_container_width=True)                

                # 显示证券基本资料
                st.subheader('证券基本资料')
                if not stock_basic_df.empty:
                    # 重命名列为中文
                    stock_basic_df = stock_basic_df.rename(columns={
                        'code': '证券代码',
                        'code_name': '证券名称',
                        'ipoDate': '上市日期',
                        'outDate': '退市日期',
                        'type': '证券类型',
                        'status': '上市状态'
                    })
                    # 将type和status转换为中文描述
                    type_map = {'1': '股票', '2': '指数', '3': '其他'}
                    status_map = {'1': '上市', '0': '退市'}
                    stock_basic_df['证券类型'] = stock_basic_df['证券类型'].map(type_map)
                    stock_basic_df['上市状态'] = stock_basic_df['上市状态'].map(status_map)
                    st.dataframe(stock_basic_df, use_container_width=True)
                else:
                    st.write("没有找到证券基本资料。")

                # 显示数据表格
                st.subheader('股票历史交易数据')
                # 重置索引以显示datetime列
                display_data = data.reset_index()
                # 格式化datetime列
                display_data['datetime'] = display_data['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
                # 重命名列为中文
                display_data = display_data.rename(columns={
                    'datetime': '日期时间',
                    'date': '交易所行情日期',
                    'time': '交易所行情时间',
                    'code': '证券代码',
                    'open': '开盘价',
                    'high': '最高价',
                    'low': '最低价',
                    'close': '收盘价',
                    'volume': '成交量'
                })
                st.dataframe(display_data, use_container_width=True)

                # 显示除权除息信息
                st.subheader('股票除权除息信息')
                if not dividend_df.empty:
                    # 重命名列为中文
                    dividend_df = dividend_df.rename(columns={
                        'code': '证券代码',
                        'dividPreNoticeDate': '预批露公告日',
                        'dividAgmPumDate': '股东大会公告日期',
                        'dividPlanAnnounceDate': '预案公告日',
                        'dividPlanDate': '分红实施公告日',
                        'dividRegistDate': '股权登记日',
                        'dividOperateDate': '除权除息日',
                        'dividPayDate': '派息日',
                        'dividStockMarketDate': '红股上市日',
                        'dividCashPsBeforeTax': '每股股利税前',
                        'dividCashPsAfterTax': '每股股利税后',
                        'dividStocksPs': '每股送股',
                        'dividCashStock': '每股转增',
                        'dividReserveToStockPs': '每股转增资本公积'
                    })
                    st.dataframe(dividend_df, use_container_width=True)
                else:
                    st.write("没有找到除权除息信息。")

                # 显示季频财务数据信息
                if show_quarterly_data:
                    st.subheader('季频财务数据信息')
                    
                    # 季频盈利能力
                    st.write("季频盈利能力")
                    st.dataframe(profit_df, use_container_width=True)
                    
                    # 季频营运能力
                    st.write("季频营运能力")
                    st.dataframe(operation_df, use_container_width=True)
                    
                    # 季频成长能力
                    st.write("季频成长能力")
                    st.dataframe(growth_df, use_container_width=True)
                    
                    # 季频偿债能力
                    st.write("季频偿债能力")
                    st.dataframe(balance_df, use_container_width=True)
                    
                    # 季频现金流量
                    st.write("季频现金流量")
                    st.dataframe(cash_flow_df, use_container_width=True)
                    
                    # 季频杜邦指数
                    st.write("季频杜邦指数")
                    st.dataframe(dupont_df, use_container_width=True)
                    
                    # 季频公司业绩快报
                    st.write("季频公司业绩快报")
                    st.dataframe(performance_express_df, use_container_width=True)
                    
                    # 季频公司业绩预告
                    st.write("季频公司业绩预告")
                    st.dataframe(forecast_df, use_container_width=True)
                
                # ----------------------------------- 网格交易 -----------------------------------
                # 添加一条横线
                st.markdown("---")
                # 执行网格交易回测
                trades, total_buy_volume, total_sell_volume, total_buy_count, total_sell_count, trade_profits, asset_values, total_fees = grid_trading(
                    data, grid_upper, grid_lower, grid_number, grid_center, shares_per_grid, initial_shares, current_holding_price, total_investment,
                    stock_code, commission_rate, transfer_fee_rate, stamp_duty_rate
                )

                # 显示交易记录
                st.subheader('网格交易记录')
                trades_df = pd.DataFrame(trades, columns=['操作', '时间', '价格', '数量', '当前持仓价格', '佣金', '过户费', '印花税', '总费用', '持股总数'])
                st.dataframe(trades_df, use_container_width=True)

                # 绘制资产价值变化图
                fig_asset = go.Figure()
                fig_asset.add_trace(go.Scatter(x=data.index, y=asset_values, mode='lines', name='资产价值'))
                fig_asset.update_layout(title='资产价值变化', xaxis_title='时间', yaxis_title='资产价值')
                st.plotly_chart(fig_asset)

                # 计算最终资产价值和利润
                initial_investment = initial_shares * current_holding_price  # 初始投资总额
                final_value = asset_values[-1]  # 最终资产价值
                profit = final_value - total_investment  # 总盈利
                profit_percentage = (profit / total_investment) * 100 if total_investment != 0 else 0  # 盈利百分比，使用总投资额计算，避免除以零错误

                # 计算扣除费用后的利润和利润率
                profit_after_fees = profit - total_fees
                profit_percentage_after_fees = (profit_after_fees / total_investment) * 100 if total_investment != 0 else 0

                # 添加网格交易回测功能
                st.subheader('网格交易回测')
                
                # 显示回测结果
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("初始投资", f"¥{initial_investment:.2f}")  # 初始投资金额
                col2.metric("最终资产", f"¥{final_value:.2f}")  # 最终资产价值
                col3.metric("利润（含费用）", f"¥{profit:.2f}", f"{profit_percentage:.2f}%")  # 利润和利润率（含费用）
                col4.metric("利润（扣除费用）", f"¥{profit_after_fees:.2f}", f"{profit_percentage_after_fees:.2f}%")  # 利润和利润率（扣除费用）

                # 计算年化波动率
                # 计算日收益率
                daily_returns = data['close'].pct_change().dropna()
                
                # 计算年化波动率
                annual_volatility = daily_returns.std() * np.sqrt(252)  # 假设一年有252个交易日
                
                # 计算年化收益率
                total_days = (end_date - start_date).days
                annual_return = ((final_value / total_investment) ** (365 / total_days) - 1) * 100 if total_investment != 0 and total_days != 0 else 0

                # 计算扣除费用后的年化收益率
                annual_return_after_fees = (((final_value - total_fees) / total_investment) ** (365 / total_days) - 1) * 100 if total_investment != 0 and total_days != 0 else 0

                # 计算扣除费用后的年化波动率
                daily_returns_after_fees = daily_returns - (total_fees / total_days / total_investment) if total_days != 0 and total_investment != 0 else daily_returns
                annual_volatility_after_fees = daily_returns_after_fees.std() * np.sqrt(252)

                # 显示绩效指标
                st.subheader('网格绩效指标')
                col1, col2, col3 = st.columns(3)
                col1.metric("总收益率（扣除费用）", f"{profit_percentage_after_fees:.2f}%")  # 总收益率（扣除费用）
                col2.metric("年化收益率（含费用）", f"{annual_return:.2f}%")  # 年化收益率（含费用）
                col3.metric("年化波动率（含费用）", f"{annual_volatility * 100:.2f}%")  # 年化波动率（含费用）

                col1, col2 = st.columns(2)
                col1.metric("年化收益率（扣除费用）", f"{annual_return_after_fees:.2f}%")  # 年化收益率（扣除费用）
                col2.metric("年化波动率（扣除费用）", f"{annual_volatility_after_fees * 100:.2f}%")  # 年化波动率（扣除费用）

                # 计算交易活动指标
                total_trades = total_buy_count + total_sell_count  # 总交易次数
                win_rate = sum(1 for profit in trade_profits if profit > 0) / len(trade_profits) if trade_profits else 0  # 胜率
                best_trade = max(trade_profits) if trade_profits else 0  # 最佳交易
                worst_trade = min(trade_profits) if trade_profits else 0  # 最差交易
                avg_trade = sum(trade_profits) / len(trade_profits) if trade_profits else 0  # 平均交易盈利

                # 显示交易活动
                st.subheader('网格交易活动')
                col1, col2, col3 = st.columns(3)
                col1.metric("总买入次数", total_buy_count)  # 总买入次数
                col2.metric("总卖出次数", total_sell_count)  # 总卖出次数
                col3.metric("交易次数", total_trades)  # 总交易次数

                col1, col2, col3 = st.columns(3)
                col1.metric("总买入金额", f"¥{total_buy_volume:.2f}")  # 总买入金额
                col2.metric("总卖出金额", f"¥{total_sell_volume:.2f}")  # 总卖出金额
                col3.metric("胜率", f"{win_rate:.2%}")  # 胜率

                col1, col2, col3 = st.columns(3)
                col1.metric("最佳交易", f"¥{best_trade:.2f}")  # 最佳交易盈利
                col2.metric("最差交易", f"¥{worst_trade:.2f}")  # 最差交易亏损
                col3.metric("平均交易", f"¥{avg_trade:.2f}")  # 平均交易盈利

            else:
                st.error('未找到股票数据，请检查股票代码是否正确。')
        else:
            st.warning('请输入股票代码。')

if __name__ == '__main__':
    main()