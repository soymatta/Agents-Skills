"""Deterministic UI gate for the ui-ux-orchestrator skill.

Scans HTML / JSX / CSS / Vue / Svelte / Astro for the machine-checkable subset
of the Vercel Web Interface Guidelines, and (when pointed at a directory) merges
the `web-esenciales` 20-item business audit into the same prioritized report.

Design rule: only high-precision, no-judgment checks live here. Anything that
needs taste (hierarchy, tone, copy) stays in the `web-design-guidelines` and
`impeccable` prose. The script never invents an opinion (see the skill's
"Deterministic gate" section).

Usage:
    python ui_gate.py <path> [--json] [--fail-on blocker|warn|info|never]
                             [--no-essentials]

Exit code: 1 when any finding is at or above `--fail-on` (default: blocker),
else 0. Stdlib only.
"""

from __future__ import annotations

import argparse
import bisect
import importlib.util
import json
import re
import sys
from pathlib import Path

# ── scan scope ────────────────────────────────────────────────────────────────

SCAN_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".vue", ".svelte", ".astro",
}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt",
    ".svelte-kit", "coverage", "vendor", ".venv", "venv", "__pycache__",
    ".cache", ".turbo",
}
SKIP_SUFFIXES = (".min.js", ".min.css", ".map")

SEVERITY_ORDER = {"INFO": 1, "WARN": 2, "BLOCKER": 3}

# ── tag scanner (quote- and brace-aware, survives JSX arrow functions) ─────────

_TAG_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9:_-]*")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def iter_tags(text: str):
    """Yield (name, start, end, tag_text) for every opening tag in `text`.

    Attributes are walked while tracking quotes and JSX `{}` depth so a `>`
    inside `onClick={() => go()}` never truncates the tag.
    """
    i, n = 0, len(text)
    while i < n:
        lt = text.find("<", i)
        if lt < 0:
            return
        m = _TAG_NAME_RE.match(text, lt + 1)
        if not m:
            i = lt + 1
            continue
        j = m.end()
        depth, quote = 0, ""
        while j < n:
            c = text[j]
            if quote:
                if c == "\\":
                    j += 2
                    continue
                if c == quote:
                    quote = ""
            elif c in "\"'`":
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                if depth:
                    depth -= 1
            elif c == ">" and depth == 0:
                break
            j += 1
        if j >= n:
            return
        yield m.group(0).lower(), lt, j + 1, text[lt:j + 1]
        i = j + 1


def _has_attr(tag: str, name: str) -> bool:
    return re.search(r"(?:^|[\s{,(])" + re.escape(name) + r"\s*[:=]", tag, re.I) is not None


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            starts.append(idx + 1)
    return starts


# ── rules ─────────────────────────────────────────────────────────────────────
# Each rule returns (offset, rule_id, severity, message) tuples.

_VIEWPORT_ZOOM_RE = re.compile(
    r"user-scalable\s*[=:]\s*[\"']?\s*(?:no|0)\b"
    r"|maximum-scale\s*[=:]\s*[\"']?\s*1(?![\d.])",
    re.I,
)
_OUTLINE_RE = re.compile(r"outline\s*:\s*none|(?:^|[\s\"'`])outline-none(?:[\s\"'`;]|$)", re.I | re.M)
_TRANSITION_ALL_RE = re.compile(
    r"transition\s*:\s*all\b|(?:^|[\s\"'`])transition-all(?:[\s\"'`]|$)", re.I | re.M
)
_PASTE_RE = re.compile(r"onpaste\s*[:=]", re.I)
_PREVENT_DEFAULT_RE = re.compile(r"preventDefault", re.I)
_AUTOFOCUS_RE = re.compile(r"(?:^|[\s{])auto[Ff]ocus(?:[\s=}>/]|$)")


def _rules(text: str) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    tags = list(iter_tags(text))
    has_focus_visible = "focus-visible" in text

    for name, start, _end, tag in tags:
        if name == "img" and "{..." not in tag:
            if not _has_attr(tag, "alt"):
                findings.append((start, "img-alt", "BLOCKER",
                                 "img without alt (a11y): add alt, or alt=\"\" if decorative"))
            if not (_has_attr(tag, "width") and _has_attr(tag, "height")):
                findings.append((start, "img-dimensions", "WARN",
                                 "img without explicit width/height (CLS): set both"))
        if name in ("div", "span") and not _has_attr(tag, "role"):
            if re.search(r"\bonclick\s*[:=]", tag, re.I):
                findings.append((start, "click-div", "WARN",
                                 "div/span with a click handler: use <button>, or add role"))
        if name == "html" and not _has_attr(tag, "lang"):
            findings.append((start, "html-lang", "WARN",
                             "<html> without lang (a11y): declare the page language"))
        if name == "a" and re.search(r"target\s*[=:]\s*[\"']?_blank", tag, re.I):
            rel_attr = re.search(r"rel\s*[:=]\s*[\"']([^\"']*)", tag, re.I)
            rel_val = rel_attr.group(1).lower() if rel_attr else ""
            if "noopener" not in rel_val and "noreferrer" not in rel_val:
                findings.append((start, "blank-noopener", "WARN",
                                 "target=\"_blank\" without rel=\"noopener\" (tabnabbing)"))
        if name in ("input", "textarea", "form", "div") and _PASTE_RE.search(tag) \
                and _PREVENT_DEFAULT_RE.search(tag):
            findings.append((start, "paste-block", "WARN",
                             "onPaste + preventDefault blocks paste: never block it"))
        if _AUTOFOCUS_RE.search(tag):
            findings.append((start, "autofocus", "INFO",
                             "autoFocus: use sparingly, desktop-only single input"))

    if not has_focus_visible:
        for m in _OUTLINE_RE.finditer(text):
            findings.append((m.start(), "outline-none", "WARN",
                             "outline removed without a focus-visible replacement"))
    for m in _TRANSITION_ALL_RE.finditer(text):
        findings.append((m.start(), "transition-all", "WARN",
                         "transition: all -> list the properties explicitly"))
    for m in _VIEWPORT_ZOOM_RE.finditer(text):
        findings.append((m.start(), "viewport-zoom", "BLOCKER",
                         "viewport disables zoom (user-scalable/maximum-scale): a11y blocker"))
    return findings


# ── collection + scan ─────────────────────────────────────────────────────────


def collect_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        # Skip build/vendor dirs *below* the root, never the root itself
        # (so `ui_gate.py dist/` actually scans the build output).
        rel_parts = p.relative_to(root).parts[:-1]
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if p.name.endswith(SKIP_SUFFIXES):
            continue
        if p.suffix.lower() in SCAN_EXTENSIONS:
            out.append(p)
    return out


def scan(root: Path, with_essentials: bool = True) -> dict:
    files = collect_files(root)
    findings: list[dict] = []
    for path in files:
        try:
            text = path.read_text("utf-8", errors="replace")
        except OSError:
            continue
        # Blank out HTML comments in place (keeps byte offsets == line numbers).
        text = _COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
        starts = _line_starts(text)
        try:
            rel = str(path.relative_to(root)) if root.is_dir() else path.name
        except ValueError:
            rel = path.name
        for offset, rule, severity, message in _rules(text):
            findings.append({
                "file": rel,
                "line": bisect.bisect_right(starts, offset),
                "rule": rule,
                "severity": severity,
                "message": message,
            })

    findings.sort(key=lambda f: (-SEVERITY_ORDER[f["severity"]], f["file"], f["line"]))
    summary = {sev: sum(1 for f in findings if f["severity"] == sev) for sev in SEVERITY_ORDER}

    essentials = None
    if with_essentials and root.is_dir():
        audit = _load_essentials_audit()
        if audit is not None and any(p.suffix.lower() in (".html", ".htm") for p in files):
            result = audit(str(root))
            missing = [k for k, ok in result.items() if not ok]
            essentials = {
                "present": sum(result.values()),
                "total": len(result),
                "missing": missing,
            }

    return {
        "root": str(root),
        "files_scanned": len(files),
        "findings": findings,
        "summary": summary,
        "essentials": essentials,
    }


def _load_essentials_audit():
    """Import audit() from the sibling web-esenciales skill, if installed."""
    candidate = Path(__file__).resolve().parents[2] / "web-esenciales" / "scripts" / "check_web_esenciales.py"
    if not candidate.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_web_esenciales_check", candidate)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "audit", None)
    except Exception:  # noqa: BLE001 - a broken sibling must not crash the gate
        return None


# ── reporting ─────────────────────────────────────────────────────────────────


def render_text(report: dict) -> str:
    lines: list[str] = [f"UI gate report - {report['root']} ({report['files_scanned']} files)"]
    if not report["findings"]:
        lines.append("  no guideline findings")
    else:
        current = None
        for f in report["findings"]:
            if f["file"] != current:
                current = f["file"]
                lines.append("")
                lines.append(f"## {current}")
            lines.append(f"{f['file']}:{f['line']} - {f['severity']} {f['rule']}: {f['message']}")
    ess = report.get("essentials")
    if ess is not None:
        lines.append("")
        lines.append(f"## business must-haves (web-esenciales) {ess['present']}/{ess['total']}")
        lines.append("missing: " + (", ".join(ess["missing"]) if ess["missing"] else "none"))
    s = report["summary"]
    lines.append("")
    lines.append(f"Summary: {s['BLOCKER']} blockers, {s['WARN']} warnings, {s['INFO']} info")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic UI gate (ui-ux-orchestrator).")
    parser.add_argument("path", help="file or directory to scan")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--no-essentials", action="store_true",
                        help="skip the web-esenciales business audit merge")
    parser.add_argument("--fail-on", choices=["blocker", "warn", "info", "never"],
                        default="blocker", help="severity threshold for a non-zero exit")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    report = scan(root, with_essentials=not args.no_essentials)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))

    if args.fail_on == "never":
        return 0
    threshold = SEVERITY_ORDER[args.fail_on.upper()]
    return 1 if any(SEVERITY_ORDER[f["severity"]] >= threshold for f in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
