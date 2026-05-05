#!/usr/bin/env python3
"""
测试文件映射器 — 增量测试用

根据 git diff 找出的源码改动，映射到应运行的测试文件。
新建项目首次提交 → 返回 "smoke" 回退到标记测试。
"""

import subprocess
import json
import sys
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
PROJECT = WORKSPACE / "projects" / "gtap"

# 源码文件 → 测试文件映射表（按模块组织）
FILE_TEST_MAP = {
    # ========== 核心模块 ==========
    "src/gtap/config.py": ["tests/test_config.py"],
    "src/gtap/grid.py": ["tests/test_grid.py", "tests/test_grid_edge_cases.py"],
    "src/gtap/fees.py": ["tests/test_fees.py"],
    "src/gtap/metrics.py": ["tests/test_metrics.py", "tests/test_metrics_precision.py"],
    "src/gtap/data.py": ["tests/test_data.py", "tests/integration/test_end_to_end.py"],
    "src/gtap/strategies.py": ["tests/test_strategies.py"],
    "src/gtap/atr.py": ["tests/test_atr.py"],
    "src/gtap/store.py": ["tests/test_store.py"],
    "src/gtap/exceptions.py": ["tests/test_config.py", "tests/test_grid.py", "tests/test_data.py"],

    # ========== 策略变体 ==========
    "src/gtap/parrondo.py": ["tests/test_portfolio_parrondo.py"],
    "src/gtap/portfolio.py": ["tests/test_portfolio_parrondo.py"],

    # ========== 可视化 ==========
    "src/gtap/plot.py": ["tests/test_plot.py"],

    # ========== 理论与文档 ==========
    "src/gtap/theory.py": ["tests/test_theory.py"],

    # ========== 数据源（全部归并到 providers 测试） ==========
    "src/gtap/providers/": ["tests/test_providers.py"],
    "src/gtap/providers/base.py": ["tests/test_providers.py"],
    "src/gtap/providers/factory.py": ["tests/test_providers.py"],
    "src/gtap/providers/baostock_provider.py": ["tests/test_providers.py"],
    "src/gtap/providers/yfinance_provider.py": ["tests/test_providers.py"],
    "src/gtap/providers/akshare_provider.py": ["tests/test_providers.py"],

    # ========== 入口与工具（不触发测试） ==========
    "src/gtap/cli.py": [],
    "src/gtap/__init__.py": [],

    # ========== 文档与脚本（不触发测试） ==========
    "docs/": [],
    "README.md": [],
}


def get_changed_files(base="HEAD^", src_dir="src/gtap/"):
    """获取自上次提交后改动的源码文件"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT)
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in files if f.startswith(src_dir)]
    except Exception as e:
        print(f"Warning: git diff failed: {e}", file=sys.stderr)
        return []


def map_to_tests(changed_files):
    """将改动的源码文件映射到测试文件"""
    tests = set()
    # 检查是否需要强制 E2E（涉及数据流或网格引擎）
    force_e2e = any(
        any(key in f for key in ["src/gtap/data.py", "src/gtap/grid.py", "src/gtap/providers/"]) 
        for f in changed_files
    )
    
    for changed in changed_files:
        matched = False
        for src_pattern, test_list in FILE_TEST_MAP.items():
            if src_pattern.endswith('/'):
                if changed.startswith(src_pattern):
                    tests.update(test_list)
                    matched = True
            else:
                if src_pattern in changed:
                    tests.update(test_list)
                    matched = True
    
    # 强制 E2E 条件
    if force_e2e:
        e2e_dir = PROJECT / "tests" / "e2e"
        if e2e_dir.exists():
            tests.add("tests/e2e/test_user_journey.py")
    
    return sorted(tests)


def get_test_targets():
    """获取应运行的测试目标（增量 or smoke）"""
    changed = get_changed_files()
    tests = map_to_tests(changed)
    
    if not tests:
        return ["-m", "smoke"]  # 回退到 smoke 标记
    return tests


def main():
    args = sys.argv[1:]
    output_json = "--json" in args

    targets = get_test_targets()
    
    if output_json:
        result = {
            "mode": "smoke" if targets == ["-m", "smoke"] else "incremental",
            "tests": targets if targets != ["-m", "smoke"] else [],
            "changed": get_changed_files()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if targets == ["-m", "smoke"]:
            print("smoke")
        else:
            for t in targets:
                print(t)


if __name__ == "__main__":
    main()
