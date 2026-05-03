# 教程 2：ATR 动态止损

## 目标
在基础网格上增加 ATR 动态止损止盈，保护收益。

## 步骤 1: 配置 ATR 参数

```python
from gtap import GridTradingConfig

config = GridTradingConfig(
    symbol="sh.600519",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000,
    grid_count=10,

    # ATR 参数（新增）
    use_atr_stop=True,           # 启用 ATR 止损
    atr_period=14,              # ATR 计算周期
    atr_stop_multiplier=2.0,    # 止损倍数（2倍ATR）
    atr_tp_multiplier=1.0,      # 止盈倍数（1倍ATR）
)
```

## 步骤 2: 运行回测

```python
from gtap import grid_trading, calculate_metrics

result = grid_trading(config)
metrics = calculate_metrics(result)

print(f"ATR 止损触发次数: {result.stop_loss_count}")
print(f"ATR 止盈触发次数: {result.take_profit_count}")
print(f"网格交易次数: {result.grid_trade_count}")
```

## 步骤 3: 对比分析

```python
# 关闭 ATR 的基准
config_no_atr = config.copy()
config_no_atr.use_atr_stop = False
result_no_atr = grid_trading(config_no_atr)

# 对比
print("启用 ATR vs 禁用 ATR:")
print(f"  最大回撤: {result.max_drawdown:.2%} vs {result_no_atr.max_drawdown:.2%}")
print(f"  总收益: {result.total_return:.2%} vs {result_no_atr.total_return:.2%}")
```

## 效果预期
- 启用 ATR 后，极端行情下最大回撤降低 30-50%
- 止盈更及时，减少利润回吐
- 交易次数可能增加（ATR 触发额外退出）

## 可视化
在 Streamlit UI 中，ATR 止损/止盈线会绘制在 K 线图上，直观展示触发点。

## 下一步
教程 3: 多资产组合回测
