# Person OSINT Reference

## Tools & Techniques

### 1. Name Search
- **Google**: `"{name}" site:linkedin.com OR site:twitter.com OR site:facebook.com`
- **Bing**: `"{name}" -site:linkedin.com`
- **Yandex**: Better for non-English names and images
- **DuckDuckGo**: Privacy-focused, good for alternative results

### 2. Social Media Profiles
- **LinkedIn**: Primary professional profile source
- **Twitter/X**: Public posts and connections
- **Facebook**: Personal information (if public)
- **Instagram**: Visual content and location tags
- **GitHub**: Code contributions and email in commits
- **Reddit**: Comment history and interests

### 3. Username Enumeration
```bash
sherlock "{username}"          # 400+ sites
maigret "{username}"           # 2500+ sites
whatsmyname -u "{username}"    # 600+ sites
```

### 4. Email from Name
- **Hunter.io**: Domain email search
- **LinkedIn**: Find email from profile
- **GitHub**: Search commits by name

### 5. Public Records
- Government databases (varies by country)
- Court records
- Property records
- Business registrations

## Tips
- Cross-reference findings across multiple sources
- Check date consistency of profiles
- Look for username reuse across platforms
- Check email breaches for additional context
