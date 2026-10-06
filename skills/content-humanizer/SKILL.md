---
name: content-humanizer
description: >-
  Final revision pass to reduce AI-detectable patterns and pass AI detection tools (Turnitin, GPTZero,
  Originality.ai, ZeroGPT). Adjusts sentence structure, vocabulary, punctuation, and burstiness while keeping
  academic rigor; includes detect_ai.py for local verification. Run ONLY at the end when content, citations,
  and references are finalized. Use when the user wants to humanize text, avoid AI detection, or pass Turnitin/
  GPTZero. Triggers: "humanize", "humanizar", "anti-AI", "evitar deteccion", "Turnitin", "GPTZero", "pasar Turnitin", "revision final",
  "make this sound human", "AI detector".
---

# Content Humanizer

Final humanization pass. Run ONLY when the document is complete, reviewed,
and all references verified.

**Do not alter:** data, citations, references, academic structure, metadata,
or inline notation tokens.

> **Pipeline token protection (mandatory):** this pass may run after math-notation
> has been applied. **Do not** "clean up" or rewrite `_text_`, `^{...}`, `_{...}`
> (variables/italics/super/subscripts used by `generate_outputs.py`). In
> particular do NOT turn `_r_{0}` into `r₀` or `_x_` into `*x*` — that would
> silently break the downstream generator. Only humanize the surrounding prose.

## When to use
- Final pass before submitting academic documents
- After all content, citations, and references are finalized
- Keywords: "humanize", "anti-AI", "Turnitin", "GPTZero", "Originality.ai", "ZeroGPT", "detect AI", "final pass", "humanizar texto", "pasar Turnitin", "evitar deteccion IA", "revision final", "texto humano", "make this sound human", "AI detector", "originality check", "does this pass as human"
- When document scores high on AI detection tools

## When NOT to use
- During initial writing or drafting phase
- When modifying data, citations, or references
- For non-academic content (blog posts, documentation)
- Before content is complete and referenced

---

## 1. HUMANIZE — Apply techniques

### 1.1 High-frequency AI words and phrases

| Avoid | Use instead |
|-------|-------------|
| "in the realm of" | "in", "within" |
| "it is fundamental to highlight" | "notably", "relevantly" |
| "it is worth mentioning that" | remove it, get straight to the point |
| "in other words" | rephrase directly |
| "in this regard" | "thus", "therefore", "then" |
| "as previously mentioned" | reference the section, do not repeat |
| "not only... but also" | use max 1 time per document |
| "it is interesting to note" | remove it, adds no value |
| "it is worth highlighting" | only if truly necessary |
| "in relation to" | "about", "regarding" |
| "as an example" | "for example", "like" |
| "one might wonder" | direct question without preamble |
| "it is important to consider" | remove or rephrase |
| "from a perspective" | "from", "according to" |
| "consequently" | "therefore", "so" |
| "likewise" | "also", "furthermore" (max 1-2 times) |
| "on the other hand" | "in contrast", "however" |
| "it is evident that" | direct statement |
| "it should be noted that" | remove it |
| "it is necessary to point out" | remove it |
| "with regard to" | "about", "regarding" |

### 1.1b Spanish high-frequency AI phrases

| Evitar | Usar en su lugar |
|--------|------------------|
| "en el ámbito de" | "en", "dentro de" |
| "es fundamental señalar" | "cabe destacar", "notablemente" |
| "es importante mencionar" | eliminarlo, ir al grano |
| "en otras palabras" | reformular directamente |
| "en este sentido" | "por lo tanto", "así", "luego" |
| "como se mencionó anteriormente" | remitir a la sección, no repetir |
| "no solo... sino también" | máximo 1 vez por documento |
| "resulta interesante destacar" | eliminarlo, no aporta valor |
| "cabe resaltar" | solo si es imprescindible |
| "en relación con" | "sobre", "acerca de" |
| "a modo de ejemplo" | "por ejemplo", "como" |
| "cabe preguntarse" | pregunta directa sin preámbulo |
| "es preciso considerar" | eliminar o reformular |
| "desde una perspectiva" | "desde", "según" |
| "en consecuencia" | "por tanto", "así" |
| "asimismo" | "también", "además" (máx. 1-2 veces) |
| "por otro lado" | "en cambio", "sin embargo" |
| "es evidente que" | enunciado directo |
| "conviene señalar que" | eliminarlo |
| "con respecto a" | "sobre", "acerca de" |

### 1.2 Break structural patterns

**Excessive parallelism:** vary grammatical structure between paragraphs.
**Mechanical transitions:** do not start every paragraph with a logical connector.
**Artificial closure:** do not end every section with "In conclusion...".

### 1.3 Syntactic structure variation

```
BEFORE (AI):  The study analyzed 150 patients. The results showed
              a significant improvement. The standard deviation was minimal.

AFTER:        In the study, 150 patients were analyzed over six months.
              The results, which showed a significant improvement, align
              with previous research. The standard deviation, notably,
              remained within expected ranges.
```

Rules:
- Alternate: SVO / verb-subject / introductory phrase
- No more than 2 consecutive sentences with the same structure
- Per paragraph: 1 long sentence (>25 words) for every 2 short ones (<15)

### 1.4 Paragraph opening variation

No paragraph should start the same way as the previous 2. Rotate between:
direct statement, rhetorical question, soft connector, specific data,
temporal reference, condition.

### 1.5 Vocabulary variation

| Concept | Alternatives |
|---------|-------------|
| "demonstrates" | "suggests", "indicates", "reveals", "shows", "points to", "evidences" |
| "important" | "relevant", "significant", "determinant", "key" |
| "analyzes" | "examines", "evaluates", "studies", "addresses", "reviews", "explores" |
| "result" | "finding", "outcome", "consequence", "product", "consequence" |
| "shows" | "evidences", "reflects", "exposes", "reveals", "presents" |
| "significant" | "considerable", "notable", "substantial", "appreciable" |

Do not use the same word more than 2 times in 3 consecutive paragraphs.

### 1.6 Natural punctuation

AI text avoids `;`, `:`, `()`, `—`. Add them:
- 1-2 semicolons per 10 sentences
- 1-2 em dashes per section
- Parentheses for clarifications (1-2 per section)
- Colons to introduce explanations

### 1.7 Burstiness

Mix sentences from 5 to 40+ words. Standard deviation of length >12.

To automatically calculate burstiness (SD of sentence lengths):
```bash
# Linux/macOS:
python -c "import sys,statistics;s=sys.stdin.read();l=[len(o.split()) for o in s.replace('?','.').replace('!','.').split('.') if o.strip()];print(f'Sentences: {len(l)}, Mean: {statistics.mean(l):.1f}, SD: {statistics.stdev(l):.1f}')" < document.md

# Windows (PowerShell):
Get-Content document.md | python -c "import sys,statistics;s=sys.stdin.read();l=[len(o.split()) for o in s.replace('?','.').replace('!','.').split('.') if o.strip()];print(f'Sentences: {len(l)}, Mean: {statistics.mean(l):.1f}, SD: {statistics.stdev(l):.1f}')"
```

> **Counting note:** the snippet above splits on every `.`, which counts decimal
> points and abbreviations (e.g. `i.e.`, `$1.5`) as sentence breaks. That inflates
> both the sentence count and the SD toward an artificially high "burstiness".
> Interpret the SD number as a **relative signal**, not an absolute target, and
> when in doubt eyeball the actual sentence boundaries.

### 1.8 Active voice > passive

Max 20% of sentences in passive (40% in methodology).

### 1.9 Controlled imperfections

1-2 per every 3 sections: sentence starting with "And"/"But",
shorter/longer paragraph, anaphora, non-ideal connector.

---

## 2. DETECT — Verify with detect_ai.py

After humanizing the document, run the local detector to gauge how detectable
the text is:

```bash
# Install dependencies (once)
pip install transformers torch

# Test the complete document (run from project root)
python scripts/detect_ai.py --file document.md --verbose
```

The script is bilingual in output: `AI`/`Human:` percentages plus a verdict that
prints **`PASA`** (passed/human) or **`DETECTADO`** (detected/AI) in Spanish.
The default AI threshold is `--threshold 0.5` (50%): the verdict is `PASA` only
when the global AI probability is ≤ the threshold **and** no individual section
exceeds it.

### Result interpretation

```
  DETECTOR DE IA - Resultados
  AI:   12.3%            ← probability of being AI (should be < threshold)
  Human: 87.7%
  Verdict: PASA          ← PASA (passed) or DETECTADO (detected)
```

| Verdict | Meaning | Action |
|---------|---------|--------|
| AI ≤ threshold, no bad section | Human-like | Ready to submit (see calibration note below) |
| AI near threshold | Ambiguous text | Review flagged sections, apply more variation |
| AI > threshold or a section exceeds it | Detected text | Repeat humanization on sections with highest score |
| AI > 70% | Highly detectable | Rewrite from scratch using this skill's techniques |

Use `--threshold X` to set a stricter/looser bar (e.g. `--threshold 0.4`).

> **Calibration (important):** `detect_ai.py` uses a 2019 RoBERTa-based detector
> with a **high false-positive rate**. Treat a `PASA` as "this text no longer
> carries the obvious AI fingerprints this skill targets" — **not** as a
> guarantee it will pass Turnitin/GPTZero/ZeroGPT, which use different models.
> Always pair it with the offline techniques (burstiness, structure, phrases)
> and a human read.

### Section-level analysis (--verbose)

The detector flags which sections have higher AI probability.
Apply additional humanization specifically to those sections
and re-run the detector.

### If transformers cannot be installed

Do NOT use `webfetch` to hit ZeroGPT/GPTZero directly — those sites are
interactive POST pages behind anti-bot controls and cannot be scraped this way.
Instead:
1. Ask the user to run the text through an online checker (e.g. ZeroGPT, GPTZero)
   and paste the result back.
2. Compare the result against the local detector output.
3. If both indicate AI, return to humanization with more techniques.

---

## 2b. Free multi-layer pipeline — verify_ai.py

`scripts/verify_ai.py` is the unified **free** detector: linguistic metrics +
local HF detectors + (optional) external free services, with one gate exit code
(0=PASA, 1=DETECTADO).

Layers (all free):

| Layer | What | Requires | Offline by default |
|-------|------|----------|--------------------|
| 1 | Lingüística: burstiness SD, TTR, conectores/frases AI, pasiva, puntuación | none | yes |
| 2 | Local HF: roberta-base-openai-detector (+ extras con `--local-extra`) | torch + transformers, caché en HF_HOME | yes |
| 3 | Hugging Face Inference API: detector por texto + juez LLM | `HF_TOKEN` (cuenta gratuita) | no |
| 4 | GPTZero API (tier gratuito con créditos limitados, endpoint oficial) | `GPTZERO_API_KEY` | no |

```bash
# Mínimo (Capa 1 + 2, sin nada online)
python scripts/verify_ai.py --file document.md --verbose

# + más detectores locales (descarga ~horas/GB; si un id falla se salta)
python scripts/verify_ai.py --file document.md --local-extra

# + capas externas gratuitas (HF_TOKEN y/o GPTZERO_API_KEY en el entorno)
python scripts/verify_ai.py --file document.md --hf-token "$env:HF_TOKEN"
python scripts/verify_ai.py --file document.md --gptzero-key "$env:GPTZERO_API_KEY"
```

Fusion: `final = 0.6*local + 0.4*externa` (si no hay externa se usa solo la local).
Verdict `PASA` solo si el global **y** cada sección están bajo el umbral
(default `--threshold 0.5`). Las capas externas degradan con aviso si fallan
(red/403/modelo no soportado) — nunca rompen el gate.

Linguistic red flags it reports automatically: `Burstiness SD < 12`,
connector density per sentence, AI-phrase hits, passive-per-sentence ratio.
Higher is normally better; treat individual numbers as a relative signal.

> **Token/keys:** HF_TOKEN (gratis) se obtiene en huggingface.co/settings/tokens;
> GPTZERO_API_KEY en gptzero.me (plan free, créditos limitados). Ninguna parte
> de este pipeline requiere pago; si no hay keys, se omiten Capas 3-4.

---

## 3. ITERATE — Verification loop

```
for iteration in 1..3:
    humanize(document)
    ok = run('python scripts/detect_ai.py --file document.md')  # exit 0 == PASA (human)
    if ok:
        break
    else:
        humanize(flagged_sections)   # from --verbose output
```

Maximum 3 iterations. If after 3 attempts still detected,
manually review the most problematic sections.

---

## Final Checklist

- [ ] Scan and replace red-table phrases
- [ ] Vary paragraph openings (none same as previous 2)
- [ ] Split or merge sentences to break uniformity
- [ ] Insert 2-3 asides with dashes or parentheses
- [ ] Convert passive to active (where applicable)
- [ ] Verify burstiness: standard deviation of length >12
- [ ] Count repeated connectors and replace
- [ ] No "as previously mentioned" or similar
- [ ] Each section ends without forced closure
- [ ] **Run detect_ai.py → Verdict: PASA (exit 0)** (or `verify_ai.py` for the full free multi-layer pipeline)

---

## Dependencies
```bash
pip install transformers torch
```
For online verification, ask the user to run the text through an online checker
and paste the result (no tool dependency). Optional (free, Layer 3-4 of
`verify_ai.py`): `HF_TOKEN` and/or `GPTZERO_API_KEY` env vars.

## Restrictions

- **DO NOT** modify data, figures, dates, names
- **DO NOT** alter direct quotes or their formatting
- **DO NOT** remove or modify references
- **DO NOT** change academic structure (sections, headers)
- **DO NOT** add new information
- **DO NOT** remove relevant information
- **DO NOT** reduce academic rigor or technical precision
- **DO NOT** touch inline notation tokens (`_…_`, `^{…}`, `_{…}`) from math-notation — humanize the prose, never the parser notation

## Error handling
- **detect_ai.py not found:** Look in `scripts/detect_ai.py` relative to the skill
- **transformers not installed:** Ask the user to run the text through an online checker (ZeroGPT/GPTZero) and paste the result; do NOT webfetch those interactive sites
- **Document too long:** Process by sections, humanize each separately
- **AI score > 70% after 3 iterations:** Manually rewrite the most problematic sections
- **Encoding error:** Ensure UTF-8 in the input file

## File structure
```
content-humanizer/
├── SKILL.md
├── scripts/
│   ├── detect_ai.py       # AI detection script (local, single-model)
│   └── verify_ai.py       # Unified free pipeline (L1 lingüística + L2 local
│                          #   + L3 HF Inference + L4 GPTZero), gate exit code
└── tests/
    └── test_detect.py     # Tests for detection script
```
