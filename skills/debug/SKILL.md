---
name: debug
description: >-
  Reproduces and fixes a known bug, or finds an unknown root cause by hypothesis validation,
  with a test-driven fix. Use when the user wants to fix a bug, find why something breaks, or
  reopen a stuck investigation. NOT for building a feature or reviewing a diff. Triggers:
  "debug", "depurar", "bug", "broken", "no funciona", "da error", "arreglar", "por que falla", "stuck".
compatibility: Language-agnostic. Edits target code. Regressions get a test.
---

# Debug

Diagnose and fix issues through structured hypothesis validation, root-cause analysis, and a
test-driven fix.

## Actions

| #   | Action          | When to use                                                  |
| --- | --------------- | ------------------------------------------------------------ |
| 01  | `reproduce`     | A known bug must be fixed end to end: reproduce, test-driven fix, branch, PR |
| 02  | `debug`         | Root cause unknown: enumerate hypotheses, validate each, confirm the cause |
| 03  | `reflect-issue` | Stuck or prior fixes failed: reopen the search space, instrument logs first |

Pick the one action matching the intent; never default to `01`. Triggers like "reproduce and
fix" route to `01`, "why does this happen" to `02`, "I'm stuck" or "previous fixes didn't
work" to `03`. Ask one question when the intent is ambiguous.

## Transversal rules

- **One action per run**: follow only the matching action.
- **Confirm the root cause before fixing**: the diagnostic actions stop at a confirmed
  cause; a fix on an unconfirmed cause is guessing.
- **Scope each fix to its bug**: never bundle drive-by refactors.
- **Evidence**: reproduce the bug first (the repro is the reference for "fixed"). A fix is
  done only when the repro no longer reproduces.
- **Regression test**: every bug fix ships the regression test that would have caught the
  bug. Verify the test fails with the bug present and passes with the fix.
- **Direct on failure**: name the failing `file:line` and the exact error, then the path to
  the fix. Matter-of-fact, no "uh oh", no apology tour.
- **Severity** uses the project's shared scale.

## Workflow

1. **Triage** — print size and the action chosen. Reproduce or enumerate hypotheses before
   touching code.
2. **Reproduce / hypothesize** — get a deterministic repro, or enumerate 2-3 hypotheses and
   validate the cheapest first. Stop at a confirmed cause.
3. **Fix** — apply the smallest fix that closes the cause at the root, not the symptom.
4. **Verify** — run the repro again (gone), run the regression test (fails pre-fix, passes
   post-fix), run the touched module's existing tests.
5. **Report** — numbered, in this order: (1) root cause in one line, (2) the fix
   (`file:line`), (3) verification evidence, (4) the regression test added. Close with the
   next action: nothing pending, or "watch X".

## Stuck investigation (reflect-issue)

If the fix failed or the search stalled: instrument logging first, reopen the search space,
and re-derive hypotheses from the new evidence instead of retrying the same approach a third
time. Report what changed.

## Keywords
"debug", "bug", "broken", "no funciona", "da error", "arreglar", "por que falla", "root cause", "fix", "reproducir", "atascado"
