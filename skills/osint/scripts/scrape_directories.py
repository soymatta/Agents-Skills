#!/usr/bin/env python3
"""Scrape free phone directories without API keys.

Uses web scraping to gather phone info from TrueCaller web, Whitepages,
and regional directories.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch URL content with error handling."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def scrape_google_search(phone_formats: list[str], max_results: int = 5) -> dict:
    """Generate Google search queries and parse basic results."""
    results = {"source": "google_search", "findings": [], "raw_results": []}

    for fmt in phone_formats[:3]:
        encoded = urllib.parse.quote(f'"{fmt}"')
        url = f"https://www.google.com/search?q={encoded}"
        content = fetch_url(url)

        if content:
            # Extract titles and snippets (basic regex parsing)
            titles = re.findall(r"<h3[^>]*>(.*?)</h3>", content)
            snippets = re.findall(r'<div[^>]*class="[^"]*"[^>]*>(.*?)</div>', content)

            for title in titles[:max_results]:
                clean = re.sub(r"<[^>]+>", "", title)
                if clean and len(clean) > 5:
                    results["raw_results"].append({"title": clean, "query": fmt})

    return results


def scrape_truecaller_web(phone: str, country_code: str = "57") -> dict:
    """Scrape TrueCaller web interface."""
    results = {"source": "truecaller_web", "findings": []}

    # TrueCaller web search URL
    formatted = phone.lstrip("+").replace(" ", "")
    url = f"https://www.truecaller.com/search/{country_code}/{formatted}"
    content = fetch_url(url)

    if content:
        # Try to extract name from meta tags or structured data
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
        if name_match:
            results["findings"].append({
                "field": "name",
                "value": name_match.group(1),
                "confidence": "medium"
            })

        # Check for spam/reported
        if "spam" in content.lower() or "fraud" in content.lower():
            results["findings"].append({
                "field": "spam_report",
                "value": "Reported as spam/fraud",
                "confidence": "low"
            })

        # Extract any location info
        location_match = re.search(r'"address locality"\s*:\s*"([^"]+)"', content)
        if location_match:
            results["findings"].append({
                "field": "location",
                "value": location_match.group(1),
                "confidence": "medium"
            })

    return results


def scrape_whitepages(phone: str) -> dict:
    """Scrape Whitepages for phone info."""
    results = {"source": "whitepages", "findings": []}

    formatted = phone.lstrip("+").replace(" ", "").replace("-", "")
    url = f"https://www.whitepages.com/phone/{formatted}"
    content = fetch_url(url)

    if content:
        # Extract name
        name_match = re.search(r'<span[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</span>', content)
        if name_match:
            clean = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()
            if clean:
                results["findings"].append({
                    "field": "name",
                    "value": clean,
                    "confidence": "medium"
                })

        # Extract location
        location_match = re.search(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</span>', content)
        if location_match:
            clean = re.sub(r"<[^>]+>", "", location_match.group(1)).strip()
            if clean:
                results["findings"].append({
                    "field": "location",
                    "value": clean,
                    "confidence": "medium"
                })

    return results


def scrapeCallerID_app(phone: str) -> dict:
    """Scrape callerid.com or similar free services."""
    results = {"source": "callerid_app", "findings": []}

    formatted = phone.lstrip("+").replace(" ", "")
    url = f"https://www.calleridtest.com/lookup/{formatted}"
    content = fetch_url(url)

    if content:
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
        if name_match:
            results["findings"].append({
                "field": "name",
                "value": name_match.group(1),
                "confidence": "low"
            })

    return results


def scrape_8x8(phone: str) -> dict:
    """Scrape 8x8 spam database."""
    results = {"source": "8x8_spam", "findings": []}

    formatted = phone.lstrip("+").replace(" ", "")
    url = f"https://www.8x8.com/lookup/{formatted}"
    content = fetch_url(url)

    if content and ("spam" in content.lower() or "scam" in content.lower()):
        results["findings"].append({
            "field": "spam_report",
            "value": "Found in spam database",
            "confidence": "medium"
        })

    return results


def scrape_whoCalledMe(phone: str) -> dict:
    """Scrape whocalledme.com."""
    results = {"source": "whocalledme", "findings": []}

    formatted = phone.lstrip("+").replace(" ", "")
    url = f"https://www.whocalledme.com/number/{formatted}"
    content = fetch_url(url)

    if content:
        # Extract reports
        reports = re.findall(r'"comment"\s*:\s*"([^"]+)"', content)
        if reports:
            results["findings"].append({
                "field": "user_reports",
                "value": reports[:3],
                "confidence": "user_reported"
            })

    return results


def run_scraping(phone: str, scrapers: Optional[list[str]] = None) -> dict:
    """Run all scrapers on a phone number."""
    from phone_parser import detect_country, clean_phone

    cleaned = clean_phone(phone)
    country = detect_country(cleaned)
    country_code = "57"  # Default to Colombia

    if country:
        code = cleaned.lstrip("+")
        for ccode in ["57", "52", "54", "56", "51", "593", "591", "58", "34", "55"]:
            if code.startswith(ccode):
                country_code = ccode
                break

    all_scrapers = {
        "google": lambda: scrape_google_search([phone, cleaned]),
        "truecaller": lambda: scrape_truecaller_web(cleaned, country_code),
        "whitepages": lambda: scrape_whitepages(cleaned),
        "callerid": lambda: scrapeCallerID_app(cleaned),
        "8x8": lambda: scrape_8x8(cleaned),
        "whocalledme": lambda: scrape_whoCalledMe(cleaned),
    }

    if scrapers:
        active = {k: v for k, v in all_scrapers.items() if k in scrapers}
    else:
        active = all_scrapers

    combined = {
        "phone": phone,
        "cleaned": cleaned,
        "country": country,
        "scrapers_run": list(active.keys()),
        "results": {},
        "all_findings": [],
    }

    for name, scraper_fn in active.items():
        try:
            result = scraper_fn()
            combined["results"][name] = result
            combined["all_findings"].extend(result.get("findings", []))
        except Exception as e:
            combined["results"][name] = {"error": str(e)}

    return combined


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape free phone directories")
    parser.add_argument("phone", nargs="?", help="Phone number to investigate")
    parser.add_argument("--scrapers", nargs="+", help="Specific scrapers to run")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true", help="List available scrapers")

    args = parser.parse_args()

    if args.list:
        print("Available scrapers:")
        print("  google      - Google search results")
        print("  truecaller  - TrueCaller web lookup")
        print("  whitepages  - Whitepages lookup")
        print("  callerid    - CallerID lookup")
        print("  8x8         - 8x8 spam database")
        print("  whocalledme - WhoCalledMe reports")
        return

    if not args.phone:
        phone = input("Enter phone number: ").strip()
    else:
        phone = args.phone

    print(f"\n  Running scrapers for: {phone}")
    print(f"{'='*50}")

    result = run_scraping(phone, args.scrapers)

    if args.json:
        # Convert for JSON serialization
        json_result = {
            "phone": result["phone"],
            "cleaned": result["cleaned"],
            "country": result["country"],
            "scrapers_run": result["scrapers_run"],
            "total_findings": len(result["all_findings"]),
            "findings": result["all_findings"],
            "results": result["results"],
        }
        print(json.dumps(json_result, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"  Scrapers run: {', '.join(result['scrapers_run'])}")
        print(f"  Total findings: {len(result['all_findings'])}")

        if result["all_findings"]:
            print(f"\n  Findings:")
            for f in result["all_findings"]:
                print(f"    [{f.get('confidence', '?')}] {f['field']}: {f['value']}")
        else:
            print(f"\n  No findings from free scrapers.")
            print(f"  Tip: Use websearch tool for better results.")

        # Show which scrapers had results
        print(f"\n  Scraper Results:")
        for name, res in result["results"].items():
            findings_count = len(res.get("findings", []))
            status = f"OK ({findings_count} findings)" if findings_count > 0 else "No data"
            if "error" in res:
                status = f"Error: {res['error'][:50]}"
            print(f"    {name:<15} {status}")

    print()


if __name__ == "__main__":
    main()
