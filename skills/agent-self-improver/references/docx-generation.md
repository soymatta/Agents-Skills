# Reference: python-docx Common Issue Patterns

Domain-specific checklist for reviewing python-docx / document-generator output.
Load this reference only when the session involves document generation (DOCX,
PDF, academic formatting). For generic agent feedback, work from the main
SKILL.md instead.

## Common Issue Patterns — Document Generation

| Pattern | Root Cause | Fix |
|---------|-----------|-----|
| Wrong font size | Copied wrong standard defaults | Create a FORMAT_SPEC dict per standard |
| Wrong line spacing | Same as above | Same as above |
| Enum typo (JUSTIFIED) | python-docx uses JUSTIFY | Search-replace in script |
| Hyperlinks broken | Used r:id for internal links | Use `w:anchor` attribute |
| Bookmarks wrong position | Called add_bookmark before runs | Call AFTER all runs added |
| Headings not detected | Hardcoded English patterns | Add i18n regex patterns |
| Title not extracted | Only checked frontmatter | Fallback to first `#` heading |
| Missing columns | Not set in section properties | Use set_two_columns() helper |
| No page numbers | Footer not configured | Add PAGE field to footer |
| Encoding issues | Console output encoding | Use UTF-8, ignore console display |

## XML Structure

| Pattern | Root Cause | Fix |
|---------|-----------|-----|
| Namespace prefix wrong | Missing `qn()` wrapper | Always use `qn("w:tagname")` |
| Element not found | Wrong namespace | Check nsmap, use `findall('.//{ns}tag')` |
| Runs not styled | Font set on paragraph not run | Set font on each run individually |
| Style not applied | Style name mismatch | Check `doc.styles` names |

## IEEE / APA formatting caveats

- IEEE body is 10pt, single-spaced, 2-column; APA body is 12pt, double-spaced,
  1-column. Proof every generated doc against the standard's spec, not against
  a previous document.
- Internal hyperlinks must use `hyperlink.set(qn('w:anchor'), bookmark_name)`
  after all runs are added.
- Verify the `WD_ALIGN_PARAGRAPH` enum: it is `JUSTIFY`, not `JUSTIFIED`.
