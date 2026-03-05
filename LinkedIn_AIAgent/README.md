# 🔍 LinkedIn Job Agent

An AI-powered job hunting agent built on a 3-layer architecture:
scraping LinkedIn for relevant roles and extracting the exact skills you need.

---

## Architecture

```
linkedin-agent/
├── workflows/                   # Layer 1 — Instructions (Markdown)
│   ├── find_relevant_jobs.md    # How to search and rank job listings
│   ├── scrape_job_skills.md     # How to analyze a specific job's skills
│   └── setup.md                 # First-time setup guide
│
├── tools/                       # Layer 3 — Execution (Python scripts)
│   ├── scrape_linkedin_jobs.py  # Search LinkedIn, return job listings
│   ├── scrape_job_details.py    # Fetch full job description from URL
│   ├── extract_skills.py        # NLP skill extraction from descriptions
│   ├── match_jobs_to_experience.py  # Score/rank jobs + gap analysis
│   └── load_experience.py       # Load & validate your profile
│
├── agent.py                     # Layer 2 — The Agent (Decision-Maker)
├── data/
│   ├── experience_template.json # Copy → experience.json and fill in
│   ├── experience.json          # YOUR profile (gitignored)
│   ├── raw_jobs.json            # Scraped job listings (auto-generated)
│   ├── matched_jobs.json        # Ranked results (auto-generated)
│   ├── job_detail.json          # Specific job data (auto-generated)
│   └── job_skills.json          # Extracted skills (auto-generated)
│
├── .env.example                 # Copy → .env and fill in API keys
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Set up API keys
```bash
cp .env.example .env
# Edit .env with your keys:
# - ANTHROPIC_API_KEY (from console.anthropic.com)
# - SCRAPER_API_KEY (from scraperapi.com — free tier available)
```

### 3. Fill in your experience
```bash
cp data/experience_template.json data/experience.json
# Edit data/experience.json with your actual profile
```

### 4. Verify setup
```bash
python tools/load_experience.py --verify
```

### 5. Start the agent
```bash
python agent.py
```

---

## What You Can Ask

| You say | Agent does |
|---------|-----------|
| "Find relevant jobs for me" | Searches LinkedIn based on your profile, returns ranked list |
| "What skills do I need for a Senior DevOps role?" | Finds job posts, extracts skills, shows your gap |
| "Analyze this job: [URL]" | Deep-dives a specific posting, full skill breakdown |
| "What am I missing for a Data Scientist role?" | Gap analysis against your experience.json |

---

## How the Agent Thinks (Layer 2)

1. Detects intent from your message
2. Reads the relevant workflow markdown
3. Calls tool scripts in the correct sequence
4. Handles errors (rate limits, blocked pages, missing data)
5. Formats and presents results

The agent **never scrapes directly** — it delegates all execution to `tools/`.
This keeps accuracy high and makes each step testable independently.

---

## API Keys Needed

| Service | Purpose | Cost | Link |
|---------|---------|------|------|
| Anthropic | Agent reasoning (Claude) | ~$0.01/query | [console.anthropic.com](https://console.anthropic.com) |
| ScraperAPI | LinkedIn bot bypass | Free: 5K req/mo | [scraperapi.com](https://www.scraperapi.com) |

---

## Troubleshooting

**No jobs found:**
LinkedIn changes its HTML structure periodically. Check `workflows/find_relevant_jobs.md` for updated selectors.

**Rate limited (429):**
Wait 60 seconds. Reduce `MAX_JOBS` in `.env`. LinkedIn is aggressive about rate limiting.

**Login wall / empty descriptions:**
Try appending `?trk=public_jobs_topcard` to the job URL. Some listings require login.

**spaCy errors:**
Run `python -m spacy download en_core_web_sm` again.
