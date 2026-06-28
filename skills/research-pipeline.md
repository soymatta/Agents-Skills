---
name: research-pipeline
description: Structured quantitative research process for prediction markets. Never ask the user.
---

# Research Pipeline

Execute autonomously. No user prompts.

## Pipeline

### 1. SCOPE — Define question
Write what, metric, constraints. Display current status.

### 2. LITERATURE — Search sources
Priority: official docs → arXiv → ACM → IEEE → Springer → Nature → OpenReview → Big Tech research → official APIs → official repos. Use specific search terms. Log each source.

### 3. HYPOTHESIS — Write testable claim
Format: "Using METHOD on DATA, we expect METRIC to improve by X%."

### 4. PROTOTYPE — Minimum implementation
Smallest possible code. Must run in <60s. Auto-fix errors.

### 5. MEASURE — Quantify result
Compare against deterministic baseline. Auto-retry on failure.

### 6. DECIDE — Keep, iterate, or discard
- Metric improves → integrate into pipeline
- Ambiguous → refine hypothesis, test again
- Worse → discard, document why

### 7. LOG
Save to `research/YYYY-MM-DD-topic.md`. Include: question, method, result table (metric, before, after, delta), conclusion.
