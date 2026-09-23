---
name: project-analyzer
description: >-
  Analyzes a codebase, audits a project, reviews code quality, finds bugs, identifies security issues, checks
  performance, and reviews dependencies. READ-ONLY on the target code (may write its own reports/audit-*.json).
  Produces a severity-rated report (CRITICAL/MAJOR/MINOR/SUGGESTION) prioritized by severity x probability x
  effort, with baseline/delta on re-runs. Language-agnostic; works with any project. Asks one optional scoping
  question then runs non-stop. Use when the user wants to analyze/audit/review a project, find bugs, or get
  improvement suggestions. Triggers: "analyze", "audit", "code review", "security audit", "analizar",
  "revisar", "auditar", "que se puede mejorar", "repo audit".
compatibility: Language-agnostic, works with any project type. No external dependencies. May write its own reports/audit JSON for baseline/delta.
---

# Project Analyzer

Read-only skill: examine a codebase, produce structured report with severity levels. **Never modify the
audited code.** It may only write its own outputs under `reports/` (audit JSON for baseline/delta).

## Scope control
- Exclude by default: `.git/`, `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/`, `.next/`, caches, lockfiles, and generated binaries.
- Cap the file set read (e.g. ~200 files / ~1MB of code) and sample representative files instead of reading everything.
- Ask **one optional scoping question** up front: "Audit everything, or focus on X (e.g. auth, build, a module)?" Then run without further prompts.

## Severity levels

- `[CRITICAL]` — Will cause failures, data loss, or security breaches. Must fix.
- `[MAJOR]` — Significant quality or reliability issue. Should fix.
- `[MINOR]` — Minor concern. Nice to fix.
- `[SUGGESTION]` — Optional improvement.

## Pillars

The audit can run either as a full pass or a single named pillar. A pillar is one focused
lens. When the request is unscoped, ask once "all seven pillars, or one?" before running;
never silently default to one pillar, never blind-run all without offering the choice.

| #   | Pillar          | Lens                                                                 |
| --- | --------------- | -------------------------------------------------------------------- |
| 01  | `code-quality`  | Clean code (naming, SOLID, DRY, readability, smells), tech debt (dead code, complexity, file/function size, error handling) |
| 02  | `architecture`  | Conformance to ADRs, coupling, boundaries, layering                   |
| 03  | `security`      | OWASP risks, authz, input validation, secrets in code                 |
| 04  | `dependencies`  | CVEs, licenses, outdated and unused deps, supply chain                |
| 05  | `performance`   | N+1 queries, hot paths, bundle size, heavy operations                 |
| 06  | `tests`         | Critical-path coverage, flakiness, test pyramid balance               |
| 07  | `ui`            | Loading/error/empty states, responsive, a11y                          |

An unscannable pillar is skipped and recorded under the report's coverage, never invented.

## Prioritization
Order recommendations by `severity x probability x effort`: fix high-severity, likely, low-effort items
first; flag high-severity-but-unlikely items for verification rather than ignoring them.

## Workflow

**1. Understand project** — Read identity files: `README.md`, `package.json`/`pyproject.toml`, `Dockerfile`, `.gitignore`, `AGENTS.md`. Establish purpose, stack, architecture.

**2. Map structure** — Use glob + directory listing (excluding the scope-control list above). Assess logical organization, naming conventions, separation of concerns.

**3. Sample code** — Read entry points, core logic, recently modified files, unusually large files. Check SRP, error handling, edge cases, dead code.

**4. Check dependencies** — Review `requirements.txt`/`package.json` etc. Check for outdated packages, excessive deps, loose pinning, unused imports, CVEs.

**5. Security scan** — Grep for: hardcoded secrets (`password=`, `api_key=`, `-----BEGIN`), injection risks (`shell=True`, `eval()`, SQL concat), unsafe deserialization (`pickle.loads`, `yaml.load`), insecure defaults (CORS `*`, debug mode). Verify findings by reading context.
- **Triage rules (reduce false positives):** `password=`/`api_key=` shallow matches are usually examples/tests/docs/templates — batch through them, and only escalate a match that (a) is inside real source, not `tests/`, `docs/`, `fixtures/`, or `*.example.*`, (b) contains an actual non-placeholder value (not `XXX`, `your-`, `demo`, `example`), and (c) is referenced by live code. When in doubt, search for the variable name vs. value to confirm it's real.
- Do not report every raw grep hit; aggregate by file+pattern and verify the plausible ones by reading ~context lines.

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
## Recommendations  (top 3-5 actionable, ordered by severity x probability x effort, each with a rough time estimate)
```

Skip empty sections with "No significant issues found." Don't force every section if nothing notable.

## Apply fixes mode

When the caller asks to fix the findings (e.g. `init_review` hands off a scope), the skill
moves from read-only diagnosis to guided repair. It receives the findings list from the
scan and applies the chosen scope. The caller (command) decides which scope, but this
mode defines how fixes are executed:

- **Scope mapping** — the fix scope selects findings by severity/area:
  - `Aplicar todo`: all findings (CRITICAL + MAJOR + MINOR + SUGGESTION).
  - `Solo lo crítico`: only CRITICAL findings.
  - `Solo estructura`: only F4 / structure / file-hygiene findings.
  - `Solo código`: only F2 (blockers) + F3 (pending work) findings.
  - `No hacer nada`: no changes.
- **Surgical, one finding at a time** — apply each selected finding with its `file:line`,
  severity, issue, and suggested fix. Never fix silently; each fix maps to a finding.
- **Skip with reason** — a finding that proves to be a false positive, or whose fix would
  introduce risk, is skipped and reported with the reason. Do not force a fix that would
  harm the project.
- **Confirm destructive behaviors** — a fix that deletes files, moves structure, changes
  behavior, or touches production asks for confirmation first.
- **Verify** — after applying the scope, run the project's tests/lint/build to confirm the
  fixes don't break anything. Report fixed vs. skipped vs. blocked.
- **Read-only concern** — this is the ONLY mode that edits target code, and only for the
  findings explicitly in scope. Everything else in this skill stays read-only.

## Baseline / delta (re-runs)
- Write a structured copy of the findings to `reports/audit-<iso>.json` (finding id, severity, file, status) alongside the human report.
- On a re-run, load the previous `reports/audit-*.json` and diff by finding id to report **newly fixed** (present before, absent now) and **newly introduced** (absent before, present now). Present the delta in the report header.
- Never modify the target code to achieve a "fixed" status — only report what exists at scan time.

## Guidelines

- **Be specific**: cite files and line ranges (`src/handlers/auth.ts:45-52`)
- **Explain impact**: "user sees blank page" not "error not handled"
- **Acknowledge positives**: praise good CI, tests, architecture
- **Fit maturity**: small script ≠ production service rigor
- **Read broadly, cite precisely**
- **Say when unsure**: "tests may not exist yet"
- **Estimate effort in minutes** per recommendation (~5 min, ~1 h) so the fix scope can be sized at a glance

## Keywords
"analyze", "audit", "code review", "code quality", "security review", "security audit", "project health", "analizar", "revisar", "auditar", "que se puede mejorar", "encontrar bugs", "problemas de seguridad", "codebase analysis", "project report", "technical debt", "code smells", "architecture review", "repo audit", "代码审查", "project overview"
