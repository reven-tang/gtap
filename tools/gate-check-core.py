#!/usr/bin/env python3
"""
Gate Check Core — 通用门禁引擎（项目无关）

用法:
    python3 tools/gate-check-core.py --project-config <config.yaml>

配置示例 (gtap.yaml):
    project: "gtap"
    src_dir: "src/gtap"
    tests_dir: "tests"
    smoke_tests:
      - script: "tools/smoke-test-gtap.py"
        args: ["--quick"]
      - script: "tools/smoke-test-gtap.py"
        args: ["--browser"]
    incremental_mapper: "tools/test-mapper.py"
    e2e_dir: "tests/e2e"
    skill_quality:
      - "gstack-qa"
      - "browser-testing-with-devtools"
    min_skill_score: 80
    min_coverage: 70
"""
import argparse, subprocess, sys, json
from pathlib import Path

class GateCheck:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.project_root = Path(self.config['project_root'])
        
    def load_config(self, path):
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    
    def run(self, phase="BUILD"):
        """执行门禁检查"""
        if phase == "BUILD":
            return self.check_build()
        elif phase == "QA":
            return self.check_qa()
        elif phase == "ALL":
            return self.check_build() and self.check_qa()
    
    def check_build(self):
        passed = True
        # 1. 增量 or smoke 测试
        targets = self.get_test_targets()
        if targets == ["smoke"]:
            cmd = ["python3", "-m", "pytest", "-m", "smoke", self.config['tests_dir'], "-v", "-q"]
        else:
            cmd = ["python3", "-m", "pytest"] + targets + ["-v", "-q"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            passed = False
            print(f"✗ pytest failed")
        else:
            print(f"✓ pytest passed")
        
        # 2. 冒烟测试
        for smoke in self.config.get('smoke_tests', []):
            script = self.project_root / smoke['script']
            args = [str(script)] + smoke.get('args', [])
            r = subprocess.run(args, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                passed = False
                print(f"✗ smoke test {script} failed")
            else:
                print(f"✓ smoke test {script} passed")
        
        # 3. progress.txt
        prog = self.project_root / "progress.txt"
        if not (prog.exists() and prog.stat().st_size > 0):
            passed = False
            print("✗ progress.txt missing")
        else:
            print("✓ progress.txt exists")
        
        # 4. 覆盖率（增量模式）
        if targets != ["smoke"]:
            r4 = subprocess.run(
                ["python3", "-m", "pytest", "-m", "smoke", self.config['tests_dir'],
                 "--cov=" + self.config['src_dir'], "--cov-report=json", "-q"],
                capture_output=True, text=True, timeout=90
            )
            cov_json = self.project_root / "coverage.json"
            cov_pct = 0
            if cov_json.exists():
                data = json.loads(cov_json.read_text())
                cov_pct = data.get("totals", {}).get("percent_covered", 0)
            if cov_pct < self.config.get('min_coverage', 70):
                passed = False
                print(f"✗ coverage: {cov_pct:.1f}% (<{self.config['min_coverage']}%)")
            else:
                print(f"✓ coverage: {cov_pct:.1f}%")
        else:
            print("⏭️  coverage: smoke mode skipped")
        
        return passed
    
    def check_qa(self):
        passed = True
        # 1. 浏览器验证
        browser_script = self.project_root / self.config.get('browser_validation', 'tools/smoke-test-gtap.py')
        r = subprocess.run([str(browser_script), "--browser"], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            passed = False
            print("✗ browser_validation failed")
        else:
            print("✓ browser_validation passed")
        
        # 2. E2E 存在
        e2e_dir = self.project_root / self.config.get('e2e_dir', 'tests/e2e')
        if not e2e_dir.exists():
            passed = False
            print("✗ e2e_tests missing")
        else:
            print("✓ e2e_tests exist")
        
        # 3. Skill Quality
        skills = self.config.get('skill_quality', [])
        for skill in skills:
            report = self.project_root / f"reports/skill-evaluations-v5/{skill}.json"
            if not report.exists():
                passed = False
                print(f"✗ skill {skill} report missing")
                continue
            score = json.loads(report.read_text()).get("total_score", 0)
            if score < self.config.get('min_skill_score', 80):
                passed = False
                print(f"✗ skill {skill}: {score} (<{self.config['min_skill_score']})")
            else:
                print(f"✓ skill {skill}: {score}")
        
        return passed
    
    def get_test_targets(self):
        mapper = self.project_root / self.config.get('incremental_mapper', 'tools/test-mapper.py')
        if not mapper.exists():
            return ["smoke"]
        try:
            r = subprocess.run([sys.executable, str(mapper)], capture_output=True, text=True, timeout=10)
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            if not lines or lines == ["smoke"]:
                return ["smoke"]
            return lines
        except:
            return ["smoke"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-config", required=True, help="YAML config file")
    parser.add_argument("--phase", choices=["BUILD", "QA", "ALL"], default="ALL")
    args = parser.parse_args()
    
    gate = GateCheck(args.project_config)
    ok = gate.run(args.phase)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
