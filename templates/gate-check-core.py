#!/usr/bin/env python3
"""
Gate Check Core — 通用门禁引擎（项目无关）

用法:
    python3 gate-check-core.py --config <project.yaml>

配置示例 (gtap.yaml):
    project: "gtap"
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
"""
import argparse, subprocess, sys, json, yaml
from pathlib import Path

class GateCheck:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.project_root = Path(self.config.get('project_root', Path.cwd()))
        
    def load_config(self, path):
        with open(path) as f:
            return yaml.safe_load(f)
    
    def run(self, phase="ALL"):
        if phase == "BUILD":
            return self.check_build()
        elif phase == "QA":
            return self.check_qa()
        elif phase == "ALL":
            return self.check_build() and self.check_qa()
    
    def check_build(self):
        passed = True
        targets = self.get_test_targets()
        
        # 1) 测试（增量 or smoke）
        if targets == ["smoke"]:
            cmd = ["python3", "-m", "pytest", "-m", "smoke", self.config['tests_dir'], "-v", "-q"]
            label = "pytest (smoke)"
        else:
            cmd = ["python3", "-m", "pytest"] + targets + ["-v", "-q"]
            label = f"pytest (incremental: {len(targets)} files)"
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90, cwd=str(self.project_root))
        ok = r.returncode == 0
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            passed = False
            print(f"    ⚠ 测试失败")
        
        # 2) 冒烟测试
        for smoke in self.config.get('smoke_tests', []):
            script = self.project_root / smoke['script']
            args = [str(script)] + smoke.get('args', [])
            r = subprocess.run(args, capture_output=True, text=True, timeout=30, cwd=str(self.project_root))
            ok = r.returncode == 0
            print(f"  {'✓' if ok else '✗'} smoke: {smoke['script']}")
            if not ok:
                passed = False
                print(f"    ⚠ 冒烟失败: {r.stderr[-100:]}")
        
        # 3) progress.txt
        prog = self.project_root / "progress.txt"
        ok3 = prog.exists() and prog.stat().st_size > 0
        print(f"  {'✓' if ok3 else '✗'} progress.txt")
        if not ok3:
            passed = False
        
        # 4) 覆盖率（仅增量模式）
        if targets != ["smoke"]:
            r4 = subprocess.run(
                ["python3", "-m", "pytest", "-m", "smoke", self.config['tests_dir'],
                 f"--cov={self.config['src_dir']}", "--cov-report=json", "-q"],
                capture_output=True, text=True, timeout=90, cwd=str(self.project_root)
            )
            cov_json = self.project_root / "coverage.json"
            cov_pct = 0
            if r4.returncode == 0 and cov_json.exists():
                data = json.loads(cov_json.read_text())
                cov_pct = data.get("totals", {}).get("percent_covered", 0)
            ok4 = cov_pct >= self.config.get('min_coverage', 70)
            print(f"  {'✓' if ok4 else '✗'} coverage: {cov_pct:.1f}% (≥{self.config.get('min_coverage',70)}%)")
            if not ok4:
                passed = False
        else:
            print(f"  ⏭️  coverage: smoke 模式跳过")
        
        return passed
    
    def check_qa(self):
        passed = True
        
        # 1) 浏览器验证
        browser_script = self.project_root / self.config.get('browser_validation', 'tools/smoke-test.py')
        r = subprocess.run([str(browser_script), "--browser"], capture_output=True, text=True, timeout=60, cwd=str(self.project_root))
        ok = r.returncode == 0
        print(f"  {'✓' if ok else '✗'} browser_validation")
        if not ok:
            passed = False
        
        # 2) E2E 存在
        e2e_dir = self.project_root / self.config.get('e2e_dir', 'tests/e2e')
        ok2 = e2e_dir.exists() and any(e2e_dir.glob("test_*.py"))
        print(f"  {'✓' if ok2 else '✗'} e2e_tests_exists")
        if not ok2:
            passed = False
        
        # 3) Skill Quality
        skills = self.config.get('skill_quality', [])
        for skill in skills:
            report = self.project_root / f"reports/skill-evaluations-v5/{skill}.json"
            if not report.exists():
                passed = False
                print(f"  ✗ skill {skill}: report missing")
                continue
            try:
                score = json.loads(report.read_text()).get("total_score", 0)
                ok = score >= self.config.get('min_skill_score', 80)
                print(f"  {'✓' if ok else '✗'} skill {skill}: {score}")
                if not ok:
                    passed = False
            except Exception:
                passed = False
                print(f"  ✗ skill {skill}: parse error")
        
        return passed
    
    def get_test_targets(self):
        mapper = self.project_root / self.config.get('incremental_mapper', 'tools/test-mapper.py')
        if not mapper.exists():
            return ["smoke"]
        try:
            r = subprocess.run([sys.executable, str(mapper)], capture_output=True, text=True, timeout=10, cwd=str(self.project_root))
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            if not lines or lines == ["smoke"]:
                return ["smoke"]
            return lines
        except Exception:
            return ["smoke"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Project YAML config")
    parser.add_argument("--phase", choices=["BUILD", "QA", "ALL"], default="ALL")
    args = parser.parse_args()
    
    gate = GateCheck(args.config)
    ok = gate.run(args.phase)
    print(f"\n{'✅ PASS' if ok else '❌ BLOCK'}: {args.phase}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
