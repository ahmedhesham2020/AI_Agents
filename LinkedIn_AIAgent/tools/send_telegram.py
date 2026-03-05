"""
Tool: send_telegram.py
Layer 3 — Execution

Sends matched job listings to a Telegram chat via Bot API.

Usage:
    python tools/send_telegram.py --jobs data/matched_jobs.json [--limit 10] [--min-score 20]
"""

import os
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(token: str, chat_id: str, text: str) -> bool:
    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=15)
    if not resp.ok:
        print(f"[telegram] Failed to send message: {resp.status_code} {resp.text}")
        return False
    return True


def format_job(job: dict, index: int) -> str:
    title = job.get("title", "N/A")
    score = job.get("match_score", 0)
    url = job.get("url", "")

    lines = [
        f"<b>{index}. {title}</b>",
        f"Match score: {score}",
    ]
    if url:
        lines.append(url)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Send matched jobs to Telegram")
    parser.add_argument("--jobs", default="data/matched_jobs.json", help="Path to matched jobs JSON")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to send")
    parser.add_argument("--min-score", type=int, default=0, help="Minimum match score to include")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[telegram] ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        exit(1)

    jobs_path = Path(args.jobs)
    if not jobs_path.exists():
        print(f"[telegram] ERROR: Jobs file not found: {jobs_path}")
        exit(1)

    with open(jobs_path) as f:
        jobs = json.load(f)

    # Filter and limit
    jobs = [j for j in jobs if j.get("match_score", 0) >= args.min_score]
    jobs = jobs[:args.limit]

    if not jobs:
        print("[telegram] No jobs to send after filtering.")
        exit(0)

    # Send header
    header = f"<b>LinkedIn Job Matches</b>\n{len(jobs)} jobs found for you:"
    send_message(token, chat_id, header)

    sent = 0
    for i, job in enumerate(jobs, start=1):
        msg = format_job(job, i)
        if send_message(token, chat_id, msg):
            sent += 1

    print(f"[telegram] Sent {sent}/{len(jobs)} job(s) to Telegram successfully.")


if __name__ == "__main__":
    main()
