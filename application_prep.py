import json
import os
import re
import sys
from datetime import datetime


# ============================================================
# FILES
# ============================================================

TRACKER_FILE = "application_tracker.json"
RESUME_MATCHES_FILE = "resume_matches.json"

OUTPUT_JSON = "application_prep.json"
OUTPUT_TEXT = "application_prep.txt"


# ============================================================
# YOUR PROFILE
# ============================================================

PROFILE = {
    "name": "Vishwas Singh",

    "joining_date": "2025-08-08",

    "experience_years": 1.02,

    "target_roles": [
        "data engineer",
        "data engineering",
        "python data engineer",
        "databricks data engineer",
    ],

    "skills": [
        "python",
        "pyspark",
        "spark",
        "sql",
        "databricks",
        "delta lake",
        "delta lakehouse",
        "aws",
        "aws glue",
        "etl",
        "elt",
        "azure",
        "mlflow",
        "git",
        "ci/cd",
        "azure devops",
        "data engineering",
        "medallion architecture",
    ],
}


PROFILE_SKILLS = {
    x.lower().strip()
    for x in PROFILE["skills"]
}


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            clean(x)
            for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            clean(v)
            for v in value.values()
        )

    return str(value).strip()


def normalize(value):

    value = clean(value)

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def number(value):

    if value is None:
        return None

    try:
        return float(value)
    except:
        return None


# ============================================================
# LOAD JSON
# ============================================================

def load_json(filename):

    if not os.path.exists(filename):

        print(
            f"WARNING: {filename} not found."
        )

        return []

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):

            # Common container keys
            for key in [
                "jobs",
                "matches",
                "results",
                "applications",
                "data",
            ]:

                if isinstance(
                    data.get(key),
                    list
                ):

                    return data[key]

        return []

    except Exception as e:

        print(
            f"ERROR reading {filename}: {e}"
        )

        return []


# ============================================================
# FIND VALUE RECURSIVELY
# ============================================================

def recursive_get(
    obj,
    possible_keys
):

    if not isinstance(obj, dict):
        return None

    normalized_keys = {
        normalize(k)
        for k in possible_keys
    }

    for key, value in obj.items():

        if normalize(key) in normalized_keys:

            return value

    for value in obj.values():

        if isinstance(
            value,
            dict
        ):

            result = recursive_get(
                value,
                possible_keys
            )

            if result is not None:
                return result

    return None


# ============================================================
# FIND JOB IDENTIFIER
# ============================================================

def job_identity(job):

    url = normalize(
        recursive_get(
            job,
            [
                "url",
                "job_url",
                "joburl",
                "apply_url",
                "application_url",
            ]
        )
    )

    title = normalize(
        recursive_get(
            job,
            [
                "title",
                "job_title",
                "jobtitle",
            ]
        )
    )

    company = normalize(
        recursive_get(
            job,
            [
                "company",
                "company_name",
                "employer",
            ]
        )
    )

    return url, title, company


# ============================================================
# BUILD RESUME MATCH INDEX
# ============================================================

def build_resume_index(
    resume_matches
):

    index = {}

    for job in resume_matches:

        url, title, company = job_identity(
            job
        )

        # URL is the strongest identifier.

        if url:

            index[
                ("url", url)
            ] = job

        # Also index title + company.

        if title and company:

            index[
                (
                    "title_company",
                    title,
                    company
                )
            ] = job

    return index


# ============================================================
# FIND RESUME MATCH
# ============================================================

def find_resume_match(
    tracker_job,
    resume_index
):

    url, title, company = job_identity(
        tracker_job
    )

    # 1. Exact URL

    if url:

        result = resume_index.get(
            ("url", url)
        )

        if result:
            return result

    # 2. Title + company

    if title and company:

        result = resume_index.get(
            (
                "title_company",
                title,
                company
            )
        )

        if result:
            return result

    return {}


# ============================================================
# EXTRACT SKILL LIST
# ============================================================

def extract_list(
    obj,
    keys
):

    value = recursive_get(
        obj,
        keys
    )

    if isinstance(
        value,
        list
    ):

        return [
            normalize(x)
            for x in value
            if normalize(x)
        ]

    if isinstance(
        value,
        str
    ):

        return [
            normalize(x)
            for x in re.split(
                r",|;",
                value
            )
            if normalize(x)
        ]

    return []


# ============================================================
# EXTRACT MATCHED / MISSING SKILLS
# ============================================================

def get_skill_data(
    resume_match
):

    matched = extract_list(
        resume_match,
        [
            "matched",
            "matched_skills",
            "matching_skills",
            "skills_matched",
        ]
    )

    missing = extract_list(
        resume_match,
        [
            "missing",
            "missing_skills",
            "skills_missing",
        ]
    )

    required = extract_list(
        resume_match,
        [
            "required_skills",
            "required",
            "skills_required",
        ]
    )

    return {
        "required": sorted(
            set(required)
        ),

        "matched": sorted(
            set(matched)
        ),

        "missing": sorted(
            set(missing)
        ),
    }


# ============================================================
# FALLBACK SKILL MATCHING
# ============================================================

ALIASES = {

    "pyspark": [
        "spark"
    ],

    "spark": [
        "pyspark"
    ],

    "delta lakehouse": [
        "delta lake"
    ],

    "delta lake": [
        "delta lakehouse"
    ],

    "aws glue": [
        "aws"
    ],

    "azure devops": [
        "ci/cd"
    ],

    "ci/cd": [
        "azure devops"
    ],

    "etl": [
        "elt"
    ],

    "elt": [
        "etl"
    ],
}


def profile_has_skill(
    skill
):

    skill = normalize(
        skill
    )

    if skill in PROFILE_SKILLS:
        return True

    for alias in ALIASES.get(
        skill,
        []
    ):

        if alias in PROFILE_SKILLS:
            return True

    return False


def fallback_skill_analysis(
    job,
    existing
):

    required = existing[
        "required"
    ]

    matched = existing[
        "matched"
    ]

    missing = existing[
        "missing"
    ]

    # If resume matcher supplied matched skills,
    # preserve them.

    if not matched and required:

        matched = [
            skill
            for skill in required
            if profile_has_skill(
                skill
            )
        ]

    if not missing and required:

        missing = [
            skill
            for skill in required
            if not profile_has_skill(
                skill
            )
        ]

    return {
        "required": sorted(
            set(required)
        ),

        "matched": sorted(
            set(matched)
        ),

        "missing": sorted(
            set(missing)
        ),
    }


# ============================================================
# EXPERIENCE
# ============================================================

def analyze_experience(
    tracker_job,
    resume_match
):

    required = recursive_get(
        resume_match,
        [
            "experience_required",
            "required_experience",
            "experience",
        ]
    )

    if required is None:

        required = recursive_get(
            tracker_job,
            [
                "experience_required",
                "required_experience",
            ]
        )

    current = PROFILE[
        "experience_years"
    ]

    required_number = number(
        required
    )

    if required_number is None:

        return {
            "required": None,
            "current": current,
            "status": "UNKNOWN",
            "gap": None,
        }

    gap = round(
        required_number - current,
        2
    )

    if gap <= 0:

        status = "MEETS"

    elif gap <= 0.5:

        status = "CLOSE"

    elif gap <= 1:

        status = "STRETCH"

    else:

        status = "TOO_SENIOR"

    return {
        "required": required_number,
        "current": current,
        "status": status,
        "gap": gap,
    }


# ============================================================
# RESUME KEYWORDS
# ============================================================

def resume_keywords(
    skill_data
):

    priority = [
        "databricks",
        "pyspark",
        "spark",
        "delta lake",
        "aws glue",
        "python",
        "sql",
        "etl",
        "elt",
        "aws",
        "azure",
        "mlflow",
        "ci/cd",
        "azure devops",
        "git",
    ]

    available = set(
        skill_data["required"]
        + skill_data["matched"]
    )

    result = []

    for skill in priority:

        if skill in available:

            if skill not in result:

                result.append(
                    skill
                )

    for skill in skill_data[
        "matched"
    ]:

        if skill not in result:

            result.append(
                skill
            )

    return result


# ============================================================
# RESUME BULLET SUGGESTIONS
# ============================================================

def bullet_suggestions(
    skill_data
):

    matched = set(
        skill_data["matched"]
    )

    bullets = []

    if (
        "databricks" in matched
        or "pyspark" in matched
    ):

        bullets.append(
            "Highlight hands-on Data Engineering "
            "experience using Databricks and PySpark."
        )

    if (
        "aws glue" in matched
        or "aws" in matched
    ):

        bullets.append(
            "Highlight AWS data engineering experience "
            "and AWS Glue pipeline migration work."
        )

    if (
        "delta lake" in matched
        or "delta lakehouse" in matched
    ):

        bullets.append(
            "Highlight Delta Lake / Lakehouse experience "
            "for reliable and scalable data pipelines."
        )

    if (
        "etl" in matched
        or "elt" in matched
    ):

        bullets.append(
            "Emphasize ETL/ELT pipeline development, "
            "transformation and validation."
        )

    if (
        "ci/cd" in matched
        or "azure devops" in matched
    ):

        bullets.append(
            "Highlight CI/CD and Azure DevOps experience "
            "for deployment and pipeline validation."
        )

    if "python" in matched:

        bullets.append(
            "Emphasize Python development for "
            "data processing and automation."
        )

    if "sql" in matched:

        bullets.append(
            "Emphasize SQL experience for "
            "data transformation and validation."
        )

    return bullets


# ============================================================
# COVER LETTER
# ============================================================

def cover_letter(
    tracker_job,
    skill_data,
    experience
):

    title = clean(
        tracker_job.get(
            "title"
        )
    )

    company = clean(
        tracker_job.get(
            "company"
        )
    )

    matched = skill_data[
        "matched"
    ]

    selected = matched[:6]

    if selected:

        skill_text = ", ".join(
            selected
        )

    else:

        skill_text = (
            "Python, PySpark and Data Engineering"
        )

    return f"""Dear Hiring Team,

I am writing to express my interest in the {title} position at {company}.

I currently work in Data Engineering and have approximately {experience['current']:.1f} years of professional experience. My experience includes {skill_text}.

My current work involves developing, migrating, validating and deploying data pipelines, and I am particularly interested in opportunities where I can apply my Data Engineering and cloud data platform experience.

I would appreciate the opportunity to discuss how my experience could contribute to your team.

Best regards,
Vishwas Singh
"""


# ============================================================
# CHECKLIST
# ============================================================

def checklist(
    skill_data,
    experience
):

    result = [

        "Open the original job posting.",

        "Confirm the position is still active.",

        "Confirm location / work arrangement.",

        "Confirm the experience requirement.",

        "Review the required qualifications.",

        "Tailor the resume using only genuine experience.",

        "Do not claim missing skills as professional experience.",

        "Submit through the official company application portal.",

        "Record the application in application_tracker.py.",
    ]

    if skill_data[
        "missing"
    ]:

        result.append(
            "Review missing skills: "
            + ", ".join(
                skill_data["missing"]
            )
        )

    if experience[
        "status"
    ] in [
        "CLOSE",
        "STRETCH",
    ]:

        result.append(
            "This is an experience stretch; "
            "apply if the posting appears flexible."
        )

    return result


# ============================================================
# PREPARE JOB
# ============================================================

def prepare_job(
    tracker_job,
    resume_match
):

    skills = get_skill_data(
        resume_match
    )

    skills = fallback_skill_analysis(
        tracker_job,
        skills
    )

    experience = analyze_experience(
        tracker_job,
        resume_match
    )

    return {

        "id": clean(
            tracker_job.get(
                "id"
            )
        ),

        "category": clean(
            tracker_job.get(
                "category"
            )
        ),

        "title": clean(
            tracker_job.get(
                "title"
            )
        ),

        "company": clean(
            tracker_job.get(
                "company"
            )
        ),

        "location": clean(
            tracker_job.get(
                "location"
            )
        ),

        "url": clean(
            tracker_job.get(
                "url"
            )
        ),

        "match_score": number(
            tracker_job.get(
                "match_score"
            )
        ),

        "priority": number(
            tracker_job.get(
                "priority"
            )
        ),

        "status": clean(
            tracker_job.get(
                "status",
                tracker_job.get(
                    "application_status"
                )
            )
        ),

        "experience_analysis":
            experience,

        "skill_analysis":
            skills,

        "resume_keywords":
            resume_keywords(
                skills
            ),

        "resume_bullet_suggestions":
            bullet_suggestions(
                skills
            ),

        "cover_letter":
            cover_letter(
                tracker_job,
                skills,
                experience
            ),

        "application_checklist":
            checklist(
                skills,
                experience
            ),

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    tracker = load_json(
        TRACKER_FILE
    )

    resume_matches = load_json(
        RESUME_MATCHES_FILE
    )

    print()
    print("=" * 100)
    print(
        "                         APPLICATION PREP"
    )
    print("=" * 100)
    print()

    print(
        f"Tracker jobs loaded: "
        f"{len(tracker)}"
    )

    print(
        f"Resume matches loaded: "
        f"{len(resume_matches)}"
    )

    print()

    resume_index = build_resume_index(
        resume_matches
    )

    prepared = []

    for tracker_job in tracker:

        category = normalize(
            tracker_job.get(
                "category"
            )
        )

        if category not in {
            "apply",
            "apply now",
            "strong apply",
        }:

            continue

        resume_match = find_resume_match(
            tracker_job,
            resume_index
        )

        prepared.append(
            prepare_job(
                tracker_job,
                resume_match
            )
        )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            prepared,
            f,
            indent=2,
            ensure_ascii=False
        )

    # ========================================================
    # REPORT
    # ========================================================

    lines = []

    lines.append(
        "=" * 100
    )

    lines.append(
        "                         APPLICATION PREPARATION"
    )

    lines.append(
        "=" * 100
    )

    lines.append("")

    lines.append(
        f"Applications prepared: "
        f"{len(prepared)}"
    )

    lines.append("")

    for i, job in enumerate(
        prepared,
        1
    ):

        skills = job[
            "skill_analysis"
        ]

        exp = job[
            "experience_analysis"
        ]

        lines.append(
            "=" * 100
        )

        lines.append(
            f"#{i} [{job['id']}] "
            f"{job['category']}"
        )

        lines.append(
            f"TITLE: {job['title']}"
        )

        lines.append(
            f"COMPANY: {job['company']}"
        )

        lines.append(
            f"LOCATION: {job['location']}"
        )

        lines.append(
            f"MATCH SCORE: "
            f"{job['match_score']}/100"
        )

        lines.append("")

        lines.append(
            "EXPERIENCE"
        )

        lines.append(
            f"Required: {exp['required']}"
        )

        lines.append(
            f"Your experience: {exp['current']}"
        )

        lines.append(
            f"Status: {exp['status']}"
        )

        lines.append("")

        lines.append(
            "REQUIRED SKILLS"
        )

        lines.append(
            ", ".join(
                skills["required"]
            )
            or "Not available"
        )

        lines.append("")

        lines.append(
            "MATCHED SKILLS"
        )

        lines.append(
            ", ".join(
                skills["matched"]
            )
            or "None"
        )

        lines.append("")

        lines.append(
            "MISSING SKILLS"
        )

        lines.append(
            ", ".join(
                skills["missing"]
            )
            or "None"
        )

        lines.append("")

        lines.append(
            "RESUME KEYWORDS"
        )

        lines.append(
            ", ".join(
                job[
                    "resume_keywords"
                ]
            )
            or "None"
        )

        lines.append("")

        lines.append(
            "RESUME BULLET SUGGESTIONS"
        )

        for bullet in job[
            "resume_bullet_suggestions"
        ]:

            lines.append(
                f"- {bullet}"
            )

        lines.append("")

        lines.append(
            "COVER LETTER"
        )

        lines.append(
            job[
                "cover_letter"
            ]
        )

        lines.append(
            "APPLICATION CHECKLIST"
        )

        for item in job[
            "application_checklist"
        ]:

            lines.append(
                f"[ ] {item}"
            )

        lines.append("")

        lines.append(
            f"URL: {job['url']}"
        )

        lines.append("")

    with open(
        OUTPUT_TEXT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )

    # ========================================================
    # CONSOLE
    # ========================================================

    print(
        f"Applications prepared: "
        f"{len(prepared)}"
    )

    print()

    print(
        f"JSON saved: "
        f"{OUTPUT_JSON}"
    )

    print(
        f"Report saved: "
        f"{OUTPUT_TEXT}"
    )

    print()

    print("=" * 100)

    print(
        "                         TOP APPLICATIONS"
    )

    print("=" * 100)

    for i, job in enumerate(
        prepared[:15],
        1
    ):

        skills = job[
            "skill_analysis"
        ]

        print()

        print(
            f"#{i} [{job['id']}] "
            f"{job['category']}"
        )

        print(
            f"TITLE: {job['title']}"
        )

        print(
            f"COMPANY: {job['company']}"
        )

        print(
            f"MATCH: "
            f"{job['match_score']}/100"
        )

        print(
            "MATCHED: "
            + (
                ", ".join(
                    skills["matched"]
                )
                or "None"
            )
        )

        print(
            "MISSING: "
            + (
                ", ".join(
                    skills["missing"]
                )
                or "None"
            )
        )

        print(
            "RESUME KEYWORDS: "
            + (
                ", ".join(
                    job[
                        "resume_keywords"
                    ]
                )
                or "None"
            )
        )

        print(
            f"URL: {job['url']}"
        )

        print(
            "-" * 100
        )

    print()
    print("Done.")


if __name__ == "__main__":
    main()