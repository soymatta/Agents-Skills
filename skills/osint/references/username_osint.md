# Username OSINT Reference

## Tools & Techniques

### 1. Automated Enumeration
```bash
sherlock "{username}"              # 400+ sites
maigret "{username}"               # 2500+ sites
whatsmyname -u "{username}"        # 600+ sites
```

### 2. Manual Platform Search
- **GitHub**: github.com/{username}
- **Twitter/X**: x.com/{username}
- **Reddit**: reddit.com/user/{username}
- **Instagram**: instagram.com/{username}
- **TikTok**: tiktok.com/@{username}
- **YouTube**: youtube.com/@{username}
- **LinkedIn**:linkedin.com/in/{username}
- **Twitch**: twitch.tv/{username}

### 3. Username Availability
```bash
curl -s "https://namechk.com/{username}" | grep -o "available\|taken"
```

### 4. Google Dork
```
"{username}" site:github.com OR site:twitter.com OR site:reddit.com
"{username}" intext:"profile" OR intext:"about"
```

### 5. Historical Search
```bash
# Wayback Machine
curl "https://web.archive.org/web/*/{domain}/{username}"
```

## Tips
- Try variations: john.doe, johndoe, john_doe, j.doe
- Check for username on multiple TLDs
- Look for email associations in public profiles
