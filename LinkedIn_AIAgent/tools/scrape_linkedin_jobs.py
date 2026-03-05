"""
Tool: scrape_linkedin_jobs.py
Layer 3 — Execution
Purpose: Search LinkedIn public job listings and return structured results.
Scrapes LinkedIn's guest jobs API directly (no login required).
Falls back to ScraperAPI if direct requests are blocked.
"""

import os
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

# LinkedIn public guest API — returns HTML job cards, no JS rendering needed
LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={keywords}&location={location}&f_TPR={tpr}&start={start}"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/jobs/search/",
}


def build_url(keywords: str, location: str, tpr: str = "r2592000", start: int = 0) -> str:
    return LINKEDIN_SEARCH_URL.format(
        keywords=quote(keywords),
        location=quote(location),
        tpr=tpr,
        start=start,
    )


def fetch_direct(url: str) -> str:
    """Fetch LinkedIn directly with browser-like headers."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_via_scraperapi(url: str) -> str:
    """Fallback: route through ScraperAPI."""
    params = {"api_key": SCRAPER_API_KEY, "url": url, "country_code": "us"}
    response = requests.get("http://api.scraperapi.com", params=params, timeout=60)
    response.raise_for_status()
    return response.text


def parse_job_cards(html: str) -> list[dict]:
    """Parse job cards from LinkedIn guest API HTML response."""
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    cards = soup.find_all("div", class_="base-card")
    if not cards:
        cards = soup.find_all("li")

    for card in cards:
        try:
            title_el = card.find("h3", class_="base-search-card__title") or card.find("h3")
            company_el = card.find("h4", class_="base-search-card__subtitle") or card.find("h4")
            location_el = card.find("span", class_="job-search-card__location")
            link_el = card.find("a", class_="base-card__full-link") or card.find("a")
            date_el = card.find("time")
            snippet_el = card.find("p")

            title = title_el.get_text(strip=True) if title_el else ""
            url = link_el["href"].split("?")[0] if link_el and link_el.get("href") else ""

            if not title or not url:
                continue

            jobs.append({
                "title": title,
                "company": company_el.get_text(strip=True) if company_el else "N/A",
                "location": location_el.get_text(strip=True) if location_el else "N/A",
                "url": url,
                "posted": date_el.get("datetime", "") if date_el else "",
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        except Exception:
            continue

    return jobs


def search_jobs(keywords: str, location: str = "Remote", limit: int = 20, tpr: str = "r2592000") -> list[dict]:
    """Main function: search LinkedIn and return job list."""
    all_jobs = []
    start = 0
    batch_size = 25  # LinkedIn returns 25 per page

    print(f"[scrape_linkedin_jobs] Searching: {keywords} | Location: {location}")

    while len(all_jobs) < limit:
        url = build_url(keywords, location, tpr, start)

        # Try direct first, fall back to ScraperAPI
        html = None
        try:
            html = fetch_direct(url)
            print(f"[scrape_linkedin_jobs] Direct fetch succeeded (start={start})")
        except requests.exceptions.HTTPError as e:
            if SCRAPER_API_KEY:
                print(f"[scrape_linkedin_jobs] Direct fetch blocked ({e.response.status_code}), trying ScraperAPI...")
                try:
                    html = fetch_via_scraperapi(url)
                    print(f"[scrape_linkedin_jobs] ScraperAPI fetch succeeded")
                except Exception as e2:
                    print(f"[scrape_linkedin_jobs] ScraperAPI also failed: {e2}")
                    break
            else:
                print(f"[scrape_linkedin_jobs] Direct fetch blocked and no SCRAPER_API_KEY set.")
                break
        except Exception as e:
            print(f"[scrape_linkedin_jobs] Fetch error: {e}")
            break

        if not html:
            break

        batch = parse_job_cards(html)
        if not batch:
            print(f"[scrape_linkedin_jobs] No more job cards found at start={start}")
            break

        all_jobs.extend(batch)
        print(f"[scrape_linkedin_jobs] Fetched {len(batch)} jobs (total: {len(all_jobs)})")

        if len(batch) < batch_size:
            break  # Last page

        start += batch_size
        time.sleep(2)  # Polite delay between pages

    result = all_jobs[:limit]
    print(f"[scrape_linkedin_jobs] Done. Returning {len(result)} jobs.")
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn job listings")
    parser.add_argument("--keywords", required=True, help="Job search keywords")
    parser.add_argument("--location", default="Remote", help="Job location")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--tpr", default="r2592000", help="Time filter: r86400=24h, r604800=week, r2592000=month")
    parser.add_argument("--output", default="data/raw_jobs.json", help="Output file path")
    args = parser.parse_args()

    jobs = search_jobs(args.keywords, args.location, args.limit, args.tpr)

    with open(args.output, "w") as f:
        json.dump(jobs, f, indent=2)

    print(f"[scrape_linkedin_jobs] Saved {len(jobs)} jobs to {args.output}")


if __name__ == "__main__":
    main()
