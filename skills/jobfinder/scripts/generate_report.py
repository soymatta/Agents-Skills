#!/usr/bin/env python3
"""Genera reportes de búsqueda de empleo en Markdown y HTML."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💼</text></svg>">
<title>Reporte de Empleo - {user_name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #fafafa; color: #1a1a1a; line-height: 1.6; padding: 1.5rem; }}
.container {{ max-width: 800px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; margin-bottom: 0.3rem; }}
h2 {{ font-size: 1.2rem; margin: 1.5rem 0 0.8rem; color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }}
h3 {{ font-size: 1rem; margin: 0.8rem 0 0.4rem; color: #444; }}
.date {{ color: #888; font-size: 0.85rem; margin-bottom: 1rem; }}
.profile {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin: 0.8rem 0; }}
.profile-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; font-size: 0.9rem; }}
.profile-label {{ color: #888; font-size: 0.8rem; }}
.job-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin: 0.8rem 0; border-left: 3px solid #22c55e; }}
.job-card.score-high {{ border-left-color: #22c55e; }}
.job-card.score-mid {{ border-left-color: #eab308; }}
.job-card.score-low {{ border-left-color: #ef4444; }}
.job-card.not-viable {{ border-left-color: #9ca3af; opacity: 0.7; }}
.job-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem; }}
.job-title {{ font-size: 1.05rem; font-weight: 600; }}
.job-company {{ color: #666; font-size: 0.9rem; }}
.score-badge {{ padding: 0.2rem 0.6rem; border-radius: 12px; font-weight: 600; font-size: 0.8rem; }}
.score-badge.high {{ background: #dcfce7; color: #166534; }}
.score-badge.mid {{ background: #fef9c3; color: #854d0e; }}
.score-badge.low {{ background: #fee2e2; color: #991b1b; }}
.score-badge.viable {{ background: #e5e7eb; color: #374151; }}
.job-meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.3rem; margin: 0.5rem 0; font-size: 0.85rem; color: #666; }}
.skill-tag {{ display: inline-block; padding: 0.15rem 0.4rem; border-radius: 4px; margin: 0.15rem; font-size: 0.75rem; }}
.skill-match {{ background: #dcfce7; color: #166534; }}
.skill-missing {{ background: #fee2e2; color: #991b1b; }}
.skill-nice {{ background: #e5e7eb; color: #374151; }}
.analysis {{ color: #666; font-size: 0.85rem; margin-top: 0.5rem; font-style: italic; }}
.gap-table {{ width: 100%; border-collapse: collapse; margin: 0.8rem 0; font-size: 0.85rem; }}
.gap-table th {{ text-align: left; padding: 0.5rem; border-bottom: 2px solid #e0e0e0; color: #555; }}
.gap-table td {{ padding: 0.5rem; border-bottom: 1px solid #f0f0f0; }}
.priority-high {{ color: #dc2626; font-weight: 600; }}
.priority-mid {{ color: #ca8a04; }}
.project-card {{ background: #f9f9f9; border: 1px solid #e5e7eb; border-radius: 6px; padding: 0.8rem; margin: 0.5rem 0; }}
.project-card a {{ color: #2563eb; text-decoration: none; }}
.project-card a:hover {{ text-decoration: underline; }}
.project-stars {{ color: #ca8a04; font-size: 0.8rem; }}
.project-why {{ color: #666; font-size: 0.8rem; margin-top: 0.2rem; }}
.action-item {{ padding: 0.4rem 0; border-left: 2px solid #e0e0e0; padding-left: 0.8rem; margin: 0.4rem 0; font-size: 0.9rem; }}
a {{ color: #2563eb; }}
</style>
</head>
<body>
<div class="container">
<h1>💼 Reporte de Empleo</h1>
<p class="date">Generado: {date}</p>

<h2>Perfil</h2>
<div class="profile">
<div class="profile-grid">
<div><div class="profile-label">Nombre</div><span>{user_name}</span></div>
<div><div class="profile-label">Rol</div><span>{current_role}</span></div>
<div><div class="profile-label">Experiencia</div><span>{years_exp} años</span></div>
<div><div class="profile-label">Educación</div><span>{education}</span></div>
<div><div class="profile-label">Ubicación</div><span>{location}</span></div>
<div><div class="profile-label">Preferencia</div><span>{work_pref}</span></div>
<div><div class="profile-label">Salario Esperado</div><span>{salary_range}</span></div>
</div>
<div style="margin-top:0.6rem"><div class="profile-label">Skills</div><div>{skills_html}</div></div>
</div>

<h2>Mejores Coincidencias ({total_matches} total)</h2>
{jobs_html}

<h2>Análisis de Skills Faltantes</h2>
<table class="gap-table">
<tr><th>Skill</th><th>Frecuencia</th><th>Tu Nivel</th><th>Prioridad</th></tr>
{gap_html}
</table>

<h2>Proyecto Recomendado por Vacante</h2>
{projects_html}

<h2>Plan de Mejora</h2>
{actions_html}

</div>
</body>
</html>"""


def _format_education(education) -> str:
    if isinstance(education, str):
        return education
    if isinstance(education, dict):
        return education.get("degree", str(education))
    if isinstance(education, list):
        parts = []
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get("degree", "")
                inst = edu.get("institution", "")
                period = edu.get("period", edu.get("status", ""))
                entry = f"{degree}"
                if inst:
                    entry += f" — {inst}"
                if period:
                    entry += f" ({period})"
                parts.append(entry)
            elif isinstance(edu, str):
                parts.append(edu)
        return " | ".join(parts) if parts else "N/A"
    return str(education)


def _format_salary_cop_usd(salary_min, salary_max, currency):
    """Format salary with both COP and USD if possible."""
    if not salary_min or not salary_max:
        return "No publicado"

    COP_USD_RATE = 4200  # Approximate rate

    if currency and currency.upper() == "COP":
        usd_min = int(salary_min / COP_USD_RATE)
        usd_max = int(salary_max / COP_USD_RATE)
        return f"${salary_min:,.0f} COP (~${usd_min:,}-${usd_max:,} USD)"
    elif currency and currency.upper() == "USD":
        cop_min = int(salary_min * COP_USD_RATE)
        cop_max = int(salary_max * COP_USD_RATE)
        return f"${salary_min:,}-${salary_max:,} USD (~${cop_min:,.0f}-${cop_max:,.0f} COP)"
    else:
        return f"{currency} {salary_min:,.0f} - {salary_max:,.0f}"


def generate_markdown(profile: dict, scored_jobs: list, projects: list) -> str:
    lines = []
    name = profile.get("name", "Desconocido")
    lines.append(f"# 💼 Reporte de Empleo — {name}")
    lines.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Perfil
    lines.append("## Perfil")
    lines.append(f"- **Nombre**: {profile.get('name', 'N/A')}")
    exp = profile.get('experience', {})
    roles = exp.get('roles', []) if isinstance(exp, dict) else []
    years = exp.get('years', 'N/A') if isinstance(exp, dict) else 'N/A'
    lines.append(f"- **Rol**: {', '.join(roles) if roles else 'N/A'}")
    lines.append(f"- **Experiencia**: {years} años")
    lines.append(f"- **Skills**: {', '.join(profile.get('skills', []))}")
    lines.append(f"- **Ubicación**: {profile.get('location', 'N/A')}")
    lines.append(f"- **Preferencia**: {profile.get('remote_preference', 'N/A')}")
    lines.append(f"- **Salario Esperado**: {profile.get('salary_expected', 'No especificado')}")
    lines.append(f"- **Educación**: {_format_education(profile.get('education', 'N/A'))}\n")

    # Top matches
    lines.append("## Mejores Coincidencias")
    for i, job in enumerate(scored_jobs[:10], 1):
        score = job.get("total_score", 0)
        viable = job.get("experience_viable", True)
        score_cls = "ALTO" if score >= 70 else "MEDIO" if score >= 50 else "BAJO"
        if not viable:
            score_cls = "NO VIABLE"

        lines.append(f"### {i}. {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}")
        lines.append(f"| Campo | Valor |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Match | **{score:.0f}%** [{score_cls}] |")
        lines.append(f"| Ubicación | {job.get('location', 'N/A')} |")

        salary_str = _format_salary_cop_usd(job.get('salary_min'), job.get('salary_max'), job.get('salary_currency', 'USD'))
        lines.append(f"| Salario | {salary_str} |")
        lines.append(f"| Tipo | {job.get('job_type', 'N/A')} |")
        lines.append(f"| Publicado | {job.get('posted', 'N/A')} |")
        lines.append(f"| Aplicar | {job.get('url', 'N/A')} |\n")

        matched = job.get("matched_skills", [])
        missing = job.get("missing_skills", [])
        nice = job.get("nice_to_have", [])

        if matched:
            lines.append(f"**Skills que tienes**: {', '.join(matched)}")
        if missing:
            lines.append(f"**Skills faltantes**: {', '.join(missing)}")
        if nice:
            lines.append(f"**Deseables**: {', '.join(nice)}")

        if job.get("required_years"):
            lines.append(f"**Experiencia requerida**: {job['required_years']} años | **Tu experiencia**: {years} años")

        lines.append(f"\n**Análisis**: {job.get('analysis', '')}\n")

        # 1 project per vacancy
        job_proj = next((p for p in projects if p.get("job_title") == job.get("title")), None)
        if job_proj:
            lines.append(f"**Proyecto para demostrar habilidades**: [{job_proj['name']}]({job_proj['url']}) ({job_proj.get('stars', '')}) — {job_proj.get('reason', '')}")

        lines.append("\n---\n")

    # Skills gap
    lines.append("## Análisis de Skills Faltantes")
    lines.append("| Skill | Frecuencia | Tu Nivel | Prioridad |")
    lines.append("|-------|------------|----------|-----------|")

    skill_freq = {}
    for job in scored_jobs:
        for s in job.get("missing_skills", []):
            skill_freq[s] = skill_freq.get(s, 0) + 1

    total = len(scored_jobs) if scored_jobs else 1
    for skill, count in sorted(skill_freq.items(), key=lambda x: -x[1])[:15]:
        pct = count / total * 100
        priority = "ALTA" if pct > 30 else "MEDIA" if pct > 15 else "BAJA"
        has_skill = "Sí" if skill in [s.lower() for s in profile.get("skills", [])] else "No"
        lines.append(f"| {skill} | {pct:.0f}% | {has_skill} | {priority} |")

    # Proyectos por vacante
    lines.append("\n## Proyectos Recomendados")
    seen = set()
    for proj in projects:
        job_key = proj.get("job_title", "")
        if job_key not in seen:
            seen.add(job_key)
            lines.append(f"### Para: {job_key}")
            lines.append(f"- **[{proj.get('name', 'N/A')}]({proj.get('url', '#')})** ({proj.get('stars', '')}) — {proj.get('reason', '')}")

    # Plan de acción
    lines.append("## Plan de Mejora")
    lines.append("### Inmediato (esta semana)")
    for skill, count in sorted(skill_freq.items(), key=lambda x: -x[1])[:3]:
        lines.append(f"- Estudiar y practicar **{skill}** — aparece en {skill_freq[skill]/total*100:.0f}% de las vacantes")
    lines.append("\n### Corto plazo (este mes)")
    lines.append("- Construir un proyecto portafolio usando 1-2 skills faltantes")
    lines.append("- Completar un curso o certificación online")
    lines.append("\n### Mediano plazo (este trimestre)")
    lines.append("- Contribuir a proyectos open-source en el tech stack objetivo")
    lines.append("- Actualizar LinkedIn y CV con nuevas skills")

    # Tabla resumen
    lines.append(f"\n## Todas las Coincidencias ({len(scored_jobs)} total)")
    lines.append("| # | Título | Empresa | Score | Ubicación | Salario |")
    lines.append("|---|--------|---------|-------|-----------|---------|")
    for i, job in enumerate(scored_jobs, 1):
        salary = _format_salary_cop_usd(job.get('salary_min'), job.get('salary_max'), job.get('salary_currency', 'USD'))
        viable = "✓" if job.get("experience_viable", True) else "✗"
        lines.append(f"| {i} | {viable} {job.get('title', 'N/A')} | {job.get('company', 'N/A')} | {job.get('total_score', 0):.0f}% | {job.get('location', 'N/A')} | {salary} |")

    return "\n".join(lines)


def generate_html(profile: dict, scored_jobs: list, projects: list) -> str:
    name = profile.get("name", "Desconocido")
    exp = profile.get("experience", {})
    roles = exp.get("roles", []) if isinstance(exp, dict) else []
    years = exp.get("years", "N/A") if isinstance(exp, dict) else "N/A"
    skills = profile.get("skills", [])
    location = profile.get("location", "N/A")
    salary = profile.get("salary_expected", "No especificado")
    education = _format_education(profile.get("education", "N/A"))
    work_pref = profile.get("remote_preference", "N/A")

    skills_html = " ".join(f'<span class="skill-tag skill-match">{s}</span>' for s in skills)

    jobs_html = ""
    for i, job in enumerate(scored_jobs[:10], 1):
        score = job.get("total_score", 0)
        viable = job.get("experience_viable", True)
        score_cls = "score-high" if score >= 70 and viable else "score-mid" if score >= 50 else "score-low" if viable else "not-viable"
        badge_cls = "high" if score >= 70 and viable else "mid" if score >= 50 else "low" if viable else "viable"
        badge_text = f"{score:.0f}%" if viable else f"{score:.0f}% (No viable)"

        matched_html = " ".join(f'<span class="skill-tag skill-match">{s}</span>' for s in job.get("matched_skills", []))
        missing_html = " ".join(f'<span class="skill-tag skill-missing">{s}</span>' for s in job.get("missing_skills", []))
        nice_html = " ".join(f'<span class="skill-tag skill-nice">{s}</span>' for s in job.get("nice_to_have", []))

        salary_str = _format_salary_cop_usd(job.get("salary_min"), job.get("salary_max"), job.get("salary_currency", "USD"))

        exp_note = ""
        if job.get("required_years"):
            exp_note = f'<div style="font-size:0.8rem;color:#666;margin-top:0.3rem">Experiencia requerida: {job["required_years"]} años</div>'

        # Find 1 project for this vacancy
        job_proj = next((p for p in projects if p.get("job_title") == job.get("title")), None)
        project_html = ""
        if job_proj:
            project_html = f'''
<div style="margin-top:0.5rem;font-size:0.85rem">
  <strong>Proyecto:</strong> <a href="{job_proj.get("url", "#")}" target="_blank">{job_proj.get("name", "")}</a>
  <span class="project-stars">({job_proj.get("stars", "")})</span>
  <div class="project-why">{job_proj.get("reason", "")}</div>
</div>'''

        jobs_html += f'''
<div class="job-card {score_cls}">
  <div class="job-header">
    <div>
      <div class="job-title">{i}. {job.get("title", "N/A")}</div>
      <div class="job-company">{job.get("company", "N/A")}</div>
    </div>
    <div class="score-badge {badge_cls}">{badge_text}</div>
  </div>
  <div class="job-meta">
    <div><span class="profile-label">Ubicación</span><br>{job.get("location", "N/A")}</div>
    <div><span class="profile-label">Salario</span><br>{salary_str}</div>
    <div><span class="profile-label">Tipo</span><br>{job.get("job_type", "N/A")}</div>
    <div><span class="profile-label">Publicado</span><br>{job.get("posted", "N/A")}</div>
  </div>
  <div>
    {"<strong>Skills:</strong> " + matched_html if matched_html else ""}
    {"<br><strong>Faltantes:</strong> " + missing_html if missing_html else ""}
    {"<br><strong>Deseables:</strong> " + nice_html if nice_html else ""}
  </div>
  {exp_note}
  <div class="analysis">{job.get("analysis", "")}</div>
  <div style="margin-top:0.5rem"><a href="{job.get("url", "#")}" target="_blank">Ver vacante →</a></div>
  {project_html}
</div>'''

    # Skills gap
    skill_freq = {}
    for job in scored_jobs:
        for s in job.get("missing_skills", []):
            skill_freq[s] = skill_freq.get(s, 0) + 1
    total = len(scored_jobs) if scored_jobs else 1

    gap_html = ""
    for skill, count in sorted(skill_freq.items(), key=lambda x: -x[1])[:15]:
        pct = count / total * 100
        priority_cls = "priority-high" if pct > 30 else "priority-mid" if pct > 15 else ""
        priority_text = "ALTA" if pct > 30 else "MEDIA" if pct > 15 else "BAJA"
        has_skill = "Sí" if skill in [s.lower() for s in skills] else "No"
        gap_html += f'<tr><td>{skill}</td><td>{pct:.0f}%</td><td>{has_skill}</td><td class="{priority_cls}">{priority_text}</td></tr>'

    # Projects (1 per vacancy, deduplicated)
    seen_jobs = set()
    unique_projects = []
    for proj in projects:
        job_key = proj.get("job_title", "")
        if job_key not in seen_jobs:
            unique_projects.append(proj)
            seen_jobs.add(job_key)

    projects_html = ""
    for proj in unique_projects:
        projects_html += f'''
<div class="project-card">
  <strong>Para: {proj.get("job_title", "N/A")}</strong>
  <div style="margin-top:0.3rem"><a href="{proj.get("url", "#")}" target="_blank">{proj.get("name", "N/A")}</a>
  <span class="project-stars">({proj.get("stars", "")} stars)</span></div>
  <div class="project-why">{proj.get("reason", "")}</div>
</div>'''

    # Actions
    top_skills = sorted(skill_freq.items(), key=lambda x: -x[1])[:3]
    actions_html = ""
    for skill, count in top_skills:
        actions_html += f'<div class="action-item">Estudiar <strong>{skill}</strong> — aparece en {skill_freq[skill]/total*100:.0f}% de las vacantes</div>'
    actions_html += '<div class="action-item">Construir proyecto portafolio usando 1-2 skills faltantes</div>'
    actions_html += '<div class="action-item">Contribuir a proyectos open-source en el tech stack objetivo</div>'

    html = HTML_TEMPLATE.format(
        user_name=name,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        current_role=", ".join(roles) if roles else "N/A",
        years_exp=years or "N/A",
        education=education,
        location=location,
        work_pref=work_pref,
        salary_range=salary or "N/A",
        skills_html=skills_html,
        total_matches=len(scored_jobs),
        jobs_html=jobs_html,
        gap_html=gap_html,
        projects_html=projects_html,
        actions_html=actions_html,
    )
    return html


def main():
    profile_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("profile.json")
    scored_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("scored.json")
    projects_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("projects.json")
    output_base = sys.argv[4] if len(sys.argv) > 4 else "job-report"

    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
    scored = json.loads(scored_path.read_text(encoding="utf-8")) if scored_path.exists() else []
    projects = json.loads(projects_path.read_text(encoding="utf-8")) if projects_path.exists() else []

    # Generate Markdown
    md = generate_markdown(profile, scored, projects)
    md_path = Path(f"{output_base}.md")
    md_path.write_text(md, encoding="utf-8")
    print(f"  Reporte Markdown: {md_path}")

    # Generate HTML
    html = generate_html(profile, scored, projects)
    html_path = Path(f"{output_base}.html")
    html_path.write_text(html, encoding="utf-8")
    print(f"  Reporte HTML: {html_path}")


if __name__ == "__main__":
    main()
