import json
import os
import re
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "resume_matches.json"

OUTPUT_JSON = "application_queue.json"
OUTPUT_TEXT = "application_queue.txt"


# ============================================================
# YOUR PROFILE
# ============================================================

JOINING_DATE = "2025-08-08"

# Current experience is calculated dynamically.
# This is only used as a fallback if resume_matcher
# did not already provide your experience.
CURRENT_EXPERIENCE = 1.02


# ============================================================
# LOCATION PREFERENCE
# ============================================================

PREFERRED_LOCATIONS = [
    "bangalore",
    "bengaluru",
    "hyderabad",
    "pune",
    "chennai",
    "mumbai",
    "gurgaon",
    "gurugram",
    "noida",
    "delhi",
    "india",
    "remote",
]


# ============================================================
# TARGET SKILLS
# ============================================================

HIGH_VALUE_SKILLS = {
    "databricks": 15,
    "pyspark": 12,
    "spark": 10,
    "delta lake": 12,
    "delta lakehouse": 12,
    "aws glue": 10,
    "aws": 8,
    "python": 7,
    "sql": 7,
    "etl": 6,
    "azure": 6,
    "mlflow": 5,
    "ci/cd": 5,
    "git": 4,
}


# ============================================================
# LOAD JSON
# ============================================================

def load_json():

    if not os.path.exists(INPUT_FILE):

        print(
            f"ERROR: {INPUT_FILE} not found."
        )

        return []

    try:

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except Exception as error:

        print(
            "ERROR loading JSON:"
        )

        print(error)

        return []

    if isinstance(
        data,
        list
    ):

        return data

    if isinstance(
        data,
        dict
    ):

        for key in [
            "jobs",
            "results",
            "matches",
            "data",
        ]:

            if isinstance(
                data.get(key),
                list
            ):

                return data[key]

    return []


# ============================================================
# HELPERS
# ============================================================

def clean_text(
    value
):

    if value is None:

        return ""

    if isinstance(
        value,
        list
    ):

        return " ".join(
            clean_text(x)
            for x in value
        )

    if isinstance(
        value,
        dict
    ):

        return " ".join(
            clean_text(v)
            for v in value.values()
        )

    return str(
        value
    ).strip()


def normalize(
    value
):

    return re.sub(
        r"\s+",
        " ",
        clean_text(
            value
        ).lower()
    ).strip()


def get_job(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return {}

    job = item.get(
        "job"
    )

    if isinstance(
        job,
        dict
    ):

        return job

    return item


def get_verification(
    item
):

    verification = item.get(
        "verification"
    )

    if isinstance(
        verification,
        dict
    ):

        return verification

    return {}


def get_title(
    item
):

    job = get_job(
        item
    )

    return clean_text(
        job.get("title")
        or job.get("job_title")
        or ""
    )


def get_company(
    item
):

    job = get_job(
        item
    )

    return clean_text(
        job.get("company")
        or job.get("employer")
        or job.get("organization")
        or "Unknown"
    )


def get_location(
    item
):

    job = get_job(
        item
    )

    return clean_text(
        job.get("location")
        or job.get("locations")
        or job.get("cities")
        or ""
    )


def get_url(
    item
):

    job = get_job(
        item
    )

    return clean_text(
        job.get("url")
        or job.get("job_url")
        or ""
    )


# ============================================================
# NUMERIC HELPERS
# ============================================================

def safe_float(
    value
):

    if value is None:

        return None

    try:

        return float(
            value
        )

    except (
        ValueError,
        TypeError
    ):

        return None


# ============================================================
# EXPERIENCE
# ============================================================

def get_required_experience(
    item
):

    verification = get_verification(
        item
    )

    value = verification.get(
        "experience_years_min"
    )

    if value is not None:

        return safe_float(
            value
        )

    # Fallback to fields that may already exist
    # inside resume_matches.json.

    for source in [
        item,
        get_job(item),
    ]:

        for key in [
            "experience_required",
            "experience_min",
            "experience_years_min",
            "required_experience",
        ]:

            value = source.get(
                key
            )

            if value is not None:

                return safe_float(
                    value
                )

    return None


# ============================================================
# EXPERIENCE STATUS
# ============================================================

def calculate_experience_status(
    required,
    current
):

    if required is None:

        return "UNKNOWN"

    if required <= current:

        return "MEETS"

    difference = (
        required
        - current
    )

    # Up to 0.5 year difference:
    # still considered close.

    if difference <= 0.5:

        return "CLOSE"

    # Up to 1 year above current experience:
    # stretch but potentially worth applying.

    if difference <= 1.0:

        return "STRETCH"

    # More than one year above current:
    # too senior for current profile.

    return "TOO_SENIOR"


# ============================================================
# MATCH SCORE
# ============================================================

def get_match_score(
    item
):

    # First check direct match score.

    for key in [
        "match_score",
        "score",
        "resume_score",
    ]:

        value = item.get(
            key
        )

        number = safe_float(
            value
        )

        if number is not None:

            return max(
                0,
                min(
                    100,
                    number
                )
            )

    # Sometimes the score is nested.

    for key in [
        "matching",
        "match",
        "analysis",
        "result",
    ]:

        nested = item.get(
            key
        )

        if isinstance(
            nested,
            dict
        ):

            for score_key in [
                "match_score",
                "score",
                "resume_score",
            ]:

                number = safe_float(
                    nested.get(
                        score_key
                    )
                )

                if number is not None:

                    return max(
                        0,
                        min(
                            100,
                            number
                        )
                    )

    return 0


# ============================================================
# SKILLS
# ============================================================

def get_required_skills(
    item
):

    verification = get_verification(
        item
    )

    skills = verification.get(
        "required_skills"
    )

    if isinstance(
        skills,
        list
    ):

        return [
            normalize(x)
            for x in skills
            if normalize(x)
        ]

    # Fallback fields.

    for source in [
        item,
        get_job(item),
    ]:

        for key in [
            "required_skills",
            "skills",
        ]:

            skills = source.get(
                key
            )

            if isinstance(
                skills,
                list
            ):

                return [
                    normalize(x)
                    for x in skills
                    if normalize(x)
                ]

    return []


def get_matched_skills(
    item
):

    for source in [
        item,
        get_job(item),
    ]:

        skills = source.get(
            "matched"
        )

        if isinstance(
            skills,
            list
        ):

            return [
                normalize(x)
                for x in skills
                if normalize(x)
            ]

        skills = source.get(
            "matched_skills"
        )

        if isinstance(
            skills,
            list
        ):

            return [
                normalize(x)
                for x in skills
                if normalize(x)
            ]

    return []


def get_missing_skills(
    item
):

    for source in [
        item,
        get_job(item),
    ]:

        skills = source.get(
            "missing"
        )

        if isinstance(
            skills,
            list
        ):

            return [
                normalize(x)
                for x in skills
                if normalize(x)
            ]

        skills = source.get(
            "missing_skills"
        )

        if isinstance(
            skills,
            list
        ):

            return [
                normalize(x)
                for x in skills
                if normalize(x)
            ]

    return []


# ============================================================
# LOCATION SCORE
# ============================================================

def location_score(
    location
):

    location = normalize(
        location
    )

    if not location:

        return 0

    for preferred in PREFERRED_LOCATIONS:

        if preferred in location:

            if preferred in [
                "bangalore",
                "bengaluru",
                "hyderabad",
                "pune",
                "chennai",
                "mumbai",
            ]:

                return 100

            if preferred == "remote":

                return 95

            if preferred == "india":

                return 80

            return 60

    return 20


# ============================================================
# TITLE RELEVANCE
# ============================================================

def title_score(
    title
):

    title = normalize(
        title
    )

    strong_titles = [
        "data engineer",
        "data engineering",
        "databricks data engineer",
        "aws data engineer",
        "azure data engineer",
        "pyspark data engineer",
        "etl data engineer",
    ]

    for phrase in strong_titles:

        if phrase in title:

            return 100

    related_titles = [
        "software engineer",
        "analytics engineer",
        "data platform",
        "data analyst",
        "machine learning engineer",
    ]

    for phrase in related_titles:

        if phrase in title:

            return 70

    return 30


# ============================================================
# SENIORITY
# ============================================================

def detect_seniority(
    title
):

    title = normalize(
        title
    )

    senior_terms = [
        "senior",
        "sr.",
        "sr ",
        "lead",
        "principal",
        "staff",
        "manager",
        "director",
        "architect",
    ]

    junior_terms = [
        "junior",
        "jr.",
        "jr ",
        "associate",
        "entry",
        "graduate",
        "fresher",
        "trainee",
    ]

    for term in senior_terms:

        if term in title:

            return "SENIOR"

    for term in junior_terms:

        if term in title:

            return "JUNIOR"

    return "NORMAL"


# ============================================================
# HIGH VALUE SKILL SCORE
# ============================================================

def high_value_skill_score(
    matched_skills
):

    score = 0

    matched = set(
        normalize(x)
        for x in matched_skills
    )

    for skill, points in HIGH_VALUE_SKILLS.items():

        if skill in matched:

            score += points

    return min(
        score,
        100
    )


# ============================================================
# APPLICATION DECISION
# ============================================================

def determine_category(
    match_score,
    experience_status,
    required_experience,
    seniority
):

    # ========================================================
    # IMPORTANT NEW RULE
    #
    # APPLY when:
    #
    # 1. Experience is suitable
    #       OR
    # 2. Match score >= 80
    #
    # BUT:
    # Clearly senior / 3+ year roles remain rejected.
    # ========================================================

    high_match = (
        match_score >= 80
    )

    experience_suitable = (
        experience_status
        in [
            "MEETS",
            "CLOSE",
        ]
    )

    # --------------------------------------------------------
    # Hard rejection for clearly senior roles.
    # --------------------------------------------------------

    if (
        required_experience is not None
        and required_experience >= 3.0
    ):

        return (
            "REJECT",
            "Experience requirement is 3+ years"
        )

    if seniority == "SENIOR":

        # A high skill score alone should not make
        # an obviously senior role an APPLY NOW.

        if (
            required_experience is not None
            and required_experience >= 2.5
        ):

            return (
                "REJECT",
                "Senior role is above current experience"
            )

    # --------------------------------------------------------
    # NEW OR CONDITION
    # --------------------------------------------------------

    if (
        experience_suitable
        or high_match
    ):

        # Very strong match.

        if match_score >= 90:

            return (
                "APPLY NOW",
                "Experience suitable OR match score >= 80; score >= 90"
            )

        if match_score >= 80:

            return (
                "APPLY",
                "Experience suitable OR match score >= 80"
            )

        return (
            "STRONG APPLY",
            "Experience requirement is suitable"
        )

    # --------------------------------------------------------
    # UNKNOWN EXPERIENCE
    # --------------------------------------------------------

    if (
        experience_status
        == "UNKNOWN"
    ):

        if match_score >= 70:

            return (
                "REVIEW",
                "Experience unknown; good profile match"
            )

        return (
            "VERIFY FIRST",
            "Experience requirement could not be verified"
        )

    # --------------------------------------------------------
    # STRETCH
    # --------------------------------------------------------

    if (
        experience_status
        == "STRETCH"
    ):

        if match_score >= 70:

            return (
                "STRETCH",
                "Experience above profile but technical match is good"
            )

        return (
            "LOW PRIORITY",
            "Experience above profile"
        )

    # --------------------------------------------------------
    # TOO SENIOR
    # --------------------------------------------------------

    if (
        experience_status
        == "TOO_SENIOR"
    ):

        return (
            "REJECT",
            "Experience requirement is significantly above profile"
        )

    return (
        "REVIEW",
        "Needs manual review"
    )


# ============================================================
# PRIORITY SCORE
# ============================================================

def calculate_priority(
    match_score,
    category,
    location_score_value,
    required_experience,
    current_experience
):

    priority = float(
        match_score
    )

    # Location bonus.

    priority += (
        location_score_value
        * 0.10
    )

    # --------------------------------------------------------
    # Experience bonus.
    # --------------------------------------------------------

    if required_experience is not None:

        if required_experience <= current_experience:

            priority += 15

        elif (
            required_experience
            - current_experience
            <= 0.5
        ):

            priority += 8

        elif (
            required_experience
            - current_experience
            <= 1
        ):

            priority += 2

        else:

            priority -= 15

    # --------------------------------------------------------
    # Category bonus.
    # --------------------------------------------------------

    category_bonus = {

        "APPLY NOW": 20,

        "APPLY": 15,

        "STRONG APPLY": 10,

        "REVIEW": 0,

        "VERIFY FIRST": -2,

        "STRETCH": -5,

        "LOW PRIORITY": -10,

        "REJECT": -30,
    }

    priority += category_bonus.get(
        category,
        0
    )

    return round(
        priority,
        1
    )


# ============================================================
# BUILD APPLICATION ENTRY
# ============================================================

def build_entry(
    item
):

    title = get_title(
        item
    )

    company = get_company(
        item
    )

    location = get_location(
        item
    )

    url = get_url(
        item
    )

    match_score = get_match_score(
        item
    )

    required_experience = (
        get_required_experience(
            item
        )
    )

    experience_status = (
        calculate_experience_status(
            required_experience,
            CURRENT_EXPERIENCE
        )
    )

    required_skills = (
        get_required_skills(
            item
        )
    )

    matched_skills = (
        get_matched_skills(
            item
        )
    )

    missing_skills = (
        get_missing_skills(
            item
        )
    )

    location_value = (
        location_score(
            location
        )
    )

    title_value = (
        title_score(
            title
        )
    )

    seniority = (
        detect_seniority(
            title
        )
    )

    skill_value = (
        high_value_skill_score(
            matched_skills
        )
    )

    category, reason = (
        determine_category(
            match_score,
            experience_status,
            required_experience,
            seniority
        )
    )

    priority = calculate_priority(
        match_score,
        category,
        location_value,
        required_experience,
        CURRENT_EXPERIENCE
    )

    return {

        "priority":
            priority,

        "category":
            category,

        "title":
            title,

        "company":
            company,

        "location":
            location,

        "url":
            url,

        "match_score":
            match_score,

        "your_experience":
            CURRENT_EXPERIENCE,

        "experience_required":
            required_experience,

        "experience_status":
            experience_status,

        "seniority":
            seniority,

        "title_score":
            title_value,

        "location_score":
            location_value,

        "high_value_skill_score":
            skill_value,

        "required_skills":
            required_skills,

        "matched_skills":
            matched_skills,

        "missing_skills":
            missing_skills,

        "decision_reason":
            reason,

        "high_match_rule":
            match_score >= 80,
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate(
    entries
):

    seen = set()

    result = []

    duplicates = 0

    for entry in entries:

        url = normalize(
            entry.get(
                "url"
            )
        )

        if url:

            key = url.split(
                "?",
                1
            )[0]

        else:

            key = (
                normalize(
                    entry.get(
                        "company"
                    )
                )
                + "|"
                + normalize(
                    entry.get(
                        "title"
                    )
                )
                + "|"
                + normalize(
                    entry.get(
                        "location"
                    )
                )
            )

        if key in seen:

            duplicates += 1

            continue

        seen.add(
            key
        )

        result.append(
            entry
        )

    return (
        result,
        duplicates
    )


# ============================================================
# REPORT
# ============================================================

def generate_report(
    entries
):

    lines = []

    lines.append(
        "=" * 95
    )

    lines.append(
        "                         APPLICATION RANKER"
    )

    lines.append(
        "=" * 95
    )

    lines.append("")

    lines.append(
        f"Your experience: "
        f"{CURRENT_EXPERIENCE:.2f} years"
    )

    lines.append("")

    categories = [

        "APPLY NOW",
        "APPLY",
        "STRONG APPLY",
        "REVIEW",
        "VERIFY FIRST",
        "STRETCH",
        "LOW PRIORITY",
        "REJECT",
    ]

    for category in categories:

        count = sum(
            1
            for entry in entries
            if entry[
                "category"
            ]
            == category
        )

        emoji = {

            "APPLY NOW":
                "🔥",

            "APPLY":
                "🚀",

            "STRONG APPLY":
                "🟢",

            "REVIEW":
                "🟡",

            "VERIFY FIRST":
                "🔍",

            "STRETCH":
                "🟠",

            "LOW PRIORITY":
                "🔴",

            "REJECT":
                "❌",
        }.get(
            category,
            ""
        )

        lines.append(
            f"{emoji} {category}: {count}"
        )

    lines.append("")

    lines.append(
        "=" * 95
    )

    lines.append(
        "                         TOP APPLICATIONS"
    )

    lines.append(
        "=" * 95
    )

    top = [
        entry
        for entry in entries
        if entry[
            "category"
        ]
        in [
            "APPLY NOW",
            "APPLY",
            "STRONG APPLY",
        ]
    ]

    top = sorted(
        top,
        key=lambda x:
            x["priority"],
        reverse=True
    )

    for rank, entry in enumerate(
        top,
        1
    ):

        lines.append("")

        lines.append(
            f"#{rank} "
            f"[Priority "
            f"{entry['priority']}] "
            f"{entry['category']}"
        )

        lines.append(
            f"TITLE: "
            f"{entry['title']}"
        )

        lines.append(
            f"COMPANY: "
            f"{entry['company']}"
        )

        lines.append(
            f"LOCATION: "
            f"{entry['location']}"
        )

        lines.append(
            f"MATCH SCORE: "
            f"{entry['match_score']}/100"
        )

        lines.append(
            f"EXPERIENCE: "
            f"{entry['experience_required']} "
            f"years required vs "
            f"{entry['your_experience']:.2f}"
        )

        lines.append(
            f"EXPERIENCE STATUS: "
            f"{entry['experience_status']}"
        )

        lines.append(
            f"REQUIRED SKILLS: "
            f"{', '.join(entry['required_skills'])}"
        )

        lines.append(
            f"MATCHED: "
            f"{', '.join(entry['matched_skills'])}"
        )

        lines.append(
            f"MISSING: "
            f"{', '.join(entry['missing_skills'])}"
        )

        lines.append(
            f"REASON: "
            f"{entry['decision_reason']}"
        )

        lines.append(
            f"URL: "
            f"{entry['url']}"
        )

        lines.append(
            "-" * 95
        )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 95
    )

    print(
        "                         APPLICATION RANKER"
    )

    print(
        "=" * 95
    )

    print()

    print(
        f"Your experience: "
        f"{CURRENT_EXPERIENCE:.2f} years"
    )

    print()

    jobs = load_json()

    print(
        f"Resume matches loaded: "
        f"{len(jobs)}"
    )

    if not jobs:

        print()

        print(
            "No resume matches found."
        )

        print(
            f"Make sure {INPUT_FILE} exists."
        )

        return

    entries = []

    for item in jobs:

        try:

            entry = build_entry(
                item
            )

            entries.append(
                entry
            )

        except Exception as error:

            print(
                "Skipping job because of error:"
            )

            print(error)

    entries, duplicates = (
        deduplicate(
            entries
        )
    )

    print()

    print(
        f"Duplicates removed: "
        f"{duplicates}"
    )

    # --------------------------------------------------------
    # Sort by priority.
    # --------------------------------------------------------

    entries.sort(
        key=lambda x:
            x["priority"],
        reverse=True
    )

    # --------------------------------------------------------
    # Save JSON.
    # --------------------------------------------------------

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            entries,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Save report.
    # --------------------------------------------------------

    report = generate_report(
        entries
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
    # Final summary.
    # --------------------------------------------------------

    print()

    print(
        "=" * 95
    )

    print(
        "                    APPLICATION QUEUE READY"
    )

    print(
        "=" * 95
    )

    print()

    categories = [

        "APPLY NOW",
        "APPLY",
        "STRONG APPLY",
        "REVIEW",
        "VERIFY FIRST",
        "STRETCH",
        "LOW PRIORITY",
        "REJECT",
    ]

    emoji = {

        "APPLY NOW":
            "🔥",

        "APPLY":
            "🚀",

        "STRONG APPLY":
            "🟢",

        "REVIEW":
            "🟡",

        "VERIFY FIRST":
            "🔍",

        "STRETCH":
            "🟠",

        "LOW PRIORITY":
            "🔴",

        "REJECT":
            "❌",
    }

    for category in categories:

        count = sum(
            1
            for entry in entries
            if entry[
                "category"
            ]
            == category
        )

        print(
            f"{emoji[category]} "
            f"{category}: "
            f"{count}"
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
        "=" * 95
    )

    print(
        "                         TOP APPLICATIONS"
    )

    print(
        "=" * 95
    )

    top = [
        entry
        for entry in entries
        if entry[
            "category"
        ]
        in [
            "APPLY NOW",
            "APPLY",
            "STRONG APPLY",
        ]
    ]

    for rank, entry in enumerate(
        top[:15],
        1
    ):

        print()

        print(
            f"#{rank} "
            f"[Priority "
            f"{entry['priority']}] "
            f"{entry['category']}"
        )

        print(
            f"TITLE: "
            f"{entry['title']}"
        )

        print(
            f"COMPANY: "
            f"{entry['company']}"
        )

        print(
            f"LOCATION: "
            f"{entry['location']}"
        )

        print(
            f"MATCH SCORE: "
            f"{entry['match_score']}/100"
        )

        print(
            f"EXPERIENCE: "
            f"{entry['experience_required']} "
            f"required vs "
            f"{CURRENT_EXPERIENCE:.2f}"
        )

        print(
            f"EXPERIENCE STATUS: "
            f"{entry['experience_status']}"
        )

        print(
            f"REASON: "
            f"{entry['decision_reason']}"
        )

        print(
            f"URL: "
            f"{entry['url']}"
        )

        print(
            "-" * 95
        )

    print()

    print(
        "Done."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()