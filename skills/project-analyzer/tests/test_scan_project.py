"""Tests for the deterministic init_review scanner (scan_project.py).

Each test builds a throwaway tree, runs the scanner, and asserts the checks
fire where they should and stay quiet where they must not (false-positive
guards are as important as detection here).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scan_project import RULES, ScanOptions, render_md, scan  # noqa: E402


def codes(root: Path, **opts) -> list[str]:
    result = scan(root, ScanOptions(ignore=(), **opts))
    return [f["code"] for f in result["findings"]]


def findings_for(root: Path, code: str, **opts) -> list[dict]:
    result = scan(root, ScanOptions(ignore=(), **opts))
    return [f for f in result["findings"] if f["code"] == code]


# --------------------------------------------------------------------------- #
# Blockers
# --------------------------------------------------------------------------- #

def test_python_syntax_error(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def x(:\n    pass\n", encoding="utf-8")
    assert "syntax.python" in codes(tmp_path)


def test_valid_python_is_clean(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def x() -> int:\n    return 1\n", encoding="utf-8")
    assert "syntax.python" not in codes(tmp_path)


def test_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "c.json").write_text('{"a": 1,}', encoding="utf-8")
    assert "syntax.json" in codes(tmp_path)


def test_lockfile_json_is_not_parsed(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text("not json at all", encoding="utf-8")
    assert "syntax.json" not in codes(tmp_path)


def test_frontmatter_missing(tmp_path: Path) -> None:
    (tmp_path / "skills" / "foo").mkdir(parents=True)
    (tmp_path / "skills" / "foo" / "SKILL.md").write_text("# Foo\n\nNo frontmatter.\n", encoding="utf-8")
    assert "frontmatter.missing" in codes(tmp_path)


def test_frontmatter_present_is_clean(tmp_path: Path) -> None:
    d = tmp_path / "skills" / "foo"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: foo\ndescription: does foo\n---\n\n# Foo\n", encoding="utf-8")
    assert "frontmatter.missing" not in codes(tmp_path)


def test_agent_without_description(tmp_path: Path) -> None:
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "a.md").write_text("---\nname: a\n---\nbody\n", encoding="utf-8")
    assert "frontmatter.missing" in codes(tmp_path)


def test_stub_body_detected(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def todo_thing():\n    pass\n", encoding="utf-8")
    assert "stub.body" in codes(tmp_path)


def test_implemented_body_is_clean(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("def thing():\n    return 42\n", encoding="utf-8")
    assert "stub.body" not in codes(tmp_path)


def test_empty_file_detected_but_init_ignored(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    found = findings_for(tmp_path, "empty.file")
    assert len(found) == 1 and found[0]["file"] == "empty.txt"


# --------------------------------------------------------------------------- #
# Markers (false-positive guards)
# --------------------------------------------------------------------------- #

def test_real_markers_detected(tmp_path: Path) -> None:
    # Built at runtime so this test file itself carries no marker literal.
    todo, fixme = "TO" "DO", "FIX" "ME"
    (tmp_path / "a.py").write_text(f"# {todo}: wire this up\nx = 1  # {fixme}\n", encoding="utf-8")
    assert len(findings_for(tmp_path, "todo.marker")) == 2


def test_spanish_todo_is_not_a_marker(tmp_path: Path) -> None:
    (tmp_path / "q.ts").write_text("// Captura: por defecto TODO lo escrito se encola\n", encoding="utf-8")
    assert findings_for(tmp_path, "todo.marker") == []


def test_marker_list_in_docs_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "- Detect `TODO`/`FIXME`/`HACK`/`XXX` markers in source.\n", encoding="utf-8")
    assert findings_for(tmp_path, "todo.marker") == []


def test_placeholder_xxx_in_backticks_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("not a placeholder value like `XXX` or `demo`\n", encoding="utf-8")
    assert findings_for(tmp_path, "todo.marker") == []


# --------------------------------------------------------------------------- #
# Doc references
# --------------------------------------------------------------------------- #

def test_doc_references_missing_script(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("Run `scripts/gone.py` to do it.\n", encoding="utf-8")
    assert "doc.missing-script" in codes(tmp_path)


def test_doc_reference_to_existing_script_is_clean(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "here.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "SKILL.md").write_text("Run `scripts/here.py`.\n", encoding="utf-8")
    assert "doc.missing-script" not in codes(tmp_path)


def test_product_names_are_not_scripts(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Built with Node.js and Next.js.\n", encoding="utf-8")
    assert findings_for(tmp_path, "doc.missing-script") == []


def test_fenced_code_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("Example:\n\n```\npython scripts/example.py\n```\n", encoding="utf-8")
    assert "doc.missing-script" not in codes(tmp_path)


def test_broken_md_link(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("See [the guide](docs/guide.md).\n", encoding="utf-8")
    assert "doc.broken-link" in codes(tmp_path)


def test_placeholder_link_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Format is `[text](url)` here.\n", encoding="utf-8")
    assert findings_for(tmp_path, "doc.broken-link") == []


def test_valid_md_link_is_clean(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("hi\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("See [the guide](docs/guide.md).\n", encoding="utf-8")
    assert "doc.broken-link" not in codes(tmp_path)


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #

def test_empty_dir_detected(tmp_path: Path) -> None:
    (tmp_path / "hollow").mkdir()
    assert "dir.empty" in codes(tmp_path)


def test_backup_file_detected(tmp_path: Path) -> None:
    (tmp_path / "old.bak").write_text("x", encoding="utf-8")
    assert "file.backup" in codes(tmp_path)


def test_duplicate_file_detected(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("identical content here\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("identical content here\n", encoding="utf-8")
    assert "file.duplicate" in codes(tmp_path)


def test_table_orphan_detected(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n| 3 | 4 |\n| 5 | 6 |\n", encoding="utf-8")
    found = findings_for(tmp_path, "md.table-orphan")
    assert len(found) == 1 and found[0]["line"] == 5


def test_table_with_blank_line_before_header_is_clean(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Some text.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    assert findings_for(tmp_path, "md.table-orphan") == []


def test_duplicate_heading_same_parent(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "## A\n\n### Steps\n\ntext\n\n### Steps\n\nmore\n", encoding="utf-8")
    assert len(findings_for(tmp_path, "md.duplicate-heading")) == 1


def test_same_heading_different_parents_is_clean(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "## Workflow: Search\n\n### Steps\n\nx\n\n## Workflow: Write\n\n### Steps\n\ny\n",
        encoding="utf-8")
    assert findings_for(tmp_path, "md.duplicate-heading") == []


def test_heading_line_numbers_survive_code_fences(tmp_path: Path) -> None:
    # A fence before the duplicate must not shift the reported line number.
    (tmp_path / "README.md").write_text(
        "## A\n\n```\ncode\nmore code\n```\n\n### Steps\n\nx\n\n### Steps\n\ny\n",
        encoding="utf-8")
    found = findings_for(tmp_path, "md.duplicate-heading")
    assert len(found) == 1 and found[0]["line"] == 12


# --------------------------------------------------------------------------- #
# Drift
# --------------------------------------------------------------------------- #

def test_inventory_drift_missing_dir(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        'ITEMS = [{"id": "x", "dir": "skills/gone", "type": "skill"}]\n', encoding="utf-8")
    assert "inventory.drift" in codes(tmp_path)


def test_inventory_drift_unregistered_skill(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text('ITEMS = []\n', encoding="utf-8")
    (tmp_path / "skills" / "stray").mkdir(parents=True)
    assert "inventory.drift" in codes(tmp_path)


def test_inventory_clean(tmp_path: Path) -> None:
    (tmp_path / "skills" / "foo").mkdir(parents=True)
    (tmp_path / "setup.py").write_text(
        'ITEMS = [{"id": "foo", "dir": "skills/foo", "type": "skill"}]\n', encoding="utf-8")
    assert "inventory.drift" not in codes(tmp_path)


def test_ci_missing_ref(tmp_path: Path) -> None:
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("jobs:\n  t:\n    steps:\n      - run: python .github/scripts/gone.py\n",
                               encoding="utf-8")
    assert "ci.missing-ref" in codes(tmp_path)


# --------------------------------------------------------------------------- #
# Model / rendering
# --------------------------------------------------------------------------- #

def test_every_finding_code_has_a_rule(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def x(:\n", encoding="utf-8")
    (tmp_path / "old.bak").write_text("x", encoding="utf-8")
    result = scan(tmp_path, ScanOptions(ignore=()))
    assert result["findings"]
    for f in result["findings"]:
        assert f["code"] in RULES, f"unmapped code: {f['code']}"
        assert f["severity"] in {"CRITICAL", "MAJOR", "MINOR", "SUGGESTION"}


def test_clean_tree_reports_zero(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def f() -> int:\n    return 1\n", encoding="utf-8")
    result = scan(tmp_path, ScanOptions(ignore=()))
    assert result["findings"] == []
    assert "Sin hallazgos" in render_md(result)


def test_findings_sorted_by_severity(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def x(:\n", encoding="utf-8")  # CRITICAL
    (tmp_path / "note.md").write_text("Some `XXX` placeholder only.\n", encoding="utf-8")
    (tmp_path / "old.bak").write_text("x", encoding="utf-8")  # MINOR
    result = scan(tmp_path, ScanOptions(ignore=()))
    sevs = [f["severity"] for f in result["findings"]]
    order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "SUGGESTION": 3}
    assert sevs == sorted(sevs, key=lambda s: order[s])


def test_scan_real_repo_has_no_criticals() -> None:
    repo = Path(__file__).resolve().parents[3]
    result = scan(repo)
    assert result["files_scanned"] > 50
    assert result["counts"]["CRITICAL"] == 0
