#!/usr/bin/env python3
"""Search job boards using scraping, APIs, and web search for unified results."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path


def ensure_deps():
    """Install dependencies if not available."""
    deps = ["requests", "beautifulsoup4"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_").split("[")[0])
        except ImportError:
            print(f"  Installing {dep}...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])


# ---------------------------------------------------------------------------
# Salary extraction
# ---------------------------------------------------------------------------

_SALARY_PATTERNS = [
    # USD ranges: "$70,000 - $90,000", "$70K-$90K", "$70k - $90k per year"
    (r"\$\s?([\d,]+(?:\.\d+)?)\s*[kK]\s*[-–to]+\s*\$\s?([\d,]+(?:\.\d+)?)\s?[kK]", "USD", 1000),
    (r"\$\s?([\d,]+(?:\.\d+)?)\s*[-–to]+\s*\$\s?([\d,]+(?:\.\d+)?)\s*(?:per\s+year|/year|yr|annually|a\.?y\.?)?", "USD", 1),
    (r"\$\s?([\d,]+(?:\.\d+)?)\s*[kK]\s*(?:per\s+year|/year|yr|annually)", "USD", 1000),
    (r"\$\s?([\d,]+(?:\.\d+)?)\s*(?:per\s+hour|/hour|hr|/h)", "USD", 1),
    # EUR
    (r"€\s?([\d.,]+)\s*[-–to]+\s*€\s?([\d.,]+)", "EUR", 1),
    (r"([\d.,]+)\s*[-–to]+\s*([\d.,]+)\s*€", "EUR", 1),
    # COP (Colombian pesos)
    (r"\$\s?([\d.,]+)\s*[-–to]+\s*\$\s?([\d.,]+)\s*(?:COP|pesos|COP/mes)", "COP", 1),
    (r"([\d.,]+)\s*[-–to]+\s*([\d.,]+)\s*(?:COP|pesos)", "COP", 1),
    # MXN
    (r"\$\s?([\d.,]+)\s*[-–to]+\s*\$\s?([\d.,]+)\s*(?:MXN|pesos mexicanos)", "MXN", 1),
    # Generic large numbers (likely annual salary)
    (r"(?:salary|compensation|pay|remuneration)[:\s]*\$?\s?([\d,]+(?:\.\d+)?)\s*[-–to]+\s*\$?\s?([\d,]+(?:\.\d+)?)", "USD", 1),
]


def extract_salary(text: str) -> tuple[int | None, int | None, str]:
    """Extract salary range from text. Returns (min, max, currency)."""
    if not text:
        return None, None, "USD"

    for pattern, currency, multiplier in _SALARY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                raw_min = match.group(1).replace(",", "").replace(".", "")
                raw_max = match.group(2).replace(",", "").replace(".", "")
                salary_min = int(float(raw_min) * multiplier)
                salary_max = int(float(raw_max) * multiplier)
                if salary_min > 0 and salary_max >= salary_min:
                    return salary_min, salary_max, currency
            except (ValueError, IndexError):
                continue

    return None, None, "USD"


# ---------------------------------------------------------------------------
# Description fetching
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_job_description(url: str, timeout: int = 10) -> str:
    """Fetch a job detail page and extract the description text."""
    if not url:
        return ""

    import requests
    from bs4 import BeautifulSoup

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try common description containers
        selectors = [
            ("div", {"class": re.compile(r"description|jobDescription|job-description|desc", re.I)}),
            ("div", {"id": re.compile(r"description|jobDescription|job-description", re.I)}),
            ("section", {"class": re.compile(r"description|jobDescription|job-description", re.I)}),
            ("div", {"class": re.compile(r"content|details|body", re.I)}),
            ("article", {}),
        ]

        for tag_name, attrs in selectors:
            el = soup.find(tag_name, attrs) if attrs else soup.find(tag_name)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 100:  # Likely a real description
                    return text[:3000]

        # Fallback: largest text block
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)[:3000]

    except Exception:
        pass

    return ""


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _load_cache(cache_dir: Path) -> dict:
    cache_file = cache_dir / "description_cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache_dir: Path, cache: dict):
    cache_file = cache_dir / "description_cache.json"
    cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_indeed(keywords: str, location: str, max_results: int = 50,
                  fetch_descriptions: bool = True, cache: dict | None = None,
                  cache_dir: Path | None = None) -> list[dict]:
    """Scrape Indeed job listings with description fetching."""
    import requests
    from bs4 import BeautifulSoup

    jobs = []
    base_url = "https://www.indeed.com/jobs"
    params = {"q": keywords, "l": location, "start": 0, "limit": min(max_results, 50)}

    try:
        while len(jobs) < max_results:
            resp = requests.get(base_url, params=params, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_="job_seen_beacon")
            if not cards:
                break

            for card in cards:
                try:
                    title_el = card.find("h2", class_="jobTitle")
                    company_el = card.find("span", class_="companyName")
                    location_el = card.find("div", class_="companyLocation")
                    link_el = card.find("a", id=True)
                    salary_el = card.find("div", class_="salary-snippet") or card.find("span", class_="salaryText")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc = location_el.get_text(strip=True) if location_el else ""
                    job_url = f"https://www.indeed.com{link_el['href']}" if link_el and link_el.get("href") else ""
                    salary_text = salary_el.get_text(strip=True) if salary_el else ""

                    if not title:
                        continue

                    # Fetch description from detail page
                    description = ""
                    salary_min, salary_max, currency = None, None, "USD"

                    if fetch_descriptions and job_url:
                        ck = _cache_key(job_url)
                        if cache and ck in cache:
                            description = cache[ck].get("description", "")
                            salary_min = cache[ck].get("salary_min")
                            salary_max = cache[ck].get("salary_max")
                            currency = cache[ck].get("salary_currency", "USD")
                        else:
                            description = fetch_job_description(job_url)
                            if description:
                                s_min, s_max, cur = extract_salary(description)
                                if s_min:
                                    salary_min, salary_max, currency = s_min, s_max, cur
                                if cache is not None:
                                    cache[ck] = {
                                        "description": description[:3000],
                                        "salary_min": salary_min,
                                        "salary_max": salary_max,
                                        "salary_currency": currency,
                                    }
                            time.sleep(0.5)

                    # Also try snippet salary
                    if not salary_min and salary_text:
                        s_min, s_max, cur = extract_salary(salary_text)
                        if s_min:
                            salary_min, salary_max, currency = s_min, s_max, cur

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "job_type": "",
                        "description": description[:3000],
                        "url": job_url,
                        "posted": "",
                        "site": "indeed",
                        "is_remote": "remote" in loc.lower(),
                    })
                except Exception:
                    continue

            params["start"] += 10
            time.sleep(1)

    except Exception as e:
        print(f"  Error on Indeed: {e}")

    return jobs[:max_results]


def scrape_linkedin(keywords: str, location: str, max_results: int = 50,
                    fetch_descriptions: bool = True, cache: dict | None = None,
                    cache_dir: Path | None = None) -> list[dict]:
    """Scrape LinkedIn job listings with description fetching."""
    import requests
    from bs4 import BeautifulSoup

    jobs = []
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {"keywords": keywords, "location": location, "start": 0, "sortBy": "DD"}

    try:
        while len(jobs) < max_results:
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break

            for card in cards:
                try:
                    title_el = card.find("h3", class_="base-search-card__title")
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    location_el = card.find("span", class_="job-search-card__location")
                    link_el = card.find("a", class_="base-card__full-link")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc = location_el.get_text(strip=True) if location_el else ""
                    job_url = (link_el["href"].split("?")[0] if link_el and link_el.get("href") else "")

                    if not title:
                        continue

                    description = ""
                    salary_min, salary_max, currency = None, None, "USD"

                    if fetch_descriptions and job_url:
                        ck = _cache_key(job_url)
                        if cache and ck in cache:
                            description = cache[ck].get("description", "")
                            salary_min = cache[ck].get("salary_min")
                            salary_max = cache[ck].get("salary_max")
                            currency = cache[ck].get("salary_currency", "USD")
                        else:
                            description = fetch_job_description(job_url)
                            if description:
                                s_min, s_max, cur = extract_salary(description)
                                if s_min:
                                    salary_min, salary_max, currency = s_min, s_max, cur
                                if cache is not None:
                                    cache[ck] = {
                                        "description": description[:3000],
                                        "salary_min": salary_min,
                                        "salary_max": salary_max,
                                        "salary_currency": currency,
                                    }
                            time.sleep(1)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "job_type": "",
                        "description": description[:3000],
                        "url": job_url,
                        "posted": "",
                        "site": "linkedin",
                        "is_remote": "remote" in loc.lower(),
                    })
                except Exception:
                    continue

            params["start"] += 25
            time.sleep(2)

    except Exception as e:
        print(f"  Error on LinkedIn: {e}")

    return jobs[:max_results]


def scrape_computrabajo(keywords: str, location: str, max_results: int = 50,
                        fetch_descriptions: bool = True, cache: dict | None = None,
                        cache_dir: Path | None = None) -> list[dict]:
    """Scrape Computrabajo (LatAm focused) with description fetching."""
    import requests
    from bs4 import BeautifulSoup

    jobs = []
    country_domains = {
        "colombia": "co", "mexico": "mx", "argentina": "ar",
        "peru": "pe", "chile": "cl", "españa": "es", "spain": "es",
    }

    country = "co"
    for key, domain in country_domains.items():
        if key in location.lower():
            country = domain
            break

    base_url = f"https://www.computrabajo.com.{country}/trabajo-de-{keywords.replace(' ', '-')}"

    try:
        resp = requests.get(base_url, headers=_HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("article", class_="box_list")

            for card in cards[:max_results]:
                try:
                    title_el = card.find("a", class_="js-o-link")
                    company_el = card.find("span", class_="fc_base")
                    location_el = card.find("span", class_="fc_gray")
                    link_el = card.find("a", class_="js-o-link")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc = location_el.get_text(strip=True) if location_el else ""
                    job_url = f"https://www.computrabajo.com.{country}{link_el['href']}" if link_el and link_el.get("href") else ""

                    if not title:
                        continue

                    description = ""
                    salary_min, salary_max, currency = None, None, "COP"

                    if fetch_descriptions and job_url:
                        ck = _cache_key(job_url)
                        if cache and ck in cache:
                            description = cache[ck].get("description", "")
                            salary_min = cache[ck].get("salary_min")
                            salary_max = cache[ck].get("salary_max")
                            currency = cache[ck].get("salary_currency", "COP")
                        else:
                            description = fetch_job_description(job_url)
                            if description:
                                s_min, s_max, cur = extract_salary(description)
                                if s_min:
                                    salary_min, salary_max, currency = s_min, s_max, cur
                                if cache is not None:
                                    cache[ck] = {
                                        "description": description[:3000],
                                        "salary_min": salary_min,
                                        "salary_max": salary_max,
                                        "salary_currency": currency,
                                    }
                            time.sleep(0.5)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "job_type": "",
                        "description": description[:3000],
                        "url": job_url,
                        "posted": "",
                        "site": "computrabajo",
                        "is_remote": "remoto" in loc.lower(),
                    })
                except Exception:
                    continue

    except Exception as e:
        print(f"  Error on Computrabajo: {e}")

    return jobs[:max_results]


def scrape_glassdoor(keywords: str, location: str, max_results: int = 50,
                     fetch_descriptions: bool = True, cache: dict | None = None,
                     cache_dir: Path | None = None) -> list[dict]:
    """Scrape Glassdoor job listings with description fetching."""
    import requests
    from bs4 import BeautifulSoup

    jobs = []
    url = "https://www.glassdoor.com/Job/jobs.htm"
    params = {"sc.keyword": keywords, "locT": "", "locId": "", "locKeyword": location}

    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li", class_="JobsList_jobListItem__wjTHv")

            for card in cards[:max_results]:
                try:
                    title_el = card.find("a", class_="JobCard_jobTitle__GLyJ1")
                    company_el = card.find("span", class_="EmployerProfile_compactEmployerName__LEl42")
                    location_el = card.find("div", class_="JobCard_jobLocation__BgrqO")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc = location_el.get_text(strip=True) if location_el else ""
                    job_url = f"https://www.glassdoor.com{title_el['href']}" if title_el and title_el.get("href") else ""

                    if not title:
                        continue

                    description = ""
                    salary_min, salary_max, currency = None, None, "USD"

                    if fetch_descriptions and job_url:
                        ck = _cache_key(job_url)
                        if cache and ck in cache:
                            description = cache[ck].get("description", "")
                            salary_min = cache[ck].get("salary_min")
                            salary_max = cache[ck].get("salary_max")
                            currency = cache[ck].get("salary_currency", "USD")
                        else:
                            description = fetch_job_description(job_url)
                            if description:
                                s_min, s_max, cur = extract_salary(description)
                                if s_min:
                                    salary_min, salary_max, currency = s_min, s_max, cur
                                if cache is not None:
                                    cache[ck] = {
                                        "description": description[:3000],
                                        "salary_min": salary_min,
                                        "salary_max": salary_max,
                                        "salary_currency": currency,
                                    }
                            time.sleep(0.5)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "job_type": "",
                        "description": description[:3000],
                        "url": job_url,
                        "posted": "",
                        "site": "glassdoor",
                        "is_remote": "remote" in loc.lower(),
                    })
                except Exception:
                    continue

    except Exception as e:
        print(f"  Error on Glassdoor: {e}")

    return jobs[:max_results]


def scrape_remotok(keywords: str, max_results: int = 50,
                   fetch_descriptions: bool = True, cache: dict | None = None,
                   cache_dir: Path | None = None) -> list[dict]:
    """Scrape RemoteOK (remote jobs). Already provides descriptions via API."""
    import requests

    jobs = []
    url = "https://remoteok.com/api"

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for item in data[1:max_results]:
                try:
                    desc = item.get("description", "")[:3000]
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    currency = item.get("currency", "USD")

                    # Try salary extraction from description if not in API
                    if not salary_min and desc:
                        s_min, s_max, cur = extract_salary(desc)
                        if s_min:
                            salary_min, salary_max, currency = s_min, s_max, cur

                    jobs.append({
                        "title": item.get("position", ""),
                        "company": item.get("company", ""),
                        "location": item.get("location", "Remote"),
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "job_type": "",
                        "description": desc,
                        "url": f"https://remoteok.com{item.get('url', '')}",
                        "posted": item.get("date", ""),
                        "site": "remoteok",
                        "is_remote": True,
                    })
                except Exception:
                    continue

    except Exception as e:
        print(f"  Error on RemoteOK: {e}")

    return jobs[:max_results]


# ---------------------------------------------------------------------------
# Web search integration (company career pages)
# ---------------------------------------------------------------------------

def parse_websearch_results(websearch_json: str | list[dict]) -> list[dict]:
    """Parse websearch tool results into unified job format.

    Accepts JSON string or list of dicts with keys: title, url, snippet/description.
    The agent should run websearch queries like:
      '"{{COMPANY}}" careers {{ROLE}}'
      '"hiring" {{ROLE}} site:example.com/careers'
    And pass the results here.
    """
    if isinstance(websearch_json, str):
        results = json.loads(websearch_json)
    else:
        results = websearch_json

    jobs = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("snippet", "") or r.get("description", "") or r.get("text", "")

        # Try to extract company from URL domain
        company = ""
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            company = domain.split(".")[0].title()

        # Extract salary from snippet
        salary_min, salary_max, currency = extract_salary(snippet)

        jobs.append({
            "title": title,
            "company": company,
            "location": "",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": currency,
            "job_type": "",
            "description": snippet[:3000],
            "url": url,
            "posted": "",
            "site": "websearch",
            "is_remote": True,
        })

    return jobs


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def search_jobs(
    keywords: str,
    location: str = "Remote",
    max_results: int = 50,
    remote_only: bool = False,
    sites: list[str] | None = None,
    years_experience: int | None = None,
    fetch_descriptions: bool = True,
    websearch_results: list[dict] | None = None,
    use_cache: bool = True,
) -> list[dict]:
    """Search multiple job boards via scraping + web search."""
    ensure_deps()

    if sites is None:
        sites = ["indeed", "linkedin", "computrabajo", "glassdoor", "remoteok"]

    # Setup cache
    cache_dir = Path(tempfile.mkdtemp(prefix="jobfinder_cache_"))
    cache = _load_cache(cache_dir) if use_cache else {}

    all_jobs = []

    scrapers = {
        "indeed": lambda: scrape_indeed(keywords, location, max_results, fetch_descriptions, cache, cache_dir),
        "linkedin": lambda: scrape_linkedin(keywords, location, max_results, fetch_descriptions, cache, cache_dir),
        "computrabajo": lambda: scrape_computrabajo(keywords, location, max_results, fetch_descriptions, cache, cache_dir),
        "glassdoor": lambda: scrape_glassdoor(keywords, location, max_results, fetch_descriptions, cache, cache_dir),
        "remoteok": lambda: scrape_remotok(keywords, max_results, fetch_descriptions, cache, cache_dir),
    }

    for site in sites:
        if site in scrapers:
            print(f"  Searching {site}...")
            try:
                results = scrapers[site]()
                all_jobs.extend(results)
                print(f"    Found: {len(results)} jobs")
                time.sleep(1)
            except Exception as e:
                print(f"    Error: {e}")

    # Add websearch results if provided
    if websearch_results:
        print(f"  Processing {len(websearch_results)} web search results...")
        ws_jobs = parse_websearch_results(websearch_results)
        all_jobs.extend(ws_jobs)
        print(f"    Added: {len(ws_jobs)} jobs from web search")

    # Save cache
    if use_cache and cache:
        _save_cache(cache_dir, cache)

    # Deduplicate by title + company (fuzzy)
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        title_key = re.sub(r"[^a-z0-9]", "", job["title"].lower())
        company_key = re.sub(r"[^a-z0-9]", "", job["company"].lower())
        key = (title_key, company_key)
        if key not in seen and title_key:
            seen.add(key)
            unique_jobs.append(job)

    # Filter by experience if provided
    if years_experience is not None:
        for job in unique_jobs:
            desc = job.get("description", "").lower()
            exp_match = re.search(r"(\d+)\+?\s*years?", desc)
            if exp_match:
                required_years = int(exp_match.group(1))
                job["experience_viable"] = years_experience >= required_years
                job["required_years"] = required_years
            else:
                job["experience_viable"] = True
                job["required_years"] = None

    # Filter remote-only if requested
    if remote_only:
        unique_jobs = [j for j in unique_jobs if j.get("is_remote")]

    # Cleanup temp cache directory
    shutil.rmtree(cache_dir, ignore_errors=True)
    return unique_jobs[:max_results]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Search jobs across multiple boards + web search")
    parser.add_argument("--keywords", "-k", required=True, help="Search keywords")
    parser.add_argument("--location", "-l", default="Remote", help="Location")
    parser.add_argument("--max-results", "-n", type=int, default=50, help="Max results")
    parser.add_argument("--remote-only", action="store_true", help="Remote jobs only")
    parser.add_argument("--sites", "-s", nargs="+",
                        default=["indeed", "linkedin", "computrabajo", "glassdoor", "remoteok"],
                        help="Sites to search")
    parser.add_argument("--experience", "-e", type=int, default=None,
                        help="User years of experience (for filtering)")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    parser.add_argument("--no-descriptions", action="store_true",
                        help="Skip description fetching (faster)")
    parser.add_argument("--websearch-json", default=None,
                        help="Path to JSON file with websearch results")

    args = parser.parse_args()

    print(f"  Searching '{args.keywords}' in {args.location}...")
    print(f"  Sites: {', '.join(args.sites)}")
    if args.experience is not None:
        print(f"  User experience: {args.experience} years")

    # Load websearch results if provided
    websearch_results = None
    if args.websearch_json:
        ws_path = Path(args.websearch_json)
        if ws_path.exists():
            websearch_results = json.loads(ws_path.read_text(encoding="utf-8"))
            print(f"  Web search results: {len(websearch_results)} entries")

    jobs = search_jobs(
        keywords=args.keywords,
        location=args.location,
        max_results=args.max_results,
        remote_only=args.remote_only,
        sites=args.sites,
        years_experience=args.experience,
        fetch_descriptions=not args.no_descriptions,
        websearch_results=websearch_results,
    )

    # Sort by experience viability
    if args.experience is not None:
        jobs.sort(key=lambda x: (x.get("experience_viable", True), x.get("title", "")), reverse=True)

    # Output
    if args.output:
        output_path = Path(args.output)
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="jobfinder_"))
        output_path = temp_dir / "results.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Found {len(jobs)} jobs. Saved to: {output_path}")

    # Summary
    viable_count = sum(1 for j in jobs if j.get("experience_viable", True))
    desc_count = sum(1 for j in jobs if j.get("description"))
    salary_count = sum(1 for j in jobs if j.get("salary_min"))

    for i, job in enumerate(jobs[:5], 1):
        salary = ""
        if job.get("salary_min") and job.get("salary_max"):
            salary = f" | {job['salary_currency']} {job['salary_min']:,}-{job['salary_max']:,}"
        viability = "V" if job.get("experience_viable", True) else "X"
        has_desc = "D" if job.get("description") else "-"
        print(f"  [{viability}][{has_desc}] {i}. {job['title']} @ {job['company']} ({job['location']}){salary}")

    if len(jobs) > 5:
        print(f"  ... and {len(jobs) - 5} more")

    print(f"\n  Stats: {desc_count}/{len(jobs)} with descriptions, {salary_count}/{len(jobs)} with salary")
    if args.experience is not None:
        print(f"  Viable: {viable_count}, Require more experience: {len(jobs) - viable_count}")

    print(f"\nTEMP_DIR={output_path.parent}")


if __name__ == "__main__":
    main()
