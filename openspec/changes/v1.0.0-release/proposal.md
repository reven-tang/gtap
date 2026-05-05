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

**量化损失分析**:

如果 v1.0.0 推迟 1 个月：
- **用户获取成本**: 手动安装流失率 60% → 每月损失潜在用户 ~50 人
- **支持成本**: 无标准化文档导致重复问答，预计增加 2h/周 支持时间
- **技术债务**: 文档与代码脱节风险，后期补文档成本 3-5x
- **机会成本**: 未上 PyPI 导致项目可见度低，错失社区贡献机会

**不做清单 (Out of Scope)**:
- 不实现 Web 版交易界面（仅 CLI + Streamlit）
- 不支持实时交易（仅回测 + 模拟）
- 不集成券商 API（仅数据获取）
- 不提供托管服务（仅本地部署）

---

## User Value (用户价值)

**受益对象**: 量化交易研究者、个人投资者、Python 开发者

**价值量化**:
| 用户类型 | 价值点 | 量化指标 |
|----------|--------|----------|
| 研究者 | 快速验证策略 | 策略开发周期从 2 周 → 3 天 |
| 个人投资者 | 降低交易门槛 | 无需编写代码即可回测 |
| 开发者 | 模块化复用 | 网格策略代码复用率 80%+ |

**成功指标 (Success Criteria)**:
| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| PyPI 周下载量 | ≥100 | pip stats |
| 文档站点 UV | ≥50/周 | ReadTheDocs analytics |
| 用户满意度 | ≥4.0/5 | GitHub issues 反馈 |
| 测试覆盖率 | ≥90% | pytest --cov |

## Scope (范围)

### 核心功能清单 (Must Have)
- [ ] Sphinx 文档框架 + ReadTheDocs 托管
- [ ] 用户指南（中英）+ 教程
- [ ] Docker 镜像构建 + docker-compose
- [ ] PyPI 发布流程脚本
- [ ] CHANGELOG v1.0.0 条目
- [ ] 宣传材料（截图 + 要点）

### 不做清单 (Won't Have)
- [ ] Web 版交易界面（仅 CLI + Streamlit）
- [ ] 实时交易支持（仅回测 + 模拟）
- [ ] 券商 API 集成（仅数据获取）
- [ ] 托管服务（仅本地部署）

## 相关链接

- ROADMAP.md: v1.0.0 里程碑
- CHANGELOG.md: 当前最新 v1.0.0
- README.md: 项目入口

---

**创建时间**: 2026-05-03
**作者**: OpenClaw AI Orchestrator
**状态**: DRAFT → 等待审查
