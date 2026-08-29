---
name: ai-job-search
description: >-
  Third-party skill (MadsLorentzen/ai-job-search, MIT license). AI-powered job application framework.
  Evaluate job postings with 5-dimension fit scoring (technical match, experience, culture, logistics, career alignment),
  tailor CVs with relevance-weighted cutting, write forward-looking cover letters, prepare STAR-format interview answers,
  and track applications. Includes PDF verification loop, ATS parseability checks, and drafter-reviewer separation.
  Use when: user wants to evaluate a job posting, assess job fit, apply to a job, prepare for an interview,
  write a cover letter, tailor a resume/CV, score a job opportunity, or track job applications.
  Triggers on: "job posting", "job application", "apply to", "CV", "cover letter", "resume", "interview prep",
  "job fit", "career", "employment", "trabajo", "empleo", "postular", "carta de presentacion", "entrevista",
  "candidatura", "puesto", "vacante", "aplicar", "linkedin job", "glassdoor", "indeed".
  Do not modify — pull updates from upstream.
---

# AI Job Search (Third-Party Reference)

> **Source:** [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) (MIT License)
> **Version:** 1.3.4 (framework)
> **Do not modify this skill directly.** To update, pull from the upstream repository.

This skill is installed as a **reference copy**. It provides methodology files and workflows
that can be used by agents (especially `jobfinder`) to enhance their capabilities.

## Quick Commands

| Command | Description |
|---------|-------------|
| `/setup` | Onboarding: fill in candidate profile via documents, CV import, or interview |
| `/apply <url>` | Full workflow: evaluate fit → draft CV + cover letter → review → compile → present |
| `/scrape` | Search multiple job portals, deduplicate, present with fit ratings |
| `/rank` | Batch-score scraped jobs into a ranked shortlist |
| `/interview` | Stage-specific interview prep pack + mock interview |
| `/outcome` | Record application results, track follow-ups |
| `/upskill` | Skill gap analysis with learning plans and web-searched resources |
| `/expand` | Enrich profile from public sources (GitHub, portfolio, etc.) |

## Workflow

```
Profile → Search → Score (5D + Gates) → Rank → Apply (CV + Cover Letter) → Review → Track
```

### Step 1: Research & Evaluate Fit
- Fetch the job posting (URL or text)
- Research the company (website, LinkedIn, news)
- Score using 5-dimension framework (see `reference/04-job-evaluation.md`)
- Apply Eligibility Gate and Language Gate before scoring

### Step 2: Tailor CV
- Read existing CV as starting point
- Follow guidelines in `reference/05-cv-templates.md`
- Create tailored CV with profile statement, skills, experience emphasis

### Step 3: Write Cover Letter
- Follow writing style rules in `reference/03-writing-style.md`
- Follow template in `reference/06-cover-letter-templates.md`
- Connect experience to role requirements

### Step 4: Interview Preparation
- Follow framework in `reference/07-interview-prep.md`
- Prepare STAR-format answers
- Draft questions for interviewer

## Reference Files

| File | Purpose |
|------|---------|
| `reference/01-candidate-profile.md` | Education, experience, skills, publications |
| `reference/02-behavioral-profile.md` | Behavioral assessment, strengths |
| `reference/03-writing-style.md` | Tone, structure, do's and don'ts |
| `reference/04-job-evaluation.md` | 5-dimension scoring framework |
| `reference/05-cv-templates.md` | CV structure and tailoring rules |
| `reference/06-cover-letter-templates.md` | Cover letter structure |
| `reference/07-interview-prep.md` | STAR examples, interview framework |
| `reference/08-application-forms.md` | Portal form filling guidance |
| `reference/09-web-research.md` | Web fetching rules and trust boundary |

## Key Methodology: 5-Dimension Fit Evaluation

| Dimension | Weight | Score Range |
|-----------|--------|-------------|
| Technical Skills Match | 30% | 0-100 |
| Experience Match | 25% | 0-100 |
| Behavioral/Culture Fit | 15% | 0-100 |
| Location & Logistics | Pass/Fail | Binary |
| Career Alignment & Motivation | 30% | 0-100 |

**Thresholds:** Strong (75+), Good (60-74), Moderate (45-59), Weak (30-44), Poor (<30)

## Pre-Scoring Gates

1. **Eligibility Gate** — citizenship/visa requirements (hard filter)
2. **Language Gate** — required vs declared languages (hard filter for undeclared, flag for level mismatch)

## What Makes This Framework Different

- **PDF verification loop** — compile and inspect every PDF, iterate until clean
- **ATS verification** — check PDF text layer for parseability
- **Relevance-weighted CV cutting** — score each line by relevance, not just seniority
- **Drafter-reviewer separation** — second agent critiques drafts
- **Forward-looking cover letters** — focus on tasks you'll solve, not just past duties
