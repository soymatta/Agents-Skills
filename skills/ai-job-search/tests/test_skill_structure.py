"""Basic structure tests for ai-job-search third-party skill."""
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists(), "SKILL.md must exist"


def test_reference_dir_exists():
    ref_dir = SKILL_DIR / "reference"
    assert ref_dir.is_dir(), "reference/ directory must exist"


def test_all_reference_files_exist():
    expected = [
        "01-candidate-profile.md",
        "02-behavioral-profile.md",
        "03-writing-style.md",
        "04-job-evaluation.md",
        "05-cv-templates.md",
        "06-cover-letter-templates.md",
        "07-interview-prep.md",
        "08-application-forms.md",
        "09-web-research.md",
    ]
    ref_dir = SKILL_DIR / "reference"
    for fname in expected:
        assert (ref_dir / fname).exists(), f"Missing reference file: {fname}"


def test_skill_md_has_frontmatter():
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
    assert "name: ai-job-search" in content, "SKILL.md must have name: ai-job-search"
    assert "Third-party" in content, "SKILL.md must note this is third-party"
