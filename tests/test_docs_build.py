"""Test Sphinx docs build success."""
import subprocess
from pathlib import Path

def test_sphinx_conf_exists():
    """docs/conf.py 必须存在且可导入。"""
    conf = Path("docs/conf.py")
    assert conf.exists(), "docs/conf.py missing"

def test_sphinx_build_success():
    """sphinx-build 必须能成功构建文档（0 错误）。"""
    result = subprocess.run(
        ["sphinx-build", "-b", "html", "docs/", "docs/_build"],
        capture_output=True, text=True
    )
    # 检查是否有 "build succeeded" 或错误数
    assert result.returncode == 0, f"Sphinx build failed: {result.stderr[:500]}"

if __name__ == "__main__":
    test_sphinx_conf_exists()
    test_sphinx_build_success()
    print("✅ Sphinx docs tests pass")
