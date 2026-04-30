# GTAP Roadmap

> Grid Trading Analysis Platform - 股票网格交易回测平台演进路线

---

## 📊 项目现状分析

### 核心问题
| 级别 | 问题 | 影响 |
|------|------|------|
| 🔴 致命 | Windows venv 提交到仓库 (`myenv/`) | 仓库臃肿，跨平台不可用 |
| 🔴 致命 | 无 `requirements.txt` | 项目无法安装 |
| 🔴 致命 | `project-structure` 文件内容错误 | 误导维护者 |
| 🟠 严重 | 单文件 655 行巨石架构 | 不可测试、难维护 |
| 🟠 严重 | 无测试覆盖 | 修改风险高 |
| 🟡 中等 | 无错误处理 | API 失败直接崩溃 |
| 🟡 中等 | 硬编码配置 | 无法灵活调整 |

### 代码质量问题
- 函数过长（`get_stock_data` 215 行，`main` 338 行）
- 无类型标注
- 无缓存机制（每次回测都重新拉数据）
- K 线频率固定为 5 分钟
- 网格回测逻辑存在冗余条件判断
- 初始持仓处理不清晰

---

## 🗺️ 版本规划

### v0.1.1 — 紧急修复 ✅ COMPLETED

**目标**: 让项目可以正常 `clone → install → run`

**完成项**:
- ✅ 删除 `myenv/` (Windows venv)
- ✅ 删除错误的 `project-structure*` 文件
- ✅ 创建 `requirements.txt`
- ✅ 创建 `pyproject.toml`
- ✅ 完善 `.gitignore`
- ✅ 重写 `README.md`
- ✅ 创建 `LICENSE` (MIT)
- ✅ 验证 `pip install -r requirements.txt` 成功

**预计工时**: 1-2 小时
**状态**: ✅ 已完成

---

### v0.2.0 — 架构重构 ✅ COMPLETED

**目标**: 模块化、可测试、可维护

**完成项**:
- ✅ 创建 `src/gtap/` 模块化包（7 个核心模块）
- ✅ 添加完整类型标注（Python 3.9 兼容）
- ✅ 修复所有已知 bug（冗余条件、grid_center 逻辑、初始持仓费用）
- ✅ 创建 `tests/` 测试套件（27 个测试，100% 通过）
- ✅ 更新 `pyproject.toml` 为包模式（packages = ["gtap"], package-dir = {"" = "src"}）
- ✅ 创建 `app.py` 新入口（精简 UI，分离关注点）
- ✅ `pip install -e .` 安装成功
- ✅ 所有依赖版本锁定并验证

**核心改进**:
- **config.py**: GridTradingConfig 数据类 + 参数验证 + grid_step 计算
- **data.py**: get_stock_data 统一接口 + K 线频率参数化 + 数据清洗
- **fees.py**: A 股费用计算独立模块（佣金/过户费/印花税）
- **grid.py**: 网格交易引擎，修复 3 个关键 bug，NamedTuple 结果类型
- **metrics.py**: 16 项绩效指标（Sharpe/Sortino/MaxDD/Calmar/盈亏比等）
- **plot.py**: 图表封装（K线/资产曲线/网格线/mplfinance）
- **exceptions.py**: 自定义异常层次（DataFetchError/GridTradingError/ConfigError 等）
- **app.py**: Streamlit 界面，侧边栏配置 + 主区结果展示 + 错误处理

**测试覆盖**:
- test_fees.py: 7 个测试（费用计算边界）
- test_grid.py: 6 个测试（回测逻辑）
- test_config.py: 7 个测试（配置验证）
- test_metrics.py: 7 个测试（指标计算）

**代码质量**: 平均函数长度 < 50 行，所有公共函数带 docstring，类型标注覆盖率 100%。

**预计工时**: 3-5 小时
**实际工时**: 约 4 小时
**状态**: ✅ 已完成

### v0.3.0 — 回测引擎升级 ✅ COMPLETE

**目标**: 回测能力达到专业水平

**完成项**:
- ✅ 引入 ATR 动态止损止盈（atr.py + grid.py 集成）
  - `calculate_atr()`: SMA 风格 ATR 计算
  - `get_atr_stop_levels()`: 止损止盈价位
  - `is_atr_stop_triggered()`: 方向感知触发判断
  - `GridTradingConfig` 扩展 4 个 ATR 参数（默认关闭）
  - `Trade` 扩展 4 个 ATR 字段
  - `GridTradingResult` 扩展 3 个统计
  - 主循环集成 ATR 检查（优先于网格交易，清仓后资产序列继续记录）
- ✅ ATR 单元测试 `tests/test_atr.py`（15 测试，100% 通过）
- ✅ 向后兼容：`use_atr_stop=False` 时行为与 v0.2.0 完全一致
- ✅ 数据与配置解耦（ATR 在 app.py 计算并传入）
- ✅ `metrics.py` 新增 ATR 统计指标（stop_loss_rate/take_profit_rate）
- ✅ `plot.py` 可选绘制 ATR 止损/止盈线 + 触发点标记
- ✅ `app.py` 侧边栏添加 ATR 配置控件 + 统计卡片
- ✅ 集成测试验证（42 测试 100% 通过）
- ✅ `@st.cache_data` 数据缓存启用（TTL=1小时）
- ✅ 测试覆盖率 58%
- ✅ 多个 bug 修复（datetime解析/matplotlib兼容/Streamlit警告）

**里程碑**: [x] v0.3.0 完成

---

### v0.4.0 — 数据源扩展 ✅ COMPLETE

**目标**: 支持更多市场

**完成项**:
- ✅ 数据源抽象层 `src/gtap/providers/`
  - `DataProvider` ABC 基类
  - `BaoStockProvider`: A股（重构现有逻辑）
  - `YFinanceProvider`: 港股/美股/外汇（可选依赖）
  - `AkShareProvider`: A股增强（可选依赖）
  - `get_provider()` 工厂函数
- ✅ 代码标准化 `normalize_code()`
- ✅ `GridTradingConfig` 新增 `data_source` 字段
- ✅ `app.py` 数据源下拉 + 代码格式提示
- ✅ 20 Provider 测试全部通过
- ✅ 可选依赖 yfinance/akshare

**向后兼容**: default source = "baostock"

---

### v0.5.0 — 香农的恶魔对齐 ✅ COMPLETE

**目标**: 修复数据正确性缺陷 + 实现再平衡策略核心

**理论依据**: [[research/shannons-demon-report]] + [[research/shannons-demon-learning-notes]] + [[research/gtap-evaluation]]

**当前对齐度**: 30% → **70%** (全部P0-P3完成)

#### P0 — 数据正确性（必须立即修复）

| # | 改进 | 状态 | 预估 |
|---|------|------|------|
| 1 | 移除 `current_holding_price`，自动从起始日收盘价获取 | ✅ | 0.5h |
| 2 | `grid_center` 默认 = 起始日收盘价（保留手动覆盖） | ✅ | 0.3h |
| 3 | 网格范围基于 ATR 自动建议 | ✅ | 1.5h |

#### P1 — 策略核心（高优先级）

| # | 改进 | 状态 | 预估 |
|---|------|------|------|
| 4 | 再平衡策略模式（threshold/periodic） | ✅ | 3h |
| 5 | 比例仓位管理（fixed_shares/amount/proportional） | ✅ | 2h |
| 6 | 等比网格间距（arithmetic/geometric） | ✅ | 1h |
| 7 | 合并 trade_metrics 到主指标函数 | ✅ | 0.5h |

#### P0 实施细节

**P0-1: 移除手动购入价**
```python
# config.py: 移除 current_holding_price 字段
# grid.py: 自动获取 entry_price = float(data.iloc[0]['close'])
# app.py: 移除侧边栏"当前持仓价格"输入框
# 验证: 所有测试更新，确保不再依赖手动购入价
```

**P0-2: 网格中心自动计算**
```python
# config.py: grid_center 默认改为 None（自动模式）
# grid.py: grid_center = config.grid_center or entry_price
# app.py: 显示"自动计算（起始日收盘价）"标签
```

**P0-3: ATR 自动网格范围**
```python
# config.py: 新增 auto_grid_range: bool = True
#              新增 grid_range_atr_multiplier: float = 2.0
# grid.py: if auto_grid_range: 基于 ATR 计算 grid_upper/grid_lower
# app.py: "网格范围" 区增加 自动/手动 切换
```

#### P1 实施细节

**P1-4: 再平衡策略模式**
```python
# config.py: 新增 rebalance_mode: Literal["grid", "threshold", "periodic"]
#              新增 target_allocation: float = 0.5
#              新增 rebalance_threshold: float = 0.05
# grid.py: 新增 RebalanceStrategy 逻辑分支
# 测试: 新增 test_rebalance.py
```

**P1-5: 比例仓位**
```python
# config.py: 新增 position_mode: Literal["fixed_shares", "fixed_amount", "proportional"]
# grid.py: 根据 position_mode 计算交易数量
```

**P1-6: 等比网格**
```python
# config.py: 新增 grid_spacing_mode: Literal["arithmetic", "geometric", "atr_dynamic"]
# grid.py: 根据模式生成 grid_prices
```

**P1-7: 合并指标**
```python
# metrics.py: calculate_metrics() 调用 calculate_trade_metrics()
#             新增 rebalancing_premium, volatility_drag 指标
```

**预计总工时**: 10h
**优先级**: ✅ 全部完成
**状态**: ✅ 已完成

---

### v0.6.0 — UI重构 + 策略完善 ✅ COMPLETE

**目标**: 用户体验提升 + 策略连续性

**理论依据**: [[research/gtap-evaluation]] P2

**当前对齐度**: 50% → 目标 70%

| # | 改进 | 预估 |
|---|------|------|
| 8 | 侧边栏3组expander重构 | ✅ | 2h |
| 9 | 清仓后50%现金重建仓 | ✅ | 1h |
| 10 | rebalance_count/rebalancing_premium | ✅ | 1h |

**预计工时**: 4h
**优先级**: 📋 中

---

### v0.7.0 — 策略引擎抽象 + 多资产 ✅ COMPLETE

**目标**: 真正的香农的恶魔实现

**理论依据**: [[research/gtap-evaluation]] P3

**当前对齐度**: 70% → 目标 80%

| # | 改进 | 预估 |
|---|------|------|
| 11 | StrategyEngine ABC + GridStrategy + RebalanceStrategy + 工厂 | ✅ | 2h |
| 12 | PortfolioConfig + portfolio_backtest + 跨资产相关性 | ✅ | 3h |
| 13 | ParrondoConfig + 4种混合模式 + 网格关联分析 | ✅ | 2h |

**预计工时**: 8h+
**优先级**: 🎯 远期

---

### v1.0.0 — 正式发布

**目标**: PyPI 可安装，生产就绪

**任务清单**:
- [ ] 完善 API 文档（Sphinx + ReadTheDocs）
- [ ] 编写用户指南 + 教程
- [ ] Docker 镜像支持
- [ ] PyPI 发布 (`twine upload`)
- [ ] 更新 CHANGELOG.md
- [ ] 准备 1.0 宣传材料

**预计工时**: 2-3 小时
**优先级**: 🎯 远期

---

## 🎯 实施建议

### 优先级策略
```
本周: v0.1.1 ✅ 已完成
下周: v0.2.0 架构重构（模块化 + 类型标注）
一个月内: v0.3.0 回测升级（止损止盈 + Sharpe）
三个月: v0.4.0 多数据源 + v0.5.0 测试
半年: v1.0.0 正式发布
```

### 并行策略
- **主线**: v0.2.0 → v0.3.0 → v0.4.0 → v0.5.0 → v1.0.0
- **并行**: 在 v0.2.0 重构时，可以同步研究 defiplot 的 ATR 实现（资料调研）

### 风险提示
1. **baostock 数据质量**: 需验证数据连续性、复权处理
2. **回测偏差**: 5 分钟频率未考虑滑点、冲击成本
3. **未来函数**: 网格中心动态调整可能引入前视偏差
4. **幸存者偏差**: 仅使用历史存活股票回测会高估收益

---

## 📈 里程碑检查点

- [x] v0.1.1: 文件清理完成，`pip install -r requirements.txt` 成功
- [x] v0.2.0: `pytest` 27/27 通过（100%），模块化架构完成
- [x] v0.3.0: ATR 动态止损止盈完成
- [x] v0.4.0: 数据源抽象层 + 3 Provider 实现
- [x] v0.5.0: P0-P3 全完成，98测试通过，对齐度70%
- [ ] v1.0.0: PyPI 发布成功

---

*最后更新: 2026-04-30*
*维护者: reven-tang / 萨莉 (OpenClaw Assistant)*
