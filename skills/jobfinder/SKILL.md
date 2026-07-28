---
name: jobfinder
description: >-
  Use when the user wants to find jobs, search for employment, analyze job offers,
  match their profile/CV to job listings, or get job recommendations. Triggers on
  keywords like "find jobs", "job search", "job offers", "cv", "resume",
  "linkedin profile", "employment", "vacancy", "position", "match",
  "salary", "github projects", "portfolio", "improve profile".
  ALWAYS ask the user for their profile data before searching.
  This skill reads CVs/profiles, scrapes job boards AND company career pages
  via web search, scores matches, generates reports with improvement suggestions,
  and creates professional CV PDFs.
---

# JobFinder

Analyzes the user's professional profile, searches multiple job boards, ATS APIs,
AND company career pages via web search, calculates match percentage for each
vacancy, and generates detailed reports with improvement suggestions and GitHub
project recommendations. Produces professional CVs in PDF format.

## When to use
- User wants to find jobs or search for employment
- Keywords: "find jobs", "job search", "job offers", "cv", "resume", "linkedin profile", "employment", "vacancy", "position", "match", "salary", "github projects", "portfolio", "improve profile"
- Match profile/CV to job listings
- Generate professional CVs in PDF format

## When NOT to use
- User wants to write a cover letter (not supported)
- User wants to negotiate salary
- User wants to prepare for interviews
- Non-job-search contexts (freelance, entrepreneurship)

## Workflow

### Step 1: Profile Collection

Before searching, collect profile data interactively. **NEVER skip these questions or infer them from the CV.** The CV provides technical context; preferences must come from the user.

#### Required questions:

```
1. What city or country are you looking for jobs in?
2. Are you looking for remote, on-site, hybrid, or no preference?
3. What is your salary expectation? (in local currency, e.g., "$80K USD", "EUR 60K")
   - NEVER assume or infer salary from the CV
   - If the user doesn't know, say "not specified"
4. Are you looking for full-time, part-time, contract, or freelance?
5. How many years of work experience do you have in your field?
   - This is CRITICAL: many jobs reject by experience level
   - The answer filters which jobs are viable
```

#### Optional questions (ask but accept "skip"):

```
6. Are there specific companies you'd like to work at?
7. What industries interest you?
8. What are your deal-breakers?
9. What languages do you speak?
```

#### CV/Profile data (parse from file or ask):

```
10. CV/Resume file (PDF, DOCX, TXT, or Markdown)
11. LinkedIn URL
12. Name and contact info
13. Current/most recent role and company
14. Technical skills (list)
15. Soft skills
16. Education level and field of study
17. Current location (city, country)
```

If the user provides a CV file, parse it using `scripts/parse_cv.py`:
```bash
python scripts/parse_cv.py /path/to/cv.pdf
```

Store the profile in structured format (see `templates/profile.json`).

### Step 2: Job Search — Multi-Source Strategy

Search across THREE source categories for maximum coverage:

#### 2a. Job Boards (scraping)

```bash
python scripts/search_jobs.py \
  --keywords "python,javascript,backend,frontend" \
  --location "{{LOCATION}}" \
  --experience {{YEARS}} \
  --max-results 50 \
  --sites remoteok linkedin indeed glassdoor
```

| Board | Type | Notes |
|-------|------|-------|
| RemoteOK | Scraping | Remote-focused, direct JSON API |
| LinkedIn Jobs | Scraping | Requires login for full results |
| Indeed | Scraping | Global, multiple countries |
| Glassdoor | Scraping | Includes company reviews |

#### 2b. ATS APIs (direct, higher quality)

| API | Example Companies | Endpoint |
|-----|-------------------|----------|
| Greenhouse | Various tech companies | `GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs` |
| Lever | Various tech companies | `GET https://api.lever.co/v0/postings/{company}` |
| Ashby | Various tech companies | `GET https://api.ashbyhq.com/posting-api/job-board/{company}` |

#### 2c. Web Search — Company Career Pages (NEW)

Many companies post jobs directly on their websites, not on job boards.
Use the `websearch` tool to find these hidden opportunities:

```
websearch('"{{COMPANY}}" careers hiring {{ROLE}}', numResults=8)
websearch('"{{COMPANY}}" "we are hiring" OR "open positions" {{ROLE}}', numResults=5)
websearch('site:{{COMPANY_DOMAIN}}/careers {{ROLE}}', numResults=5)
```

**Strategy for each target company:**
1. Search `"{{COMPANY_NAME}}" careers {{ROLE}}` on websearch
2. Look for `/careers`, `/jobs`, `/openings` pages on their domain
3. Extract job listings from the career page via webfetch
4. Match against profile

**Additional web search sources beyond job boards:**

| Source | Search Query Pattern | Why It Matters |
|--------|---------------------|----------------|
| Company career pages | `"{{COMPANY}}" careers {{ROLE}}` | Many companies only post on their own site |
| LinkedIn (via web) | `"{{ROLE}}" site:linkedin.com/jobs` | Aggregates across companies |
| GitHub Jobs ecosystem | `"{{ROLE}}" "hiring" site:github.com` | Open source companies hiring |
| AngelList/Wellfound | `"{{ROLE}}" site:wellfound.com` | Startup jobs |
| Y Combinator Work at a Startup | `"{{ROLE}}" site:workatastartup.com` | YC company jobs |
| Remote-specific boards | `"{{ROLE}}" remote site:weworkremotely.com` | Remote-first companies |
| Government/NGO boards | `"{{ROLE}}" site:jobs.undp.org OR site:usajobs.gov` | International org jobs |
| University career pages | `"{{ROLE}}" site:careers.{{UNIVERSITY}}.edu` | Academic/research positions |

### Step 3: Auto-Translation

The `search_jobs.py` script automatically:
- Detects the original language of each vacancy (EN/ES/unknown)
- Translates titles to the target language
- Adds `title_translated` and `origin_language` fields
- Shows language badges in the report

### Step 4: Match Scoring

For each vacancy, calculate a match score (0-100%) using `scripts/score_match.py`:

```bash
python scripts/score_match.py --profile profile.json --jobs results.json
```

**Scoring weights:**
| Factor | Weight | Description |
|--------|--------|-------------|
| Skills match | 35% | % of user skills that match |
| Work experience | 20% | Years of experience vs requirement |
| Salary alignment | 15% | Expectation vs vacancy range |
| Location/remote | 15% | Location and remote preference |
| Education | 10% | Education level |
| Industry | 5% | Industry match |

**Experience filter:** Vacancies requiring more years of experience are marked as "Not viable" and placed at the end.

### Step 5: GitHub Project Suggestions

For each vacancy, suggest EXACTLY 1 GitHub project demonstrating the required skills:

```bash
python scripts/suggest_projects.py \
  --missing-skills "kubernetes,docker,aws" \
  --tech-stack "python,fastapi,postgresql" \
  --job-title "Backend Developer" \
  --output projects.json
```

**Important rule:** 1 project per vacancy, selected so the employer can see the specific skills for the position.

### Step 6: Report Generation

Generate Markdown and HTML reports:

```bash
python scripts/generate_report.py profile.json scored.json projects.json job-report
```

This generates:
- `job-report.md` — Markdown report
- `job-report.html` — Clean, minimal HTML report

**Auto-cleanup:** Temporary files (profile.json, results.json, scored.json, projects.json) are automatically deleted after report generation. Only `job-report.md` and `job-report.html` survive.

**Report contents:**
- Job title (with original language if translated)
- Source badge (board name, company career page, ATS API)
- Match score with breakdown
- Key requirements vs user profile
- Suggested GitHub project
- Direct link to the job posting

### Step 7: CV PDF Generation

**IMPORTANT:** Always generate CVs in PDF format using `scripts/generate_cv_pdf.py`. NEVER generate CVs in Markdown or HTML.

Create TWO separate JSON files (one per language) with CV data and run:

```bash
python scripts/generate_cv_pdf.py cv_{{LANG1}}.json cv_{{LANG2}}.json /output/path
```

This automatically generates:
- `{{Name}}_CV_{{LANG1}}.pdf`
- `{{Name}}_CV_{{LANG2}}.pdf`

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
    "profile": "{{Brief professional summary (DO NOT mention job seeking)}}",
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

**Important rules:**
- The `profile` must be a general professional summary, WITHOUT mentioning job seeking
- Contact info with email, LinkedIn, GitHub, and website are generated as clickable hyperlinks
- Contact elements are separated with `|`

### Step 8: Final Report

Reports and CVs are generated in the user's folder.

Offer to:
- Filter results by minimum score
- Search more jobs at specific companies (via ATS APIs)
- Deep-dive into a specific vacancy
- Re-run with adjusted criteria

## Important Notes

- **Ask before searching:** Never assume the user's profile.
- **Respect rate limits:** Portals have anti-scraping measures. Space out requests.
- **Approximate salary data:** Many vacancies don't include salary. Mark as "Not published".
- **Scores are estimates:** Based on keyword matching and structured data.
- **Direct links:** Each vacancy must have a direct link to the posting page.
- **Experience is critical:** Filter aggressively by experience to avoid rejections.
- **UTF-8 enforced:** All scripts use UTF-8 to avoid encoding issues on Windows.

## Dependencies

```bash
pip install requests beautifulsoup4 fpdf2
```

## File structure

```
jobfinder/
├── SKILL.md
├── scripts/
│   ├── parse_cv.py          # Parse CV files (PDF, DOCX, TXT) to JSON
│   ├── search_jobs.py       # Search job boards + ATS APIs + websearch
│   ├── score_match.py       # Calculate match scores (skills, exp, salary, location, industry)
│   ├── suggest_projects.py  # Suggest GitHub projects (1 per vacancy, static + dynamic)
│   ├── generate_report.py   # Generate MD/HTML reports
│   ├── generate_cv_pdf.py   # Generate professional CV PDFs (ES + EN, multi-page)
│   └── md_to_json.py        # Convert Markdown CV to JSON for PDF generation
└── templates/
    ├── profile.json         # User profile schema
    └── sample_cv.json       # Sample CV JSON template
```

### Script details

**search_jobs.py** features:
- Description fetching from job detail pages (with caching)
- Salary extraction from descriptions (supports USD, EUR, COP, MXN)
- Websearch integration via `--websearch-json` flag
- Deduplication across boards (fuzzy title+company matching)
- Experience-based viability filtering

**suggest_projects.py** features:
- Static fallback list (30+ skills)
- Dynamic websearch queries via `--generate-queries` flag
- Websearch results integration via `--websearch-json` flag

**generate_cv_pdf.py** features:
- Multi-page support (auto page break enabled)
- Cross-platform fonts (Segoe UI on Windows, DejaVu on Linux, Helvetica fallback)
- Page numbers in footer
- Dual output: Spanish + English versions

## Error handling
- **Portal blocks scraping:** Reduce frequency, try another portal
- **CV parsing fails:** Ask user for alternative format (TXT, DOCX)
- **ATS API not responding:** Continue with remaining scraping portals
- **No results:** Broaden location, reduce filters, search more portals and company career pages
- **Encoding issues:** Force UTF-8 on all input files

## Restrictions
- Do NOT fabricate salary when not available — mark "Not published"
- Do NOT omit the direct link to the job posting
- Do NOT generate CVs in Markdown or HTML — always PDF
- Do NOT assume user profile — always ask
- Do NOT exceed portal rate limits
