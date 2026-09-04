---
name: code-review
description: >-
  Reviews a diff read-only on three axes (code quality, feature behavior vs. plan, and relevancy)
  into one verdict report. Use before shipping a change to catch issues. READ-ONLY: surfaces each
  finding with its fix described, never patches. Not for auditing a whole codebase (use
  project-analyzer) or for fixing findings. Triggers: "review", "revisar", "review this diff",
  "code review", "revisar cambios".
compatibility: Language-agnostic. Read-only on target code. May write its report to disk.
---

# Code Review

Review a diff read-only on three axes, composed into one verdict report. Use before shipping
a change.

## Actions

| #   | Axis               | What it judges                                             |
| --- | ------------------ | ---------------------------------------------------------- |
| 01  | `code-quality`     | Clean-code quality on the changed lines (naming, DRY, smells, dead code) |
| 02  | `functional`       | The diff against the plan's phases and their acceptance criteria |
| 03  | `relevancy`        | Does the change belong: fit to the need, rule conformance, no rot |

Run all three by default, composing one report. Run a single axis only when the caller names
it; if it is unclear whether they want all or one, ask.

## Transversal rules

- **Read-only**: surface each finding with its fix described, never patch. Do not edit the
  reviewed code.
- **Severity**: use the shared 3-4 level scale (`CRITICAL` / `MAJOR` / `MINOR` / `SUGGESTION`)
  consistent with `project-analyzer`.
- **Verdict**: one overall verdict, the strictest across the axes run. When all green, say so
  plainly; never inflate to force a pass, never invent issues to look thorough.
- **Tie to the plan**: when a plan is in scope, each finding's `Phase` column ties it to the
  plan. When no plan is in scope, leave it `-`.
- **Not run**: an axis that did not run marks its sections "Not run"; it never leaves a
  placeholder or invents data. Skipping an axis is visible in the header.
- **Acceptance criteria**: judge the diff against the user's stated intent / acceptance
  criteria. An unmet criterion is a `fix`-tagged finding, not a suggestion.

## Report structure

```
## Verdict
<one overall verdict: ship | iterate | rework, strictest across axes>

## Axes run
<which of the three axes ran>

## Findings
| Severity | Kind | Phase | Location | Issue | Suggested fix |
| CRITICAL | functional | <phase or -> | file:line | ... | ... |

## Passed
<what the diff does correctly — acknowledge good work>

## Recommendations
<top 3-5 actionable, ordered by severity x probability x effort>
```

## Guidelines

- **Be specific**: cite exact `file:line` ranges on changed lines.
- **Explain impact**: "user sees blank page" not "error not handled".
- **Acknowledge positives**: praise good structure that matches conventions.
- **Say when unsure**: "coverage not confirmed, tests may not exist yet".
- **Fit maturity**: a small script does not get production-service rigor.

## Handoff

The report is the deliverable another agent (e.g. `builder`) can act on. Keep it tight and
token-optimized so a fix can be applied directly from the Findings table.

## Keywords
"review", "code review", "revisar", "review diff", "revisar cambios", "verdict", "ship or iterate", "code review report"
