# Proposal: GTAP v1.0.0 正式发布

## Why (为什么)

GTAP 已完成 v0.7.0，核心功能稳定（141 测试通过，模块化架构，香农理论对齐度 70%）。现在是发布 v1.0.0 的最佳时机：
- 核心网格交易引擎经过充分验证
- 策略抽象层支持多种模式（grid/threshold/periodic）
- 数据源抽象完善（BaoStock/YFinance/AkShare）
- 用户界面可用的 Streamlit 版本已就绪

v1.0.0 将标志着**第一个生产可用版本**，可在 PyPI 安装并实际使用。

## What Changes (变什么)

### 发布准备（6 项任务）
| # | 任务 | 产出 | 预估工时 |
|---|------|------|----------|
| 1 | API 文档（Sphinx + ReadTheDocs） | docs/ + readthedocs 配置 | 2h |
| 2 | 用户指南 + 教程（中英） | USER_GUIDE.md + TUTORIAL.md | 2h |
| 3 | Docker 镜像支持 | Dockerfile + docker-compose.yml | 1h |
| 4 | PyPI 发布流程脚本 | scripts/publish.sh + .pypirc | 1h |
| 5 | CHANGELOG v1.0.0 条目 | CHANGELOG.md 更新 | 0.5h |
| 6 | v1.0 宣传材料（截图/要点） | docs/1.0-announcement.md | 0.5h |

### 质量门禁
- 测试覆盖率 ≥ 90% (当前 65% → 需补充)
- Sphinx 构建无警告
- Docker 镜像大小 < 500MB
- PyPI 元数据完整（description/long_description/classifiers）

## Success Criteria (成功标准)

**硬性标准（必须全部满足）**：
1. ✅ `pip install gtap` 成功
2. ✅ `python -m gtap --help` 显示帮助信息
3. ✅ 示例脚本运行（`examples/basic_grid.py`）不报错
4. ✅ 文档站点（ReadTheDocs）可访问
5. ✅ Docker 镜像 `ghcr.io/yourname/gtap:1.0.0` 可 pull 并运行
6. ✅ CHANGELOG.md 包含 v1.0.0 条目

**软性标准（尽量满足）**：
- 用户指南覆盖 80% 常见用例
- 宣传材料包含 3 个以上截图

## Cost of Inaction (不做代价)

如果 v1.0.0 推迟：
- 用户仍需要手动安装（非 pip install）
- 无标准化文档，学习成本高
- 无法 Docker 一键部署
- 项目可见度低（未上 PyPI）

---

## 相关链接

- ROADMAP.md: v1.0.0 里程碑
- CHANGELOG.md: 当前最新 v0.8.1
- README.md: 项目入口

---

**创建时间**: 2026-05-03
**作者**: OpenClaw AI Orchestrator
**状态**: DRAFT → 等待审查
