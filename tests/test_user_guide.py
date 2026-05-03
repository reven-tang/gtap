"""Test USER_GUIDE completeness."""
from pathlib import Path

def test_user_guide_exists():
    """USER_GUIDE.md 必须存在。"""
    p = Path("docs/guide/USER_GUIDE.md")
    assert p.exists(), f"Missing {p}"

def test_user_guide_sections():
    """USER_GUIDE.md 必须包含 5 大章节。"""
    content = Path("docs/guide/USER_GUIDE.md").read_text()
    required = ["安装", "配置", "使用", "参数说明", "故障排除"]
    for section in required:
        assert section in content, f"Missing section: {section}"

if __name__ == "__main__":
    test_user_guide_exists()
    test_user_guide_sections()
    print("✅ USER_GUIDE tests pass")
