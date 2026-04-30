## [0.5.1] — 2026-04-30

### Added 新增
- ✅ P0: 数据正确性修复（购入价自动获取、grid_center自动、ATR自动网格范围）
- ✅ P1-4: 再平衡策略模式（threshold/periodic）
- ✅ P1-5: 比例仓位管理（fixed_shares/fixed_amount/proportional）
- ✅ P1-6: 等比网格间距（arithmetic/geometric）
- ✅ P1-7: 合并 trade_metrics 到主指标函数（trade_profits 参数传入）
- ✅ P2-8: 侧边栏重构为3组expander（基础设置/交易策略/高级设置）
- ✅ P2-9: 清仓后50%现金重建仓逻辑（exit_reason="reentry"）
- ✅ P2-10: 再平衡溢价指标（rebalance_count/rebalancing_premium）
- ✅ P3-11: 策略引擎抽象（StrategyEngine ABC + GridStrategy + RebalanceStrategy + 工厂）
- ✅ P3-12: 多资产组合回测（PortfolioConfig + portfolio_backtest + 跨资产相关性）
- ✅ P3-13: Parrondo悖论模拟（4种混合模式 + 网格关联分析）
- ✅ PortfolioError 异常类
- ✅ README.md 重写：香农网格交易法深度解读 + 计算公式 + 术语表 + 使用指南

### Fixed 修复
- 🔧 auto_grid_range 模式下 ATR 未自动计算（条件改为 use_atr_stop OR auto_grid_range）

### Changed 变更
- 🔄 侧边栏新增策略模式、间距模式、仓位模式控件
- 🔄 GridTradingConfig 新增 strategy_mode/target_allocation/rebalance_threshold/position_mode/grid_spacing_mode/amount_per_grid
- 🔄 PerformanceMetrics 新增 rebalance_count/rebalancing_premium

### Stats 统计
- 测试: 98 passed (新增 14 Portfolio/Parrondo + 16 Strategies)
- 对齐度: 30% → 70%
- 新增模块: portfolio.py, parrondo.py, strategies.py
- 新增测试: test_portfolio_parrondo.py, test_strategies.py

# GTAP Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-04-30

### Added 新增
- ✅ ruff lint 集成（代码风格检查）
- ✅ mypy type check（类型检查通过）
- ✅ pytest-cov 覆盖率报告
- ✅ 新增测试 17 个（总计 70 个）
  - 网格交易集成测试（ATR 止损/止盈、多网格跨越、资金不足等边界）
  - 配置边界测试（ATR 参数、数据源字段）
  - 指标计算测试（ATR 交易统计）

### Changed 变更
- 🔄 代码风格统一（ruff auto-fix）
- 🔄 类型标注完善（mypy 0 errors）

### Fixed 修复
- 🔧 移除未使用变量（`initial_investment`, `avg_atr_at_entry`, `lg`）
- 🔧 `__init__.py` 添加 `available_providers` 到 `__all__`

### Stats 统计
- 测试通过率: 69/70 (98.6%)
- 代码覆盖率: 65% (核心模块 90%+)
- ruff: 0 errors
- mypy: 0 errors

---

## [0.4.0] — 2026-04-30

### Added 新增
- ✅ 数据源抽象层 `src/gtap/providers/`
  - `DataProvider` ABC 抽象基类（fetch_kline/fetch_dividend/fetch_basic/normalize_code）
  - `BaoStockProvider`: A 股沪市/深市数据，重构现有 baostock 逻辑
  - `YFinanceProvider`: 港股/美股/外汇/加密货币数据（可选依赖）
  - `AkShareProvider`: A 股增强数据（基金/期货/债券）（可选依赖）
  - `get_provider()`: 数据源工厂函数
  - `available_providers()`: 查询当前可用数据源
- ✅ 代码标准化：每个 Provider 实现 normalize_code() 转换
  - BaoStock: "601398" → "sh.601398"
  - YFinance: "sh.601398" → "601398.SS"
  - AkShare: "sh.601398" → "601398"
- ✅ `GridTradingConfig` 新增 `data_source` 字段（默认 "baostock"）
- ✅ `data.py` 重构：get_stock_data 内部使用 DataProvider 抽象层
- ✅ `app.py` 侧边栏数据源下拉选择 + 代码格式提示
- ✅ Provider 测试 `tests/test_providers.py`（20 测试，100% 通过）
- ✅ 可选依赖：yfinance>=0.2.31, akshare>=1.12.0

### Changed 变更
- 🔄 `get_stock_data()` 新增 `data_source` 参数（默认 "baostock"，向后兼容）
- 🔄 `__init__.py` 导出新增 DataProvider/get_provider/available_providers

### Fixed 修复
- 🔧 可选数据源 import 失败时给出明确安装提示

---

## [0.3.0] — 2026-04-30

### Added 新增
- ✅ ATR 动态止损止盈模块 `src/gtap/atr.py`
  - `calculate_atr()`: SMA 风格 ATR 计算（前 period-1 个值为 NaN）
  - `get_atr_stop_levels()`: 止损止盈价位计算
  - `is_atr_stop_triggered()`: 持仓方向感知的触发判断（多头/空头）
- ✅ `GridTradingConfig` 新增 4 个 ATR 参数
  - `use_atr_stop` (默认 False，向后兼容)
  - `atr_period` (默认 14)
  - `atr_stop_multiplier` (默认 1.5)
  - `atr_tp_multiplier` (默认 0.5)
- ✅ `Trade` NamedTuple 扩展 4 个 ATR 字段
  - `atr_value`, `stop_loss_price`, `take_profit_price`, `exit_reason`
- ✅ `GridTradingResult` 扩展 3 个统计字段
  - `stop_loss_count`, `take_profit_count`, `grid_trade_count`
- ✅ ATR 单元测试 `tests/test_atr.py`（15 测试，100% 通过）
- ✅ `grid.py` 主循环集成 ATR 检查（优先于网格交易）
- ✅ 清仓后资产序列继续记录现金价值（不提前终止）
- ✅ `metrics.py` 新增 ATR 统计指标（stop_loss_rate/take_profit_rate/avg_atr_at_entry）
- ✅ `plot.py` 可选绘制 ATR 止损/止盈线 + 触发点标记
- ✅ `app.py` 侧边栏 ATR 配置控件 + ATR 统计卡片展示
- ✅ `@st.cache_data` 数据缓存（TTL=1小时）

### Changed 变更
- 🔄 `grid_trading()` 签名：新增可选参数 `atr_series: Optional[pd.Series]`
- 🔄 普通网格卖出 `Trade` 记录补充 ATR 字段（向后兼容填充默认值）
- 🔄 `app.py` 添加缓存包装器 fetch_stock_data
- 🔄 返回 `GridTradingResult` 时包含 ATR 统计字段

### Fixed 修复
- 🔧 matplotlib 3.8.2 在 Python 3.14/macOS 上编译失败（freetype 2.6.1 兼容性问题），升级至 3.10.9
- 🔧 pandas 3.x 日期解析严格化修复：baostock 日线 `time` 字段可能返回 `"20240102000000"`（14位数字，旧检查 `len==8` 漏掉此情况），导致拼接出 `"2024-01-02 20240102"` 无法解析。改为向量化正则 `^\d+$` 检测任意长度纯数字 + `numpy.where` + `format="mixed"` 彻底解决
- 🔧 依赖版本升级：streamlit 1.39.0→1.57.0, numpy 1.26.4→2.4.4, pandas 2.2.3→3.0.2, baostock 0.8.9→0.9.1

### Known Issues 已知问题
- ⚠️ `@st.cache_data` 缓存尚未启用
- ⚠️ `app.py` 侧边栏 ATR 控件尚未添加
- ⚠️ `plot.py` ATR 止损/止盈线绘制未实现
- ⚠️ 测试覆盖率未统计（计划 pytest-cov）

---

## [0.2.0] — 2026-04-28

### Added 新增
- ✅ 模块化架构：`src/gtap/` 包（7 个核心模块）
  - `config.py`: GridTradingConfig 配置类，参数验证
  - `data.py`: get_stock_data 统一数据获取接口
  - `fees.py`: A 股交易费用计算（佣金/过户费/印花税）
  - `grid.py`: 网格交易回测引擎
  - `metrics.py`: 16 项绩效指标计算
  - `plot.py`: K线/资产曲线/网格线图表封装
  - `exceptions.py`: 自定义异常层次
  - `__init__.py`: 公共 API 导出
- ✅ 全新 Streamlit 入口 `app.py`（侧边栏配置 + 主区展示）
- ✅ 测试套件 `tests/`（27 个测试，100% 通过）
  - `test_config.py`: 7 测试（配置验证）
  - `test_fees.py`: 7 测试（费用计算）
  - `test_grid.py`: 6 测试（回测逻辑）
  - `test_metrics.py`: 7 测试（指标计算）
- ✅ 类型标注全覆盖（Python 3.9 兼容 Optional 语法）
- ✅ 完整 docstring（Google 风格）
- ✅ K 线频率参数化（5/15/30/60 分钟 + 日/周/月）
- ✅ 复权类型可选（前复权/后复权/不复权）

### Fixed 修复
- 🔧 修复冗余条件判断 `price < lower and price < lower`
- 🔧 修复 `grid_center` 更新逻辑混乱（买入向上、卖出向下）
- 🔧 修复初始持仓费用未计算问题
- 🔧 修复资产价值序列提前终止（清仓逻辑优化）

### Changed 变更
- 📦 `pyproject.toml` 切换为包模式（`packages = ["gtap"]`, `package-dir = {"" = "src"}`）
- 📦 依赖版本统一锁定（requirements.txt 与 pyproject.toml 一致）
- 🎨 UI 优化：侧边栏分组、加载状态、错误提示

### Removed 移除
- ❌ 删除 `myenv/` (Windows venv，约 3MB)
- ❌ 删除 `project-structure` 错误文件
- ❌ 删除 `project-structure-update` 错误文件

### Known Issues 已知问题
- ⚠️ `@st.cache_data` 缓存尚未启用（v0.3.0 前添加）
- ⚠️ 数据源仅支持 baostock（v0.4.0 扩展 yfinance/akshare）
- ⚠️ ATR 动态止损未实现（v0.3.0 引入）
- ⚠️ 测试覆盖率未统计（v0.5.0 集成 pytest-cov）

---

## [0.1.1] — 2026-04-28

### Added 新增
- ✅ `requirements.txt`（7 个固定版本依赖）
- ✅ `pyproject.toml`（项目元数据 + 构建配置）
- ✅ `LICENSE`（MIT License）
- ✅ `ROADMAP.md`（完整版本路线图）
- ✅ `.gitignore` 补充（标准 Python 规则 + myenv/）

### Changed 变更
- 📝 `README.md` 重写：中文规范 + 三平台虚拟环境安装指导
- 📝 README 安装章节结构化（前置条件 → 两种安装方式 → 常见问题）

### Removed 移除
- ❌ 清理误提交文件（myenv/, project-structure*）

---

## [0.1.0] — 原始版本

- 📦 初始发布：单文件 `gtap.py`（655 行）
- 🎯 功能：网格交易回测 + K线图 + 财务数据
- ⚠️ 问题：巨石架构、无测试、无类型标注
