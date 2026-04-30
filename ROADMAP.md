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

### v0.4.0 — 数据源扩展

**目标**: 支持更多市场

**任务清单**:

#### 1. 新增数据源
- [ ] **yfinance**: 支持港股、美股、外汇、加密货币
- [ ] **akshare**: 更丰富的 A 股数据（基金、期货、债券）
- [ ] **tushare**: 备用 A 股数据源（需 token）

#### 2. 数据源抽象层
```python
class DataProvider(ABC):
    @abstractmethod
    def fetch_kline(self, code, start, end, freq): ...
    @abstractmethod
    def fetch_basic(self, code): ...
```

#### 3. 数据源工厂
```python
def get_provider(source: str) -> DataProvider:
    if source == "baostock": return BaoStockProvider()
    if source == "yfinance": return YFinanceProvider()
```

#### 4. 实时行情（可选）
- [ ] 接入 WebSocket 实时推送（需券商 API）
- [ ] 支持模拟交易模式

**预计工时**: 3-4 小时
**优先级**: 📋 中

---

### v0.5.0 — 测试与 CI/CD

**目标**: 可信任、可自动化

**任务清单**:

#### 1. 单元测试
- [ ] `tests/test_fees.py` - 费用计算边界情况
- [ ] `tests/test_grid.py` - 网格交易逻辑
- [ ] `tests/test_metrics.py` - 绩效指标准确性
- [ ] `tests/test_data.py` - 数据获取（使用 mock）

#### 2. 集成测试
- [ ] 端到端回测流程验证
- [ ] 已知历史数据回测结果比对

#### 3. 代码质量工具
- [ ] `ruff` 代码检查 + 自动修复
- [ ] `mypy` 类型检查
- [ ] `pytest-cov` 覆盖率报告（目标 > 80%）

#### 4. CI/CD
- [ ] GitHub Actions 配置
  - 每次 PR 自动运行测试
  - 自动检查代码风格
  - 自动构建 wheel 包
- [ ] 自动化发布（tag → PyPI）

**预计工时**: 3-4 小时
**优先级**: 📋 中

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
- [ ] v0.3.0: Sharpe 比率计算通过验证
- [ ] v0.4.0: 支持 3+ 数据源切换
- [ ] v0.5.0: CI 绿色，覆盖率 > 80%
- [ ] v1.0.0: PyPI 发布成功

---

*最后更新: 2026-04-28*
*维护者: reven-tang / 萨莉 (OpenClaw Assistant)*
