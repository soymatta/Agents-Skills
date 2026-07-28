"""Tests for content-humanizer detect_ai module."""

from __future__ import annotations

import pytest


class TestSplitSections:
    def test_single_section(self, detect_ai_module):
        text = "Just plain text without headers."
        sections = detect_ai_module.split_sections(text)
        assert len(sections) >= 1

    def test_with_headers(self, detect_ai_module):
        text = "# Introduction\n" + "word " * 100 + "\n## Methods\n" + "word " * 100
        sections = detect_ai_module.split_sections(text, max_chars=50)
        headers = [h for h, _ in sections]
        assert "Introduction" in headers

    def test_merge_small_sections(self, detect_ai_module):
        text = "# H1\nShort.\n## H2\nShort.\n## H3\nA longer section with enough content to exceed the minimum threshold for merging with other sections."
        sections = detect_ai_module.split_sections(text, max_chars=500)
        assert len(sections) >= 1

    def test_empty_text(self, detect_ai_module):
        sections = detect_ai_module.split_sections("")
        assert isinstance(sections, list)

    def test_no_headers(self, detect_ai_module):
        text = "Line 1\nLine 2\nLine 3"
        sections = detect_ai_module.split_sections(text)
        assert len(sections) >= 1


class TestClassifySection:
    def test_empty_text(self, detect_ai_module):
        result = detect_ai_module.classify_section(None, "")
        assert result["label"] == "SKIP"
        assert result["score"] == 0.0

    def test_whitespace_only(self, detect_ai_module):
        result = detect_ai_module.classify_section(None, "   \n  ")
        assert result["label"] == "SKIP"

    def test_mock_detector_human(self, detect_ai_module):
        class MockDetector:
            def __call__(self, text):
                return [[{"label": "REAL", "score": 0.9}, {"label": "FAKE", "score": 0.1}]]

        result = detect_ai_module.classify_section(MockDetector(), "This is human text.")
        assert result["label"] == "HUMAN"
        assert result["human_prob"] == 0.9

    def test_mock_detector_ai(self, detect_ai_module):
        class MockDetector:
            def __call__(self, text):
                return [[{"label": "FAKE", "score": 0.85}, {"label": "REAL", "score": 0.15}]]

        result = detect_ai_module.classify_section(MockDetector(), "This is AI text.")
        assert result["label"] == "AI"
        assert result["ai_prob"] == 0.85


class TestReadText:
    def test_read_from_file(self, detect_ai_module, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")
        text = detect_ai_module.read_text(str(test_file))
        assert text == "Hello world"

    def test_read_none_returns_empty(self, detect_ai_module):
        import sys
        from io import StringIO
        old_stdin = sys.stdin
        sys.stdin = StringIO("")
        try:
            text = detect_ai_module.read_text(None)
            assert text == ""
        finally:
            sys.stdin = old_stdin


class TestPrintResult:
    def test_print_human(self, detect_ai_module, capsys):
        global_result = {"label": "HUMAN", "ai_prob": 0.1, "human_prob": 0.9}
        detect_ai_module.print_result(global_result, [], False)
        captured = capsys.readouterr()
        assert "PASA" in captured.out

    def test_print_ai(self, detect_ai_module, capsys):
        global_result = {"label": "AI", "ai_prob": 0.8, "human_prob": 0.2}
        detect_ai_module.print_result(global_result, [], False)
        captured = capsys.readouterr()
        assert "DETECTADO" in captured.out

    def test_verbose_with_sections(self, detect_ai_module, capsys):
        global_result = {"label": "AI", "ai_prob": 0.7, "human_prob": 0.3}
        sections = [
            {"label": "AI", "ai_prob": 0.8, "human_prob": 0.2, "header": "Intro", "length": 500},
            {"label": "HUMAN", "ai_prob": 0.2, "human_prob": 0.8, "header": "Methods", "length": 300},
        ]
        detect_ai_module.print_result(global_result, sections, True)
        captured = capsys.readouterr()
        assert "ANALISIS POR SECCION" in captured.out
        assert "Intro" in captured.out
