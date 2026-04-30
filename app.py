"""
GTAP 网格交易回测平台 - Streamlit 应用入口

重构后版本：v0.2.0
模块化架构：config + data + fees + grid + metrics + plot
"""

import streamlit as st
from datetime import date
from typing import Tuple

# 从 src.gtap 导入重构后的模块
from src.gtap import (
    GridTradingConfig,
    get_stock_data,
    grid_trading,
    calculate_metrics,
    calculate_trade_metrics,
    plot_kline,
    plot_asset_curve,
    plot_grid_lines,
    DataFetchError,
    GridTradingError,
)
import pandas as pd
import plotly.graph_objects as go


# ========== Streamlit 页面配置 ==========
st.set_page_config(
    page_title="GTAP - 网格交易回测平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ========== 侧边栏参数配置 ==========
def sidebar_config() -> Tuple[GridTradingConfig, bool]:
    """渲染侧边栏并返回配置对象 + 运行按钮状态"""

    st.sidebar.title("Grid Trading Analysis Platform")
    st.markdown("<style>h1{text-align: center;}</style>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # ---- 股票代码与周期 ----
    st.sidebar.subheader("股票代码及周期参数")
    stock_code = st.sidebar.text_input(
        "请输入股票代码（例如：sh.601398）",
        value="sh.601398",
        help="沪市：sh.601398；深市：sz.000001",
    )
    start_date = st.sidebar.date_input("开始日期", value=date(2024, 1, 1))
    end_date = st.sidebar.date_input("结束日期", value=date(2024, 12, 31))

    # ---- 网格参数 ----
    st.sidebar.subheader("网格交易参数")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        grid_upper = st.sidebar.number_input("网格上限", value=6.0, step=0.01, format="%.2f")
        grid_lower = st.sidebar.number_input("网格下限", value=4.0, step=0.01, format="%.2f")
        grid_number = st.sidebar.number_input("网格数量", value=10, min_value=2, step=1)
    with col2:
        grid_center = st.sidebar.number_input("网格中心价格", value=5.0, step=0.01, format="%.2f")
        current_holding_price = st.sidebar.number_input("当前持仓价格", value=5.0, step=0.01, format="%.2f")
        initial_shares = st.sidebar.number_input("初次买入股数", value=100, min_value=1, step=1)

    shares_per_grid = st.sidebar.number_input("每个网格交易股数", value=100, min_value=1, step=1)
    total_investment = st.sidebar.number_input(
        "预计投入总资金", value=10000.0, min_value=0.0, step=100.0, format="%.2f"
    )

    # 计算并显示网格价差
    grid_step = (grid_upper - grid_lower) / (grid_number - 1) if grid_number > 1 else 0.0
    st.sidebar.text_input(
        "网格价差（自动计算）",
        value=f"{grid_step:.4f}",
        disabled=True,
        help="网格间距 = (上限 - 下限) / (网格数 - 1)",
    )
    remaining = total_investment - current_holding_price * initial_shares
    st.sidebar.text_input(
        "剩余资金（未扣除手续费）",
        value=f"{remaining:.2f}",
        disabled=True,
    )

    # ---- 交易费用 ----
    st.sidebar.subheader("交易费用参数")
    commission_rate = st.sidebar.number_input(
        "佣金费率", value=0.0003, min_value=0.0, format="%.4f", help="默认 0.03%，最低 5 元"
    )
    transfer_fee_rate = st.sidebar.number_input(
        "过户费费率", value=0.00001, min_value=0.0, format="%.5f", help="沪市收取，默认 0.001%"
    )
    stamp_duty_rate = st.sidebar.number_input(
        "印花税费率", value=0.001, min_value=0.0, format="%.4f", help="卖出时收取，默认 0.1%"
    )

    # ---- 数据源选项 ----
    st.sidebar.subheader("数据源选项")
    frequency = st.sidebar.selectbox(
        "K线频率",
        options=["5", "15", "30", "60", "d", "w", "m"],
        index=0,
        format_func=lambda x: {
            "5": "5分钟",
            "15": "15分钟",
            "30": "30分钟",
            "60": "60分钟",
            "d": "日线",
            "w": "周线",
            "m": "月线",
        }.get(x, x),
    )
    adjustflag = st.sidebar.selectbox(
        "复权类型",
        options=["1", "2", "3"],
        index=2,
        format_func=lambda x: {"1": "前复权", "2": "后复权", "3": "不复权"}.get(x, x),
    )

    # ---- ATR 动态止损止盈（v0.3.0）----
    st.sidebar.markdown("---")
    st.sidebar.subheader("ATR 动态止损止盈")
    use_atr_stop = st.sidebar.checkbox("启用 ATR 止损止盈", value=False, help="使用 ATR 动态止损止盈，默认关闭")
    if use_atr_stop:
        atr_period = st.sidebar.slider("ATR 计算周期", min_value=5, max_value=30, value=14, step=1)
        atr_stop_mult = st.sidebar.slider("止损乘数", min_value=0.5, max_value=5.0, value=1.5, step=0.1, format="%.1f")
        atr_tp_mult = st.sidebar.slider("止盈乘数", min_value=0.0, max_value=2.0, value=0.5, step=0.1, format="%.1f")
    else:
        atr_period = 14
        atr_stop_mult = 1.5
        atr_tp_mult = 0.5

    show_quarterly = st.sidebar.checkbox("显示季频财务数据", value=False)

    st.sidebar.write("")
    run_button = st.sidebar.button("▶️ 运行网格交易回测", type="primary", width='stretch')

    # 构建配置对象
    config = GridTradingConfig(
        stock_code=stock_code,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        grid_upper=grid_upper,
        grid_lower=grid_lower,
        grid_number=grid_number,
        grid_center=grid_center,
        shares_per_grid=shares_per_grid,
        initial_shares=initial_shares,
        current_holding_price=current_holding_price,
        total_investment=total_investment,
        commission_rate=commission_rate,
        transfer_fee_rate=transfer_fee_rate,
        stamp_duty_rate=stamp_duty_rate,
        frequency=frequency,
        adjustflag=adjustflag,
        show_quarterly_data=show_quarterly,
        # ATR 参数（v0.3.0）
        use_atr_stop=use_atr_stop,
        atr_period=atr_period,
        atr_stop_multiplier=atr_stop_mult,
        atr_tp_multiplier=atr_tp_mult,
    )

    return config, run_button


# ========== 主界面渲染 ==========
def main() -> None:
    """主函数：渲染 UI、执行回测、显示结果"""

    config, run_button = sidebar_config()

    # 标题区
    st.title("📈 GTAP - Grid Trading Analysis Platform")
    st.markdown("---")

    if not run_button:
        st.info("👈 请在左侧边栏配置参数，然后点击「运行网格交易回测」")
        return

    # ========== 数据获取 ==========
    @st.cache_data(ttl=3600, show_spinner=False)
    def fetch_stock_data(code, start_date, end_date, frequency, adjustflag, show_quarterly):
        return get_stock_data(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            adjustflag=adjustflag,
            show_quarterly=show_quarterly,
        )

    with st.spinner(f"正在获取 {config.stock_code} 数据..."):
        try:
            stock_data = fetch_stock_data(
                code=config.stock_code,
                start_date=config.start_date,
                end_date=config.end_date,
                frequency=config.frequency,
                adjustflag=config.adjustflag,
                show_quarterly=config.show_quarterly_data,
            )
            data = stock_data.kline
        except DataFetchError as e:
            st.error(f"数据获取失败: {e}")
            return
        except Exception as e:
            st.error(f"未知错误: {e}")
            return

    if data.empty:
        st.error("未获取到数据，请检查股票代码和日期范围")
        return

    st.success(f"✅ 数据获取成功：共 {len(data)} 条 K 线记录")

    # 计算 ATR（如果启用）
    atr_series = None
    if config.use_atr_stop:
        from src.gtap.atr import calculate_atr
        with st.spinner("正在计算 ATR 动态止损止盈指标..."):
            try:
                atr_series = calculate_atr(data, period=config.atr_period)
                # 显示 ATR 统计
                valid_atr = atr_series.dropna()
                if len(valid_atr) > 0:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("当前 ATR", f"{valid_atr.iloc[-1]:.4f}")
                    col2.metric("ATR 均值", f"{valid_atr.mean():.4f}")
                    col3.metric("ATR 最大值", f"{valid_atr.max():.4f}")
            except Exception as e:
                st.warning(f"ATR 计算失败: {e}，将使用固定百分比止损")
                atr_series = None

    # ========== 股票数据概览 ==========
    st.header("📊 股票历史 K 线数据")
    latest = data.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("开盘", f"{latest['open']:.2f}")
    col2.metric("收盘", f"{latest['close']:.2f}")
    col3.metric("最高", f"{latest['high']:.2f}")
    col4.metric("最低", f"{latest['low']:.2f}")

    col5, col6 = st.columns(2)
    col5.metric("成交量", f"{latest['volume']:.0f}")
    if len(data) >= 2:
        pct_change = (latest["close"] / data.iloc[-2]["close"] - 1) * 100
        col6.metric("涨跌幅", f"{pct_change:.2f}%")

    # ========== 网格交易回测 ==========
    st.markdown("---")
    st.header("🔁 网格交易回测")

    with st.spinner("正在执行回测..."):
        try:
            result = grid_trading(data, config, atr_series=atr_series)
        except GridTradingError as e:
            st.error(f"回测失败: {e}")
            return

    # ========== K 线图（含交易标注）==========
    st.markdown("---")
    st.header("📊 K 线图 & 交易标注")
    fig_kline = plot_kline(data, config.stock_code, atr_series=atr_series, trades=result.trades)
    st.plotly_chart(fig_kline, width="stretch")

    # ---------- 交易记录 ----------
    st.subheader("📋 交易记录")
    trades_df = pd.DataFrame(
        [
            {
                "操作": t.action,
                "时间": t.timestamp,
                "价格": f"{t.price:.2f}",
                "数量": t.shares,
                "持股总数": t.total_shares,
                "佣金": f"{t.commission:.2f}",
                "过户费": f"{t.transfer_fee:.2f}",
                "印花税": f"{t.stamp_duty:.2f}",
                "总费用": f"{t.total_fee:.2f}",
                "持仓均价": f"{t.avg_price:.2f}",
            }
            for t in result.trades
        ]
    )
    st.dataframe(trades_df, width='stretch', height=400)

    # ---------- 资产曲线 ----------
    st.subheader("📈 资产价值变化")
    fig_asset = plot_asset_curve(data.index, result.asset_values)
    st.plotly_chart(fig_asset, width='stretch')

    # ---------- 绩效指标 ----------
    st.subheader("📊 绩效指标")

    # 计算指标（v0.3.0+: 从 asset_values 自动推导初始投资）
    metrics = calculate_metrics(
        asset_values=result.asset_values,
        trades=result.trades,
        total_fees=result.total_fees,
        start_date=pd.Timestamp(config.start_date),
        end_date=pd.Timestamp(config.end_date),
    )

    # 展示指标卡片
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("初始资产", f"¥{result.asset_values[0]:,.2f}" if result.asset_values else "¥0.00")
    col2.metric("最终资产", f"¥{result.asset_values[-1]:,.2f}" if result.asset_values else "¥0.00")
    col3.metric("总利润（含费）", f"¥{result.asset_values[-1] - result.asset_values[0]:,.2f}" if result.asset_values else "¥0.00")
    col4.metric("总费用", f"¥{result.total_fees:,.2f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("总收益率", f"{metrics['total_return']:.2f}%")
    col2.metric("年化收益率", f"{metrics['annual_return']:.2f}%")
    col3.metric("年化波动率", f"{metrics['annual_volatility']:.2f}%")

    # ATR 动态止损止盈统计（v0.3.0+）
    if config.use_atr_stop:
        st.markdown("**🛡️ ATR 动态止损止盈统计**")
        col_a, col_b, col_c, col_d, col_e = st.columns(5)
        col_a.metric("止损次数", str(result.stop_loss_count))
        col_b.metric("止盈次数", str(result.take_profit_count))
        col_c.metric("网格交易次数", str(result.grid_trade_count))
        col_d.metric("止损占比", f"{metrics['stop_loss_rate']:.2%}")
        col_e.metric("止盈占比", f"{metrics['take_profit_rate']:.2%}")

    col1, col2, col3 = st.columns(3)
    col1.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
    col2.metric("最大回撤", f"{metrics['max_drawdown']:.2f}%")
    col3.metric("胜率", f"{metrics.get('win_rate', 0):.2%}")

    # 详细指标表格
    with st.expander("📑 详细指标表"):
        detail_df = pd.DataFrame([metrics])
        st.dataframe(detail_df, width='stretch')


# ========== 运行入口 ==========
if __name__ == "__main__":
    main()
