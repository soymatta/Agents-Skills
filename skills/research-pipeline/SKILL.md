---
name: research-pipeline
description: >-
  Conducts quantitative research for prediction markets, market analysis, or data-driven questions via a
  structured pipeline: SCOPE (clarifying questions + budget) -> LITERATURE (delegated) -> HYPOTHESIS ->
  PROTOTYPE -> MEASURE -> DECIDE -> LOG. Non-interrupting after scoping. Use when the user needs to answer a
  quantitative research question, test a data-driven hypothesis, or run a structured investigation end to end.
  Run BEFORE telegram-notify. Triggers: "research", "prediction market", "market research", "hypothesis test",
  "investigar", "probar hipotesis", "structured research".
compatibility: Delegates literature search to academic-source-search; notifies via telegram-notify. Produces research logs saved to research/ directory.
---


# Research Pipeline

Execute with minimal interruption. Ask 1-2 scoping questions up front (metric + data source + iteration/cost/time budget), then run autonomously without further prompts until DECIDE/LOG. Each step has a purpose: scoping prevents ambiguous questions, literature search prevents reinventing the wheel, the hypothesis forces clarity, and the final decision ensures every investigation ends with an actionable conclusion.

## When to use
- User needs to answer a quantitative research question
- Keywords: "research", "investigacion", "prediction market", "pipeline", "quant research", "market research", "forecast", "prediccion", "hypothesis test", "benchmark", "data-driven research", "quantitative analysis", "research question", "scientific method", "literature review", "market analysis", "investigar", "estudio cuantitativo", "probar hipotesis", "evaluar metodo", "comparar enfoques", "research pipeline", "structured research", "autonomous research", "research loop", "data investigation"
- Need a structured approach from question to conclusion
- Market analysis or data-driven hypothesis testing

## When NOT to use
- User wants to search for academic sources only (use `academic-source-search`)
- User wants to send a notification about research (use `telegram-notify`)
- Question is qualitative, not data-driven
- No clear metric or measurable outcome possible

## Workflow

### 1. SCOPE - Define question
Ask 1-2 clarifying questions up front: (a) the exact metric to optimize and its direction, (b) the data source / constraints, (c) the iteration budget (default: max 3 hypothesis iterations) and time/cost ceiling. Then write what, metric, constraints. Display current status. Do not proceed before the metric and direction are unambiguous.

### 2. LITERATURE - Search sources
Delegate the search to `academic-source-search` rather than rolling your own (it has the standardized free-API flow: CrossRef/arXiv/PubMed + DOI dedup). Also check official docs, official APIs, and official repos directly. Use specific search terms. Log each source. If a paywalled source (IEEE/Springer/Nature) needs API credentials, note whether a key is available in the environment/.env before attempting it; otherwise skip and rely on free sources.

### 3. HYPOTHESIS - Write testable claim
Format: "Using METHOD on DATA, we expect METRIC to improve by X%."

### 4. PROTOTYPE - Minimum implementation
Smallest possible code. Must run in <60s. Auto-fix errors up to 3 attempts.

### 5. MEASURE - Quantify result
Compare against deterministic baseline. Auto-retry on failure.

### 6. DECIDE - Keep, iterate, or discard
- Metric improves > integrate into pipeline
- Ambiguous > refine hypothesis, test again
- Worse > discard, document why
- **Iteration cap:** do not iterate more than 3 rounds (or the agreed budget). After the cap, pick the best result or discard with a documented reason — do NOT loop indefinitely.

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
- **Source needs an API key that is unavailable:** Skip that source and rely on free ones; note in LOG

## File structure
```
research-pipeline/
��� SKILL.md
```

## Restrictions
- **DO** ask 1-2 scoping questions up front (metric, data source, iteration/time budget), then execute without further prompts
- **DO NOT** skip the SCOPE step - every pipeline needs a clear question and metric direction
- **DO NOT** skip the DECIDE step - every pipeline must end with a conclusion
- **DO NOT** exceed the iteration cap (default 3) - pick best or discard rather than loop forever
- **DO NOT** proceed to PROTOTYPE without a written HYPOTHESIS
- **DO NOT** roll your own literature scraper when `academic-source-search` already exists
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
