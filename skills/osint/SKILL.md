---
name: osint
description: >-
  Performs OSINT (Open Source Intelligence) investigation on any target: person, company, domain, email,
  phone, username, IP, or crypto wallet. Generates structured plans with phases, tools, and commands, backed
  by real scripts (phone parsing, plan/command/report generation, directory scraping, tool check). websearch
  is the primary method; curl-based commands are fallbacks. ALWAYS confirms role/consent and gets approval
  before running investigative commands — never executes without approval. Use when the user wants to
  investigate someone, check an email/phone/username, verify identity, or do due diligence. Triggers:
  "osint", "investigar", "investigate", "recon", "background check", "due diligence", "whois",
  "verificar identidad", "OSINT report".
---

# OSINT Investigation Framework

A skill for conducting Open Source Intelligence (OSINT) investigations. Generates
structured investigation plans, tools, and commands for gathering intelligence on
any target: persons, companies, domains, emails, phones, usernames, IPs, or
crypto wallets.

## When to use
- User wants to investigate a person/company, check an email/phone/username, look up a domain or IP, verify identity, do due diligence or a background check, or gather OSINT intelligence on any target
- **Keywords:** "osint", "investigar", "investigate", "recon", "lookup", "dossier", "background check", "due diligence", "verify identity", "verificar identidad", "whois", "phone lookup", "email lookup", "username search", "investigar persona/empresa", "numero de telefono", "data breach", "HIBP", "sherlock", "maigret", "shodan", "domain recon", "subdomain enumeration", "OSINT report", "filtracion", "huella digital", "crypto wallet check", "reverse image search", "breach check"

## Restrictions
- **DO NOT** execute any *investigative* command against a third-party target without explicit user approval — present plan first, get confirmation. Offline/local scripts (phone_parser, generate_plan, gen_commands, tools_check) that touch no external target are exempt from this gate
- **DO NOT** run ACTIVE scans (e.g. nmap) or any probe against a host you don't own or lack written authorization for
- **DO NOT** use for stalking, harassment, or unauthorized access
- **DO NOT** skip documenting findings — always save to a structured report
- **DO NOT** expose API keys or credentials in reports
- **DO NOT** use paid tools without confirming user has API keys
- **DO NOT** report a single-source finding as fact — corroborate before writing it into the report
- Only use publicly available, legal OSINT tools and sources
- Respect consent, proportionality, and data retention: only collect what the stated purpose requires, and delete intermediate files (`findings.json`, `commands.sh`, `investigation_plan.json`) when the investigation is done or keep them only as long as the purpose requires

## Workflow

### Step 0: Ethical gate + tool check
Before any investigation, confirm **role / consent / proportionality**:
- Are you the data subject, the target's owner, an authorized client (e.g. due diligence, security engagement, hiring with candidate consent), or an unrelated third party?
- Is the purpose legitimate, and is the planned depth/scope **proportional** to it (scoped for background checks, deeper only when justified)?
- Only proceed with a legitimate purpose and consent/authority. If the user is an unrelated third party with no legitimate purpose, stop and explain.

Then verify required tools are installed (the missing "Step 0" today):
```bash
cd scripts
python tools_check.py
```
Flag or skip any tool that is missing before generating a plan.

### Step 1: Target Identification

Before any investigation, ask the user:

```
Ask the user for:

1. ROLE / CONSENT: Are you the subject, an authorized client, or a third party?
   (If a third party with no legitimate purpose, stop.)

2. TARGET TYPE: What are you investigating?
   - Person (name, DNI/ID, email, phone)
   - Company (name, domain, registration)
   - Domain/Website
   - Email address
   - Phone number
   - Username/social media
   - IP address
   - Cryptocurrency wallet

3. TARGET VALUE: The actual value to investigate
   Example: "{{EMAIL}}", "{{PHONE}}", "{{COMPANY_NAME}}"

4. PURPOSE: Why are you investigating?
   - Background check / hiring (with candidate consent)
   - Due diligence / business
   - Security investigation (authorized)
   - Personal curiosity (your own data)
   - Legal/compliance
   - Other: ___

5. DEPTH: How deep should the investigation go?
   - Quick (5-10 minutes): Basic lookup, key findings
   - Standard (30-60 minutes): Comprehensive scan
   - Deep (2+ hours): Full profile with cross-references
   Only go as deep as the purpose proportionally justifies.

6. BUDGET: Do you have API keys for paid services?
   - Free only (no API keys)
   - Have some API keys (list them)
   - Full access (Bright Data, Shodan, etc.)
```

### Step 2: Phone Number Pre-processing (for phone targets)

Before generating the plan, parse the phone number to extract metadata:

```bash
cd scripts
python phone_parser.py "{{PHONE}}"
```

This provides:
- Country code and country name
- Carrier detection
- Line type (mobile/landline)
- Multiple search-optimized formats
- Pre-generated search queries

### Step 3: Investigation Plan

Based on the target type, generate a structured investigation plan using
`scripts/generate_plan.py`:

```bash
cd scripts
python generate_plan.py \
  --target-type phone \
  --target-value "{{PHONE}}" \
  --depth quick \
  --budget free \
  --output investigation_plan.json
```

The plan includes phases, tools, commands, and expected outputs for each step.

### Step 4: Primary Investigation with websearch

**IMPORTANT**: Always use `websearch` tool as the PRIMARY investigation method.
The curl-based commands in the plan are fallbacks only.

For phone investigations, run these websearch queries:

```python
# Use the agent's websearch tool with these queries:
websearch('"{{PHONE}}"', numResults=8)
websearch('"{{PHONE}}" truecaller OR whitepages', numResults=5)
websearch('"{{PHONE}}" spam OR scam OR fraud', numResults=5)
```

For other target types, adapt the queries:
- **Person**: `websearch('"John Doe" linkedin OR twitter OR facebook')`
- **Email**: `websearch('"john@example.com" breach OR leak')`
- **Domain**: `websearch('site:example.com')` + use curl for DNS/headers
- **Username**: `websearch('"johndoe" site:github.com OR site:twitter.com')`

### Step 5: Directory Scraping (for phone targets)

Run the free directory scrapers:

```bash
cd scripts
python scrape_directories.py "{{PHONE}}" --json
```

Available scrapers: `google`, `truecaller`, `whitepages`, `callerid`, `8x8`, `whocalledme`

### Step 6: Tool Selection

For each investigation type, select appropriate tools from the reference files:

- **Person/Name**: `reference/person_osint.md`
- **Email**: `reference/email_osint.md`
- **Phone**: `reference/phone_osint.md`
- **Username**: `reference/username_osint.md`
- **Domain/IP**: `reference/domain_osint.md`
- **Company**: `reference/company_osint.md`
- **Crypto**: `reference/crypto_osint.md`

Each reference file contains:
- Free tools and their usage
- Paid tools (if available)
- Command templates
- Expected output format
- Tips and caveats

### Step 7: Command Generation

Generate investigation commands using `scripts/gen_commands.py`:

```bash
cd scripts
python gen_commands.py investigation_plan.json --output commands.sh
```

This generates a shell script with all investigation commands, commented and
organized by phase. Each command includes:
- What it does
- Expected output
- Time estimate
- Dependencies

### Step 8: Execute with Approval

Present the findings and ask for approval to continue deeper:

```
PHASE 1: Basic Enumeration (2 minutes)
[websearch] "phone number" → Results
[websearch] "phone number" site:truecaller.com → Results
[scrape_directories] → Findings

Do you want to continue to Phase 2? [y/N]
```

Execute only with explicit approval. One phase at a time.

### Step 9: Report Generation

After investigation, generate a structured report using `scripts/gen_report.py`:

```bash
cd scripts
python gen_report.py \
  --target "{{PHONE}}" \
  --target-type phone \
  --findings findings.json \
  --output osint_report.md \
  --format markdown
```

Report structure:

```markdown
# OSINT Report: {target}
Generated: {date} | Depth: {depth} | Analyst: AI Assistant

## Executive Summary
{Brief summary of findings and risk assessment}

## Target Profile
| Field | Value |
|-------|-------|
| Target | {target} |
| Type | {type} |
| Investigation Date | {date} |
| Confidence Level | {high/medium/low} |

## Findings

### 1. Digital Footprint
- **Emails found**: {list}
- **Phone numbers**: {list}
- **Social profiles**: {list}
- **Username presence**: {list}

### 2. Online Presence
- **LinkedIn**: {url} — {summary}
- **Twitter/X**: {url} — {summary}
- **GitHub**: {url} — {summary}
- **Other platforms**: {list}

### 3. Domain/Infrastructure (if applicable)
- **Domain**: {domain}
- **Registrar**: {registrar}
- **Created**: {date}
- **IP**: {ip}
- **Technologies**: {list}
- **SSL Certificate**: {info}

### 4. Data Breaches (if applicable)
- **Breaches found**: {count}
- **Exposed data**: {types}
- **Risk level**: {high/medium/low}

### 5. Employment/Business (if applicable)
- **Current company**: {company}
- **Position**: {title}
- **Connections**: {count}
- **Business registrations**: {list}

### 6. Risk Assessment
| Risk Factor | Level | Evidence |
|-------------|-------|----------|
| Data exposure | {level} | {evidence} |
| Social engineering risk | {level} | {evidence} |
| Identity verification | {level} | {evidence} |

## Tools Used
| Tool | Purpose | Source |
|------|---------|--------|
| {tool} | {purpose} | {free/paid} |

## Recommendations
1. {recommendation}
2. {recommendation}

## Methodology
- Investigation depth: {depth}
- Tools used: {count}
- Sources checked: {count}
- Time spent: {time}

## Disclaimer
This report was generated using publicly available information (OSINT).
Findings should be verified through additional sources before making decisions.
This investigation was conducted legally and ethically using only public data.
```

## Investigation Types Reference

### Person Investigation
1. Name search (Google, Bing, Yandex)
2. Social media profiles (LinkedIn, Twitter, Facebook, Instagram)
3. Username enumeration (Sherlock, Maigret, WhatsMyName)
4. Email lookup (Hunter, EmailRep, HIBP)
5. Phone lookup (NumVerify, TrueCaller, Twilio)
6. Data breach check (HIBP, BreachDirectory)
7. Public records (government databases)
8. Image reverse search (Google Images, TinEye)

### Company Investigation
1. Company registration (SEC, Companies House, etc.)
2. Domain WHOIS and DNS
3. Employee search (LinkedIn)
4. Technology stack (Wappalyzer, BuiltWith)
5. Financial records (if public)
6. News and press releases
7. Social media presence
8. Job postings (hiring signals)

### Domain/IP Investigation
1. WHOIS lookup
2. DNS records (A, AAAA, MX, NS, TXT, CNAME)
3. SSL certificate analysis
4. Subdomain enumeration
5. Web technology detection
6. Wayback Machine snapshots
7. IP geolocation
8. Reverse DNS
9. Shodan/Censys device search
10. Security headers analysis

### Email Investigation
1. Email validation (syntax, MX, disposable check)
2. Breach check (HIBP)
3. Social media account lookup
4. Domain WHOIS (if corporate email)
5. Email reputation (EmailRep)
6. Hunter.io domain search

### Username Investigation
1. Sherlock (400+ sites)
2. Maigret (2500+ sites)
3. WhatsMyName (600+ sites)
4. Namechk
5. Social media direct search

### Crypto Wallet Investigation
1. Blockchain explorer (Etherscan, Blockchain.com)
2. Transaction history
3. Balance check
4. Associated addresses
5. Exchange deposits (if known)

## Dependencies

Install required tools:

```bash
# Core tools (free)
pip install sherlock-project  # Username enumeration
pip install holehe             # Email account discovery
pip install theHarvester       # Email/domain recon

# System tools (install separately)
# whois - domain registration lookup
# nslookup/dig - DNS resolution
# nmap - ACTIVE port scanning (requires host owner authorization — see domain_osint.md)
# curl/wget - HTTP probing
```

For advanced investigations:
```bash
pip install python-whois      # WHOIS lookups
pip install dnspython         # DNS queries
pip install shodan            # Shodan API
pip install haveibeenpwned    # HIBP API
```

## File Structure

```
osint/
├── SKILL.md
├── scripts/
│   ├── generate_plan.py      # Generate investigation plan
│   ├── gen_commands.py       # Generate shell commands
│   ├── gen_report.py         # Generate investigation report
│   ├── tools_check.py        # Check installed OSINT tools
│   ├── phone_parser.py       # Parse phone numbers (no APIs needed)
│   ├── scrape_directories.py # Scrape free phone directories
│   └── run_investigation.py  # Execute investigation pipeline
└── reference/
    ├── person_osint.md       # Person investigation guide
    ├── email_osint.md        # Email investigation guide
    ├── phone_osint.md        # Phone investigation guide
    ├── username_osint.md     # Username investigation guide
    ├── domain_osint.md       # Domain/IP investigation guide
    ├── company_osint.md      # Company investigation guide
    └── crypto_osint.md       # Crypto wallet investigation guide
```

## Phone Number Quick Reference

### Colombia Prefixes (57)
| Prefix | Carrier | Type |
|--------|---------|------|
| 300-305 | Claro/Movistar | Mobile |
| 310-321 | Claro/Movistar | Mobile |
| 322-325 | Tigo | Mobile |
| 350 | ETB | Mobile |
| 1 (landline) | Various | Fixed |

### Mexico Prefixes (52)
| Prefix | Carrier | Type |
|--------|---------|------|
| 55 | Telcel/AT&T | Mobile |
| 33 | Telcel/AT&T | Mobile |
| 81 | Telcel/AT&T | Mobile |

### USA Area Codes (1)
Common codes: 212 (NYC), 213 (LA), 312 (Chicago), 305 (Miami), 415 (SF), 713 (Houston)

## Websearch Query Templates

### Phone Number
```
websearch('"{phone}"', numResults=8)
websearch('"{phone}" truecaller OR whitepages', numResults=5)
websearch('"{phone}" spam OR scam OR fraud', numResults=5)
websearch('"national_format" site:truecaller.com', numResults=3)
```

### Person Name
```
websearch('"{name}" linkedin OR twitter OR facebook', numResults=8)
websearch('"{name}" site:linkedin.com', numResults=5)
websearch('"{name}" email OR phone OR address', numResults=5)
```

### Email
```
websearch('"{email}"', numResults=8)
websearch('"{email}" breach OR leak OR exposed', numResults=5)
websearch('"{email}" site:haveibeenpwned.com', numResults=3)
```

### Domain
```
websearch('site:{domain}', numResults=8)
websearch('"{domain}" whois OR registrar', numResults=5)
websearch('"{domain}" technology OR stack OR builtwith', numResults=5)
```

## Methodology: corroboration, confidence, and "no data"

- **Corroboration rule:** a finding from a single source is a *lead*, not a fact.
  Do not write it into the report until it is cross-checked against at least one
  independent source (a second directory, an official record, or the target's own
  primary account). Label each finding with the sources that corroborate it.
- **Confidence levels:**
  - **High** — corroborated by 2+ independent, authoritative sources
  - **Medium** — corroborated by secondary sources or one authoritative source
  - **Low / Unverified** — single source, scraped data, or self-reported; state the caveat
- **No data found:** "absence of evidence is not evidence of absence." Report
  explicitly when an expected surface (e.g. no breach history, no social profile)
  is empty, and note that data may simply be under the surface.
- **Fragile/legacy endpoints:** several plan commands target public pages/APIs
  (TrueCaller, Whitepages, DeBank, OpenSea, some `curl` lookups) that change or
  block scrapers. Treat their output as **possibly stale/unverified** — prefer an
  `websearch`-backed confirmation before treating scraped data as a finding.
- **Source labelling:** in the report, mark each tool/source as `verified` vs
  `possibly stale — prefer websearch` so the reader can weight the evidence.

## Cleanup
Delete intermediate artifacts (`investigation_plan.json`, `commands.sh`,
`scrape_directories` output, `findings.json`) once the report is finalized, or
keep them only as long as the stated purpose requires. Do not leave raw scraped
data about a person/company lying around indefinitely.
