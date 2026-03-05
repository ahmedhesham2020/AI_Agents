"""
Agent: agent.py
Layer 2 — The Decision-Maker

This agent reads workflows, decides which tools to run, sequences them correctly,
handles failures gracefully, and presents results to the user.

It uses Claude (claude-sonnet-4-6) as its reasoning engine.
The agent never tries to do scraping or parsing itself — it delegates to tools/.
"""

import os
import json
import subprocess
import re
import argparse
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv()

AVAILABLE_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
]

SYSTEM_PROMPT = """You are a LinkedIn Job Agent — an intelligent coordinator (Layer 2).

## MANDATORY: HOW TO RUN TOOLS
- You MUST use the following format to run any tool: [RUN_TOOL: python tools/script_name.py --args]
- DO NOT just say you are running a tool. You MUST output the bracketed command.
- After you output a [RUN_TOOL: ...] command, STOP and wait for the tool output.
- The environment will provide the tool output to you in the next turn.

## FILE PATHS (CRITICAL)
- ALWAYS use `data/experience.json` as the `--profile` argument for tools.
- NEVER pass a list of skills or a string of text as a file path.
- Raw jobs from scraping are in `data/raw_jobs.json`.
- Matched/Ranked results are in `data/matched_jobs.json`.

## Your Goal
1. Understand what the user wants (find jobs OR analyze a specific job's skills)
2. Use the read_experience() and read_workflow(name) functions provided in your context to understand the user and the steps.
3. Call the appropriate tools in sequence via [RUN_TOOL: ...]
4. Present results clearly to the user based on the tool outputs.

## Available Tools (in tools/ folder)
- load_experience.py --path data/experience.json --verify: Load/validate user profile ONLY. Never pass any other file to this tool.
- scrape_linkedin_jobs.py --keywords "KEY" --location "LOC" --limit 20: Search LinkedIn for jobs.
- match_jobs_to_experience.py --jobs data/raw_jobs.json --profile data/experience.json: Rank scraped jobs.
- read_jobs.py --path data/matched_jobs.json --exclude-company "CompanyA,CompanyB" --limit 10: Read and display matched jobs. Use --exclude-company to filter out unwanted companies.
- scrape_job_details.py --url "LINKEDIN_URL": Get full description for a specific job URL.
- send_telegram.py --jobs data/matched_jobs.json [--limit 10] [--min-score 20]: Send matched job listings to the user's Telegram chat.

## Decision Logic
- To find jobs:
  1. load_experience.py --path data/experience.json --verify
  2. scrape_linkedin_jobs.py --keywords "..." --location "..."
  3. match_jobs_to_experience.py --jobs data/raw_jobs.json --profile data/experience.json
  4. read_jobs.py --path data/matched_jobs.json [--exclude-company "..."] → then present results to user. STOP.
- To analyze a job URL: scrape_job_details.py --url "URL" → match_jobs_to_experience --mode gap
- To send jobs to Telegram: send_telegram.py --jobs data/matched_jobs.json [--limit N] [--min-score N]
  - If the user asks to send jobs to Telegram after a search, run send_telegram.py immediately on data/matched_jobs.json.
  - If no search has been done yet, run the full find-jobs flow first, then send_telegram.py.

## Rules
- NEVER use load_experience.py on any file other than data/experience.json.
- NEVER run inline python3 -c commands. Always use the tools in tools/.
- NEVER use cat to read JSON files. Always use read_jobs.py to read job results.
- After read_jobs.py runs and you have the output, present the results immediately. Do NOT run more tools.
- If a tool fails, read the error and fix only the command that failed.
- Be concise.
"""


# ─── Helpers ────────────────────────────────────────────────────────────────

def read_workflow(name: str) -> str:
    path = Path(f"workflows/{name}.md")
    if not path.exists():
        return f"[ERROR] Workflow '{name}' not found at {path}"
    return path.read_text()


def read_experience() -> dict:
    path = Path("data/experience.json")
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def read_json_file(path: str):
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


# ─── Tool executor ──────────────────────────────────────────────────────────

def run_tool(command: str) -> tuple[bool, str]:
    if command.startswith("python "):
        command = command.replace("python ", "python3 ", 1)

    print(f"\n[agent] Running: {command}")
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr
    success = result.returncode == 0
    status = "Tool completed" if success else f"Tool failed (exit {result.returncode})"
    print(f"[agent] {status}")
    print(f"[agent] Output: {output.strip()[:500]}")
    return success, output


# ─── Intent + context ────────────────────────────────────────────────────────

def detect_intent(user_message: str) -> str:
    msg = user_message.lower()
    if any(w in msg for w in ["find jobs", "relevant jobs", "job search", "what jobs", "show me jobs"]):
        return "find_relevant_jobs"
    if any(w in msg for w in ["skills", "what do i need", "analyze", "job post", "missing", "gap"]):
        return "scrape_job_skills"
    if any(w in msg for w in ["setup", "install", "configure", "start"]):
        return "setup"
    if any(w in msg for w in ["telegram", "send", "notify", "notification"]):
        return "send_telegram"
    return "general"


def build_context(intent: str, user_message: str) -> str:
    parts = [f"User request: {user_message}\n"]

    profile = read_experience()
    if profile:
        parts.append(
            f"User profile loaded: {profile.get('current_title', 'N/A')} | "
            f"Skills: {', '.join(profile.get('skills', [])[:8])}"
        )
    else:
        parts.append("No experience.json found. User needs to set up profile first.")

    if intent != "general":
        workflow = read_workflow(intent)
        parts.append(f"\n--- Relevant Workflow: {intent} ---\n{workflow}")

    matched = read_json_file("data/matched_jobs.json")
    if matched:
        parts.append(f"\nPrevious job results available: {len(matched)} jobs in data/matched_jobs.json")

    return "\n".join(parts)


# ─── Core agent loop ─────────────────────────────────────────────────────────

def run_agent(user_message: str, history: list, client: anthropic.Anthropic, model: str) -> tuple[str, list]:
    """
    Sends message + context to Claude, processes tool calls, returns (response_text, updated_history).
    """
    intent = detect_intent(user_message)
    context = build_context(intent, user_message)

    history.append({"role": "user", "content": context})

    MAX_ROUNDS = 20  # hard safety cap — agent stops naturally before this
    for round_num in range(MAX_ROUNDS):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=history,
            )
            assistant_text = response.content[0].text
        except Exception as e:
            return f"Model error: {e}", history

        history.append({"role": "assistant", "content": assistant_text})

        tool_calls = re.findall(r'\[RUN_TOOL:\s*(.+?)\]', assistant_text)

        # No tool calls → agent is done, return final answer immediately
        if not tool_calls:
            print(f"[agent] Task complete after {round_num + 1} round(s).")
            return assistant_text, history

        # Execute every tool call in this round
        tool_results = []
        for cmd in tool_calls:
            success, output = run_tool(cmd.strip())
            tool_results.append(
                f"Tool '{cmd.strip()}': {'Success' if success else 'Failed'}\nOutput: {output[:3000]}"
            )

        tool_feedback = (
            "Tool execution results:\n" +
            "\n\n".join(tool_results) +
            "\n\nNow read any output files needed and present the final results to the user."
        )
        history.append({"role": "user", "content": tool_feedback})
        print(f"[agent] Round {round_num + 1} done — continuing...")

    return "Safety cap reached — agent ran too many reasoning rounds.", history


# ─── Main chat interface ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Job Agent CLI")
    parser.add_argument("--model", default="claude-sonnet-4-6", choices=AVAILABLE_MODELS, help="Claude model to use")
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current_model = args.model
    history = []

    print("\n" + "=" * 60)
    print(f"  LinkedIn Job Agent — Powered by {current_model}")
    print("=" * 60)
    print("  Commands:")
    print("  • 'Find relevant jobs for me'")
    print("  • 'What skills do I need for a Senior DevOps role?'")
    print("  • 'Analyze this job: [LinkedIn URL]'")
    print("  • 'switch [model_name]' to change model")
    print("  • 'models' to list available models")
    print("  • 'quit' to exit")
    print("=" * 60 + "\n")

    if not Path("data/experience.json").exists():
        print("No experience profile found!")
        print("Please copy data/experience_template.json -> data/experience.json and fill it in.\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if user_input.lower() == "models":
                print(f"Available models: {', '.join(AVAILABLE_MODELS)}")
                continue

            if user_input.lower().startswith("switch "):
                new_model = user_input.split(" ", 1)[1].strip()
                if new_model in AVAILABLE_MODELS:
                    current_model = new_model
                    history = []  # reset history on model switch
                    print(f"Switched to {current_model}")
                else:
                    print(f"Model '{new_model}' not available. Choose from: {', '.join(AVAILABLE_MODELS)}")
                continue

            print(f"\nAgent ({current_model}): thinking...\n")
            response, history = run_agent(user_input, history, client, current_model)
            print(f"\nAgent: {response}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[agent] Unexpected error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
