---
name: academic-source-search
description: >-
  Searches for verified scientific sources in academic databases (Google Scholar, arXiv, PubMed, SciELO, IEEE,
  Scopus, Web of Science), filters by quality tier, extracts full metadata (DOI, authors, abstract, citations),
  and generates preliminary citations. Use when the user needs academic papers, scientific references, a
  literature review, state of the art, fuentes/referencias academicas, or source verification. ALWAYS run
  BEFORE citation-formatter. Triggers: "find papers", "search articles", "academic sources", "buscar articulos",
  "marco teorico", "DOI lookup", "peer-reviewed sources".
compatibility: Produces metadata consumed by citation-formatter for formatting references. No skills depend on this one.
---

# Academic Source Search

Systematic search of scientific literature to support academic work.

## When to use
- Starting a new academic document
- Need sources to support an unsubstantiated claim
- Expanding the theoretical framework / state of the art section
- Verifying the quality of existing sources
- **Keywords:** "find papers", "search articles", "academic sources", "scientific references", "necesito fuentes", "buscar articulos", "literatura academica", "scholar search", "find studies", "look up research", "papers on", "DOI lookup", "journal articles", "peer-reviewed sources", "preprint search", "bibliografia", "marco teorico", "articulos cientificos", "systematic review", "snowball search", "citation tracking"

## When NOT to use
- Sections already have complete bibliographic support
- User needs to format citations (use `citation-formatter`)
- Looking for non-academic information (news, general blogs)
- No clarity on the research topic

## First step — mandatory clarifying preamble (one round)
Before any search, confirm with the user:
- **(a)** the exact research question / claim to support
- **(b)** the target section (marco teórico, state of the art, etc.)
- **(c)** the year range (e.g. `2022..2026`)
- **(d)** the language of the sources (e.g. Spanish, English, both)
- **(e)** the minimum acceptable tier (default Tier 1-2, allow preprints only if needed)

Do not search until (a) and (d) are answered. This prevents wasted searches on
the wrong framing and keeps the quota (below) focused on real claims.

## Source tiers (quality classification)
| Tier | Type | Priority |
|------|------|----------|
| 1 | Peer-reviewed journal (Q1-Q2) | Highest |
| 2 | Conference proceedings, academic books | High |
| 3 | Preprints (arXiv, SSRN), doctoral theses | Medium |
| 4 | Government reports, patents | Low |
| 5 | Popular media, blogs, Wikipedia (references only) | Do not use directly |

**Integration:** Once metadata is extracted, persist it to `sources.yaml` (see
[Output format](#output-format)) and run `citation-formatter` — either its
`scripts/references.py` (renders the references list and in-text pairs) or the
document generator in `scripts/generate_outputs.py`.

---

## Databases by Priority

**Prefer free programmatic APIs** (they are scrape-safe and return structured
metadata); treat Google Scholar as **manual verification only** (it is
CAPTCHA-protected and not reliably scrapable).

| Priority | Database | Access | How to query | URL |
|----------|----------|--------|--------------|-----|
| 1 | **CrossRef** | Free REST API | `REST https://api.crossref.org/works?query.bibliographic=...` (best metadata/DOI) | https://api.crossref.org |
| 2 | **arXiv** | Free API | `https://export.arxiv.org/api/query?search_query=...` (Atom XML, good for preprints) | https://arxiv.org |
| 3 | **PubMed / PMC** | Free E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?...` + `efetch` | https://pubmed.ncbi.nlm.nih.gov |
| 4 | SciELO | Free API | `https://analytics.scielo.org/w/accesses` / OAI-PMH | https://scielo.org |
| 5 | Redalyc | Free LatAm | web search | https://www.redalyc.org |
| 6 | Dialnet | Free | web search | https://dialnet.unirioja.es |
| 7 | IEEE Xplore | Free abstracts | web search (some metadata via DOI) | https://ieeexplore.ieee.org |
| 8 | Scopus | Free abstracts | web search (login may be required) | https://www.scopus.com |
| 9 | Web of Science | Free abstracts | web search | https://www.webofscience.com |
| 10 | JSTOR | Limited free reading | web search | https://www.jstor.org |
| 11 | DOAJ | Free Open Access | web search | https://doaj.org |
| 12 | Open Access Theses | Free theses | web search | https://oatd.org |
| 13 | PubMed Books | Free academic books | web search | https://www.ncbi.nlm.nih.gov/books |
| 14 | Google Books Preview | Fragments | web search | https://books.google.com |
| 15 | **Google Scholar** | Manual only | verify an already-found source (CAPTCHA) | https://scholar.google.com |

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
1. Broad search with key terms (via CrossRef/arXiv/PubMed APIs) → identify 10-20 candidates
2. Read abstract of each → select 5-10 relevant ones
3. Snowball: search citing articles and articles cited by selected ones
4. **Deduplicate by DOI** (and by normalized title when DOI missing); keep the
   highest-tier, most-cited copy of any duplicate.
5. **Per-claim quota:** allocate a budget of sources per claim/section (default
   ~5-10; the user can raise it). Stop expanding a claim once its quota is met —
   do not pad a claim with sources that only loosely support it.
6. Extract DOI, authors, year, journal, abstract, keywords, citation count

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
tier: 1
```

> **Schema contract:** `citation-formatter/scripts/references.py` validates this
> schema (required: `title`; rejects any entry that cannot be rendered). Keep
> the field names and formats exactly as shown above.

---

## Verification

- DOI: verify it resolves at https://doi.org/XXXX
- Access: try downloading PDF or reading abstract via `webfetch`
- Date: confirm it matches the actual publication
- Authors: verify institutional affiliation when possible
- Journal: verify indexing (JCR, Scopus, Latindex)

---

## Output format

Two artifacts are produced:

### 1. `sources.yaml` (machine-readable, REQUIRED)
Persist **every** selected source to a `sources.yaml` file using the metadata
schema above. This is the contract that `citation-formatter` consumes — do not
skip it. Example:

```yaml
- title: "Full title"
  authors: ["Last, F.; Last, F."]
  year: 2024
  journal: "Journal Name"
  volume: "12"
  issue: "3"
  pages: "45-67"
  doi: "10.xxxx/xxxxx"
  url: "https://doi.org/10.xxxx/xxxxx"
  type: "journal"
  abstract: "Abstract text"
  keywords: ["word1", "word2"]
  citations_count: 150
  tier: 1
```

### 2. Human summary table (optional, for the user)
Deliver a summary table at the end:

| # | Authors | Year | Title | Source | DOI/URL | Tier | Verified |
|---|---------|------|-------|--------|---------|------|----------|
| 1 | Smith, J. | 2024 | "Title" | Nature | doi:... | 1 | [x] |
| 2 | ... | ... | ... | ... | ... | ... | ... |

---

## Dependencies
No additional pip packages required. Uses built-in `webfetch` and `websearch` tools.

## Error handling

- **DOI does not resolve:** search by full title in the CrossRef API, then verify
- **CrossRef `select=` param returns 400:** the CrossRef REST API may reject the
  `select` parameter on the `/works/{doi}` endpoint. Fall back to the full
  `/works/{doi}` response (the JSON is larger; it can be parsed programmatically)
  rather than retrying the same request
- **Large Crossref JSON truncated in a tool call:** the response can exceed the
  output budget. If the tool truncates it, save it to a temp file and parse with a
  script (e.g. PowerShell `Invoke-RestMethod` + `ConvertFrom-Json`); do not grep a
  single-line JSON blob
- **Database inaccessible:** try the next one in the priority list
- **Paywall:** read abstract, search for preprint on arXiv, ResearchGate, or author version
- **No results:** reformulate query with synonyms, reduce filters, expand year range
- **Broken link in existing reference:** search for alternative DOI or URL on archive.org
- **Google Scholar CAPTCHA:** treat Scholar as manual verification only; use CrossRef/arXiv/PubMed APIs for the actual search

## Verifying existing references (references audit)

When auditing a reference list that already exists (not a new search), apply the
same rigor as a fresh search:

1. **Resolve every DOI/URL** via `https://api.crossref.org/works/{doi}` (or arXiv
   `export.arxiv.org/api/query?id_list=...`). Confirm title, authors, journal,
   volume, issue, pages/article number, and year against the paper's entry —
   fix any fields that differ, never assume the paper entry is correct.
2. **Deduplicate by DOI** (and by normalized title when DOI is missing). If the
   same source appears twice (e.g. one entry with DOI and a second entry that is
   the web-URL version of the same article), merge them into a single reference
   and update every in-text citation.
3. **Check for fabricated metadata:** authors who are not in the Crossref/arXiv
   record, placeholder group names ("Research Team"), or journal names that are
   actually the publisher or a dead DOI page are red flags — correct them from
   the authoritative record.
4. **Ensure every reference is cited in the text and every in-text citation has
   an entry** (order of appearance for IEEE/Vancouver, alphabetical for APA).
   Either add a supporting sentence or drop the orphan entry.
5. **Confirm active links** before delivery — a reference without a verifiable active link must not be shipped (matches the skill's Restrictions).

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
