---
name: research-pipeline
description: >-
  Use when the user needs to conduct quantitative research for prediction markets, market analysis, or data-driven research questions. Triggers on keywords like "research", "prediction market", "pipeline", "quant research", "market research", "forecast". This skill runs a structured research pipeline including scope definition, literature search, hypothesis formulation, prototyping, measurement, and decision. Use BEFORE telegram-notify (which sends notifications on pipeline completion).
compatibility: Used by telegram-notify for completion notifications. Produces research logs saved to research/ directory.
---

# Research Pipeline

Execute autonomously. No user prompts. This pipeline is designed to produce reproducible and structured quantitative research results. Each step has a purpose: scoping prevents ambiguous questions, literature search prevents reinventing the wheel, the hypothesis forces clarity, and the final decision ensures every investigation ends with an actionable conclusion.

## When to use
- User needs to answer a quantitative research question
- Keywords: "research", "investigacion", "prediction market", "pipeline", "quant research", "forecast", "prediccion"
- Need a structured approach from question to conclusion
- Market analysis or data-driven hypothesis testing

## When NOT to use
- User wants to search for academic sources only (use `academic-source-search`)
- User wants to send a notification about research (use `telegram-notify`)
- Question is qualitative, not data-driven
- No clear metric or measurable outcome possible

## Workflow

### 1. SCOPE — Define question
Write what, metric, constraints. Display current status.

### 2. LITERATURE — Search sources
Priority: official docs > arXiv > ACM > IEEE > Springer > Nature > OpenReview > Big Tech research > official APIs > official repos. Use specific search terms. Log each source.

### 3. HYPOTHESIS — Write testable claim
Format: "Using METHOD on DATA, we expect METRIC to improve by X%."

### 4. PROTOTYPE — Minimum implementation
Smallest possible code. Must run in <60s. Auto-fix errors.

### 5. MEASURE — Quantify result
Compare against deterministic baseline. Auto-retry on failure.

### 6. DECIDE — Keep, iterate, or discard
- Metric improves > integrate into pipeline
- Ambiguous > refine hypothesis, test again
- Worse > discard, document why

### 7. LOG
Save to `research/YYYY-MM-DD-topic.md`. Include: question, method, result table (metric, before, after, delta), conclusion.

## Output format
- Markdown file at `research/YYYY-MM-DD-topic.md` containing:
  - Research question
  - Method description
  - Result table (metric, before, after, delta)
  - Conclusion (keep/iterate/discard)

## Dependencies
No additional pip packages required. Uses built-in tools and standard Python libraries.

## Error handling
- **Prototype fails to run:** Auto-fix errors up to 3 attempts. If persistent, log blocker and move to DECIDE
- **No relevant literature found:** Proceed with hypothesis based on domain knowledge, note in LOG
- **Measurement produces NaN/inf:** Re-run with different parameters, log failure
- **Scope too broad:** Narrow to a single testable metric before proceeding

## File structure
```
research-pipeline/
└── SKILL.md
```

## Restrictions
- **DO NOT** prompt the user for input — execute autonomously
- **DO NOT** skip the SCOPE step — every pipeline needs a clear question
- **DO NOT** skip the DECIDE step — every pipeline must end with a conclusion
- **DO NOT** proceed to PROTOTYPE without a written HYPOTHESIS
- **DO NOT** discard results without documenting why

## Workflow Example

**Question:** "What is the best caching strategy to reduce latency in REST APIs?"

1. **SCOPE**: Metric = response time (ms), constraint = <50ms p99, data = APIs with 10k requests/min
2. **LITERATURE**: Search "API caching strategies Redis Memcached benchmark" on arXiv and ACM
3. **HYPOTHESIS**: "Using Redis with 60s TTL on read endpoints, we expect p95 latency to decrease by 40%"
4. **PROTOTYPE**: 50-line script comparing Redis vs Memcached vs no cache
5. **MEASURE**: Benchmark with 10k requests, measure p50/p95/p99
6. **DECIDE**: If Redis reduces >30%, integrate. Otherwise, try different configuration.
7. **LOG**: Save to `research/YYYY-MM-DD-api-caching.md`
