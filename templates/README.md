# AI Self-Loop Dev System — 门禁系统模板 v1.3.0

## 📦 模板概览

本模板包提供完整的门禁系统基础设施，适用于所有后续项目。

### 模板文件

| 文件 | 说明 | 配置方式 |
|------|------|----------|
| `templates/gate-check-core.py` | 通用门禁引擎 | YAML 配置文件 |
| `templates/smoke-test-stub.py` | 冒烟测试模板 | 环境变量/自动探测 |
| `templates/test-mapper-stub.py` | 增量测试映射器 | 修改 `FILE_TEST_MAP` |
| `templates/e2e-scaffold.py` | E2E 测试脚手架 | 继承基类实现场景 |

---

## 🚀 快速开始（3 步）

### 步骤 1: 复制模板到项目

```bash
# 从系统模板目录复制
cp templates/smoke-test-stub.py tools/smoke-test.py
cp templates/test-mapper-stub.py tools/test-mapper.py
cp templates/e2e-scaffold.py tests/e2e/test_user_journey.py
```

### 步骤 2: 配置 gate-check

创建 `gtap.yaml`（项目配置文件）：

```yaml
project: "gtap"
project_root: "."
src_dir: "src/gtap"
tests_dir: "tests"
smoke_tests:
  - script: "tools/smoke-test.py"
    args: ["--quick"]
  - script: "tools/smoke-test.py"
    args: ["--browser"]
incremental_mapper: "tools/test-mapper.py"
e2e_dir: "tests/e2e"
skill_quality:
  - "gstack-qa"
  - "browser-testing-with-devtools"
min_skill_score: 80
min_coverage: 70
```

### 步骤 3: 运行门禁

```bash
# BUILD 阶段（快速验证）
python3 gate-check-core.py --config gtap.yaml --phase BUILD

# QA 阶段（完整验证）
python3 gate-check-core.py --config gtap.yaml --phase QA

# 全链路
python3 gate-check-core.py --config gtap.yaml --phase ALL
```

---

## 📋 配置详解

### gate-check-core.py 配置项

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | str | ✅ | 项目标识名 |
| `project_root` | str | ❌ | 项目根目录（默认 `.`） |
| `src_dir` | str | ✅ | 源码目录（相对 project_root） |
| `tests_dir` | str | ✅ | 测试目录（相对 project_root） |
| `smoke_tests` | list | ✅ | 冒烟测试列表（每个含 script + args） |
| `incremental_mapper` | str | ✅ | 增量映射器路径 |
| `e2e_dir` | str | ✅ | E2E 测试目录 |
| `skill_quality` | list | ✅ | 需要的技能评估报告列表 |
| `min_skill_score` | int | ❌ | 技能分数阈值（默认 80） |
| `min_coverage` | int | ❌ | 覆盖率阈值（默认 70） |

### smoke-test-stub.py 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PROJECT_ROOT` | 自动检测 | 项目根目录 |
| `APP_ENTRY` | `app.py` | 应用入口文件 |
| `APP_PORT` | `8501` | 应用监听端口 |

---

## 🔧 定制指南

### 定制冒烟测试

1. 复制 `templates/smoke-test-stub.py` 到 `tools/smoke-test.py`
2. 修改 `test_*` 函数，添加项目特定的检查
3. 保持函数签名 `() -> (bool, str)`（成功，消息）

### 定制增量映射

1. 复制 `templates/test-mapper-stub.py` 到 `tools/test-mapper.py`
2. 修改 `FILE_TEST_MAP`，添加源码文件到测试文件的映射
3. 修改 `FORCE_E2E_KEYS`，定义哪些关键文件改动强制运行 E2E

### 定制 E2E 测试

1. 复制 `templates/e2e-scaffold.py` 到 `tests/e2e/test_user_journey.py`
2. 实现 `TestErrorHandling` 和 `TestPerformance` 的 skip 测试
3. 添加项目特定的页面元素检查和交互流程

---

## 📊 门禁阶段说明

### Phase BUILD（构建验证）

| 检查项 | 说明 | 阻断条件 |
|--------|------|----------|
| 单元测试 | 增量模式或 smoke 标记 | 测试失败 |
| 冒烟测试 | --quick 快速检查 | 任一冒烟失败 |
| progress.txt | 存在且非空 | 缺失 |
| 覆盖率 | 增量模式要求 ≥min_coverage | 覆盖率不足（smoke 模式跳过） |

### Phase QA（质量保证）

| 检查项 | 说明 | 阻断条件 |
|--------|------|----------|
| 浏览器验证 | --browser UI 检查 | Console 0 error + HTTP 200 |
| E2E 测试 | tests/e2e/ 存在且可运行 | 目录缺失 |
| Skill Quality | 技能评估报告分数 | 任一技能 < min_skill_score |

---

## 🎯 最佳实践

### 1. 首次提交使用 smoke 模式
无 git 基线时，test-mapper 返回 `smoke`，运行标记测试快速验证。

### 2. 日常提交使用增量模式
git diff 检测改动，仅运行相关测试，速度 <0.5 秒。

### 3. 关键文件强制 E2E
`data.py`、`grid.py` 等核心模块改动，自动触发全套 E2E 测试。

### 4. 浏览器验证降级
Playwright 不可用时降级为 HTTP 200 + 内容检查，确保 CI 稳定。

### 5. 技能质量门禁
gate-check 自动读取 `reports/skill-evaluations-v5/*.json`，分数不足阻断发布。

---

## 📁 项目结构示例

```
my-project/
├── src/
│   └── myproject/
│       ├── config.py
│       ├── data.py
│       └── ...
├── tests/
│   ├── test_config.py
│   ├── test_data.py
│   ├── integration/
│   │   └── test_end_to_end.py
│   └── e2e/
│       └── test_user_journey.py   ← 复制 scaffold
├── tools/
│   ├── smoke-test.py               ← 复制 stub
│   └── test-mapper.py               ← 复制 stub + 配置映射
├── templates/                       ← 系统模板（只读）
├── gate-check-core.py              ← 通用门禁引擎（或从系统复制）
├── myproject.yaml                  ← 项目配置
└── progress.txt                     ← 进度文件
```

---

## 🔄 升级到新版本

模板更新时：

1. 比较 `templates/` 与项目中的副本
2. 合并新增功能（保持项目特定定制）
3. 更新 `brain/concepts/ai-self-loop-dev-system.md` 记录版本变更

---

**版本**: v1.3.0  
**更新日期**: 2026-05-05  
**维护**: AI 自闭环开发系统
