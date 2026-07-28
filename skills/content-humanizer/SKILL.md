---
name: content-humanizer
description: >
  Final document revision to reduce AI-detectable patterns
  (Turnitin, GPTZero, Originality). Adjusts structure, vocabulary, and flow
  while maintaining academic rigor. Run ONLY at the end, when content
  is complete and referenced. Includes detection script to verify
  the text passes as human-written.
---

# Content Humanizer

Final humanization pass. Run ONLY when the document is complete, reviewed,
and all references verified.

**Do not alter:** data, citations, references, academic structure, metadata.

## When to use
- Final pass before submitting academic documents
- After all content, citations, and references are finalized
- Keywords: "humanize", "anti-AI", "Turnitin", "GPTZero", "detect AI", "final pass"
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

### 1.8 Active voice > passive

Max 20% of sentences in passive (40% in methodology).

### 1.9 Controlled imperfections

1-2 per every 3 sections: sentence starting with "And"/"But",
shorter/longer paragraph, anaphora, non-ideal connector.

---

## 2. DETECT — Verify with detect_ai.py

After humanizing the document, run the local detector to confirm
the text passes as human:

```bash
# Install dependencies (once)
pip install transformers torch

# Test the complete document (run from project root)
python scripts/detect_ai.py --file document.md --verbose
```

### Result interpretation

```
  AI:   12.3%            ← probability of being AI (should be <50%)
  Human: 87.7%           ← probability of being human
  Verdict: PASS           ← PASS or DETECTED
```

| Result | Meaning | Action |
|--------|---------|--------|
| AI < 30% | Human text | Ready. Submit. |
| AI 30-50% | Ambiguous text | Review flagged sections, apply more variation |
| AI > 50% | Detected text | Repeat humanization on sections with highest score |
| AI > 70% | Highly detectable | Rewrite from scratch using this skill's techniques |

### Section-level analysis (--verbose)

The detector flags which sections have higher AI probability.
Apply additional humanization specifically to those sections
and re-run the detector.

### If transformers cannot be installed

Use web detectors via `webfetch`:
1. Send text to https://www.zerogpt.com (free, no API key)
2. Send to https://gptzero.me (limited free)
3. Compare results between both
4. If both say "AI", go back to step 1 with more techniques

---

## 3. ITERATE — Verification loop

```
while True:
    humanize(document)
    result = detect(document)
    if result.verdict == "PASS":
        break
    else:
        humanize(result.flagged_sections)
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
- [ ] **Run detect_ai.py → Verdict: PASS**

---

## Dependencies
```bash
pip install transformers torch
```
For web-based detection: no additional packages (uses webfetch tool).

## Restrictions

- **DO NOT** modify data, figures, dates, names
- **DO NOT** alter direct quotes or their formatting
- **DO NOT** remove or modify references
- **DO NOT** change academic structure (sections, headers)
- **DO NOT** add new information
- **DO NOT** remove relevant information
- **DO NOT** reduce academic rigor or technical precision

## Error handling
- **detect_ai.py not found:** Look in `scripts/detect_ai.py` relative to the skill
- **transformers not installed:** Use web detectors via webfetch (ZeroGPT, GPTZero)
- **Document too long:** Process by sections, humanize each separately
- **AI score > 70% after 3 iterations:** Manually rewrite the most problematic sections
- **Encoding error:** Ensure UTF-8 in the input file

## File structure
```
content-humanizer/
├── SKILL.md
├── scripts/
│   └── detect_ai.py       # AI detection script (local)
└── tests/
    └── test_detect.py     # Tests for detection script
```
