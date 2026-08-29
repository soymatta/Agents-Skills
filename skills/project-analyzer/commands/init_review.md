---
description: Analyze the project and suggest improvements (read-only; delegates to the project-analyzer skill)
---

Run the **project-analyzer** skill (see `skills/project-analyzer/SKILL.md` for full workflow, severity
taxonomy, security triage rules, prioritization, and baseline/delta).

Essentials if the skill body can't be loaded:
- Read-only with respect to the audited code — never edit/create/delete project files.
- Ask one optional scoping question ("audit everything, or focus on X?"), then run non-stop.
- Exclude `node_modules`, `.git`, build/dist, venvs, caches.
- Produce a structured report with severity levels CRITICAL > MAJOR > MINOR > SUGGESTION.
- Cite specific file paths and line ranges; explain user-visible impact; acknowledge strengths.
- Write findings copy to `reports/audit-<iso>.json` for baseline/delta on re-runs.
