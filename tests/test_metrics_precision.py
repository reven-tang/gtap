"""Test metrics calculation using actual grid_trading result."""
import pytest
from gtap import GridTradingConfig, grid_trading, get_stock_data, calculate_metrics

def test_metrics_from_real_backtest():
    """calculate_metrics 应能计算真实回测的指标。"""
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
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    metrics = calculate_metrics(result)

    # 字段存在
    assert hasattr(metrics, 'total_return')
    assert hasattr(metrics, 'sharpe_ratio')
    assert hasattr(metrics, 'max_drawdown')
    assert hasattr(metrics, 'win_rate')
    assert hasattr(metrics, 'profit_factor')

    # 值范围合理
    assert isinstance(metrics.total_return, float)
    assert -1 <= metrics.max_drawdown <= 0
    assert 0 <= metrics.win_rate <= 1
    assert metrics.profit_factor > 0

def test_metrics_with_atr_stop():
    """启用 ATR 止损的指标计算。"""
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
        auto_grid_range=False
    )
    result = grid_trading(data.kline, config)
    metrics = calculate_metrics(result)
    assert hasattr(metrics, 'stop_loss_rate')
    assert hasattr(metrics, 'take_profit_rate')
    assert 0 <= metrics.stop_loss_rate <= 1
    assert 0 <= metrics.take_profit_rate <= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
