"""
Tool: extract_skills.py
Layer 3 — Execution
Purpose: Extract required/preferred skills from a job description using
         spaCy NLP + a curated skill taxonomy for tech roles.
"""

import re
import json
import argparse

# Comprehensive skill taxonomy (extend as needed)
SKILL_TAXONOMY = {
    "languages": [
        "Python", "JavaScript", "TypeScript", "Java", "Go", "Golang", "Rust",
        "C++", "C#", "Ruby", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL",
        "Bash", "Shell", "PHP", "Perl", "Haskell", "Lua", "Dart", "Elixir"
    ],
    "frameworks_libraries": [
        "React", "Next.js", "Vue", "Angular", "Svelte", "Django", "Flask",
        "FastAPI", "Spring", "Rails", "Express", "Node.js", "TensorFlow",
        "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy", "Spark",
        "Kafka", "Celery", "GraphQL", "REST", "gRPC", "Langchain", "Hugging Face"
    ],
    "cloud_devops": [
        "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform", "Helm",
        "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "Ansible", "Puppet",
        "Chef", "Prometheus", "Grafana", "Datadog", "ELK", "Elasticsearch",
        "ArgoCD", "Istio", "Linux", "Unix"
    ],
    "data_ml": [
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "MLOps",
        "Feature Engineering", "A/B Testing", "Statistical Analysis", "Data Pipeline",
        "ETL", "Data Warehouse", "dbt", "Airflow", "Spark", "BigQuery",
        "Snowflake", "Redshift", "PostgreSQL", "MySQL", "MongoDB", "Redis",
        "Pinecone", "Vector Database", "RAG", "LLM", "Fine-tuning"
    ],
    "tools_practices": [
        "Git", "Jira", "Agile", "Scrum", "TDD", "Unit Testing", "API Design",
        "System Design", "Microservices", "Event-driven", "SOA", "OAuth",
        "JWT", "Security", "OWASP", "Figma", "Postman", "Swagger"
    ],
    "soft_skills": [
        "communication", "leadership", "collaboration", "cross-functional",
        "mentoring", "problem-solving", "analytical", "stakeholder", "ownership",
        "initiative", "fast-paced", "ambiguity", "prioritization"
    ]
}

# Flatten all hard skills for fast lookup
ALL_SKILLS = []
for category, skills in SKILL_TAXONOMY.items():
    if category != "soft_skills":
        ALL_SKILLS.extend(skills)

SOFT_SKILLS = SKILL_TAXONOMY["soft_skills"]

# Patterns to identify years of experience requirements
EXPERIENCE_PATTERN = re.compile(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE)
EDUCATION_PATTERN = re.compile(r"(BS|MS|PhD|Bachelor|Master|Doctorate)[^\n.]*(?:Computer Science|Engineering|Mathematics|Statistics|related)[^\n.]*", re.IGNORECASE)


def find_section(text: str, section_keywords: list[str]) -> str:
    """Extract text near a section header like 'Requirements' or 'Qualifications'."""
    lines = text.split("\n")
    in_section = False
    section_lines = []

    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in section_keywords):
            in_section = True
            continue
        if in_section:
            # Stop at next section header (short line followed by content)
            if len(line) < 50 and line.strip().endswith(":") and i > 0:
                break
            section_lines.append(line)
            if len(section_lines) > 40:  # Cap section length
                break

    return "\n".join(section_lines)


def extract_skills_from_text(text: str, skill_list: list[str]) -> list[str]:
    """Find which skills from a list appear in text."""
    found = []
    text_lower = text.lower()
    for skill in skill_list:
        # Match whole word / skill name (case-insensitive)
        pattern = re.compile(r'\b' + re.escape(skill.lower()) + r'\b')
        if pattern.search(text_lower):
            found.append(skill)
    return found


def classify_required_vs_preferred(text: str, skills: list[str]) -> tuple[list, list]:
    """Heuristically split skills into required vs preferred."""
    required_section = find_section(text, ["requirements", "required", "qualifications", "must have", "you will need"])
    preferred_section = find_section(text, ["preferred", "nice to have", "bonus", "plus", "desired", "advantageous"])

    # Full text fallback if sections not found
    if not required_section:
        required_section = text
    if not preferred_section:
        preferred_section = ""

    required = []
    preferred = []
    either = []

    for skill in skills:
        in_required = bool(re.search(r'\b' + re.escape(skill.lower()) + r'\b', required_section.lower()))
        in_preferred = bool(re.search(r'\b' + re.escape(skill.lower()) + r'\b', preferred_section.lower()))

        if in_preferred and not in_required:
            preferred.append(skill)
        elif in_required:
            required.append(skill)
        else:
            either.append(skill)

    # Skills in 'either' but not in preferred section go to required
    required.extend(either)

    return required, preferred


def extract_skills(job_detail: dict) -> dict:
    """Main extraction function."""
    description = job_detail.get("description_raw", "")

    if not description:
        return {
            "error": "No description found",
            "required_skills": [],
            "preferred_skills": [],
            "soft_skills": [],
            "experience_years": "unknown",
            "education": ""
        }

    # Find all mentioned skills
    all_found = extract_skills_from_text(description, ALL_SKILLS)
    soft_found = extract_skills_from_text(description, SOFT_SKILLS)

    # Classify required vs preferred
    required, preferred = classify_required_vs_preferred(description, all_found)

    # Extract experience years
    exp_matches = EXPERIENCE_PATTERN.findall(description)
    experience_years = f"{min(int(y) for y in exp_matches)}+" if exp_matches else "Not specified"

    # Extract education requirement
    edu_match = EDUCATION_PATTERN.search(description)
    education = edu_match.group(0).strip() if edu_match else "Not specified"

    return {
        "required_skills": required,
        "preferred_skills": preferred,
        "soft_skills": soft_found,
        "experience_years": experience_years,
        "education": education,
        "all_found_count": len(all_found)
    }


def main():
    parser = argparse.ArgumentParser(description="Extract skills from a job description")
    parser.add_argument("--input", default="data/job_detail.json", help="Input job detail JSON")
    parser.add_argument("--output", default="data/job_skills.json", help="Output skills JSON")
    args = parser.parse_args()

    with open(args.input) as f:
        job_detail = json.load(f)

    skills = extract_skills(job_detail)

    with open(args.output, "w") as f:
        json.dump(skills, f, indent=2)

    print(f"[extract_skills] Required: {len(skills['required_skills'])} | Preferred: {len(skills['preferred_skills'])}")
    print(f"[extract_skills] Experience: {skills['experience_years']} | Education: {skills['education']}")
    print(f"[extract_skills] Saved to {args.output}")


if __name__ == "__main__":
    main()
