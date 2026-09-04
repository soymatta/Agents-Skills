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

Standalone (PDF): requires reportlab (pure Python)
    python generate_outputs.py --file input.md --pdf --out output.pdf

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
    ("ESC",     r"\\(?P<esc_t>[\\.!_])"),                                # \. \_ \!  → literal char
    ("ISUP",    r"_(?P<isup_var>[^_{}]*?)_\^{(?P<isup_sup>[^}]*)}"),  # _X_^{y}
    ("ISUB",    r"_(?P<isub_var>[^_{}]*?)_{(?P<isub_sub>[^}]*)}"),    # _X_{y}
    ("BOLDI",   r"\*\*\*(?P<bi_t>[^*]+)\*\*\*"),                        # ***text*** → bold+italic
    ("BOLD",    r"\*\*(?P<bold_t>[^*]+)\*\*"),                          # **text**
    ("LINK",    r"\[(?P<link_t>[^\]]+)\]\((?P<link_u>[^)]+)\)"),       # [text](url)
    ("STARIT",  r"\*(?P<starit_t>[^*]+)\*"),                            # *text* italic
    ("ITALIC",  r"_(?P<ital_t>[^\^_*{}\r\n]+?)_"),                      # _text_
    ("SUP",     r"\^{(?P<sup_t>[^}]*)}"),                               # ^{text}
    ("SUB",     r"_{(?P<sub_t>[^}]*)}"),                                # _{text}
    ("TEXT",    r"[^\^_*{}\r\n\\[\\]()]+"),                             # plain text
    ("CHAR",    r"."),                                                  # single other char
]

TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKEN_SPEC))


# Maps token kinds to their content group names (for simple 1-group patterns)
_CONTENT_GROUP: dict[str, str] = {
    "BOLD": "bold_t",
    "BOLDI": "bi_t",
    "ITALIC": "ital_t",
    "STARIT": "starit_t",
    "SUP": "sup_t",
    "SUB": "sub_t",
}


def split_inline(text: str) -> list[Token]:
    """Tokenize inline text into structured tokens."""
    tokens: list[Token] = []

    for match in TOKEN_RE.finditer(text):
        kind = match.lastgroup

        if kind == "ESC":
            tokens.append(Token("text", match.group("esc_t")))

        elif kind == "ISUB":
            var = match.group("isub_var")
            sub = match.group("isub_sub")
            tokens.append(Token("italic_sub", f"{var}|{sub}"))

        elif kind == "ISUP":
            var = match.group("isup_var")
            sup = match.group("isup_sup")
            tokens.append(Token("italic_sup", f"{var}|{sup}"))

        elif kind == "LINK":
            tokens.append(Token("link", f"{match.group('link_t')}|{match.group('link_u')}"))

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
        elif t.kind == "boldi":
            parts.append(f"<strong><em>{t.value}</em></strong>")
        elif t.kind == "link":
            text, url = t.value.split("|", 1)
            parts.append(f'<a href="{_html_escape(url)}">{_html_escape(text)}</a>')
        elif t.kind == "starit":
            parts.append(f"<em>{t.value}</em>")
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


# ── Inline → renderer-specific markup ─────────────────────────────────────────


def _rl_escape(text: str) -> str:
    """Escape text for reportlab Paragraph mini-markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tokens_to_reportlab(tokens: list[Token]) -> str:
    """Convert inline tokens to reportlab Paragraph mini-markup."""
    parts: list[str] = []
    for t in tokens:
        if t.kind == "text":
            parts.append(t.value)
        elif t.kind == "italic":
            parts.append(f"<i>{t.value}</i>")
        elif t.kind == "bold":
            parts.append(f"<b>{t.value}</b>")
        elif t.kind == "boldi":
            parts.append(f"<b><i>{t.value}</i></b>")
        elif t.kind == "link":
            text, url = t.value.split("|", 1)
            parts.append(f'<a href="{_rl_escape(url)}" color="#0000FF"><u>{_rl_escape(text)}</u></a>')
        elif t.kind == "starit":
            parts.append(f"<i>{t.value}</i>")
        elif t.kind == "sup":
            parts.append(f"<super>{t.value}</super>")
        elif t.kind == "sub":
            parts.append(f"<sub>{t.value}</sub>")
        elif t.kind == "italic_sub":
            var, sub = t.value.split("|", 1)
            parts.append(f"<i>{var}</i><sub>{sub}</sub>")
        elif t.kind == "italic_sup":
            var, sup = t.value.split("|", 1)
            parts.append(f"<i>{var}</i><super>{sup}</super>")
    return "".join(parts)


def _rl_text(text: str) -> str:
    """Escape then apply inline math notation for reportlab."""
    return tokens_to_reportlab(split_inline(_rl_escape(text)))


# Regex matching one citation token like [1] (also used inside [1][3][14]).
RE_RLLINK_CITE = re.compile(r"\[(\d+)\]")


def _rl_link_citations(text: str, enabled: bool) -> str:
    """Convert numeric citations [N] into blue underlined internal hyperlinks.

    Only applied to body text (enabled=True). Inside the references section we
    keep the citation markers as plain text (they are the entry labels).
    """
    if not enabled:
        return text
    return RE_RLLINK_CITE.sub(
        lambda m: f'<a href="#bib_ref_{m.group(1)}" '
                  f'color="#0000FF"><u>[{m.group(1)}]</u></a>',
        text,
    )


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


def _add_docx_runs(paragraph, tokens: list[Token]) -> None:
    """Apply inline tokens to a python-docx paragraph/heading as runs."""
    from docx.shared import Pt
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT

    def _ext_link(p, text, url):
        """Insert a blue, underlined hyperlink into *p*."""
        try:
            r_id = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
        except Exception:
            r_id = None
        hl = OxmlElement("w:hyperlink")
        if r_id is not None:
            hl.set(qn("r:id"), r_id)
        run = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0000FF")
        rPr.append(color)
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
        run.append(rPr)
        run_text = OxmlElement("w:t")
        run_text.set(qn("xml:space"), "preserve")
        run_text.text = text
        run.append(run_text)
        hl.append(run)
        p._p.append(hl)

    for t in tokens:
        if t.kind == "text":
            paragraph.add_run(t.value)
        elif t.kind == "italic":
            r = paragraph.add_run(t.value)
            r.italic = True
        elif t.kind == "bold":
            r = paragraph.add_run(t.value)
            r.bold = True
        elif t.kind == "boldi":
            r = paragraph.add_run(t.value)
            r.bold = True
            r.italic = True
        elif t.kind == "link":
            text, url = t.value.split("|", 1)
            _ext_link(paragraph, text, url)
        elif t.kind == "starit":
            r = paragraph.add_run(t.value)
            r.italic = True
        elif t.kind == "sup":
            r = paragraph.add_run(t.value)
            r.font.superscript = True
        elif t.kind == "sub":
            r = paragraph.add_run(t.value)
            r.font.subscript = True
        elif t.kind == "italic_sub":
            var, sub = t.value.split("|", 1)
            r = paragraph.add_run(var)
            r.italic = True
            rs = paragraph.add_run(sub)
            rs.font.subscript = True
        elif t.kind == "italic_sup":
            var, sup = t.value.split("|", 1)
            r = paragraph.add_run(var)
            r.italic = True
            rs = paragraph.add_run(sup)
            rs.font.superscript = True


def _add_docx_page_field(paragraph) -> None:
    """Insert a PAGE field into a python-docx paragraph."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    fld.append(r)
    fld.append(t)
    paragraph._p.append(fld)


def _add_docx_toc_field(doc) -> None:
    """Insert a Word TOC field that Word populates on update."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    para = doc.add_paragraph()
    run = para.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "Right-click here and choose Update Field to build the table of contents."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    for el in (fld_begin, instr, fld_sep, t, fld_end):
        run._r.append(el)


def generate_docx(front: dict, body_md: str, out_path: Path) -> None:
    """Render a DOCX via python-docx if available.

    Raises RuntimeError with instructions if python-docx is not installed.
    Emits the APA 7th title page (equal spacing), an optional TOC, a page-number
    header, and inline-formatted body (italic/bold/sub/sup from math-notation).
    """
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt
    except ImportError:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "python-docx is required for --docx output. "
            "Install it with `pip install python-docx`."
        )

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        hdr = section.header.paragraphs[0]
        hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _add_docx_page_field(hdr)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.paragraph_format.line_spacing = 2.0

    norm = front.get("NORM", "APA 7th")
    is_apa = norm == "APA 7th"
    if is_apa:
        items = [front.get(k, "") for k in _TITLE_ITEMS if front.get(k)]
        for i, item in enumerate(items):
            p = doc.add_paragraph(item)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pf = p.paragraph_format
            pf.space_before = Pt(72)
            pf.space_after = Pt(0 if i < len(items) - 1 else 72)
            if i == 0:
                for run in p.runs:
                    run.bold = True
        doc.add_page_break()
    else:
        title = doc.add_paragraph(front.get("TITLE", "Untitled"))
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title.runs:
            run.bold = True

    if front.get("TOC", "").strip().lower() == "true":
        doc.add_heading("Table of Contents", level=1)
        _add_docx_toc_field(doc)
        doc.add_page_break()

    for raw in body_md.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            h = doc.add_heading("", level=min(len(m.group(1)), 6))
            _add_docx_runs(h, split_inline(m.group(2)))
            continue
        if re.match(r"^\s*---+\s*$", line):
            continue
        p = doc.add_paragraph()
        if re.match(r"^\s*[-*]\s+", line):
            p = doc.add_paragraph(line.strip()[1:].strip(), style="List Bullet")
        _add_docx_runs(p, split_inline(line.lstrip("# ")))

    doc.save(str(out_path))


def generate_pdf(front: dict, body_md: str, out_path: Path) -> None:
    """Render a real PDF via reportlab (pure Python, no system deps).

    Supports the APA 7th title page, an optional TOC with dot leaders/page
    numbers, single- (APA/Vancouver) or two-column (IEEE) body layout, and
    page numbers (top-right for APA/Vancouver, bottom-center for IEEE).
    Raises RuntimeError if reportlab is not installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            NextPageTemplate,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
        )
        from reportlab.platypus.tableofcontents import TableOfContents
    except ImportError:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "reportlab is required for --pdf output. "
            "Install it with `pip install reportlab`."
        )

    norm = front.get("NORM", "APA 7th")
    is_apa = norm == "APA 7th"
    is_ieee = norm == "IEEE"
    font = 10 if is_ieee else 12
    leading = font if is_ieee else 2.0 * font

    def _hstyle(level: int) -> ParagraphStyle:
        return ParagraphStyle(
            name=f"Heading{min(level, 6)}",
            fontName="Times-Bold",
            fontSize=font,
            leading=leading,
            spaceBefore=14 if level <= 2 else 8,
            spaceAfter=4,
            textColor=colors.black,
        )

    body_style = ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=font, leading=leading,
        alignment=TA_LEFT, spaceAfter=6, textColor=colors.black,
    )
    ref_style = ParagraphStyle(
        "BodyRef", parent=body_style,
        leftIndent=0.5 * inch, firstLineIndent=-0.5 * inch,
    )
    center = ParagraphStyle(
        "Center", parent=body_style, alignment=TA_CENTER,
    )
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(f"TOC{lv}", parent=body_style) for lv in (0, 1, 2)]

    class AcademicDoc(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name.startswith("Heading"):
                level = int(flowable.style.name[7:] or 1)
                self.notify("TOCEntry", (min(level, 3), flowable.getPlainText(), self.page))

        # Internal citation destinations are created with inline `<a name="bib_ref_N">`
        # anchors injected into each reference entry (see the render loop in
        # generate_pdf), which makes PDF viewers jump to the exact reference line
        # rather than to the top of the page.

    m = inch
    width, height = letter
    if is_ieee:
        gap = 0.25 * inch
        col_w = (width - 2 * m - gap) / 2
        body_frames = [
            Frame(m, m, col_w, height - 2 * m, id="col1"),
            Frame(m + col_w + gap, m, col_w, height - 2 * m, id="col2"),
        ]
    else:
        body_frames = [Frame(m, m, width - 2 * m, height - 2 * m, id="normal")]

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 10)
        if is_ieee:
            canvas.drawCentredString(width / 2.0, 0.5 * inch, str(canvas.getPageNumber()))
        else:
            canvas.drawRightString(width - m, height - 0.5 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    doc = AcademicDoc(
        str(out_path),
        pagesize=letter,
        title=front.get("TITLE", "Untitled"),
        author=front.get("AUTHOR", ""),
    )
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[Frame(m, m, width - 2 * m, height - 2 * m, id="cover")], onPage=_on_page),
        PageTemplate(id="body", frames=body_frames, onPage=_on_page),
    ])

    story: list = []
    if is_apa:
        items = [front.get(k, "") for k in _TITLE_ITEMS if front.get(k)]
        gap = Spacer(1, 0.55 * inch)
        for i, item in enumerate(items):
            story.append(gap)
            st = ParagraphStyle(
                f"TP{i}",
                parent=center,
                fontName="Times-Bold" if i == 0 else "Times-Roman",
                fontSize=font * 1.2 if i == 0 else font,
                leading=leading,
            )
            story.append(Paragraph(_rl_text(item), st))
        story.append(gap)
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())
    else:
        story.append(Paragraph(
            _rl_text(front.get("TITLE", "Untitled")),
            ParagraphStyle("DocTitle", parent=center, fontName="Times-Bold", fontSize=24, leading=28),
        ))
        if front.get("AUTHOR"):
            story.append(Spacer(1, 10))
            story.append(Paragraph(_rl_text(front.get("AUTHOR")), center))
        story.append(Spacer(1, 14))
        story.append(NextPageTemplate("body"))

    if front.get("TOC", "").strip().lower() == "true":
        story.append(Paragraph("Table of Contents", _hstyle(1)))
        story.append(toc)
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())

    in_refs = False
    for raw in body_md.splitlines():
        line = raw.strip()
        if not line:
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            htxt = h.group(2).strip()
            in_refs = htxt.rstrip(":").lower() == "references"
            story.append(Paragraph(_rl_text(htxt), _hstyle(min(len(h.group(1)), 6))))
            continue
        # References section may be styled as `**REFERENCES**` (manual bold),
        # not a markdown heading. Detect it by its bare text.
        bare = re.sub(r"\*\*", "", line).strip().rstrip(":")
        if bare.lower() == "references" or bare.lower() == "referencias":
            in_refs = True
            story.append(Paragraph(_rl_text(line), _hstyle(1)))
            continue
        if re.match(r"^\s*---+\s*$", line):
            story.append(Spacer(1, 6))
            continue
        if re.match(r"^\s*[-*]\s+", line):
            story.append(Paragraph(_rl_link_citations(_rl_text(line[1:].strip()), not in_refs), body_style))
            continue
        st = ref_style if in_refs else body_style
        markup = _rl_link_citations(_rl_text(line), not in_refs)
        if in_refs:
            mref = re.match(r"^\[(\d+)\]", line)
            if mref:
                # Anchor the destination at the exact reference line so in-body
                # citation links jump straight to it.
                markup = f'<a name="bib_ref_{mref.group(1)}"></a>' + markup
        story.append(Paragraph(markup, st))

    # Single build is deterministic and keeps the internal citation destinations.
    # multiBuild (used only for the TOC) can discard pages and lose the named
    # bookmarks that in-body citations link to.
    if front.get("TOC", "").strip().lower() == "true":
        doc.multiBuild(story)
    else:
        doc.build(story)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Academic document generator.")
    parser.add_argument("--file", type=str, help="Input markdown file")
    parser.add_argument("--norm", type=str, default="APA 7th", help="Citation norm (unused here, kept for CLI compat)")
    parser.add_argument("--html", action="store_true", help="Output a full HTML document")
    parser.add_argument("--docx", action="store_true", help="Output a DOCX document")
    parser.add_argument("--pdf", action="store_true", help="Output a PDF document (via reportlab)")
    parser.add_argument("--out", type=str, help="Output path (default: <file>.<ext>)")
    args = parser.parse_args(argv)

    if not args.file:
        tests = [
            "mcd(_a_, _b_)",
            "_r_{0}",
            "_M_^{e}",
            "2^{255}",
            "**bold**",
            "H_{2}O",
            "_{0}",
            "n = 1",
        ]
        for t in tests:
            html = tokens_to_html(split_inline(t))
            print(f"{t:30s} -> {html}")
        return 0

    text = Path(args.file).read_text("utf-8")
    front = parse_frontmatter(text)
    body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, count=1, flags=re.DOTALL)

    if args.docx:
        out = Path(args.out) if args.out else Path(args.file).with_suffix(".docx")
        generate_docx(front, body, out)
        print(f"wrote {out}")
        return 0

    if args.pdf:
        out = Path(args.out) if args.out else Path(args.file).with_suffix(".pdf")
        generate_pdf(front, body, out)
        print(f"wrote {out}")
        return 0

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

        body_html = "\n".join(parts)

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
{body_html}
</body>
</html>"""
        out = Path(args.out) if args.out else Path(args.file).with_suffix(".html")
        out.write_text(doc, "utf-8")
        print(f"wrote {out}")
        return

    print(json.dumps(front, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
