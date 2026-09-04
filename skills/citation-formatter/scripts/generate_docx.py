#!/usr/bin/env python3
"""
generate_docx.py — IEEE-formatted DOCX generator from Markdown with clickable citation hyperlinks.

Fixes applied (from agent-self-improver session-001 feedback):
  - [FIX-001] IEEE format: 10pt, single spacing, 2 columns
  - [FIX-002] WD_ALIGN_PARAGRAPH.JUSTIFY (not JUSTIFIED)
  - [FIX-003] Internal hyperlinks use w:anchor (not r:id)
  - [FIX-004] bookmarkEnd inserted AFTER all runs
  - [FIX-005] References detected in English AND Spanish
  - [FIX-006] Title extracted from first # heading (fallback from bold text)
  - [FIX-007] Page numbers in footer (bottom center)
  - [FIX-008] Two columns via raw XML (python-docx has no built-in)
  - [FIX-009] Hanging indent for reference entries
  - [FIX-010] Inline parsing follows math-notation: `_text_` italic, `^{...}`
    superscript, `_{...}` subscript (with `*text*` italic as a fallback)
  - [FIX-011] External links (DOIs/URLs) are real w:hyperlink relId links,
    rendered blue/underlined, anywhere in body or references
  - [FIX-012] Title AND authors are centered in a single-column section; the
    2-column layout starts only AFTER the author block (continuous section
    break), per IEEE template conventions
  - [FIX-013] Author line read from the first non-heading line after the # title
    (template: `**Autor1Nombre Autor1Apellidos**; **Autor2Nombre Autor2Apellidos**`),
    up to 2 authors, split on `;` or ` y `

Usage:
    python generate_docx.py input.md output.docx
    python generate_docx.py input.md  # outputs to input.docx
"""

import re
import sys
from pathlib import Path
from copy import deepcopy

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT


# ═══════════════════════════════════════════════════════════════════════════
# IEEE FORMAT SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════

IEEE_SPEC = {
    "font_name": "Times New Roman",
    "font_size_title": Pt(24),
    "font_size_author": Pt(12),
    "font_size_abstract": Pt(9),
    "font_size_body": Pt(10),
    "font_size_heading1": Pt(10),
    "font_size_heading2": Pt(10),
    "font_size_heading3": Pt(10),
    "font_size_reference": Pt(8),
    "line_spacing": 1.0,
    "columns": 2,
    "margins": {
        "top": Cm(1.91),
        "bottom": Cm(1.91),
        "left": Cm(0.81),
        "right": Cm(0.81),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def set_run_font(run, font_name=None, size=None, bold=False, italic=False, color=None):
    """Set font properties on a run."""
    font = run.font
    font.name = font_name or IEEE_SPEC["font_name"]
    font.size = size or IEEE_SPEC["font_size_body"]
    font.bold = bold
    font.italic = italic
    if color:
        font.color.rgb = color


def add_page_number_footer(doc):
    """Add page number to footer (bottom center) per IEEE format."""
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # [FIX-002]

    # Add PAGE field
    run = p.add_run()
    fldChar1 = OxmlElement("w:fldChar")
    fldChar1.set(qn("w:fldCharType"), "begin")
    run._r.append(fldChar1)

    run2 = p.add_run()
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = " PAGE "
    run2._r.append(instrText)

    run3 = p.add_run()
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "end")
    run3._r.append(fldChar2)

    set_run_font(run, size=IEEE_SPEC["font_size_body"])
    set_run_font(run2, size=IEEE_SPEC["font_size_body"])
    set_run_font(run3, size=IEEE_SPEC["font_size_body"])


def set_section_columns(section, num_cols=2):
    """Set column count using raw XML (python-docx has no built-in). [FIX-008]"""
    sectPr = section._sectPr
    # Remove existing cols
    for cols in sectPr.findall(qn("w:cols")):
        sectPr.remove(cols)
    # Add new cols
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num_cols))
    cols.set(qn("w:space"), "360")  # ~0.63cm gutter
    sectPr.append(cols)


def set_section_type(section, type_name):
    """Set the section break type (e.g. 'continuous'). Keeps child ordering."""
    sectPr = section._sectPr
    t = sectPr.find(qn("w:type"))
    if t is not None:
        t.set(qn("w:val"), type_name)
        return
    t = OxmlElement("w:type")
    t.set(qn("w:val"), type_name)
    insert_at = 0
    for ref_tag in ("w:headerReference", "w:footerReference"):
        for child in sectPr.findall(qn(ref_tag)):
            insert_at = max(insert_at, list(sectPr).index(child) + 1)
    sectPr.insert(insert_at, t)


def set_two_columns(doc, num_cols=2):
    """Backward-compatible wrapper: apply columns to the first section."""
    set_section_columns(doc.sections[0], num_cols)


def add_bookmark_to_paragraph(paragraph, bookmark_name):
    """Add a bookmark around the entire paragraph content. [FIX-004]"""
    pPr = paragraph._p.get_or_add_pPr()

    # bookmarkStart
    bookmarkStart = OxmlElement("w:bookmarkStart")
    bookmarkStart.set(qn("w:id"), str(hash(bookmark_name) % 1000000))
    bookmarkStart.set(qn("w:name"), bookmark_name)
    pPr.append(bookmarkStart)

    # bookmarkEnd
    bookmarkEnd = OxmlElement("w:bookmarkEnd")
    bookmarkEnd.set(qn("w:id"), str(hash(bookmark_name) % 1000000))
    paragraph._p.append(bookmarkEnd)


def add_internal_link(paragraph, display_text, bookmark_name):
    """Add a clickable internal hyperlink to a bookmark. [FIX-003]"""
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), bookmark_name)  # [FIX-003] w:anchor NOT r:id

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    # Style as hyperlink (blue, underline)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0000FF")
    rPr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    font = OxmlElement("w:rFonts")
    font.set(qn("w:ascii"), IEEE_SPEC["font_name"])
    font.set(qn("w:hAnsi"), IEEE_SPEC["font_name"])
    rPr.append(font)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(IEEE_SPEC["font_size_body"].pt * 2)))
    rPr.append(sz)

    new_run.append(rPr)
    new_run.text = display_text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_external_link(paragraph, display_text, url, size=None):
    """Add a clickable external hyperlink to a URL (w:hyperlink with r:id)."""
    try:
        r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    except Exception:
        r_id = None

    hyperlink = OxmlElement("w:hyperlink")
    if r_id is not None:
        hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0000FF")
    rPr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    font = OxmlElement("w:rFonts")
    font.set(qn("w:ascii"), IEEE_SPEC["font_name"])
    font.set(qn("w:hAnsi"), IEEE_SPEC["font_name"])
    rPr.append(font)
    if size is not None:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size.pt * 2)))
        rPr.append(sz)
        szCs = OxmlElement("w:szCs")
        szCs.set(qn("w:val"), str(int(size.pt * 2)))
        rPr.append(szCs)

    new_run.append(rPr)
    new_run.text = display_text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def make_paragraph_space_before(paragraph, pts=0):
    """Set space before paragraph in points."""
    pPr = paragraph._p.get_or_add_pPr()
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:before"), str(int(pts * 20)))  # twips


def make_paragraph_space_after(paragraph, pts=0):
    """Set space after paragraph in points."""
    pPr = paragraph._p.get_or_add_pPr()
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    spacing.set(qn("w:after"), str(int(pts * 20)))  # twips


def parse_authors_line(line):
    """Extract up to 2 authors from the template line under the title.

    Template: `**Autor1Nombre Autor1Apellidos**; **Autor2Nombre Autor2Apellidos**`
    Separators: `;` or `y`. Returns a list of author name strings (max 2).
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", line).strip()
    if not text:
        return []
    parts = re.split(r"\s*;\s*|\s+y\s*", text)
    return [p.strip() for p in parts if p.strip()][:2]


# ═══════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ═══════════════════════════════════════════════════════════════════════════

# [FIX-005] Detect references in English AND Spanish
RE_SECTIONReferences = re.compile(
    r"^##\s+(References|Referencias|Bibliography|Bibliograf[ií]a)\s*$",
    re.IGNORECASE,
)

RE_HEADING1 = re.compile(r"^#\s+(.+)$")
RE_HEADING2 = re.compile(r"^##\s+(.+)$")
RE_HEADING3 = re.compile(r"^###\s+(.+)$")
RE_HEADING4 = re.compile(r"^####\s+(.+)$")
RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
RE_ITALIC = re.compile(r"\*(.+?)\*")
RE_LINK = re.compile(r"\[(.+?)\]\((.+?)\)")
RE_CITATION = re.compile(r"\[(\d+(?:,\s*\d+)*)\]")
RE_TABLE_ROW = re.compile(r"^\|(.+)\|$")
RE_TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
RE_HR = re.compile(r"^---+$")


def parse_inline(text):
    """Parse inline markdown into segments: text, bold, italic, super/sub,
    link, bare URL and citation.

    Notation follows math-notation: `_text_` for italic, `^{...}` for
    superscript, `_{...}` for subscript. `**text**` for bold. Classic `*text*`
    italic is accepted as a fallback.
    """
    segments = []
    pos = 0
    text = text.replace("\\.", ".")  # unescape \. → literal period (ordered lists)

    pattern = re.compile(
        r"(\*\*\*(.+?)\*\*\*)"            # 1,2 bold + italic
        r"|(\*\*(.+?)\*\*)"               # 3,4 bold
        r"|(\^\{([^}]+)\})"               # 5,6 superscript ^{...}
        r"|(_\{([^}]+)\})"                # 7,8 subscript _{...}
        r"|(_[^_]+_)"                     # 9 italic _text_
        r"|(\*(.+?)\*)"                   # 10,11 italic *text* (fallback)
        r"|(https?://[^\s\]}\)]+)"        # 12 bare URL
        r"|(\[(\d+(?:,\s*\d+)*)\])"       # 13,14 citation [1] or [1,2]
        r"|(\[(.+?)\]\((.+?)\))"          # 15,16,17 link [text](url)
    )

    for m in pattern.finditer(text):
        if m.start() > pos:
            segments.append({"type": "text", "content": text[pos:m.start()]})

        if m.group(2):       # boldable (bold+italic)
            segments.append({"type": "boldi", "content": m.group(2)})
        elif m.group(4):     # bold
            segments.append({"type": "bold", "content": m.group(4)})
        elif m.group(6):     # superscript
            segments.append({"type": "super", "content": m.group(6)})
        elif m.group(8):     # subscript
            segments.append({"type": "sub", "content": m.group(8)})
        elif m.group(9):     # italic (underscore)
            segments.append({"type": "italic", "content": m.group(9)[1:-1]})
        elif m.group(11):    # italic (asterisk fallback)
            segments.append({"type": "italic", "content": m.group(11)})
        elif m.group(12):    # bare URL
            segments.append({"type": "url", "content": m.group(12)})
        elif m.group(14):    # citation
            segments.append({"type": "citation", "content": m.group(14)})
        elif m.group(17):    # markdown link
            segments.append({"type": "link", "text": m.group(16), "url": m.group(17)})

        pos = m.end()

    if pos < len(text):
        segments.append({"type": "text", "content": text[pos:]})

    return segments


def add_segments(paragraph, segments, size=None):
    """Render parsed inline segments into a paragraph."""
    for seg in segments:
        stype = seg["type"]
        if stype == "text":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"])
        elif stype == "bold":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"], bold=True)
        elif stype == "boldi":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"], bold=True, italic=True)
        elif stype == "italic":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"], italic=True)
        elif stype == "super":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"])
            run.font.superscript = True
        elif stype == "sub":
            run = paragraph.add_run(seg["content"])
            set_run_font(run, size=size or IEEE_SPEC["font_size_body"])
            run.font.subscript = True
        elif stype == "citation":
            ref_num = seg["content"].split(",")[0].strip()
            add_internal_link(paragraph, f"[{seg['content']}]", f"bib_ref_{ref_num}")
        elif stype == "link":
            add_external_link(paragraph, seg["text"], seg["url"], size=size)
        elif stype == "url":
            add_external_link(paragraph, seg["content"], seg["content"], size=size)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_docx(md_path, docx_path=None):
    """Generate IEEE-formatted DOCX from Markdown."""
    md_path = Path(md_path)
    if docx_path is None:
        docx_path = md_path.with_suffix(".docx")

    md_content = md_path.read_text(encoding="utf-8")
    lines = md_content.split("\n")

    doc = Document()

    # ── Page Setup ────────────────────────────────────────────────────────
    section = doc.sections[0]
    section.top_margin = IEEE_SPEC["margins"]["top"]
    section.bottom_margin = IEEE_SPEC["margins"]["bottom"]
    section.left_margin = IEEE_SPEC["margins"]["left"]
    section.right_margin = IEEE_SPEC["margins"]["right"]

    # Set default paragraph style
    style = doc.styles["Normal"]
    style.font.name = IEEE_SPEC["font_name"]
    style.font.size = IEEE_SPEC["font_size_body"]
    style.paragraph_format.line_spacing = IEEE_SPEC["line_spacing"]
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)

    # ── Parse and Render ──────────────────────────────────────────────────
    in_references = False
    references_start_line = None
    title_extracted = False

    # First pass: find references section line
    for i, line in enumerate(lines):
        if RE_SECTIONReferences.match(line.strip()):
            references_start_line = i
            break

    # Second pass: render
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Skip frontmatter
        if i == 0 and stripped == "---":
            # Find end of frontmatter
            for j in range(1, min(len(lines), 50)):
                if lines[j].strip() == "---":
                    i = j + 1
                    break
            else:
                i += 1
            continue

        # Horizontal rule
        if RE_HR.match(stripped):
            i += 1
            continue

        # ── References Section ────────────────────────────────────────────
        if RE_SECTIONReferences.match(stripped):
            in_references = True
            # Add "REFERENCES" heading (IEEE: uppercase)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run("REFERENCES")
            set_run_font(run, size=Pt(10), bold=True)
            make_paragraph_space_before(p, 6)
            make_paragraph_space_after(p, 6)
            i += 1
            continue

        if in_references:
            # Parse reference entries: [N] Author et al., "Title," ...
            ref_match = re.match(r"^\[(\d+)\]\s+(.+)$", stripped)
            if ref_match:
                ref_num = ref_match.group(1)
                ref_text = ref_match.group(2)

                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                make_paragraph_space_before(p, 0)
                make_paragraph_space_after(p, 3)

                # Hanging indent
                pPr = p._p.get_or_add_pPr()
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), "420")   # ~0.74cm
                ind.set(qn("w:hanging"), "420")
                pPr.append(ind)

                # Add bookmark [FIX-004: AFTER paragraph is created]
                bookmark_name = f"bib_ref_{ref_num}"
                add_bookmark_to_paragraph(p, bookmark_name)

                # Add reference number
                run_num = p.add_run(f"[{ref_num}] ")
                set_run_font(run_num, size=IEEE_SPEC["font_size_reference"])

                # Render reference text: italics for journal names and
                # clickable external links for DOIs/URLs
                segments = parse_inline(ref_text)
                add_segments(p, segments, size=IEEE_SPEC["font_size_reference"])

            i += 1
            continue

        # ── Title Extraction ──────────────────────────────────────────────
        h1_match = RE_HEADING1.match(stripped)
        if h1_match and not title_extracted:
            title = h1_match.group(1).strip()
            title_extracted = True

            # Also check next lines for a bold title — but ONLY if the whole
            # line is a single bold span; must NOT swallow the author line
            # (which is `**A1**; **A2**` and therefore has ';' or a 2nd '**')
            for j in range(i + 1, min(i + 10, len(lines))):
                next_stripped = lines[j].strip()
                bold_match = RE_BOLD.match(next_stripped)
                if (
                    bold_match
                    and ";" not in next_stripped
                    and next_stripped.count("**") == 2
                ):
                    title = bold_match.group(1)
                    break
                if next_stripped and not RE_HR.match(next_stripped) and next_stripped != "## Título":
                    break

            # [FIX-013] Author line = first non-heading line after the title
            authors = []
            author_line_index = None
            for j in range(i + 1, min(i + 10, len(lines))):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    continue
                if (
                    next_stripped.startswith("#")
                    or RE_HR.match(next_stripped)
                    or next_stripped.startswith("|")
                ):
                    break
                authors = parse_authors_line(next_stripped)
                author_line_index = j
                break

            # [FIX-012] Title + authors: centered, full width (1 column)
            p_title = doc.add_paragraph()
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_title = p_title.add_run(title)
            set_run_font(run_title, size=IEEE_SPEC["font_size_title"], bold=True)
            make_paragraph_space_after(p_title, 12)

            for author in authors:
                p_author = doc.add_paragraph()
                p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_author = p_author.add_run(author)
                set_run_font(run_author, size=IEEE_SPEC["font_size_author"])
                make_paragraph_space_before(p_author, 0)
                make_paragraph_space_after(p_author, 4)

            # [FIX-012] Columns start ONLY after the author block
            body_section = doc.add_section(WD_SECTION.CONTINUOUS)
            set_section_type(doc.sections[0], "continuous")
            for mkey, mval in IEEE_SPEC["margins"].items():
                setattr(body_section, f"{mkey}_margin", mval)
            set_section_columns(body_section, IEEE_SPEC["columns"])

            # Skip past the author line so it is not rendered twice
            i = (author_line_index + 1) if author_line_index is not None else (i + 1)
            continue

        # Skip "## Título" section header (title already extracted)
        if stripped == "## Título":
            i += 1
            continue

        # ── Section Headings ──────────────────────────────────────────────
        h4_match = RE_HEADING4.match(stripped)
        h3_match = RE_HEADING3.match(stripped)
        h2_match = RE_HEADING2.match(stripped)

        if h2_match:
            heading_text = h2_match.group(1).strip()
            # IEEE: section headings uppercase, bold
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(heading_text.upper())
            set_run_font(run, size=IEEE_SPEC["font_size_heading1"], bold=True)
            make_paragraph_space_before(p, 10)
            make_paragraph_space_after(p, 4)
            i += 1
            continue

        if h3_match:
            heading_text = h3_match.group(1).strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(heading_text.upper())
            set_run_font(run, size=IEEE_SPEC["font_size_heading2"], bold=True)
            make_paragraph_space_before(p, 6)
            make_paragraph_space_after(p, 3)
            i += 1
            continue

        if h4_match:
            heading_text = h4_match.group(1).strip()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(heading_text)
            set_run_font(run, size=IEEE_SPEC["font_size_heading3"], bold=True, italic=True)
            make_paragraph_space_before(p, 4)
            make_paragraph_space_after(p, 2)
            i += 1
            continue

        # ── Table ─────────────────────────────────────────────────────────
        if RE_TABLE_ROW.match(stripped):
            # Collect table rows
            table_lines = []
            while i < len(lines) and RE_TABLE_ROW.match(lines[i].strip()):
                row_text = lines[i].strip()
                if RE_TABLE_SEP.match(row_text):
                    i += 1
                    continue  # skip separator
                cells = [c.strip() for c in row_text.split("|")[1:-1]]
                table_lines.append(cells)
                i += 1

            if table_lines:
                # Add table
                table = doc.add_table(rows=len(table_lines), cols=len(table_lines[0]))
                table.style = "Table Grid"

                for r_idx, row_cells in enumerate(table_lines):
                    for c_idx, cell_text in enumerate(row_cells):
                        if c_idx < len(table.columns):
                            cell = table.cell(r_idx, c_idx)
                            cell.text = ""
                            p = cell.paragraphs[0]
                            # Parse inline formatting in cells
                            segments = parse_inline(cell_text)
                            add_segments(p, segments, size=Pt(8))

                            # Bold first row as header
                            if r_idx == 0:
                                for run in p.runs:
                                    run.bold = True

                doc.add_paragraph()  # spacing after table
            continue

        # ── Ordered List ──────────────────────────────────────────────────
        ol_match = re.match(r"^(\d+)\.\s+\*\*(.+?)\*\*(.*)$", stripped)
        ol_match2 = re.match(r"^(\d+)\.\s+(.+)$", stripped)

        if ol_match:
            num = ol_match.group(1)
            bold_text = ol_match.group(2)
            rest_text = ol_match.group(3).strip()

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            indent_level = line.count("    ")
            pPr = p._p.get_or_add_pPr()
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), str(420 + indent_level * 420))
            pPr.append(ind)

            # Number
            run = p.add_run(f"{num}. ")
            set_run_font(run, size=IEEE_SPEC["font_size_body"])

            # Bold part
            run_bold = p.add_run(bold_text)
            set_run_font(run_bold, size=IEEE_SPEC["font_size_body"], bold=True)

            # Rest with inline parsing
            if rest_text:
                segments = parse_inline(rest_text)
                add_segments(p, segments)

            i += 1
            continue

        if ol_match2 and not ol_match:
            num = ol_match2.group(1)
            text = ol_match2.group(2)

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            indent_level = line.count("    ")
            pPr = p._p.get_or_add_pPr()
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), str(420 + indent_level * 420))
            pPr.append(ind)

            run = p.add_run(f"{num}. ")
            set_run_font(run, size=IEEE_SPEC["font_size_body"])

            segments = parse_inline(text)
            add_segments(p, segments)

            i += 1
            continue

        # ── Unordered List ────────────────────────────────────────────────
        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if ul_match:
            text = ul_match.group(1)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            indent_level = line.count("    ")
            pPr = p._p.get_or_add_pPr()
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), str(420 + indent_level * 420))
            pPr.append(ind)

            run = p.add_run("• ")
            set_run_font(run, size=IEEE_SPEC["font_size_body"])

            segments = parse_inline(text)
            add_segments(p, segments)

            i += 1
            continue

        # ── Regular Paragraph ─────────────────────────────────────────────
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        make_paragraph_space_before(p, 0)
        make_paragraph_space_after(p, 3)

        segments = parse_inline(stripped)
        add_segments(p, segments)

        i += 1

    # ── Post-Processing ───────────────────────────────────────────────────
    # [FIX-007] Add page numbers
    add_page_number_footer(doc)

    # [FIX-012] If no # title was found, fall back to 2 columns everywhere
    if not title_extracted:
        set_two_columns(doc, IEEE_SPEC["columns"])

    # Save
    doc.save(str(docx_path))
    print(f"Generated: {docx_path}")
    print(f"  Format: IEEE (10pt, single spacing, 2 columns)")
    print(f"  Title: {title_extracted}")

    return docx_path


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_docx.py input.md [output.docx]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    generate_docx(input_path, output_path)
