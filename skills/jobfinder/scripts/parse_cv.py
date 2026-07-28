#!/usr/bin/env python3
"""Parse CV/Resume files (PDF, DOCX, TXT, Markdown) into a structured profile."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_pdf(path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        print("  Installing pdfplumber...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "-q"])
        import pdfplumber

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def parse_docx(path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        import docx
    except ImportError:
        print("  Installing python-docx...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "-q"])
        import docx

    doc = docx.Document(path)
    return "\n".join(para.text for para in doc.paragraphs)


def parse_text(path: str) -> str:
    """Read plain text file."""
    return Path(path).read_text(encoding="utf-8")


def extract_skills(text: str) -> list[str]:
    """Extract skills from text using common patterns."""
    skill_patterns = [
        r"skills?[:\s]+(.*?)(?:\n\n|\Z)",
        r"technical\s+skills?[:\s]+(.*?)(?:\n\n|\Z)",
        r"habilidades?[:\s]+(.*?)(?:\n\n|\Z)",
        r"technologies?[:\s]+(.*?)(?:\n\n|\Z)",
    ]

    skills = set()
    text_lower = text.lower()

    # Common tech skills to look for
    common_skills = [
        "python", "javascript", "typescript", "java", "c\\+\\+", "c#", "ruby",
        "go", "rust", "php", "swift", "kotlin", "scala", "r", "matlab",
        "html", "css", "scss", "sass", "less",
        "react", "vue", "angular", "svelte", "nextjs", "nuxt",
        "node", "express", "fastapi", "django", "flask", "spring", "rails",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
        "git", "github", "gitlab", "bitbucket",
        "linux", "bash", "powershell",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit",
        "pandas", "numpy", "data science", "data analysis",
        "rest api", "graphql", "grpc", "websockets",
        "ci/cd", "jenkins", "github actions", "gitlab ci",
        "agile", "scrum", "jira", "confluence",
        "figma", "sketch", "adobe xd",
        "sql", "nosql", "etl", "airflow", "spark",
        "blockchain", "solidity", "web3",
        "cybersecurity", "penetration testing", "owasp",
    ]

    for skill in common_skills:
        if re.search(rf"\b{skill}\b", text_lower):
            skills.add(skill.replace("\\+", "+").replace("\\", ""))

    # Try regex patterns
    for pattern in skill_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            raw = match.group(1)
            for s in re.split(r"[,\n;•\|]+", raw):
                s = s.strip().strip("-*·")
                if len(s) > 1 and len(s) < 50:
                    skills.add(s)

    return sorted(skills)


def extract_experience(text: str) -> dict:
    """Extract experience information."""
    experience = {"years": None, "roles": []}

    # Try to find years of experience
    years_match = re.search(
        r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
        text, re.IGNORECASE
    )
    if years_match:
        experience["years"] = int(years_match.group(1))

    # Try to find roles/titles
    role_patterns = [
        r"(?:senior|junior|lead|principal|staff|head|director|vp|chief)\s+\w+\s+engineer",
        r"software\s+engineer",
        r"full[\s-]?stack\s+developer",
        r"back[\s-]?end\s+developer",
        r"front[\s-]?end\s+developer",
        r"data\s+(?:scientist|engineer|analyst)",
        r"devops\s+engineer",
        r"product\s+manager",
        r"project\s+manager",
        r"ui/?ux\s+(?:designer|engineer)",
        r"mobile\s+developer",
        r"cloud\s+architect",
        r"solutions?\s+architect",
        r"technical\s+lead",
        r"engineering\s+manager",
    ]

    for pattern in role_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if m.strip() not in experience["roles"]:
                experience["roles"].append(m.strip())

    return experience


def extract_education(text: str) -> str:
    """Extract education level."""
    text_lower = text.lower()
    if "phd" in text_lower or "doctorate" in text_lower or "doctorado" in text_lower:
        return "PhD/Doctorate"
    if "master" in text_lower or "maestr" in text_lower or "mba" in text_lower:
        return "Master's Degree"
    if "bachelor" in text_lower or "licenciatur" in text_lower or "grado" in text_lower:
        return "Bachelor's Degree"
    if "bootcamp" in text_lower or "certification" in text_lower or "certificado" in text_lower:
        return "Bootcamp/Certification"
    if "diplom" in text_lower or "tecnico" in text_lower or "tecnolog" in text_lower:
        return "Technical Degree"
    return "Not specified"


def parse_cv(file_path: str) -> dict:
    """Parse a CV file and return structured profile."""
    path = Path(file_path)
    if not path.exists():
        print(f"  Error: File not found: {file_path}")
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = parse_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        text = parse_docx(file_path)
    elif suffix in (".txt", ".md", ".markdown", ".rst"):
        text = parse_text(file_path)
    else:
        print(f"  Error: Unsupported file format: {suffix}")
        sys.exit(1)

    # Extract name (first line or common patterns)
    lines = text.strip().split("\n")
    name = lines[0].strip() if lines else "Unknown"

    # Extract email
    email_match = re.search(r"[\w.-]+@[\w.-]+\.\w+", text)
    email = email_match.group(0) if email_match else None

    # Extract phone
    phone_match = re.search(r"[\+]?[\d\s\-\(\)]{7,15}", text)
    phone = phone_match.group(0).strip() if phone_match else None

    # Extract location
    location_patterns = [
        r"(?:location|ubicaci[oó]n|ciudad|city|pa[ií]s|country)[:\s]+(.+?)(?:\n|$)",
        r"(?:remote|remoto|hybrid|h[ií]brido|presencial|on[\s-]?site)",
    ]
    location = None
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(0).strip()
            break

    profile = {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "skills": extract_skills(text),
        "experience": extract_experience(text),
        "education": extract_education(text),
        "raw_text": text[:5000],  # First 5000 chars for context
    }

    return profile


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_cv.py <cv_file_path>")
        print("  Supported formats: PDF, DOCX, TXT, MD")
        sys.exit(1)

    file_path = sys.argv[1]
    profile = parse_cv(file_path)

    output_path = Path("profile.json")
    output_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Profile extracted:")
    print(f"    Name: {profile['name']}")
    print(f"    Email: {profile['email'] or 'Not found'}")
    print(f"    Skills: {', '.join(profile['skills'][:10])}{'...' if len(profile['skills']) > 10 else ''}")
    print(f"    Experience: {profile['experience']['years'] or 'Not specified'} years")
    print(f"    Education: {profile['education']}")
    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
