# 教程 3：多资产组合回测

## 目标
使用 GTAP 回测多只股票，分析组合收益和相关性。

## 步骤 1: 配置组合

```python
from gtap import PortfolioConfig, portfolio_backtest

config = PortfolioConfig(
    symbols=["sh.600519", "sz.000001", "sh.600036"],  # 茅台、平安银行、招商银行
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=300000,          # 30 万，每只 10 万
    allocation_mode="equal",         # 等权分配
    grid_count=8,                    # 每只股票 8 层网格
    use_correlation=True,            # 启用相关性风控
    correlation_threshold=0.7        # 相关性 >0.7 时减少仓位
)
```

## 步骤 2: 运行组合回测

```python
result = portfolio_backtest(config)

print(f"组合总收益: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")

# 各资产明细
for asset in result.assets:
    print(f"  {asset.symbol}: {asset.return:.2%} (权重 {asset.weight:.0%})")
```

## 步骤 3: 相关性分析

```python
# 查看相关性矩阵
corr_matrix = result.correlation_matrix
print("资产相关性矩阵:")
print(corr_matrix)

# 再平衡溢价
print(f"再平衡次数: {result.rebalance_count}")
print(f"再平衡贡献收益: {result.rebalancing_premium:.2%}")
```

## 步骤 4: 对比单资产 vs 组合

```python
from gtap import GridTradingConfig, grid_trading

# 单资产（只持茅台）
single = grid_trading(GridTradingConfig(
    symbol="sh.600519",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000
))

print(f"单资产收益: {single.total_return:.2%}")
print(f"组合收益: {result.total_return:.2%}")
print(f"分散化提升: {result.total_return - single.total_return:.2%}")
```

## 效果预期
- 组合波动率低于单资产（diversification benefit）
- 再平衡贡献额外收益（0.5-2%）
- 相关性风控避免同涨同跌

## 注意事项
- 数据源需支持多股票（BaoStock 免费，YFinance 需安装）
- 回测时间 ≈ 单资产 × 资产数量（可并行加速）
