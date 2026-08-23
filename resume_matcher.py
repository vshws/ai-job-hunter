import json
import os
import re
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "verified_jobs.json"
OUTPUT_JSON = "resume_matches.json"
OUTPUT_TEXT = "resume_matches.txt"

JOINING_DATE = "2025-08-08"


# ============================================================
# YOUR ACTUAL PROFILE
# ============================================================

PROFILE_SKILLS = {
    "python",
    "pyspark",
    "spark",
    "sql",

    "databricks",
    "delta lake",
    "delta lakehouse",

    "aws",
    "aws glue",
    "s3",

    "azure",
    "azure devops",

    "etl",
    "elt",

    "mlflow",

    "ci/cd",
    "ci cd",

    "git",
}


# Skills that are particularly important for your target roles.
CORE_SKILLS = {
    "python",
    "pyspark",
    "spark",
    "sql",
    "databricks",
    "delta lake",
    "aws",
    "aws glue",
    "azure",
    "etl",
}


PREFERRED_LOCATIONS = [
    "bangalore",
    "bengaluru",
    "pune",
    "hyderabad",
    "chennai",
    "mumbai",
    "delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "lucknow",
    "kochi",
    "india",
    "remote",
]


SENIOR_WORDS = [
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


JUNIOR_WORDS = [
    "junior",
    "associate",
    "entry",
    "graduate",
    "fresher",
    "trainee",
]


# ============================================================
# EXPERIENCE
# ============================================================

def calculate_current_experience():

    start_date = datetime.strptime(
        JOINING_DATE,
        "%Y-%m-%d"
    )

    today = datetime.now()

    days = (
        today - start_date
    ).days

    return round(
        days / 365.25,
        2
    )


CURRENT_EXPERIENCE = calculate_current_experience()


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    if isinstance(value, list):

        return " ".join(
            normalize_text(x)
            for x in value
        )

    if isinstance(value, dict):

        return " ".join(
            normalize_text(v)
            for v in value.values()
        )

    value = str(value)

    value = (
        value
        .replace("&nbsp;", " ")
        .replace("&#x20;", " ")
        .replace("&amp;", "&")
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def lower(value):

    return normalize_text(
        value
    ).lower()


# ============================================================
# FILE LOADING
# ============================================================

def load_jobs():

    if not os.path.exists(
        INPUT_FILE
    ):

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

            data = json.load(file)

    except Exception as error:

        print(
            "ERROR loading verified_jobs.json:"
        )

        print(error)

        return []

    if isinstance(
        data,
        list
    ):

        return data

    # Support files where jobs are stored
    # inside a data/jobs/results key.
    if isinstance(
        data,
        dict
    ):

        for key in [
            "jobs",
            "data",
            "results",
            "verified_jobs",
        ]:

            value = data.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                return value

    return []


# ============================================================
# JOB STRUCTURE
# ============================================================

def get_job(item):

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


def get_verification(item):

    if not isinstance(
        item,
        dict
    ):

        return {}

    verification = item.get(
        "verification"
    )

    if isinstance(
        verification,
        dict
    ):

        return verification

    return {}


def get_title(item):

    job = get_job(item)

    return normalize_text(
        job.get("title")
        or job.get("job_title")
        or ""
    )


def get_company(item):

    job = get_job(item)

    return normalize_text(
        job.get("company")
        or job.get("employer")
        or job.get("organization")
        or "Unknown"
    )


def get_location(item):

    job = get_job(item)

    value = (
        job.get("location")
        or job.get("locations")
        or job.get("cities")
        or ""
    )

    return normalize_text(
        value
    )


def get_url(item):

    job = get_job(item)

    verification = get_verification(
        item
    )

    return normalize_text(
        job.get("url")
        or job.get("job_url")
        or verification.get(
            "original_url"
        )
        or ""
    )


def get_description(item):

    job = get_job(item)

    fields = [
        "description",
        "job_description",
        "details",
        "content",
        "requirements",
        "responsibilities",
        "experience",
        "skills",
    ]

    parts = []

    for field in fields:

        value = job.get(
            field
        )

        if value:

            parts.append(
                normalize_text(
                    value
                )
            )

    return " ".join(
        parts
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

    patterns = [

        r"(?:minimum|min\.?|at least|required)"
        r"\s*(?:of\s+)?"
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",

        r"(\d+(?:\.\d+)?)\s*\+?\s*years?"
        r"\s+(?:of\s+)?experience",

        r"experience\s*(?:of|required)?\s*"
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",

        r"(\d+(?:\.\d+)?)\s*[-–]\s*"
        r"(\d+(?:\.\d+)?)\s*years?",
    ]

    values = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            if isinstance(
                match,
                tuple
            ):

                for value in match:

                    try:

                        number = float(
                            value
                        )

                        if 0 <= number <= 15:

                            values.append(
                                number
                            )

                    except Exception:
                        pass

            else:

                try:

                    number = float(
                        match
                    )

                    if 0 <= number <= 15:

                        values.append(
                            number
                        )

                except Exception:
                    pass

    if not values:

        return None

    return min(
        values
    )


def get_required_experience(
    item
):

    verification = get_verification(
        item
    )

    # First use verifier output.
    for key in [
        "detected_experience",
        "experience_years_min",
        "experience_min",
        "minimum_experience",
        "min_experience",
    ]:

        value = verification.get(
            key
        )

        if value is not None:

            try:

                return float(
                    value
                )

            except Exception:
                pass

    # Then check job object.
    job = get_job(item)

    for key in [
        "experience_years_min",
        "experience_min",
        "minimum_experience",
        "min_experience",
    ]:

        value = job.get(
            key
        )

        if value is not None:

            try:

                return float(
                    value
                )

            except Exception:
                pass

    # Finally parse description.
    return extract_experience_from_text(
        get_description(item)
    )


def experience_match(
    required
):

    if required is None:

        return {
            "required": None,
            "status": "UNKNOWN",
            "score": 65,
        }

    required = float(
        required
    )

    if required <= CURRENT_EXPERIENCE:

        return {
            "required": required,
            "status": "MEETS",
            "score": 100,
        }

    difference = (
        required
        - CURRENT_EXPERIENCE
    )

    if difference <= 0.75:

        return {
            "required": required,
            "status": "CLOSE",
            "score": 85,
        }

    if difference <= 1.5:

        return {
            "required": required,
            "status": "STRETCH",
            "score": 55,
        }

    return {
        "required": required,
        "status": "TOO_SENIOR",
        "score": 15,
    }


# ============================================================
# SKILL DATA
# ============================================================

def clean_skill_list(
    value
):

    if not isinstance(
        value,
        list
    ):

        return []

    result = []

    for skill in value:

        skill = lower(
            skill
        )

        if skill and skill not in result:

            result.append(
                skill
            )

    return result


def get_required_skills(
    item
):

    verification = get_verification(
        item
    )

    return clean_skill_list(
        verification.get(
            "required_skills"
        )
    )


def get_preferred_skills(
    item
):

    verification = get_verification(
        item
    )

    return clean_skill_list(
        verification.get(
            "preferred_skills"
        )
    )


def get_mentioned_skills(
    item
):

    verification = get_verification(
        item
    )

    return clean_skill_list(
        verification.get(
            "mentioned_skills"
        )
    )


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_match(item):

    required = get_required_skills(
        item
    )

    preferred = get_preferred_skills(
        item
    )

    mentioned = get_mentioned_skills(
        item
    )

    # --------------------------------------------------------
    # No actual verifier skill data
    # --------------------------------------------------------

    if not required and not preferred:

        if mentioned:

            matched = [
                skill
                for skill in mentioned
                if skill in PROFILE_SKILLS
            ]

            percentage = round(
                (
                    len(matched)
                    / len(mentioned)
                ) * 100
            )

            return {
                "data_status": "KNOWN",
                "required": [],
                "preferred": [],
                "matched_required": matched,
                "missing_required": [],
                "matched_preferred": [],
                "missing_preferred": [],
                "percentage": percentage,
                "combined_percentage": percentage,
            }

        return {
            "data_status": "UNKNOWN",
            "required": [],
            "preferred": [],
            "matched_required": [],
            "missing_required": [],
            "matched_preferred": [],
            "missing_preferred": [],
            "percentage": None,
            "combined_percentage": None,
        }

    # --------------------------------------------------------
    # Required skills
    # --------------------------------------------------------

    matched_required = [
        skill
        for skill in required
        if skill in PROFILE_SKILLS
    ]

    missing_required = [
        skill
        for skill in required
        if skill not in PROFILE_SKILLS
    ]

    # --------------------------------------------------------
    # Preferred skills
    # --------------------------------------------------------

    matched_preferred = [
        skill
        for skill in preferred
        if skill in PROFILE_SKILLS
    ]

    missing_preferred = [
        skill
        for skill in preferred
        if skill not in PROFILE_SKILLS
    ]

    # --------------------------------------------------------
    # Percentages
    # --------------------------------------------------------

    if required:

        required_percentage = round(
            (
                len(matched_required)
                / len(required)
            ) * 100
        )

    else:

        required_percentage = None

    if preferred:

        preferred_percentage = round(
            (
                len(matched_preferred)
                / len(preferred)
            ) * 100
        )

    else:

        preferred_percentage = None

    if (
        required_percentage is not None
        and preferred_percentage is not None
    ):

        combined_percentage = round(
            (
                required_percentage * 0.80
                +
                preferred_percentage * 0.20
            )
        )

    elif required_percentage is not None:

        combined_percentage = (
            required_percentage
        )

    elif preferred_percentage is not None:

        combined_percentage = (
            preferred_percentage
        )

    else:

        combined_percentage = None

    return {
        "data_status": "KNOWN",
        "required": required,
        "preferred": preferred,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "percentage": required_percentage,
        "combined_percentage": combined_percentage,
    }


# ============================================================
# CORE SKILL ANALYSIS
# ============================================================

def core_skill_analysis(
    skills
):

    if skills[
        "data_status"
    ] == "UNKNOWN":

        return {
            "data_status": "UNKNOWN",
            "percentage": None,
        }

    required = skills[
        "required"
    ]

    if not required:

        return {
            "data_status": "KNOWN",
            "percentage":
                skills[
                    "combined_percentage"
                ],
        }

    core_required = [
        skill
        for skill in required
        if skill in CORE_SKILLS
    ]

    if not core_required:

        return {
            "data_status": "KNOWN",
            "percentage": 100,
        }

    matched = [
        skill
        for skill in core_required
        if skill in PROFILE_SKILLS
    ]

    percentage = round(
        (
            len(matched)
            / len(core_required)
        ) * 100
    )

    return {
        "data_status": "KNOWN",
        "percentage": percentage,
    }


# ============================================================
# TITLE
# ============================================================

def title_analysis(
    item
):

    title = lower(
        get_title(item)
    )

    relevant_words = [
        "data engineer",
        "data engineering",
        "data platform",
        "analytics engineer",
        "etl",
        "pyspark",
        "databricks",
        "data developer",
    ]

    if any(
        word in title
        for word in relevant_words
    ):

        return {
            "score": 100,
            "relevant": True,
            "reason":
                "Relevant Data Engineering title",
        }

    if (
        "software engineer"
        in title
        and "data"
        in title
    ):

        return {
            "score": 90,
            "relevant": True,
            "reason":
                "Software/Data Engineering title",
        }

    return {
        "score": 40,
        "relevant": False,
        "reason":
            "Weak Data Engineering relevance",
    }


# ============================================================
# SENIORITY
# ============================================================

def seniority_analysis(
    item
):

    title = lower(
        get_title(item)
    )

    senior = any(
        word in title
        for word in SENIOR_WORDS
    )

    junior = any(
        word in title
        for word in JUNIOR_WORDS
    )

    return {
        "senior": senior,
        "junior": junior,
    }


# ============================================================
# LOCATION
# ============================================================

def location_analysis(
    item
):

    location = lower(
        get_location(item)
    )

    if not location:

        return {
            "score": 50,
            "match": False,
            "matched_location": None,
        }

    for preferred in PREFERRED_LOCATIONS:

        if preferred in location:

            return {
                "score": 100,
                "match": True,
                "matched_location":
                    preferred,
            }

    return {
        "score": 35,
        "match": False,
        "matched_location": None,
    }


# ============================================================
# CRITICAL MISSING SKILLS
# ============================================================

def get_critical_missing(
    skills
):

    critical = {
        "python",
        "pyspark",
        "spark",
        "sql",
        "databricks",
        "delta lake",
        "aws",
        "azure",
        "etl",
    }

    return [
        skill
        for skill in skills[
            "missing_required"
        ]
        if skill in critical
    ]


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(
    skills,
    experience,
    core
):

    skill_count = (
        len(
            skills[
                "required"
            ]
        )
        +
        len(
            skills[
                "preferred"
            ]
        )
    )

    experience_known = (
        experience[
            "status"
        ] != "UNKNOWN"
    )

    skills_known = (
        skills[
            "data_status"
        ] == "KNOWN"
    )

    core_known = (
        core[
            "data_status"
        ] == "KNOWN"
    )

    if (
        skills_known
        and experience_known
        and core_known
        and skill_count >= 4
    ):

        return "HIGH"

    if (
        skills_known
        and skill_count >= 2
        and (
            experience_known
            or core_known
        )
    ):

        return "MEDIUM"

    return "LOW"


# ============================================================
# SCORE
# ============================================================

def calculate_score(
    skills,
    experience,
    core,
    location,
    title,
    seniority,
    critical_missing,
    confidence
):

    components = []

    # Skills = 45%
    if (
        skills[
            "combined_percentage"
        ]
        is not None
    ):

        components.append(
            (
                skills[
                    "combined_percentage"
                ],
                0.45
            )
        )

    # Experience = 20%
    components.append(
        (
            experience[
                "score"
            ],
            0.20
        )
    )

    # Core skills = 15%
    if (
        core[
            "percentage"
        ]
        is not None
    ):

        components.append(
            (
                core[
                    "percentage"
                ],
                0.15
            )
        )

    # Location = 5%
    components.append(
        (
            location[
                "score"
            ],
            0.05
        )
    )

    # Title = 10%
    components.append(
        (
            title[
                "score"
            ],
            0.10
        )
    )

    # Seniority = 5%
    if seniority[
        "senior"
    ]:

        seniority_score = 20

    else:

        seniority_score = 100

    components.append(
        (
            seniority_score,
            0.05
        )
    )

    if components:

        total_weight = sum(
            weight
            for _, weight
            in components
        )

        score = (
            sum(
                value * weight
                for value, weight
                in components
            )
            / total_weight
        )

    else:

        score = 0

    # --------------------------------------------------------
    # Penalize missing critical skills.
    # --------------------------------------------------------

    score -= (
        len(
            critical_missing
        )
        * 7
    )

    # --------------------------------------------------------
    # Confidence caps.
    # --------------------------------------------------------

    if confidence == "LOW":

        score = min(
            score,
            70
        )

    elif confidence == "MEDIUM":

        score = min(
            score,
            85
        )

    # --------------------------------------------------------
    # UNKNOWN experience can NEVER be 100.
    # --------------------------------------------------------

    if experience[
        "status"
    ] == "UNKNOWN":

        score = min(
            score,
            82
        )

    # --------------------------------------------------------
    # Unknown skill data should not look excellent.
    # --------------------------------------------------------

    if skills[
        "data_status"
    ] == "UNKNOWN":

        score = min(
            score,
            65
        )

    return round(
        max(
            0,
            min(
                100,
                score
            )
        )
    )


# ============================================================
# DECISION
# ============================================================

def make_decision(
    score,
    confidence,
    experience,
    seniority,
    critical_missing
):

    # --------------------------------------------------------
    # Hard rejection
    # --------------------------------------------------------

    if experience[
        "status"
    ] == "TOO_SENIOR":

        return "❌ REJECT"

    if seniority[
        "senior"
    ]:

        return "❌ REJECT"

    if len(
        critical_missing
    ) >= 3:

        return "❌ REJECT"

    # --------------------------------------------------------
    # UNKNOWN EXPERIENCE
    # --------------------------------------------------------
    #
    # UNKNOWN can NEVER become APPLY.
    #

    if experience[
        "status"
    ] == "UNKNOWN":

        if score >= 70:

            return "🟡 REVIEW"

        if score >= 55:

            return "🟠 STRETCH"

        return "🔴 LOW PRIORITY"

    # --------------------------------------------------------
    # Experience meets requirement
    # --------------------------------------------------------

    if experience[
        "status"
    ] == "MEETS":

        if (
            score >= 85
            and len(
                critical_missing
            ) == 0
        ):

            return "🔥 APPLY"

        if score >= 75:

            return "🟢 STRONG APPLY"

        if score >= 60:

            return "🟡 REVIEW"

        return "🟠 STRETCH"

    # --------------------------------------------------------
    # Slight experience gap
    # --------------------------------------------------------

    if experience[
        "status"
    ] == "CLOSE":

        if (
            score >= 88
            and len(
                critical_missing
            ) == 0
        ):

            return "🔥 APPLY"

        if score >= 75:

            return "🟢 STRONG APPLY"

        if score >= 60:

            return "🟡 REVIEW"

        return "🟠 STRETCH"

    # --------------------------------------------------------
    # Moderate experience gap
    # --------------------------------------------------------

    if experience[
        "status"
    ] == "STRETCH":

        if score >= 70:

            return "🟠 STRETCH"

        return "🔴 LOW PRIORITY"

    return "🟡 REVIEW"


# ============================================================
# FULL JOB ANALYSIS
# ============================================================

def analyze_job(
    item
):

    required_experience = (
        get_required_experience(
            item
        )
    )

    experience = (
        experience_match(
            required_experience
        )
    )

    skills = skill_match(
        item
    )

    core = core_skill_analysis(
        skills
    )

    title = title_analysis(
        item
    )

    seniority = seniority_analysis(
        item
    )

    location = location_analysis(
        item
    )

    critical_missing = (
        get_critical_missing(
            skills
        )
    )

    confidence = (
        calculate_confidence(
            skills,
            experience,
            core
        )
    )

    score = calculate_score(
        skills,
        experience,
        core,
        location,
        title,
        seniority,
        critical_missing,
        confidence
    )

    decision = make_decision(
        score,
        confidence,
        experience,
        seniority,
        critical_missing
    )

    return {

        "score": score,

        "decision": decision,

        "confidence": confidence,

        "experience": experience,

        "skills": skills,

        "core": core,

        "title": title,

        "seniority": seniority,

        "location": location,

        "critical_missing":
            critical_missing,
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def duplicate_key(
    item
):

    url = lower(
        get_url(item)
    )

    if url:

        url = url.split(
            "?",
            1
        )[0]

        return (
            "url|"
            + url
        )

    return (
        "job|"
        + lower(
            get_company(item)
        )
        + "|"
        + lower(
            get_title(item)
        )
        + "|"
        + lower(
            get_location(item)
        )
    )


def deduplicate_jobs(
    jobs
):

    seen = set()

    result = []

    duplicates = 0

    for item in jobs:

        key = duplicate_key(
            item
        )

        if key in seen:

            duplicates += 1

            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    return (
        result,
        duplicates
    )


# ============================================================
# REPORT
# ============================================================

def generate_report(
    results
):

    lines = []

    lines.append(
        "=" * 95
    )

    lines.append(
        "                         RESUME MATCHER"
    )

    lines.append(
        "=" * 95
    )

    lines.append("")

    lines.append(
        f"Joining date: {JOINING_DATE}"
    )

    lines.append(
        f"Current experience: "
        f"{CURRENT_EXPERIENCE} years"
    )

    lines.append("")

    counts = {

        "🔥 APPLY": 0,
        "🟢 STRONG APPLY": 0,
        "🟡 REVIEW": 0,
        "🟠 STRETCH": 0,
        "❌ REJECT": 0,
        "🔴 LOW PRIORITY": 0,
    }

    for item in results:

        decision = item[
            "match"
        ][
            "decision"
        ]

        if decision in counts:

            counts[
                decision
            ] += 1

    lines.append(
        f"Jobs analyzed: {len(results)}"
    )

    lines.append("")

    for decision, count in counts.items():

        lines.append(
            f"{decision}: {count}"
        )

    lines.append("")

    lines.append(
        "=" * 95
    )

    lines.append(
        "                           TOP MATCHES"
    )

    lines.append(
        "=" * 95
    )

    for rank, item in enumerate(
        results[:30],
        1
    ):

        match = item[
            "match"
        ]

        skills = match[
            "skills"
        ]

        experience = match[
            "experience"
        ]

        lines.append("")

        lines.append(
            f"#{rank} "
            f"[{match['score']}/100] "
            f"{match['decision']}"
        )

        lines.append(
            f"CONFIDENCE: "
            f"{match['confidence']}"
        )

        lines.append(
            f"TITLE: "
            f"{get_title(item)}"
        )

        lines.append(
            f"COMPANY: "
            f"{get_company(item)}"
        )

        lines.append(
            f"LOCATION: "
            f"{get_location(item)}"
        )

        lines.append(
            f"EXPERIENCE REQUIRED: "
            f"{experience['required']}"
        )

        lines.append(
            f"YOUR EXPERIENCE: "
            f"{CURRENT_EXPERIENCE}"
        )

        lines.append(
            f"EXPERIENCE STATUS: "
            f"{experience['status']}"
        )

        if (
            skills[
                "combined_percentage"
            ]
            is not None
        ):

            lines.append(
                f"REQUIRED SKILLS: "
                f"{skills['combined_percentage']}%"
            )

        else:

            lines.append(
                "SKILL DATA: UNKNOWN"
            )

        if skills[
            "matched_required"
        ]:

            lines.append(
                "MATCHED: "
                +
                ", ".join(
                    skills[
                        "matched_required"
                    ]
                )
            )

        if skills[
            "missing_required"
        ]:

            lines.append(
                "MISSING: "
                +
                ", ".join(
                    skills[
                        "missing_required"
                    ]
                )
            )

        lines.append(
            f"URL: "
            f"{get_url(item)}"
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
        "                         RESUME MATCHER"
    )

    print(
        "=" * 95
    )

    print()

    print(
        f"Joining date: {JOINING_DATE}"
    )

    print(
        f"Current experience: "
        f"{CURRENT_EXPERIENCE} years"
    )

    print()

    jobs = load_jobs()

    print(
        f"Verified jobs loaded: "
        f"{len(jobs)}"
    )

    print()

    # --------------------------------------------------------
    # Only use jobs marked VERIFIED or PARTIAL.
    # --------------------------------------------------------

    usable_jobs = []

    for item in jobs:

        verification = get_verification(
            item
        )

        status = lower(
            verification.get(
                "status"
            )
        )

        if status in [
            "verified",
            "partial",
        ]:

            usable_jobs.append(
                item
            )

    print(
        f"Usable jobs before deduplication: "
        f"{len(usable_jobs)}"
    )

    usable_jobs, duplicates = (
        deduplicate_jobs(
            usable_jobs
        )
    )

    print(
        f"Duplicates removed: "
        f"{duplicates}"
    )

    print(
        f"Usable unique jobs: "
        f"{len(usable_jobs)}"
    )

    print()

    print(
        "Matching jobs against your profile..."
    )

    print()

    results = []

    for item in usable_jobs:

        try:

            match = analyze_job(
                item
            )

            results.append(
                {
                    "job":
                        get_job(item),

                    "verification":
                        get_verification(
                            item
                        ),

                    "match":
                        match,
                }
            )

        except Exception as error:

            print(
                "WARNING: Could not analyze job:"
            )

            print(
                error
            )

    # --------------------------------------------------------
    # Sort by score
    # --------------------------------------------------------

    results.sort(
        key=lambda item:
            item[
                "match"
            ][
                "score"
            ],
        reverse=True
    )

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    report = generate_report(
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
    # Counts
    # --------------------------------------------------------

    counts = {

        "🔥 APPLY": 0,
        "🟢 STRONG APPLY": 0,
        "🟡 REVIEW": 0,
        "🟠 STRETCH": 0,
        "❌ REJECT": 0,
        "🔴 LOW PRIORITY": 0,
    }

    for item in results:

        decision = item[
            "match"
        ][
            "decision"
        ]

        if decision in counts:

            counts[
                decision
            ] += 1

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print(
        "=" * 95
    )

    print(
        "                    RESUME MATCHING COMPLETE"
    )

    print(
        "=" * 95
    )

    print()

    print(
        f"Jobs analyzed: "
        f"{len(results)}"
    )

    print()

    for decision, count in counts.items():

        print(
            f"{decision}: {count}"
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
        "                           TOP MATCHES"
    )

    print(
        "=" * 95
    )

    for rank, item in enumerate(
        results[:20],
        1
    ):

        match = item[
            "match"
        ]

        skills = match[
            "skills"
        ]

        experience = match[
            "experience"
        ]

        print()

        print(
            f"#{rank} "
            f"[{match['score']}/100] "
            f"{match['decision']}"
        )

        print(
            f"CONFIDENCE: "
            f"{match['confidence']}"
        )

        print(
            f"TITLE: "
            f"{get_title(item)}"
        )

        print(
            f"COMPANY: "
            f"{get_company(item)}"
        )

        print(
            f"LOCATION: "
            f"{get_location(item)}"
        )

        print(
            f"EXPERIENCE REQUIRED: "
            f"{experience['required']}"
        )

        print(
            f"YOUR EXPERIENCE: "
            f"{CURRENT_EXPERIENCE}"
        )

        print(
            f"EXPERIENCE STATUS: "
            f"{experience['status']}"
        )

        if (
            skills[
                "combined_percentage"
            ]
            is not None
        ):

            print(
                f"REQUIRED SKILLS: "
                f"{skills['combined_percentage']}%"
            )

        else:

            print(
                "SKILL DATA: UNKNOWN"
            )

        if skills[
            "matched_required"
        ]:

            print(
                "MATCHED: "
                +
                ", ".join(
                    skills[
                        "matched_required"
                    ]
                )
            )

        if skills[
            "missing_required"
        ]:

            print(
                "MISSING: "
                +
                ", ".join(
                    skills[
                        "missing_required"
                    ]
                )
            )

        print(
            f"URL: "
            f"{get_url(item)}"
        )

        print(
            "-" * 95
        )

    print()

    print("Done.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()