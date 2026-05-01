"""
GTAP — 香农网格交易回测平台

v0.8.0: 香农策略默认配置 + BH对比 + 自适应网格 + P0配置修正
"""

import streamlit as st
from datetime import date
from typing import Tuple, Optional

from src.gtap import (
    GridTradingConfig,
    get_stock_data,
    grid_trading,
    calculate_metrics,
    plot_kline,
    plot_asset_curve,
    DataFetchError,
    GridTradingError,
)
from src.gtap.data import auto_frequency, get_data_overview
from src.gtap.store import get_store
from src.gtap.atr import calculate_atr
from src.gtap.providers.factory import available_providers
from src.gtap.theory import (
    calculate_shannon_insight,
    recommend_grid_params,
    get_market_regime,
    ShannonInsight,
)
import pandas as pd


# ========== Streamlit 页面配置 ==========
st.set_page_config(
    page_title="GTAP - 香农网格回测平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ========== 侧边栏参数配置 ==========
def sidebar_config() -> Tuple[GridTradingConfig, bool]:
    """渲染侧边栏并返回配置对象 + 运行按钮状态"""

    st.sidebar.title("📈 GTAP 香农回测")

    # ========== 快速预设 ==========
    st.sidebar.markdown("**⚡ 快速预设**")
    preset = st.sidebar.selectbox(
        "选择预设策略",
        options=["自定义", "🟢 香农经典(50/50)", "🔵 保守蓝筹(70/30)", "🔴 激进震荡(40/60)"],
        index=0,
        help="快速应用预设的再平衡参数"
    )

    preset_configs = {
        "🟢 香农经典(50/50)": {
            "strategy_mode": "rebalance_threshold", "target_allocation": 0.5,
            "rebalance_threshold": 0.05, "position_mode": "proportional",
            "auto_grid_range": True, "grid_spacing_mode": "geometric",
        },
        "🔵 保守蓝筹(70/30)": {
            "strategy_mode": "rebalance_threshold", "target_allocation": 0.7,
            "rebalance_threshold": 0.08, "position_mode": "proportional",
            "auto_grid_range": True, "grid_spacing_mode": "arithmetic",
        },
        "🔴 激进震荡(40/60)": {
            "strategy_mode": "rebalance_threshold", "target_allocation": 0.4,
            "rebalance_threshold": 0.03, "position_mode": "proportional",
            "auto_grid_range": True, "grid_spacing_mode": "geometric",
        },
    }

    # 应用预设
    if preset != "自定义":
        st.sidebar.success(f"已应用: {preset}")

    # ========== 基础设置 ==========
    with st.sidebar.expander("🎯 基础设置", expanded=True):
        stock_code = st.text_input("股票代码", value="sh.600958",
            help="沪市sh.600958；深市sz.000001")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input("开始日期", value=date(2022, 1, 1),
                help="建议3年以上，确保再平衡事件统计显著")
        with col_d2:
            end_date = st.date_input("结束日期", value=date(2024, 12, 31),
                help="截至最近完整年度")
        total_investment = st.number_input("投入总资金", value=200000.0,
            min_value=0.0, step=100.0, format="%.2f")
        initial_shares = st.number_input("初次买入股数", value=100, min_value=1, step=1)
        shares_per_grid = st.number_input("每格交易股数", value=100, min_value=1, step=1)

        available = available_providers()
        data_source = st.selectbox("数据源", options=available, index=0,
            format_func=lambda x: {"baostock": "BaoStock (A股免费)",
                                   "yfinance": "YFinance (港美股)",
                                   "akshare": "AkShare (A股增强)"}.get(x, x))

        st.info("💡 **香农提示**：再平衡可以从波动中创造收益。波动越大，潜在再平衡溢价越高。")

        if data_source != "baostock":
            hint = {"yfinance": "A股：600958.SS / 美股：AAPL",
                    "akshare": "纯数字：600958 / 000001"}.get(data_source, "")
            if hint:
                st.info(f"💡 代码格式: {hint}")

    # ========== 交易策略 ==========
    with st.sidebar.expander("📊 交易策略", expanded=True):
        # 网格范围 —— 默认自动
        auto_grid_range = st.checkbox("自动网格范围", value=True,
            help="基于 ATR 自动计算上下限（推荐开启）")
        if auto_grid_range:
            grid_range_mult = st.slider("ATR 乘数", min_value=0.5, max_value=5.0,
                value=2.0, step=0.1, format="%.1f",
                help="ATR × 此值 = 网格上下偏移")
            grid_upper = st.number_input("网格上限", value=12.0, step=0.01,
                format="%.2f", disabled=True, help="自动模式下由ATR计算")
            grid_lower = st.number_input("网格下限", value=8.0, step=0.01,
                format="%.2f", disabled=True, help="自动模式下由ATR计算")
        else:
            grid_range_mult = 2.0
            grid_upper = st.number_input("网格上限", value=12.0, step=0.01, format="%.2f")
            grid_lower = st.number_input("网格下限", value=8.0, step=0.01, format="%.2f")

        grid_number = st.number_input("网格数量", value=10, min_value=2, step=1)
        grid_center_manual = st.checkbox("手动设定网格中心",
            value=False, help="默认=起始日收盘价")
        grid_center = (st.number_input("网格中心", value=10.0, step=0.01, format="%.2f")
                       if grid_center_manual else None)

        # 网格间距 —— 默认等比（香农策略核心）
        grid_spacing_mode = st.selectbox("网格间距",
            options=["geometric", "arithmetic"], index=0,
            format_func=lambda x: {"geometric": "等比间距（推荐）",
                                   "arithmetic": "等差间距"}.get(x, x))

        # 策略模式引导 —— 市场判断推荐
        st.markdown("---")
        st.markdown("**🎯 你的市场判断？**")
        market_regime = st.radio("市场判断",
            options=["震荡市", "趋势市", "不确定"],
            index=1,  # 默认趋势市 → 阈值再平衡
            horizontal=True,
            help="震荡市：价格在区间内波动 | 趋势市：有方向性 | 不确定：随机")

        regime_to_strategy = {
            "震荡市": ("grid", "📊 经典网格（推荐）"),
            "趋势市": ("rebalance_threshold", "⚖️ 阈值再平衡（推荐）"),
            "不确定": ("rebalance_periodic", "📅 周期再平衡（推荐）"),
        }
        recommended_strategy, recommended_label = regime_to_strategy[market_regime]

        strategy_options = ["grid", "rebalance_threshold", "rebalance_periodic"]
        strategy_labels = {
            "grid": "📊 经典网格" + (" ✓" if market_regime == "震荡市" else ""),
            "rebalance_threshold": "⚖️ 阈值再平衡" + (" ✓" if market_regime == "趋势市" else ""),
            "rebalance_periodic": "📅 周期再平衡" + (" ✓" if market_regime == "不确定" else ""),
        }

        current_index = strategy_options.index(recommended_strategy)
        strategy_mode = st.selectbox("策略模式",
            options=strategy_options,
            index=current_index,
            format_func=lambda x: strategy_labels.get(x, x))

        regime_reasons = {
            "震荡市": "低买高卖，频繁收割波动",
            "趋势市": "捕捉趋势中的回调，减少过度交易",
            "不确定": "定期再平衡，避免情绪化操作",
        }
        if strategy_mode == recommended_strategy:
            st.success(f"💡 {market_regime}推荐：{regime_reasons[market_regime]}")
        else:
            st.info("💡 已手动切换策略")

        # 再平衡参数
        if "rebalance" in strategy_mode:
            target_allocation = st.select_slider("目标股票比例",
                options=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                value=0.5,
                format_func=lambda x: f"{x*100:.0f}%")
            rebalance_threshold = st.select_slider("再平衡阈值",
                options=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20],
                value=0.05,
                format_func=lambda x: f"{x*100:.0f}%")
        else:
            target_allocation = 0.5
            rebalance_threshold = 0.05

        # 仓位模式 —— 默认比例仓位（再平衡更合理）
        position_mode = st.selectbox("仓位模式",
            options=["proportional", "fixed_shares", "fixed_amount"], index=0,
            format_func=lambda x: {"proportional": "比例仓位（推荐）",
                                   "fixed_shares": "固定股数",
                                   "fixed_amount": "固定金额"}.get(x, x))
        if position_mode == "fixed_amount":
            amount_per_grid = st.number_input("每格交易金额", value=1000.0,
                min_value=1.0, step=100.0, format="%.2f")
        else:
            amount_per_grid = 1000.0

        # ATR止损
        use_atr_stop = st.checkbox("ATR 止损止盈", value=False)
        if use_atr_stop:
            atr_period = st.slider("ATR 周期", min_value=5, max_value=30, value=14)
            atr_stop_mult = st.slider("止损乘数", min_value=0.5, max_value=5.0,
                value=1.5, step=0.1)
            atr_tp_mult = st.slider("止盈乘数", min_value=0.0, max_value=2.0,
                value=0.5, step=0.1)
        else:
            atr_period, atr_stop_mult, atr_tp_mult = 14, 1.5, 0.5

    # ========== 理论洞察 ==========
    with st.sidebar.expander("🧠 香农理论洞察", expanded=False):
        st.markdown("**基于当前配置的理论预期**")
        st.info("💡 数据获取后将显示详细的波动拖累和再平衡溢价分析")
        st.markdown("---")
        st.caption("波动不是风险，而是收益来源——前提是有正确的再平衡机制")

    # ========== 高级设置 ==========
    with st.sidebar.expander("⚙️ 高级设置", expanded=False):
        commission_rate = st.number_input("佣金费率", value=0.0003,
            min_value=0.0, format="%.4f", help="默认0.03%最低5元")
        transfer_fee_rate = st.number_input("过户费费率", value=0.00001,
            min_value=0.0, format="%.5f", help="沪市0.001%")
        stamp_duty_rate = st.number_input("印花税费率", value=0.001,
            min_value=0.0, format="%.4f", help="卖出0.1%")

        # 自动降采样 —— 默认开启
        auto_freq = st.checkbox("自动推荐频率", value=True,
            help="根据时间跨度自动选择最佳 K 线频率")

        if auto_freq:
            recommended = auto_frequency(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
            frequency = st.selectbox("K线频率",
                options=["5", "15", "30", "60", "d", "w", "m"],
                index=["5", "15", "30", "60", "d", "w", "m"].index(recommended),
                format_func=lambda x: {
                    "5": "5分钟", "15": "15分钟", "30": "30分钟",
                    "60": "60分钟", "d": "日线", "w": "周线", "m": "月线"}.get(x, x))

            freq_hint = {"5": "适合 < 1个月", "d": "适合 1月~3年", "w": "适合 > 3年"}.get(recommended, "")
            if freq_hint:
                st.caption(f"💡 自动推荐：{freq_hint}")
        else:
            frequency = st.selectbox("K线频率",
                options=["5", "15", "30", "60", "d", "w", "m"], index=4,  # 默认日线
                format_func=lambda x: {
                    "5": "5分钟", "15": "15分钟", "30": "30分钟",
                    "60": "60分钟", "d": "日线", "w": "周线", "m": "月线"}.get(x, x))

        adjustflag = st.selectbox("复权类型", options=["1", "2", "3"], index=0,  # 默认前复权
            format_func=lambda x: {"1": "前复权", "2": "后复权",
                                   "3": "不复权"}.get(x, x))
        show_quarterly = st.checkbox("季频财务数据", value=False)

        # 本地仓库开关
        use_local_store = st.checkbox("使用本地数据仓库", value=True,
            help="关闭则每次从 API 重新拉取")
        if st.checkbox("📦 查看本地数据概况"):
            try:
                overview = get_data_overview()
                if not overview.empty:
                    st.dataframe(overview, height=150)
                else:
                    st.caption("本地暂无数据")
            except Exception:
                st.caption("数据仓库不可用")

    st.sidebar.write("")
    run_button = st.sidebar.button("▶️ 运行回测", type="primary",
                                   use_container_width=True)

    # 应用预设配置
    if preset != "自定义":
        preset_vals = preset_configs[preset]
        strategy_mode = preset_vals.get("strategy_mode", strategy_mode)
        target_allocation = preset_vals.get("target_allocation", target_allocation)
        rebalance_threshold = preset_vals.get("rebalance_threshold", rebalance_threshold)
        position_mode = preset_vals.get("position_mode", position_mode)
        auto_grid_range = preset_vals.get("auto_grid_range", auto_grid_range)
        grid_spacing_mode = preset_vals.get("grid_spacing_mode", grid_spacing_mode)

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
        total_investment=total_investment,
        auto_grid_range=auto_grid_range,
        grid_range_atr_multiplier=grid_range_mult,
        grid_spacing_mode=grid_spacing_mode,
        strategy_mode=strategy_mode,
        target_allocation=target_allocation,
        rebalance_threshold=rebalance_threshold,
        position_mode=position_mode,
        amount_per_grid=amount_per_grid,
        commission_rate=commission_rate,
        transfer_fee_rate=transfer_fee_rate,
        stamp_duty_rate=stamp_duty_rate,
        data_source=data_source,
        frequency=frequency,
        adjustflag=adjustflag,
        show_quarterly_data=show_quarterly,
        use_atr_stop=use_atr_stop,
        atr_period=atr_period,
        atr_stop_multiplier=atr_stop_mult,
        atr_tp_multiplier=atr_tp_mult,
    )

    return config, run_button, use_local_store


# ========== 主函数 ==========
def main() -> None:
    config, run_button, use_local_store = sidebar_config()

    st.title("📈 GTAP — 香农网格交易回测平台")
    st.markdown("---")

    if not run_button:
        st.info("👈 请在左侧边栏配置参数，然后点击「▶️ 运行回测」")
        return

    # ===== 进度条数据获取 =====
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    progress_placeholder.progress(0, "准备获取数据...")
    status_placeholder.info("正在连接数据源...")

    def streamlit_progress(msg: str, pct: int):
        progress_placeholder.progress(min(pct, 100), msg)
        status_placeholder.info(msg)

    # ===== 数据获取 =====
    streamlit_progress("开始获取数据...", 3)

    try:
        stock_data = get_stock_data(
            code=config.stock_code,
            start_date=config.start_date,
            end_date=config.end_date,
            frequency=config.frequency,
            adjustflag=config.adjustflag,
            show_quarterly=config.show_quarterly_data,
            data_source=config.data_source,
            use_local_store=use_local_store,
            progress_callback=streamlit_progress,
        )
        data = stock_data.kline
    except DataFetchError as e:
        progress_placeholder.empty()
        status_placeholder.error(f"数据获取失败: {e}")
        return
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.error(f"未知错误: {e}")
        return

    if data.empty:
        progress_placeholder.empty()
        status_placeholder.error("未获取到数据，请检查股票代码和日期范围")
        return

    progress_placeholder.empty()
    status_placeholder.success(
        f"✅ 数据就绪：{len(data)} 条记录 "
        f"({data.index[0].strftime('%Y-%m-%d') if hasattr(data.index[0], 'strftime') else str(data.index[0])} "
        f"~ {data.index[-1].strftime('%Y-%m-%d') if hasattr(data.index[-1], 'strftime') else str(data.index[-1])})"
    )

    # ===== ATR 计算 =====
    atr_series = None
    if config.use_atr_stop or config.auto_grid_range:
        with st.spinner("正在计算 ATR 指标..."):
            try:
                atr_series = calculate_atr(data, period=config.atr_period)
                valid_atr = atr_series.dropna()
                if len(valid_atr) > 0:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("当前 ATR", f"{valid_atr.iloc[-1]:.4f}")
                    col2.metric("ATR 均值", f"{valid_atr.mean():.4f}")
                    col3.metric("ATR 最大值", f"{valid_atr.max():.4f}")
            except Exception as e:
                st.warning(f"ATR 计算失败: {e}")
                if config.auto_grid_range:
                    st.error("自动网格范围依赖 ATR，请关闭自动网格范围或确保数据完整")
                    return

    # ===== 香农理论洞察 =====
    st.header("🧠 香农理论洞察")

    with st.spinner("正在计算理论预期..."):
        try:
            insight = calculate_shannon_insight(
                price_data=data["close"],
                grid_upper=config.grid_upper,
                grid_lower=config.grid_lower,
                grid_count=config.grid_number,
                target_allocation=config.target_allocation,
                commission_rate=config.commission_rate,
                rebalance_threshold=config.rebalance_threshold,
            )

            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            col_t1.metric("年化波动率", f"{insight.volatility*100:.1f}%")
            col_t2.metric("波动拖累", f"{insight.volatility_drag*100:.2f}%",
                         help="波动对几何收益的隐性惩罚")
            col_t3.metric("预期再平衡", f"{insight.expected_rebalances}次")
            col_t4.metric("再平衡溢价", f"{insight.rebalancing_premium*100:.2f}%",
                         help="再平衡策略相比买入持有的超额收益")

            col_b1, col_b2, col_b3 = st.columns(3)
            col_b1.metric("📉 买入持有预期", f"{insight.buy_hold_return*100:.1f}%")
            col_b2.metric("📈 再平衡预期", f"{insight.rebalanced_return*100:.1f}%")
            delta_color = "normal" if insight.net_benefit >= 0 else "inverse"
            col_b3.metric("💎 净收益", f"{insight.net_benefit*100:.2f}%",
                         delta=f"{insight.rebalancing_premium*100:.1f}% 溢价 - 成本",
                         delta_color=delta_color)

            if insight.confidence == "高":
                st.success(f"✅ **{insight.recommendation}**")
            elif insight.confidence == "中":
                st.info(f"ℹ️ **{insight.recommendation}**")
            else:
                st.warning(f"⚠️ **{insight.recommendation}**")
        except Exception as e:
            st.warning(f"理论计算暂时不可用: {e}")

    st.markdown("---")

    # ===== 股票数据概览 =====
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

    # ===== 回测 =====
    st.markdown("---")
    st.header("🔁 网格交易回测")

    with st.spinner("正在执行回测..."):
        try:
            result = grid_trading(data, config, atr_series=atr_series)
        except GridTradingError as e:
            st.error(f"回测失败: {e}")
            return

    # ===== 计算买入持有基准 =====
    initial_cash = config.total_investment
    initial_price = data["close"].iloc[0]
    bh_shares = int(initial_cash / initial_price / 100) * 100
    bh_cash = initial_cash - bh_shares * initial_price
    bh_values = [bh_shares * p + bh_cash for p in data["close"]]
    bh_final = bh_values[-1]
    strategy_final = result.asset_values[-1]
    premium_pct = ((strategy_final - bh_final) / initial_cash) * 100

    # ===== 结果展示 (Tab组织) =====
    tab_overview, tab_kline, tab_trades, tab_insight = st.tabs(
        ["📊 总览", "📈 K线图+交易", "📋 交易明细", "🧠 香农解读"])

    with tab_overview:
        # 股票概览 + BH对比 + 关键指标
        latest = data.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("收盘", f"¥{latest['close']:.2f}")
        col2.metric("涨跌幅", f"{(latest['close']/data.iloc[-2]['close']-1)*100:+.2f}%" if len(data)>1 else "N/A")
        col3.metric("BH终值", f"¥{bh_final:,.0f}")
        col4.metric("策略终值", f"¥{strategy_final:,.0f}", delta=f"{premium_pct:+.1f}%")

        st.plotly_chart(fig_asset, width='stretch')

    with tab_kline:
        fig_kline = plot_kline(data, config.stock_code,
                               atr_series=atr_series, trades=result.trades)
        st.plotly_chart(fig_kline, width='stretch')

    with tab_trades:
        st.dataframe(trades_df, width='stretch', height=500)

    with tab_insight:
        # ===== 绩效指标 =====
        st.subheader("📊 绩效指标")

        metrics = calculate_metrics(
            asset_values=result.asset_values,
            trades=result.trades,
            total_fees=result.total_fees,
            start_date=pd.Timestamp(config.start_date),
            end_date=pd.Timestamp(config.end_date),
            trade_profits=result.trade_profits,
        )

        col1, col2, col3, col4 = st.columns(4)
        initial_val = result.asset_values[0] if result.asset_values else 0
        final_val = result.asset_values[-1] if result.asset_values else 0
        col1.metric("初始资产", f"¥{initial_val:,.2f}")
        col2.metric("最终资产", f"¥{final_val:,.2f}")
        col3.metric("总利润（含费）", f"¥{final_val - initial_val:,.2f}")
        col4.metric("总费用", f"¥{result.total_fees:,.2f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("总收益率", f"{metrics['total_return']:.2f}%")
        col2.metric("年化收益率", f"{metrics['annual_return']:.2f}%")
        col3.metric("年化波动率", f"{metrics['annual_volatility']:.2f}%")

        if config.use_atr_stop:
            st.markdown("**🛡️ ATR 动态止损止盈统计**")
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            col_a.metric("止损次数", str(result.stop_loss_count))
            col_b.metric("止盈次数", str(result.take_profit_count))
            col_c.metric("网格交易次数", str(result.grid_trade_count))
            col_d.metric("止损占比", f"{metrics['stop_loss_rate']:.2%}")
            col_e.metric("止盈占比", f"{metrics['take_profit_rate']:.2%}")

        if "rebalance" in config.strategy_mode:
            st.markdown("**⚖️ 再平衡统计**")
            col_r1, col_r2 = st.columns(2)
            col_r1.metric("再平衡次数", str(metrics.get("rebalance_count", 0)))
            col_r2.metric("再平衡溢价", f"{metrics.get('rebalancing_premium', 0):.4f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
        col2.metric("最大回撤", f"{metrics['max_drawdown']:.2f}%")
        col3.metric("胜率", f"{metrics.get('win_rate', 0):.2%}")

        with st.expander("📑 详细指标表"):
            detail_df = pd.DataFrame([metrics])
            st.dataframe(detail_df, width='stretch')

        # ===== 香农解读 =====
        st.markdown("---")
        st.header("📚 本次回测的香农解读")

    try:
        insight = calculate_shannon_insight(
            price_data=data["close"],
            grid_upper=config.grid_upper,
            grid_lower=config.grid_lower,
            grid_count=config.grid_number,
        )

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown("**📊 波动分析**")
            st.write(f"- 年化波动率: **{insight.volatility*100:.1f}%**")
            st.write(f"- 波动拖累: **{insight.volatility_drag*100:.2f}%** (买入持有的隐性损失)")
            st.write(f"- 理论最优仓位: **{insight.optimal_allocation*100:.0f}%** (凯利准则)")

        with col_s2:
            st.markdown("**⚖️ 再平衡效果**")
            actual_premium = metrics.get('rebalancing_premium', 0)
            st.write(f"- 实际再平衡溢价: **{actual_premium:.4f}**")
            st.write(f"- 理论预期溢价: **{insight.rebalancing_premium*100:.2f}%**")
            st.write(f"- 再平衡次数: **{metrics.get('rebalance_count', 0)}** 次")

        st.markdown("**💡 优化建议**")
        if insight.net_benefit > 0.02:
            st.success("当前配置表现优秀！再平衡策略有效捕捉了波动收益。")
        elif insight.net_benefit > 0:
            st.info("当前配置可行。可考虑放宽再平衡阈值以减少交易摩擦。")
        else:
            st.warning("当前配置可能受交易摩擦影响较大。建议：1) 减少网格数量 2) 放宽阈值 3) 或选择更低费率券商")

    except Exception as e:
        st.caption(f"详细解读生成中... ({e})")


if __name__ == "__main__":
    main()