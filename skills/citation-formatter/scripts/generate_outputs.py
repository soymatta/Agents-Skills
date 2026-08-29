"""Inline parser and full academic document generator.

Usage:
    from generate_outputs import split_inline, tokens_to_html

    html = tokens_to_html(split_inline("mcd(_a_, _b_)"))
    # -> 'mcd(<em>a</em>, <em>b</em>)'

Standalone (HTML full document):
    python generate_outputs.py --file input.md --html --out output.html
    python generate_outputs.py --file input.md --html          # writes input.md.html

Standalone (DOCX): requires python-docx
    python generate_outputs.py --file input.md --docx --out output.docx

Standalone (default: self-test of the inline parser):
    python generate_outputs.py

Frontmatter keys consumed (YAML-like, single ``:`` per line):
    TITLE, AUTHOR, INSTITUTION, PROGRAM, COURSE, PROFESSOR, DATE,
    TOC (\"true\"), NORM (\"APA 7th\" | \"IEEE\" | \"Vancouver\").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


# ── Types ─────────────────────────────────────────────────────────────────────


class Token(NamedTuple):
    kind: str
    value: str


# ── Inline Parser ─────────────────────────────────────────────────────────────
#
# The parser understands this custom notation:
#   _text_          → italic       (<em>)
#   **text**        → bold         (<strong>)
#   ^{text}         → superscript  (<sup>)
#   _{text}         → subscript    (<sub>)
#   _X_{y}          → italic + sub (<em>X</em><sub>y</sub>)
#   _X_^{y}         → italic + sup (<em>X</em><sup>y</sup>)
#   \_              → literal underscore
#
# All patterns use named groups so we can extract content by name.
# Note: TEXT excludes ^ so that ^{...} can be picked up by SUP.


_TOKEN_SPEC = [
    ("ESC",     r"\\_"),                                   # \_
    ("ISUP",    r"_(?P<isup_var>[^_{}]*?)_\^{(?P<isup_sup>[^}]*)}"),  # _X_^{y}
    ("ISUB",    r"_(?P<isub_var>[^_{}]*?)_{(?P<isub_sub>[^}]*)}"),    # _X_{y}
    ("BOLD",    r"\*\*(?P<bold_t>[^*]+)\*\*"),                         # **text**
    ("ITALIC",  r"_(?P<ital_t>[^_]+)_"),                               # _text_
    ("SUP",     r"\^{(?P<sup_t>[^}]*)}"),                              # ^{text}
    ("SUB",     r"_{(?P<sub_t>[^}]*)}"),                              # _{text}
    ("TEXT",    r"[^\^_*{}\\n]+"),                                     # plain text
    ("CHAR",    r"."),                                                  # single other char
]

TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC))


# Maps token kinds to their content group names (for simple 1-group patterns)
_CONTENT_GROUP: dict[str, str] = {
    "BOLD": "bold_t",
    "ITALIC": "ital_t",
    "SUP": "sup_t",
}


def split_inline(text: str) -> list[Token]:
    """Tokenize inline text into structured tokens."""
    tokens: list[Token] = []

    for match in TOKEN_RE.finditer(text):
        kind = match.lastgroup

        if kind == "ESC":
            tokens.append(Token("text", "_"))

        elif kind == "ISUB":
            var = match.group("isub_var")
            sub = match.group("isub_sub")
            tokens.append(Token("italic_sub", f"{var}|{sub}"))

        elif kind == "ISUP":
            var = match.group("isup_var")
            sup = match.group("isup_sup")
            tokens.append(Token("italic_sup", f"{var}|{sup}"))

        elif kind in _CONTENT_GROUP:
            tokens.append(Token(kind.lower(), match.group(_CONTENT_GROUP[kind])))

        elif kind in ("TEXT", "CHAR"):
            tokens.append(Token("text", match.group(0)))

    return tokens


def tokens_to_html(tokens: list[Token]) -> str:
    """Convert tokens to HTML string."""
    parts: list[str] = []
    for t in tokens:
        if t.kind == "text":
            parts.append(t.value)
        elif t.kind == "italic":
            parts.append(f"<em>{t.value}</em>")
        elif t.kind == "bold":
            parts.append(f"<strong>{t.value}</strong>")
        elif t.kind == "sup":
            parts.append(f"<sup>{t.value}</sup>")
        elif t.kind == "sub":
            parts.append(f"<sub>{t.value}</sub>")
        elif t.kind == "italic_sub":
            var, sub = t.value.split("|", 1)
            parts.append(f"<em>{var}</em><sub>{sub}</sub>")
        elif t.kind == "italic_sup":
            var, sup = t.value.split("|", 1)
            parts.append(f"<em>{var}</em><sup>{sup}</sup>")
    return "".join(parts)


# ── Markdown helpers ──────────────────────────────────────────────────────────


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_inline(text: str) -> str:
    """Escape HTML then apply the inline math notation to the result."""
    return tokens_to_html(split_inline(_html_escape(text)))


def markdown_to_html(text: str) -> str:
    """Very light Markdown → HTML for the document body.

    Handles headings (#..####), unordered lists, horizontal rules and
    paragraphs. Everything else (tables, code blocks) is passed through as
    escaped text. Inline notation is applied per line.
    """
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = min(len(m.group(1)), 6)
            out.append(f"<h{level}>{render_inline(m.group(2))}</h{level}>")
            continue
        if re.match(r"^\s*[-*]\s+", line):
            out.append(f"<li>{render_inline(line.strip()[1:].strip())}</li>")
            continue
        if re.match(r"^\s*---+\s*$", line):
            out.append("<hr>")
            continue
        out.append(f"<p>{render_inline(line)}</p>")
    return "\n".join(out)


def extract_headings(text: str) -> list[tuple[int, str]]:
    """Collect (level, text) for markdown headings, in order."""
    headings: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            # Undo escaping so the TOC shows raw text.
            headings.append((min(len(m.group(1)), 6), m.group(2)))
    return headings


# ── Frontmatter / document generation ─────────────────────────────────────────


def parse_frontmatter(text: str) -> dict:
    """Extract YAML-like frontmatter from markdown text (single ``:`` per line)."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    front: dict = {}
    for line in m.group(1).strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            front[key.strip()] = val.strip().strip('"').strip("'")
    return front


_TITLE_ITEMS = ("TITLE", "AUTHOR", "INSTITUTION", "PROGRAM", "COURSE", "PROFESSOR", "DATE")


def generate_title_page_html(front: dict) -> str:
    """Generate APA 7th title page HTML from frontmatter."""
    title = _html_escape(front.get("TITLE", "Untitled"))
    items = [_html_escape(front.get(k, "")) for k in _TITLE_ITEMS if front.get(k)]
    elements = "\n".join(f'      <div class="title-item">{i}</div>' for i in items)

    return f"""<section class="title-page">
{elements}
</section>"""


def generate_toc_html(headings: list[tuple[int, str]]) -> str:
    """Generate Table of Contents HTML.

    Args:
        headings: list of (level, text) tuples, in document order.
    """
    lines = [
        '<section class="toc-page">',
        '  <h1 class="toc-title">Table of Contents</h1>',
        '  <div class="toc-entries">',
    ]
    for level, text in headings:
        pad = (level - 1) * 24
        cleaned = _html_escape(text.replace("\\_", "_"))
        lines.append(
            f'  <div class="toc-entry" style="padding-left:{pad}px;">{cleaned}</div>'
        )
    lines.append("  </div>")
    lines.append("</section>")
    return "\n".join(lines)


def generate_docx(front: dict, body_md: str, out_path: Path) -> None:
    """Render a DOCX via python-docx if available.

    Raises RuntimeError with instructions if python-docx is not installed.
    The body is written as plain paragraphs; the APA title page is written
    first with the documented equal-spacing (72pt before/after).
    """
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "python-docx is required for --docx output. "
            "Install it with `pip install python-docx`."
        )

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    is_apa = front.get("NORM", "APA 7th") == "APA 7th"
    if is_apa:
        items = [front.get(k, "") for k in _TITLE_ITEMS if front.get(k)]
        for i, item in enumerate(items):
            p = doc.add_paragraph(item)
            p.alignment = 1  # center
            pf = p.paragraph_format
            pf.space_before = Pt(72)
            pf.space_after = Pt(0 if i < len(items) - 1 else 72)
            if i == 0:
                for run in p.runs:
                    run.bold = True

    for raw in body_md.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            h = doc.add_heading("", level=min(len(m.group(1)), 6))
            h.add_run(m.group(2))
            continue
        p = doc.add_paragraph()
        p.add_run(line.lstrip("# "))

    doc.save(str(out_path))


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Academic document generator.")
    parser.add_argument("--file", type=str, help="Input markdown file")
    parser.add_argument("--norm", type=str, default="APA 7th", help="Citation norm (unused here, kept for CLI compat)")
    parser.add_argument("--html", action="store_true", help="Output a full HTML document")
    parser.add_argument("--docx", action="store_true", help="Output a DOCX document")
    parser.add_argument("--out", type=str, help="Output path (default: <file>.<ext>)")
    args = parser.parse_args()

    if not args.file:
        tests = ["mcd(_a_, _b_)", "_r_{0}", "_M_^{e}", "2^{255}", "**bold**"]
        for t in tests:
            html = tokens_to_html(split_inline(t))
            print(f"{t:30s} -> {html}")
        return

    text = Path(args.file).read_text("utf-8")
    front = parse_frontmatter(text)
    body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)

    if args.docx:
        out = Path(args.out) if args.out else Path(args.file).with_suffix(".docx")
        generate_docx(front, body, out)
        print(f"wrote {out}")
        return

    if args.html:
        title = _html_escape(front.get("TITLE", "Untitled"))
        headings = extract_headings(body)

        parts: list[str] = []
        if front.get("NORM", "APA 7th") == "APA 7th":
            # APA 7th mandates page 1 as the title page.
            parts.append('<div class="page title-page-wrap">')
            parts.append(generate_title_page_html(front))
            parts.append("</div>")

        if front.get("TOC", "").strip().lower() == "true":
            parts.append('<div class="page toc-page-wrap">')
            parts.append(generate_toc_html(headings))
            parts.append("</div>")

        parts.append('<div class="page body-page">')
        parts.append(markdown_to_html(body))
        parts.append("</div>")

        doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: letter; margin: 1in; }}
  body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; line-height: 2.0; }}
  .page {{ page-break-after: always; }}
  .title-page {{
    display: flex; flex-direction: column; justify-content: space-evenly;
    align-items: center; height: 9in; text-align: center;
  }}
  .title-item:first-child {{ font-weight: bold; }}
  .toc-title {{ text-align: center; font-size: 12pt; }}
  .toc-entry {{ padding-left: 0; }}
  .body-page p {{ margin: 0 0 0.4em; }}
  h1, h2, h3, h4 {{ margin: 1em 0 0.5em; }}
  .references {{ padding-left: 2.54cm; text-indent: -2.54cm; }} /* hanging indent */
</style>
</head>
<body>
{"\n".join(parts)}
</body>
</html>"""
        out = Path(args.out) if args.out else Path(args.file).with_suffix(".html")
        out.write_text(doc, "utf-8")
        print(f"wrote {out}")
        return

    print(json.dumps(front, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
