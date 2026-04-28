"""
图表绘制模块 - GTAP 网格交易回测平台

封装 K线图、资产曲线、网格线等可视化逻辑。
"""

from typing import TYPE_CHECKING, Optional
import plotly.graph_objects as go
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from .data import StockData
    from .grid import GridTradingResult, Trade


def plot_kline(
    data: pd.DataFrame,
    stock_code: str,
    atr_series: Optional[pd.Series] = None,
    trades: Optional[list] = None,
) -> go.Figure:
    """
    绘制交互式 K 线图（含均线 + 可选 ATR 止损/止盈参考线）。

    Args:
        data: 价格数据（索引为 datetime，包含 open/high/low/close/volume）
        stock_code: 股票代码（用于标题）
        atr_series: ATR 值序列（与 data 索引对齐），可选
        trades: 交易记录列表（Trade NamedTuple），可选，用于标注止损/止盈触发点

    Returns:
        Plotly Figure 对象
    """
    if data.empty:
        raise ValueError("数据为空，无法绘图")

    # 计算均线
    data = data.copy()
    data["MA5"] = data["close"].rolling(window=5).mean()
    data["MA10"] = data["close"].rolling(window=10).mean()
    data["MA20"] = data["close"].rolling(window=20).mean()

    fig = go.Figure()

    # K 线
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="K线",
        )
    )

    # 均线
    fig.add_trace(go.Scatter(x=data.index, y=data["MA5"], name="MA5", line=dict(color="blue", width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data["MA10"], name="MA10", line=dict(color="orange", width=1)))
    fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20", line=dict(color="green", width=1)))

    # ATR 曲线（次坐标轴，可选）
    if atr_series is not None and len(atr_series) > 0:
        # 对齐数据索引
        atr_aligned = atr_series.reindex(data.index)
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=atr_aligned,
                name="ATR",
                line=dict(color="purple", width=1, dash="dash"),
                yaxis="y3",
                opacity=0.7,
            )
        )

    # 止损/止盈触发点标注（可选）
    if trades is not None:
        stop_loss_times = []
        stop_loss_prices = []
        take_profit_times = []
        take_profit_prices = []
        for t in trades:
            reason = getattr(t, "exit_reason", "grid")
            if reason == "stop_loss":
                stop_loss_times.append(t.timestamp)
                stop_loss_prices.append(t.price)
            elif reason == "take_profit":
                take_profit_times.append(t.timestamp)
                take_profit_prices.append(t.price)
        if stop_loss_times:
            fig.add_trace(
                go.Scatter(
                    x=stop_loss_times,
                    y=stop_loss_prices,
                    mode="markers",
                    name="止损触发",
                    marker=dict(symbol="triangle-down", size=12, color="red", line=dict(width=1, color="darkred")),
                    yaxis="y",
                )
            )
        if take_profit_times:
            fig.add_trace(
                go.Scatter(
                    x=take_profit_times,
                    y=take_profit_prices,
                    mode="markers",
                    name="止盈触发",
                    marker=dict(symbol="triangle-up", size=12, color="green", line=dict(width=1, color="darkgreen")),
                    yaxis="y",
                )
            )

    # 成交量（次坐标轴）
    fig.add_trace(
        go.Bar(x=data.index, y=data["volume"], name="成交量", yaxis="y2", visible="legendonly")
    )

    fig.update_layout(
        title=f"{stock_code} K线图",
        yaxis_title="价格",
        xaxis_rangeslider_visible=True,
        height=800,
        dragmode="zoom",
        # yaxis: 左侧主坐标轴（价格）
        yaxis=dict(title="价格", domain=[0.3, 1]),
        # yaxis2: 右侧坐标轴（ATR 曲线）
        yaxis2=dict(title="ATR", overlaying="y", side="right", showgrid=False, domain=[0.3, 1]),
        # yaxis3: 底部坐标轴（成交量）
        yaxis3=dict(title="成交量", overlaying="x", side="bottom", showgrid=False, domain=[0, 0.2]),
        xaxis_rangeslider=dict(visible=True, yaxis=dict(rangemode="auto")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # 成交量使用 yaxis3（底部坐标轴）
    # 已在 add_trace 中指定 yaxis="y3"

    return fig


def plot_asset_curve(data_index: pd.DatetimeIndex, asset_values: list[float]) -> go.Figure:
    """
    绘制资产价值变化曲线。

    Args:
        data_index: 时间索引
        asset_values: 资产价值序列

    Returns:
        Plotly Figure 对象
    """
    if len(data_index) != len(asset_values):
        raise ValueError("时间索引与资产价值长度不一致")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data_index, y=asset_values, mode="lines", name="资产价值"))
    fig.update_layout(title="资产价值变化", xaxis_title="时间", yaxis_title="资产价值（元）")
    return fig


def plot_grid_lines(
    data_index: pd.DatetimeIndex,
    close_prices: list[float],
    grid_prices: list[float],
    trades: list,
) -> go.Figure:
    """
    绘制带有网格买卖点的 K 线图。

    Args:
        data_index: 时间索引
        close_prices: 收盘价序列
        grid_prices: 网格价格线列表
        trades: 交易记录列表

    Returns:
        Plotly Figure 对象
    """
    fig = go.Figure()

    # 收盘价线
    fig.add_trace(go.Scatter(x=data_index, y=close_prices, mode="lines", name="收盘价", line=dict(color="black", width=1)))

    # 网格线（水平线）
    for gp in grid_prices:
        fig.add_hline(y=gp, line_dash="dash", line_color="gray", opacity=0.5)

    # 标注买卖点
    buy_times = [t.timestamp for t in trades if t.action == "买入"]
    buy_prices = [t.price for t in trades if t.action == "买入"]
    sell_times = [t.timestamp for t in trades if t.action == "卖出"]
    sell_prices = [t.price for t in trades if t.action == "卖出"]

    if buy_times:
        fig.add_trace(
            go.Scatter(
                x=buy_times,
                y=buy_prices,
                mode="markers",
                name="买入",
                marker=dict(symbol="triangle-up", size=10, color="green"),
            )
        )

    if sell_times:
        fig.add_trace(
            go.Scatter(
                x=sell_times,
                y=sell_prices,
                mode="markers",
                name="卖出",
                marker=dict(symbol="triangle-down", size=10, color="red"),
            )
        )

    fig.update_layout(
        title="网格交易买卖点",
        xaxis_title="时间",
        yaxis_title="价格",
        showlegend=True,
    )
    return fig


def plot_mplfinance(data: pd.DataFrame, stock_code: str, grid_prices: Optional[list[float]] = None):
    """
    使用 mplfinance 绘制静态 K 线图（可用于保存图片）。

    Args:
        data: OHLCV 数据
        stock_code: 股票代码
        grid_prices: 可选网格线价格列表
    """
    if data.empty:
        raise ValueError("数据为空，无法绘图")

    # mplfinance 需要特定列名
    plot_data = data[["open", "high", "low", "close", "volume"]].copy()
    plot_data.index.name = "Date"

    # 准备附加线
    apds = []
    if "MA5" in data.columns:
        apds.append(mpf.make_addplot(data["MA5"], color="blue"))
    if "MA10" in data.columns:
        apds.append(mpf.make_addplot(data["MA10"], color="orange"))
    if "MA20" in data.columns:
        apds.append(mpf.make_addplot(data["MA20"], color="green"))

    # 网格线（水平线）
    if grid_prices:
        for gp in grid_prices:
            apds.append(mpf.make_addplot([gp] * len(data), color="gray", linestyle="--", alpha=0.5))

    mpf.plot(
        plot_data,
        type="candle",
        volume=True,
        addplot=apds if apds else None,
        title=f"{stock_code} - K线图",
        style="yahoo",
        figratio=(16, 9),
        figscale=1.2,
    )
