# Phone OSINT Reference

## Tools & Techniques

### 1. Phone Validation
```bash
# NumVerify
curl "http://apilayer.net/api/validate?access_key=KEY&number={phone}"

# Twilio Lookup
curl -u "ACCOUNT_SID:AUTH_TOKEN" \
  "https://lookups.twilio.com/v2/PhoneNumbers/{phone}"
```

### 2. Caller ID / Identity
```bash
# TrueCaller (API or web scraping)
curl "https://api.truecaller.com/v1/search?q={phone}"
```

### 3. Social Media Association
- Search phone on Facebook (login required)
- WhatsApp contact sync
- Telegram username lookup

### 4. People Search
```bash
# TruePeopleSearch (free, web-based)
# Whitepages
# BeenVerified
```

### 5. Breach Check
```bash
# If email is associated
curl -H "hibp-api-key: KEY" \
  "https://haveibeenpwned.com/api/v3/breachedaccount/{associated_email}"
```

## Number Format Notes
- Always include country code (+1, +34, +52, etc.)
- Strip spaces, dashes, parentheses
- Validate format before searching
