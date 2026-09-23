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

> **For AI agents:** don't scan the repo. Read `INSTALL.md`, run
> `python setup.py --manifest` for the inventory, then
> `python setup.py --all --global --platform opencode`.

## Usage

### Agents

Talk to these agents in natural language. They auto-detect intent and run the appropriate workflow.

| Agent | Example Prompts |
|-------|----------------|
| `vault` | "Find notes about Python", "Organize my vault by topic", "Create a daily note" |
| `paper-researcher` | "Write a research paper on X in APA", "Find academic sources for my thesis", "Review my paper's citations" |
| `jobfinder` | "Find remote Python developer jobs", "Score my CV against this posting", "Generate a cover letter for this role" |
| `builder` | "Implement this feature", "Refactor this module", "Run the tests and fix failures", "Create a roadmap for this project", "Alcanza este objetivo", "Improve this skill" |

### Skills

Skills are triggered automatically when the AI detects relevant keywords. Just describe what you need.

| Skill | Usage Example |
|-------|--------------|
| `telegram-notify` | "Notify me on Telegram when this completes" |
| `academic-source-search` | "Find papers about machine learning" |
| `citation-formatter` | "Format my citations in APA 7th" |
| `content-humanizer` | "Make this text undetectable by AI" |
| `osint` | "Run an OSINT investigation on this target" |
| `goal` | "Alcanza este objetivo", "Optimize this metric to 95% accuracy" |
| `roadmaps` | "Create a plan for this project" |
| `project-analyzer` | "Analyze this codebase for issues" |
| `qa-tester` | "Test this app", "Runs QA on the project", "Intenta romper la app" |
| `research-pipeline` | "Research this prediction market question" |
| `backtest-run` | "Backtest this trading strategy" |
| `backtest-validate` | "Validate this backtest quality" |
| `math-notation` | Auto-applied when writing math in academic docs |
| `agent-self-improver` | "Improve this agent's performance" |
| `skill-creator` | "Create a new skill from scratch" |
| `code-review` | "Review this diff" |
| `refactor` | "Refactor this module for performance" |
| `debug` | "Debug why this breaks" |
| `git-workflow` | "Commit these changes" |
| `project-memory` | "Set up project memory" |
| `impeccable` | `/init`, `/shape`, `/critique`, `/polish`, `/audit` |
| `ai-job-search` | `/setup`, `/apply`, `/scrape`, `/rank`, `/interview` |
| `jobfinder` | "Find jobs for this profile", "Score my CV against this posting", "Generate a cover letter" |

### Commands

Slash commands you can type directly in your AI assistant:

| Skill | Command | Description |
|-------|---------|-------------|
| `project-analyzer` | `/init_review [ruta]` | Onboarding + scan de salud de un proyecto (solo lectura) y correcciones guiadas |
| `impeccable` | `/init` | Capture product context in PRODUCT.md |
| | `/shape [feature]` | Plan UX/UI before writing code |
| | `/critique [target]` | UX design review with heuristic scoring |
| | `/audit [target]` | Technical quality checks (a11y, perf, responsive) |
| | `/polish [target]` | Final quality pass before shipping |
| | `/bolder [target]` | Amplify safe or bland designs |
| | `/harden [target]` | Production-ready: errors, i18n, edge cases |
| | `/animate [target]` | Add purposeful animations and motion |
| | `/layout [target]` | Fix spacing, rhythm, and visual hierarchy |
| | `/document` | Generate DESIGN.md from existing code |
| | `/live` | Visual variant mode in the browser |
| `ai-job-search` | `/setup` | Onboarding: fill in candidate profile |
| | `/apply <url>` | Full workflow: evaluate fit, draft CV + cover letter |
| | `/scrape` | Search multiple job portals with fit ratings |
| | `/rank` | Batch-score scraped jobs into ranked shortlist |
| | `/interview` | Stage-specific interview prep + mock interview |
| | `/upskill` | Skill gap analysis with learning plans |

### Plugins

Runtime plugins for OpenCode that act automatically on SDK events (no prompt
needed). OpenCode-only by design — they are not ported to other assistants.

| Plugin | What it does | Install |
|--------|--------------|---------|
| `opencode-telegram-answers` | Sends a Telegram notification when the AI finishes a task (`session.idle`) or requests a tool permission (`permission.asked`/`permission.updated`). Text-only, markdown→HTML, debounced. | `python setup.py` and toggle it, or `plugins/opencode-telegram-answers/install.ps1` |

> **Relation to `telegram-notify`:** the skill is an on-demand Telegram library
> (text, files, webhooks); the plugin is an automatic event listener. They are
> complementary — both use `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## Repository Structure

```
Agents-Skills/
  setup.py               # Interactive installer (TUI menu)
  README.md              # This file
  agents/                # Agent definitions (YAML frontmatter + markdown)
    vault.md             # Unified notes manager (Obsidian, OneNote, Notion)
    paper-researcher.md  # Academic paper writer
    jobfinder.md         # Job application assistant
    builder.md            # Build Mod — full-access dev agent (clone of opencode build)
  plugins/               # OpenCode runtime plugins (event listeners)
    opencode-telegram-answers/  # Telegram alerts on session.idle / permission.*
  skills/                # Skill definitions + scripts
    requirements.txt     # Python dependencies
    pyproject.toml       # Project config + pytest settings
    academic-source-search/
    ai-job-search/       # (Third-party — MadsLorentzen, MIT)
    backtest-run/
    backtest-validate/   # + tests/
    citation-formatter/
    content-humanizer/   # + tests/
    impeccable/          # (Third-party — pbakaus, Apache 2.0)
    jobfinder/           # scripts/ + templates/ + tests/
    math-notation/
    goal/
    osint/               # + tests/
    project-analyzer/
    code-review/
    debug/
    git-workflow/
    project-memory/
    refactor/
    research-pipeline/
    roadmaps/            # + tests/
    skill-creator/       # (Third-party — Anthropic, Apache 2.0) + tests/
    telegram-notify/
    agent-self-improver/ # + tests/
  web/                   # Astro landing page (documentation site; not installed by setup.py)
```

## Agents

| Agent | Description | Permissions |
|-------|-------------|-------------|
| `vault` | Unified notes manager for Obsidian, OneNote, Notion, and any markdown-based app. Index, search, organize, verify, create notes, health checks, broken links, and link suggestions — 8 workflows, bilingual EN/ES. | read, glob, grep, task, edit |
| `paper-researcher` | Produces rigorous academic papers in Markdown (APA/IEEE/Vancouver). Bilingual EN/ES. | bash, read, glob, grep, webfetch, task, edit |
| `jobfinder` | Analyzes professional profile, searches jobs across multiple boards, calculates 5D match scores, generates CVs/cover letters, and tracks applications. | bash, read, glob, grep, webfetch, task, edit |
| `builder` | Clone del agente opencode `build` (Build Mod): agente primario de trabajo con todas las herramientas. Integrado con auto-mejora, creación de skills, optimización de metas y roadmaps. Descubre e integra desde la web MCP, skills, plugins y comandos (bajo aprobación). Comunicación optimizada en tokens (breve entre agentes, completa con el usuario). Decisión-first estilo hermes-agent: resuelve opciones con evidencia (determinista → simulación → pregunta), sin interrogatorio. | all tools (allow), question, doom_loop (ask) |

## Skills

> **Third-party skills** are marked with *(Third-party)*. Do not modify their contents — pull updates from the upstream source instead.

| Skill | Description | Dependencies |
|-------|-------------|--------------|
| `telegram-notify` | Full Telegram Bot API client with auto-retry and zero-dep fallback. | — |
| `research-pipeline` | Structured quantitative research process for prediction markets. | telegram-notify |
| `backtest-run` | Runs backtests for trading strategies with slippage/fill modeling. | telegram-notify |
| `backtest-validate` | 5-dimension scoring framework for backtest quality (Deploy/Refine/Abandon). | backtest-run |
| `academic-source-search` | Search scientific sources across 14 academic databases with tier system. | — |
| `citation-formatter` | Complete APA 7th, IEEE and Vancouver referencing with CSS/DOCX output. | — |
| `math-notation` | Math notation rules for the inline parser of the generator. | citation-formatter |
| `content-humanizer` | Final anti-AI-detection pass with 9 techniques + local verification script. | — |
| `osint` | OSINT investigation framework with 7 reference guides and 5 scripts. | — |
| `goal` | Iterative loop that drives a flow until a measurable objective is reached (metrics, quality gates, targets). | — |
| `roadmaps` | Creates, updates, and follows adaptive roadmaps for any project. | — |
| `project-analyzer` | Read-only project analysis: structure, code quality, bugs, security, performance. | — |
| `agent-self-improver` | Self-improvement framework for agents with human supervision. | — |
| `code-review` | Reviews a diff read-only on three axes (code quality, feature behavior vs. plan, relevancy) into one verdict report. | — |
| `refactor` | Improves code across four axes (cleanup, performance, security, architecture) by scanning and fixing, or applying audit findings. Behavior-preserving except security. | — |
| `debug` | Reproduces and fixes a known bug, or finds an unknown root cause by hypothesis validation, with a test-driven fix and regression test. | — |
| `git-workflow` | Version-control workflows: atomic conventional commits, branches, pull/merge requests, release tags. | — |
| `project-memory` | Builds and maintains the project's durable memory of architecture, conventions, and decisions so every session starts grounded. | — |
| `skill-creator` | Meta-skill: create, evaluate, compare and optimize other skills. *(Third-party — Anthropic, Apache 2.0)* | — |
| `impeccable` | Frontend design audit, polish, and redesign skill. *(Third-party — pbakaus, Apache 2.0)* | — |
| `ai-job-search` | AI job application framework: 5D fit evaluation, CV tailoring, cover letters. *(Third-party — MadsLorentzen, MIT)* | — |

## Commands

Slash commands you can type directly in your AI assistant:

### impeccable (23 commands)

| Command | Description |
|---------|-------------|
| `/init` | Capture product context in PRODUCT.md |
| `/shape [feature]` | Plan UX/UI before writing code |
| `/critique [target]` | UX design review with heuristic scoring |
| `/audit [target]` | Technical quality checks (a11y, perf, responsive) |
| `/polish [target]` | Final quality pass before shipping |
| `/bolder [target]` | Amplify safe or bland designs |
| `/quieter [target]` | Tone down aggressive designs |
| `/distill [target]` | Strip to essence, remove complexity |
| `/harden [target]` | Production-ready: errors, i18n, edge cases |
| `/onboard [target]` | Design first-run flows, empty states |
| `/animate [target]` | Add purposeful animations and motion |
| `/colorize [target]` | Add strategic color to monochromatic UIs |
| `/typeset [target]` | Improve typography hierarchy and fonts |
| `/layout [target]` | Fix spacing, rhythm, and visual hierarchy |
| `/delight [target]` | Add personality and memorable touches |
| `/clarify [target]` | Improve UX copy, labels, and error messages |
| `/adapt [target]` | Adapt for different devices and screen sizes |
| `/optimize [target]` | Diagnose and fix UI performance |
| `/document` | Generate DESIGN.md from existing code |
| `/extract [target]` | Pull reusable tokens and components |
| `/live` | Visual variant mode in the browser |

### ai-job-search (8 commands)

| Command | Description |
|---------|-------------|
| `/setup` | Onboarding: fill in candidate profile |
| `/apply <url>` | Full workflow: evaluate fit, draft CV + cover letter |
| `/scrape` | Search multiple job portals with fit ratings |
| `/rank` | Batch-score scraped jobs into ranked shortlist |
| `/interview` | Stage-specific interview prep + mock interview |
| `/outcome` | Record application results, track follow-ups |
| `/upskill` | Skill gap analysis with learning plans |
| `/expand` | Enrich profile from public sources |

## Dependency Graph

```
vault (agent)
  8 workflows: Auto-Index, Search, Organize, Verify, Create, Health, Link, Clean

paper-researcher (agent)
  +-- academic-source-search (skill)
  +-- citation-formatter (skill)
        +-- scripts/generate_outputs.py

jobfinder (agent)
  +-- scripts/ (10 scripts: scoring, scraping, CV/cover-letter, reports, tracking)

builder (agent, Build Mod)
  +-- agent-self-improver (skill)  # feedback collection + pattern detection
  +-- skill-creator (skill)        # create/improve/benchmark skills
  +-- goal (skill)                # autonomous loop until an objective is reached
  +-- roadmaps (skill)             # multi-step task tracking (goal + steps)

telegram-notify (skill)
  +-- backtest-run (skill)
  |     +-- backtest-validate (skill)
  |     +-- scripts/cloud.py (remote execution)
  +-- research-pipeline (skill)

skill-creator (meta-skill, third-party — Anthropic)
  +-- scripts/ (run_eval, run_loop, aggregate_benchmark, etc.)

impeccable (skill, third-party — pbakaus)
  +-- scripts/ (context, hooks)
  +-- reference/ (design playbooks)

ai-job-search (skill, third-party — MadsLorentzen)
  +-- reference/ (9 docs)
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
4. (Optional) Add `scripts/` with CLI tools.

### Adding a new agent

1. Create `agents/<name>.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-agent
   description: Agent description.
   mode: primary
   permission:
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
python -m pytest skills/roadmaps/tests/ -v
python -m pytest skills/jobfinder/tests/ -v
python -m pytest skills/ai-job-search/tests/ -v
python -m pytest skills/agent-self-improver/tests/ -v
```

### Third-party skills

- `skill-creator` — authored by **Anthropic, PBC** (Apache 2.0). Do not modify. To update, pull from the upstream source.
- `impeccable` — authored by **pbakaus** (Apache 2.0). Do not modify. To update, run `npx impeccable install --providers=opencode --scope=project --force`.
- `ai-job-search` — authored by **MadsLorentzen** (MIT). Do not modify. To update, pull from the upstream source.
