"""Test tutorial completeness."""
from pathlib import Path

def test_tutorial_dir_exists():
    """docs/tutorial/ 目录必须存在。"""
    p = Path("docs/tutorial")
    assert p.exists(), "docs/tutorial/ missing"

def test_tutorial_has_three_files():
    """必须包含 3 个教程文件。"""
    tutorial_dir = Path("docs/tutorial")
    files = list(tutorial_dir.glob("*.md"))
    assert len(files) >= 3, f"Expected 3 tutorial files, got {len(files)}"

def test_tutorial_basic_grid_exists():
    """基础网格教程必须存在。"""
    p = Path("docs/tutorial/basic_grid.md")
    assert p.exists(), "basic_grid.md missing"

if __name__ == "__main__":
    test_tutorial_dir_exists()
    test_tutorial_has_three_files()
    test_tutorial_basic_grid_exists()
    print("✅ Tutorial tests pass")
