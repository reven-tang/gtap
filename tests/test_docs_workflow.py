"""Test GitHub Actions docs workflow."""
from pathlib import Path

def test_github_workflow_exists():
    """必须包含 docs.yml 工作流。"""
    p = Path(".github/workflows/docs.yml")
    assert p.exists(), "Missing .github/workflows/docs.yml"

def test_workflow_has_sphinx_build():
    """工作流必须包含 sphinx-build 步骤。"""
    content = Path(".github/workflows/docs.yml").read_text()
    assert "sphinx-build" in content, "Workflow missing sphinx-build step"

if __name__ == "__main__":
    test_github_workflow_exists()
    test_workflow_has_sphinx_build()
    print("✅ Docs workflow tests pass")
