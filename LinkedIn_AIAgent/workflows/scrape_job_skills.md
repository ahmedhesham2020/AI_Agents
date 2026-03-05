# Workflow: Scrape Skills from a Specific Job Post

## Purpose
Given a job title or LinkedIn job URL, scrape the full job description and extract a structured list of required and preferred skills — then compare against the user's profile.

## Trigger
User says something like:
- "What skills do I need for [job title]?"
- "Analyze this job: [URL]"
- "What's missing from my profile for a Senior DevOps role?"

---

## Inputs Required
- [ ] Job title OR LinkedIn job URL (from user or from `data/matched_jobs.json`)
- [ ] `data/experience.json` (for gap analysis)

If only a title is given (no URL) → run Step 1 to find a representative posting first.
If URL is given → skip to Step 2.

---

## Execution Steps

### Step 1 — Find Job URL (if title only)
```bash
python tools/scrape_linkedin_jobs.py \
  --keywords "{job_title}" \
  --limit 3
```
Pick the top result URL and proceed.

---

### Step 2 — Scrape Full Job Description
```bash
python tools/scrape_job_details.py \
  --url "{job_url}" \
  --output data/job_detail.json
```
**Output:** `data/job_detail.json` with:
```json
{
  "title": "...",
  "company": "...",
  "location": "...",
  "description_raw": "...",
  "posted_date": "..."
}
```

**Known Issues:**
- LinkedIn requires JS rendering for full descriptions → tool uses `requests-html` or `playwright`
- Some job pages redirect to login → tool targets `linkedin.com/jobs/view/{id}` public endpoints
- If blocked → try appending `?trk=public_jobs_topcard` to URL

---

### Step 3 — Extract Skills from Description
```bash
python tools/extract_skills.py \
  --input data/job_detail.json \
  --output data/job_skills.json
```
**Output:** `data/job_skills.json`:
```json
{
  "required_skills": ["Python", "Docker", "Kubernetes", "CI/CD"],
  "preferred_skills": ["Terraform", "AWS", "Helm"],
  "soft_skills": ["communication", "cross-functional collaboration"],
  "experience_years": "5+",
  "education": "BS/MS in Computer Science or related"
}
```

**Extraction method:** Keyword matching + NLP (spaCy or regex patterns against known skill taxonomy)

---

### Step 4 — Gap Analysis Against User Profile
```bash
python tools/match_jobs_to_experience.py \
  --mode gap \
  --job data/job_skills.json \
  --profile data/experience.json \
  --output data/skill_gap.json
```
**Output:** `data/skill_gap.json`:
```json
{
  "you_have": ["Python", "Docker", "CI/CD"],
  "you_are_missing": ["Kubernetes", "Terraform"],
  "nice_to_have_missing": ["Helm", "AWS"],
  "match_score": 74
}
```

---

### Step 5 — Present Results to User

```
📋 Skills Analysis: Senior DevOps Engineer @ Stripe

✅ You Already Have (3/4 required):
   • Python ✓  • Docker ✓  • CI/CD ✓

❌ You're Missing (Critical):
   • Kubernetes — most common gap, ~3mo to learn basics
   • Terraform — infra-as-code, ~1mo fundamentals

⚠️  Nice to Have (not blocking):
   • Helm, AWS (you have Docker, so cloud basics transfer)

📊 Match Score: 74/100 — Strong candidate, close skill gap on K8s

🎯 Recommendation: Learn Kubernetes basics to become highly competitive.
```

---

## Error Handling

| Error | Action |
|-------|--------|
| URL gives 404 | Job may be closed → search for similar open role |
| Login redirect | Use alternative public URL format, or note limitation |
| Empty description | Try fetching 2nd or 3rd search result |
| spaCy model missing | Run `python -m spacy download en_core_web_sm` |
| No skills extracted | Fall back to keyword regex, log for review |

---

## Post-Run
- Save `data/job_skills.json` and `data/skill_gap.json`
- If user asks follow-up ("tell me more about Kubernetes"), pivot to explanation mode — no new scraping needed
