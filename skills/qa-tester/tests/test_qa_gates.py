"""Cross-platform coherence gate: QA gate names in SKILL.md vs scripts/qa-gates.ps1.

Two directions have to hold, and they are not the same set:

- The QA report template's ``## Gates`` block is what the operator prints, so it
  must be a **subset** of what the script actually runs (the report cannot show a
  gate the script never executes).
- Every npm script the script tries must be **named in SKILL.md**, so the operator
  knows the contract before running it (the script falls back across project
  naming conventions: ``typecheck``/``tsc``, ``test:e2e``/``e2e``,
  ``test:smoke``/``smoke``).

Both files are read as text, so no PowerShell is needed and the suite runs on
Linux CI.
"""

from __future__ import annotations

import re
from pathlib import Path

QA_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = QA_DIR / "SKILL.md"
GATES_PS1 = QA_DIR / "scripts" / "qa-gates.ps1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def documented_gates(skill_md: str) -> set[str]:
    """Gate names the SKILL.md QA report template tells the operator to report.

    Lives in the "## Gates" block of the fenced "# QA Report" template; each
    line carries one or more ``- <name>: <mark>`` entries.
    """
    template = re.search(r"```\n(# QA Report.*?)```", skill_md, re.DOTALL)
    assert template, "SKILL.md no longer ships a fenced '# QA Report' template"
    block = re.search(r"## Gates\n(.*?)(?=\n## |\Z)", template.group(1), re.DOTALL)
    assert block, "QA report template no longer has a '## Gates' section"
    return set(re.findall(r"-\s*([a-z][\w:.-]*?)\s*:", block.group(1)))


def declared_gates(ps1_script: str) -> set[str]:
    """Gate names scripts/qa-gates.ps1 actually runs (one Run-Npm call each)."""
    return set(re.findall(r'Run-Npm\s+"([^"]+)"', ps1_script))


def test_skill_md_documents_gate_names():
    assert documented_gates(_read(SKILL_MD)), "SKILL.md documents no gate names"


def test_qa_gates_script_declares_gate_names():
    assert declared_gates(_read(GATES_PS1)), "qa-gates.ps1 declares no gates"


def test_reported_gates_are_a_subset_of_the_script_gates():
    documented = documented_gates(_read(SKILL_MD))
    declared = declared_gates(_read(GATES_PS1))
    only_doc = sorted(documented - declared)
    assert documented <= declared, (
        "the QA report template promises gates the script never runs.\n"
        f"  reported in SKILL.md ('## Gates') : {sorted(documented)}\n"
        f"  run by scripts/qa-gates.ps1       : {sorted(declared)}\n"
        f"  reported but NOT run              : {only_doc}"
    )


def test_every_script_gate_is_named_in_the_skill():
    skill_md = _read(SKILL_MD)
    declared = declared_gates(_read(GATES_PS1))
    missing = sorted(g for g in declared if f"`{g}`" not in skill_md)
    assert not missing, (
        "scripts/qa-gates.ps1 runs npm scripts SKILL.md never names, so the "
        "operator cannot know the contract.\n"
        f"  run by the script but not named in SKILL.md: {missing}"
    )
