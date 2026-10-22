# INSTALL.md — one-shot installer for AI agents

Read this file first. It is the only file you need to install this repo.
Do not scan `skills/`, `agents/`, or `plugins/` contents unless you are debugging
an install failure.

## What this repo ships

- 6 agents, 29 skills, 3 plugins (opencode-only), 27 slash commands
  (23 of them generated from the impeccable metadata table).
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
- `--only <id> [<id> ...]` install just those items and touch nothing else
  (never removes unrelated items)
- `--check` verify an installed config against the manifest, write nothing,
  exit 1 on drift (needs `--platform` plus `--global` or `--local`)

Installing without the plugins (agents + skills + commands only): pass every
non-plugin id to `--only` (the flag installs nor removes nothing else). The list
comes from `python setup.py --manifest` — every item whose `type` is not
`plugin`.

Variants:
- omit `--global` for a project-local install (`.opencode/` in the cwd)
- `--platform claude` for Claude Code, etc.

## Verify

```bash
python setup.py --manifest   # shows the inventory (id, type, dependencies)
python setup.py --check --global --platform opencode   # exit 1 if the install drifted
```

`--check` compares every installed item (and every generated command) byte by
byte against the repo and lists what is missing, stale, or extra. Plugins that
are not installed are reported as notes, not as drift.

Installed layout (global opencode):

```
~/.config/opencode/agent/<name>.md      # agents (builder, vault, ...)
~/.config/opencode/skills/<name>/       # skills (each with SKILL.md)
~/.config/opencode/plugins/<id>.ts      # plugins
~/.config/opencode/plugins/<id>/        # plugin runtime assets (non-.ts files)
~/.config/opencode/commands/<cmd>.md    # slash commands
```

Commands come from an item's `commands/` directory, or are generated at install
time from a vendor metadata table (`impeccable` ships
`scripts/command-metadata.json`, 23 sub-commands, installed as
`impeccable-<command>.md`). `python setup.py --manifest` lists both.

## Scope

- `AGENTS.md`, this file, and `README.md` now carry behavior + install rules.
- `setup.py` is the single source of truth for what installs where.
- Third-party skills are pulled from upstream; do not modify their contents.