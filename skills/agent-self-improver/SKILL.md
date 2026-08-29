---
name: agent-self-improver
description: >-
  Use when the user wants to improve an agent's performance, analyze agent
  behavior, detect recurring issues across sessions, or optimize agent prompts /
  skills / scripts. Collects structured feedback, detects patterns, and suggests
  concrete improvements — always with human approval; never auto-applies changes.
  Works for any agent or automated tool (not just document generation). Triggers:
  "agent improvement", "self-improvement", "agent feedback", "agent patterns",
  "improve agent", "optimize agent", "agent performance", "detect issues",
  "mejorar agente", "retroalimentacion", "patrones de agente", "auto-mejora",
  "agent review", "agent audit", "feedback loop", "prompt optimization",
  "behavior analysis". Also use when reviewing scripts or automated tool output
  quality.
compatibility: [python]
---

# Agent Self-Improver

Self-improvement framework for AI agents. Collects structured feedback across
sessions, detects recurring patterns, and suggests concrete improvements —
always requiring human approval before applying anything. Generic by design;
domain-specific checklists (e.g. python-docx) live in `references/` and are
loaded only when relevant.

## When to Use
- After completing a non-trivial task (any domain: code, docs, research, config)
- When the user reports issues or asks "what went wrong?"
- When reviewing scripts or tools for quality
- Proactively: after a session that had a fixed failure or `retry_count >= 2`

Do NOT interrupt for every session — proactive review is for *failed or flaky*
sessions, not routine successful work (so the user doesn't start ignoring it).

## Inputs (What We Need)

Gather these data points after a session:

```yaml
session_context:
  task_description: "What was the user trying to do?"
  agent: "which agent or tool ran"
  tools_used: ["tool1", "tool2"]
  files_created: ["file1.docx", "file2.py"]
  retry_count: 3          # times user had to re-prompt
  total_tool_calls: 15
  errors_encountered:
    - type: "bug"          # one canonical type, see below
      severity: "high"     # critical | high | medium | low
      message: "exact error message"
      fix_applied: "what fixed it"
      root_cause: "why it happened"
```

### Canonical issue `type` vocabulary

Use exactly one of these for every issue (the analysis script groups by this
field, so mixing spellings fragments the data):

| type | Meaning |
|------|---------|
| `format` | Output doesn't match the required format/spec |
| `bug` | Script or logic error |
| `xml` | XML/DOCX structure issue |
| `i18n` | Non-English / internationalization issue |
| `logic` | Wrong reasoning or algorithmic decision |
| `performance` | Too slow / too many tokens / inefficiency |
| `other` | Anything not covered above (describe in `description`) |

The top-level `category` is a separate, coarse bucket for the whole session:
`document-generation`, `code`, `research`, `config`, `other` — do not reuse the
issue `type` values there.

## Targets (What Success Looks Like)

Define measurable targets BEFORE starting work. Use only metrics relevant to the
session's domain (the examples below are guidance, not a fixed checklist):

- **Format compliance** — output matches the required spec (IEEE/APA/etc.)
- **Functional correctness** — output runs / links resolve / features work
- **i18n** — non-English content handled correctly
- **Code quality** — script is maintainable, correct, handles errors

See `references/docx-generation.md` for a concrete docx-specific checklist.

## State store (persistence)

To make "detect patterns across sessions" actually work, keep accumulated
feedback in a stable, append-only location. Recommended layout (create on first
use):

```
.opencode/state/agent-self-improver/
  sessions.jsonl           # one feedback entry per line, append-only
  improvement-log.json     # derived patterns / suggestions (from analyze)
  checkpoint/              # backups before any applied modification
```

`collect_feedback.py` appends to its `templates/agent-feedback.json` by default;
`analyze_feedback.py` reads it. For your own projects, prefer the
`.opencode/state/agent-self-improver/` layout above and point the scripts at it
with `--input`/`--output`. If both locations exist, trust the newer timestamps
and merge by deduplicating on session `id`.

## Workflow

### 1. Collect Feedback
After each agent session, record structured feedback with
`scripts/collect_feedback.py`:

```bash
python scripts/collect_feedback.py \
  --task "Generate IEEE DOCX with clickable citations" \
  --agent paper-researcher \
  --category document-generation \
  --rating 3 \
  --issues "format_wrong,bookmark_order,i18n_missing" \
  --issue-types "format,xml,i18n" \
  --issue-severities "high,high,medium" \
  --fixes "use_justify_enum,w_anchor,spanish_pattern" \
  --root-causes "copied_apa_default,order_of_ops,hardcoded_english" \
  --retries 2 --tool-calls 25 --tokens 50000 --duration 1200
```

`python scripts/collect_feedback.py --interactive` walks through the fields and
validates enum values. The script requires `--task` and `--rating`.

### 2. Detect Patterns
Run `scripts/analyze_feedback.py` to find recurring issues:

```bash
python scripts/analyze_feedback.py \
  --input .opencode/state/agent-self-improver/sessions.jsonl \
  --output .opencode/state/agent-self-improver/improvement-log.json \
  --threshold 0.2 --min-sessions 2
```

It detects: frequency (issues in >threshold of sessions), severity, category
grouping, trend over time, and common fix patterns.

### 3. Suggest Improvements
For each detected pattern, generate a structured suggestion (concrete, with
exact before/after, not vague advice). Deduplicate suggestions across sessions
before presenting.

### 4. Present — Human Approval Required
**NEVER auto-apply changes.** Present suggestions in this format:

```
IMPROVEMENT SUGGESTION [#1]
━━━━━━━━━━━━━━━━━━━━━━━━━━
Pattern: IEEE format specs ignored on first attempt
Frequency: 33% of sessions
Severity: HIGH
Confidence: 90%

Proposed change:
  Add FORMAT_SPEC dictionary with all standard values

Before: FONT_SIZE_BODY = Pt(12)
After:  IEEE_FONT_SIZE = Pt(10)

Affected: scripts/generate_docx.py
Approve? [y/n]
```

### 5. Apply + Close the Loop
After the user approves and you apply a change:
1. **Backup** the affected file to the `checkpoint/` dir first.
2. **Test** the change (run the script/output) before declaring success.
3. **Track** the relevant target metrics before and after.
4. Later, re-run `analyze_feedback.py` and report the **delta** in pattern
   frequency (did the issue drop?) — this closes the loop and shows whether the
   improvement actually worked.

## Metrics Tracked

| Metric | Description | Target |
|--------|-------------|--------|
| Task completion rate | % of tasks completed on first try | >80% |
| Average rating | User satisfaction (1-5) | >4 |
| Retry rate | Times user re-prompts | <2 |
| Issue density | Issues per 10 tool calls | <1 |
| Fix success rate | % of fixes that work first time | >90% |

## Common Issue Patterns

The generic patterns to watch for when reviewing any session: repeated
failures on the same tool call, re-prompting by the user, output that needed
manual correction, and commands documented in a skill that don't exist in the
codebase. For python-docx / document-generation specifics, load
`references/docx-generation.md`.

## Error handling
- **Missing `--task`/`--rating`** in `collect_feedback.py`: it exits with a
  clear error; provide both or use `--interactive`.
- **Empty feedback store:** `analyze_feedback.py` returns `{"error": "No
  feedback entries found"}`; collect feedback first.
- **Threshold out of range:** clamp `--threshold` to (0, 1]; `--min-sessions`
  to >= 1.
- **Corrupted feedback file:** if JSON/JSONL fails to parse, back it up and
  start a fresh file rather than silently discarding history.

## Rules
1. **Human in the loop** — Never modify agent files without explicit user approval.
2. **Data-driven** — Base suggestions on accumulated feedback, not single sessions.
3. **Specific changes** — Suggest exact edits, not vague improvements.
4. **Measurable** — Track metrics before and after changes; report the delta.
5. **Reversible** — Always keep a checkpoint/backup before any modification.
6. **Test first** — Run the script/output before declaring success.
7. **Verify format** — Cross-check output against the actual standard spec.
8. **Unified vocabulary** — Use one canonical issue `type` per issue (table above).
9. **Persist always** — Append every session to the state store so cross-session
   patterns are real, not replayed in-memory.
