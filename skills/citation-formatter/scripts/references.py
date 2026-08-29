"""Format a ``sources.yaml`` catalog into a Markdown ``## References`` section.

This script is the *consumer* of the machine-readable source list produced by
``academic-source-search`` (and collected by the ``paper-researcher`` agent).
It renders each source in APA 7th, IEEE, or Vancouver and emits a section that
``generate_outputs.py`` can ingest (titles in ``_..._`` use math-notation, and
DOIs are emitted as active links).

Usage:
    python references.py --file sources.yaml --norm "APA 7th" [--out References.md]
    python references.py --file sources.yaml --norm IEEE
    python references.py --file sources.yaml --norm Vancouver [--sort order]
    python references.py --file sources.yaml --pairs        # in-text citation snippets

``--sort``: ``alpha`` (default for APA) or ``order`` (default for IEEE/Vancouver).

Exit code 0 = all sources rendered; 1 = catalog invalid or rules violated.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on environment
    yaml = None

SUPPORTED_NORMS = ("APA 7th", "IEEE", "Vancouver")
VALID_TYPES = ("journal", "conference", "book", "thesis", "preprint", "website")


# ── catalog loading ───────────────────────────────────────────────────────────


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    """Parse ``sources.yaml`` into a list of source dicts.

    The file must be a YAML list of maps. Missing files error out; the schema
    is validated loosely (minimal fields required) so the agent keeps control
    of quality without the tool being stricter than the docs.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install it with `pip install pyyaml`.")
    src = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(src)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a YAML list of sources, got {type(data).__name__}")
    sources: list[dict[str, Any]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: entry #{i} is not a mapping")
        if not item.get("title"):
            raise ValueError(f"{path}: entry #{i} has no 'title'")
        sources.append(item)
    return sources


# ── author handling ───────────────────────────────────────────────────────────


def _split_authors(raw: Any) -> list[str]:
    """Normalize an ``authors`` field into a list of "Last, I." strings.

    Accepts: ["Last, F.; Last, F."], ["Last, F.", "Last, F."], or a bare string.
    Elements containing ';' are split further. Empty input -> [].
    """
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    names: list[str] = []
    for it in items:
        if isinstance(it, str):
            parts = [p.strip() for p in it.split(";") if p.strip()]
            names.extend(parts)
        else:
            names.append(str(it).strip())
    return names


def _last_initial(name: str) -> tuple[str, str]:
    """Split a "Last, I." style name into (last, initials_letters). Robust to 'et al.'"""
    parts = [p.strip() for p in name.split(",")]
    last = parts[0].strip()
    if last.lower() in ("", "et al", "etal"):
        return "", ""
    if len(parts) > 1:
        initials = parts[1]
    elif len(name.split()) > 1:
        m = re.search(r"\b([A-ZÄÖÜÑÁÉÍÓÚ]\.?)\s*$", name)
        initials = m.group(1) if m else ""
    else:
        initials = ""
    letters = re.sub(r"[^A-ZÄÖÜÑÁÉÍÓÚ]", "", initials.upper())
    return last, letters


def _dotted(letters: str) -> str:
    """'JM' -> 'J. M.' (APA / IEEE initials with periods)."""
    return " ".join(c + "." for c in letters)


def authors_apa(names: list[str]) -> str:
    keep = [_last_initial(n) for n in names if _last_initial(n)[0]]
    if not keep:
        return "Anon."
    rendered = [f"{l}, {_dotted(i)}" if i else l for l, i in keep]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return f"{rendered[0]} & {rendered[1]}"
    return f"{rendered[0]} et al."


def authors_ieee(names: list[str]) -> str:
    keep = [_last_initial(n) for n in names if _last_initial(n)[0]]
    if not keep:
        return "Anon."
    rendered = [(_dotted(i) + " " + l) if i else l for l, i in keep]
    if len(rendered) == 1:
        return rendered[0]
    if len(rendered) == 2:
        return " and ".join(rendered)
    return ", ".join(rendered[:-1]) + ", and " + rendered[-1]


def authors_vancouver(names: list[str]) -> str:
    keep = [_last_initial(n) for n in names if _last_initial(n)[0]]
    if not keep:
        return "Anon"
    rendered = [(l + " " + i) if i else l for l, i in keep]
    return ", ".join(rendered)


def _year(src: dict) -> str:
    y = src.get("year")
    if y in (None, ""):
        return "n.d."
    return str(y)


def _doi_url(src: dict) -> str:
    doi = (src.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}"
    return (src.get("url") or "").strip()


def _infer_type(src: dict) -> str:
    t = (src.get("type") or "").strip().lower()
    if t in VALID_TYPES:
        return t
    if src.get("journal") or src.get("volume") or src.get("issue"):
        return "journal"
    if "arxiv" in (src.get("url") or ""):
        return "preprint"
    return "misc"


# ── per-style rendering ───────────────────────────────────────────────────────


def _ref_apa(src: dict) -> str:
    t = _infer_type(src)
    authors = authors_apa(_split_authors(src.get("authors")))
    year = _year(src)
    title = (src.get("title") or "Untitled").strip().rstrip(".")
    link = _doi_url(src)

    if t == "journal":
        journal = src.get("journal") or src.get("venue") or ""
        vol = src.get("volume") or ""
        iss = src.get("issue") or ""
        pg = src.get("pages") or ""
        vol_iss = f"{vol}({iss})" if vol and iss else vol
        loc = ", ".join(x for x in (vol_iss, pg) if x)
        ref = f"{authors} ({year}). {title}."
        if journal:
            ref += f" _{journal}_"
            if loc:
                ref += f", {loc}"
        elif loc:
            ref += f" {loc}"
        ref += "."
    elif t == "book":
        pub = src.get("publisher") or ""
        ed = src.get("edition") or ""
        middle = f" ({ed} ed.)" if ed else ""
        ref = f"{authors} ({year}). _{title}_{middle}."
        if pub:
            ref += f" {pub}."
        if link and link not in ref:
            ref += f" {link}"
        return ref
    elif t == "conference":
        proc = src.get("proceedings") or src.get("journal") or ""
        pg = src.get("pages") or ""
        ref = f"{authors} ({year}). {title}."
        if proc:
            ref += f" _{proc}_"
            if pg:
                ref += f", {pg}"
        elif pg:
            ref += f" {pg}"
        if link and link not in ref:
            ref = ref.rstrip(".") + ". " + link
        if not ref.endswith("."):
            ref += "."
        return ref
    elif t == "thesis":
        uni = src.get("university") or src.get("institution") or ""
        repo = src.get("repository") or ""
        ref = f"{authors} ({year}). _{title}_ [Doctoral dissertation"
        if uni:
            ref += f", {uni}"
        ref += "]."
        if repo:
            ref += f" {repo}."
        if link and link not in ref:
            ref += f" {link}"
        return ref
    elif t == "website":
        site = src.get("journal") or src.get("site") or ""
        ref = f"{authors} ({year}). {title}."
        if site:
            ref += f" {site}."
        if link:
            ref += f" {link}"
        return ref
    elif t == "preprint":
        arx = src.get("repository") or "arXiv"
        ref = f"{authors} ({year}). {title}. {arx}."
        if link:
            ref += f" {link}"
        return ref
    else:
        ref = f"{authors} ({year}). {title}."
        if link and link not in ref:
            ref += f" {link}"
        return ref

    # journal path: append the DOI/URL when it is not already present
    if link and link not in ref:
        ref += f" {link}"
    return ref


def _ref_ieee(src: dict) -> str:
    t = _infer_type(src)
    authors = authors_ieee(_split_authors(src.get("authors")))
    year = _year(src)
    title = (src.get("title") or "Untitled").strip()
    doi = (src.get("doi") or "").strip()
    quoted = f'"{title}"'
    if t == "journal":
        j = src.get("journal") or src.get("venue") or ""
        vol = src.get("volume") or ""
        no = src.get("issue") or ""
        pp = src.get("pages") or ""
        fields = [authors, quoted]
        if j:
            fields.append(f"_{j}_")
            if vol or no or pp:
                vol_s = f"vol. {vol}" if vol else ""
                no_s = f"no. {no}" if no else ""
                pp_s = f"pp. {pp}" if pp else ""
                fields.append(", ".join(x for x in (vol_s, no_s, pp_s) if x))
        if year and year != "n.d.":
            fields.append(year)
        ref = ", ".join(f for f in fields if f)
        if doi:
            ref += f", doi: {doi}."
        else:
            ref += "."
        return ref
    if t == "book":
        pub = src.get("publisher") or ""
        ed = src.get("edition") or ""
        mid = f" ({ed} ed.)" if ed else ""
        if pub:
            return f"{authors}, _{title}_{mid} {pub}, {year}."
        return f"{authors}, _{title}_{mid} {year}."
    if t == "conference":
        proc = src.get("proceedings") or src.get("journal") or ""
        pp = src.get("pages") or ""
        ref = f"{authors}, {quoted}"
        if proc:
            ref += f", in Proc. _{proc}_"
        if pp:
            ref += f", pp. {pp}"
        ref += f", {year}"
        if doi:
            ref += f", doi: {doi}"
        return ref + "."
    if t == "website":
        site = src.get("journal") or src.get("site") or ""
        url = _doi_url(src)
        ref = f"{authors}, {quoted}"
        if site:
            ref += f", _{site}_"
        ref += f", {year}. [Online]. Available: {url}"
        return ref
    ref = f"{authors}, {quoted}"
    if doi:
        ref += f", doi: {doi}"
    return ref + f", {year}."


def _ref_vancouver(src: dict) -> str:
    t = _infer_type(src)
    authors = authors_vancouver(_split_authors(src.get("authors")))
    year = _year(src)
    title = (src.get("title") or "Untitled").strip().rstrip(".")
    doi = (src.get("doi") or "").strip()
    if t == "journal":
        j = src.get("journal") or src.get("venue") or "Journal"
        vol = src.get("volume") or ""
        iss = src.get("issue") or ""
        pp = src.get("pages") or ""
        ref = f"{authors}. {title}. _{j}_."
        if year:
            ref += f" {year}"
        if vol and iss:
            ref += f";{vol}({iss})"
        elif vol:
            ref += f";{vol}"
        if pp:
            ref += f":{pp}"
        if doi:
            ref += f" doi:{doi}"
        return ref + "."
    if t == "book":
        ed = src.get("edition") or ""
        mid = f" {ed} ed." if ed else ""
        pub = src.get("publisher") or ""
        ref = f"{authors}. _{title}_ {mid} {pub}; {year}."
        return re.sub(r"\s+", " ", ref).strip()
    if t == "conference":
        proc = src.get("proceedings") or src.get("journal") or ""
        pp = src.get("pages") or ""
        ref = f"{authors}. {title}."
        if proc:
            ref += f" In: _{proc}_."
        if pp:
            ref += f" p. {pp}."
        if year:
            ref += f" {year}"
        return ref + "."
    if t == "thesis":
        uni = src.get("university") or src.get("institution") or ""
        ref = f"{authors}. _{title}_ [dissertation]."
        if uni:
            ref += f" {uni}."
        if year:
            ref += f" {year}"
        return ref + "."
    if t == "website":
        site = src.get("journal") or src.get("site") or ""
        url = _doi_url(src)
        ref = f"{authors}. _{title}_ [Internet]."
        if site:
            ref += f" {site}."
        if year:
            ref += f" {year}"
        ref += f" Available from: {url}"
        return ref
    ref = f"{authors}. {title}"
    if year:
        ref += f". {year}"
    if doi:
        ref += f" doi:{doi}"
    return ref + "."


_REF_RENDERERS: dict[str, Any] = {
    "APA 7th": lambda s: _ref_apa(s),
    "IEEE": lambda s: _ref_ieee(s),
    "Vancouver": lambda s: _ref_vancouver(s),
}


def render(sources: list[dict[str, Any]], norm: str, sort: str = "alpha") -> list[str]:
    """Return the formatted reference lines for ``norm``."""
    if norm not in SUPPORTED_NORMS:
        raise ValueError(f"Unsupported norm {norm!r}; choose from {', '.join(SUPPORTED_NORMS)}")
    lines = [_REF_RENDERERS[norm](s) for s in sources]

    if sort == "alpha":
        key = lambda s: (_split_authors(s.get("authors")) or ["Anon."])[0].lower()
        ordered_lines = [
            _REF_RENDERERS[norm](s) for s in sorted(sources, key=key)
        ]
        return ordered_lines

    # order of appearance → IEEE/Vancouver numbers
    numbered = []
    for i, line in enumerate(lines, 1):
        prefix = f"[{i}] " if norm == "IEEE" else f"{i}. "
        numbered.append(prefix + line)
    return numbered


def citation_pairs(sources: list[dict[str, Any]], norm: str) -> list[str]:
    """In-text citation snippets (APA parenthetical / IEEE [n] / Vancouver (n))."""
    if norm == "IEEE":
        return [f"[{i}]" for i in range(1, len(sources) + 1)]
    if norm == "Vancouver":
        return [f"({i})" for i in range(1, len(sources) + 1)]
    out = []
    for src in sources:
        names = _split_authors(src.get("authors"))
        if len(names) >= 3:
            last = _last_initial(names[0])[0]
            author = f"{last} et al."
        elif len(names) == 2:
            author = " & ".join(_last_initial(n)[0] for n in names)
        elif names:
            author = _last_initial(names[0])[0]
        else:
            author = "Anon."
        out.append(f"({author}, {_year(src)})")
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Format sources.yaml into References (APA/IEEE/Vancouver).")
    parser.add_argument("--file", required=True, help="Path to sources.yaml (list of sources)")
    parser.add_argument("--norm", default="APA 7th", choices=SUPPORTED_NORMS, help="Citation norm")
    parser.add_argument("--sort", default=None, help="alpha (APA) or order (IEEE/Vancouver)")
    parser.add_argument("--out", help="Output path (default: print to stdout)")
    parser.add_argument("--pairs", action="store_true", help="Print in-text citation snippets instead")
    args = parser.parse_args(argv)

    try:
        sources = load_sources(args.file)
        if args.pairs:
            lines = citation_pairs(sources, args.norm)
        else:
            sort = args.sort or ("alpha" if args.norm == "APA 7th" else "order")
            lines = render(sources, args.norm, sort=sort)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        print(f"references.py: {e}", file=sys.stderr)
        return 1

    if args.pairs:
        text = "Keep your in-text citations in sync with these entry primers:\n" + "\n".join(lines)
    else:
        text = "## References\n" + "\n".join(f"- {l}" for l in lines)

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())