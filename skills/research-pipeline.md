---
name: research-pipeline
description: Use when the user needs to conduct quantitative research for prediction markets, market analysis, or data-driven research questions. Triggers on keywords like "research", "investigacion", "prediction market", "pipeline", "quant research", "analisis cuantitativo", "market research", "forecast", "prediccion". This skill runs a structured research pipeline: scope definition, literature search, hypothesis formulation, prototyping, measurement, and decision. Use BEFORE telegram-notify (which sends notifications on pipeline completion).
compatibility: Used by telegram-notify for completion notifications.
---

# Research Pipeline

Execute autonomously. No user prompts. Este pipeline esta disenado para producir resultados de investigacion cuantitativa reproducibles y estructurados. Cada paso tiene un proposito: el scoping evita preguntas ambiguas, la busqueda de literatura evita reinventar la rueda, la hipotesis fuerza claridad, y la decision final asegura que cada investigacion termine con una conclusion accionable.

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
