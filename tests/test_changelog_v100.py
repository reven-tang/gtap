"""Test CHANGELOG v1.0.0 entry format and completeness."""
import re
from pathlib import Path

def test_changelog_has_v100_entry():
    """CHANGELOG.md 必须包含 v1.0.0 条目。"""
    content = Path("CHANGELOG.md").read_text()
    assert re.search(r'## \[1\.0\.0\]', content), "Missing v1.0.0 heading"

def test_changelog_v100_has_sections():
    """v1.0.0 条目必须包含 Added/Fixed/Changed 小节。"""
    content = Path("CHANGELOG.md").read_text()
    # Find v1.0.0 section
    section = re.search(r'## \[1\.0\.0\] .*?\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    assert section, "Cannot find v1.0.0 section"
    body = section.group(1)
    # At least one of Added/Fixed/Changed should exist
    has_section = any(re.search(f'^### {s}', body, re.MULTILINE) for s in ['Added', 'Fixed', 'Changed'])
    assert has_section, "v1.0.0 missing section headers (Added/Fixed/Changed)"

if __name__ == "__main__":
    test_changelog_has_v100_entry()
    test_changelog_v100_has_sections()
    print("✅ CHANGELOG v1.0.0 entry tests pass")
