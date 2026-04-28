# GTAP Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
