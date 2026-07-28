# Company OSINT Reference

## Tools & Techniques

### 1. Basic Company Info
```bash
# Google search
"{company}" company OR corporation OR LLC

# LinkedIn
site:linkedin.com "{company}" company

# SEC filings (US)
site:sec.gov "{company}"
```

### 2. Financial & Funding
```bash
# Crunchbase
site:crunchbase.com "{company}"

# PitchBook
site:pitchbook.com "{company}"

# AngelList
site:angellist.com "{company}"
```

### 3. Employee Research
```bash
# LinkedIn employees
site:linkedin.com/company/{company} employees

# Glassdoor reviews
site:glassdoor.com "{company}" reviews

# Indeed jobs
site:indeed.com "{company}" jobs
```

### 4. Domain & Tech Stack
```bash
whois {company_domain}
whatweb {company_domain}
curl -sI "https://{company_domain}"
```

### 5. News & Press
```bash
"{company}" after:2023
site:techcrunch.com "{company}"
site:prnewswire.com "{company}"
```

### 6. Legal & Compliance
```bash
# Court records
site:unicourt.com "{company}"

# Trademarks
site:uspto.gov "{company}"

# Business registration
"{company}" site:state.{state}.us
```

### 7. Job Postings (Hiring Signals)
```bash
site:indeed.com "{company}"
site:linkedin.com/jobs "{company}"
site:glassdoor.com/Jobs "{company}"
```

## Red Freuds
- Multiple name changes
- Frequent leadership turnover
- Negative news coverage
- High employee turnover (Glassdoor)
- Pending lawsuits
