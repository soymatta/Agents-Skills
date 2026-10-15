---
name: commit
description: >-
  Creates git commits in this repository's house convention: a capitalized
  conventional type plus a short English explanation, formatted
  `{Type}: {explanation}`. Ships a commit-msg validator and wires it into a husky
  hook (native git hook fallback). Use whenever the user wants to commit,
  stage-and-save, record progress, or when a task finishes and the work should be
  captured in history. Triggers: "commit", "comitear", "make a commit",
  "commit this", "guardar cambios", "stage and commit", "save my work",
  "conventional commit", "commit message", "confirmar cambios". NOT for branching,
  pull requests, or releases (use git-workflow).
compatibility: Requires git. The husky hook needs Node/npm; without Node the skill installs a native .git/hooks/commit-msg that runs the same validator.
---

# Commit

## Why one convention

The repo history is mixed: lowercase types (`feat:`, `docs:`), some subjects in
Spanish, some untagged. That makes `git log` hard to skim and impossible to
machine-check. This skill pins one shape going forward so every commit is
scannable by a human and verifiable by a hook.

## Message format

```
{Type}: {explanation}
```

- **{Type}** — exactly one of, capitalized: `Fix`, `Feature`, `Docs`, `Refactor`,
  `Test`, `Chore`, `Perf`, `Build`, `CI`, `Style`, `Revert`.
- **{explanation}** — a short, specific phrase describing the change. Always in
  **English**, even when the conversation is Spanish. No trailing period. Keep the
  whole subject line at or under 72 characters.
- **Body** (optional) — add one only when the *why* isn't obvious from the subject.
  Separate it from the subject with a blank line; the subject alone must stand on
  its own.

| Type      | Use for                                              | Replaces (lowercase) |
| --------- | ---------------------------------------------------- | -------------------- |
| `Feature` | New capability or behavior                           | `feat`               |
| `Fix`     | Bug fix                                              | `fix`                |
| `Docs`    | Documentation only                                   | `docs`               |
| `Refactor`| Internal change, no behavior change                  | `refactor`           |
| `Test`    | Tests only                                           | `test`               |
| `Chore`   | Maintenance, deps, housekeeping                      | `chore`              |
| `Perf`    | Performance improvement                              | `perf`               |
| `Build`   | Build system / tooling                               | `build`              |
| `CI`      | CI configuration                                     | `ci`                 |
| `Style`   | Formatting, whitespace, no logic change              | `style`              |
| `Revert`  | Revert a previous commit                             | `revert`             |

Examples:

```
Feature: add deterministic init_review scanner
Fix: prevent crash when the config file is missing
Docs: document the queue subcommands
Refactor: extract the shared HTML chunk splitter
```

## Language

English, always — the explanation is not translated. A Spanish conversation still
produces an English subject, so the log stays uniform for anyone reading the repo.

## Author

Commit as the repository owner (`@soymatta`). Do **not** add agent/AI attribution
trailers (`Co-authored-by: opencode`, "Generated with…"); the commit is the user's.

## Workflow

1. **Triage** — state the size and what will be committed.
2. **Inspect** — `git status`, `git diff`, `git log --oneline -5`. Check the recent
   subjects for tone when you add a body.
3. **Stage** — only the intended files (`git add <paths>` or `git add -p`). Never
   blind `git add -A`; never stage secrets.
4. **Compose** — `{Type}: {explanation}` in English, ≤72 chars, no trailing period.
5. **Validate + commit** — run the validator (or let the hook do it), then
   `git commit -m "..."`.
6. **Report** — the subject line and the exact next git action. Push only when asked.

If a hook rejects the commit, read its output, fix the message, and commit again.
Never `--no-verify`, never amend a failed commit — the hook is the point.

## Validator

`scripts/validate_commit_msg.py` is a deterministic check (no LLM). Use it before
committing or let the hook call it:

```bash
python scripts/validate_commit_msg.py --message "Fix: correct login timeout"
python scripts/validate_commit_msg.py .git/COMMIT_EDITMSG   # what the hook calls
```

It exits 0 when valid, 1 with a one-line reason when not. It accepts git-generated
`Merge …` and `Revert "…"` subjects so merges never break.

## Hook setup (husky, with a native fallback)

Wire the validator so every commit is checked automatically. Pick the path that
fits the project:

- **Node project (has `package.json`)** — use husky:
  ```bash
  npm pkg set scripts.prepare="husky"
  npx husky init
  python scripts/validate_commit_msg.py --install --husky
  ```
  The `--install` writes `.husky/commit-msg` pointing at this validator. Commit the
  `.husky/` dir so the team gets it.

- **Otherwise (pure Python / no Node)** — native hook:
  ```bash
  python scripts/validate_commit_msg.py --install
  ```
  That writes `.git/hooks/commit-msg` (executable) wired to this validator. It's
  local to the clone; to share it, copy the file into the repo and document it.

## Safety

- Never commit secrets. If `.env` is involved, verify `.gitignore` covers it first.
- **Do not commit unless the user asks.** Commits are explicit, never assumed.
- Never `--force` push; never `--no-verify`.
- A hook that rejects the commit is working as intended — fix the message.

## When NOT to use

Branching, pull requests, and releases/tags are `git-workflow`'s job. This skill is
only the commit (message convention + the commit act + the hook).

## Keywords

"commit", "comitear", "make a commit", "commit this", "guardar cambios",
"stage and commit", "save my work", "conventional commit", "commit message",
"confirmar cambios", "git commit"
