"""Tests for ui_gate.py (ui-ux-orchestrator deterministic gate).

Covers the quote/brace-aware tag scanner, every rule's positive and negative
case, the web-esenciales merge, comment handling, and the CLI exit codes.

Run: python -m pytest skills/ui-ux-orchestrator -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE_PATH = REPO_ROOT / "skills" / "ui-ux-orchestrator" / "scripts" / "ui_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("_ui_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_ui_gate"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _rules_for(tmp_path: Path, content: str, name: str = "index.html") -> set[str]:
    _write(tmp_path, name, content)
    report = gate.scan(tmp_path, with_essentials=False)
    return {f["rule"] for f in report["findings"]}


# ── tag scanner ───────────────────────────────────────────────────────────────


def test_tag_scanner_survives_jsx_arrow_function():
    text = '<img alt="hero" width={1} height={2} onClick={() => go()} />'
    tags = list(gate.iter_tags(text))
    assert len(tags) == 1
    name, _start, _end, tag = tags[0]
    assert name == "img"
    assert "onClick={() => go()}" in tag
    assert tag.endswith("/>")


def test_tag_scanner_keeps_gt_inside_quotes():
    text = '<img alt="a > b" width="1" height="1">'
    tags = list(gate.iter_tags(text))
    assert len(tags) == 1
    assert tags[0][3] == text


# ── rules ─────────────────────────────────────────────────────────────────────


def test_img_without_alt_is_blocker(tmp_path):
    _write(tmp_path, "index.html", "<img src='a.png' width='1' height='1'>")
    report = gate.scan(tmp_path, with_essentials=False)
    assert "img-alt" in {f["rule"] for f in report["findings"]}
    assert report["summary"]["BLOCKER"] == 1


def test_img_with_alt_but_no_dimensions_is_warn(tmp_path):
    rules = _rules_for(tmp_path, "<img src='a.png' alt='x'>")
    assert "img-dimensions" in rules
    assert "img-alt" not in rules


def test_img_spread_skips_alt_check(tmp_path):
    rules = _rules_for(tmp_path, "<img {...props} width={1} height={1} />")
    assert "img-alt" not in rules


def test_div_click_without_role_warns(tmp_path):
    rules = _rules_for(tmp_path, '<div onClick={() => x()}>hi</div>')
    assert "click-div" in rules


def test_div_click_with_role_is_ok(tmp_path):
    rules = _rules_for(tmp_path, '<div role="button" onClick={() => x()}>hi</div>')
    assert "click-div" not in rules


def test_html_without_lang_warns(tmp_path):
    assert "html-lang" in _rules_for(tmp_path, "<html><body></body></html>")


def test_html_with_lang_is_ok(tmp_path):
    assert "html-lang" not in _rules_for(tmp_path, '<html lang="es"><body></body></html>')


def test_viewport_zoom_is_blocker(tmp_path):
    html = '<meta name="viewport" content="width=device-width, user-scalable=no">'
    assert "viewport-zoom" in _rules_for(tmp_path, html)


def test_viewport_maximum_scale_is_blocker(tmp_path):
    html = '<meta name="viewport" content="width=device-width, maximum-scale=1">'
    assert "viewport-zoom" in _rules_for(tmp_path, html)


def test_viewport_without_zoom_lock_is_ok(tmp_path):
    html = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    assert "viewport-zoom" not in _rules_for(tmp_path, html)


def test_target_blank_without_rel_warns(tmp_path):
    assert "blank-noopener" in _rules_for(tmp_path, '<a href="x" target="_blank">x</a>')


def test_target_blank_with_noopener_is_ok(tmp_path):
    link = '<a href="x" target="_blank" rel="noopener noreferrer">x</a>'
    assert "blank-noopener" not in _rules_for(tmp_path, link)


def test_outline_none_warns_without_focus_visible(tmp_path):
    assert "outline-none" in _rules_for(tmp_path, "<style>.b{outline:none}</style>", "a.css")


def test_outline_none_suppressed_with_focus_visible(tmp_path):
    css = ".b{outline:none}.b:focus-visible{outline:2px solid blue}"
    assert "outline-none" not in _rules_for(tmp_path, css, "a.css")


def test_transition_all_warns(tmp_path):
    assert "transition-all" in _rules_for(tmp_path, ".b{transition: all .2s}", "a.css")


def test_paste_block_warns(tmp_path):
    tag = '<input onPaste={(e) => e.preventDefault()} />'
    assert "paste-block" in _rules_for(tmp_path, tag)


def test_autofocus_is_info(tmp_path):
    report = gate.scan(_write(tmp_path, "index.html", "<input autoFocus>"), with_essentials=False)
    assert report["summary"]["INFO"] == 1


def test_clean_file_has_no_findings(tmp_path):
    html = '<html lang="es"><body><img src="a.png" alt="x" width="1" height="1"></body></html>'
    report = gate.scan(_write(tmp_path, "index.html", html), with_essentials=False)
    assert report["findings"] == []
    assert report["summary"]["BLOCKER"] == 0


def test_html_comment_is_ignored(tmp_path):
    html = "<html lang='es'><!-- <img src='a.png'> --></html>"
    report = gate.scan(_write(tmp_path, "index.html", html), with_essentials=False)
    assert "img-alt" not in {f["rule"] for f in report["findings"]}


def test_minified_js_is_skipped(tmp_path):
    _write(tmp_path, "app.min.js", "outline:none;transition: all")
    assert gate.collect_files(tmp_path) == []


def test_root_named_dist_is_not_skipped(tmp_path):
    """Regression: `ui_gate.py dist/` must scan dist, not skip it as nested."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<img src='a.png'>", encoding="utf-8")
    report = gate.scan(dist, with_essentials=False)
    assert "img-alt" in {f["rule"] for f in report["findings"]}


def test_nested_skip_dir_is_skipped(tmp_path):
    nested = tmp_path / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "x.html").write_text("<img src='a.png'>", encoding="utf-8")
    assert gate.collect_files(tmp_path) == []


# ── merge + CLI ───────────────────────────────────────────────────────────────


def test_dir_scan_merges_essentials(tmp_path):
    _write(tmp_path, "index.html", "<html lang='es'><body>hola</body></html>")
    report = gate.scan(tmp_path, with_essentials=True)
    assert report["essentials"] is not None, "web-esenciales sibling must be found in-repo"
    assert report["essentials"]["total"] == 20
    assert isinstance(report["essentials"]["missing"], list)


def test_no_essentials_flag_disables_merge(tmp_path):
    _write(tmp_path, "index.html", "<html lang='es'><body>hola</body></html>")
    assert gate.scan(tmp_path, with_essentials=False)["essentials"] is None


def test_cli_exit_code_blocker(tmp_path, capsys):
    _write(tmp_path, "index.html", "<img src='a.png'>")
    code = gate.main([str(tmp_path), "--no-essentials"])
    assert code == 1


def test_cli_exit_code_clean(tmp_path):
    html = '<html lang="es"><body><img src="a.png" alt="x" width="1" height="1"></body></html>'
    _write(tmp_path, "index.html", html)
    assert gate.main([str(tmp_path), "--no-essentials"]) == 0


def test_cli_fail_on_never_always_zero(tmp_path):
    _write(tmp_path, "index.html", "<img src='a.png'>")
    assert gate.main([str(tmp_path), "--no-essentials", "--fail-on", "never"]) == 0


def test_cli_json_output(tmp_path, capsys):
    _write(tmp_path, "index.html", "<img src='a.png'>")
    gate.main([str(tmp_path), "--no-essentials", "--json"])
    import json

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["BLOCKER"] == 1
