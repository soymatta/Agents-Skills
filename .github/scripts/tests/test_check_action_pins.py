"""Tests for check_action_pins.py — network is always stubbed out."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_action_pins as mod  # noqa: E402

CHECKOUT = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
SETUP_NODE = "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1"


def _fake(verdict):
    calls = []

    def _resolve(owner, repo, ref, token=None, timeout=15):
        calls.append((owner, repo, ref))
        return verdict

    return _resolve, calls


def test_iter_uses_reads_pinned_refs() -> None:
    text = (
        "steps:\n"
        f"  - uses: {CHECKOUT} # v4.2.2\n"
        f"    uses: {SETUP_NODE}\n"
        "  - uses: ./local/action\n"
        '  - uses: "actions/cache@abc123"\n'
    )

    assert list(mod.iter_uses(text)) == [
        CHECKOUT,
        SETUP_NODE,
        "./local/action",
        "actions/cache@abc123",
    ]


def test_parse_ref() -> None:
    assert mod.parse_ref(CHECKOUT) == ("actions", "checkout", "11bd71901bbe5b1630ceea73d27597364c9af683")
    assert mod.parse_ref("./local/action") is None
    assert mod.parse_ref("../other/action") is None
    assert mod.parse_ref("docker://alpine:3") is None
    assert mod.parse_ref("actions/checkout") is None
    assert mod.parse_ref("actions/checkout@") is None


def test_main_flags_unresolved(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "ci.yml").write_text("jobs:\n  a:\n    steps:\n      - uses: actions/setup-node@deadbeef\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve", _fake(False)[0])

    assert mod.main([], workflows_dir=tmp_path) == 1
    out = capsys.readouterr().out
    assert "actions/setup-node@deadbeef" in out
    assert "do not resolve" in out


def test_main_passes_when_resolved(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "ci.yml").write_text(f"steps:\n  - uses: {CHECKOUT}\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve", _fake(True)[0])

    assert mod.main([], workflows_dir=tmp_path) == 0
    assert "1 action ref(s) resolved" in capsys.readouterr().out


def test_main_warns_but_passes_when_api_unreachable(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "ci.yml").write_text(f"steps:\n  - uses: {CHECKOUT}\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve", _fake(None)[0])

    assert mod.main([], workflows_dir=tmp_path) == 0
    assert "WARN" in capsys.readouterr().out


def test_strict_fails_when_api_unreachable(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "ci.yml").write_text(f"steps:\n  - uses: {CHECKOUT}\n", encoding="utf-8")
    monkeypatch.setattr(mod, "resolve", _fake(None)[0])

    assert mod.main(["--strict"], workflows_dir=tmp_path) == 1


def test_local_actions_are_not_checked(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "ci.yml").write_text("steps:\n  - uses: ./local/action\n", encoding="utf-8")
    resolver, calls = _fake(True)
    monkeypatch.setattr(mod, "resolve", resolver)

    assert mod.main([], workflows_dir=tmp_path) == 0
    assert calls == []
