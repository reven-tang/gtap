# GTAP Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-04-28 (开发中)

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

### Changed 变更
- 🔄 `grid_trading()` 签名：新增可选参数 `atr_series: Optional[pd.Series]`
- 🔄 普通网格卖出 `Trade` 记录补充 ATR 字段（向后兼容填充默认值）
- 🔄 返回 `GridTradingResult` 时包含 ATR 统计字段

### Fixed 修复
- 🔧 matplotlib 3.8.2 在 Python 3.14/macOS 上编译失败（freetype 2.6.1 兼容性问题），升级至 3.10.9
- 🔧 pandas 3.x 日期解析严格化修复：`time` 字段为 8 位数字 (YYYYMMDD) 时，旧代码拼接为 `"2024-01-02 20240102"` 导致 to_datetime 失败。`data.py` 新增智能检测（8位数字 → 仅用 date 字段；否则 → 合并 date + time 前8位）
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
