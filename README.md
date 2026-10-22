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
| `reverse-engineer` | "Reverse engineer this APK", "Analyze this binary", "Como funciona esta app", "Decompile this Electron app" |
| `fitness-coach` | "¿Sentadilla o prensa para cuádriceps?", "Is training to failure necessary?", "How many sets per muscle per week?", "Periodiza mi rutina" |

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
| `qa-tester` | "Test this app", "Runs QA on the project", "Intenta romper la app", "Usa codegen para escafaldar specs" |
| `research-pipeline` | "Research this prediction market question" |
| `backtest-run` | "Backtest this trading strategy" |
| `backtest-validate` | "Validate this backtest quality" |
| `math-notation` | Auto-applied when writing math in academic docs |
| `agent-self-improver` | "Improve this agent's performance" |
| `skill-creator` | "Create a new skill from scratch" |
| `code-review` | "Review this diff" |
| `refactor` | "Refactor this module for performance", "Pasa el checklist web launch" |
| `debug` | "Debug why this breaks" |
| `git-workflow` | "Commit these changes" |
| `commit` | "Commit this", "Guardar cambios", "Make a commit" |
| `project-memory` | "Set up project memory" |
| `impeccable` | `/impeccable-init`, `/impeccable-shape`, `/impeccable-critique`, `/impeccable-polish`, `/impeccable-audit` |
| `ai-job-search` | Upstream Claude-Code commands, **not installed by `setup.py`**: `/setup`, `/apply`, `/scrape`, `/rank`, `/interview` |
| `web-cloner` | "Clone this landing page", "Descarga esta web a HTML estático", "Replica este sitio en Astro" |
| `jobfinder` | "Find jobs for this profile", "Score my CV against this posting", "Generate a cover letter" |
| `ui-ux-pro-max` | "Build a landing page for my SaaS", "Design a dashboard", "Mejora el diseño de mi app" |
| `web-esenciales` | "Mejora mi web", "Que le falta a mi pagina", "Revisa mi landing antes de publicar" |
| `web-design-guidelines` | "Review my UI", "Check accessibility", "Audit design", "Revisa mi interfaz contra las guias de Vercel" |
| `ui-ux-orchestrator` | "Haz mi web", "Mejora el diseno", "Que skills de UI aplico", "Prepara mi sitio para publicar" |

### Commands

Slash commands you can type directly in your AI assistant:

| Skill | Command | Description |
|-------|---------|-------------|
| `project-analyzer` | `/init-review [ruta]` | Onboarding + scan de salud de un proyecto (solo lectura) y correcciones guiadas |
| `ui-ux-orchestrator` | `/init-ui-ux [ruta]` | Inicializacion y orquestacion frontend (fase seed/craft, playbooks UI, verificacion) |
| `impeccable` | `/impeccable-init` | Capture product context in PRODUCT.md |
| | `/impeccable-shape [feature]` | Plan UX/UI before writing code |
| | `/impeccable-critique [target]` | UX design review with heuristic scoring |
| | `/impeccable-audit [target]` | Technical quality checks (a11y, perf, responsive) |
| | `/impeccable-polish [target]` | Final quality pass before shipping |
| | `/impeccable-bolder [target]` | Amplify safe or bland designs |
| | `/impeccable-harden [target]` | Production-ready: errors, i18n, edge cases |
| | `/impeccable-animate [target]` | Add purposeful animations and motion |
| | `/impeccable-layout [target]` | Fix spacing, rhythm, and visual hierarchy |
| | `/impeccable-document` | Generate DESIGN.md from existing code |
| | `/impeccable-live` | Visual variant mode in the browser |
| `ai-job-search` | `/setup` | Onboarding: fill in candidate profile |
| | `/apply <url>` | Full workflow: evaluate fit, draft CV + cover letter |
| | `/scrape` | Search multiple job portals with fit ratings |
| | `/rank` | Batch-score scraped jobs into ranked shortlist |
| | `/interview` | Stage-specific interview prep + mock interview |
| | `/upskill` | Skill gap analysis with learning plans |

> **`ai-job-search` is a third-party skill that ships no `commands/` directory.** The
> commands above (`/setup`, `/apply`, `/scrape`, `/rank`, `/interview`, `/upskill`,
> `/outcome`, `/expand`) are upstream Claude-Code commands and are **NOT installed by
> `setup.py`** — they do not exist as slash commands here. Use the first-party `jobfinder`
> skill/agent for the installed workflow.

### Plugins

Runtime plugins for OpenCode that act automatically on SDK events (no prompt
needed). OpenCode-only by design — they are not ported to other assistants.

| Plugin | What it does | Install |
|--------|--------------|---------|
| `opencode-telegram-answers` | Sends a Telegram notification when the AI finishes a task (`session.idle`) or requests a tool permission (`permission.asked`/`permission.updated`). Text-only, markdown→HTML, debounced. | `python setup.py` and toggle it, or `plugins/opencode-telegram-answers/install.ps1` (both install `opencode-telegram-answers.ts`) |
| `opencode-tui-queue` | Queues everything typed while the session is busy and sends it one message per idle turn (`/queue list|front|now|stop|start|flush`). | `python setup.py` and toggle it |
| `opencode-auto-session` | On a usage-limit failure (`session.execution.failed` / `session.retry.scheduled` with a quota/429/402 error): dumps the session to `.opencode_session_dump-<session-id>.md` (one file per session) and runs the OS-specific notice script — `limit-notify.ps1` on Windows (`cmd /c start` opens its own console), `limit-notify.sh` on Linux/macOS (logs to `limit-notify.log`, opens a terminal if it has none). Also announces the limit inside the session. On a new session it injects the repo's session files as context for the first turn, scrubbed of the old error header. `/autosession status\|dump\|files\|inject\|simulate\|reset`. | `python setup.py --only opencode-auto-session --global --platform opencode` |

> **Relation to `telegram-notify`:** the skill is an on-demand Telegram library
> (text, files, webhooks); the plugin is an automatic event listener. They are
> complementary — both use `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.

## Repository Structure

```
Agents-Skills/
  setup.py               # Interactive installer (TUI menu)
  README.md              # This file
  agents/                # Agent definitions (YAML frontmatter + markdown)
    vault.md             # Unified notes manager (Obsidian / markdown)
    paper-researcher.md  # Academic paper writer
    jobfinder.md         # Job application assistant
    builder.md            # Build Mod — full-access dev agent (clone of opencode build)
    reverse-engineer.md   # Reverse-engineering orchestrator (apk-reverse + rea MCP)
    fitness-coach.md      # Science-based training advisor (read-only: cites, never codes)
  plugins/               # OpenCode runtime plugins (event listeners)
    opencode-telegram-answers/  # Telegram alerts on session.idle / permission.*
    opencode-tui-queue/         # Queues prompts typed while the session is busy
    opencode-auto-session/      # Session dump on usage limit + repo context on new session
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
    web-cloner/          # scripts/ + tests/
    ui-ux-pro-max/       # (Third-party — nextlevelbuilder)
    web-esenciales/      # scripts/ + tests/ + evals/
    web-design-guidelines/  # (Third-party — vercel-labs, MIT)
    ui-ux-orchestrator/  # scripts/ + tests/ + evals/
    math-notation/
    goal/
    osint/               # + tests/
    project-analyzer/
    code-review/
    debug/
    git-workflow/
    commit/              # + scripts/ + tests/ + evals/
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
| `vault` | Unified notes manager for Obsidian and any markdown-based app. Index, search, organize, verify, create notes, health checks, broken links, and link suggestions — 8 workflows, bilingual EN/ES. | read, glob, grep, task, edit |
| `paper-researcher` | Produces rigorous academic papers in Markdown (APA/IEEE/Vancouver). Bilingual EN/ES. | bash, read, glob, grep, webfetch, task, edit |
| `jobfinder` | Analyzes professional profile, searches jobs across multiple boards, calculates 5D match scores, generates CVs/cover letters, and tracks applications. | bash, read, glob, grep, webfetch, task, edit |
| `builder` | Clone del agente opencode `build` (Build Mod): agente primario de trabajo con todas las herramientas. Integrado con auto-mejora, creación de skills, optimización de metas y roadmaps. Descubre e integra desde la web MCP, skills, plugins y comandos (bajo aprobación). Comunicación optimizada en tokens (breve entre agentes, completa con el usuario). Decisión-first estilo hermes-agent: resuelve opciones con evidencia (determinista → simulación → pregunta), sin interrogatorio. | all tools (allow), question, doom_loop (ask) |
| `reverse-engineer` | Orquestador de ingeniería inversa para software propio o autorizado. Gate 0 de autorización, clasifica el objetivo y enruta a la toolchain correcta: `apk-reverse` (skill) para APKs Android; `rea` (MCP) para binarios nativos, .NET, JS/Electron, Flutter y firmware. No reimplementa RE: delega. Instala toolchains bajo demanda (aprobación). Bilingüe EN/ES. | edit, bash, read, glob, grep, list, webfetch, websearch, task, question |
| `fitness-coach` | Asesor de entrenamiento basado en evidencia: hipertrofia, fuerza, periodización y selección de ejercicios, con búsqueda en PubMed/CrossRef y citas APA 7th. Solo responde con fuentes Tier 1-2 verificadas (DOI); declara "evidencia insuficiente" cuando no las hay. Delega la literatura en `academic-source-search` y el formato en `citation-formatter`. No escribe código ni ejecuta comandos. | read, glob, grep, webfetch, websearch, task |

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
| `qa-tester` | Multiplatform QA suite: functional regression, exploration, break-to-fix loop, multi-user, performance, security, device compatibility. Playwright codegen only as exploration scaffolding. | — |
| `agent-self-improver` | Self-improvement framework for agents with human supervision. | — |
| `code-review` | Reviews a diff read-only on three axes (code quality, feature behavior vs. plan, relevancy) into one verdict report. | — |
| `refactor` | Improves code across four axes (cleanup, performance, security, architecture) by scanning and fixing, or applying audit findings. Behavior-preserving except security. Includes the 20-point web launch checklist (SEO, canonical URLs, SSL, backups, conversions). | — |
| `debug` | Reproduces and fixes a known bug, or finds an unknown root cause by hypothesis validation, with a test-driven fix and regression test. | — |
| `git-workflow` | Version-control workflows for branches, pull/merge requests, and release tags. Commits are owned by `commit`. | — |
| `commit` | Creates git commits in this repo's house convention (`{Type}: {explanation}`); ships a commit-msg validator and wires it into a husky hook (native git hook fallback). | — |
| `project-memory` | Builds and maintains the project's durable memory of architecture, conventions, and decisions so every session starts grounded. | — |
| `skill-creator` | Meta-skill: create, evaluate, compare and optimize other skills. *(Third-party — Anthropic, Apache 2.0)* | — |
| `impeccable` | Frontend design audit, polish, and redesign skill. *(Third-party — pbakaus, Apache 2.0)* | — |
| `ai-job-search` | AI job application framework: 5D fit evaluation, CV tailoring, cover letters. *(Third-party — MadsLorentzen, MIT)* | — |
| `jobfinder` | Job-search pipeline: profile matching, board search, 5D scoring, CV/cover-letter generation, application tracking. | ai-job-search |
| `web-cloner` | Clones pages and full sites into organized local code (index.html, styles/, scripts/, assets/) with stack detection and port to Astro/React/Vue/Svelte. | — |
| `ui-ux-pro-max` | Generates complete design systems (pattern, style, colors, typography) with 79 styles and 192 per-industry rules. *(Third-party — nextlevelbuilder)* | — |
| `web-esenciales` | Audits and completes the 20 must-haves of a business website (404, CTA, FAQs, schema, analytics); asks before implementing each gap. | — |
| `web-design-guidelines` | Reviews UI code against the Vercel Web Interface Guidelines (a11y, focus, forms, motion, i18n, perf, copy) with terse `file:line` findings. *(Third-party — vercel-labs, MIT)* | — |
| `ui-ux-orchestrator` | Orchestrates the UI/UX design set: routes to the owning skill per phase (design, gate, verify), fixes order and precedence so results never conflict, merges the executable checks into one prioritized report. | ui-ux-pro-max, impeccable, web-design-guidelines, web-esenciales |

## Commands

Slash commands you can type directly in your AI assistant.

`impeccable` does not ship one `.md` per command: its 23 sub-commands live in
`skills/impeccable/scripts/command-metadata.json`, so `setup.py` generates them
at install time (`--manifest` lists the resulting files). They carry the
`impeccable-` prefix so they never shadow built-ins such as `/init`.

### impeccable (23 commands)

| Command | Description |
|---------|-------------|
| `/impeccable-init` | Capture product context in PRODUCT.md |
| `/impeccable-craft [feature]` | Deprecated alias for an ordinary new-work request (build/redesign use the same flow) |
| `/impeccable-shape [feature]` | Plan UX/UI before writing code |
| `/impeccable-critique [target]` | UX design review with heuristic scoring |
| `/impeccable-audit [target]` | Technical quality checks (a11y, perf, responsive) |
| `/impeccable-polish [target]` | Final quality pass before shipping |
| `/impeccable-bolder [target]` | Amplify safe or bland designs |
| `/impeccable-quieter [target]` | Tone down aggressive designs |
| `/impeccable-distill [target]` | Strip to essence, remove complexity |
| `/impeccable-harden [target]` | Production-ready: errors, i18n, edge cases |
| `/impeccable-onboard [target]` | Design first-run flows, empty states |
| `/impeccable-animate [target]` | Add purposeful animations and motion |
| `/impeccable-colorize [target]` | Add strategic color to monochromatic UIs |
| `/impeccable-typeset [target]` | Improve typography hierarchy and fonts |
| `/impeccable-layout [target]` | Fix spacing, rhythm, and visual hierarchy |
| `/impeccable-delight [target]` | Add personality and memorable touches |
| `/impeccable-overdrive [target]` | Push past conventional limits: shaders, spring physics, scroll-driven reveals, 60fps motion |
| `/impeccable-clarify [target]` | Improve UX copy, labels, and error messages |
| `/impeccable-adapt [target]` | Adapt for different devices and screen sizes |
| `/impeccable-optimize [target]` | Diagnose and fix UI performance |
| `/impeccable-document` | Generate DESIGN.md from existing code |
| `/impeccable-extract [target]` | Pull reusable tokens and components |
| `/impeccable-live` | Visual variant mode in the browser |

### ai-job-search (8 commands)

> These are **upstream Claude-Code commands; `setup.py` does not install them.** The
> `ai-job-search` skill ships no `commands/` directory, so none of them exist as slash
> commands in this repo (the manifest lists 27 commands: 23 `impeccable-*`, `init-review`,
> `init-ui-ux`, `queue`, `autosession`). The descriptions below are kept for reference only.

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
  +-- jobfinder (skill)
        +-- ai-job-search (skill, third-party — upstream framework)
        +-- scripts/ (10 scripts: scoring, scraping, CV/cover-letter, reports, tracking)

builder (agent, Build Mod)
  +-- agent-self-improver (skill)  # feedback collection + pattern detection
  +-- skill-creator (skill)        # create/improve/benchmark skills
  +-- goal (skill)                # autonomous loop until an objective is reached
  +-- roadmaps (skill)             # multi-step task tracking (goal + steps)

reverse-engineer (agent)
  +-- apk-reverse (skill, external — newliver666, MIT; installed on demand)
  +-- rea (MCP server, external — morluto, MIT; installed on demand)

commit (skill)
  +-- scripts/validate_commit_msg.py  # commit-msg validator + husky hook installer

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

ui-ux-orchestrator (skill)
  +-- ui-ux-pro-max (skill, third-party)          # generate a design system from zero
  +-- impeccable (skill, third-party)             # craft / refine / audit an existing interface
  +-- web-design-guidelines (skill, third-party)  # code review vs the Vercel rules
  +-- web-esenciales (skill)                      # 20 business must-haves gate
  +-- scripts/ui_gate.py                          # merged deterministic gate
  # not UI skills: web-cloner (replication), refactor (code quality) stay out of this set

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
# Deterministic gates (fast; this is what CI runs)
python .github/scripts/check_doc_code_coherence.py   # docs cite real files
python .github/scripts/check_evals.py                # eval sets can actually fail
python .github/scripts/check_python_syntax.py        # every first-party .py compiles
python skills/backtest-validate/scripts/evaluate_backtest.py --selftest
python skills/jobfinder/scripts/score_match.py --selftest

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
python -m pytest skills/ui-ux-orchestrator -v
```

The two `--selftest` commands parse their own `SKILL.md` tables, so a threshold
edited in the doc without the code (or the reverse) fails. Executing the
`evals/evals.json` assertions needs `claude -p` plus an API key and stays a
manual step; CI only proves the files are well-formed and carry assertions.

### Third-party skills

- `skill-creator` — authored by **Anthropic, PBC** (Apache 2.0). Do not modify. To update, pull from the upstream source.
- `ui-ux-pro-max` — authored by **nextlevelbuilder** (check upstream repo for license). Do not modify. To update, pull from the upstream source or run `uipro update`.
- `impeccable` — authored by **pbakaus** (Apache 2.0). Do not modify. To update, run `npx impeccable install --providers=opencode --scope=project --force`.
- `ai-job-search` — authored by **MadsLorentzen** (MIT). Do not modify. To update, pull from the upstream source.
- `web-design-guidelines` — authored by **vercel-labs** (MIT). Do not modify. It fetches the live rules from `vercel-labs/web-interface-guidelines`; to update, re-copy `skills/web-design-guidelines/SKILL.md` from `vercel-labs/agent-skills`.
