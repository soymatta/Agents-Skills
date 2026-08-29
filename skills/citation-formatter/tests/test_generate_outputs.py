"""Tests for citation-formatter generate_outputs inline parser + generators."""

from __future__ import annotations


class TestInlineParser:
    def _html(self, module, text):
        return module.tokens_to_html(module.split_inline(text))

    def test_italic(self, generate_outputs_module):
        assert self._html(generate_outputs_module, "mcd(_a_, _b_)") == "mcd(<em>a</em>, <em>b</em>)"

    def test_subscript_only(self, generate_outputs_module):
        # Regression: format "{sub}" was previously dropped entirely.
        assert self._html(generate_outputs_module, "_{0}") == "<sub>0</sub>"

    def test_letter_n_in_text(self, generate_outputs_module):
        # Regression: TEXT regex excluded 'n', splitting it into CHAR tokens.
        assert self._html(generate_outputs_module, "n = 1") == "n = 1"

    def test_italic_sub_combined(self, generate_outputs_module):
        assert self._html(generate_outputs_module, "_r_{0}") == "<em>r</em><sub>0</sub>"

    def test_italic_sup_combined(self, generate_outputs_module):
        assert self._html(generate_outputs_module, "_M_^{e}") == "<em>M</em><sup>e</sup>"

    def test_superscript(self, generate_outputs_module):
        assert self._html(generate_outputs_module, "2^{255}") == "2<sup>255</sup>"

    def test_bold(self, generate_outputs_module):
        assert self._html(generate_outputs_module, "**bold**") == "<strong>bold</strong>"

    def test_escaped_underscore(self, generate_outputs_module):
        assert self._html(generate_outputs_module, r"a\_b") == "a_b"

    def test_reportlab_markup(self, generate_outputs_module):
        rl = generate_outputs_module.tokens_to_reportlab(
            generate_outputs_module.split_inline("_x_^{2} + H_{2}O")
        )
        assert rl == "<i>x</i><super>2</super> + H<sub>2</sub>O"


class TestMarkdown:
    def test_headings(self, generate_outputs_module):
        html = generate_outputs_module.markdown_to_html("# Titulo\n\n## Seccion\n")
        assert "<h1>Titulo</h1>" in html
        assert "<h2>Seccion</h2>" in html

    def test_list_items(self, generate_outputs_module):
        html = generate_outputs_module.markdown_to_html("- item uno\n- item dos\n")
        assert html.count("<li>") == 2

    def test_extract_headings(self, generate_outputs_module):
        heads = generate_outputs_module.extract_headings("# A\n## B\n### C\n")
        assert heads == [(1, "A"), (2, "B"), (3, "C")]


class TestFrontmatter:
    def test_parse(self, generate_outputs_module):
        text = '---\nTITLE: "Mi titulo"\nTOC: "true"\nNORM: "IEEE"\n---\n\nCuerpo'
        front = generate_outputs_module.parse_frontmatter(text)
        assert front["TITLE"] == "Mi titulo"
        assert front["TOC"] == "true"
        assert front["NORM"] == "IEEE"

    def test_parse_no_frontmatter(self, generate_outputs_module):
        assert generate_outputs_module.parse_frontmatter("sin frontmatter") == {}


class TestGenerators:
    def test_self_test_returns_zero(self, generate_outputs_module, capsys):
        assert generate_outputs_module.main([]) == 0
        captured = capsys.readouterr()
        assert "<sub>0</sub>" in captured.out

    def test_pdf_output(self, generate_outputs_module, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            '---\nTITLE: "X"\nAUTHOR: "Y"\nTOC: "true"\nNORM: "APA 7th"\n---\n\n'
            "# Intro\n\nUn texto _largo_ con H_{2}O y 2^{10}.\n\n# References\n\nItem uno.\n",
            encoding="utf-8",
        )
        out = tmp_path / "doc.pdf"
        generate_outputs_module.generate_pdf(
            generate_outputs_module.parse_frontmatter(md.read_text(encoding="utf-8")),
            "Un texto _largo_ con H_{2}O y 2^{10}.\n\n# References\n\nItem uno.\n",
            out,
        )
        assert out.stat().st_size > 1000
        head = out.read_bytes()[:5]
        assert head == b"%PDF-"

    def test_docx_output_runs(self, generate_outputs_module, tmp_path):
        md = tmp_path / "doc.md"
        md.write_text(
            '---\nTITLE: "X"\nNORM: "APA 7th"\n---\n\n# Intro\n\nUn texto _largo_ con 2^{10}.\n',
            encoding="utf-8",
        )
        out = tmp_path / "doc.docx"
        generate_outputs_module.generate_docx(
            generate_outputs_module.parse_frontmatter(md.read_text(encoding="utf-8")),
            "Un texto _largo_ con 2^{10}.\n",
            out,
        )
        from docx import Document

        doc = Document(str(out))
        body = next(p for p in doc.paragraphs if p.text.startswith("Un texto"))
        tags = []
        for r in body.runs:
            if r.italic:
                tags.append("i")
            if r.font.superscript:
                tags.append("sup")
        assert "i" in tags
        assert "sup" in tags