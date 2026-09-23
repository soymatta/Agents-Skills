#!/usr/bin/env python3
"""Generate professional CV PDF from JSON data (ES + EN).

Usage:
    python generate_cv_pdf.py --input cv_data.json --output ./output

JSON format:
{
    "name": "Full Name",
    "title": "Professional Title",
    "contact": {
        "email": "email@example.com",
        "phone": "1234567890",
        "linkedin": "linkedin.com/in/username/",
        "location": "City, Country",
        "website": "website.com/"
    },
    "profile": "Brief professional summary...",
    "skills": {
        "Category": "skill1, skill2, skill3"
    },
    "experience": [
        {
            "company": "Company Name",
            "role": "Job Title",
            "period": "Month Year - Month Year",
            "bullets": ["Achievement 1", "Achievement 2"]
        }
    ],
    "projects": [
        {
            "name": "Project Name (Award/Recognition)",
            "role": "Developer Role",
            "bullets": ["Description 1"]
        }
    ],
    "education": [
        {
            "institution": "University Name",
            "degree": "Degree Title",
            "period": "Year - Year",
            "details": "Optional details"
        }
    ],
    "languages": {
        "Language": "Level"
    }
}
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    print("  Error: fpdf2 not installed. Run: pip install fpdf2")
    sys.exit(1)


def _setup_encoding():
    """Configure stdout/stderr for UTF-8 on Windows (call when needed, not at import)."""
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _tl(value, lang: str):
    """Resolve a (possibly localized) field for the requested language.

    A translatable field may be either a plain string, or a dict keyed by
    language code (e.g. {"en": "...", "es": "..."}). Lists are mapped
    element-wise so bullets/items translate individually. This lets a single
    JSON drive fully localized ES and EN PDFs (only section headers were local
    before, leaving body content in English in both outputs).
    """
    if isinstance(value, dict):
        if "en" in value or "es" in value:
            return value.get(lang) or value.get("en") or next(iter(value.values()), "")
        return value
    if isinstance(value, list):
        return [_tl(item, lang) for item in value]
    return value


# === COLOR SCHEME ===
PRIMARY = (11, 43, 74)
SECONDARY = (26, 58, 92)
TEXT_DARK = (30, 30, 30)
TEXT_GRAY = (100, 100, 100)
TEXT_LIGHT = (140, 140, 140)
LINE_COLOR = (200, 200, 200)


class CVPdf(FPDF):
    def __init__(self):
        super().__init__(unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self._font = self._setup_fonts()

    def _setup_fonts(self) -> str:
        """Register fonts with cross-platform fallback."""
        import platform
        system = platform.system()

        font_dirs = {
            "Windows": Path(r"C:\Windows\Fonts"),
            "Darwin": Path("/Library/Fonts"),  # macOS
            "Linux": Path("/usr/share/fonts/truetype") / "msttcorefonts",
        }
        font_dir = font_dirs.get(system)

        # Segoe UI (Windows), Calibri-like alternatives on other OS
        font_candidates = [
            ("Segoe", {"": "segoeui.ttf", "B": "segoeuib.ttf", "I": "segoeuii.ttf", "BI": "segoeuiz.ttf"}),
            ("DejaVu", {"": "DejaVuSans.ttf", "B": "DejaVuSans-Bold.ttf", "I": "DejaVuSans-Oblique.ttf", "BI": "DejaVuSans-BoldOblique.ttf"}),
        ]

        if font_dir:
            for font_name, files in font_candidates:
                try:
                    all_found = True
                    for style, filename in files.items():
                        path = font_dir / filename
                        if not path.exists():
                            # Try sibling directories
                            for sub in font_dir.iterdir():
                                if sub.is_dir():
                                    path = sub / filename
                                    if path.exists():
                                        break
                            else:
                                all_found = False
                                break
                        self.add_font(font_name, style, str(path))
                    if all_found:
                        return font_name
                except Exception:
                    continue

        return "Helvetica"

    def footer(self):
        """Page number in footer."""
        self.set_y(-10)
        self.set_font(self._font, "", 8)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(0, 10, f"{self.page_no()}", align="C")

    def header_name(self, name: str):
        self.set_font(self._font, "B", 20)
        self.set_text_color(*PRIMARY)
        self.cell(0, 9, name, new_x="LMARGIN", new_y="NEXT")

    def header_title(self, title: str):
        self.set_font(self._font, "", 12)
        self.set_text_color(*TEXT_GRAY)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")

    def header_contact(self, parts: list[str]):
        self.set_font(self._font, "", 10)
        self.set_text_color(*TEXT_LIGHT)
        line = " \u00b7 ".join(p for p in parts if p)
        self.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def section(self, title: str):
        self.ln(3)
        self.set_font(self._font, "B", 12)
        self.set_text_color(*PRIMARY)
        self.cell(0, 7, title.upper(), new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self.set_draw_color(*LINE_COLOR)
        self.set_line_width(0.3)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(2)

    def entry(self, title: str, subtitle: str = ""):
        self.set_font(self._font, "B", 11)
        self.set_text_color(*SECONDARY)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font(self._font, "I", 10)
            self.set_text_color(*TEXT_GRAY)
            self.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def bullet(self, text: str):
        self.set_font(self._font, "", 10)
        self.set_text_color(*TEXT_DARK)
        x = self.l_margin + 3
        self.set_x(x)
        self.cell(3, 5, "\u2022")
        self.set_x(x + 3)
        w = self.w - self.r_margin - x - 3
        self.multi_cell(w, 5, text)
        self.ln(0.5)

    def skill_row(self, label: str, value: str):
        self.set_font(self._font, "B", 10)
        self.set_text_color(*TEXT_DARK)
        lw = self.get_string_width(label + ": ") + 1
        self.cell(lw, 5, label + ": ")
        self.set_font(self._font, "", 10)
        remaining = self.w - self.r_margin - self.get_x()
        self.multi_cell(remaining, 5, value)
        self.ln(0.5)

    def body(self, text: str, size: int = 10):
        self.set_font(self._font, "", size)
        self.set_text_color(*TEXT_DARK)
        self.multi_cell(0, 5, text)
        self.ln(0.5)


def generate_cv(data: dict, output_path: str, lang: str = "es"):
    """Generate CV PDF from data dict.

    Args:
        data: CV data dictionary. Translatable fields (profile, skills values,
            experience role/bullets, project bullets, education degree/details,
            languages) may be plain strings or {"en": .., "es": ..} dicts so a
            single JSON produces a fully-localized CV in each language.
        output_path: Output PDF file path
        lang: Language code ('es' or 'en')
    """
    pdf = CVPdf()
    pdf.add_page()

    # === HEADER ===
    pdf.header_name(data.get("name", ""))
    pdf.header_title(_tl(data.get("title", ""), lang))

    contact = data.get("contact", {})
    contact_parts = [
        _tl(contact.get("email", ""), lang),
        _tl(contact.get("phone", ""), lang),
        _tl(contact.get("linkedin", ""), lang),
        _tl(contact.get("location", ""), lang),
        _tl(contact.get("website", ""), lang),
    ]
    pdf.header_contact([p for p in contact_parts if p])

    # === PROFILE ===
    profile = _tl(data.get("profile", ""), lang)
    if profile:
        profile_label = "Perfil" if lang == "es" else "Profile"
        pdf.section(profile_label)
        pdf.body(profile)

    # === SKILLS ===
    if data.get("skills"):
        skills_label = "Habilidades" if lang == "es" else "Skills"
        pdf.section(skills_label)
        skills_data = data["skills"]
        if isinstance(skills_data, dict):
            pairs = skills_data.items()
        else:
            pairs = []
            for item in skills_data:
                if isinstance(item, dict):
                    pairs.append((_tl(item.get("category") or item.get("name") or "", lang),
                                  _tl(item.get("value") or item.get("items") or "", lang)))
                else:
                    pairs.append((item, ""))
        for category, items in pairs:
            pdf.skill_row(_tl(category, lang), _tl(items, lang))

    # === EXPERIENCE ===
    if data.get("experience"):
        exp_label = "Experiencia" if lang == "es" else "Experience"
        pdf.section(exp_label)
        for job in data["experience"]:
            subtitle = f"{_tl(job.get('role', ''), lang)} \u00b7 {_tl(job.get('period', ''), lang)}"
            pdf.entry(_tl(job.get("company", ""), lang), subtitle.strip(" \u00b7"))
            for bullet in _tl(job.get("bullets", []), lang):
                pdf.bullet(bullet)

    # === PROJECTS ===
    if data.get("projects"):
        proj_label = "Proyectos" if lang == "es" else "Projects"
        pdf.section(proj_label)
        for project in data["projects"]:
            pdf.entry(_tl(project.get("name", ""), lang), _tl(project.get("role", ""), lang))
            for bullet in _tl(project.get("bullets", []), lang):
                pdf.bullet(bullet)

    # === EDUCATION ===
    if data.get("education"):
        edu_label = "Educaci\u00f3n" if lang == "es" else "Education"
        pdf.section(edu_label)
        for edu in data["education"]:
            subtitle = f"{_tl(edu.get('institution', ''), lang)} \u00b7 {_tl(edu.get('period', ''), lang)}"
            pdf.entry(_tl(edu.get("degree", ""), lang), subtitle.strip(" \u00b7"))
            if edu.get("details"):
                pdf.body(_tl(edu["details"], lang))
            pdf.ln(2)  # spacing between education entries

    # === CERTIFICATIONS / LICENSES ===
    if data.get("certifications"):
        cert_label = "Certificaciones y Licencias" if lang == "es" else "Certifications & Licenses"
        pdf.section(cert_label)
        if isinstance(data["certifications"], list):
            items = [{"name": it.get("name"), "issuer": it.get("issuer"), "id": it.get("id")}
                     for it in data["certifications"] if isinstance(it, dict)]
            for it in items:
                subtitle = " \u00b7 ".join(
                    p for p in [_tl(it.get("issuer", ""), lang), _tl(it.get("id", ""), lang)] if p
                )
                pdf.entry(_tl(it.get("name", ""), lang), subtitle)
        else:
            for name, issuer in data["certifications"].items():
                pdf.entry(_tl(name, lang), _tl(issuer, lang))

    # === LANGUAGES ===
    if data.get("languages"):
        lang_label = "Idiomas" if lang == "es" else "Languages"
        pdf.section(lang_label)
        languages = data["languages"]
        if isinstance(languages, dict):
            pairs = languages.items()
        else:
            pairs = []
            for item in languages:
                if isinstance(item, dict):
                    pairs.append((item.get("language") or item.get("name") or "", item.get("level") or ""))
                else:
                    pairs.append((item, ""))
        for language, level in pairs:
            pdf.skill_row(_tl(language, lang), _tl(level, lang))

    pdf.output(output_path)
    print(f"  CV ({lang.upper()}): {output_path}")


def main():
    _setup_encoding()
    import argparse
    parser = argparse.ArgumentParser(description="Generate professional CV PDFs (ES + EN)")
    parser.add_argument("--input", "-i", required=True, help="Path to CV JSON file")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current)")
    args = parser.parse_args()

    json_path = Path(args.input)
    if not json_path.exists():
        print(f"  Error: {json_path} not found")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))

    name = data.get("name", "CV").replace(" ", "_")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    es_path = str(output_dir / f"{name}_CV_ES.pdf")
    en_path = str(output_dir / f"{name}_CV_EN.pdf")

    generate_cv(data, es_path, lang="es")
    generate_cv(data, en_path, lang="en")


if __name__ == "__main__":
    main()
