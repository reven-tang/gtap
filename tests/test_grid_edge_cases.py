"""Test grid_trading edge cases - using correct GTAP API (final)."""
import pytest
import pandas as pd
from gtap import (
    GridTradingConfig, grid_trading, get_stock_data,
    GridTradingError, ConfigError, calculate_metrics
)

def test_basic_grid_backtest():
    """基础网格交易回测应成功。"""
    data = get_stock_data(
        code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        frequency="d"
    )
    config = GridTradingConfig(
        stock_code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        grid_upper=120.0,
        grid_lower=100.0,
        grid_number=5,
        total_investment=100000,
        shares_per_grid=100,
        grid_spacing_mode="arithmetic",
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    assert result is not None
    assert result.asset_values[-1] > 0

def test_geometric_grid_backtest():
    """等比网格应正常执行。"""
    data = get_stock_data(
        code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        frequency="d"
    )
    config = GridTradingConfig(
        stock_code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        grid_upper=120.0,
        grid_lower=100.0,
        grid_number=5,
        total_investment=100000,
        grid_spacing_mode="geometric",
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    assert result is not None

def test_atr_stop_backtest():
    """ATR 止损应正常执行。"""
    data = get_stock_data(
        code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        frequency="d"
    )
    config = GridTradingConfig(
        stock_code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        grid_upper=120.0,
        grid_lower=100.0,
        grid_number=5,
        total_investment=100000,
        use_atr_stop=True,
        atr_period=14,
        atr_stop_multiplier=2.0,
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    assert result is not None
    assert hasattr(result, 'stop_loss_count')
    assert hasattr(result, 'take_profit_count')

def test_config_invalid_grid_number():
    """grid_number < 2 应被配置验证拦截。"""
    with pytest.raises(ConfigError):
        GridTradingConfig(
            stock_code="sh.600519",
            start_date="2023-01-01",
            end_date="2023-01-31",
            grid_upper=120.0,
            grid_lower=100.0,
            grid_number=1
        )

def test_config_invalid_investment():
    """负投资额应被拦截。"""
    with pytest.raises(ConfigError):
        GridTradingConfig(
            stock_code="sh.600519",
            start_date="2023-01-01",
            end_date="2023-01-31",
            grid_upper=120.0,
            grid_lower=100.0,
            total_investment=-10000
        )

def test_config_invalid_grid_range():
    """grid_upper <= grid_lower 应被拦截（auto_grid_range=False）。"""
    with pytest.raises(ConfigError):
        GridTradingConfig(
            stock_code="sh.600519",
            start_date="2023-01-01",
            end_date="2023-01-31",
            grid_upper=100.0,
            grid_lower=120.0,
            grid_number=5,
            auto_grid_range=False
        )

def test_metrics_calculation_from_result():
    """calculate_metrics 应能从 grid_trading 结果计算指标（返回 dict）。"""
    data = get_stock_data(
        code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        frequency="d"
    )
    config = GridTradingConfig(
        stock_code="sh.600519",
        start_date="2023-01-01",
        end_date="2023-01-31",
        grid_upper=120.0,
        grid_lower=100.0,
        grid_number=5,
        total_investment=100000,
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    metrics = calculate_metrics(
        asset_values=result.asset_values,
        trades=result.trades,
        total_fees=result.total_fees,
        start_date=pd.Timestamp(config.start_date),
        end_date=pd.Timestamp(config.end_date),
        trade_profits=result.trade_profits
    )
    # calculate_metrics 返回 dict，验证关键字段存在
    assert isinstance(metrics, dict)
    required_keys = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
    for key in required_keys:
        assert key in metrics, f"Missing key: {key}"
    # 值范围（profit_factor 允许为 0，极端情况无盈利交易）
    assert -1 <= metrics['max_drawdown'] <= 0
    assert 0 <= metrics['win_rate'] <= 1
    assert metrics['profit_factor'] >= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
