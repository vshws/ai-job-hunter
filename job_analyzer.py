import json
import re
import os
from datetime import datetime


# ============================================================
# FILES
# ============================================================

JOBS_FILE = "jobs.json"

OUTPUT_JSON = "job_analysis.json"

OUTPUT_TEXT = "job_analysis.txt"


# ============================================================
# YOUR REAL PROFILE
#
# Based on your current resume.
# Do NOT add skills here that you do not actually have.
# ============================================================

PROFILE = {

    "name": "Vishwas R Singh",

    "experience_years": 1.0,

    "current_role": "System Engineer / Data Engineer",

    "company": "Infosys",

    "client": "bp",

    "education": [
        "B.Tech Computer Science and Engineering",
        "SRM Institute of Science and Technology"
    ],

    "certifications": [
        "Databricks Certified Data Engineer Associate"
    ],

    "skills": {

        "databricks": 1.0,

        "pyspark": 1.0,

        "spark": 1.0,

        "python": 1.0,

        "sql": 1.0,

        "delta lake": 1.0,

        "delta lakehouse": 1.0,

        "aws": 1.0,

        "aws glue": 1.0,

        "azure": 1.0,

        "azure devops": 1.0,

        "etl": 1.0,

        "elt": 1.0,

        "data engineering": 1.0,

        "data pipeline": 1.0,

        "data migration": 1.0,

        "ci/cd": 1.0,

        "git": 1.0,

        "data validation": 1.0,

        "data reconciliation": 1.0,

        "production support": 1.0,

        "agile": 1.0,

        "mlflow": 1.0,

    },

    "preferred_locations": [

        "pune",
        "bangalore",
        "bengaluru",
        "hyderabad",
        "chennai",
        "mumbai",
        "delhi",
        "gurgaon",
        "gurugram",
        "noida",
        "lucknow",
        "kochi",
        "remote",
        "india",

    ],

}


# ============================================================
# SKILL IMPORTANCE
#
# Higher = more important for your profile.
# ============================================================

SKILL_WEIGHTS = {

    "databricks": 10,

    "pyspark": 10,

    "spark": 8,

    "python": 8,

    "sql": 8,

    "delta lake": 9,

    "delta lakehouse": 9,

    "aws glue": 8,

    "aws": 6,

    "azure": 6,

    "azure devops": 5,

    "etl": 6,

    "elt": 5,

    "data engineering": 8,

    "data pipeline": 6,

    "data migration": 7,

    "ci/cd": 4,

    "git": 4,

    "data validation": 4,

    "data reconciliation": 4,

    "production support": 3,

    "agile": 2,

    "mlflow": 3,

}


# ============================================================
# REQUIRED / IMPORTANT SKILLS
#
# These affect the final score more strongly.
# ============================================================

CORE_SKILLS = [

    "databricks",
    "pyspark",
    "python",
    "sql",
    "spark",
    "delta lake",
    "data engineering",

]


# ============================================================
# SENIORITY
# ============================================================

SENIOR_TERMS = [

    "senior",
    "sr.",
    "sr ",
    "lead",
    "principal",
    "staff",
    "manager",
    "director",
    "architect",
    "head of",
    "vice president",
    "vice-president",
    "assistant vice president",
    "avp",

]


# ============================================================
# EXPERIENCE PATTERNS
# ============================================================

EXPERIENCE_PATTERNS = [

    r"(\d+(?:\.\d+)?)\s*\+\s*years?",

    r"minimum\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*years?",

    r"at\s+least\s+(\d+(?:\.\d+)?)\s*years?",

    r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*years?",

    r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*years?",

    r"(\d+(?:\.\d+)?)\s*years?\s*of\s*experience",

]


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).lower()


def normalize_text(value):

    text = clean_text(value)

    text = text.replace(
        "&",
        " and "
    )

    text = re.sub(
        r"[^a-z0-9+#./\- ]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_job_text(job):

    parts = [

        job.get("title"),

        job.get("company"),

        job.get("employer"),

        job.get("organization"),

        job.get("description"),

        job.get("location"),

    ]

    skills = job.get(
        "skills"
    )

    if isinstance(
        skills,
        list
    ):

        parts.extend(
            skills
        )

    elif skills:

        parts.append(
            skills
        )

    return normalize_text(
        " ".join(
            str(x)
            for x in parts
            if x
        )
    )


def get_title(job):

    return normalize_text(
        job.get("title")
        or ""
    )


def get_company(job):

    return (

        job.get("company")

        or job.get("employer")

        or job.get("organization")

        or "Unknown"

    )


def get_location(job):

    return (

        job.get("location")

        or job.get("cities")

        or job.get("regions")

        or "Unknown"

    )


def get_url(job):

    return (
        job.get("url")
        or "No URL"
    )


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience_from_text(
    text
):

    text = normalize_text(
        text
    )

    candidates = []

    for pattern in EXPERIENCE_PATTERNS:

        matches = re.findall(
            pattern,
            text
        )

        for match in matches:

            if isinstance(
                match,
                tuple
            ):

                numbers = []

                for value in match:

                    if value:

                        try:

                            numbers.append(
                                float(value)
                            )

                        except ValueError:

                            pass

                if numbers:

                    candidates.append(
                        max(numbers)
                    )

            else:

                try:

                    candidates.append(
                        float(match)
                    )

                except ValueError:

                    pass

    if not candidates:

        return None

    return max(
        candidates
    )


def get_job_experience(
    job
):

    enrichment = job.get(
        "enrichment"
    ) or {}

    api_value = enrichment.get(
        "experience_years_min"
    )

    api_experience = None

    if api_value is not None:

        try:

            api_experience = float(
                api_value
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    description = job.get(
        "description"
    ) or ""

    description_experience = (
        extract_experience_from_text(
            description
        )
    )

    if (
        api_experience is not None
        and description_experience is not None
    ):

        return max(
            api_experience,
            description_experience
        )

    if api_experience is not None:

        return api_experience

    return description_experience


# ============================================================
# SENIORITY
# ============================================================

def is_senior_title(
    title
):

    title = normalize_text(
        title
    )

    for term in SENIOR_TERMS:

        if term in title:

            return True

    return False


# ============================================================
# LOCATION
# ============================================================

def location_match(
    job
):

    location = normalize_text(
        get_location(job)
    )

    for preferred in PROFILE[
        "preferred_locations"
    ]:

        if preferred in location:

            return preferred

    return None


# ============================================================
# ENTRY LEVEL
# ============================================================

def entry_level_signal(
    job
):

    text = get_job_text(
        job
    )

    terms = [

        "junior",

        "entry level",

        "entry-level",

        "associate",

        "graduate",

        "new grad",

        "new graduate",

        "fresher",

        "trainee",

        "early career",

        "0-1 years",

        "0 to 1 years",

        "1 year experience",

        "1+ year",

    ]

    matches = []

    for term in terms:

        if term in text:

            matches.append(
                term
            )

    return matches


# ============================================================
# SKILL MATCHING
# ============================================================

def find_skill_matches(
    job
):

    text = get_job_text(
        job
    )

    matched = []

    missing = []

    total_weight = 0

    matched_weight = 0

    for skill, weight in SKILL_WEIGHTS.items():

        total_weight += weight

        if skill in text:

            matched.append(
                skill
            )

            matched_weight += weight

        else:

            missing.append(
                skill
            )

    if total_weight == 0:

        skill_percentage = 0

    else:

        skill_percentage = (
            matched_weight
            / total_weight
            * 100
        )

    return (
        matched,
        missing,
        skill_percentage
    )


# ============================================================
# CORE SKILLS
# ============================================================

def find_core_skill_matches(
    job
):

    text = get_job_text(
        job
    )

    matched = []

    missing = []

    for skill in CORE_SKILLS:

        if skill in text:

            matched.append(
                skill
            )

        else:

            missing.append(
                skill
            )

    return matched, missing


# ============================================================
# JOB DESCRIPTION REQUIREMENTS
# ============================================================

def extract_requirement_signals(
    job
):

    text = get_job_text(
        job
    )

    signals = {

        "python": "python" in text,

        "sql": "sql" in text,

        "pyspark": "pyspark" in text,

        "spark": "spark" in text,

        "databricks": "databricks" in text,

        "delta": (
            "delta lake" in text
            or "delta lakehouse" in text
        ),

        "aws": "aws" in text,

        "azure": "azure" in text,

        "etl": "etl" in text,

        "airflow": "airflow" in text,

        "snowflake": "snowflake" in text,

        "dbt": "dbt" in text,

    }

    return signals


# ============================================================
# EXPERIENCE SCORE
# ============================================================

def experience_score(
    job_experience
):

    user_experience = (
        PROFILE[
            "experience_years"
        ]
    )

    if job_experience is None:

        return 70, "Unknown"

    if job_experience <= user_experience:

        return 100, "Excellent"

    difference = (
        job_experience
        - user_experience
    )

    if difference <= 0.5:

        return 90, "Very good"

    if difference <= 1:

        return 80, "Good"

    if difference <= 1.5:

        return 65, "Stretch"

    if difference <= 2:

        return 45, "Significant stretch"

    return 20, "Too senior"


# ============================================================
# OVERALL SCORE
# ============================================================

def calculate_final_score(
    job
):

    job_exp = get_job_experience(
        job
    )

    skill_matches, skill_missing, skill_percentage = (
        find_skill_matches(
            job
        )
    )

    core_matches, core_missing = (
        find_core_skill_matches(
            job
        )
    )

    exp_score, exp_label = (
        experience_score(
            job_exp
        )
    )

    loc = location_match(
        job
    )

    entry_signals = entry_level_signal(
        job
    )

    title = get_title(
        job
    )

    senior = is_senior_title(
        title
    )

    # --------------------------------------------------------
    # Base
    # --------------------------------------------------------

    score = 0

    # Skill match = 45%
    score += (
        skill_percentage
        * 0.45
    )

    # Experience = 25%
    score += (
        exp_score
        * 0.25
    )

    # Core skills = 15%
    if len(CORE_SKILLS) > 0:

        core_percentage = (
            len(core_matches)
            / len(CORE_SKILLS)
            * 100
        )

    else:

        core_percentage = 0

    score += (
        core_percentage
        * 0.15
    )

    # Location = 10%
    if loc:

        location_score = 100

    else:

        location_score = 0

    score += (
        location_score
        * 0.10
    )

    # Entry level = 5%
    if entry_signals:

        entry_score = 100

    else:

        entry_score = 0

    score += (
        entry_score
        * 0.05
    )

    # --------------------------------------------------------
    # Senior penalty
    # --------------------------------------------------------

    if senior:

        score -= 35

    # --------------------------------------------------------
    # Core skill penalty
    # --------------------------------------------------------

    # If more than half of the core skills
    # are missing, reduce confidence.

    if len(core_missing) >= 4:

        score -= 15

    elif len(core_missing) >= 3:

        score -= 8

    # --------------------------------------------------------
    # Experience penalty
    # --------------------------------------------------------

    if job_exp is not None:

        if job_exp >= 3:

            score -= 10

        elif job_exp > 2:

            score -= 5

    score = max(
        0,
        min(
            100,
            round(score)
        )
    )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if (
        score >= 85
        and job_exp is not None
        and job_exp <= 2
        and len(core_matches) >= 4
    ):

        recommendation = "🔥 APPLY"

    elif (
        score >= 80
        and (
            job_exp is None
            or job_exp <= 2
        )
    ):

        recommendation = "🟢 STRONG APPLY"

    elif score >= 70:

        recommendation = "🟡 MAYBE"

    elif score >= 55:

        recommendation = "🟠 STRETCH"

    else:

        recommendation = "🔴 LOW PRIORITY"

    return {

        "final_score": score,

        "recommendation": recommendation,

        "job_experience": job_exp,

        "experience_score": exp_score,

        "experience_label": exp_label,

        "skill_percentage": round(
            skill_percentage
        ),

        "core_percentage": round(
            core_percentage
        ),

        "matched_skills": skill_matches,

        "missing_skills": skill_missing,

        "core_matches": core_matches,

        "core_missing": core_missing,

        "location_match": loc,

        "entry_level_signals": entry_signals,

        "senior_title": senior,

        "signals": extract_requirement_signals(
            job
        ),

    }


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    results
):

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# TEXT REPORT
# ============================================================

def generate_text_report(
    results
):

    lines = []

    lines.append(
        "=" * 80
    )

    lines.append(
        "             AI JOB ANALYSIS REPORT"
    )

    lines.append(
        "=" * 80
    )

    lines.append("")

    lines.append(
        f"Generated: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    lines.append("")

    lines.append(
        f"Jobs analyzed: "
        f"{len(results)}"
    )

    lines.append("")

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    apply_count = 0
    strong_count = 0
    maybe_count = 0
    stretch_count = 0
    low_count = 0

    for item in results:

        rec = item[
            "analysis"
        ][
            "recommendation"
        ]

        if "🔥 APPLY" in rec:

            apply_count += 1

        elif "STRONG APPLY" in rec:

            strong_count += 1

        elif "MAYBE" in rec:

            maybe_count += 1

        elif "STRETCH" in rec:

            stretch_count += 1

        else:

            low_count += 1

    lines.append(
        f"🔥 APPLY: {apply_count}"
    )

    lines.append(
        f"🟢 STRONG APPLY: {strong_count}"
    )

    lines.append(
        f"🟡 MAYBE: {maybe_count}"
    )

    lines.append(
        f"🟠 STRETCH: {stretch_count}"
    )

    lines.append(
        f"🔴 LOW PRIORITY: {low_count}"
    )

    lines.append("")

    lines.append(
        "=" * 80
    )

    lines.append(
        "TOP MATCHES"
    )

    lines.append(
        "=" * 80
    )

    # --------------------------------------------------------
    # TOP 30
    # --------------------------------------------------------

    for rank, item in enumerate(
        results[:30],
        1
    ):

        job = item[
            "job"
        ]

        analysis = item[
            "analysis"
        ]

        lines.append("")

        lines.append(
            f"#{rank} "
            f"{analysis['final_score']}/100 "
            f"{analysis['recommendation']}"
        )

        lines.append(
            f"TITLE: "
            f"{job.get('title', 'Unknown')}"
        )

        lines.append(
            f"COMPANY: "
            f"{get_company(job)}"
        )

        lines.append(
            f"LOCATION: "
            f"{get_location(job)}"
        )

        lines.append(
            f"EXPERIENCE: "
            f"{analysis['job_experience']}"
        )

        lines.append(
            f"SKILL MATCH: "
            f"{analysis['skill_percentage']}%"
        )

        lines.append(
            f"CORE SKILLS: "
            f"{analysis['core_percentage']}%"
        )

        lines.append(
            "MATCHED: "
            + (
                ", ".join(
                    analysis[
                        "matched_skills"
                    ]
                )
                if analysis[
                    "matched_skills"
                ]
                else "None"
            )
        )

        lines.append(
            "MISSING: "
            + (
                ", ".join(
                    analysis[
                        "core_missing"
                    ]
                )
                if analysis[
                    "core_missing"
                ]
                else "None"
            )
        )

        if analysis[
            "entry_level_signals"
        ]:

            lines.append(
                "ENTRY SIGNALS: "
                + ", ".join(
                    analysis[
                        "entry_level_signals"
                    ]
                )
            )

        lines.append(
            f"URL: "
            f"{get_url(job)}"
        )

        lines.append(
            "-" * 80
        )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print("=" * 80)

    print(
        "             AI JOB ANALYZER"
    )

    print("=" * 80)

    # --------------------------------------------------------
    # Check jobs file
    # --------------------------------------------------------

    if not os.path.exists(
        JOBS_FILE
    ):

        print()

        print(
            "ERROR:"
        )

        print(
            "jobs.json was not found."
        )

        print()

        print(
            "Run this first:"
        )

        print(
            "python job_search.py"
        )

        return

    # --------------------------------------------------------
    # Load jobs
    # --------------------------------------------------------

    try:

        with open(
            JOBS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            jobs = json.load(
                file
            )

    except Exception as e:

        print()

        print(
            "ERROR reading jobs.json:"
        )

        print(e)

        return

    if not isinstance(
        jobs,
        list
    ):

        print(
            "ERROR: jobs.json is not a list."
        )

        return

    print()

    print(
        f"Jobs loaded: "
        f"{len(jobs)}"
    )

    print()

    print(
        "Analyzing jobs against your profile..."
    )

    # --------------------------------------------------------
    # Analyze
    # --------------------------------------------------------

    results = []

    for index, job in enumerate(
        jobs,
        1
    ):

        try:

            analysis = calculate_final_score(
                job
            )

            results.append(
                {
                    "job": job,
                    "analysis": analysis,
                }
            )

        except Exception as e:

            print(
                f"Warning: "
                f"job {index} failed: {e}"
            )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    results.sort(
        key=lambda item:
        item[
            "analysis"
        ][
            "final_score"
        ],
        reverse=True
    )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    save_json(
        results
    )

    # --------------------------------------------------------
    # Save text
    # --------------------------------------------------------

    report = generate_text_report(
        results
    )

    with open(
        OUTPUT_TEXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()

    print(
        "=" * 80
    )

    print(
        "ANALYSIS COMPLETE"
    )

    print(
        "=" * 80
    )

    print()

    print(
        f"Jobs analyzed: "
        f"{len(results)}"
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

    print(
        "=" * 80
    )

    print(
        "TOP 15 JOBS"
    )

    print(
        "=" * 80
    )

    # --------------------------------------------------------
    # Top 15
    # --------------------------------------------------------

    for rank, item in enumerate(
        results[:15],
        1
    ):

        job = item[
            "job"
        ]

        analysis = item[
            "analysis"
        ]

        print()

        print(
            f"#{rank} "
            f"[{analysis['final_score']}/100] "
            f"{analysis['recommendation']}"
        )

        print(
            f"{job.get('title', 'Unknown')}"
        )

        print(
            f"{get_company(job)}"
        )

        print(
            f"{get_location(job)}"
        )

        print(
            f"Experience: "
            f"{analysis['job_experience']}"
        )

        print(
            f"Skills: "
            f"{analysis['skill_percentage']}%"
        )

        print(
            f"Core: "
            f"{analysis['core_percentage']}%"
        )

        print(
            f"URL: "
            f"{get_url(job)}"
        )

        print(
            "-" * 80
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()