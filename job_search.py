import urllib.request
import urllib.parse
import json
import time
import re
from datetime import datetime, timezone


API = "https://freehire.me/api/v1/jobs/search"


USER_EXPERIENCE_YEARS = 1.0


TARGET_SKILLS = {
    "databricks": 14,
    "pyspark": 12,
    "delta lake": 10,
    "delta lakehouse": 10,
    "spark": 8,
    "python": 7,
    "sql": 7,
    "aws": 5,
    "azure": 5,
    "etl": 4,
    "data engineering": 5,
    "airflow": 3,
    "dbt": 3,
    "snowflake": 3,
}


SEARCH_QUERIES = [
    "Data Engineer",
    "Data Engineering",
    "Data Platform Engineer",
    "Databricks Data Engineer",
    "PySpark Data Engineer",
    "Spark Data Engineer",
    "AWS Data Engineer",
    "Azure Data Engineer",
    "Junior Data Engineer",
    "Associate Data Engineer",
    "Entry Level Data Engineer",
    "Graduate Data Engineer",
    "Fresher Data Engineer",
    "Trainee Data Engineer",
    "Junior Databricks Data Engineer",
    "Junior PySpark Data Engineer",
]


PREFERRED_LOCATIONS = [
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
]


INDIA_LOCATIONS = [
    "india",
    "pune",
    "maharashtra",
    "bangalore",
    "bengaluru",
    "karnataka",
    "hyderabad",
    "telangana",
    "chennai",
    "tamil nadu",
    "mumbai",
    "delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "uttar pradesh",
    "lucknow",
    "kerala",
    "kochi",
]


REMOTE_LOCATIONS = [
    "remote",
    "remote india",
    "india remote",
]


GOOD_TITLE_TERMS = [
    "data engineer",
    "data engineering",
    "databricks",
    "pyspark",
    "data platform engineer",
    "big data engineer",
    "software engineer",
]


BAD_TITLE_TERMS = [
    "data analyst",
    "business analyst",
    "data scientist",
    "machine learning",
    "ml engineer",
    "data steward",
    "data governance",
    "data quality",
    "business intelligence",
    "bi developer",
    "analytics manager",
    "project manager",
    "product manager",
    "data architect",
    "solution architect",
    "enterprise architect",
    "data engineering manager",
    "engineering manager",
    "director",
    "vice president",
    "vice-president",
    "assistant vice president",
    "avp",
    "head of",
]


SENIOR_TITLE_TERMS = [
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


JUNIOR_TITLE_TERMS = [
    "junior",
    "jr.",
    "jr ",
    "entry",
    "associate",
    "graduate",
    "fresher",
    "trainee",
    "new grad",
    "new graduate",
]


PAGE_SIZE = 100
MAX_OFFSET = 9000
POSTED_WITHIN_DAYS = 30


def fetch_jobs(query, offset=0):

    params = {
        "q": query,
        "category": "data_engineering",
        "countries": "IN",
        "posted_within_days": str(
            POSTED_WITHIN_DAYS
        ),
        "sort": "posted_at",
        "order": "desc",
        "limit": str(PAGE_SIZE),
        "offset": str(offset),
    }

    url = (
        API
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return json.load(response)


def fetch_all_jobs():

    all_jobs = []

    print()
    print("=" * 75)
    print("SEARCHING FOR JOBS")
    print("=" * 75)

    for query in SEARCH_QUERIES:

        print()
        print(
            f"SEARCH: {query}"
        )

        offset = 0

        while offset <= MAX_OFFSET:

            try:

                response = fetch_jobs(
                    query,
                    offset
                )

                jobs = response.get(
                    "data",
                    []
                )

                total = response.get(
                    "meta",
                    {}
                ).get(
                    "total",
                    0
                )

                print(
                    f"  Offset {offset}: "
                    f"{len(jobs)} jobs / "
                    f"{total} available"
                )

                if not jobs:
                    break

                for job in jobs:

                    job[
                        "_search_query"
                    ] = query

                    all_jobs.append(job)

                if len(jobs) < PAGE_SIZE:
                    break

                offset += PAGE_SIZE

                time.sleep(0.20)

            except Exception as e:

                print(
                    f"  ERROR at offset "
                    f"{offset}: {e}"
                )

                break

    return all_jobs


def get_text(job):

    parts = [
        job.get("title"),
        job.get("company"),
        job.get("employer"),
        job.get("organization"),
        job.get("description"),
        job.get("location"),
    ]

    skills = job.get("skills") or []

    if isinstance(skills, list):
        parts.extend(skills)

    return " ".join(
        str(x)
        for x in parts
        if x
    ).lower()


def get_title(job):

    return str(
        job.get("title")
        or ""
    ).lower().strip()


def title_is_relevant(job):

    title = get_title(job)

    for term in BAD_TITLE_TERMS:

        if term in title:
            return False

    for term in GOOD_TITLE_TERMS:

        if term in title:
            return True

    return False


def is_senior_job(job):

    title = get_title(job)

    for term in SENIOR_TITLE_TERMS:

        if term in title:
            return True

    return False


def url_contains_seniority(job):

    url = str(
        job.get("url")
        or ""
    ).lower()

    senior_terms = [
        "assistant-vice-president",
        "assistant%20vice%20president",
        "vice-president",
        "vice_president",
        "avp",
        "senior",
        "principal",
        "lead",
        "manager",
        "director",
        "architect",
    ]

    for term in senior_terms:

        if term in url:
            return True

    return False


def get_locations(job):

    locations = []

    for key in [
        "location",
        "countries",
        "regions",
        "cities",
    ]:

        value = job.get(key)

        if isinstance(value, list):

            locations.extend(
                str(x).lower()
                for x in value
            )

        elif value:

            locations.append(
                str(value).lower()
            )

    return locations


def is_india_or_remote(job):

    locations = get_locations(job)

    for location in locations:

        location = (
            location
            .strip()
            .lower()
        )

        for india_location in INDIA_LOCATIONS:

            if india_location in location:
                return True

        for remote_location in REMOTE_LOCATIONS:

            if location == remote_location:
                return True

    countries = job.get(
        "countries"
    )

    if isinstance(countries, list):

        for country in countries:

            country = str(
                country
            ).lower().strip()

            if country in [
                "india",
                "in",
            ]:
                return True

    elif countries:

        if "india" in str(
            countries
        ).lower():

            return True

    return False


def get_location_match(job):

    locations = get_locations(job)

    for location in locations:

        for preferred in PREFERRED_LOCATIONS:

            if preferred in location:
                return preferred

    for location in locations:

        if location.strip() in REMOTE_LOCATIONS:
            return "remote"

    return None


def get_api_experience(job):

    enrichment = job.get(
        "enrichment"
    ) or {}

    value = enrichment.get(
        "experience_years_min"
    )

    if value is None:
        return None

    try:
        return float(value)

    except (
        ValueError,
        TypeError
    ):
        return None


def extract_description_experience(job):

    description = str(
        job.get("description")
        or ""
    ).lower()

    if not description:
        return None

    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+\s*years?",
        r"minimum\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*years?",
        r"at\s+least\s+(\d+(?:\.\d+)?)\s*years?",
        r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*years?",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*years?",
    ]

    candidates = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            description
        )

        for match in matches:

            if isinstance(
                match,
                tuple
            ):

                numbers = []

                for value in match:

                    if value:
                        numbers.append(
                            float(value)
                        )

                if numbers:
                    candidates.append(
                        max(numbers)
                    )

            else:

                candidates.append(
                    float(match)
                )

    if not candidates:
        return None

    return max(candidates)


def get_effective_experience(job):

    api_exp = get_api_experience(job)

    description_exp = (
        extract_description_experience(
            job
        )
    )

    if (
        api_exp is not None
        and description_exp is not None
    ):

        return max(
            api_exp,
            description_exp
        )

    if api_exp is not None:
        return api_exp

    return description_exp


def get_age_days(job):

    enrichment = job.get(
        "enrichment"
    ) or {}

    reality = enrichment.get(
        "reality"
    ) or {}

    age = reality.get(
        "age_days"
    )

    if age is not None:

        try:
            return int(age)

        except (
            ValueError,
            TypeError
        ):
            pass

    posted_at = job.get(
        "posted_at"
    )

    if posted_at:

        try:

            posted = datetime.fromisoformat(
                posted_at.replace(
                    "Z",
                    "+00:00"
                )
            )

            now = datetime.now(
                timezone.utc
            )

            return max(
                0,
                (now - posted).days
            )

        except Exception:
            pass

    return None


def normalize_company(company):

    if not company:
        return ""

    company = str(
        company
    ).lower()

    company = company.replace(
        "&",
        " and "
    )

    company = re.sub(
        r"[^a-z0-9]+",
        " ",
        company
    )

    company = re.sub(
        r"\s+",
        " ",
        company
    ).strip()

    company = company.replace(
        "jp morgan chase",
        "jpmorgan"
    )

    company = company.replace(
        "jp morgan",
        "jpmorgan"
    )

    company = company.replace(
        "jpmorgan chase",
        "jpmorgan"
    )

    return company.strip()


def normalize_title(title):

    if not title:
        return ""

    title = str(
        title
    ).lower()

    title = re.sub(
        r"[^a-z0-9]+",
        " ",
        title
    )

    title = re.sub(
        r"\b(i|ii|iii|iv|v)\b",
        "",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


def normalize_location(location):

    if not location:
        return ""

    location = str(
        location
    ).lower()

    location = re.sub(
        r"[^a-z0-9]+",
        " ",
        location
    )

    location = location.replace(
        "bengaluru",
        "bangalore"
    )

    return location.strip()


def deduplicate_jobs(jobs):

    unique = {}

    for job in jobs:

        company = (
            job.get("company")
            or job.get("employer")
            or job.get("organization")
            or ""
        )

        title = job.get(
            "title"
        ) or ""

        location = (
            job.get("location")
            or ""
        )

        key = (
            normalize_company(company)
            + "|"
            + normalize_title(title)
            + "|"
            + normalize_location(location)
        )

        if key == "||":

            key = str(
                job.get("id")
                or job.get("url")
                or ""
            ).lower()

        if key not in unique:

            unique[key] = job

        else:

            old_age = get_age_days(
                unique[key]
            )

            new_age = get_age_days(
                job
            )

            if (
                new_age is not None
                and (
                    old_age is None
                    or new_age < old_age
                )
            ):

                unique[key] = job

    return list(
        unique.values()
    )


def is_entry_level(job):

    title = get_title(job)

    text = get_text(job)

    entry_terms = [
        "junior",
        "jr.",
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

    for term in entry_terms:

        if term in title:
            return True

        if term in text:
            return True

    return False


def calculate_skill_score(job):

    text = get_text(job)

    points = 0
    matched = []

    for skill, value in TARGET_SKILLS.items():

        if skill in text:

            points += value

            matched.append(
                skill
            )

    return points, matched


def score_job(job):

    title = get_title(job)

    text = get_text(job)

    if not title_is_relevant(job):
        return None

    if not is_india_or_remote(job):
        return None

    if is_senior_job(job):
        return None

    if url_contains_seniority(job):
        return None

    experience = get_effective_experience(job)

    if (
        experience is not None
        and experience > 3
    ):
        return None

    score = 0

    reasons = []
    concerns = []

    skill_score, matched = (
        calculate_skill_score(job)
    )

    score += min(
        skill_score,
        45
    )

    if "databricks" in text:

        score += 7

        reasons.append(
            "Databricks"
        )

    if "pyspark" in text:

        score += 7

        reasons.append(
            "PySpark"
        )

    if "delta lake" in text:

        score += 6

        reasons.append(
            "Delta Lake"
        )

    if "delta lakehouse" in text:

        score += 6

        reasons.append(
            "Delta Lakehouse"
        )

    if "aws glue" in text:

        score += 4

        reasons.append(
            "AWS Glue"
        )

    location_match = get_location_match(job)

    if location_match:

        score += 10

        reasons.append(
            "Remote"
            if location_match == "remote"
            else location_match.title()
        )

    if experience is None:

        score += 3

        concerns.append(
            "Experience unclear"
        )

    elif experience <= 1:

        score += 20

        reasons.append(
            "0-1 year experience"
        )

    elif experience <= 2:

        score += 15

        reasons.append(
            "1-2 year experience"
        )

    elif experience <= 3:

        score += 3

        concerns.append(
            "3 year experience requirement"
        )

    if is_entry_level(job):

        score += 12

        reasons.append(
            "Entry-level signal"
        )

    for term in JUNIOR_TITLE_TERMS:

        if term in title:

            score += 6

            reasons.append(
                "Junior title"
            )

            break

    age_days = get_age_days(job)

    if age_days is not None:

        if age_days <= 1:

            score += 8

            reasons.append(
                "Posted today"
            )

        elif age_days <= 3:

            score += 6

            reasons.append(
                "Posted recently"
            )

        elif age_days <= 7:

            score += 4

        elif age_days > 21:

            score -= 3

            concerns.append(
                "Older posting"
            )

    enrichment = job.get(
        "enrichment"
    ) or {}

    reality = enrichment.get(
        "reality"
    ) or {}

    if reality.get(
        "fake_freshness",
        False
    ):

        score -= 10

        concerns.append(
            "Possible fake freshness"
        )

    try:

        if int(
            reality.get(
                "repost_count",
                0
            )
        ) > 5:

            score -= 5

            concerns.append(
                "Frequently reposted"
            )

    except:
        pass

    if (
        score >= 75
        and experience is not None
        and experience <= 2
    ):

        recommendation = "APPLY"

    elif (
        score >= 75
        and experience is None
        and is_entry_level(job)
    ):

        recommendation = "APPLY"

    elif (
        score >= 60
        and experience is not None
        and experience <= 2
    ):

        recommendation = "STRONG MAYBE"

    elif (
        score >= 65
        and experience is not None
        and experience <= 3
    ):

        recommendation = "STRETCH"

    elif score >= 50:

        recommendation = "MAYBE"

    else:

        recommendation = "LOW PRIORITY"

    score = max(
        0,
        min(
            score,
            100
        )
    )

    return {
        "score": score,
        "matched": matched,
        "reasons": reasons,
        "concerns": concerns,
        "location": location_match,
        "experience": experience,
        "age_days": age_days,
        "recommendation": recommendation,
    }


def main():

    print()
    print("=" * 75)
    print(
        "        AI DATA ENGINEERING JOB HUNTER V7"
    )
    print("=" * 75)

    jobs = fetch_all_jobs()

    print()
    print("=" * 75)
    print("SEARCH SUMMARY")
    print("=" * 75)

    print(
        f"Raw jobs received: {len(jobs)}"
    )

    jobs = deduplicate_jobs(
        jobs
    )

    print(
        f"Unique jobs: {len(jobs)}"
    )

    results = []

    title_filtered = 0
    location_filtered = 0
    seniority_filtered = 0
    experience_filtered = 0

    for job in jobs:

        if not title_is_relevant(job):

            title_filtered += 1

            continue

        if not is_india_or_remote(job):

            location_filtered += 1

            continue

        if is_senior_job(job):

            seniority_filtered += 1

            continue

        if url_contains_seniority(job):

            seniority_filtered += 1

            continue

        experience = get_effective_experience(
            job
        )

        if (
            experience is not None
            and experience > 3
        ):

            experience_filtered += 1

            continue

        result = score_job(job)

        if result is None:
            continue

        results.append(
            (
                result["score"],
                result,
                job
            )
        )

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    print()
    print("=" * 75)
    print("FILTER SUMMARY")
    print("=" * 75)

    print(
        f"Title filtered: {title_filtered}"
    )

    print(
        f"Location filtered: {location_filtered}"
    )

    print(
        f"Seniority filtered: {seniority_filtered}"
    )

    print(
        f"Experience filtered: {experience_filtered}"
    )

    print(
        f"Final matches: {len(results)}"
    )

    counts = {
        "APPLY": 0,
        "STRONG MAYBE": 0,
        "STRETCH": 0,
        "MAYBE": 0,
        "LOW PRIORITY": 0,
    }

    for _, result, _ in results:

        category = result[
            "recommendation"
        ]

        if category in counts:

            counts[
                category
            ] += 1

    print()
    print(
        f"APPLY: {counts['APPLY']}"
    )

    print(
        f"STRONG MAYBE: "
        f"{counts['STRONG MAYBE']}"
    )

    print(
        f"STRETCH: {counts['STRETCH']}"
    )

    print(
        f"MAYBE: {counts['MAYBE']}"
    )

    print(
        f"LOW PRIORITY: "
        f"{counts['LOW PRIORITY']}"
    )

    # ========================================================
    # SAVE RESULTS FOR ANALYZER
    # ========================================================

    saved_jobs = []

    for score, result, job in results:

        job_copy = dict(job)

        job_copy[
            "_match_score"
        ] = score

        job_copy[
            "_recommendation"
        ] = result[
            "recommendation"
        ]

        job_copy[
            "_matched_skills"
        ] = result[
            "matched"
        ]

        job_copy[
            "_experience"
        ] = result[
            "experience"
        ]

        job_copy[
            "_location_match"
        ] = result[
            "location"
        ]

        saved_jobs.append(
            job_copy
        )

    with open(
        "jobs.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            saved_jobs,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "Saved all filtered jobs to:"
    )

    print(
        "jobs.json"
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print("=" * 75)
    print(
        "        TOP JOBS FOR YOU"
    )
    print("=" * 75)

    for rank, (
        score,
        result,
        job
    ) in enumerate(
        results[:25],
        1
    ):

        company = (
            job.get("company")
            or job.get("employer")
            or job.get("organization")
            or "Unknown"
        )

        location = (
            job.get("location")
            or job.get("cities")
            or "Unknown"
        )

        print()

        print(
            f"#{rank} "
            f"MATCH: {score}/100 "
            f"[{result['recommendation']}]"
        )

        print(
            f"TITLE: {job.get('title')}"
        )

        print(
            f"COMPANY: {company}"
        )

        print(
            f"LOCATION: {location}"
        )

        print(
            f"EXPERIENCE: "
            f"{result['experience']}"
        )

        print(
            f"URL: "
            f"{job.get('url', 'No URL')}"
        )

        print(
            "-" * 75
        )


if __name__ == "__main__":
    main()