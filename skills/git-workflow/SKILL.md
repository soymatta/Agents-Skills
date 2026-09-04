---
name: git-workflow
description: >-
  Version-control workflows: atomic conventional commits, branches, pull/merge requests, and
  release tags. Use when the user wants to commit, branch, open a PR, or cut a release. NOT for
  amending, rebasing, or destructive git ops. Triggers: "commit", "comitear", "git", "branch",
  "pull request", "release", "PR", "confirmar cambios".
compatibility: Works on any git repo. Calls git commands via the shell.
---

# Git Workflow

Standardized, safe version-control operations. One concern per commit, imperative messages,
and no destructive operations without explicit instruction.

## Actions

| #   | Action          | When to use                                               |
| --- | --------------- | --------------------------------------------------------- |
| 01  | `commit`        | Commit staged/selected changes with a conventional message |
| 02  | `branch`        | Create a branch for a task                                |
| 03  | `pull-request`  | Open a pull/merge request                                 |
| 04  | `release-tag`   | Cut a semver release with annotated tag and notes         |

## Conventional commit format

```
<type>(<scope>): <imperative summary>

<body: why, not what>

[Refs: #<issue>]
```

- **Types**: `feat` (feature), `fix` (bug fix), `refactor`, `docs`, `test`, `chore`, `perf`,
  `style`, `build`, `ci`.
- **Scope** (optional): the module/area, e.g. `feat(auth):`.
- **Imperative mood**: "add", "fix", "rename" — not "added", "fixing".
- **Body says why, not what.**
- **One concern per commit**: several concerns means several commits.

## Transversal rules

- **One concern per commit. Imperative mood. Body says why.**
- Reference the issue in the body when there is one.
- **Inspect before staging**: run `git status`, `git diff`, and `git log --oneline -10`
  first; stage only intended files; never commit secrets.
- **Never `--force` push. `--force-with-lease` only when explicitly asked.**
- **A hook that rejects the commit is not this skill's job**: report which hook and why,
  then stop. Re-stage only files a hook auto-formatted.
- **Do not commit unless the user asks.** Commits are explicit, never assumed.
- **Good messages match the repo style**: check previous commits for tone and structure.

## Safety

- Never commit secrets. If `.env` is involved, verify `.gitignore` first.
- Never run destructive ops (`rm -rf`, `git reset --hard`, force-push) without explicit
  explicit instruction.
- Branch names are kebab-case and describe the task, e.g. `fix/login-timeout`.

## Workflow

1. **Triage** — print size and the operation.
2. **Inspect** — `git status`, `git diff`; identify what belongs in this commit.
3. **Stage** — stage only intended files.
4. **Commit** — write the conventional message; push only when asked.
5. **Report** — the diff summary and the exact next git action.

## Keywords
"commit", "comitear", "git", "branch", "rama", "pull request", "PR", "release", "tag", "confirmar cambios"
