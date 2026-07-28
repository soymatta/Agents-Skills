---
name: math-notation
description: >
  Math notation rules for the inline parser of the generator.
  Use ONLY _text_ for italic (NEVER *text*), ^{...} for superscript,
  _{...} for subscript, and _X_{...} for italic+subscript combined.
  Activates when writing formulas, variables, and math expressions.
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

| Script | Args | Description |
|--------|------|-------------|
| `scripts/generate_outputs.py` | — | Generator that uses the inline parser (in citation-formatter) |

## Output format
- Correctly formatted Markdown using `_text_` for italics, `^{...}` for superscripts, `_{...}` for subscripts
- When processed by generate_outputs.py: produces `<em>`, `<sub>`, `<sup>` HTML tags

## Dependencies
No additional pip packages required for notation rules. Verification requires `generate_outputs.py` from the `citation-formatter` skill.

## Error handling
- **Underscore accidentally interpreted as italic:** Escape with `\_` before the underscore
- **Unicode superscript/subscript used by mistake:** Replace with `^{...}` or `_{...}` syntax
- **Verification fails:** Check that `generate_outputs.py` is accessible from project root

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

## 9. VERIFICATION

After writing formulas, verify with (requires `generate_outputs.py` in the path or at project root):

```bash
python -c "
from generate_outputs import split_inline, tokens_to_html
tests = ['gcd(_a_, _b_)', '_r_{0}', '_M_^{e}', '2^{255}']
for t in tests:
    html = tokens_to_html(split_inline(t))
    print(t, '->', html)
"
```

Every formula should produce HTML tags `<em>`, `<sub>`, `<sup>` as appropriate.
If a literal `_` appears in the output, the notation is incorrect.
