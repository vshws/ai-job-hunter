import json
import os
import re
import time
import html
import urllib.request
import urllib.parse
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "job_analysis.json"

OUTPUT_JSON = "verified_jobs.json"
OUTPUT_TEXT = "job_verification.txt"

REQUEST_TIMEOUT = 20

DELAY_BETWEEN_REQUESTS = 0.5

MAX_JOBS = 200


# ============================================================
# USER PROFILE SKILLS
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


# ============================================================
# SKILL ALIASES
# ============================================================

SKILL_ALIASES = {

    "python": [
        "python",
    ],

    "pyspark": [
        "pyspark",
        "py spark",
    ],

    "spark": [
        "apache spark",
        "spark framework",
        "spark",
    ],

    "sql": [
        "sql",
    ],

    "databricks": [
        "databricks",
        "azure databricks",
    ],

    "delta lake": [
        "delta lake",
        "delta tables",
        "delta lakehouse",
    ],

    "delta lakehouse": [
        "delta lakehouse",
        "lakehouse",
    ],

    "aws": [
        "amazon web services",
        "aws",
    ],

    "aws glue": [
        "aws glue",
        "amazon glue",
    ],

    "s3": [
        "amazon s3",
        "aws s3",
        "s3",
    ],

    "azure": [
        "microsoft azure",
        "azure",
    ],

    "azure devops": [
        "azure devops",
    ],

    "etl": [
        "etl",
        "extract transform load",
    ],

    "elt": [
        "elt",
        "extract load transform",
    ],

    "mlflow": [
        "mlflow",
    ],

    "ci/cd": [
        "ci/cd",
        "ci cd",
        "continuous integration",
        "continuous delivery",
    ],

    "git": [
        "git",
        "github",
        "gitlab",
        "bitbucket",
    ],
}


# ============================================================
# JOB SKILLS TO DETECT
# ============================================================

DETECTABLE_SKILLS = {

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
    "git",

    # Common external requirements.
    "airflow",
    "dbt",
    "snowflake",
    "kafka",
    "scala",
    "java",
    "gcp",
    "bigquery",
    "redshift",
    "tableau",
    "power bi",
    "machine learning",
    "tensorflow",
    "pytorch",
    "terraform",
    "kubernetes",
    "docker",
    "oracle",
    "hadoop",
    "hive",
    "postgresql",
    "mysql",
    "mongodb",
}


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
]


JUNIOR_TERMS = [
    "junior",
    "jr.",
    "jr ",
    "associate",
    "entry level",
    "entry-level",
    "graduate",
    "fresher",
    "trainee",
]


# ============================================================
# LOAD JOBS
# ============================================================

def load_jobs():

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

            data = json.load(file)

    except Exception as error:

        print(
            "ERROR loading job_analysis.json:"
        )

        print(error)

        return []

    if isinstance(data, list):

        return data

    if isinstance(data, dict):

        for key in [
            "jobs",
            "results",
            "data",
            "analysis",
        ]:

            if isinstance(
                data.get(key),
                list
            ):

                return data[key]

    return []


# ============================================================
# JOB HELPERS
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


def get_title(item):

    job = get_job(
        item
    )

    return clean_text(
        job.get("title")
        or job.get("job_title")
        or ""
    )


def get_company(item):

    job = get_job(
        item
    )

    return clean_text(
        job.get("company")
        or job.get("employer")
        or job.get("organization")
        or "Unknown"
    )


def get_location(item):

    job = get_job(
        item
    )

    return clean_text(
        job.get("location")
        or job.get("locations")
        or job.get("cities")
        or ""
    )


def get_url(item):

    job = get_job(
        item
    )

    return clean_text(
        job.get("url")
        or job.get("job_url")
        or ""
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):

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

    value = str(
        value
    )

    value = html.unescape(
        value
    )

    value = re.sub(
        r"<script.*?</script>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL
    )

    value = re.sub(
        r"<style.*?</style>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL
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


# ============================================================
# HTTP FETCH
# ============================================================

def fetch_url(url):

    if not url:

        return {
            "success": False,
            "status": None,
            "html": "",
            "error": "No URL",
        }

    headers = {

        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36",

        "Accept":
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8",

        "Accept-Language":
            "en-US,en;q=0.9",
    }

    request = urllib.request.Request(
        url,
        headers=headers
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            raw = response.read()

            charset = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            try:

                page = raw.decode(
                    charset,
                    errors="ignore"
                )

            except Exception:

                page = raw.decode(
                    "utf-8",
                    errors="ignore"
                )

            return {
                "success": True,
                "status": response.status,
                "html": page,
                "error": None,
            }

    except Exception as error:

        return {
            "success": False,
            "status": None,
            "html": "",
            "error": str(error),
        }


# ============================================================
# EXTRACT TEXT FROM HTML
# ============================================================

def extract_page_text(
    page
):

    if not page:

        return ""

    # Remove scripts/styles first.
    page = re.sub(
        r"<script.*?</script>",
        " ",
        page,
        flags=re.IGNORECASE | re.DOTALL
    )

    page = re.sub(
        r"<style.*?</style>",
        " ",
        page,
        flags=re.IGNORECASE | re.DOTALL
    )

    page = re.sub(
        r"<noscript.*?</noscript>",
        " ",
        page,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Preserve JSON-LD separately by decoding it later.
    text = re.sub(
        r"<[^>]+>",
        " ",
        page
    )

    text = html.unescape(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# JSON-LD EXTRACTION
# ============================================================

def extract_json_ld(
    page
):

    results = []

    patterns = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>'
        r"(.*?)"
        r"</script>",
        page,
        flags=re.IGNORECASE | re.DOTALL
    )

    for raw in patterns:

        raw = raw.strip()

        try:

            data = json.loads(
                raw
            )

            if isinstance(
                data,
                list
            ):

                results.extend(
                    data
                )

            else:

                results.append(
                    data
                )

        except Exception:

            continue

    return results


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience(
    text
):

    text = normalize(
        text
    )

    candidates = []

    # --------------------------------------------------------
    # Explicit experience phrases
    # --------------------------------------------------------

    patterns = [

        r"(\d+(?:\.\d+)?)\s*\+?\s*years?"
        r"\s+(?:of\s+)?experience",

        r"experience\s*(?:of|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",

        r"minimum\s+(?:of\s+)?"
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",

        r"at\s+least\s+"
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?",

        r"(\d+(?:\.\d+)?)\s*[-–]\s*"
        r"(\d+(?:\.\d+)?)\s*years?"
        r"\s+(?:of\s+)?experience",

        r"(\d+(?:\.\d+)?)\s*\+?\s*"
        r"years?\s+in\s+"
        r"(?:data|software|engineering)",
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for match in matches:

            if isinstance(
                match,
                tuple
            ):

                values = match

            else:

                values = [
                    match
                ]

            for value in values:

                try:

                    number = float(
                        value
                    )

                    if (
                        0
                        <= number
                        <= 15
                    ):

                        candidates.append(
                            number
                        )

                except Exception:

                    pass

    # --------------------------------------------------------
    # Experience ranges.
    # --------------------------------------------------------

    range_matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*[-–]\s*"
        r"(\d+(?:\.\d+)?)\s*years?",
        text,
        flags=re.IGNORECASE
    )

    for low, high in range_matches:

        try:

            low = float(
                low
            )

            high = float(
                high
            )

            if (
                0 <= low <= 15
                and 0 <= high <= 15
            ):

                candidates.append(
                    low
                )

        except Exception:

            pass

    # --------------------------------------------------------
    # Avoid accidental numbers.
    # --------------------------------------------------------

    if not candidates:

        return None

    # We use the LOWEST explicit requirement.
    # This prevents "5 years preferred" from being
    # interpreted as a mandatory 5-year requirement
    # when the posting also says 2 years minimum.
    return min(
        candidates
    )


# ============================================================
# SKILL DETECTION
# ============================================================

def skill_present(
    text,
    skill
):

    aliases = SKILL_ALIASES.get(
        skill,
        [skill]
    )

    for alias in aliases:

        alias = normalize(
            alias
        )

        if not alias:

            continue

        # Word-boundary matching where possible.
        pattern = (
            r"(?<![a-z0-9])"
            +
            re.escape(
                alias
            )
            +
            r"(?![a-z0-9])"
        )

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            return True

    return False


def detect_skills(
    text
):

    found = []

    for skill in DETECTABLE_SKILLS:

        if skill_present(
            text,
            skill
        ):

            found.append(
                skill
            )

    return sorted(
        found
    )


# ============================================================
# REQUIRED VS PREFERRED SKILLS
# ============================================================

def classify_skills(
    text,
    detected
):

    text_lower = normalize(
        text
    )

    required = []
    preferred = []

    # --------------------------------------------------------
    # Look at sentences/sections containing requirement words.
    # --------------------------------------------------------

    requirement_patterns = [
        "required",
        "requirements",
        "must have",
        "must-have",
        "minimum qualifications",
        "basic qualifications",
        "qualifications",
        "you have",
        "what you bring",
        "essential",
        "mandatory",
    ]

    preferred_patterns = [
        "preferred",
        "nice to have",
        "nice-to-have",
        "good to have",
        "bonus",
        "plus",
        "desirable",
    ]

    # --------------------------------------------------------
    # Extract approximate local context around each skill.
    # --------------------------------------------------------

    for skill in detected:

        aliases = SKILL_ALIASES.get(
            skill,
            [skill]
        )

        found_context = ""

        for alias in aliases:

            match = re.search(
                re.escape(
                    alias
                ),
                text_lower,
                flags=re.IGNORECASE
            )

            if match:

                start = max(
                    0,
                    match.start() - 500
                )

                end = min(
                    len(text_lower),
                    match.end() + 500
                )

                found_context = (
                    text_lower[
                        start:end
                    ]
                )

                break

        if not found_context:

            continue

        is_preferred = any(
            phrase in found_context
            for phrase
            in preferred_patterns
        )

        is_required = any(
            phrase in found_context
            for phrase
            in requirement_patterns
        )

        if is_preferred and not is_required:

            preferred.append(
                skill
            )

        elif is_required:

            required.append(
                skill
            )

    # --------------------------------------------------------
    # If classification is weak, use conservative fallback.
    #
    # We do NOT claim every mentioned skill is required.
    # --------------------------------------------------------

    if not required and not preferred:

        # Core job skills mentioned in the posting are treated
        # as "mentioned", not automatically required.
        return {
            "required": [],
            "preferred": [],
            "mentioned": detected,
            "status": "PARTIAL",
        }

    # Skills detected but not classified.
    classified = set(
        required
        + preferred
    )

    mentioned = [
        skill
        for skill in detected
        if skill not in classified
    ]

    return {
        "required":
            sorted(
                set(required)
            ),

        "preferred":
            sorted(
                set(preferred)
            ),

        "mentioned":
            sorted(
                set(mentioned)
            ),

        "status":
            "VERIFIED",
    }


# ============================================================
# SENIORITY
# ============================================================

def detect_seniority(
    title,
    text
):

    title_lower = normalize(
        title
    )

    text_lower = normalize(
        text
    )

    title_senior = []

    title_junior = []

    for term in SENIOR_TERMS:

        if term in title_lower:

            title_senior.append(
                term
            )

    for term in JUNIOR_TERMS:

        if term in title_lower:

            title_junior.append(
                term
            )

    if title_senior:

        return {
            "status": "SENIOR",
            "terms": title_senior,
        }

    if title_junior:

        return {
            "status": "JUNIOR",
            "terms": title_junior,
        }

    # Don't infer seniority from random description mentions.
    return {
        "status": "UNKNOWN",
        "terms": [],
    }


# ============================================================
# JOB QUALITY
# ============================================================

def calculate_quality(
    page_success,
    experience,
    skills,
    seniority
):

    score = 0

    if page_success:

        score += 25

    if experience is not None:

        score += 30

    if skills[
        "required"
    ]:

        score += 25

    elif skills[
        "mentioned"
    ]:

        score += 10

    if seniority[
        "status"
    ] != "UNKNOWN":

        score += 20

    return score


# ============================================================
# VERIFY ONE JOB
# ============================================================

def verify_job(
    item,
    index,
    total
):

    job = get_job(
        item
    )

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

    print(
        f"[{index}/{total}] "
        f"{company} - {title}"
    )

    print(
        f"  URL: {url}"
    )

    fetched = fetch_url(
        url
    )

    if not fetched[
        "success"
    ]:

        print(
            "  FAILED:"
            f" {fetched['error']}"
        )

        return {

            "job":
                job,

            "verification": {

                "status":
                    "FAILED",

                "verified_at":
                    datetime.now().isoformat(),

                "source_url":
                    url,

                "http_status":
                    fetched["status"],

                "error":
                    fetched["error"],

                "experience_years_min":
                    None,

                "required_skills":
                    [],

                "preferred_skills":
                    [],

                "mentioned_skills":
                    [],

                "seniority":
                    "UNKNOWN",

                "confidence":
                    "LOW",
            },
        }

    page = fetched[
        "html"
    ]

    page_text = extract_page_text(
        page
    )

    # Include JSON-LD content because many ATS systems
    # put job description data there.
    json_ld = extract_json_ld(
        page
    )

    json_ld_text = clean_text(
        json.dumps(
            json_ld,
            ensure_ascii=False
        )
    )

    combined_text = (
        page_text
        + " "
        + json_ld_text
    )

    combined_text = re.sub(
        r"\s+",
        " ",
        combined_text
    )

    experience = extract_experience(
        combined_text
    )

    detected_skills = detect_skills(
        combined_text
    )

    skill_data = classify_skills(
        combined_text,
        detected_skills
    )

    seniority = detect_seniority(
        title,
        combined_text
    )

    quality = calculate_quality(
        True,
        experience,
        skill_data,
        seniority
    )

    # --------------------------------------------------------
    # Verification status
    # --------------------------------------------------------

    if (
        experience is not None
        and skill_data["required"]
    ):

        status = "VERIFIED"

        confidence = "HIGH"

    elif (
        experience is not None
        or skill_data["mentioned"]
    ):

        status = "PARTIAL"

        confidence = "MEDIUM"

    else:

        status = "PARTIAL"

        confidence = "LOW"

    print(
        f"  Experience: "
        f"{experience}"
    )

    print(
        f"  Required skills: "
        f"{len(skill_data['required'])}"
    )

    print(
        f"  Preferred skills: "
        f"{len(skill_data['preferred'])}"
    )

    print(
        f"  Mentioned skills: "
        f"{len(skill_data['mentioned'])}"
    )

    print(
        f"  Seniority: "
        f"{seniority['status']}"
    )

    print(
        f"  Status: "
        f"{status}"
    )

    print()

    return {

        "job":
            job,

        "verification": {

            "status":
                status,

            "verified_at":
                datetime.now().isoformat(),

            "source_url":
                url,

            "http_status":
                fetched["status"],

            "experience_years_min":
                experience,

            "required_skills":
                skill_data[
                    "required"
                ],

            "preferred_skills":
                skill_data[
                    "preferred"
                ],

            "mentioned_skills":
                skill_data[
                    "mentioned"
                ],

            "all_detected_skills":
                detected_skills,

            "seniority":
                seniority[
                    "status"
                ],

            "seniority_terms":
                seniority[
                    "terms"
                ],

            "confidence":
                confidence,

            "quality_score":
                quality,

            "page_text_length":
                len(page_text),

            "error":
                None,
        },
    }


# ============================================================
# DEDUPLICATION
# ============================================================

def duplicate_key(
    item
):

    url = normalize(
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
        + normalize(
            get_company(item)
        )
        + "|"
        + normalize(
            get_title(item)
        )
        + "|"
        + normalize(
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
        "                         JOB VERIFIER"
    )

    lines.append(
        "=" * 95
    )

    lines.append("")

    counts = {
        "VERIFIED": 0,
        "PARTIAL": 0,
        "FAILED": 0,
    }

    for item in results:

        status = item[
            "verification"
        ][
            "status"
        ]

        if status in counts:

            counts[
                status
            ] += 1

    lines.append(
        f"Jobs processed: "
        f"{len(results)}"
    )

    lines.append(
        f"VERIFIED: "
        f"{counts['VERIFIED']}"
    )

    lines.append(
        f"PARTIAL: "
        f"{counts['PARTIAL']}"
    )

    lines.append(
        f"FAILED: "
        f"{counts['FAILED']}"
    )

    lines.append("")

    lines.append(
        "=" * 95
    )

    lines.append(
        "                         VERIFICATION RESULTS"
    )

    lines.append(
        "=" * 95
    )

    for rank, item in enumerate(
        results,
        1
    ):

        verification = item[
            "verification"
        ]

        lines.append("")

        lines.append(
            f"#{rank} "
            f"{verification['status']}"
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
            f"EXPERIENCE MIN: "
            f"{verification['experience_years_min']}"
        )

        lines.append(
            f"REQUIRED SKILLS: "
            f"{', '.join(verification['required_skills'])}"
        )

        lines.append(
            f"PREFERRED SKILLS: "
            f"{', '.join(verification['preferred_skills'])}"
        )

        lines.append(
            f"MENTIONED SKILLS: "
            f"{', '.join(verification['mentioned_skills'])}"
        )

        lines.append(
            f"SENIORITY: "
            f"{verification['seniority']}"
        )

        lines.append(
            f"CONFIDENCE: "
            f"{verification['confidence']}"
        )

        lines.append(
            f"QUALITY SCORE: "
            f"{verification.get('quality_score', 0)}"
        )

        lines.append(
            f"URL: "
            f"{verification['source_url']}"
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
        "                         JOB VERIFIER"
    )

    print(
        "=" * 95
    )

    print()

    jobs = load_jobs()

    print(
        f"Jobs loaded: "
        f"{len(jobs)}"
    )

    if not jobs:

        print(
            "No jobs to verify."
        )

        return

    jobs, duplicates = (
        deduplicate_jobs(
            jobs
        )
    )

    print(
        f"Duplicates removed: "
        f"{duplicates}"
    )

    if len(jobs) > MAX_JOBS:

        print(
            f"Limiting verification to "
            f"{MAX_JOBS} jobs."
        )

        jobs = jobs[
            :MAX_JOBS
        ]

    print(
        f"Jobs to verify: "
        f"{len(jobs)}"
    )

    print()

    results = []

    total = len(
        jobs
    )

    for index, item in enumerate(
        jobs,
        1
    ):

        try:

            result = verify_job(
                item,
                index,
                total
            )

            results.append(
                result
            )

        except KeyboardInterrupt:

            print()

            print(
                "Verification stopped by user."
            )

            break

        except Exception as error:

            print(
                "  ERROR:"
                f" {error}"
            )

            results.append(
                {
                    "job":
                        get_job(item),

                    "verification": {

                        "status":
                            "FAILED",

                        "verified_at":
                            datetime.now().isoformat(),

                        "source_url":
                            get_url(item),

                        "http_status":
                            None,

                        "experience_years_min":
                            None,

                        "required_skills":
                            [],

                        "preferred_skills":
                            [],

                        "mentioned_skills":
                            [],

                        "seniority":
                            "UNKNOWN",

                        "confidence":
                            "LOW",

                        "quality_score":
                            0,

                        "error":
                            str(error),
                    },
                }
            )

        time.sleep(
            DELAY_BETWEEN_REQUESTS
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

    verified = 0
    partial = 0
    failed = 0

    for item in results:

        status = item[
            "verification"
        ][
            "status"
        ]

        if status == "VERIFIED":

            verified += 1

        elif status == "PARTIAL":

            partial += 1

        elif status == "FAILED":

            failed += 1

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print()

    print(
        "=" * 95
    )

    print(
        "                    VERIFICATION COMPLETE"
    )

    print(
        "=" * 95
    )

    print()

    print(
        f"Jobs processed: "
        f"{len(results)}"
    )

    print(
        f"VERIFIED: "
        f"{verified}"
    )

    print(
        f"PARTIAL: "
        f"{partial}"
    )

    print(
        f"FAILED: "
        f"{failed}"
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

    print("Done.")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()