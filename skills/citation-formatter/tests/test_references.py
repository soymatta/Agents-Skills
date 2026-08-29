"""Tests for citation-formatter references module."""

from __future__ import annotations

import pytest


JOURNAL = {
    "title": "Deep learning in education",
    "authors": ["Smith, J.; Johnson, M."],
    "year": "2024",
    "type": "journal",
    "journal": "Journal of Innovation",
    "volume": "15",
    "issue": "2",
    "pages": "40-55",
    "doi": "10.1000/xyz",
}

BOOK = {
    "title": "Strategic management",
    "authors": ["Porter, M. E."],
    "year": "1998",
    "type": "book",
    "edition": "2nd",
    "publisher": "Free Press",
}

THREE_AUTHORS = {
    "title": "Multiauthor paper",
    "authors": ["Smith, J.; Jones, K.; White, L."],
    "year": "2023",
    "type": "journal",
    "journal": "Journal of Innovation",
    "volume": "5",
}


class TestAuthors:
    def _split(self, references, raw):
        return references._split_authors(raw)

    def test_apa_two(self, references):
        names = self._split(references, ["Smith, J.; Johnson, M."])
        assert references.authors_apa(names) == "Smith, J. & Johnson, M."

    def test_apa_three_et_al(self, references):
        names = self._split(references, ["Smith, J.; Jones, K.; White, L."])
        assert references.authors_apa(names) == "Smith, J. et al."

    def test_apa_single_dotted_initials(self, references):
        assert references.authors_apa(["Porter, M. E."]) == "Porter, M. E."

    def test_apa_lastname_only(self, references):
        assert references.authors_apa(["Anonimo"]) == "Anonimo"

    def test_ieee_two(self, references):
        names = self._split(references, ["Smith, J.; Johnson, M."])
        assert references.authors_ieee(names) == "J. Smith and M. Johnson"

    def test_ieee_three(self, references):
        names = self._split(references, ["Smith, J.; Jones, K.; White, L."])
        assert (
            references.authors_ieee(names)
            == "J. Smith, K. Jones, and L. White"
        )

    def test_vancouver(self, references):
        assert references.authors_vancouver(["Porter, M. E."]) == "Porter ME"


class TestRefApa:
    def test_journal(self, references):
        ref = references._ref_apa(JOURNAL)
        assert ref.startswith("Smith, J. & Johnson, M. (2024). Deep learning in education.")
        assert "_Journal of Innovation_" in ref
        assert ", 15(2), 40-55" in ref
        assert "https://doi.org/10.1000/xyz" in ref

    def test_book(self, references):
        ref = references._ref_apa(BOOK)
        assert ref == (
            "Porter, M. E. (1998). _Strategic management_ (2nd ed.). Free Press."
        )

    def test_three_authors_et_al(self, references):
        ref = references._ref_apa(THREE_AUTHORS)
        assert ref.startswith("Smith, J. et al.")


class TestRefIeee:
    def test_journal(self, references):
        ref = references._ref_ieee(JOURNAL)
        assert ref.startswith(
            'J. Smith and M. Johnson, "Deep learning in education", _Journal of Innovation_, '
            "vol. 15, no. 2, pp. 40-55, 2024, doi: 10.1000/xyz."
        )

    def test_book(self, references):
        ref = references._ref_ieee(BOOK)
        assert ref == "M. E. Porter, _Strategic management_ (2nd ed.) Free Press, 1998."


class TestRefVancouver:
    def test_journal(self, references):
        ref = references._ref_vancouver(JOURNAL)
        assert ref.startswith(
            "Smith J, Johnson M. Deep learning in education. _Journal of Innovation_. "
            "2024;15(2):40-55 doi:10.1000/xyz."
        )

    def test_book(self, references):
        ref = references._ref_vancouver(BOOK)
        assert ref == "Porter ME. _Strategic management_ 2nd ed. Free Press; 1998."


class TestRenderAndPairs:
    def test_render_ieee_numbered(self, references):
        lines = references.render([JOURNAL, BOOK], "IEEE", sort="order")
        assert lines[0].startswith("[1] ")
        assert lines[1].startswith("[2] ")

    def test_render_apa_alpha(self, references):
        lines = references.render([JOURNAL, BOOK], "APA 7th", sort="alpha")
        assert lines[0].startswith("Porter")  # B before S
        assert lines[1].startswith("Smith")

    def test_pairs_apa(self, references):
        pairs = references.citation_pairs([JOURNAL, BOOK, THREE_AUTHORS], "APA 7th")
        assert pairs[0] == "(Smith & Johnson, 2024)"
        assert pairs[2] == "(Smith et al., 2023)"

    def test_pairs_ieee(self, references):
        assert references.citation_pairs([JOURNAL, BOOK], "IEEE") == ["[1]", "[2]"]

    def test_pairs_vancouver(self, references):
        assert references.citation_pairs([JOURNAL, BOOK], "Vancouver") == ["(1)", "(2)"]

    def test_unsupported_norm(self, references):
        with pytest.raises(ValueError):
            references.render([JOURNAL], "Chicago")


class TestLoadAndCli:
    def test_load_and_render(self, references, tmp_path):
        ys = tmp_path / "sources.yaml"
        ys.write_text("- title: X\n  authors: Y.\n  year: 2020\n  type: misc\n", encoding="utf-8")
        sources = references.load_sources(str(ys))
        assert len(sources) == 1
        assert sources[0]["title"] == "X"
        assert references.render(sources, "APA 7th", sort="alpha")[0].startswith("Y. (2020). X.")

    def test_missing_title_fails(self, references, tmp_path):
        ys = tmp_path / "sources.yaml"
        ys.write_text("- year: 2020\n", encoding="utf-8")
        with pytest.raises(ValueError):
            references.load_sources(str(ys))

    def test_cli_ieee(self, references, tmp_path, capsys):
        ys = tmp_path / "sources.yaml"
        ys.write_text("- title: X\n  authors: Y.\n  year: 2020\n  type: misc\n", encoding="utf-8")
        code = references.main(["--file", str(ys), "--norm", "IEEE"])
        assert code == 0
        captured = capsys.readouterr()
        assert "## References" in captured.out
        assert "[1]" in captured.out

    def test_cli_bad_file(self, references, tmp_path, capsys):
        code = references.main(["--file", str(tmp_path / "nope.yaml"), "--norm", "IEEE"])
        assert code == 1
        captured = capsys.readouterr()
        assert "references.py:" in captured.err