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

## Usage

### Agents

Talk to these agents in natural language. They auto-detect intent and run the appropriate workflow.

| Agent | Example Prompts |
|-------|----------------|
| `vault` | "Find notes about Python", "Organize my vault by topic", "Create a daily note" |
| `paper-researcher` | "Write a research paper on X in APA", "Find academic sources for my thesis", "Review my paper's citations" |
| `jobfinder` | "Find remote Python developer jobs", "Score my CV against this posting", "Generate a cover letter for this role" |

### Skills

Skills are triggered automatically when the AI detects relevant keywords. Just describe what you need.

| Skill | Trigger Phrases |
|-------|----------------|
| `telegram-notify` | "Notify me on Telegram when this completes", "Send alert to my chat" |
| `academic-source-search` | "Find papers about machine learning", "Search arXiv for recent studies" |
| `citation-formatter` | "Format my citations in APA 7th", "Generate a references section in IEEE" |
| `content-humanizer` | "Make this text undetectable by AI", "Run AI detection on this essay" |
| `osint` | "Run an OSINT investigation on this target", "Look up this phone number" |
| `metric-optimizer` | "Optimize this metric to 95% accuracy", "Maximize model performance" |
| `roadmaps` | "Create a plan for this project", "Break this feature into steps" |
| `project-analyzer` | "Analyze this codebase for issues", "Audit this project's security" |
| `research-pipeline` | "Research this prediction market question", "Test this hypothesis with data" |
| `backtest-run` | "Backtest this trading strategy", "Run a backtest with slippage" |
| `backtest-validate` | "Validate this backtest quality", "Score this strategy before deploying" |
| `math-notation` | Auto-applied when writing math in academic docs |
| `agent-self-improver` | "Improve this agent's performance", "Review agent patterns and issues" |
| `skill-creator` | "Create a new skill from scratch", "Optimize this skill's triggers" |
| `impeccable` | "Polish this landing page UI", "Audit this design for accessibility" |
| `ai-job-search` | "Evaluate this job posting fit", "Tailor my CV for this role" |

## Repository Structure

```
Agents-Skills/
  setup.py               # Interactive installer (TUI menu)
  README.md              # This file
  agents/                # Agent definitions (YAML frontmatter + markdown)
    vault.md             # Unified Obsidian vault manager
    paper-researcher.md  # Academic paper writer
    jobfinder.md         # Job application assistant
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
    jobfinder/           # scripts/ + templates/
    math-notation/
    metric-optimizer/
    osint/               # + tests/
    project-analyzer/
    research-pipeline/
    roadmaps/            # + tests/
    skill-creator/       # (Third-party — Anthropic, Apache 2.0) + tests/
    telegram-notify/
    agent-self-improver/ # + tests/
```

## Agents

| Agent | Description | Permissions |
|-------|-------------|-------------|
| `vault` | Unified Obsidian vault manager. Index, search, organize, verify, create notes, health checks, broken links, and link suggestions — 8 workflows, bilingual EN/ES. | read, glob, grep, task, edit |
| `paper-researcher` | Produces rigorous academic papers in Markdown (APA/IEEE/Vancouver). Bilingual EN/ES. | bash, read, glob, grep, webfetch, task, edit |
| `jobfinder` | Analyzes professional profile, searches jobs across multiple boards, calculates 5D match scores, generates CVs/cover letters, and tracks applications. | bash, read, glob, grep, webfetch, task, edit |

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
| `metric-optimizer` | Optimizes numerical metrics via autonomous iterative improvement loop. | — |
| `roadmaps` | Creates, updates, and follows adaptive roadmaps for any project. | — |
| `project-analyzer` | Read-only project analysis: structure, code quality, bugs, security, performance. | — |
| `agent-self-improver` | Self-improvement framework for agents with human supervision. | — |
| `skill-creator` | Meta-skill: create, evaluate, compare and optimize other skills. *(Third-party — Anthropic, Apache 2.0)* | — |
| `impeccable` | Frontend design audit, polish, and redesign skill. *(Third-party — pbakaus, Apache 2.0)* | — |
| `ai-job-search` | AI job application framework: 5D fit evaluation, CV tailoring, cover letters. *(Third-party — MadsLorentzen, MIT)* | — |

## Commands

Runnable CLI scripts you can execute directly from the terminal:

### OSINT

```bash
# Generate investigation plan
python skills/osint/scripts/generate_plan.py --target-type person --target-value "John Doe" --depth standard

# Execute OSINT pipeline
python skills/osint/scripts/run_investigation.py --plan investigation_plan.json --interactive

# Parse phone numbers
python skills/osint/scripts/phone_parser.py +1234567890 --json

# Scrape free directories
python skills/osint/scripts/scrape_directories.py +1234567890 --json

# Generate report
python skills/osint/scripts/gen_report.py --target "John Doe" --target-type person --format both
```

### Job Search

```bash
# Search jobs
python skills/jobfinder/scripts/search_jobs.py --keywords "python developer" --location "Remote" --remote-only

# Score job matches (5D framework)
python skills/jobfinder/scripts/score_match.py --profile profile.json --jobs results.json

# Analyze skill gaps
python skills/jobfinder/scripts/gap_analysis.py --profile profile.json --scored scored.json

# Generate CV PDF
python skills/jobfinder/scripts/generate_cv_pdf.py --profile profile.json --lang en

# Generate cover letter
python skills/jobfinder/scripts/generate_cover_letter.py --profile profile.json --job job.json

# Suggest projects for skill gaps
python skills/jobfinder/scripts/suggest_projects.py --missing-skills "kubernetes,docker" --job-title "SRE"

# Track applications
python skills/jobfinder/scripts/track_application.py add --company "Acme" --role "Dev"
```

### Finance

```bash
# Evaluate backtest quality
python skills/backtest-validate/scripts/evaluate_backtest.py --total-trades 200 --win-rate 0.58 --avg-win-pct 2.1 --avg-loss-pct 1.5 --max-drawdown-pct 12 --years-tested 3 --num-parameters 8 --slippage-tested
```

### Writing

```bash
# Detect AI-generated text
python skills/content-humanizer/scripts/detect_ai.py --file essay.md --verbose

# Generate formatted academic document
python skills/citation-formatter/scripts/generate_outputs.py --file paper.md --norm apa --html
```

### Planning

```bash
# Validate roadmap structure
python skills/roadmaps/scripts/validate_roadmap.py --file roadmap.md
```

## Dependency Graph

```
vault (agent)
  8 workflows: Auto-Index, Search, Organize, Verify, Create, Health, Link, Clean

paper-researcher (agent)
  +-- academic-source-search (skill)
  +-- citation-formatter (skill)
        +-- scripts/generate_outputs.py

jobfinder (agent)
  +-- scripts/ (7 scripts: scoring, scraping, CV, reports, tracking)

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
python -m pytest skills/roadmaps/tests/ -v
python -m pytest skills/jobfinder/tests/ -v
python -m pytest skills/ai-job-search/tests/ -v
python -m pytest skills/agent-self-improver/tests/ -v
```

### Third-party skills

- `skill-creator` — authored by **Anthropic, PBC** (Apache 2.0). Do not modify. To update, pull from the upstream source.
- `impeccable` — authored by **pbakaus** (Apache 2.0). Do not modify. To update, run `npx impeccable install --providers=opencode --scope=project --force`.
- `ai-job-search` — authored by **MadsLorentzen** (MIT). Do not modify. To update, pull from the upstream source.
