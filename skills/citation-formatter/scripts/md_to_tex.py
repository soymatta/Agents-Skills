#!/usr/bin/env python3
"""
md_to_tex.py — Convert the research Markdown (IEEE, citation-formatter schema)
into a standalone LaTeX document (.tex).

Routes supported:
    python md_to_tex.py input.md            -> input.tex
    python md_to_tex.py input.md --pdf      -> input.pdf (via xelatex/pdflatex
                                               if installed; otherwise prints the
                                               path to the .tex so it can be
                                               compiled manually or via Overleaf)

Notes:
  - Skips the `---` frontmatter block
  - Title from the first `#` heading; authors from the placeholder line under it
    (`**Autor1Nombre Autor1Apellidos**; **Autor2Nombre Autor2Apellidos**`)
  - Title + authors are typeset in a single-column block; the body then flows in
    two columns (continuous layout via \\twocolumn[...] as in IEEE sbircs)
  - math-notation tokens are honored: `_text_` -> \\emph, **text** -> \\textbf,
    `^{...}`/`_{...}` -> $^{...}$/$_{...}$, bare URLs -> \\url, [N] stays [N]
  - Requires a TeX engine (xelatex/pdflatex) only for the --pdf route.
"""

import re
import subprocess
import sys
from pathlib import Path

RE_HEADING1 = re.compile(r"^#\s+(.+)$")
RE_HEADING2 = re.compile(r"^##\s+(.+)$")
RE_HEADING3 = re.compile(r"^###\s+(.+)$")
RE_HEADING4 = re.compile(r"^####\s+(.+)$")
RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
RE_TABLE_ROW = re.compile(r"^\|(.+)\|$")
RE_TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
RE_HR = re.compile(r"^---+$")
RE_OL = re.compile(r"^(\d+)\.\s+(.+)$")
RE_UL = re.compile(r"^[-*]\s+(.+)$")


def escape_text(t):
    return (
        t.replace("\\", r"\textbackslash{}")
        .replace("$", "\\$")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("_", r"\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
        .replace("<", r"\textless{}")
        .replace(">", r"\textgreater{}")
    )


TOKENS = re.compile(
    r"(\*\*(.+?)\*\*)"                    # 1,2 bold
    r"|(\^\{([^}]+)\})"                   # 3,4 superscript
    r"|(_\{([^}]+)\})"                    # 5,6 subscript
    r"|(_[^_]+_)"                         # 7 italic _text_
    r"|(https?://[^\s\]}\)]+)"            # 8 bare URL
    r"|(\[(\d+(?:,\s*\d+)*)\])"           # 9,10 citation [N]
    r"|(\[(.+?)\]\((.+?)\))"              # 11,12,13 link [text](url)
)


def tex_inline(text):
    out = []
    pos = 0
    for m in TOKENS.finditer(text):
        if m.start() > pos:
            out.append(escape_text(text[pos : m.start()]))
        if m.group(2):
            out.append(r"\textbf{" + escape_text(m.group(2)) + "}")
        elif m.group(4):
            out.append("\\ensuremath{^{" + escape_text(m.group(4)) + "}}")
        elif m.group(6):
            out.append("\\ensuremath{_{" + escape_text(m.group(6)) + "}}")
        elif m.group(7):
            out.append(r"\emph{" + escape_text(m.group(7)[1:-1]) + "}")
        elif m.group(8):
            out.append(r"\url{" + m.group(8) + "}")
        elif m.group(10):
            out.append("[" + m.group(10).replace(" ", r"\,") + "]")
        elif m.group(13):
            out.append(r"\href{" + m.group(13) + "}{" + escape_text(m.group(12)) + "}")
        pos = m.end()
    if pos < len(text):
        out.append(escape_text(text[pos:]))
    return "".join(out)


def parse_block(block):
    lines = block.split("\n")
    parsed = []
    para = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            if para:
                parsed.append(("para", " ".join(para)))
                para = []
            i += 1
            continue
        if stripped.startswith("#"):
            if para:
                parsed.append(("para", " ".join(para)))
                para = []
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            parsed.append((f"h{level}", title))
            i += 1
            continue
        if RE_TABLE_ROW.match(stripped):
            if para:
                parsed.append(("para", " ".join(para)))
                para = []
            rows = []
            while i < len(lines) and RE_TABLE_ROW.match(lines[i].strip()):
                rt = lines[i].strip()
                if not RE_TABLE_SEP.match(rt):
                    rows.append([c.strip() for c in rt.split("|")[1:-1]])
                i += 1
            parsed.append(("table", rows))
            continue
        if RE_HR.match(stripped) or stripped.startswith("<!---"):
            if para:
                parsed.append(("para", " ".join(para)))
                para = []
            i += 1
            continue
        ol = RE_OL.match(stripped)
        ul = RE_UL.match(stripped)
        if ol or ul:
            if para:
                parsed.append(("para", " ".join(para)))
                para = []
            if ol:
                parsed.append(("ol", ol.group(1), ol.group(2)))
            else:
                parsed.append(("ul", ul.group(1)))
            i += 1
            continue
        para.append(tex_inline(stripped))
        i += 1
    if para:
        parsed.append(("para", " ".join(para)))
    return parsed


def md_to_tex(md_path, pdf=False):
    md_path = Path(md_path)
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Skip frontmatter
    if lines and lines[0].strip() == "---":
        for j in range(1, min(len(lines), 50)):
            if lines[j].strip() == "---":
                lines = lines[j + 1 :]
                break

    title = None
    authors = []
    for k, line in enumerate(lines):
        m = RE_HEADING1.match(line.strip())
        if m:
            title = m.group(1).strip()
            # authors: first non-heading line after title
            for j in range(k + 1, min(k + 10, len(lines))):
                s = lines[j].strip()
                if not s:
                    continue
                if s.startswith("#") or RE_HR.match(s) or s.startswith("|"):
                    break
                core = re.sub(r"\*\*(.+?)\*\*", r"\1", s).strip()
                if core:
                    authors = [a.strip() for a in re.split(r"\s*;\s*|\s+y\s*", core)][:2]
                break
            break

    if not title:
        title = Path(md_path).stem.replace("_", " ")

    # Reconstruct body (skip title + author lines)
    body_lines = []
    seen_title = False
    author_skipped = not authors
    for line in lines:
        if not seen_title and RE_HEADING1.match(line.strip()):
            seen_title = True
            continue
        if seen_title and not author_skipped:
            s = line.strip()
            if s:
                author_skipped = True
                continue
        body_lines.append(line)
    body = "\n".join(body_lines)

    # References section
    ref_match = re.search(r"^##\s+(References|Referencias|Bibliography|Bibliograf[ií]a)\s*$", body, re.IGNORECASE | re.MULTILINE)
    refs = []
    if ref_match:
        after = body[ref_match.end() :]
        refs = [(m.group(1).strip(), m.group(2).strip()) for m in re.finditer(r"^\[(\d+)\]\s*(.*)$", after, re.MULTILINE)]
        body = body[: ref_match.start()]

    parsed = parse_block(body)

    doc = []
    doc.append(r"\documentclass[10pt,a4paper]{article}")
    doc.append(r"\usepackage[utf8]{inputenc}")
    doc.append(r"\usepackage[T1]{fontenc}")
    doc.append(r"\usepackage[spanish]{babel}")
    doc.append(r"\usepackage{times}")
    doc.append(r"\usepackage{graphicx}")
    doc.append(r"\usepackage[margin=1in]{geometry}")
    doc.append(r"\usepackage{hanging}")
    doc.append(r"\usepackage{hyperref}")
    doc.append(r"\usepackage{url}")
    doc.append(r"\usepackage{enumitem}")
    doc.append(r"\urlstyle{same}")
    doc.append(r"\setlength{\parindent}{0pt}")
    doc.append(r"\begin{document}")

    # Title + authors in a single-column block; body flows in two columns
    doc.append(r"\twocolumn[")
    doc.append(r"\begin{@twocolumnfalse}")
    doc.append(r"\begin{center}")
    doc.append(r"{\Large\bfseries " + escape_text(title) + r"}")
    for i, a in enumerate(authors):
        doc.append(r"\\[0.5em]" + escape_text(a))
    doc.append(r"\end{center}")
    doc.append(r"\end{@twocolumnfalse}")
    doc.append(r"]")

    for item in parsed:
        kind = item[0]
        if kind == "h2":
            doc.append(r"\section*{" + escape_text(item[1].upper()) + "}")
        elif kind == "h3":
            doc.append(r"\subsection*{" + escape_text(item[1].upper()) + "}")
        elif kind == "h4":
            doc.append(r"\subsubsection*{\emph{" + escape_text(item[1]) + "}}")
        elif kind == "para":
            doc.append(item[1] + r"\\[0.6em]")
        elif kind == "ol":
            doc.append(r"\begin{enumerate}[leftmargin=1.5em]")
            doc.append(r"\item " + item[2])
            doc.append(r"\end{enumerate}")
        elif kind == "ul":
            doc.append(r"\begin{itemize}[leftmargin=1.5em]")
            doc.append(r"\item " + item[1])
            doc.append(r"\end{itemize}")
        elif kind == "table":
            rows = item[1]
            if not rows:
                continue
            ncols = max(len(r) for r in rows)
            colspec = "|" + "|".join("l" for _ in range(ncols)) + "|"
            doc.append(r"\begin{table}[h]")
            doc.append(r"\centering")
            doc.append(r"\resizebox{\columnwidth}{!}{%")
            doc.append(r"\begin{tabular}{" + colspec + r"}")
            for r_idx, row in enumerate(rows):
                cells = [tex_inline(c) for c in row]
                cells += [""] * (ncols - len(cells))
                line = " & ".join(cells) + r" \\\hline"
                if r_idx == 0:
                    line = r"\hline " + line
                doc.append(line)
            doc.append(r"\end{tabular}}")
            doc.append(r"\end{table}")

    if refs:
        doc.append(r"\begin{hangparas}{1.5em}{1}")
        for num, ref in refs:
            doc.append("[" + num + "] " + tex_inline(re.sub(r"\s+", " ", ref)) + r"\\")
        doc.append(r"\end{hangparas}")

    doc.append(r"\end{document}")

    tex_path = md_path.with_suffix(".tex")
    tex_path.write_text("\n".join(doc), encoding="utf-8")
    print(f"Generated: {tex_path}")

    if pdf:
        engines = [e for e in ("xelatex", "pdflatex") if subprocess.run(["where", e], capture_output=True).returncode == 0]
        if not engines:
            print("  No TeX engine (xelatex/pdflatex) found. Compile the .tex manually or on Overleaf.")
            return tex_path
        for _ in range(2):
            subprocess.run([engines[0], "-interaction=nonstopmode", str(tex_path)], capture_output=True)
        pdf_path = md_path.with_suffix(".pdf")
        if pdf_path.exists():
            print(f"Generated: {pdf_path}")
            return pdf_path
        print("  LaTeX compile failed; check the .log file.")
    return tex_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python md_to_tex.py input.md [--pdf]")
        sys.exit(1)
    args = sys.argv[1:]
    md_to_tex(args[0], pdf="--pdf" in args)