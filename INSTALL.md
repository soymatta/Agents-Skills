# INSTALL.md — one-shot installer for AI agents

Read this file first. It is the only file you need to install this repo.
Do not scan `skills/`, `agents/`, or `plugins/` contents unless you are debugging
an install failure.

## What this repo ships

- 4 agents, 26 skills, 2 plugins (opencode-only), 2 slash commands.
- Authoritative inventory: `python setup.py --manifest` (JSON, no interaction).
- Installer: `setup.py` copies items + resolves dependencies, then outputs the
  destination of every file. No manual copying.

## Install everything (recommended)

Non-interactive, installs all items, resolves dependencies:

```bash
python -m pip install -r skills/requirements.txt
python setup.py --all --global --platform opencode
```

Flags:
- `--all` install every agent, skill, and plugin
- `--global` install to `~/.config/opencode/`
- `--platform opencode` target assistant (claude | cursor | windsurf | opencode)

Variants:
- omit `--global` for a project-local install (`.opencode/` in the cwd)
- `--platform claude` for Claude Code, etc.

## Verify

```bash
python setup.py --manifest   # shows the inventory (id, type, dependencies)
```

Installed layout (global opencode):

```
~/.config/opencode/agent/<name>.md      # agents (builder, vault, ...)
~/.config/opencode/skills/<name>/       # skills (each with SKILL.md)
~/.config/opencode/plugins/<id>.ts      # plugins
~/.config/opencode/commands/<cmd>.md    # slash commands
```

## Scope

- `AGENTS.md`, this file, and `README.md` now carry behavior + install rules.
- `setup.py` is the single source of truth for what installs where.
- Third-party skills are pulled from upstream; do not modify their contents.