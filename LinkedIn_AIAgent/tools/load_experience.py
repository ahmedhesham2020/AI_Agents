"""
Tool: load_experience.py
Layer 3 — Execution
Purpose: Load, validate, and summarize the user's experience profile from experience.json.
"""

import json
import sys
import argparse
from pathlib import Path

REQUIRED_FIELDS = ["current_title", "skills", "years_of_experience"]
PROFILE_PATH = "data/experience.json"


def load_profile(path: str = PROFILE_PATH) -> dict:
    """Load and validate experience.json."""
    p = Path(path)
    if not p.exists():
        print(f"[load_experience] ERROR: {path} not found.")
        print("[load_experience] Please copy data/experience_template.json → data/experience.json and fill it in.")
        sys.exit(1)

    with open(p) as f:
        try:
            profile = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[load_experience] ERROR: Invalid JSON in {path}: {e}")
            sys.exit(1)

    # Validate required fields
    missing = [field for field in REQUIRED_FIELDS if field not in profile]
    if missing:
        print(f"[load_experience] ERROR: Missing fields in experience.json: {missing}")
        sys.exit(1)

    # Validate non-empty skills list
    if not profile.get("skills"):
        print("[load_experience] WARNING: skills list is empty. Add your skills for better matching.")

    return profile


def summarize_profile(profile: dict):
    """Print a human-readable summary."""
    name = profile.get("name", "User")
    title = profile.get("current_title", "N/A")
    years = profile.get("years_of_experience", "N/A")
    skills = profile.get("skills", [])
    seniority = profile.get("seniority", "mid")
    preferred_roles = profile.get("preferred_roles", [])
    location = profile.get("preferred_location", "Any")

    print(f"\n{'='*50}")
    print(f"  Profile: {name}")
    print(f"  Title:   {title} ({seniority})")
    print(f"  Exp:     {years} years")
    print(f"  Skills:  {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")
    if preferred_roles:
        print(f"  Seeking: {', '.join(preferred_roles)}")
    print(f"  Location: {location}")
    print(f"{'='*50}\n")


def generate_search_keywords(profile: dict) -> list[str]:
    """
    Derive search keyword combinations from user profile.
    Returns a list of query strings to use in job scraping.
    """
    title = profile.get("current_title", "")
    preferred_roles = profile.get("preferred_roles", [title])
    top_skills = profile.get("skills", [])[:5]
    seniority = profile.get("seniority", "")

    keywords = []
    for role in preferred_roles[:3]:
        base = f"{seniority} {role}".strip() if seniority else role
        keywords.append(base)
        if top_skills:
            keywords.append(f"{base} {top_skills[0]}")

    return keywords


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=PROFILE_PATH)
    parser.add_argument("--verify", action="store_true", help="Validate and print summary")
    parser.add_argument("--keywords", action="store_true", help="Print generated search keywords")
    args = parser.parse_args()

    profile = load_profile(args.path)

    if args.verify:
        summarize_profile(profile)
        print("✅ Profile loaded successfully!")

    if args.keywords:
        keywords = generate_search_keywords(profile)
        print("Generated search keywords:")
        for kw in keywords:
            print(f"  - {kw}")


if __name__ == "__main__":
    main()
