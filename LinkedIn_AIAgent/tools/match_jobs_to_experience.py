"""
Tool: match_jobs_to_experience.py
Layer 3 — Execution
Purpose: 
  - Mode 'rank': Score a list of jobs against user's experience profile
  - Mode 'gap': Compare a specific job's skills against user profile
"""

import json
import argparse
import re
from pathlib import Path


def load_json(path: str) -> dict | list:
    with open(path) as f:
        return json.load(f)


def normalize(text: str) -> str:
    return text.lower().strip()


def skill_overlap(user_skills: list[str], job_skills: list[str]) -> tuple[list, list]:
    """Return (matched, missing) skills."""
    user_normalized = {normalize(s) for s in user_skills}
    matched = [s for s in job_skills if normalize(s) in user_normalized]
    missing = [s for s in job_skills if normalize(s) not in user_normalized]
    return matched, missing


def seniority_level(text: str) -> int:
    """Map seniority label to numeric level (1=junior, 2=mid, 3=senior, 4=lead/staff)."""
    text = text.lower()
    if any(w in text for w in ["intern", "junior", "entry", "associate"]):
        return 1
    if any(w in text for w in ["senior", "sr.", "sr "]):
        return 3
    if any(w in text for w in ["lead", "staff", "principal", "director"]):
        return 4
    return 2  # mid-level default


def score_job(job: dict, profile: dict) -> tuple[int, str]:
    """
    Score a job 0–100 against a user profile.
    Returns (score, rationale).
    """
    user_skills = profile.get("skills", [])
    user_title = profile.get("current_title", "")
    user_seniority = seniority_level(profile.get("seniority", "mid"))

    job_title = job.get("title", "")
    job_snippet = job.get("snippet", "") + " " + job.get("title", "")

    score = 0
    rationale_parts = []

    # --- Title match (40 pts) ---
    user_title_words = set(normalize(user_title).split())
    job_title_words = set(normalize(job_title).split())
    title_overlap = user_title_words & job_title_words
    title_score = min(40, len(title_overlap) * 15)
    score += title_score
    if title_score > 0:
        rationale_parts.append(f"title overlap ({', '.join(title_overlap)})")

    # --- Skill match from snippet (40 pts) ---
    matched_skills = [s for s in user_skills if normalize(s) in normalize(job_snippet)]
    skill_score = min(40, len(matched_skills) * 8)
    score += skill_score
    if matched_skills:
        rationale_parts.append(f"skills match: {', '.join(matched_skills[:3])}")

    # --- Seniority match (20 pts) ---
    job_seniority = seniority_level(job_title)
    seniority_diff = abs(user_seniority - job_seniority)
    if seniority_diff == 0:
        score += 20
        rationale_parts.append("seniority: perfect match")
    elif seniority_diff == 1:
        score += 10
        rationale_parts.append("seniority: close match")
    else:
        rationale_parts.append("seniority: mismatch")

    rationale = "; ".join(rationale_parts) if rationale_parts else "low relevance"
    return score, rationale


def rank_mode(jobs: list[dict], profile: dict, output_path: str):
    """Rank jobs against profile and save results."""
    results = []
    for job in jobs:
        score, rationale = score_job(job, profile)
        results.append({**job, "match_score": score, "match_rationale": rationale})

    results.sort(key=lambda x: x["match_score"], reverse=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[match_jobs] Ranked {len(results)} jobs. Top score: {results[0]['match_score'] if results else 'N/A'}")
    print(f"[match_jobs] Saved to {output_path}")


def gap_mode(job_skills: dict, profile: dict, output_path: str):
    """Perform skill gap analysis for a specific job."""
    user_skills = profile.get("skills", [])

    required = job_skills.get("required_skills", [])
    preferred = job_skills.get("preferred_skills", [])

    matched_required, missing_required = skill_overlap(user_skills, required)
    matched_preferred, missing_preferred = skill_overlap(user_skills, preferred)

    all_matched = matched_required + matched_preferred
    all_missing_required = missing_required
    all_missing_preferred = missing_preferred

    # Score: % of required skills covered
    if required:
        match_score = int((len(matched_required) / len(required)) * 100)
    else:
        match_score = 50  # No required skills listed

    result = {
        "you_have": all_matched,
        "you_are_missing": all_missing_required,
        "nice_to_have_missing": all_missing_preferred,
        "match_score": match_score,
        "required_total": len(required),
        "required_matched": len(matched_required),
        "preferred_total": len(preferred),
        "preferred_matched": len(matched_preferred)
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[match_jobs] Gap analysis complete. Score: {match_score}/100")
    print(f"  ✅ You have: {len(all_matched)} skills")
    print(f"  ❌ Missing (required): {len(all_missing_required)}")
    print(f"  ⚠️  Missing (preferred): {len(all_missing_preferred)}")
    print(f"[match_jobs] Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Match jobs to user experience")
    parser.add_argument("--mode", choices=["rank", "gap"], default="rank")
    parser.add_argument("--jobs", help="Path to raw_jobs.json (rank mode)")
    parser.add_argument("--job", help="Path to job_skills.json (gap mode)")
    parser.add_argument("--profile", default="data/experience.json")
    parser.add_argument("--output", default="data/matched_jobs.json")
    args = parser.parse_args()

    profile = load_json(args.profile)

    if args.mode == "rank":
        if not args.jobs:
            raise ValueError("--jobs required for rank mode")
        jobs = load_json(args.jobs)
        rank_mode(jobs, profile, args.output)
    else:
        if not args.job:
            raise ValueError("--job required for gap mode")
        job_skills = load_json(args.job)
        gap_mode(job_skills, profile, args.output)


if __name__ == "__main__":
    main()
