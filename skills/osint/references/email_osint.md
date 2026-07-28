# Email OSINT Reference

## Tools & Techniques

### 1. Email Validation
```bash
# Syntax check
echo "{email}" | grep -E "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# MX record check
dig {domain} MX +short

# SMTP verification (manual)
telnet {mx_server} 25
```

### 2. Account Discovery
```bash
holehe "{email}"              # Check registrations
holehe "{email}" --all        # Full enumeration
```

### 3. Breach Check
```bash
# Have I Been Pwned (API key required)
curl -H "hibp-api-key: YOUR_KEY" \
  "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"

# BreachDirectory
curl "https://breachdirectory.org/api/search?email={email}"
```

### 4. Email Reputation
```bash
curl "https://emailrep.io/{email}"
```

### 5. Social Media Lookup
- Search email on LinkedIn, Twitter, Facebook
- Check Gravatar profile
- GitHub commit search

### 6. Domain Investigation (if corporate)
```bash
whois {domain}
curl "https://api.hunter.io/v2/domain-search?domain={domain}"
theHarvester -d {domain} -b all
```

## Red Flags
- Disposable email providers
- Recently created accounts
- Multiple breaches
- Email forwarding to suspicious domains
