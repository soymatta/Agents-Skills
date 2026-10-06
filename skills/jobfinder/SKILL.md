---
name: jobfinder
description: >-
  Find jobs, search employment, match your profile/CV to listings, get recommendations, generate cover
  letters and CV PDFs, track applications, run skill-gap analysis, and prep interviews. Searches job boards
  (RemoteOK, LinkedIn, Indeed, Glassdoor), ATS APIs (Greenhouse, Lever, Ashby), and company career pages.
  ALWAYS ask for profile data before searching. Use when the user wants to find jobs, assess job offers,
  match a CV, or prepare for an interview. First-party scripts alternative to the `ai-job-search`
  framework (third-party) and the conversational `jobfinder` agent: use this skill for scripted
  scoring/CV pipelines, the agent for guided back-and-forth. Triggers: "find jobs", "job search", "busco trabajo", "ofertas
  de empleo", "cv", "cover letter", "carta de presentacion", "interview prep", "aplicar empleo", "generate CV".
---

# JobFinder

Analyzes the user's professional profile, searches multiple job boards, ATS APIs,
AND company career pages via web search, calculates match percentage for each
vacancy using a 5-dimension evaluation framework, generates cover letters,
tracks applications, and produces professional CVs in PDF format.

## When to use
- User wants to find jobs or search for employment
- Keywords: "find jobs", "job search", "job offers", "cv", "resume", "linkedin profile", "employment", "vacancy", "position", "match", "salary", "github projects", "portfolio", "improve profile", "cover letter", "interview prep"
- Match profile/CV to job listings
- Generate professional CVs and cover letters
- Track job applications

## When NOT to use
- User wants to negotiate salary
- Non-job-search contexts (freelance, entrepreneurship)
- User hasn't provided profile data yet (ask first)

## Workflow

### Step 1: Profile Collection (progressive)

Collect the profile **progressively** — start with the 3 core essentials, then
expand only as needed. Do not dump 18 questions up front; ask in waves.

#### Core (3, required to start)
```
1. What role/title and seniority are you targeting?
2. Location + work mode: city/country, and remote / on-site / hybrid / no preference
3. Do you have a CV file? (If yes, parse it with parse_cv.py; fields fill in below)
```

#### Expand (ask adaptively, accept "skip" or infer-from-CV where safe)
```
4. Salary expectation — NEITHER assume NOR infer from the CV; if not given, mark "Not published"
5. Employment type: full-time, part-time, contract, freelance
6. Years of work experience in your field
7. Languages you speak and level (e.g., "Spanish: Native", "English: B1/B2")
8. Specific companies you're targeting
9. Industries that interest you
10. Deal-breakers
11. Career goals
12. Name/contact, current role & company, skills, education, current location (from CV or ask)
```

**The one thing NEVER to skip or infer:** salary and language level (used by the
gates). Everything else can be progressively filled in.

If the user provides a CV file, parse it using `scripts/parse_cv.py`:
```bash
python scripts/parse_cv.py /path/to/cv.pdf
```

Store the profile in structured format (see `templates/profile.json`).

### Step 2: Pre-Scoring Gates

Before scoring, run two gates (from ai-job-search methodology):

#### Eligibility Gate
Check if the posting has citizenship/visa/security clearance requirements that
would exclude the user. Hard filter — not a scoring dimension.

#### Language Gate
Check if the posting requires languages the user hasn't declared.
- Undeclared language → **FAIL** (don't score)
- Language declared but level may be insufficient → **FLAG** (score but note)

### Step 3: Job Search — Multi-Source Strategy

Search across THREE source categories for maximum coverage.

> **Scope note:** this is the only frontier where the script truly automates.
> Implemented scrapers: `indeed`, `linkedin`, `computrabajo`, `glassdoor`, `remoteok`
> (5 portals). **Implemented ATS APIs:** `greenhouse`, `lever`, `ashby`. Everything
> else — ZipRecruiter, Google Jobs, Bumeran, Jooble, Workable, etc. — is **not**
> implemented; do not claim or invoke handlers that do not exist. Use websearch
> (3c) for those instead.

#### 3a. Job Boards (scraping)

```bash
python scripts/search_jobs.py \
  --keywords "python,javascript,backend,frontend" \
  --location "{{LOCATION}}" \
  --experience {{YEARS}} \
  --max-results 50 \
  --sites remoteok linkedin indeed glassdoor\
  --output results.json
```

| Board | Type | Status |
|-------|------|--------|
| RemoteOK | Scraping | Implemented (direct JSON API) |
| LinkedIn Jobs | Scraping | Implemented (partial, login limits) |
| Indeed | Scraping | Implemented |
| Glassdoor | Scraping | Implemented |
| Computrabajo | Scraping | Implemented |

#### 3b. ATS APIs (direct, higher quality)

Pass ATS company boards via `--ats ats:company`:

```bash
python scripts/search_jobs.py \
  --keywords "python" --location "Remote" \
  --ats greenhouse:stripe lever:acme ashby:notion \
  --output results.json
```

| API | Board slug syntax | Endpoint |
|-----|-------------------|----------|
| Greenhouse | `greenhouse:{company}` | `GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs` |
| Lever | `lever:{company}` | `GET https://api.lever.co/v0/postings/{company}` |
| Ashby | `ashby:{company}` | `GET https://api.ashbyhq.com/posting-api/job-board/{company}` |

#### 3c. Web Search — Company Career Pages

```bash
websearch('"{{COMPANY}}" careers hiring {{ROLE}}', numResults=8)
websearch('site:{{COMPANY_DOMAIN}}/careers {{ROLE}}', numResults=5)
```

Save the results to a JSON file and pass via `--websearch-json` so they get
normalized into the same unified job format and deduplicated.

### Step 4: Match Scoring (5-Dimension Framework)

For each vacancy, calculate a match score (0-100%) using `scripts/score_match.py`:

```bash
python scripts/score_match.py --profile profile.json --jobs results.json
```

**Scoring dimensions (ai-job-search methodology):**

| Dimension | Weight | Score Range | Description |
|-----------|--------|-------------|-------------|
| Technical Skills Match | 30% | 0-100 | % of required skills the user has |
| Experience Match | 25% | 0-100 | Years and relevance of experience |
| Behavioral/Culture Fit | 15% | 0-100 | Company culture alignment |
| Location & Logistics | Pass/Fail | Binary | Remote/on-site compatibility |
| Career Alignment | 30% | 0-100 | How well role matches career goals |

**Thresholds:**
- **Strong Fit** (75+): Definitely apply
- **Good Fit** (60-74): Apply, address gaps in cover letter
- **Moderate Fit** (45-59): Consider carefully
- **Weak Fit** (30-44): Probably skip
- **Poor Fit** (<30): Skip

**Experience filter:** Vacancies requiring more years than the user has are marked "Not viable".

### Step 5: Skill Gap Analysis

For comprehensive gap analysis across all scored jobs:

```bash
python scripts/gap_analysis.py --profile profile.json --scored scored.json
```

This generates:
- Skill frequency analysis across all jobs
- Priority ranking (high/medium/low)
- Learning suggestions for each gap

### Step 6: Cover Letter Generation

Generate a tailored cover letter for each Strong/Good fit job:

```bash
python scripts/generate_cover_letter.py \
  --profile profile.json \
  --job job_data.json \
  --skills "python,fastapi,postgresql" \
  --output cover_letter.md
```

**Cover letter rules:**
- Forward-looking: focus on tasks you'll solve, not just past duties
- Company-specific: reference their mission/values/projects
- No em-dashes, no cliches, no generic buzzwords
- 250-300 words maximum

### Step 7: CV PDF Generation

**IMPORTANT:** Always generate CVs in PDF format using `scripts/generate_cv_pdf.py`. NEVER generate CVs in Markdown or HTML.

Create TWO separate JSON files (one per language) with CV data and run:

```bash
python scripts/generate_cv_pdf.py --input cv_data.json --output ./output
```

**PDF verification loop (do not skip):** after generating, verify the PDF actually
opened and rendered the expected fields before declaring success:
1. Re-read the output PDF text (e.g. `python -c "import pdfplumber; ..."`) and confirm
   name, title, and a couple of key skills/roles appear.
2. Confirm the ATS-critical fields survived (section headings, no missing blocks).
3. If a field is missing or the layout is broken, fix the input JSON and regenerate —
   never deliver an unverified PDF.

**Required JSON format:**
```json
{
    "name": "{{FULL_NAME}}",
    "title": "{{PROFESSIONAL_TITLE}}",
    "contact": {
        "email": "{{EMAIL}}",
        "phone": "{{PHONE}}",
        "linkedin": "{{LINKEDIN_URL}}",
        "github": "{{GITHUB_URL}}",
        "location": "{{CITY, COUNTRY}}",
        "website": "{{WEBSITE_URL}}"
    },
    "profile": "{{Brief professional summary}}",
    "skills": {
        "{{Category}}": "{{Skill1, Skill2, Skill3}}"
    },
    "experience": [
        {
            "company": "{{COMPANY}}",
            "role": "{{ROLE}}",
            "period": "{{MMM YYYY - MMM YYYY}}",
            "bullets": ["{{Achievement 1}}", "{{Achievement 2}}"]
        }
    ],
    "projects": [
        {
            "name": "{{PROJECT_NAME}}",
            "role": "{{ROLE}}",
            "bullets": ["{{Description}}"]
        }
    ],
    "education": [
        {
            "institution": "{{INSTITUTION}}",
            "degree": "{{DEGREE}}",
            "period": "{{YYYY - YYYY}}",
            "details": "{{Additional details}}"
        }
    ],
    "languages": {
        "{{Language}}": "{{Level}}"
    }
}
```

### Step 8: Application Tracking

Track all applications using `scripts/track_application.py`:

```bash
# Add application
python scripts/track_application.py add \
  --company "Acme Corp" \
  --role "Backend Developer" \
  --source "https://..." \
  --cv "cv_acme_backend.pdf" \
  --cover-letter "cover_acme_backend.md"

# Update status
python scripts/track_application.py update \
  --company "Acme Corp" \
  --role "Backend Developer" \
  --status "interview" \
  --notes "Phone screen scheduled"

# List all applications
python scripts/track_application.py list
python scripts/track_application.py list --status "applied"
```

**Statuses:** applied, interview, offer, rejected, withdrawn

### Step 9: Report Generation

Generate Markdown and HTML reports:

```bash
python scripts/generate_report.py profile.json scored.json projects.json job-report
```

`projects.json` is **optional** — the generator defaults to an empty list when the
file is absent (no crash). Pass it only if you have project data (e.g. from
`suggest_projects.py`); otherwise you can omit it or pass any existing JSON.

This generates:
- `job-report.md` — Markdown report with 5D scores
- `job-report.html` — Clean, minimal HTML report

**Auto-cleanup:** Temporary files are automatically deleted after report generation.

### Step 10: Interview Preparation

For Strong/Good fit jobs, prepare interview answers:

- Review the job's key requirements and matched/missing skills
- Prepare STAR-format answers for likely questions
- Draft questions the candidate should ask the interviewer
- Reference `skills/ai-job-search/reference/07-interview-prep.md` for framework

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/parse_cv.py` | Parse CV files (PDF, DOCX, TXT) to JSON |
| `scripts/search_jobs.py` | Search job boards + ATS APIs + web search |
| `scripts/score_match.py` | Calculate 5D match scores with gates |
| `scripts/gap_analysis.py` | Analyze skill gaps across all jobs |
| `scripts/generate_cover_letter.py` | Generate tailored cover letters |
| `scripts/suggest_projects.py` | Suggest GitHub projects (deprecated, use gap_analysis) |
| `scripts/generate_report.py` | Generate MD/HTML reports |
| `scripts/generate_cv_pdf.py` | Generate professional CV PDFs |
| `scripts/md_to_json.py` | Convert Markdown CV to JSON |
| `scripts/track_application.py` | Track applications in CSV |

## Dependencies

```bash
pip install requests beautifulsoup4 fpdf2 pdfplumber python-docx
```

- `pdfplumber` + `python-docx` are needed by `scripts/parse_cv.py` for PDF/DOCX
  CV parsing.
- `generate_cv_pdf.py` uses `fpdf2`.
- All job-search scripts use `requests` + `beautifulsoup4`.

## Error handling
- **Portal blocks scraping:** Reduce frequency, try another portal
- **CV parsing fails:** Ask user for alternative format (TXT, DOCX)
- **ATS API not responding:** Continue with remaining scraping portals
- **ATS site slug unknown:** Verify the company slug on the ATS board page, or
  fall back to websearch for that company
- **No results:** Broaden location, reduce filters, search more portals and company career pages
- **Encoding issues:** Force UTF-8 on all input files

## Restrictions
- Do NOT fabricate salary when not available — mark "Not published"
- Do NOT omit the direct link to the job posting
- Do NOT generate CVs in Markdown or HTML — always PDF
- Do NOT assume user profile — always ask
- Do NOT exceed portal rate limits
- Do NOT apply to jobs — only search, score, and report
