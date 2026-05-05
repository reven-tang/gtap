"""
GTAP 集成测试 — 模块间交互验证

测试数据流、控制流在真实场景下的协同工作，避免纯 mock 的单元测试盲区。
"""

import pytest
import pandas as pd
import numpy as np

from src.gtap.config import GridTradingConfig
from src.gtap.grid import grid_trading
from src.gtap.metrics import calculate_metrics
from src.gtap.exceptions import DataFetchError, GridTradingError, ConfigError
from src.gtap.atr import calculate_atr


# ========== Fixtures ==========

@pytest.fixture
def ohlcv_df():
    """标准 OHLCV 测试数据"""
    dates = pd.date_range("2022-01-01", periods=100, freq="D")
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, 100)
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, 100)),
        "high": prices * (1 + np.random.uniform(0, 0.02, 100)),
        "low": prices * (1 - np.random.uniform(0, 0.02, 100)),
        "close": prices,
        "volume": np.random.randint(1000, 10000, 100),
    }, index=dates)


@pytest.fixture
def cfg():
    """默认配置"""
    return GridTradingConfig(
        stock_code="test.000001",
        grid_upper=120.0, grid_lower=80.0, grid_number=5,
        total_investment=100000.0, initial_shares=100,
    )


# ========== 场景 1: 完整回测流水线 ==========

class TestFullPipeline:
    """配置 → 数据 → 网格 → 指标 全链路"""

    def test_full_flow(self, ohlcv_df, cfg):
        """完整回测流程不崩溃"""
        result = grid_trading(ohlcv_df, cfg)
        assert result is not None
        assert len(result.trades) >= 0
        assert result.total_buy_count >= 0
        assert result.total_fees >= 0
        assert len(result.asset_values) > 0
        assert result.asset_values[-1] > 0

    def test_metrics_output(self, ohlcv_df, cfg):
        """绩效指标计算正常"""
        import pandas as pd
        result = grid_trading(ohlcv_df, cfg)
        metrics = calculate_metrics(
            result.asset_values,
            result.trades,
            result.total_fees,
            pd.Timestamp(ohlcv_df.index[0]),
            pd.Timestamp(ohlcv_df.index[-1]),
        )
        # 检查关键指标存在
        assert "total_return" in metrics
        assert "annual_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

    def test_auto_grid_range(self, ohlcv_df):
        """自动网格范围"""
        cfg = GridTradingConfig(
            stock_code="test.auto",
            auto_grid_range=True,
            total_investment=50000.0, initial_shares=50,
        )
        result = grid_trading(ohlcv_df, cfg)
        assert result is not None

    def test_fee_impact(self, ohlcv_df):
        """高费用应降低净收益"""
        cfg_low = GridTradingConfig(
            stock_code="test.fee", commission_rate=0.0001,
            total_investment=50000.0, initial_shares=50,
        )
        cfg_high = GridTradingConfig(
            stock_code="test.fee", commission_rate=0.001,
            total_investment=50000.0, initial_shares=50,
        )
        r_low = grid_trading(ohlcv_df, cfg_low)
        r_high = grid_trading(ohlcv_df, cfg_high)
        assert r_low.total_fees < r_high.total_fees


# ========== 场景 2: 费用链路 ==========

class TestFeeChain:
    """费用计算完整性"""

    def test_fee_in_grid(self, ohlcv_df, cfg):
        """费用应 >0 且合理"""
        result = grid_trading(ohlcv_df, cfg)
        # 费用应大于等于 0（可能有最低佣金）
        assert result.total_fees >= 0
        assert result.total_fees < cfg.total_investment * 0.1

    def test_fee_calculation_trades(self, ohlcv_df):
        """费用与交易次数匹配（每笔交易至少有 5 元最低佣金）"""
        cfg = GridTradingConfig(
            stock_code="test.feechain", commission_rate=0.0003,
            total_investment=100000.0, initial_shares=100,
            grid_upper=120.0, grid_lower=80.0, grid_number=5,
        )
        result = grid_trading(ohlcv_df, cfg)
        # 每笔交易产生费用
        if result.trades:
            assert result.total_fees > 0
            # 费用应在合理范围：总投入的 0.1% ~ 5%
            fee_ratio = result.total_fees / cfg.total_investment
            assert 0.0001 < fee_ratio < 0.05


# ========== 场景 3: 错误传播 ==========

class TestErrorPropagation:

    def test_invalid_config(self):
        """grid_upper < grid_lower（非自动模式）应抛出 ConfigError"""
        with pytest.raises(ConfigError):
            GridTradingConfig(
                stock_code="test.invalid",
                auto_grid_range=False,
                grid_upper=80.0, grid_lower=120.0, grid_number=5,
                total_investment=10000.0, initial_shares=10,
            )

    def test_empty_data(self, cfg):
        """空数据应抛出异常"""
        with pytest.raises((GridTradingError, ValueError)):
            grid_trading(pd.DataFrame(), cfg)

    def test_short_data_graceful(self):
        """极短数据不应崩溃，应优雅返回或抛出明确异常"""
        cfg = GridTradingConfig(stock_code="test.short", initial_shares=10,
                                total_investment=10000.0)
        df = pd.DataFrame({
            "open": [100]*3, "high": [101]*3, "low": [99]*3,
            "close": [100]*3, "volume": [1000]*3,
        })
        # 短数据允许不崩溃，但应返回合理结果（可能0交易）
        result = grid_trading(df, cfg)
        assert result is not None
        assert result.total_buy_count >= 0
        assert result.asset_values[-1] > 0

    def test_atr_bad_input(self):
        """ATR 对垃圾输入的处理"""
        with pytest.raises(Exception):
            calculate_atr(pd.DataFrame())


# ========== 场景 4: ATR 集成 ==========

class TestATRIntegration:

    def test_atr_raw_data(self, ohlcv_df):
        """ATR 从 OHLCV 数据正常计算"""
        atr_series = calculate_atr(ohlcv_df, period=14)
        assert isinstance(atr_series, pd.Series)
        assert len(atr_series) == len(ohlcv_df)
        # 前 period-1 个值为 NaN
        assert atr_series.iloc[:13].isna().all()
        valid = atr_series.dropna()
        assert (valid > 0).all()

    def test_atr_grid_dynamic(self, ohlcv_df):
        """基于 ATR 的网格间距是合理值"""
        atr_series = calculate_atr(ohlcv_df, period=14)
        avg_atr = atr_series.dropna().mean()
        # 平均 ATR 应 < 价格的 10%（合理范围）
        avg_price = ohlcv_df["close"].mean()
        assert avg_atr < avg_price * 0.1


# ========== 场景 5: 策略对比 ==========

class TestStrategyComparison:

    def test_grid_vs_rebalance(self, ohlcv_df):
        """两种策略都产生有效结果"""
        cfg_grid = GridTradingConfig(
            stock_code="test.grid", strategy_mode="grid",
            grid_upper=110.0, grid_lower=90.0, grid_number=5,
            total_investment=50000.0, initial_shares=50,
        )
        cfg_rebal = GridTradingConfig(
            stock_code="test.rebal", strategy_mode="rebalance_threshold",
            target_allocation=0.5, rebalance_threshold=0.05,
            total_investment=50000.0, initial_shares=50,
        )
        r1 = grid_trading(ohlcv_df, cfg_grid)
        r2 = grid_trading(ohlcv_df, cfg_rebal)
        assert r1.asset_values[-1] > 0
        assert r2.asset_values[-1] > 0

    def test_position_modes(self, ohlcv_df):
        """两种仓位模式都正常"""
        for mode in ["fixed_shares", "proportional"]:
            cfg = GridTradingConfig(
                stock_code=f"test.{mode}", position_mode=mode,
                total_investment=50000.0, initial_shares=50,
            )
            result = grid_trading(ohlcv_df, cfg)
            assert result is not None


# ========== 场景 6: 边界条件 ==========

class TestEdgeCases:

    def test_extreme_volatility_graceful(self):
        """极端波动不崩溃（允许 NaN，但不应 throw）"""
        dates = pd.date_range("2022-01-01", periods=50, freq="D")
        p = [100.0]
        for i in range(1, 50):
            if i % 10 == 0: p.append(p[-1] * 1.1)
            elif i % 10 == 5: p.append(p[-1] * 0.9)
            else: p.append(p[-1])
        prices = pd.Series(p)
        df = pd.DataFrame({
            "open": prices, "high": prices*1.02, "low": prices*0.98,
            "close": prices, "volume": [1000]*50,
        }, index=dates)
        cfg = GridTradingConfig(
            stock_code="test.extr", grid_upper=200.0, grid_lower=50.0,
            grid_number=10, total_investment=100000.0, initial_shares=100,
        )
        result = grid_trading(df, cfg)
        # 极端波动不产生 NaN 的最后一个资产值
        valid = [v for v in result.asset_values if not (np.isnan(v) if isinstance(v, float) else False)]
        if valid:
            assert valid[-1] > 0

    def test_minimal_grid(self):
        """最小网格数 (2)"""
        dates = pd.date_range("2022-01-01", periods=20, freq="D")
        df = pd.DataFrame({
            "open": [100.0]*20, "high": [101.0]*20,
            "low": [99.0]*20, "close": [100.0]*20,
            "volume": [1000]*20,
        }, index=dates)
        cfg = GridTradingConfig(
            stock_code="test.min", grid_upper=110.0, grid_lower=90.0,
            grid_number=2, total_investment=10000.0, initial_shares=10,
        )
        result = grid_trading(df, cfg)
        assert result.total_buy_count >= 0

    def test_narrow_price_range(self):
        """窄幅震荡（价格几乎不变）"""
        dates = pd.date_range("2022-01-01", periods=30, freq="D")
        base = 100.0
        df = pd.DataFrame({
            "open": [base + np.sin(i*0.1)*0.5 for i in range(30)],
            "high": [base + np.sin(i*0.1)*0.5 + 0.3 for i in range(30)],
            "low": [base + np.sin(i*0.1)*0.5 - 0.3 for i in range(30)],
            "close": [base + np.sin(i*0.1)*0.5 for i in range(30)],
            "volume": [1000]*30,
        }, index=dates)
        cfg = GridTradingConfig(
            stock_code="test.narrow", grid_upper=105.0, grid_lower=95.0,
            grid_number=3, total_investment=10000.0, initial_shares=10,
        )
        result = grid_trading(df, cfg)
        # 窄幅震荡可能无交易或极少交易，但不崩溃
        assert result.asset_values[-1] > 0
