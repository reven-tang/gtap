# GTAP Progress — 香农的恶魔对齐路线

> 基于 [[research/shannons-demon-report]] + [[research/shannons-demon-learning-notes]] + [[research/gtap-evaluation]] 的改进路线

**当前对齐度**: 30% → 目标 80%
**当前版本**: v0.7.0
**理论对齐目标**: 香农的恶魔核心机制（再平衡+波动收割+比例仓位）

---

## P0 — 数据正确性 ✅ 全部完成

| # | 改进 | 状态 | 完成时间 | 改动摘要 |
|---|------|------|---------|---------|
| P0-1 | 移除 `current_holding_price`，自动从起始日收盘价获取 | ✅ | 2026-04-30 | config.py 删除字段; grid.py 自动获取 `entry_price`; app.py 移除输入框 |
| P0-2 | `grid_center` 默认 = 起始日收盘价 | ✅ | 2026-04-30 | config.py `Optional[float]=None`; app.py 增加"手动设定"开关 |
| P0-3 | 网格范围基于 ATR 自动建议 | ✅ | 2026-04-30 | config.py 新增 `auto_grid_range` + `grid_range_atr_multiplier`; grid.py ATR 自动计算上下限; app.py 增加"自动网格范围"开关 |

**测试**: 49 passed (新增 3 个 P0 专项测试)

---

## P1 — 策略核心 ✅ P1-4/5/6 已完成

| # | 改进 | 状态 | 预估工时 | 改动摘要 |
|---|------|------|---------|---------|
| P1-4 | 新增再平衡策略模式（threshold/periodic） | ✅ | 3h | config.py 新增 strategy_mode/target_allocation; grid.py 实现阈值再平衡逻辑 |
| P1-5 | 比例仓位管理（替代固定股数） | ✅ | 2h | config.py 新增 position_mode/amount_per_grid; grid.py 支持 fixed_shares/fixed_amount/proportional |
| P1-6 | 等比网格间距选项（geometric/atr_dynamic） | ✅ | 1h | config.py 新增 grid_spacing_mode; grid.py 支持 arithmetic/geometric |
| P1-7 | 合并 trade_metrics 到主指标函数 | ✅ | 0.5h | metrics.py 加 trade_profits 参数; app.py 传入 result.trade_profits |

---

## P2 — 用户体验 ⏳ 部分完成

| # | 改进 | 状态 | 预估工时 | 改动摘要 |
|---|------|------|---------|---------|
| P2-8 | 重构侧边栏分组（按用户意图分组） | ✅ | 2h | 3 组 expander: 基础设置/交易策略/高级设置 |
| P2-9 | 清仓后重新建仓逻辑 | ✅ | 1h | grid.py 清仓后 price∈范围时用50%现金重建仓 |
| P2-10 | 新增再平衡溢价指标 | ✅ | 1h | metrics.py 新增 rebalance_count/rebalancing_premium |

---

## P3 — 扩展能力

| # | 改进 | 状态 | 预估工时 |
|---|------|------|---------|
| P3-11 | 策略引擎抽象化（StrategyEngine ABC） | ✅ | 3h | strategies.py 新增 ABC + GridStrategy + RebalanceStrategy + create_strategy 工厂 |
| P3-12 | 多资产组合支持 | ✅ | 5h | portfolio.py 组合回测+相关性+再平衡溢价; exceptions.py 新增 PortfolioError |
| P3-13 | Parrondo's Paradox 探索 | ✅ | 研究 | parrondo.py 模拟+网格关联分析; 4种混合模式(alternating/random/a_only/b_only) |

---

## 对齐度追踪

| 版本 | 完成项 | 对齐度 |
|------|--------|--------|
| v0.4.0 (之前) | 基础网格+ATR+3数据源 | 30% |
| v0.7.0 (当前) | P0+P1+P2+P3 全完成 | ~70% |
| v0.5.0 (目标) | +P3-12 | 70% |
| v0.6.0 (目标) | +P2 | 70% |
| v0.7.0 (目标) | +P3 | 80% |

---

*最后更新: 2026-04-30 21:50*