# Design: GTAP v1.0.0 发布技术方案

## Architecture (架构)

### 发布包结构
```
gtap-1.0.0/
├── gtap/                    # Python 包（已存在）
│   ├── __init__.py         # 公共 API 导出
│   ├── config.py           # 配置类
│   ├── data.py             # 数据获取
│   ├── grid.py             # 网格引擎
│   ├── metrics.py          # 指标计算
│   ├── plot.py             # 图表
│   ├── fees.py             # 费用计算
│   ├── exceptions.py       # 异常
│   ├── providers/          # 数据源抽象
│   └── theory.py           # 香农理论
├── docs/                   # Sphinx 文档（新增）
│   ├── conf.py            # Sphinx 配置
│   ├── index.rst          # 首页
│   ├── api/               # API 参考（autodoc）
│   ├── guide/             # 用户指南
│   ├── tutorial/          # 教程
│   └── 1.0-announcement.md # 发布公告
├── scripts/               # 发布脚本（新增）
│   ├── publish.sh        # PyPI 发布流程
│   ├── build-docs.sh     # 文档构建
│   └── build-docker.sh   # Docker 构建
├── examples/              # 示例脚本（已有）
├── Dockerfile            # Docker 镜像定义（新增）
├── docker-compose.yml    # 编排文件（新增）
├── .readthedocs.yaml     # ReadTheDocs 配置（新增）
├── pyproject.toml        # 项目配置（已有，需增强）
└── CHANGELOG.md          # 更新 v1.0.0 条目
```

### 依赖关系
```
Sphinx 文档 ← 源码 docstring + examples/
Docker 镜像 ← Python + gtap 包 + 系统依赖
PyPI 发布 ← 源码分发包 (sdist + wheel)
```

---

## API Design

### 命令行接口
```bash
# 安装
pip install gtap

# Streamlit 界面
streamlit run gtap/app.py

# 模块化 API
python -c "from gtap import GridTradingConfig, grid_trading; print(grid_trading(...))"
```

### Python API（已存在，无需改动）
```python
from gtap import (
    GridTradingConfig,
    get_stock_data,
    grid_trading,
    calculate_metrics,
    plot_results
)
```

### 配置参数（向后兼容）
所有 v0.7.0 配置字段保持不变，新增：
- `docs_path`: 文档输出目录（可选）
- `publish_metadata`: PyPI 发布元数据（可选）

---

## Data Model

无需修改数据模型，保持 v0.7.0 向后兼容。

---

## Dependencies (依赖)

### 运行时依赖（requirements.txt）
已有 7 个核心依赖：
- streamlit
- pandas
- numpy
- matplotlib
- baostock
- plotly
- mplfinance

### 文档依赖（新增）
```
sphinx>=7.0
sphinx-rtd-theme>=2.0
sphinx-autodoc-typehints>=2.0
myst-parser>=2.0  # Markdown 支持
```

### 发布依赖（新增）
```
build>=1.0  # python -m build
twine>=5.0  # PyPI 上传
docker>=7.0 # 镜像构建（可选）
```

### 可选依赖
- yfinance, akshare（已有，可选）
- pytest, pytest-cov（测试，已配置）

---

## Dependencies 管理策略

**策略**: 分离依赖组，避免发布包臃肿

| 组 | 依赖 | 安装方式 |
|----|------|----------|
| core | 运行时核心（7 个） | pip install gtap |
| docs | Sphinx + 主题 | pip install gtap[docs] |
| dev | 测试 + lint + 类型检查 | pip install gtap[dev] |
| all | 全部 | pip install gtap[all] |

**pyproject.toml 配置**：
```toml
[project.optional-dependencies]
docs = ["sphinx[rtd]>=7.0", "myst-parser>=2.0"]
dev = ["pytest>=8.0", "pytest-cov", "ruff", "mypy"]
all = ["gtap[docs,dev]", "yfinance>=0.2", "akshare>=1.12"]
```

---

## Migration (迁移)

**无需数据库迁移**，但需要：
1. 用户从源码安装切换到 `pip install gtap`
2. 配置格式保持兼容（GridTradingConfig 不变）
3. 数据目录默认位置不变（~/.gtap/）

**向后兼容保证**：
- 所有 v0.7.0 API 保持稳定
- 新增功能通过新参数/新函数提供
- 移除任何功能需提前 2 个版本通知

---

## Testing Strategy

### 测试覆盖目标
| 模块 | 当前覆盖率 | 目标覆盖率 | 差距 |
|------|-----------|-----------|------|
| config.py | 95% | 95% | ✅ |
| grid.py | 70% | 90% | +20% |
| metrics.py | 80% | 90% | +10% |
| data.py | 75% | 90% | +15% |
| plot.py | 60% | 85% | +25% |
| fees.py | 95% | 95% | ✅ |
| atr.py | 100% | 100% | ✅ |
| theory.py | 100% | 100% | ✅ |

### 新增测试（v1.0.0 前补充）
- 文档构建测试（sphinx-build 成功）
- Docker 运行测试（容器启动 + API 响应）
- 发布脚本测试（dry-run 模式）

### 门禁
- 所有测试通过（141 → 目标 160+）
- 覆盖率 ≥ 90%（核心模块）
- 0 个 mypy 类型错误
- 0 个 ruff 警告

---

## 部署拓扑

### 发布管道（本地）
```
源码 → 构建分发包 (python -m build) → 验证 (twine check) → 上传 PyPI (twine upload)
```

### Docker 部署（单容器）
```dockerfile
# 基于 slim Python 镜像
python:3.11-slim → 安装 gtap → 暴露端口 8501 → CMD ["streamlit", "run", "gtap/app.py"]
```

### ReadTheDocs 构建
- .readthedocs.yaml 配置
- 自动从 GitHub 触发
- 依赖安装：`pip install .[docs]`

---

## 失败场景

| 场景 | 影响 | 恢复 |
|------|------|------|
| PyPI 上传失败 | 无法 pip install | 检查 twine 凭证，重试 |
| Docker 构建失败 | 无法容器化 | 检查 Dockerfile 依赖顺序 |
| 文档构建失败 | ReadTheDocs 红 | 检查 Sphinx 版本兼容 |
| 覆盖率不达标 | 质量门禁阻塞 | 补充缺失测试 |

---

## 相关链接

- OpenSpec v2.0 规范
- Python 打包指南（PyPA）
- ReadTheDocs 配置文档
- Docker 最佳实践

---

**设计评审状态**: DRAFT → 等待审查
**预计总工时**: 7 小时（6 任务 + 测试补充）
**风险等级**: 🟢 Low（无破坏性变更，纯新增）
