#!/usr/bin/env python3
"""Convert Markdown CV to JSON format for generate_cv_pdf.py."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_md_cv(md_path: str) -> dict:
    """Parse markdown CV into structured JSON."""
    text = Path(md_path).read_text(encoding="utf-8")
    lines = text.split("\n")

    data = {
        "name": "",
        "title": "",
        "contact": {},
        "profile": "",
        "skills": {},
        "experience": [],
        "projects": [],
        "education": [],
        "languages": {},
    }

    section = None
    current_entry = None
    current_bullets = []

    def flush_entry():
        nonlocal current_entry, current_bullets
        if current_entry and current_bullets:
            current_entry["bullets"] = current_bullets
        current_entry = None
        current_bullets = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        # Name (H1)
        if stripped.startswith("# ") and not section:
            data["name"] = stripped[2:].strip()
            continue

        # Section headers (uppercase lines)
        upper = stripped.upper()
        if stripped == upper and len(stripped) > 2 and not stripped.startswith("#"):
            flush_entry()
            if upper in ("PERFIL", "PROFILE"):
                section = "profile"
            elif upper in ("HABILIDADES", "SKILLS"):
                section = "skills"
            elif upper in ("EXPERIENCIA", "EXPERIENCE"):
                section = "experience"
            elif upper in ("PROYECTOS", "PROJECTS"):
                section = "projects"
            elif upper in ("EDUCACIÓN", "EDUCACION", "EDUCATION"):
                section = "education"
            elif upper in ("IDIOMAS", "LANGUAGES"):
                section = "languages"
            else:
                section = upper.lower()
            continue

        # Title (line after name, before contact)
        if not section and not data["title"] and data["name"] and "@" not in stripped and "·" not in stripped:
            data["title"] = stripped
            continue

        # Contact line (contains email or ·)
        if not section and ("@" in stripped or "·" in stripped):
            parts = [p.strip() for p in stripped.split("·")]
            for part in parts:
                part = part.strip()
                if "@" in part:
                    data["contact"]["email"] = part
                elif part.isdigit():
                    data["contact"]["phone"] = part
                elif "linkedin" in part.lower():
                    data["contact"]["linkedin"] = part
                elif "github.io" in part or "portfolio" in part.lower():
                    data["contact"]["website"] = part
                elif any(c.isalpha() for c in part) and not any(c.isdigit() for c in part):
                    data["contact"]["location"] = part
            continue

        # Profile section
        if section == "profile":
            data["profile"] = stripped
            section = None
            continue

        # Skills section
        if section == "skills":
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                data["skills"][key.strip()] = val.strip()
            continue

        # Experience section
        if section == "experience":
            # Bullet point
            if stripped.startswith("•") or stripped.startswith("-") or stripped.startswith("*"):
                bullet = stripped.lstrip("•-* ").strip()
                if current_bullets is not None:
                    current_bullets.append(bullet)
                continue

            # Company name (no · or |, not a bullet)
            if "·" not in stripped and "|" not in stripped:
                flush_entry()
                current_entry = {"company": stripped, "role": "", "period": "", "bullets": []}
                current_bullets = current_entry["bullets"]
                data["experience"].append(current_entry)
                continue

            # Role and period line
            if current_entry:
                if "·" in stripped:
                    parts = stripped.split("·", 1)
                    current_entry["role"] = parts[0].strip()
                    current_entry["period"] = parts[1].strip()
                else:
                    current_entry["role"] = stripped
            continue

        # Projects section
        if section == "projects":
            if stripped.startswith("•") or stripped.startswith("-") or stripped.startswith("*"):
                bullet = stripped.lstrip("•-* ").strip()
                if current_bullets is not None:
                    current_bullets.append(bullet)
                continue

            # Project name with role (contains |)
            if "|" in stripped:
                flush_entry()
                name_part, role_part = stripped.split("|", 1)
                current_entry = {"name": name_part.strip(), "role": role_part.strip(), "bullets": []}
                current_bullets = current_entry["bullets"]
                data["projects"].append(current_entry)
                continue

            # Project name without role
            flush_entry()
            current_entry = {"name": stripped, "role": "", "bullets": []}
            current_bullets = current_entry["bullets"]
            data["projects"].append(current_entry)
            continue

        # Education section
        if section == "education":
            if "·" in stripped:
                # Degree + period line (e.g., "Especialización en Seguridad Informática · Actualmente")
                parts = stripped.split("·", 1)
                degree = parts[0].strip()
                period = parts[1].strip()
                # Find the last entry without a degree (institution-only line)
                if data["education"] and not data["education"][-1].get("degree"):
                    data["education"][-1]["degree"] = degree
                    data["education"][-1]["period"] = period
                else:
                    flush_entry()
                    current_entry = {
                        "institution": "",
                        "degree": degree,
                        "period": period,
                        "details": ""
                    }
                    data["education"].append(current_entry)
            elif stripped.startswith("Asignaturas:"):
                # Details line
                if data["education"]:
                    data["education"][-1]["details"] = stripped
            else:
                # Institution name (line before degree)
                flush_entry()
                current_entry = {
                    "institution": stripped,
                    "degree": "",
                    "period": "",
                    "details": ""
                }
                data["education"].append(current_entry)
            continue

        # Languages section
        if section == "languages":
            if ":" in stripped:
                key, val = stripped.split(":", 1)
                data["languages"][key.strip()] = val.strip()
            continue

    flush_entry()
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python md_to_json.py <cv.md> [output.json]")
        sys.exit(1)

    md_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else md_path.rsplit(".", 1)[0] + ".json"

    data = parse_md_cv(md_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Converted: {md_path} -> {output_path}")
    print(f"  Name: {data['name']}")
    print(f"  Sections: profile={bool(data['profile'])}, skills={len(data['skills'])}, "
          f"experience={len(data['experience'])}, projects={len(data['projects'])}, "
          f"education={len(data['education'])}, languages={len(data['languages'])}")


if __name__ == "__main__":
    main()
