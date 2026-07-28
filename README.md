# Agents-Skills

Personal collection of AI agents and skills for AI coding assistants (OpenCode, Claude Code, Cursor, Windsurf). Each agent/skill defines procedures, permissions, and constraints for the AI to follow.

## Quick Install

```bash
git clone https://github.com/soymatta/Agents-Skills.git
cd Agents-Skills
pip install -r skills/requirements.txt
python setup.py
```

The interactive installer lets you toggle which agents/skills to install, resolves dependencies automatically, and copies them to your AI assistant's config directory.

## Repository Structure

```
Agents-Skills/
  setup.py               # Interactive installer (TUI menu)
  README.md              # This file
  agents/                # Agent definitions (YAML frontmatter + markdown)
    vault-indexer.md
    vault-researcher.md
    paper-researcher.md
    vault-search.md
    vault-organizer.md
    roadmaps.md
    jobfinder.md
    metric-optimizer.md
  skills/                # Skill definitions + infrastructure
    requirements.txt     # Python dependencies
    pyproject.toml       # Project config + pytest settings
    academic-source-search/
    backtest-run/
    backtest-validate/   # + tests/
    citation-formatter/
    content-humanizer/   # + tests/
    math-notation/
    osint/               # + tests/
    research-pipeline/
    skill-creator/       # + tests/
    project-analyzer/    # + commands/ (init_review.md)
    telegram-notify/
    goal-pursuit/        # + tests/
    metric-optimizer/    # templates only (agent uses them)
    roadmaps/            # scripts + templates only (agent uses them)
    jobfinder/           # scripts + templates only (agent uses them)
```

## Agents

| Agent | Description | Permissions |
|-------|-------------|-------------|
| `vault-indexer` | Reads/indexes all .md notes in the vault. Answers exclusively from file contents. | read, glob, grep, task |
| `vault-researcher` | Sub-agent of vault-indexer. Investigates external sources to verify unclear concepts. | read, glob, grep, webfetch, task |
| `paper-researcher` | Produce trabajos academicos rigurosos en Markdown (APA/IEEE/Vancouver). | bash, read, glob, grep, webfetch, task, edit |
| `vault-search` | Busca topics dentro del vault usando glob y grep. Complemento al vault-indexer. | read, glob, grep, task |
| `vault-organizer` | Analiza la estructura del vault y sugiere donde colocar informacion nueva. | read, glob, grep, task |
| `roadmaps` | Crea, actualiza y sigue roadmaps adaptativos para cualquier proyecto. | bash, read, glob, grep, task, edit |
| `jobfinder` | Analiza perfil profesional, busca empleos, calcula match scores y genera reportes. | bash, read, glob, grep, webfetch, task, edit |
| `metric-optimizer` | Optimiza metricos numericos via loop autonomo de mejoras iterativas. | bash, read, glob, grep, task, edit |

## Skills

> **Third-party skills** are marked with *(Third-party)*. Do not modify their contents — pull updates from the upstream source instead. Currently: `skill-creator` (Anthropic) and `impeccable` (pbakaus).

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| `research-pipeline` | Structured quantitative research process for prediction markets. | telegram-notify |
| `telegram-notify` | Full Telegram Bot API client with auto-retry and zero-dep fallback. | — |
| `backtest-run` | Runs backtests for trading strategies with slippage/fill modeling. | telegram-notify |
| `backtest-validate` | 5-dimension scoring framework for backtest quality (Deploy/Refine/Abandon). | backtest-run |
| `academic-source-search` | Busca fuentes cientificas en 14 bases de datos academicas con sistema de tiers. | — |
| `citation-formatter` | Referencia completa APA 7th, IEEE y Vancouver con implementacion CSS/DOCX. | — |
| `content-humanizer` | Pase final anti-deteccion IA con 9 tecnicas + script de verificacion local. | — |
| `math-notation` | Reglas de notacion matematica para el inline parser del generador. | citation-formatter |
| `skill-creator` | Meta-skill: crear, evaluar, comparar y optimizar otros skills. *(Third-party — Anthropic, Apache 2.0)* | — |
| `osint` | OSINT investigation framework con 7 guias de referencia y 4 scripts. | — |
| `goal-pursuit` | Autonomous optimization loop for numerical metrics via iterative improvement. | — |
| `impeccable` | Frontend design audit, polish, and redesign skill. *(Third-party — pbakaus, Apache 2.0)* | — |
| `project-analyzer` | Read-only project analysis: structure, code quality, bugs, security, performance, and dependency health. | — |

## Dependency Graph

```
vault-indexer (agent)
  +-- vault-researcher (sub-agent)
  +-- vault-search (agent)
  +-- vault-organizer (agent)

paper-researcher (agent)
  +-- academic-source-search (skill)
  +-- citation-formatter (skill)
        +-- scripts/generate_outputs.py

telegram-notify (skill)
  +-- backtest-run (skill)
  |     +-- backtest-validate (skill)
  |     +-- scripts/cloud.py (remote execution)
  +-- research-pipeline (skill)

roadmaps (agent)
  +-- scripts/validate_roadmap.py
  +-- templates/ (web-app, ml-model, api-service, migration)

skill-creator (meta-skill, third-party — Anthropic)
  +-- analyzer, comparator, grader (sub-agents)
  +-- scripts/ (run_eval, run_loop, aggregate_benchmark, etc.)

jobfinder (agent)
  +-- scripts/ (7 scripts: scoring, scraping, CV, reports)
  +-- templates/ (profile.json, sample_cv.json)

goal-pursuit (skill)
  +-- templates/goal_state_template.json
  +-- tests/test_goal_state.py

osint (skill)
  +-- scripts/ (4 scripts) + references/ (7 guides)

impeccable (skill, third-party — pbakaus)
  +-- scripts/ (context, hooks)
  +-- reference/ (design playbooks)
```

## Requirements

- **Python >= 3.11**
- **pip install -r skills/requirements.txt** (installs all dependencies)
- Optional: `claude CLI` (for skill-creator eval/improve loop)

## Development

### Adding a new skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: Pushy description with trigger keywords.
   compatibility: Lists which skills depend on this one.
   ---
   ```
2. Add an entry in `setup.py` `ITEMS` list.
3. Add to the table in this README.
4. (Optional) Add `commands/` with custom OpenCode commands, referenced via `"commands": ["cmd.md"]` in the ITEMS entry.

### Adding a new agent

1. Create `agents/<name>.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-agent
   description: Agent description.
   mode: primary
   permissions:
     read: allow
     glob: allow
     grep: allow
   ---
   ```
2. Add an entry in `setup.py` `ITEMS` list.
3. Add to the table in this README.

### Running tests

```bash
# All tests
python -m pytest skills/ -v

# By skill
python -m pytest skills/backtest-validate/tests/ -v
python -m pytest skills/osint/tests/ -v
python -m pytest skills/content-humanizer/tests/ -v
python -m pytest skills/skill-creator/tests/ -v
python -m pytest skills/goal-pursuit/tests/ -v
python -m pytest skills/roadmaps/tests/ -v
python -m pytest skills/jobfinder/tests/ -v
```

### Third-party skills

- `skill-creator` — authored by **Anthropic, PBC** (Apache 2.0). Do not modify. To update, pull from the upstream source.
- `impeccable` — authored by **pbakaus** (Apache 2.0). Do not modify. To update, run `npx impeccable install --providers=opencode --scope=project --force`.
