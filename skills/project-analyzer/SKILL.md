---
name: project-analyzer
description: >-
  Use when the user wants to analyze a codebase, audit a project, review code quality,
  find bugs, identify security issues, check performance problems, review dependencies,
  or get improvement suggestions for any project. Triggers on keywords like "analyze",
  "audit", "review", "issues", "problems", "improve", "code quality", "security review",
  "project health", "suggest improvements", "analizar", "revisar", "auditar", "que
  se puede mejorar". This skill is READ-ONLY — it never edits, modifies, or writes
  files. It produces a structured report with severity levels for each finding. Use
  this for ANY project regardless of language or framework, even if the user doesn't
  explicitly ask for an "audit" — vague requests like "look at this project" or "tell
  me what you think" should also trigger this skill.
compatibility: Language-agnostic, works with any project type. No external dependencies.
---

# Project Analyzer

Read-only skill: examine a codebase, produce structured report with severity levels. **Never modify files.**

## Severity levels

- `[CRITICAL]` — Will cause failures, data loss, or security breaches. Must fix.
- `[MAJOR]` — Significant quality or reliability issue. Should fix.
- `[MINOR]` — Minor concern. Nice to fix.
- `[SUGGESTION]` — Optional improvement.

## Workflow

**1. Understand project** — Read identity files: `README.md`, `package.json`/`pyproject.toml`, `Dockerfile`, `.gitignore`, `AGENTS.md`. Establish purpose, stack, architecture.

**2. Map structure** — Use glob + directory listing. Assess logical organization, naming conventions, separation of concerns.

**3. Sample code** — Read entry points, core logic, recently modified files, unusually large files. Check SRP, error handling, edge cases, dead code.

**4. Check dependencies** — Review `requirements.txt`/`package.json` etc. Check for outdated packages, excessive deps, loose pinning, unused imports, CVEs.

**5. Security scan** — Grep for: hardcoded secrets (`password=`, `api_key=`, `-----BEGIN`), injection risks (`shell=True`, `eval()`, SQL concat), unsafe deserialization (`pickle.loads`, `yaml.load`), insecure defaults (CORS `*`, debug mode). Verify findings by reading context.

**6. Performance** — Check for N+1 queries, unbounded file reads, missing cache, blocking in async contexts, redundant computation.

**7. Build & CI** — Check build config, CI pipeline, test setup. Don't run them — infer from config.

## Report structure

```
## Project Overview  (purpose, stack, size, architecture)
## Project Structure (layout assessment)
## Code Quality      (readability, patterns, testing)
## Potential Bugs & Issues (concrete risks with severity)
## Security Concerns (findings with severity + pattern)
## Performance Considerations
## Dependency Health
## Recommendations  (top 3-5 actionable, ordered by priority)
```

Skip empty sections with "No significant issues found." Don't force every section if nothing notable.

## Guidelines

- **Be specific**: cite files and line ranges (`src/handlers/auth.ts:45-52`)
- **Explain impact**: "user sees blank page" not "error not handled"
- **Acknowledge positives**: praise good CI, tests, architecture
- **Fit maturity**: small script ≠ production service rigor
- **Read broadly, cite precisely**
- **Say when unsure**: "tests may not exist yet"
