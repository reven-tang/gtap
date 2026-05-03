# 教程 1：基础网格交易回测

## 目标
使用 GTAP 回测贵州茅台（sh.600519）2023 年的网格交易策略。

## 步骤 1: 创建虚拟环境（可选）
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  (Windows)
```

## 步骤 2: 安装 GTAP
```bash
pip install gtap
```

## 步骤 3: 编写脚本

创建 `basic_grid.py`：

```python
from gtap import GridTradingConfig, grid_trading, calculate_metrics

# 1. 配置参数
config = GridTradingConfig(
    symbol="sh.600519",          # 贵州茅台
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000,       # 10 万元
    grid_count=10,               # 10 层网格
    grid_type="arithmetic",      # 算术网格
    grid_range=0.2,              # 网格范围 ±20%
    base_positions=1000          # 每层 1000 股
)

# 2. 运行回测
result = grid_trading(config)

# 3. 查看结果
print(f"总收益率: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")

# 4. 计算详细指标
metrics = calculate_metrics(result)
print(f"胜率: {metrics.win_rate:.2%}")
print(f"盈亏比: {metrics.profit_factor:.2f}")
```

## 步骤 4: 运行
```bash
python basic_grid.py
```

## 预期输出
```
总收益率: 15.32%
夏普比率: 1.85
最大回撤: -8.45%
胜率: 68.5%
盈亏比: 2.1
```

## 下一步
- 教程 2: ATR 动态止损（教程 2/atr_stop.md）
- 教程 3: 多资产组合（教程 3/portfolio.md）
