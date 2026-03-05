"""
Tool: read_jobs.py
Layer 3 — Execution
Purpose: Read and display matched_jobs.json in a clean, formatted summary.
Use this after match_jobs_to_experience.py to present results to the user.
"""

import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Read and display matched jobs")
    parser.add_argument("--path", default="data/matched_jobs.json", help="Path to jobs JSON file")
    parser.add_argument("--exclude-company", default="", help="Comma-separated company names to exclude")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to show")
    args = parser.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"[read_jobs] ERROR: {args.path} not found. Run match_jobs_to_experience.py first.")
        return

    with open(p) as f:
        jobs = json.load(f)

    # Apply company exclusions
    excluded = [c.strip().lower() for c in args.exclude_company.split(",") if c.strip()]
    if excluded:
        before = len(jobs)
        jobs = [j for j in jobs if j.get("company", "").lower() not in excluded]
        print(f"[read_jobs] Excluded {before - len(jobs)} job(s) from: {', '.join(excluded)}")

    jobs = jobs[:args.limit]

    if not jobs:
        print("[read_jobs] No jobs found after filtering.")
        return

    print(f"\n[read_jobs] Showing {len(jobs)} job(s):\n")
    for i, job in enumerate(jobs, 1):
        print(f"{i}. [{job.get('match_score', 'N/A')}/100] {job.get('title', 'N/A')}")
        print(f"   Company:  {job.get('company', 'N/A')}")
        print(f"   Location: {job.get('location', 'N/A')}")
        print(f"   Posted:   {job.get('posted', 'N/A')}")
        print(f"   Match:    {job.get('match_rationale', 'N/A')}")
        print(f"   URL:      {job.get('url', 'N/A')}")
        if job.get("snippet"):
            print(f"   Snippet:  {job['snippet'][:120]}...")
        print()


if __name__ == "__main__":
    main()
