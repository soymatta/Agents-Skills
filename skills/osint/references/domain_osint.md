# Domain/IP OSINT Reference

## Tools & Techniques

### 1. WHOIS Lookup
```bash
whois {domain}
python -c "import whois; print(whois.whois('{domain}'))"
```

### 2. DNS Records
```bash
dig {domain} ANY +noall +answer
dig {domain} A AAAA MX NS TXT CNAME SOA
nslookup {domain}
```

### 3. Subdomain Enumeration
```bash
subfinder -d {domain} -all
amass enum -d {domain}
```

### 4. Technology Detection
```bash
whatweb {domain}
whatweb -a 3 {domain}  # Aggressive
curl -s {domain} | grep -i "generator\|powered-by\|framework"
```

### 5. Certificate Transparency
```bash
curl "https://crt.sh/?q=%.{domain}&output=json"
```

### 6. Wayback Machine
```bash
curl "https://web.archive.org/cdx/search/cdx?url={domain}&output=json"
```

### 7. Port Scanning
```bash
nmap -sV -sC {domain}
nmap -sV -sC -p- {domain}  # Full scan
```

### 8. IP Information
```bash
curl "https://ipinfo.io/{ip}/json"
curl "https://api.shodan.io/shodan/host/{ip}?key=KEY"
```

### 9. Security Headers
```bash
curl -sI "https://{domain}" | grep -i "strict-transport\|content-security\|x-frame\|x-content-type"
```

### 10. Google Dork
```
site:{domain} filetype:pdf OR filetype:doc
site:{domain} inurl:admin OR inurl:login
site:{domain} "password" OR "internal" OR "confidential"
```

## Red Flags
- Privacy-protected WHOIS
- Recently registered domains
- Multiple redirects
- Missing security headers
- Suspicious SSL certificates
