#!/usr/bin/env python3
"""Generate investigation plans based on target type and depth."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PLANS = {
    "person": {
        "quick": {
            "phases": [
                {
                    "name": "Basic Enumeration",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}" site:linkedin.com OR site:twitter.com OR site:facebook.com', "purpose": "Find social profiles"},
                        {"tool": "bing", "command": 'search "{target}" -site:linkedin.com', "purpose": "Find additional web presence"},
                        {"tool": "holehe", "command": 'holehe "{email}" --timeout 10', "purpose": "Check email account registrations", "condition": "if email provided"},
                    ],
                },
                {
                    "name": "Social Media Quick Check",
                    "estimated_time": "3 min",
                    "steps": [
                        {"tool": "sherlock", "command": 'sherlock "{username}" --timeout 10', "purpose": "Username enumeration across 400+ sites", "condition": "if username provided"},
                        {"tool": "namechk", "command": 'curl -s "https://namechk.com/{username}"', "purpose": "Username availability check"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Enumeration",
                    "estimated_time": "10 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}" filetype:pdf OR filetype:doc', "purpose": "Find documents mentioning target"},
                        {"tool": "google", "command": 'search "{target}" site:linkedin.com', "purpose": "LinkedIn profile search"},
                        {"tool": "holehe", "command": 'holehe "{email}"', "purpose": "Email account discovery"},
                        {"tool": "sherlock", "command": 'sherlock "{username}"', "purpose": "Full username enumeration"},
                    ],
                },
                {
                    "name": "Data Breach Check",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "hibp", "command": 'curl -H "hibp-api-key: YOUR_KEY" "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"', "purpose": "Check data breaches"},
                        {"tool": "breachdirectory", "command": 'curl "https://breachdirectory.org/api/search?email={email}"', "purpose": "Additional breach search"},
                    ],
                },
                {
                    "name": "Professional Background",
                    "estimated_time": "10 min",
                    "steps": [
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}" AND ("experience" OR "education")', "purpose": "Career history"},
                        {"tool": "google_scholar", "command": 'search site:scholar.google.com "{target}"', "purpose": "Publications and research"},
                        {"tool": "github", "command": 'search "{target}" site:github.com', "purpose": "Open source contributions"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Enumeration",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}" -site:linkedin.com -site:twitter.com', "purpose": "Deep web search"},
                        {"tool": "yandex", "command": 'search "{target}"', "purpose": "Yandex search (different index)"},
                        {"tool": "holehe", "command": 'holehe "{email}" --all', "purpose": "Full email enumeration"},
                        {"tool": "sherlock", "command": 'sherlock "{username}" --all', "purpose": "All platforms check"},
                        {"tool": "maigret", "command": 'maigret "{username}" --json', "purpose": "Extended username search (2500+ sites)"},
                    ],
                },
                {
                    "name": "Deep Background",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}" ("engineer" OR "developer" OR "manager")', "purpose": "Career timeline"},
                        {"tool": "google_news", "command": 'search "{target}" after:2020', "purpose": "Recent news mentions"},
                        {"tool": "archive", "command": 'curl "https://web.archive.org/web/*/{website}"', "purpose": "Wayback Machine history"},
                        {"tool": "pdl", "command": 'curl "https://api.peopledatalabs.com/v5/person/search?name={target}"', "purpose": "People Data Labs enrichment"},
                    ],
                },
                {
                    "name": "Technical Footprint",
                    "estimated_time": "20 min",
                    "steps": [
                        {"tool": "github", "command": 'search "{email}" site:github.com', "purpose": "GitHub commits with email"},
                        {"tool": "gitlab", "command": 'search "{email}" site:gitlab.com', "purpose": "GitLab activity"},
                        {"tool": "stackoverflow", "command": 'search "{target}" site:stackoverflow.com', "purpose": "Stack Overflow activity"},
                        {"tool": "medium", "command": 'search "{target}" site:medium.com', "purpose": "Blog posts and articles"},
                    ],
                },
            ],
        },
    },
    "email": {
        "quick": {
            "phases": [
                {
                    "name": "Email Validation & Enumeration",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "holehe", "command": 'holehe "{target}"', "purpose": "Check accounts registered with email"},
                        {"tool": "emailrep", "command": 'curl "https://emailrep.io/{target}"', "purpose": "Email reputation check"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Find mentions of email"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Email Investigation",
                    "estimated_time": "15 min",
                    "steps": [
                        {"tool": "holehe", "command": 'holehe "{target}" --all', "purpose": "Full account discovery"},
                        {"tool": "emailrep", "command": 'curl "https://emailrep.io/{target}"', "purpose": "Reputation and risk"},
                        {"tool": "hibp", "command": 'curl -H "hibp-api-key: KEY" "https://haveibeenpwned.com/api/v3/breachedaccount/{target}"', "purpose": "Breach check"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Web mentions"},
                        {"tool": "hunter", "command": 'curl "https://api.hunter.io/v2/email-verifier?email={target}&api_key=KEY"', "purpose": "Email verification"},
                        {"tool": "domain_whois", "command": 'whois {domain}', "purpose": "Domain registration (if corporate)"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Email Intelligence",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "holehe", "command": 'holehe "{target}" --all', "purpose": "Full account enumeration"},
                        {"tool": "emailrep", "command": 'curl "https://emailrep.io/{target}"', "purpose": "Detailed reputation"},
                        {"tool": "hibp", "command": 'curl "https://haveibeenpwned.com/api/v3/breachedaccount/{target}"', "purpose": "Breach history"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Web presence"},
                        {"tool": "hunter_domain", "command": 'curl "https://api.hunter.io/v2/domain-search?domain={domain}&api_key=KEY"', "purpose": "Domain email enumeration"},
                        {"tool": "theHarvester", "command": 'theHarvester -d {domain} -b all', "purpose": "Email harvesting from domain"},
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}"', "purpose": "LinkedIn profile"},
                        {"tool": "github_commits", "command": 'search "{target}" site:github.com', "purpose": "Git commits with email"},
                    ],
                },
            ],
        },
    },
    "phone": {
        "quick": {
            "phases": [
                {
                    "name": "Phone Validation",
                    "estimated_time": "3 min",
                    "steps": [
                        {"tool": "numverify", "command": 'curl "http://apilayer.net/api/validate?access_key=KEY&number={target}"', "purpose": "Validate and get carrier info"},
                        {"tool": "truecaller", "command": 'curl "https://api.truecaller.com/v1/search?q={target}"', "purpose": "Caller ID lookup"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Find mentions of number"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Phone Investigation",
                    "estimated_time": "15 min",
                    "steps": [
                        {"tool": "numverify", "command": 'curl "http://apilayer.net/api/validate?number={target}"', "purpose": "Phone validation and carrier"},
                        {"tool": "truecaller", "command": 'curl "https://api.truecaller.com/v1/search?q={target}"', "purpose": "Name and location"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Web mentions"},
                        {"tool": "facebook", "command": 'search "{target}" site:facebook.com', "purpose": "Facebook profile"},
                        {"tool": "whatsapp", "command": 'curl -s "https://api.whatsapp.com/send?phone={target}" -o /dev/null -w "%{http_code}"', "purpose": "WhatsApp availability check"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Phone Intelligence",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "numverify", "command": 'curl "http://apilayer.net/api/validate?number={target}"', "purpose": "Full validation"},
                        {"tool": "twilio", "command": 'curl "https://lookups.twilio.com/v2/PhoneNumbers/{target}"', "purpose": "Carrier and line type"},
                        {"tool": "truecaller", "command": 'curl "https://api.truecaller.com/v1/search?q={target}"', "purpose": "Identity lookup"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "All web mentions"},
                        {"tool": "facebook", "command": 'search "{target}" site:facebook.com', "purpose": "Social profiles"},
                        {"tool": "breach", "command": 'curl "https://haveibeenpwned.com/api/v3/breachedaccount/{target}"', "purpose": "Breach check"},
                        {"tool": "directory", "command": 'curl "https://www.truepeoplesearch.com/results?phoneno={target}"', "purpose": "People search"},
                    ],
                },
            ],
        },
    },
    "username": {
        "quick": {
            "phases": [
                {
                    "name": "Username Enumeration",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "sherlock", "command": 'sherlock "{target}"', "purpose": "Search 400+ platforms"},
                        {"tool": "namechk", "command": 'curl "https://namechk.com/{target}"', "purpose": "Username availability"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "General web search"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Username Investigation",
                    "estimated_time": "15 min",
                    "steps": [
                        {"tool": "sherlock", "command": 'sherlock "{target}" --all', "purpose": "Full platform enumeration"},
                        {"tool": "maigret", "command": 'maigret "{target}"', "purpose": "Extended 2500+ site search"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Web mentions"},
                        {"tool": "github", "command": 'search "{target}" site:github.com', "purpose": "GitHub profile"},
                        {"tool": "twitter", "command": 'search "{target}" site:twitter.com OR site:x.com', "purpose": "Twitter/X profile"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Username Intelligence",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "sherlock", "command": 'sherlock "{target}" --all', "purpose": "Full enumeration"},
                        {"tool": "maigret", "command": 'maigret "{target}" --json', "purpose": "Extended search with data"},
                        {"tool": "whatsmyname", "command": 'python -m whatsmyname -u "{target}"', "purpose": "600+ site enumeration"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "All web mentions"},
                        {"tool": "github", "command": 'search "{target}" site:github.com', "purpose": "Code contributions"},
                        {"tool": "stackoverflow", "command": 'search "{target}" site:stackoverflow.com', "purpose": "Q&A activity"},
                        {"tool": "reddit", "command": 'search "{target}" site:reddit.com', "purpose": "Reddit activity"},
                    ],
                },
            ],
        },
    },
    "domain": {
        "quick": {
            "phases": [
                {
                    "name": "Domain Basic Recon",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "whois", "command": 'whois {target}', "purpose": "Domain registration info"},
                        {"tool": "dig", "command": 'dig {target} ANY +noall +answer', "purpose": "DNS records"},
                        {"tool": "curl", "command": 'curl -sI https://{target}', "purpose": "HTTP headers and server info"},
                        {"tool": "google", "command": 'search site:{target}', "purpose": "Indexed pages"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Domain Recon",
                    "estimated_time": "15 min",
                    "steps": [
                        {"tool": "whois", "command": 'whois {target}', "purpose": "Registration details"},
                        {"tool": "dig", "command": 'dig {target} ANY', "purpose": "All DNS records"},
                        {"tool": "nmap", "command": 'nmap -sV -sC {target}', "purpose": "Port scan and services"},
                        {"tool": "curl", "command": 'curl -sI https://{target}', "purpose": "HTTP headers"},
                        {"tool": "subfinder", "command": 'subfinder -d {target}', "purpose": "Subdomain enumeration"},
                        {"tool": "whatweb", "command": 'whatweb {target}', "purpose": "Technology detection"},
                        {"tool": "wayback", "command": 'curl "https://web.archive.org/web/*/{target}"', "purpose": "Historical snapshots"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Domain Intelligence",
                    "estimated_time": "30 min",
                    "steps": [
                        {"tool": "whois", "command": 'whois {target}', "purpose": "Full registration"},
                        {"tool": "dig", "command": 'dig {target} ANY', "purpose": "All DNS records"},
                        {"tool": "nmap", "command": 'nmap -sV -sC -p- {target}', "purpose": "Full port scan"},
                        {"tool": "subfinder", "command": 'subfinder -d {target} -all', "purpose": "All subdomains"},
                        {"tool": "whatweb", "command": 'whatweb -a 3 {target}', "purpose": "Deep technology detection"},
                        {"tool": "shodan", "command": 'curl "https://api.shodan.io/dns/domain/{target}?key=KEY"', "purpose": "Shodan DNS info"},
                        {"tool": "crt_sh", "command": 'curl "https://crt.sh/?q=%.{target}&output=json"', "purpose": "Certificate transparency"},
                        {"tool": "wayback", "command": 'curl "https://web.archive.org/cdx/search/cdx?url={target}&output=json"', "purpose": "Wayback Machine CDX API"},
                        {"tool": "security_headers", "command": 'curl -sI "https://{target}" | grep -i "strict\|content-security\|x-frame\|x-content"', "purpose": "Security headers check"},
                    ],
                },
            ],
        },
    },
    "company": {
        "quick": {
            "phases": [
                {
                    "name": "Company Basic Info",
                    "estimated_time": "5 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}" company', "purpose": "Company overview"},
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}"', "purpose": "LinkedIn company page"},
                        {"tool": "whois", "command": 'whois {domain}', "purpose": "Domain registration"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Company Research",
                    "estimated_time": "20 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}" company OR corporation', "purpose": "Company information"},
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}" company', "purpose": "LinkedIn profile and employees"},
                        {"tool": "sec", "command": 'search site:sec.gov "{target}"', "purpose": "SEC filings (US companies)"},
                        {"tool": "crunchbase", "command": 'search site:crunchbase.com "{target}"', "purpose": "Funding and investors"},
                        {"tool": "glassdoor", "command": 'search site:glassdoor.com "{target}"', "purpose": "Employee reviews"},
                        {"tool": "whois", "command": 'whois {domain}', "purpose": "Domain info"},
                        {"tool": "whatweb", "command": 'whatweb {domain}', "purpose": "Tech stack"},
                    ],
                },
            ],
        },
        "deep": {
            "phases": [
                {
                    "name": "Comprehensive Company Intelligence",
                    "estimated_time": "45 min",
                    "steps": [
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Full web search"},
                        {"tool": "linkedin", "command": 'search site:linkedin.com "{target}"', "purpose": "All LinkedIn data"},
                        {"tool": "sec", "command": 'search site:sec.gov "{target}"', "purpose": "Regulatory filings"},
                        {"tool": "crunchbase", "command": 'search site:crunchbase.com "{target}"', "purpose": "Funding history"},
                        {"tool": "glassdoor", "command": 'search site:glassdoor.com "{target}"', "purpose": "Employee sentiment"},
                        {"tool": "indeed", "command": 'search site:indeed.com "{target}"', "purpose": "Job postings (hiring signals)"},
                        {"tool": "whois", "command": 'whois {domain}', "purpose": "Domain details"},
                        {"tool": "whatweb", "command": 'whatweb -a 3 {domain}', "purpose": "Deep tech stack"},
                        {"tool": "shodan", "command': 'curl "https://api.shodan.io/dns/domain/{domain}?key=KEY"', "purpose": "Infrastructure"},
                        {"tool": "news", "command": 'search "{target}" after:2023', "purpose": "Recent news"},
                    ],
                },
            ],
        },
    },
    "crypto": {
        "quick": {
            "phases": [
                {
                    "name": "Wallet Basic Check",
                    "estimated_time": "3 min",
                    "steps": [
                        {"tool": "etherscan", "command": 'curl "https://api.etherscan.io/api?module=account&action=balance&address={target}&tag=latest"', "purpose": "ETH balance (if ETH wallet)"},
                        {"tool": "blockchain", "command": 'curl "https://blockchain.info/rawaddr/{target}"', "purpose": "BTC balance (if BTC wallet)"},
                        {"tool": "google", "command": 'search "{target}"', "purpose": "Find mentions of wallet"},
                    ],
                },
            ],
        },
        "standard": {
            "phases": [
                {
                    "name": "Full Wallet Investigation",
                    "estimated_time": "15 min",
                    "steps": [
                        {"tool": "etherscan", "command": 'curl "https://api.etherscan.io/api?module=account&action=txlist&address={target}"', "purpose": "ETH transaction history"},
                        {"tool": "blockchain", "command": 'curl "https://blockchain.info/rawaddr/{target}"', "purpose": "BTC transaction history"},
                        {"tool": "google", "command": 'search "{target}" wallet OR address', "purpose": "Web mentions"},
                        {"tool": "debank", "command": 'curl "https://api.debank.com/user/addr/{target}"', "purpose": "Multi-chain portfolio"},
                    ],
                },
            ],
        },
    },
}


def generate_plan(target_type: str, target_value: str, depth: str = "standard",
                  budget: str = "free", purpose: str = "") -> dict:
    """Generate an investigation plan."""
    type_plans = PLANS.get(target_type, PLANS["person"])
    plan = type_plans.get(depth, type_plans.get("standard", next(iter(type_plans.values())) if type_plans else {}))

    # Filter out paid tools if budget is free
    if budget == "free":
        for phase in plan.get("phases", []):
            phase["steps"] = [
                step for step in phase["steps"]
                if step.get("tool") not in ("shodan", "pdl", "hunter")
            ]

    return {
        "target_type": target_type,
        "target_value": target_value,
        "depth": depth,
        "budget": budget,
        "purpose": purpose,
        "phases": plan.get("phases", []),
        "total_phases": len(plan.get("phases", [])),
        "estimated_total_time": "unknown",
        "_phases_count": len(plan.get("phases", [])),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate OSINT investigation plan")
    parser.add_argument("--target-type", required=True, choices=["person", "email", "phone", "username", "domain", "company", "crypto"])
    parser.add_argument("--target-value", required=True, help="Target to investigate")
    parser.add_argument("--depth", default="standard", choices=["quick", "standard", "deep"])
    parser.add_argument("--budget", default="free", choices=["free", "paid"])
    parser.add_argument("--purpose", default="", help="Investigation purpose")
    parser.add_argument("--output", default="investigation_plan.json")

    args = parser.parse_args()

    plan = generate_plan(args.target_type, args.target_value, args.depth, args.budget, args.purpose)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Investigation Plan Generated")
    print(f"  Target: {args.target_value} ({args.target_type})")
    print(f"  Depth: {args.depth}")
    print(f"  Phases: {plan['total_phases']}")
    for i, phase in enumerate(plan["phases"], 1):
        print(f"    {i}. {phase['name']} ({phase['estimated_time']}) - {len(phase['steps'])} steps")
    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
