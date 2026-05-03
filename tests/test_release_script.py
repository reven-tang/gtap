"""Test release automation script."""
import os
from pathlib import Path
import stat

def test_publish_script_exists():
    """scripts/publish.sh 必须存在且可执行。"""
    p = Path("scripts/publish.sh")
    assert p.exists(), "publish.sh missing"
    assert os.access(p, os.X_OK), "publish.sh not executable"

def test_publish_script_has_steps():
    """publish.sh 必须包含关键步骤：build, check, upload。"""
    content = Path("scripts/publish.sh").read_text()
    required = ["python -m build", "twine check", "twine upload", "git tag"]
    for step in required:
        assert step in content, f"Missing step: {step}"

def test_publish_script_has_dry_run():
    """publish.sh 必须支持 --dry-run 参数。"""
    content = Path("scripts/publish.sh").read_text()
    assert "--dry-run" in content or "dry_run" in content, "Missing dry-run support"

if __name__ == "__main__":
    test_publish_script_exists()
    test_publish_script_has_steps()
    test_publish_script_has_dry_run()
    print("✅ Release script tests pass")
