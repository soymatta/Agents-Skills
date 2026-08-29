"""Tests for osint phone_parser module."""

from __future__ import annotations


class TestDetectCountryCode:
    def test_colombia(self, phone_parser_module):
        assert phone_parser_module.detect_country_code("+573001112233") == "57"

    def test_mexico(self, phone_parser_module):
        assert phone_parser_module.detect_country_code("525511223344") == "52"

    def test_three_digit_priority(self, phone_parser_module):
        # Ecuador is 593, so it must win over the naive 59 / 5 prefixes.
        assert phone_parser_module.detect_country_code("593991234567") == "593"

    def test_unknown(self, phone_parser_module):
        assert phone_parser_module.detect_country_code("999000111") is None

    def test_detect_country_iso(self, phone_parser_module):
        country = phone_parser_module.detect_country("+573001112233")
        assert country["iso"] == "CO"


class TestParsePhone:
    def test_parses_colombian_mobile(self, phone_parser_module):
        result = phone_parser_module.parse_phone("+57 300 123 4567")
        assert result["country"]["iso"] == "CO"
        assert result["carrier"]["carrier"] == "Claro Colombia"
        assert result["is_valid"] is True

    def test_parses_us_number(self, phone_parser_module):
        result = phone_parser_module.parse_phone("+1 212 555 0177")
        assert result["country"]["iso"] == "US"
        assert result["carrier"]["location"] == "New York, NY"