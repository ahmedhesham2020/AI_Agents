# Workflow: Find Relevant Jobs on LinkedIn

## Purpose
Search LinkedIn for job postings that match the user's experience profile and return a ranked list of relevant opportunities.

## Trigger
User says something like:
- "Find jobs for me"
- "What jobs match my experience?"
- "Show me relevant job listings"

---

## Inputs Required
Before running, confirm you have:
- [ ] `data/experience.json` exists with the user's profile
- [ ] `.env` contains `SCRAPER_API_KEY` or `PROXYCURL_API_KEY` (check which is available)
- [ ] Search keywords derived from experience (auto-generated from profile if not specified)
- [ ] Optional: location preference (default: remote)

If `experience.json` is missing → ask the user to fill it in (see `data/experience_template.json`)

---

## Execution Steps

### Step 1 — Load Experience Profile
```bash
python tools/load_experience.py
```
**Output:** Parsed skills, job titles, years of experience → stored in memory as `profile`

**Failure:** If file missing or malformed JSON → STOP, ask user to complete `data/experience.json`

---

### Step 2 — Generate Search Keywords
The agent reads the profile and extracts:
- Top 3 job title variations (e.g., "Data Scientist", "ML Engineer", "AI Researcher")
- Key technical skills (top 5)
- Seniority level (junior / mid / senior / lead)

Construct search queries like:
```
"{title}" AND ("{skill1}" OR "{skill2}") site:linkedin.com/jobs
```

---

### Step 3 — Scrape LinkedIn Job Listings
```bash
python tools/scrape_linkedin_jobs.py \
  --keywords "{generated_keywords}" \
  --location "{location}" \
  --limit 20
```
**Output:** `data/raw_jobs.json` — list of job objects with title, company, URL, snippet

**Known Issues:**
- LinkedIn rate-limits aggressively after ~30 requests → tool uses 2s delay between requests
- If 429 error → wait 60 seconds and retry once, then STOP and report
- Login walls: tool uses public job search URL (no auth needed for listings)

---

### Step 4 — Match Jobs to Experience
```bash
python tools/match_jobs_to_experience.py \
  --jobs data/raw_jobs.json \
  --profile data/experience.json \
  --output data/matched_jobs.json
```
**Output:** `data/matched_jobs.json` — jobs scored 0–100 with match rationale

**Scoring Logic (inside the tool):**
- Title match: 40 pts
- Skill overlap: 40 pts
- Seniority match: 20 pts

---

### Step 5 — Present Results
Read `data/matched_jobs.json` and present to user:

```
🔍 Found {N} relevant jobs for you:

1. [Score: 92] Senior Data Scientist @ Stripe (Remote)
   Match: Python, ML, your 4yr experience aligns perfectly
   🔗 {url}

2. [Score: 78] ML Engineer @ Notion (NYC)
   Match: Strong on NLP skills, missing: Kubernetes experience
   🔗 {url}
...
```

---

## Error Handling

| Error | Action |
|-------|--------|
| `experience.json` missing | Ask user to fill template |
| No jobs found | Broaden keywords, retry with fewer filters |
| Rate limit (429) | Wait 60s, retry once, then report |
| Scraper blocked | Inform user, suggest trying again in 1hr |
| JSON parse error | Log raw output, ask user to check `.env` config |

---

## Post-Run
- Save results to `data/matched_jobs.json`
- Update workflow if new rate-limit patterns or URL structures are discovered
- If <5 results returned, note that LinkedIn structure may have changed
