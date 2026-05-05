#!/usr/bin/env python3
"""
Test Mapper Stub — 增量测试映射器模板（项目无关）

用法:
    python3 tools/test-mapper.py [--json]

功能:
    - 检测自上次提交后的源码改动
    - 映射到应运行的测试文件
    - 支持强制 E2E 触发（关键模块改动）
    - 无改动时返回 "smoke" 兜底

配置:
    修改 FILE_TEST_MAP，添加项目特定的源码→测试映射
"""
import subprocess, json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2] if Path(__file__).name == "test-mapper.py" else Path.cwd()

# ========== 项目配置：修改此处映射源码到测试 ==========
FILE_TEST_MAP = {
    # 核心模块
    "src/<project>/config.py": ["tests/test_config.py"],
    "src/<project>/data.py": ["tests/test_data.py", "tests/integration/test_end_to_end.py"],
    "src/<project>/grid.py": ["tests/test_grid.py", "tests/test_grid_edge_cases.py"],
    # 添加更多模块...
    
    # 入口与文档（不触发测试）
    "src/<project>/cli.py": [],
    "src/<project>/__init__.py": [],
    "docs/": [],
    "README.md": [],
}

# 强制触发 E2E 的关键模块（改动这些时自动运行 E2E 全套）
FORCE_E2E_KEYS = [
    "src/<project>/data.py",
    "src/<project>/grid.py",
    "src/<project>/providers/",
]

def get_changed_files(base=None, src_dir="src/<project>/"):
    """获取改动的源码文件（优先 staged，fallback 到 HEAD^）"""
    try:
        # 优先检测 staged 文件（pre-commit hook 场景）
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT)
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        if files:
            return [f for f in files if f.startswith(src_dir)]
        
        # fallback: 检测自上次提交后的改动
        result = subprocess.run(
            ["git", "diff", "--name-only", base or "HEAD^", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT)
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        return [f for f in files if f.startswith(src_dir)]
    except Exception as e:
        print(f"Warning: git diff failed: {e}", file=sys.stderr)
        return []

def map_to_tests(changed_files):
    """将改动的源码文件映射到测试文件"""
    tests = set()
    force_e2e = any(
        any(key in f for key in FORCE_E2E_KEYS)
        for f in changed_files
    )
    
    for changed in changed_files:
        for src_pattern, test_list in FILE_TEST_MAP.items():
            if src_pattern.endswith('/'):
                if changed.startswith(src_pattern):
                    tests.update(test_list)
                    break
            else:
                if src_pattern in changed:
                    tests.update(test_list)
                    break
    
    if force_e2e:
        e2e_dir = PROJECT_ROOT / "tests" / "e2e"
        if e2e_dir.exists():
            tests.add("tests/e2e/test_user_journey.py")
    
    return sorted(tests)

def main():
    args = sys.argv[1:]
    output_json = "--json" in args
    
    changed = get_changed_files()
    tests = map_to_tests(changed)
    
    if not tests:
        print("smoke")
        return
    
    if output_json:
        print(json.dumps({
            "mode": "incremental",
            "tests": tests,
            "changed": changed
        }, indent=2, ensure_ascii=False))
    else:
        for t in tests:
            print(t)

if __name__ == "__main__":
    main()
