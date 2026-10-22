#!/usr/bin/env python3
"""Deterministic project scanner for the ``init-review`` command.

Runs a fast, LLM-free pass over a project and emits structured findings
(JSON + Markdown). It replaces the expensive "read everything, reason about
it" part of the onboarding scan with cheap, reproducible checks; the model
only reads the compact findings file (the handoff channel to the builder agent).

Design goals
------------
- **Stdlib only** (no install, runs anywhere Python 3.9+ runs).
- **Read-only on the audited project**: it never writes inside the target
  tree, except to the output paths the caller asks for (used as the handoff
  artifact).
- **Deterministic**: same tree in -> same findings out (stable ordering).

Usage
-----
    python scan_project.py [ROOT]                 # Markdown to stdout
    python scan_project.py [ROOT] --json f.json   # also write JSON findings
    python scan_project.py [ROOT] --md f.md       # also write Markdown
    python scan_project.py [ROOT] --fail-on-critical
    python scan_project.py [ROOT] --include-third-party --orphans --max-files 0

Finding shape::

    {"id": 1, "code": "syntax.python", "severity": "CRITICAL",
     "category": "blocker", "file": "a/b.py", "line": 12,
     "message": "...", "fix": "..."}

Categories map to the init-review report:
``blocker`` -> F2, ``pending`` -> F3, ``structure`` -> F4, ``drift`` -> F5 note.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "build", "dist", ".next",
    ".astro", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", "coverage", "htmlcov", ".idea", ".vscode", ".models", "hub",
    ".cache", ".eggs", "site-packages",
}

# Third-party / vendored trees never reported on (hard rule: do not touch them).
DEFAULT_IGNORE = (
    "skills/impeccable",
    "skills/skill-creator",
    "skills/ai-job-search",
    "skills/ui-ux-pro-max",
    ".opencode",
    "clones",
)

# Text extensions we are willing to parse.
TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json",
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".md", ".markdown", ".txt",
    ".sh", ".ps1", ".sql", ".html", ".css", ".mdc", ".astro", ".vue", ".svelte",
}

LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "cargo.lock", "uv.lock", "composer.lock", "gemfile.lock", "pipfile.lock",
}

BACKUP_SUFFIXES = (".bak", ".orig", ".old", ".tmp", ".rej")
BACKUP_NAMES = {"thumbs.db", ".ds_store"}

SEVERITY_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "SUGGESTION": 3}

# code -> (severity, category, human label)
RULES: dict[str, tuple[str, str, str]] = {
    "syntax.python":       ("CRITICAL", "blocker", "Python file fails to parse"),
    "syntax.json":         ("MAJOR", "blocker", "JSON file fails to parse"),
    "frontmatter.missing": ("MAJOR", "blocker", "SKILL.md/agent missing name or description frontmatter"),
    "empty.file":          ("MINOR", "blocker", "Empty file (0 bytes)"),
    "stub.body":           ("MINOR", "blocker", "Function body is only pass/.../NotImplementedError"),
    "doc.missing-script":  ("MAJOR", "blocker", "Doc references a script that does not exist"),
    "doc.broken-link":     ("MAJOR", "blocker", "Markdown relative link/image target not found"),
    "ci.missing-ref":      ("MAJOR", "blocker", "CI workflow references a missing file"),
    "todo.marker":         ("SUGGESTION", "pending", "TODO/FIXME/HACK/XXX marker"),
    "dir.empty":           ("MINOR", "structure", "Empty directory (no files anywhere beneath)"),
    "file.backup":         ("MINOR", "structure", "Backup/temp file left in the tree"),
    "file.duplicate":      ("SUGGESTION", "structure", "Duplicate file content"),
    "file.orphan":         ("SUGGESTION", "structure", "Source file never referenced anywhere"),
    "file.large":          ("SUGGESTION", "structure", "Large file (candidate to split)"),
    "md.table-orphan":     ("MINOR", "structure", "Table row separated from its table by a blank line"),
    "md.duplicate-heading":("SUGGESTION", "structure", "Duplicate heading text"),
    "inventory.drift":     ("MAJOR", "drift", "Declared inventory does not match the filesystem"),
}

_MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
_COMMENT_END_RE = re.compile(r"(#|//|/\*|<!--|;|\*)\s*$")
_SCRIPT_REF_RE = re.compile(r"[\w./\\-]+\.(?:py|mjs|sh|js)\b", re.IGNORECASE)
_MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_PRODUCT_NAME_RE = re.compile(r"^[A-Z][A-Za-z]+\.(?:js|ts)$")
_SCRIPT_DENY = {"node.js", "next.js", "three.js", "vue.js", "react.js", "nuxt.js",
                "alpine.js", "d3.js", "express.js", "socket.io", "crt.sh", "skills.sh",
                "commands.sh"}
_LINK_PLACEHOLDERS = {"url", "link", "path", "href", "target", "...", "\u2026",
                      "example", "your-url", "yourlink"}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class Finding:
    code: str
    file: str
    line: int
    message: str
    fix: str = ""

    @property
    def severity(self) -> str:
        return RULES.get(self.code, ("SUGGESTION", "structure", self.code))[0]

    @property
    def category(self) -> str:
        return RULES.get(self.code, ("SUGGESTION", "structure", self.code))[1]

    def as_dict(self, fid: int) -> dict:
        return {
            "id": fid,
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
        }


@dataclass
class ScanOptions:
    ignore: tuple[str, ...] = DEFAULT_IGNORE
    max_files: int = 5000
    large_bytes: int = 120_000
    include_orphans: bool = False


# --------------------------------------------------------------------------- #
# Filesystem helpers
# --------------------------------------------------------------------------- #

def _is_ignored(rel: str, ignore: tuple[str, ...]) -> bool:
    rel = rel.replace("\\", "/")
    for prefix in ignore:
        p = prefix.replace("\\", "/").strip("/")
        if rel == p or rel.startswith(p + "/"):
            return True
        if f"/{p}/" in f"/{rel}/":
            return True
    return False


def iter_files(root: Path, opts: ScanOptions) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if any(part in EXCLUDE_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        if _is_ignored(rel, opts.ignore):
            continue
        out.append(p)
        if opts.max_files and len(out) >= opts.max_files:
            break
    return out


def _rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def _read_text(p: Path, limit: int = 1_000_000) -> str | None:
    if p.suffix.lower() not in TEXT_SUFFIXES and p.name.lower() not in LOCKFILES:
        return None
    try:
        data = p.read_bytes()[:limit]
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1")
        except UnicodeDecodeError:
            return None


def _numbered_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(original_line_no, line)`` for lines outside fenced blocks.

    Keeping the original line numbers matters: findings must point at the
    real file:line, and stripping fences shifts every index after them.
    """
    out: list[tuple[int, str]] = []
    in_block = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_block = not in_block
            continue
        if not in_block:
            out.append((i, line))
    return out


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def check_empty_files(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.name == "__init__.py":  # empty package marker is expected
            continue
        rel = _rel(root, p)
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size == 0:
            out.append(Finding("empty.file", rel, 1, "File is 0 bytes.",
                               "Remove it if unused, or add the intended content."))
    return out


def check_python_syntax(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.suffix != ".py":
            continue
        text = _read_text(p)
        if text is None:
            continue
        try:
            ast.parse(text, filename=str(p))
        except SyntaxError as e:
            out.append(Finding("syntax.python", _rel(root, p), e.lineno or 0,
                               f"SyntaxError: {e.msg}",
                               "Fix the syntax; the module cannot be imported."))
    return out


def check_json(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.suffix.lower() != ".json" or p.name.lower() in LOCKFILES:
            continue
        text = _read_text(p)
        if text is None:
            continue
        try:
            json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            line = getattr(e, "lineno", 0) or 0
            out.append(Finding("syntax.json", _rel(root, p), line,
                               f"Invalid JSON: {e}",
                               "Repair the JSON; tooling that reads it will fail."))
    return out


def _frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m:
            data[m.group(1)] = m.group(2).strip()
    return data


def check_frontmatter(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        rel = _rel(root, p)
        if p.suffix.lower() not in (".md", ".markdown"):
            continue
        is_skill = p.name == "SKILL.md"
        is_agent = rel.startswith("agents/") or "/agents/" in rel
        if not (is_skill or is_agent):
            continue
        text = _read_text(p)
        if text is None:
            continue
        fm = _frontmatter(text)
        if fm is None:
            out.append(Finding("frontmatter.missing", rel, 1, "No YAML frontmatter block.",
                               "Add `--- name/description ---`; discoverers skip it otherwise."))
            continue
        missing = [k for k in ("name", "description") if not fm.get(k)]
        if missing:
            out.append(Finding("frontmatter.missing", rel, 1,
                               f"Frontmatter missing: {', '.join(missing)}.",
                               "Add the missing key(s) so the agent/skill can be discovered."))
    return out


def check_stub_bodies(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.suffix != ".py":
            continue
        text = _read_text(p)
        if text is None:
            continue
        try:
            tree = ast.parse(text, filename=str(p))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = [n for n in node.body if not (isinstance(n, ast.Expr)
                        and isinstance(getattr(n, "value", None), ast.Constant)
                        and isinstance(n.value.value, str))]
                if len(body) == 1:
                    n0 = body[0]
                    stub = isinstance(n0, ast.Pass) or \
                        (isinstance(n0, ast.Expr) and isinstance(getattr(n0, "value", None), ast.Constant)
                         and n0.value.value is Ellipsis) or \
                        (isinstance(n0, ast.Raise) and isinstance(n0.exc, ast.Call)
                         and getattr(n0.exc.func, "id", "") == "NotImplementedError")
                    if stub:
                        out.append(Finding("stub.body", _rel(root, p), node.lineno,
                                           f"`{node.name}` has a stub body.",
                                           "Implement it or mark it explicitly as a placeholder."))
    return out


def _is_marker_line(line: str, m: re.Match) -> bool:
    """A real marker is either followed by ``:``/``(``/end-of-line, or sits
    right after a comment delimiter. This drops Spanish "TODO" (all), doc
    lines that merely list the marker names, and placeholder ``XXX``."""
    after = line[m.end():]
    if after[:1] in (":", "(", "!", "?") or after.strip() == "":
        return True
    return bool(_COMMENT_END_RE.search(line[:m.start()]))


def check_markers(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        text = _read_text(p)
        if text is None:
            continue
        rel = _rel(root, p)
        for i, line in enumerate(text.splitlines(), 1):
            for m in _MARKER_RE.finditer(line):
                if not _is_marker_line(line, m):
                    continue
                token = m.group(1)
                out.append(Finding("todo.marker", rel, i,
                                   f"{token}: {line.strip()[:120]}",
                                   "Resolve the marker or convert it into a tracked task."))
                break
    return out


def _script_basenames(root: Path) -> set[str]:
    """Collect basenames of all script files in the repo (excluding only system dirs).
    
    Used for resolving doc references; must include third-party/vendored scripts
    so references to them don't false-positive as missing.
    """
    names = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            continue
        # Only skip system/excluded dirs, NOT third-party ignore list
        if any(part in EXCLUDE_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        if p.suffix.lower() in {".py", ".mjs", ".sh", ".js"}:
            names.add(p.name.lower())
    return names


def check_doc_script_refs(root: Path, files: list[Path]) -> list[Finding]:
    available = _script_basenames(root)
    out = []
    for p in files:
        if p.suffix.lower() not in (".md", ".markdown"):
            continue
        text = _read_text(p)
        if text is None:
            continue
        for i, line in _numbered_lines(text):
            for m in _SCRIPT_REF_RE.finditer(line):
                tok = m.group(0)
                base = tok.replace("\\", "/").rsplit("/", 1)[-1].lower()
                if tok.startswith(".") or tok.startswith("http"):
                    continue
                if _PRODUCT_NAME_RE.match(tok) or base in _SCRIPT_DENY:
                    continue
                if base not in available:
                    out.append(Finding("doc.missing-script", _rel(root, p), i,
                                       f"References `{tok}` which is not in the repo.",
                                       "Ship the script or fix the reference."))
                    break  # one per file is enough noise control
    return out


def check_md_links(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.suffix.lower() not in (".md", ".markdown"):
            continue
        text = _read_text(p)
        if text is None:
            continue
        for i, line in _numbered_lines(text):
            for m in _MD_LINK_RE.finditer(line):
                target = m.group(1).strip().split("#", 1)[0].split(" ", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:", "#", "/", "data:")):
                    continue
                if target.lower() in _LINK_PLACEHOLDERS or ("." not in target and "/" not in target):
                    continue
                resolved = (p.parent / target).resolve()
                if not resolved.exists():
                    out.append(Finding("doc.broken-link", _rel(root, p), i,
                                       f"Link target not found: `{target}`",
                                       "Fix the path or the file it points to."))
    return out


def check_ci_refs(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        rel = _rel(root, p)
        if ".github/workflows/" not in rel or p.suffix.lower() not in (".yml", ".yaml"):
            continue
        text = _read_text(p)
        if text is None:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in _SCRIPT_REF_RE.finditer(line):
                tok = m.group(0)
                if tok.startswith(("http", "$", "actions/", ".client.", ".server.")):
                    continue
                if tok.startswith((".github/", "scripts/", "skills/", "tools/")) \
                        and not (root / tok).exists():
                    out.append(Finding("ci.missing-ref", rel, i,
                                       f"Workflow references `{tok}` which does not exist.",
                                       "Create the file or fix the CI path."))
    return out


def check_empty_dirs(root: Path, opts: ScanOptions) -> list[Finding]:
    out = []
    for d in sorted(root.rglob("*")):
        if not d.is_dir():
            continue
        rel = _rel(root, d)
        if _is_ignored(rel, opts.ignore):
            continue
        if any(part in EXCLUDE_DIRS for part in d.relative_to(root).parts):
            continue
        has_file = any(child.is_file() for child in d.rglob("*"))
        if not has_file:
            out.append(Finding("dir.empty", rel, 0, "Directory contains no files.",
                               "Remove it, or add the file it was meant to hold."))
    return out


def check_backup_files(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        low = p.name.lower()
        if low.endswith(BACKUP_SUFFIXES) or low.endswith("~") or low in BACKUP_NAMES:
            out.append(Finding("file.backup", _rel(root, p), 1,
                               "Backup/temp artifact.", "Delete it; it is not source."))
    return out


def check_duplicate_files(root: Path, files: list[Path]) -> list[Finding]:
    by_hash: dict[str, list[Path]] = {}
    for p in files:
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size == 0 or size > 200_000:
            continue
        try:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
        by_hash.setdefault(digest, []).append(p)
    out = []
    for digest, group in by_hash.items():
        if len(group) < 2:
            continue
        names = ", ".join(_rel(root, g) for g in group[:4])
        for g in group[1:]:
            out.append(Finding("file.duplicate", _rel(root, g), 1,
                               f"Identical to {_rel(root, group[0])} ({names}).",
                               "Consolidate into a single source of truth."))
    return out


def check_large_files(root: Path, files: list[Path], opts: ScanOptions) -> list[Finding]:
    out = []
    for p in files:
        if p.name.lower() in LOCKFILES:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size >= opts.large_bytes:
            out.append(Finding("file.large", _rel(root, p), 0,
                               f"{size // 1024} KB.", "Consider splitting or generating it."))
    return out


def _table_orphans(numbered: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """A table row that got separated from its table by a blank line.

    Detected as: a ``|``-line whose only gap to the previous ``|``-line is
    blank line(s), and which is neither a separator row nor the header of a
    new table (a header is always followed by a separator row).
    """
    out = []
    last_pipe_idx: int | None = None
    for idx, (line_no, line) in enumerate(numbered):
        if not line.lstrip().startswith("|"):
            continue
        if last_pipe_idx is not None and idx > last_pipe_idx + 1:
            between = numbered[last_pipe_idx + 1:idx]
            if between and all(l.strip() == "" for _, l in between):
                nxt = numbered[idx + 1][1] if idx + 1 < len(numbered) else ""
                if not _SEPARATOR_RE.match(line) and not _SEPARATOR_RE.match(nxt):
                    out.append((line_no, line.strip()[:100]))
        last_pipe_idx = idx
    return out


def check_md_tables(root: Path, files: list[Path]) -> list[Finding]:
    out = []
    for p in files:
        if p.suffix.lower() not in (".md", ".markdown"):
            continue
        text = _read_text(p)
        if text is None:
            continue
        for line_no, snippet in _table_orphans(_numbered_lines(text)):
            out.append(Finding("md.table-orphan", _rel(root, p), line_no,
                               f"Row detached from its table: {snippet}",
                               "Remove the blank line above it to rejoin the table."))
    return out


def check_md_headings(root: Path, files: list[Path]) -> list[Finding]:
    """Flag a heading text repeated under the *same* parent section.

    Repeats under different parents (e.g. ``### Steps`` inside every
    ``## Workflow``) are a normal doc pattern, not a defect.
    """
    out = []
    heading_re = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
    for p in files:
        if p.suffix.lower() not in (".md", ".markdown"):
            continue
        text = _read_text(p)
        if text is None:
            continue
        # stack of (level, text) ancestors; key = (parent path, level, text)
        stack: list[tuple[int, str]] = []
        seen: dict[tuple, int] = {}
        for i, line in _numbered_lines(text):
            m = heading_re.match(line)
            if not m:
                continue
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = tuple(t for _, t in stack)
            key = (parent, level, title.lower())
            if key in seen:
                out.append(Finding("md.duplicate-heading", _rel(root, p), i,
                                   f"Heading `{title}` repeated in the same section (line {seen[key]}).",
                                   "Merge or rename one of the headings."))
            else:
                seen[key] = i
            stack.append((level, title))
    return out


def check_inventory_drift(root: Path, files: list[Path]) -> list[Finding]:
    setup = root / "setup.py"
    if not setup.is_file():
        return []
    text = _read_text(setup)
    if not text or "ITEMS" not in text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    items: list[dict] = []
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "ITEMS" for t in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "ITEMS":
            value = node.value
        if isinstance(value, ast.List):
            for elt in value.elts:
                if isinstance(elt, ast.Dict):
                    d = {k.value: v.value for k, v in zip(elt.keys, elt.values)
                         if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}
                    items.append(d)
    out = []
    for it in items:
        src = it.get("dir")
        if not src:
            continue
        target = root / src
        if not target.exists():
            out.append(Finding("inventory.drift", "setup.py", 0,
                               f"Item `{it.get('id', src)}` -> `{src}` does not exist.",
                               "Create the source or drop the ITEMS entry."))
    # skills on disk but not registered
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        declared = {str(it.get("dir", "")).replace("\\", "/") for it in items}
        for child in sorted(skills_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            rel = f"skills/{child.name}"
            if rel not in declared and not any(d.startswith(rel + "/") for d in declared):
                out.append(Finding("inventory.drift", "setup.py", 0,
                                   f"`{rel}` exists on disk but is not in ITEMS.",
                                   "Register it or remove the directory."))
    return out


def _orphan_files(root: Path, files: list[Path], opts: ScanOptions) -> list[Finding]:
    # Heuristic: a source file whose basename is never mentioned in any
    # non-excluded text file. High false-positive rate -> opt-in only.
    corpus = []
    for p in files:
        text = _read_text(p)
        if text:
            corpus.append(text)
    blob = "\n".join(corpus).lower()
    out = []
    for p in files:
        if p.suffix.lower() not in {".py", ".js", ".mjs", ".ts", ".sh", ".ps1"}:
            continue
        name = p.name.lower()
        if p.name in {"setup.py", "conftest.py", "__init__.py", "index.js", "index.ts"}:
            continue
        stem = p.stem.lower()
        if blob.count(name) <= 1 and blob.count(stem) <= 1:
            out.append(Finding("file.orphan", _rel(root, p), 0,
                               "No reference to this file found in the tree.",
                               "Confirm it is used; otherwise remove (structural, opt-in check)."))
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def scan(root: Path, opts: ScanOptions | None = None) -> dict:
    opts = opts or ScanOptions()
    root = root.resolve()
    files = iter_files(root, opts)
    findings: list[Finding] = []
    for fn in (
        lambda: check_empty_files(root, files),
        lambda: check_python_syntax(root, files),
        lambda: check_json(root, files),
        lambda: check_frontmatter(root, files),
        lambda: check_stub_bodies(root, files),
        lambda: check_doc_script_refs(root, files),
        lambda: check_md_links(root, files),
        lambda: check_ci_refs(root, files),
        lambda: check_markers(root, files),
        lambda: check_empty_dirs(root, opts),
        lambda: check_backup_files(root, files),
        lambda: check_duplicate_files(root, files),
        lambda: check_large_files(root, files, opts),
        lambda: check_md_tables(root, files),
        lambda: check_md_headings(root, files),
        lambda: check_inventory_drift(root, files),
    ):
        findings.extend(fn())
    if opts.include_orphans:
        findings.extend(_orphan_files(root, files, opts))

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.category, f.file, f.line))

    items = [f.as_dict(i + 1) for i, f in enumerate(findings)]
    counts: dict[str, int] = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "SUGGESTION": 0}
    by_category: dict[str, int] = {}
    for it in items:
        counts[it["severity"]] = counts.get(it["severity"], 0) + 1
        by_category[it["category"]] = by_category.get(it["category"], 0) + 1
    return {
        "root": str(root),
        "files_scanned": len(files),
        "counts": counts,
        "by_category": by_category,
        "findings": items,
    }


_CATEGORY_TITLE = {
    "blocker": "Bloqueantes (F2)",
    "pending": "Pendientes (F3)",
    "structure": "Estructura / archivos optimizables (F4)",
    "drift": "Deriva de inventario/docs (F5)",
}


def render_md(result: dict) -> str:
    counts = result["counts"]
    total = sum(counts.values())
    health = "Saludable"
    if counts.get("CRITICAL"):
        health = "Roto"
    elif counts.get("MAJOR"):
        health = "Con problemas"
    lines = [
        "## Scan deterministico",
        f"Raiz: `{result['root']}` - {result['files_scanned']} archivos.",
        f"Hallazgos: {total} "
        f"(CRITICAL {counts.get('CRITICAL', 0)}, MAJOR {counts.get('MAJOR', 0)}, "
        f"MINOR {counts.get('MINOR', 0)}, SUGGESTION {counts.get('SUGGESTION', 0)}).",
        "",
    ]
    if total == 0:
        lines.append("Sin hallazgos: nada roto, nada pendiente, estructura limpia.")
        return "\n".join(lines)
    for cat in ("blocker", "pending", "structure", "drift"):
        group = [f for f in result["findings"] if f["category"] == cat]
        if not group:
            continue
        lines.append(f"## {_CATEGORY_TITLE[cat]}")
        for f in group:
            loc = f["file"] + (f":{f['line']}" if f["line"] else "")
            lines.append(f"- [{f['severity']}] (#{f['id']}) {loc} - {f['message']}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Deterministic init-review scanner.")
    ap.add_argument("root", nargs="?", default=".", help="project root (default: cwd)")
    ap.add_argument("--json", dest="json_path", help="write findings JSON here")
    ap.add_argument("--md", dest="md_path", help="write Markdown here")
    ap.add_argument("--format", choices=["md", "json", "both"], default="md")
    ap.add_argument("--max-files", type=int, default=5000, help="0 = no cap")
    ap.add_argument("--include-third-party", action="store_true",
                    help="do not skip vendored/third-party dirs")
    ap.add_argument("--orphans", action="store_true", help="enable the heuristic orphan check")
    ap.add_argument("--fail-on-critical", action="store_true", help="exit 1 if any CRITICAL")
    args = ap.parse_args(argv)

    opts = ScanOptions(
        ignore=() if args.include_third_party else DEFAULT_IGNORE,
        max_files=args.max_files,
        include_orphans=args.orphans,
    )
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    result = scan(root, opts)
    md = render_md(result)
    payload = json.dumps(result, indent=2, ensure_ascii=False)

    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    if args.md_path:
        out = Path(args.md_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")

    if args.format in ("json",):
        print(payload)
    elif args.format in ("both",):
        print(md)
        print(payload)
    else:
        print(md)

    if args.fail_on_critical and result["counts"].get("CRITICAL"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
