---
name: academic-source-search
description: Searches for verified scientific sources in academic databases. Filters by quality, extracts metadata, and generates preliminary citations.
compatibility: Produces metadata consumed by citation-formatter for formatting references. No skills depend on this one.
---

# Academic Source Search

Systematic search of scientific literature to support academic work.

## When to use
- Starting a new academic document
- Need sources to support an unsubstantiated claim
- Expanding the theoretical framework / state of the art section
- Verifying the quality of existing sources

## When NOT to use
- Sections already have complete bibliographic support
- User needs to format citations (use `citation-formatter`)
- Looking for non-academic information (news, general blogs)
- No clarity on the research topic

## Source tiers (quality classification)
| Tier | Type | Priority |
|------|------|----------|
| 1 | Peer-reviewed journal (Q1-Q2) | Highest |
| 2 | Conference proceedings, academic books | High |
| 3 | Preprints (arXiv, SSRN), doctoral theses | Medium |
| 4 | Government reports, patents | Low |
| 5 | Popular media, blogs, Wikipedia (references only) | Do not use directly |

**Integration:** Once metadata is extracted, use `citation-formatter` to format citations according to the selected style.

---

## Databases by Priority

| Priority | Database | Access | URL |
|----------|----------|--------|-----|
| 1 | Google Scholar | Free | https://scholar.google.com |
| 2 | arXiv | Free Open Access | https://arxiv.org |
| 3 | PubMed / PMC | Free | https://pubmed.ncbi.nlm.nih.gov |
| 4 | SciELO | Free LatAm | https://scielo.org |
| 5 | Redalyc | Free LatAm | https://www.redalyc.org |
| 6 | Dialnet | Free | https://dialnet.unirioja.es |
| 7 | IEEE Xplore | Free abstracts | https://ieeexplore.ieee.org |
| 8 | Scopus | Free abstracts | https://www.scopus.com |
| 9 | Web of Science | Free abstracts | https://www.webofscience.com |
| 10 | JSTOR | Limited free reading | https://www.jstor.org |
| 11 | DOAJ | Free Open Access | https://doaj.org |
| 12 | Open Access Theses | Free theses | https://oatd.org |
| 13 | PubMed Books | Free academic books | https://www.ncbi.nlm.nih.gov/books |
| 14 | Google Books Preview | Fragments | https://books.google.com |

---

## Search Formulation

### Boolean operators (work in Scholar, Scopus, WoS)
```
"climate change" AND "renewable energy"              → both exact terms
("machine learning" OR "deep learning") AND "ERP"   → either term + ERP
"climate change" -"climate change denial"            → exclude term
intitle:"neural networks"                            → in title only
author:"name"                                        → by author
source:"Nature"                                      → by journal
```

### Recommended filters
- Year range: use recent years (e.g., `2020..2026` or `2022..2026` as needed)
- Type: `review`, `journal article`, `conference`
- Sort by: relevance, citations, date

### Strategy
1. Broad search with key terms → identify 10-20 candidates
2. Read abstract of each → select 5-10 relevant ones
3. Search citing articles and articles cited by selected ones (snowball)
4. Extract DOI, authors, year, journal, abstract, keywords, citation count

---

## Metadata Extraction

For each selected source, extract:

```yaml
title: "Full title"
authors: ["Last, F.; Last, F."]
year: 2024
journal: "Journal Name"
volume: "12"
issue: "3"
pages: "45-67"
doi: "10.xxxx/xxxxx"
url: "https://doi.org/10.xxxx/xxxxx"
type: "journal" | "conference" | "book" | "thesis" | "preprint"
abstract: "Abstract text"
keywords: ["word1", "word2"]
citations_count: 150
```

---

## Verification

- DOI: verify it resolves at https://doi.org/XXXX
- Access: try downloading PDF or reading abstract via `webfetch`
- Date: confirm it matches the actual publication
- Authors: verify institutional affiliation when possible
- Journal: verify indexing (JCR, Scopus, Latindex)

---

## Output format

At the end of the search, deliver a summary table:

| # | Authors | Year | Title | Source | DOI/URL | Tier | Verified |
|---|---------|------|-------|--------|---------|------|----------|
| 1 | Smith, J. | 2024 | "Title" | Nature | doi:... | 1 | [x] |
| 2 | ... | ... | ... | ... | ... | ... | ... |

---

## Dependencies
No additional pip packages required. Uses built-in `webfetch` and `websearch` tools.

## Error handling

- **DOI does not resolve:** search by full title in Google Scholar or CrossRef
- **Database inaccessible:** try the next one in the priority list
- **Paywall:** read abstract, search for preprint on arXiv, ResearchGate, or author version
- **No results:** reformulate query with synonyms, reduce filters, expand year range
- **Broken link in existing reference:** search for alternative DOI or URL on archive.org

## File structure
```
academic-source-search/
└── SKILL.md
```

## Restrictions
- Do not use sources without DOI or verifiable URL
- Do not fabricate metadata
- Do not include sources without reading at least the abstract
- Do not prioritize quantity over quality
- Do not use Tier 5 sources as direct support
