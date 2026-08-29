---
framework_version: 1.2.4
source: MadsLorentzen/ai-job-search (MIT)
---

# Job Evaluation Framework

## Pre-Scoring Gates

### Eligibility Gate
Check citizenship/visa requirements. Hard filter — not a scoring dimension.

| Posting wording | Verdict |
|-----------------|---------|
| Citizenship/PR requirement | FAIL |
| Security clearance required | FAIL |
| "International applicants welcome" | PASS |
| Silent on citizenship | PROCEED (mark unverified) |

### Language Gate
Check required languages vs declared languages.

| Requirement vs profile | Verdict |
|----------------------|---------|
| Language not on table | FAIL |
| Language listed but level may be higher | FLAG (proceed, note gap) |
| Language listed at/below declared level | PASS |

## Scoring Dimensions (5D)

### 1. Technical Skills Match (30%, 0-100)
| Score | Meaning |
|-------|---------|
| 80-100 | Core requirements are primary skills |
| 60-79 | Most match, 1-2 learnable gaps |
| 40-59 | Partial match, significant upskilling |
| 0-39 | Fundamental mismatch |

### 2. Experience Match (25%, 0-100)
| Score | Meaning |
|-------|---------|
| 80-100 | Direct experience in same domain |
| 60-79 | Related experience, transferable |
| 40-59 | Adjacent experience |
| 0-39 | Unrelated |

### 3. Behavioral/Culture Fit (15%, 0-100)
| Score | Meaning |
|-------|---------|
| 80-100 | Strong culture match |
| 60-79 | Mixed but compatible |
| 40-59 | Some friction |
| 0-39 | Significant mismatch |

### 4. Location & Logistics (Pass/Fail)
- Within commute: PASS
- Remote with occasional office: PASS
- Requires relocation: FAIL
- Frequent travel: FLAG

### 5. Career Alignment & Motivation (30%, 0-100)
| Score | Meaning |
|-------|---------|
| 80-100 | Strongly aligned, clear growth |
| 60-79 | Good, partially aligned |
| 40-59 | Decent but not building toward goals |
| 0-39 | Dead end |

## Weighting
- Technical: 30%
- Experience: 25%
- Behavioral: 15%
- Career: 30%
- Location: Pass/Fail

## Thresholds
- **Strong** (75+): Definitely apply
- **Good** (60-74): Apply, address gaps
- **Moderate** (45-59): Consider carefully
- **Weak** (30-44): Probably skip
- **Poor** (<30): Skip
