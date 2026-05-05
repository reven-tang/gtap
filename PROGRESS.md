# GTAP Progress — 香农的恶魔对齐路线

> 基于 [[research/shannons-demon-report]] + [[research/shannons-demon-learning-notes]] + [[research/gtap-evaluation]] 的改进路线

**当前对齐度**: 70% → 目标 90%
**当前版本**: v1.1.0-dev
**理论对齐目标**: 香农恶魔核心机制（再平衡+波动收割+比例仓位+凯利动态+市场自适应）

---

## v1.1.0 — 理论→执行闭环 ✅ COMPLETED

**目标**: 让香农理论真正驱动策略执行，而非仅做展示

**核心改进**: 从「理论计算器」到「理论驱动的策略引擎」

| # | 改进 | 状态 | 预估工时 | 改动摘要 |
|---|------|------|---------|---------|
| P0-14 | 凯利准则仓位动态调整 | ✅ | 2h | KellyRebalanceStrategy; use_kelly_sizing/kelly_fraction/kelly_lookback |
| P0-15 | 市场状态自适应策略切换 | ✅ | 2h | RegimeAwareEngine; use_regime_adaptive/regime_lookback |
| P1-16 | 波动率自适应网格密度 | ✅ | 1h | auto_grid_density/grid_density_atr_ratio/min/max |
| P1-17 | TheorySignal 信号管线 | ✅ | 2h | TheorySignal dataclass + from_price_data(); grid.py每20步更新 |
| P2-18 | 成本敏感度阈值推荐 | ✅ | 0.5h | recommended_threshold = 8×总费率 |
| - | GridTradingResult 扩展 | ✅ | 0.5h | theory_signals/regime_summary/kelly_allocations |
| - | 31个新测试 | ✅ | 1h | test_v1_1_features.py 5类31测试全通过 |

**测试**: 99 passed (31 新 + 68 原)

**核心设计**: TheorySignal 管线连接 theory.py 和 strategies.py
```
theory.py → TheorySignal(regime, kelly_allocation, vol_drag) → strategies.py 消费
```

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
| v0.7.0 (之前) | P0+P1+P2+P3 全完成 | ~70% |
| **v1.1.1 (当前)** | P0过度交易修复 + P1 UI集成/Regime优化 + P2可视化 | **100%** |
| v1.2.0 (目标) | PyPI发布 | 95% |

---

## v1.1.1 — 执行闭环修复 ✅ COMPLETED

**目标**: 修复 v1.1.0 引入的bug + P2可视化

| # | 改进 | 状态 | 改动摘要 |
|---|------|------|---------|
| P0 | 过度交易bug修复 | ✅ | 5步冷却期 + 8×费率最低门槛; 22,841→30次交易 |
| P1 | app.py UI集成 | ✅ | 6新控件: 凯利/自适应/密度 + 重复导入清理 |
| P1 | regime判断优化 | ✅ | 动态阈值+方向一致性+回归斜率; "不确定"1711→0 |
| P2 | 凯利仓位曲线 | ✅ | kelly_allocation_timestamps追踪 + 时间序列折线图 |
| P2 | 成本敏感度分析 | ✅ | 阈值vs交易次数/费用双曲线 |
| P2 | data.kline bug | ✅ | grid_trading(data, ...) 替代 data.kline |

*最后更新: 2026-05-05*