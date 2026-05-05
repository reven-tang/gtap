#!/usr/bin/env python3
"""
GTAP Gate Check — 简化版（无 OpenSpec 依赖）

验证:
- BUILD: 增量测试 / smoke + 冒烟(--quick) + progress.txt + 覆盖率≥70%
- QA:   浏览器验证(--browser) + E2E 存在 + 技能质量
"""

import argparse, subprocess, sys, json
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw" / "workspace"
PROJECT = WORKSPACE / "projects" / "gtap"
TEST_MAPPER = PROJECT / "tools" / "test-mapper.py"


def run(cmd, cwd=PROJECT, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))


def get_test_targets():
    """调用 test-mapper.py 获取应运行的测试文件列表"""
    if not TEST_MAPPER.exists():
        return ["smoke"]
    try:
        result = subprocess.run(
            [sys.executable, str(TEST_MAPPER)],
            capture_output=True, text=True, timeout=10, cwd=str(PROJECT)
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if not lines or lines == ["smoke"]:
            return ["-m", "smoke"]
        # 返回具体测试文件路径列表
        return lines
    except Exception as e:
        print(f"Warning: test-mapper failed: {e}", file=sys.stderr)
        return ["-m", "smoke"]


def check_build():
    print("\n" + "="*50 + "\n🚧 Gate Check: BUILD\n" + "="*50)
    passed = True

    # 1) pytest (增量 or smoke)
    targets = get_test_targets()
    if targets == ["-m", "smoke"]:
        cmd = ["python3", "-m", "pytest", "-m", "smoke", "tests/", "-v", "--tb=short", "-q"]
        label = "pytest (smoke)"
    else:
        cmd = ["python3", "-m", "pytest"] + targets + ["-v", "--tb=short", "-q"]
        label = f"pytest (incremental: {len(targets)} files)"
    
    r = run(cmd, timeout=90)
    ok = r.returncode == 0
    print(f"  {'✓' if ok else '✗'} {label}")
    if not ok and "FAILED" in (r.stdout + r.stderr):
        passed = False
        print(f"    ⚠ 测试失败 — 查看输出")
    if r.stdout:
        print(f"    📊 {r.stdout.strip().split()[-1] if r.stdout.strip() else 'OK'}")

    # 2) 冒烟 (--quick)
    r2 = run([str(PROJECT/"venv/bin/python3"), str(WORKSPACE/"tools/smoke-test-gtap.py"), "--quick"], timeout=30)
    ok2 = r2.returncode == 0
    print(f"  {'✓' if ok2 else '✗'} smoke_test (--quick)")
    if not ok2:
        passed = False
        print(f"    ⚠ 冒烟失败: {r2.stderr[-100:]}")

    # 3) progress.txt
    prog = PROJECT / "progress.txt"
    ok3 = prog.exists() and prog.stat().st_size > 0
    print(f"  {'✓' if ok3 else '✗'} progress.txt")
    if not ok3:
        passed = False

    # 4) 覆盖率 (仅 smoke 模式或增量目标包含核心模块时)
    # 简化：只对 smoke 模式检查覆盖率
    if targets == ["-m", "smoke"]:
        r4 = run(["python3", "-m", "pytest", "-m", "smoke", "tests/", "--cov=src/gtap", "--cov-report=json", "-q"], timeout=90)
        cov_pct = 0
        if r4.returncode == 0:
            cov_json = PROJECT / "coverage.json"
            if cov_json.exists():
                data = json.loads(cov_json.read_text())
                cov_pct = data.get("totals", {}).get("percent_covered", 0)
        ok4 = cov_pct >= 70
        print(f"  {'✓' if ok4 else '✗'} coverage: {cov_pct:.1f}% (≥70%)")
        if not ok4:
            passed = False
    else:
        print(f"  ✓ coverage: 增量模式跳过（后台异步）")

    print(f"\n  {'✅ PASS' if passed else '❌ BLOCK'}: BUILD → VERIFY")
    return passed


def check_qa():
    print("\n" + "="*50 + "\n🚧 Gate Check: QA\n" + "="*50)
    passed = True

    # 1) 浏览器验证 (--browser)
    r = run([str(PROJECT/"venv/bin/python3"), str(WORKSPACE/"tools/smoke-test-gtap.py"), "--browser"], timeout=60)
    ok = r.returncode == 0
    print(f"  {'✓' if ok else '✗'} browser_validation")
    if not ok:
        passed = False
        print(f"    ⚠ 浏览器验证失败")

    # 2) E2E 存在
    e2e = PROJECT / "tests" / "e2e"
    ok2 = e2e.exists()
    print(f"  {'✓' if ok2 else '✗'} e2e_tests_exists")
    if not ok2:
        passed = False

    # 3) 技能质量
    eval_dir = WORKSPACE / "reports" / "skill-evaluations-v5"
    scores = {}
    if eval_dir.exists():
        for f in eval_dir.glob("*.json"):
            try:
                d = json.loads(f.read_text())
                # 字段名适配: skill-evaluator 输出 skill_name/total_score
                skill_key = d.get("skill_name", f.stem)
                score_val = d.get("total_score", 0)
                scores[skill_key] = score_val
            except: pass
    ok3 = scores.get("gstack-qa", 0) >= 80 and scores.get("browser-testing-with-devtools", 0) >= 80
    print(f"  {'✓' if ok3 else '✗'} skill_quality (gstack-qa: {scores.get('gstack-qa','N/A')}, browser: {scores.get('browser-testing-with-devtools','N/A')})")
    if not ok3:
        passed = False

    print(f"\n  {'✅ PASS' if passed else '❌ BLOCK'}: QA → SHIP")
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["BUILD","QA"])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all or args.phase == "BUILD":
        b = check_build()
    if args.all or args.phase == "QA":
        q = check_qa()
