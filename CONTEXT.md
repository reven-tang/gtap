# GTAP 领域术语表（CONTEXT.md）

> 共享语言，减少 AI 沟通成本。Matt Pocock 模式：用 1 个词代替 20 个词的描述。

## 核心概念

| 术语 | 含义 | 一句话 |
|:--|:--|:--|
| 香农再平衡 | Shannon's Demon 再平衡策略 | 定期调整现金/股票比例以收割波动收益 |
| 网格交易 (grid) | 价格区间内均匀下单 | 高频小幅再平衡，适合震荡市 |
| 阈值再平衡 (rebalance_threshold) | 仓位偏离超过 X% 再调整 | 低频大幅再平衡，适合趋势市 |
| 波动拖累 (volatility drag) | σ²/2，波动对收益的侵蚀 | 波动越大，几何收益越低于算术收益 |
| 再平衡溢价 (rebalancing premium) | 再平衡的超额收益 | 再平衡收益 - BH 收益，香农理论核心 |
| BH | Buy and Hold，买入持有 | 不进行任何调整的基准策略 |
| ATR | Average True Range，平均真实波幅 | 用于计算网格间距和阈值的波动指标 |
| Parrondo 效应 | 两个负期望策略组合产生正收益 | 网格 + 阈值组合可能优于单独使用 |

## 项目架构

| 术语 | 含义 |
|:--|:--|
| Streamlit | Web UI 框架 |
| DuckDB | 本地列式数据仓库 |
| BaoStock | A 股数据源 |
| providers/ | 多数据源适配层 |
| store.py | DuckDB 存储层 |

## 股票代码格式

| 格式 | 含义 |
|:--|:--|
| sh.600958 | 上交所东方证券 |
| sh.600000 | 上交所浦发银行 |
| sh.601398 | 上交所工商银行 |

## GTAP 定义

- Grid Trading Analysis Platform
- 基于香农理论的网格交易回测和策略优化工具
- 核心价值：用数据验证"再平衡能否创造超额收益"
