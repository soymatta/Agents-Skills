---
name: git-workflow
description: >-
  Version-control workflows for branches, pull/merge requests, and release tags. Commits are
  owned by the `commit` skill (house format `{Type}: {explanation}` with its validator and
  hook); this skill does not restate that format. Use when the user wants to branch, open a PR,
  or cut a release. NOT for creating commit messages (use commit), amending, rebasing, or destructive git ops.
  Triggers: "branch", "rama", "git", "pull request", "merge request", "PR", "release", "tag".
compatibility: Works on any git repo. Calls git commands via the shell.
---

# Git Workflow

Standardized, safe version-control operations: branches, pull/merge requests and releases.
One concern per operation, and no destructive operation without explicit instruction.

## Actions

Commits are not one of them: the `commit` skill owns the commit step (house
format `{Type}: {explanation}`, plus its validator and hook). One owner per step.

| #   | Action          | When to use                                               |
| --- | --------------- | --------------------------------------------------------- |
| 01  | `branch`        | Create a branch for a task                                |
| 02  | `pull-request`  | Open a pull/merge request                                 |
| 03  | `release-tag`   | Cut a semver release with annotated tag and notes         |

## Commit messages

Owned by the `commit` skill: `{Type}: {explanation}` (capitalized conventional type, short
English explanation). Do not restate that format here and do not write a `git commit -m`
yourself when that skill is available: its validator and hook reject anything else.

What stays true for commits touched while branching or releasing: **one concern per commit**,
**imperative mood**, **body says why, not what**, never commit secrets.

## Transversal rules

- **Inspect before staging**: run `git status`, `git diff`, and `git log --oneline -10`
  first; stage only intended files.
- **Never `--force` push. `--force-with-lease` only when explicitly asked.**
- **Do not commit unless the user asks.** Commits are explicit, never assumed.
- **A hook that rejects a commit**: report which hook and why, then stop. Re-stage only files
  a hook auto-formatted.

## Safety

- Never commit secrets. If `.env` is involved, verify `.gitignore` first.
- Never run destructive ops (`rm -rf`, `git reset --hard`, force-push) without explicit
  instruction.
- Branch names are kebab-case and describe the task, e.g. `fix/login-timeout`.

## Workflow

1. **Triage** — print size and the operation.
2. **Inspect** — `git status`, `git diff`, `git log --oneline -10`; identify what is staged and
   what belongs where.
3. **Execute** — run the requested operation (`branch`, `pull-request`, `release-tag`). When
   the answer needs a commit, hand it to the `commit` skill instead of writing the message
   here; push only when asked.
4. **Report** — what changed in the repo state and the exact next git action.
