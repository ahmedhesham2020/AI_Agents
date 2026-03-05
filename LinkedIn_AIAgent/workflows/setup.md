# Workflow: First-Time Setup

## Purpose
Get the system ready for the first run. Only needs to be done once (or when environment is reset).

## Steps

### Step 1 — Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Step 2 — Configure Environment
Copy `.env.example` to `.env` and fill in:
- `SCRAPER_API_KEY` — from ScraperAPI.com (free tier: 5,000 req/month)
- `PROXYCURL_API_KEY` — optional, for richer LinkedIn data
- `ANTHROPIC_API_KEY` — for the agent's reasoning layer

### Step 3 — Fill In Your Experience
Edit `data/experience.json`:
- Add your job titles, years of experience, skills, education
- The more detail you add, the better the matching

### Step 4 — Verify Setup
```bash
python tools/load_experience.py --verify
```
Expected output: `✅ Profile loaded: {N} skills, {title}, {years}yr experience`

### Step 5 — Run First Job Search
```bash
python agent.py
```
Then type: `"Find relevant jobs for me"`

---

## Troubleshooting
- `ModuleNotFoundError` → re-run `pip install -r requirements.txt`
- `API key invalid` → double-check `.env` file, no quotes around values
- `No jobs found` → verify internet connection; LinkedIn may have changed structure (check workflow for updates)
