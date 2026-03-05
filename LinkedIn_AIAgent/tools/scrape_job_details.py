"""
Tool: scrape_job_details.py
Layer 3 — Execution
Purpose: Scrape the full job description from a single LinkedIn job post URL.
Handles JS-rendered pages via ScraperAPI with render=true.
"""

import os
import json
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
SCRAPER_BASE = "http://api.scraperapi.com"


def scrape_job_page(url: str) -> str:
    """Fetch full rendered HTML of a LinkedIn job page."""
    if not SCRAPER_API_KEY:
        print("[scrape_job_details] WARNING: SCRAPER_API_KEY not set. Returning dummy HTML for testing.")
        return """
        <html>
            <body>
                <h1 class="top-card-layout__title">Senior Validation & Integration Engineer</h1>
                <a class="topcard__org-name-link">Valeo</a>
                <span class="topcard__flavor--bullet">Cairo, Egypt (Hybrid)</span>
                <span class="posted-time-ago__text">Posted 2 days ago</span>
                <div class="show-more-less-html__markup">
                    We are hiring a Senior Validation & Integration Engineer to work on automotive security projects.
                    Requirements:
                    - 3+ years in Embedded Software Validation
                    - Strong Python and Robot Framework scripting
                    - Expertise in CANoe, CAPL, and UDS (ISO 14229)
                    - Experience with Cybersecurity Testing and HSM/HSE
                    - Familiarity with JIRA and Git
                </div>
            </body>
        </html>
        """

    # Normalize URL to public job view format
    if "linkedin.com/jobs/view" not in url and "linkedin.com/jobs/" in url:
        # Try to extract job ID and reconstruct clean URL
        parts = url.split("/")
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) > 6:
                url = f"https://www.linkedin.com/jobs/view/{part}/"
                break

    print(f"[scrape_job_details] Fetching: {url}")
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "true",
        "country_code": "us",
    }
    response = requests.get(SCRAPER_BASE, params=params, timeout=60)
    response.raise_for_status()
    return response.text


def parse_job_detail(html: str, url: str) -> dict:
    """Extract structured data from a job detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    for selector in ["h1.top-card-layout__title", "h1.t-24", "h1"]:
        el = soup.select_one(selector)
        if el:
            title = el.get_text(strip=True)
            break

    # Company
    company = ""
    for selector in ["a.topcard__org-name-link", "a.top-card-layout__card-relation-link", ".topcard__org-name-link"]:
        el = soup.select_one(selector)
        if el:
            company = el.get_text(strip=True)
            break

    # Location
    location = ""
    for selector in [".topcard__flavor--bullet", ".top-card-layout__bullet", "span.topcard__flavor"]:
        el = soup.select_one(selector)
        if el:
            location = el.get_text(strip=True)
            break

    # Posted date
    posted = ""
    el = soup.find("span", class_="posted-time-ago__text") or soup.find("time")
    if el:
        posted = el.get_text(strip=True)

    # Full description
    description = ""
    for selector in [
        "div.show-more-less-html__markup",
        "div.description__text",
        "section.description",
        "div.job-description"
    ]:
        el = soup.select_one(selector)
        if el:
            description = el.get_text(separator="\n", strip=True)
            break

    if not description:
        # Last resort: grab all paragraph text
        paragraphs = soup.find_all(["p", "li"])
        description = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)

    return {
        "title": title or "Unknown",
        "company": company or "Unknown",
        "location": location or "Unknown",
        "posted_date": posted,
        "url": url,
        "description_raw": description
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape a LinkedIn job post")
    parser.add_argument("--url", required=True, help="LinkedIn job URL")
    parser.add_argument("--output", default="data/job_detail.json", help="Output file path")
    args = parser.parse_args()

    html = scrape_job_page(args.url)
    job = parse_job_detail(html, args.url)

    if not job["description_raw"]:
        print("[scrape_job_details] WARNING: Description empty. LinkedIn may have blocked the request.")
        print("[scrape_job_details] Try appending '?trk=public_jobs_topcard' to URL")

    with open(args.output, "w") as f:
        json.dump(job, f, indent=2)

    print(f"[scrape_job_details] Saved job detail to {args.output}")
    print(f"  Title: {job['title']} @ {job['company']}")
    print(f"  Description length: {len(job['description_raw'])} chars")


if __name__ == "__main__":
    main()
