"""Test PyPI release configuration."""
from pathlib import Path
import tomllib

def test_pyproject_has_required_metadata():
    """pyproject.toml 必须包含完整的项目元数据。"""
    data = tomllib.loads(Path("pyproject.toml").read_text())
    project = data.get("project", {})
    required = ["name", "version", "description", "authors", "dependencies"]
    for field in required:
        assert field in project, f"Missing project.{field}"

def test_pyproject_has_classifiers():
    """必须包含 PyPI classifiers（License, Programming Language）。"""
    data = tomllib.loads(Path("pyproject.toml").read_text())
    classifiers = data.get("project", {}).get("classifiers", [])
    assert any("License" in c for c in classifiers), "Missing License classifier"
    assert any("Programming Language :: Python" in c for c in classifiers), "Missing Python classifier"

def test_pypirc_template_exists():
    """scripts/.pypirc.template 必须存在。"""
    assert Path("scripts/.pypirc.template").exists(), "Missing .pypirc.template"

if __name__ == "__main__":
    test_pyproject_has_required_metadata()
    test_pyproject_has_classifiers()
    test_pypirc_template_exists()
    print("✅ PyPI config tests pass")
