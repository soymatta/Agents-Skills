"""Inline parser and document generator for academic output.

Usage:
    from generate_outputs import split_inline, tokens_to_html

    html = tokens_to_html(split_inline("mcd(_a_, _b_)"))
    # -> 'mcd(<em>a</em>, <em>b</em>)'

Standalone:
    python generate_outputs.py --file input.md --norm "APA 7th"
"""

from __future__ import annotations

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


# ── Document Generator ────────────────────────────────────────────────────────


def parse_frontmatter(text: str) -> dict:
    """Extract YAML-like frontmatter from markdown text."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    front: dict = {}
    for line in m.group(1).strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            front[key.strip()] = val.strip().strip('"').strip("'")
    return front


def generate_title_page_html(front: dict) -> str:
    """Generate APA 7th title page HTML from frontmatter."""
    title = front.get("TITLE", "Untitled")
    author = front.get("AUTHOR", "")
    institution = front.get("INSTITUTION", "")
    program = front.get("PROGRAM", "")
    course = front.get("COURSE", "")
    professor = front.get("PROFESSOR", "")
    date = front.get("DATE", "")

    items = [i for i in [title, author, institution, program, course, professor, date] if i]
    elements = "\n".join(f'      <div class="title-item">{i}</div>' for i in items)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: letter; margin: 1in; }}
  body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; line-height: 2.0; }}
  .title-page {{
    display: flex; flex-direction: column; justify-content: space-evenly;
    align-items: center; height: 9in; text-align: center;
  }}
  .title-item:first-child {{ font-weight: bold; }}
</style>
</head>
<body>
<section class="title-page">
{elements}
</section>
</body>
</html>"""


def generate_toc_html(headings: list[tuple[int, str, int]]) -> str:
    """Generate Table of Contents HTML from heading data.

    Args:
        headings: list of (level, text, page_number) tuples.
    """
    lines = [
        '<div class="toc-page">',
        '  <h1 class="toc-title">Table of Contents</h1>',
        '  <div class="toc-entries">',
    ]
    for level, text, page in headings:
        dots = "." * (50 - len(text) - len(str(page)))
        pad = (level - 1) * 20
        lines.append(f'  <div class="toc-entry" style="padding-left:{pad}px;">{text} {dots} {page}</div>')
    lines.append("  </div>")
    lines.append("</div>")
    return "\n".join(lines)


def generate_docx_titlepage_xml(front: dict) -> str:
    """Generate python-docx compatible XML for APA title page spacing."""
    items = [
        front.get("TITLE", ""),
        front.get("AUTHOR", ""),
        front.get("INSTITUTION", ""),
        front.get("PROGRAM", ""),
        front.get("COURSE", ""),
        front.get("PROFESSOR", ""),
        front.get("DATE", ""),
    ]
    items = [i for i in items if i]

    xml_parts: list[str] = []
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        xml_parts.append(
            f"""<w:p>
  <w:pPr>
    <w:spacing w:before="72" w:after="{72 if is_last else 0}" w:line="480" w:lineRule="auto"/>
    <w:jc w:val="center"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
      <w:sz w:val="24"/>
      <w:b w:val="{1 if i == 0 else 0}"/>
    </w:rPr>
    <w:t xml:space="preserve">{item}</w:t>
  </w:r>
</w:p>"""
        )
    return "\n".join(xml_parts)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Document generator for academic output.")
    parser.add_argument("--file", type=str, help="Input markdown file")
    parser.add_argument("--norm", type=str, default="APA 7th", help="Citation norm")
    parser.add_argument("--html", action="store_true", help="Output HTML")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text("utf-8")
        front = parse_frontmatter(text)
        if args.html:
            print(generate_title_page_html(front))
        else:
            print(json.dumps(front, indent=2, ensure_ascii=False))
    else:
        tests = ["mcd(_a_, _b_)", "_r_{0}", "_M_^{e}", "2^{255}", "**bold**"]
        for t in tests:
            tokens = split_inline(t)
            html = tokens_to_html(tokens)
            print(f"{t:30s} -> {html}")


if __name__ == "__main__":
    main()
