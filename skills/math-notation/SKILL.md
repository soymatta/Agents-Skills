---
name: math-notation
description: >-
  Math notation rules for the custom inline parser used by generate_outputs.py.
  CRITICAL RULE: Use ONLY _text_ for italic (NEVER *text*), ^{...} for superscript,
  _{...} for subscript, _X_{...} for italic+subscript, and _X_^{...} for italic+superscript.
  Bold uses **text** (standard Markdown). Escape literal underscores with \_.
  Use when: writing mathematical formulas, variables, expressions, equations in Markdown documents
  that will be processed by generate_outputs.py (PDF/DOCX generation).
  Triggers on: "math notation", "math formatting", "subscript", "superscript", "italic math",
  "math variables", "formula formatting", "inline math", "LaTeX simplificado",
  "notacion matematica", "subindice", "superindice", "variables en italica",
  "r_0", "x^{2}", "generador de PDF", "PDF formulas", "DOCX math",
  "generate_outputs", "inline parser", "math in markdown", "equation format",
  "scientific notation markdown", "academic formulas", "citation math variables".
  Referenced by academic-source-search and citation-formatter.
compatibility: Requires generate_outputs.py from citation-formatter skill for verification. Referenced by academic-source-search when formatting mathematical content in citations.
---

# Math Notation — Format Rules for the Inline Parser

The `generate_outputs.py` generator uses its own inline parser that **does not**
understand classic Markdown (`*text*` for italic). It only recognizes the
simplified LaTeX notation described below.

## When to use
- Writing mathematical formulas, variables, or expressions in Markdown documents
- Writing academic papers that will be processed by `generate_outputs.py`
- Any content where italic variables, subscripts, or superscripts are needed
- Generating PDF/DOCX output through the citation-formatter pipeline

## When NOT to use
- Writing pure Markdown for web display (not processed by generate_outputs.py)
- Content that will not be converted to PDF/DOCX
- Mathematical notation is not needed (plain text only)
- User is writing LaTeX natively (this skill is for the simplified inline parser only)

---

## 1. ITALIC — Use `_text_`, NEVER `*text*`

| Correct (`_..._`) | Incorrect (`*...*`) |
|--------------------|---------------------|
| `_a_ + _b_ = _c_` | `*a* + *b* = *c*` |
| `gcd(_a_, _b_)` | `gcd(*a*, *b*)` |
| `_Elements_` (book) | `*Elements*` |
| `_Communications of the ACM_` | `*Communications of the ACM*` |
| `_Enhanced Euclid Algorithm_` | `*Enhanced Euclid Algorithm*` |

**Rule:** Throughout the entire Markdown document, replace `*text*` with `_text_`.
This applies to:
- Math variables: `_x_`, `_y_`, `_n_`, `_e_`, `_d_`
- Book names, journal names, conference proceedings
- Algorithm names in foreign languages

---

## 2. SUPERSCRIPT — Use `^{...}`

| Expression | Notation |
|------------|----------|
| 5^13 | `5^{13}` |
| 2^255 | `2^{255}` |
| 26^37 | `26^{37}` |
| x^2 | `x^{2}` or better `_x_^{2}` |
| e^-1 | `e^{-1}` or better `_e_^{-1}` |
| log^2 n | `log^{2} _n_` |

Do NOT use Unicode superscript characters (², ³, ¹, ⁴, ⁵, ⁶, ⁷, ⁸, ⁹, ⁰, ⁻).
Always use `^{digits}`.

---

## 3. SUBSCRIPT — Use `_{...}`

| Expression | Notation |
|------------|----------|
| r_0 | `_r_{0}` |
| r_1 | `_r_{1}` |
| n_1024 | `_n_{1024}` |

Do NOT use Unicode subscript characters (₀, ₁, ₂, ₃, ₄, ₅, ₆, ₇, ₈, ₉, ₙ).
Always use `_{digits}`.

---

## 4. COMBINED: Italic + Subscript — Use `_X_{...}`

For an italic variable followed by a subscript:

| Expression | Notation | Explanation |
|------------|----------|-------------|
| r_0 | `_r_{0}` | Italic _r_ + subscript 0 |
| r_1 | `_r_{1}` | Italic _r_ + subscript 1 |
| r_n | `_r_{n}` | Italic _r_ + subscript _n_ |

The parser recognizes `_X_{...}` via the combined pattern (pattern 4)
and produces `<em>X</em><sub>...</sub>`.

---

## 5. COMBINED: Italic + Superscript — Use `_X_^{...}`

For an italic variable followed by a superscript:

| Expression | Notation | Explanation |
|------------|----------|-------------|
| M^e | `_M_^{e}` | Italic _M_ + superscript _e_ |
| C^d | `_C_^{d}` | Italic _C_ + superscript _d_ |
| e^-1 | `_e_^{-1}` | Italic _e_ + superscript -1 |

Do NOT use Unicode superscript characters (ᵉ, ᵈ, ⁻, etc.).
Always use `^{...}`.

---

## 6. BOLD — Use `**...**`

Bold DOES use classic Markdown `**...**`:

| Expression | Notation |
|------------|----------|
| **Step 1:** | `**Step 1:**` |
| **Summary** | `**Summary**` |
| **Keywords:** | `**Keywords:**` |

The parser recognizes `**...**` as bold (pattern 3).

---

## 7. SUMMARY: Quick conversion table

| Concept | CORRECT NOTATION | INCORRECT NOTATION |
|---------|------------------|--------------------|
| Simple italic | `_a_ + _b_` | `*a* + *b*` |
| Superscript | `2^{256}` | `2²⁵⁶` |
| Subscript | `_r_{0}` | `_r_₀` or `r₀` |
| Italic + sub | `_r_{0}` | `*r*₀` |
| Italic + sup | `_M_^{e}` | `*M*ᵉ` |
| Bold | `**Title**` | `__Title__` |

---

## 8. Escaping literal underscores

If you need a literal underscore that should NOT be interpreted as italic (e.g., file_names, variables_in code), use a backslash before the underscore:

| Context | Notation |
|---------|----------|
| File name | `file\_name.txt` |
| Code variable | `my\_var\_name` |
| URL with underscore | `https://example.com/page\_name` |

The parser will always try to interpret `_..._` as italic. Escape literal underscores with `\_`.

---

## Scripts

This skill has **no scripts of its own** — the verification snippet below runs
`generate_outputs.py`, which lives in `citation-formatter/scripts/`:

| Script (in citation-formatter) | Purpose |
|--------|------|
| `skills/citation-formatter/scripts/generate_outputs.py` | Inline parser used to verify notation |
| `skills/citation-formatter/scripts/generate_docx.py` | IEEE DOCX generator that consumes this notation in documents (`_text_`, `^{...}`, `_{...}`) |
| `skills/citation-formatter/scripts/md_to_tex.py` | MD→LaTeX converter that maps the same tokens to `\emph`, `\textbf`, `$^{...}`, `$_{...}` |

## Output format
- Correctly formatted Markdown using `_text_` for italics, `^{...}` for superscripts, `_{...}` for subscripts
- When processed by generate_outputs.py: produces `<em>`, `<sub>`, `<sup>` HTML tags

## Dependencies
No additional pip packages required for notation rules. Verification requires `generate_outputs.py` from the `citation-formatter` skill.

## Error handling
- **Underscore accidentally interpreted as italic:** Escape with `\_` before the underscore
- **Unicode superscript/subscript used by mistake:** Replace with `^{...}` or `_{...}` syntax
- **Verification fails:** Ensure `sys.path` includes `skills/citation-formatter/scripts` (see 9b), then re-run
- **Literal `_` appears in parser output:** the notation folded incorrectly — escape or restructure per the tables

## File structure
```
math-notation/
└── SKILL.md
```

## Restrictions
- Do NOT use `*text*` for italic — use `_text_`
- Do NOT use Unicode superscript/subscript characters — use `^{...}` / `_{...}`
- Do NOT use `__text__` for bold — use `**text**`
- Do NOT use classic Markdown `*text*` — the parser does not recognize it as italic
- **Downstream no-touch contract:** do NOT "clean up" `_…_`, `^{…}`, or `_{…}`
  written by this skill (e.g. `_r_{0}` → `r₀`). They are intentional parser
  notation, not style clutter. Downstream passes (e.g. content-humanizer) must
  leave them untouched.

## 9. VERIFICATION

After writing formulas, lint the document for violations, then verify the parser
output. Both steps are required.

### 9a. Lint for violations
Scan the target document for the common mistakes and fix them before verifying:

```bash
# Find classic-markdown italic (should be `_text_`)
grep -nE '\*[^*]+\*' doc.md
# Find Unicode super/subscripts (should be ^{...} / _{...})
grep -nE '[²³¹⁴⁵⁶⁷⁸⁹⁰⁻₀₁₂₃₄₅₆₇₈₉ₙᵉᵈ]' doc.md
```

Replace each hit according to the tables above.

### 9b. Verify with the parser
`generate_outputs.py` lives in the `citation-formatter` skill. Run the check from
the repo root with the correct module path (this is what works reliably on
Windows and Linux):

```bash
python -c "
import sys; sys.path.insert(0, 'skills/citation-formatter/scripts')
from generate_outputs import split_inline, tokens_to_html
tests = ['gcd(_a_, _b_)', '_r_{0}', '_M_^{e}', '2^{255}', '**bold**']
for t in tests:
    html = tokens_to_html(split_inline(t))
    print(t, '->', html)
"
```

Every formula should produce HTML tags `<em>`, `<sub>`, `<sup>` as appropriate.
If a literal `_` appears in the output, the notation is incorrect.

> **Note on the self-check mismatch:** this skill's examples say `gcd(...)` but
> the generator's own built-in self-test uses `mcd(...)` (Spanish). Both exercise
> the same parser path; use the literal `mcd(_a_, _b_)` only if you run the
> generator's docstring example. In your own documents use whichever is correct
> for the content.

### 9c. Whitespace ambiguity in `_..._`
`_text_` only becomes *italic* when the underscores telescope cleanly
(`_x_` with no internal whitespace on both sides). Treat `_word with spaces_`
as ambiguous: the parser's `ITALIC` pattern does not match internal spaces, so
it may fall through to raw text/other tokens. If you need italics around a
multi-word phrase, double-check the parser output in 9b rather than assuming it
works.
