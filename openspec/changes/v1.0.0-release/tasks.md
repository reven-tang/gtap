# Tasks: GTAP v1.0.0 发布准备

## 任务总览

| 阶段 | 任务数 | 预计总工时 | 状态 |
|------|--------|-----------|------|
| Phase 1: 文档 | 3 | 5h | ⏳ |
| Phase 2: 打包 | 2 | 2h | ⏳ |
| Phase 3: 测试补充 | 2 | 2h | ⏳ |
| Phase 4: 发布脚本 | 2 | 1h | ⏳ |
| **总计** | **9** | **10h** | **0%** |

---

## Phase 1: 文档建设（5h）

### Task 1.1: Sphinx 文档框架搭建
**优先级**: P0
**预估工时**: 2h
**验收标准**:
- [ ] **GWT-01**: Given 开发者已安装依赖，When 运行 `sphinx-build -b html docs/ docs/_build`，Then 命令返回 0 且无警告
- [ ] **GWT-02**: Given 已配置 `.readthedocs.yaml`，When 推送到 main 分支，Then ReadTheDocs 自动构建成功
- [ ] **GWT-03**: Given 访问文档站点，When 点击首页链接，Then 可正常跳转到 API 参考和用户指南

**子任务（垂直切片）**:
1. 创建 `docs/conf.py`（从 sphinx-quickstart 生成 + 定制）
2. 编写 `docs/index.rst`（3 节：介绍、安装、快速开始）
3. 配置 autodoc 自动提取 gtap 模块 docstring
4. 配置 myst-parser 支持 Markdown 文件（USER_GUIDE.md）
5. 本地构建验证（clean + build）

**文件路径**:
- 新建: `docs/conf.py`, `docs/index.rst`, `.readthedocs.yaml`
- 修改: `pyproject.toml`（添加 docs 可选依赖）

**测试**:
- 无需单元测试，但需手动验证 `make html` 成功

---

### Task 1.2: 用户指南编写
**优先级**: P0
**预估工时**: 2h
**验收标准**:
- [ ] `docs/guide/` 目录创建
- [ ] `USER_GUIDE.md` 包含 5 大章节（安装、配置、使用、参数说明、故障排除）
- [ ] 每个功能点配 Screenshot（Streamlit 界面截图）
- [ ] 常见问题 ≥10 条
- [ ] 中英文版本（`USER_GUIDE.md` + `USER_GUIDE.en.md`）

**子任务**:
1. 安装指南（pip/源码/Docker 三种方式）
2. 配置详解（所有 GridTradingConfig 参数）
3. 策略选择指南（网格/再平衡/混合）
4. 性能指标解读（Sharpe/Sortino/最大回撤）
5. 故障排除（数据源问题、回测异常、性能优化）

**依赖**: Task 1.1 完成（Sphinx 框架就绪）

---

### Task 1.3: 教程编写
**优先级**: P1
**预估工时**: 1h
**验收标准**:
- [ ] `docs/tutorial/` 目录创建
- [ ] `TUTORIAL.md` 包含 3 个渐进式示例（基础网格 → ATR 止损 → 多资产）
- [ ] 每个示例可复制粘贴直接运行
- [ ] 示例输出截图（图表 + 指标）

**子任务**:
1. 教程 1：单股票基础网格（5 分钟 K 线，沪深300）
2. 教程 2：ATR 动态止损（实时保护）
3. 教程 3：多资产组合回测（Portfolio + 相关性）

---

## Phase 2: 打包准备（2h）

### Task 2.1: PyPI 发布配置
**优先级**: P0
**预估工时**: 1h
**验收标准**:
- [ ] **GWT-01**: Given 已配置 `pyproject.toml`，When 运行 `python -m build`，Then 成功生成 sdist 和 wheel 文件
- [ ] **GWT-02**: Given 已生成分发包，When 运行 `twine check dist/*`，Then 返回 "PASSED" 无错误
- [ ] **GWT-03**: Given 已填写 `.pypirc`，When 运行 `twine upload --repository testpypi`，Then 包成功上传到 TestPyPI

**子任务**:
1. 完善 `pyproject.toml` project 表（添加 keywords/classifiers/urls）
2. 创建 `scripts/.pypirc.template`（供用户填写 token）
3. 本地构建验证（确保无 .pyc 等无关文件打包）
4. 测试 `twine upload --repository testpypi`（dry-run）

**文件路径**:
- 修改: `pyproject.toml`
- 新建: `scripts/.pypirc.template`

---

### Task 2.2: Docker 镜像
**优先级**: P0
**预估工时**: 1h
**验收标准**:
- [ ] **GWT-01**: Given 已创建 Dockerfile，When 运行 `docker build -t gtap:1.0.0 .`，Then 镜像大小 < 500MB
- [ ] **GWT-02**: Given 已创建 docker-compose.yml，When 运行 `docker-compose up -d`，Then 容器状态为 "healthy"
- [ ] **GWT-03**: Given 容器已运行，When 访问 `http://localhost:8501`，Then Streamlit 界面正常加载

**子任务**:
1. 编写 Dockerfile（安装依赖 + 复制代码 + 暴露端口）
2. 编写 docker-compose.yml（服务定义 + 卷映射）
3. 构建镜像并测试大小（`docker images`）
4. 运行容器并验证 UI 可访问

**文件路径**:
- 新建: `Dockerfile`, `docker-compose.yml`, `.dockerignore`

---

## Phase 3: 测试补充（2h）

### Task 3.1: 覆盖率提升至 90%
**优先级**: P0
**预估工时**: 1.5h
**验收标准**:
- [ ] 新增测试 ≥ 10 个
- [ ] 核心模块覆盖率：grid.py ≥ 90%，metrics.py ≥ 90%
- [ ] 运行 `pytest --cov=gtap --cov-report=html` 生成报告
- [ ] 覆盖率报告提交到 `docs/coverage/`（可选）

**目标模块**:
- `grid.py`: 补充边界条件测试（空数据、单条记录、极端价格）
- `metrics.py`: 补充夏普比率、最大回撤计算测试
- `data.py`: 补充数据清洗测试（停牌处理、复权）

**测试文件**:
- `tests/test_grid_edge_cases.py`（新建）
- `tests/test_metrics_precision.py`（新建）

---

### Task 3.2: 文档构建测试
**优先级**: P1
**预估工时**: 0.5h
**验收标准**:
- [ ] 新增 GitHub Actions 工作流 `.github/workflows/docs.yml`
- [ ] 每次 PR 自动构建文档
- [ ] Sphinx 警告数为 0

**子任务**:
1. 创建 docs.yml（安装依赖 + sphinx-build）
2. 配置 ReadTheDocs 自动触发
3. 本地验证 GitHub Actions 语法（act 或推送到测试分支）

---

## Phase 4: 发布脚本（1h）

### Task 4.1: 发布自动化脚本
**优先级**: P0
**预估工时**: 0.5h
**验收标准**:
- [ ] `scripts/publish.sh` 可执行，包含以下步骤：
  1. 版本检查（确认 git 干净）
  2. 运行测试（pytest）
  3. 构建分发包（python -m build）
  4. 检查包（twine check）
  5. 上传 TestPyPI（dry-run 可选）
  6. 上传 PyPI（需要确认）
  7. 打标签（git tag v1.0.0）
  8. 推送到 GitHub（git push --tags）
- [ ] 脚本有 dry-run 模式（`--dry-run` 参数）
- [ ] 脚本有 help 说明

**依赖**: Task 2.1 完成（PyPI 配置就绪）

---

### Task 4.2: CHANGELOG 更新
**优先级**: P0
**预估工时**: 0.5h
**验收标准**:
- [ ] CHANGELOG.md 新增 `## [1.0.0] — YYYY-MM-DD` 章节
- [ ] 包含新增、变更、修复分类
- [ ] 列出所有 v0.7.0 → v1.0.0 的新功能
- [ ] 鸣谢贡献者（如有）

**内容来源**:
- 从 git log 提取 commit 消息（自 v0.7.0 标签之后）
- 汇总 6 个发布任务的完成情况

---

## 门禁检查（所有任务完成前）

- [ ] 9 个任务全部标记完成
- [ ] 测试覆盖率 ≥ 90%
- [ ] Sphinx 构建无警告
- [ ] Docker 镜像 < 500MB
- [ ] PyPI 发布脚本 dry-run 通过
- [ ] CHANGELOG 更新完整

---

## 相关技能触发

| 任务 | 推荐技能 |
|------|----------|
| 文档编写 | `writing-skills` |
| 测试补充 | `test-driven-development` |
| Docker 构建 | 通用 DevOps |
| 发布流程 | `gstack-ship` + `gstack-land-deploy` |

---

## Milestone 分组

**M1 - Documentation** (Sprint 1): Task 1.1~1.3 完成，文档框架 + 用户指南 + 教程就绪
**M2 - Packaging** (Sprint 2): Task 2.1~2.2 完成，PyPI 配置 + Docker 镜像就绪
**M3 - Quality** (Sprint 3): Task 3.1~3.2 完成，覆盖率 ≥90% + 文档构建测试通过
**M4 - Release** (Sprint 4): Task 4.1~4.2 完成，发布脚本 + CHANGELOG 更新，v1.0.0 可发布

---

**创建时间**: 2026-05-03
**预计完成**: 10 工时（可分 2 天）
**阻塞依赖**: 无（可并行）
