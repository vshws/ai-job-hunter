#!/usr/bin/env python3


from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


# =============================================================================
# CONFIGURATION
# =============================================================================

HOST = "0.0.0.0"
PORT = 8000

BASE_DIR = Path(__file__).resolve().parent

TRACKER_FILE = BASE_DIR / "application_tracker.json"
QUEUE_FILE = BASE_DIR / "application_queue.json"
ARCHIVE_FILE = BASE_DIR / "archived_jobs.json"
TRASH_FILE = BASE_DIR / "trash_jobs.json"

REFRESH_SCRIPT = BASE_DIR / "refresh_jobs.py"
REFRESH_STATUS_FILE = BASE_DIR / ".refresh_status.json"
REFRESH_LOG_FILE = BASE_DIR / "refresh_jobs.log"


# =============================================================================
# APPLICATION STATUSES
# =============================================================================

VALID_STATUSES = (
    "NOT APPLIED",
    "APPLIED",
    "INTERVIEW",
    "ACCEPTED",
    "REJECTED",
)

STATUS_COLORS = {
    "NOT APPLIED": "#64748b",
    "APPLIED": "#2563eb",
    "INTERVIEW": "#d97706",
    "ACCEPTED": "#16a34a",
    "REJECTED": "#dc2626",
}


# =============================================================================
# REFRESH STATE
# =============================================================================

refresh_lock = threading.Lock()
refresh_thread = None


# =============================================================================
# JSON HELPERS
# =============================================================================

def load_json(path: Path):
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def save_json(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary.replace(path)


def as_list(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in (
            "applications",
            "jobs",
            "queue",
            "items",
            "results",
            "data",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def number(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


# =============================================================================
# TEXT / STATUS HELPERS
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value or ""))


def normalize_status(value):
    if not value:
        return "NOT APPLIED"

    raw = (
        str(value)
        .strip()
        .upper()
        .replace("_", " ")
    )

    aliases = {
        "NOTAPPLIED": "NOT APPLIED",
        "NOT APPLIED": "NOT APPLIED",
        "APPLIED": "APPLIED",
        "INTERVIEW": "INTERVIEW",
        "INTERVIEWING": "INTERVIEW",
        "ACCEPTED": "ACCEPTED",
        "OFFER": "ACCEPTED",
        "REJECTED": "REJECTED",
        "REJECT": "REJECTED",
    }

    return aliases.get(raw, "NOT APPLIED")


def clean_url(url):
    if not url:
        return ""

    return str(url).strip().split("#", 1)[0]


def job_key(job):
    if not isinstance(job, dict):
        return ""

    nested = job.get("job")

    if isinstance(nested, dict):
        merged = dict(nested)
        merged.update(
            {
                key: value
                for key, value in job.items()
                if key != "job"
            }
        )
        job = merged

    url = clean_url(
        job.get("url")
        or job.get("apply_url")
        or job.get("application_url")
    )

    if url:
        return "URL:" + url.lower()

    title = str(
        job.get("title")
        or job.get("job_title")
        or ""
    ).strip().lower()

    company = str(
        job.get("company")
        or job.get("company_name")
        or ""
    ).strip().lower()

    location = str(
        job.get("location")
        or job.get("job_location")
        or ""
    ).strip().lower()

    return "TEXT:" + title + "|" + company + "|" + location


# =============================================================================
# JOB NORMALIZATION
# =============================================================================

def normalize_job(raw, index=0):
    if not isinstance(raw, dict):
        raw = {}

    nested = raw.get("job")

    if isinstance(nested, dict):
        merged = dict(nested)
        merged.update(
            {
                key: value
                for key, value in raw.items()
                if key != "job"
            }
        )
        raw = merged

    app_id = (
        raw.get("application_id")
        or raw.get("app_id")
        or raw.get("id")
        or f"APP-{index + 1:04d}"
    )

    title = (
        raw.get("title")
        or raw.get("job_title")
        or "Untitled Job"
    )

    company = (
        raw.get("company")
        or raw.get("company_name")
        or "Unknown Company"
    )

    location = (
        raw.get("location")
        or raw.get("job_location")
        or "Unknown"
    )

    url = (
        raw.get("url")
        or raw.get("apply_url")
        or raw.get("application_url")
        or "#"
    )

    score = raw.get("match_score")

    if score is None:
        score = raw.get("score")

    if isinstance(score, dict):
        score = score.get("score")

    priority = raw.get("priority", 0)

    status = normalize_status(
        raw.get("status")
        or raw.get("application_status")
        or raw.get("workflow_status")
    )

    # Different pipeline versions use different field names.
    experience_required = (
        raw.get("experience_required")
        if raw.get("experience_required") is not None
        else raw.get("required_experience")
    )

    if experience_required is None:
        experience_required = raw.get("experience")

    experience_status = (
        raw.get("experience_status")
        or raw.get("experience_requirement_status")
        or ""
    )

    skill_match = raw.get("skill_match")

    if skill_match is None:
        skill_match = raw.get("skill_match_percentage")

    recommendation = (
        raw.get("recommendation")
        or raw.get("category")
        or raw.get("classification")
        or raw.get("decision")
        or raw.get("label")
        or ""
    )

    matched_skills = (
        raw.get("matched_skills")
        or raw.get("matched")
        or raw.get("skills_matched")
        or []
    )

    missing_skills = (
        raw.get("missing_skills")
        or raw.get("missing")
        or raw.get("skills_missing")
        or []
    )

    if isinstance(matched_skills, str):
        matched_skills = [
            item.strip()
            for item in matched_skills.split(",")
            if item.strip()
        ]

    if isinstance(missing_skills, str):
        missing_skills = [
            item.strip()
            for item in missing_skills.split(",")
            if item.strip()
        ]

    record = dict(raw)

    record.update(
        {
            "application_id": str(app_id),
            "title": str(title),
            "company": str(company),
            "location": str(location),
            "url": str(url),
            "match_score": number(score),
            "priority": number(priority),
            "status": status,
            "experience_required": experience_required,
            "experience_status": str(experience_status or ""),
            "skill_match": number(skill_match),
            "recommendation": str(recommendation or ""),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "job_state": str(raw.get("job_state") or "ACTIVE"),
            "first_seen_at": str(raw.get("first_seen_at") or ""),
            "last_seen_at": str(raw.get("last_seen_at") or ""),
            "archived_at": str(raw.get("archived_at") or ""),
        }
    )

    return record


def load_from_file(path: Path):
    data = load_json(path)
    result = []
    seen = set()

    for index, raw in enumerate(as_list(data)):
        job = normalize_job(raw, index)
        key = job_key(job)

        if key in seen:
            continue

        seen.add(key)
        result.append(job)

    return result


# =============================================================================
# LOAD ACTIVE / REVIEW / ARCHIVE DATA
# =============================================================================

def load_applications():
    tracker = load_from_file(TRACKER_FILE)

    if tracker:
        return tracker

    return load_from_file(QUEUE_FILE)


def load_queue():
    return load_from_file(QUEUE_FILE)


def load_archive():
    return load_from_file(ARCHIVE_FILE)


def load_trash():
    return load_from_file(TRASH_FILE)


def application_keys(applications):
    return {
        job_key(job)
        for job in applications
        if job_key(job)
    }


def is_review_candidate(job, active_keys, archived_keys):
    """
    Manual review is intentionally LENIENT.

    A job is shown for manual review when:
      - the ranker calls it REVIEW / VERIFY FIRST / STRETCH / MAYBE
      - OR experience is unknown but the match is good
      - OR experience requirement is between 1 and 3 years and the
        match is reasonably good

    This deliberately includes 1-year and 3-year opportunities.
    """

    key = job_key(job)

    if not key:
        return False

    if key in active_keys or key in archived_keys:
        return False

    recommendation = (
        job.get("recommendation", "")
        .strip()
        .upper()
    )

    score = number(job.get("match_score"))
    skill_match = number(job.get("skill_match"))

    review_labels = {
        "REVIEW",
        "VERIFY FIRST",
        "STRETCH",
        "MAYBE",
        "MANUAL REVIEW",
    }

    if recommendation in review_labels:
        return True

    raw_experience = job.get("experience_required")

    if raw_experience is None or str(raw_experience).strip() == "":
        # Unknown experience + good resume match = review.
        return score >= 70 or skill_match >= 65

    experience = number(raw_experience, -1)

    if 1 <= experience <= 3:
        return score >= 65 or skill_match >= 60

    return False


def get_review_jobs(applications, queue, archive):
    active_keys = application_keys(applications)
    archived_keys = application_keys(archive)

    review = []

    for job in queue:
        if is_review_candidate(
            job,
            active_keys,
            archived_keys,
        ):
            review.append(job)

    review.sort(
        key=lambda job: (
            -number(job.get("match_score")),
            -number(job.get("skill_match")),
            -number(job.get("priority")),
            job.get("company", "").lower(),
        )
    )

    return review


def get_new_jobs(applications, refresh_status):
    """
    New jobs are jobs whose first_seen_at happened during the latest
    successful refresh.
    """

    if not applications:
        return []

    started_at = str(
        refresh_status.get("started_at") or ""
    )

    finished_at = str(
        refresh_status.get("finished_at") or ""
    )

    if not started_at:
        return []

    new_jobs = []

    for job in applications:
        first_seen = str(
            job.get("first_seen_at") or ""
        )

        if not first_seen:
            continue

        # ISO timestamps compare safely when generated by refresh_jobs.py.
        if started_at <= first_seen <= (finished_at or first_seen):
            new_jobs.append(job)

    new_jobs.sort(
        key=lambda job: (
            -number(job.get("priority")),
            -number(job.get("match_score")),
        )
    )

    return new_jobs


# =============================================================================
# UPDATE APPLICATION STATUS
# =============================================================================

def update_application(app_id, status, job_key_value=""):
    status = normalize_status(status)

    if status not in VALID_STATUSES:
        return False, "Invalid status."

    data = load_json(TRACKER_FILE)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = []

        for key in (
            "applications",
            "jobs",
            "queue",
            "items",
            "results",
            "data",
        ):
            if isinstance(data.get(key), list):
                items = data[key]
                break
    else:
        items = []

    found = False
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for raw in items:
        if not isinstance(raw, dict):
            continue

        current_id = (
            raw.get("application_id")
            or raw.get("app_id")
            or raw.get("id")
            or ""
        )

        normalized = normalize_job(raw)
        normalized_id = str(normalized.get("application_id") or "")
        current_key = job_key(raw)

        matches_id = str(current_id) == str(app_id)
        matches_normalized_id = (
            normalized_id
            and normalized_id == str(app_id)
        )
        matches_key = (
            job_key_value
            and current_key == str(job_key_value)
        )

        if not (matches_id or matches_normalized_id or matches_key):
            continue

        raw["status"] = status
        raw["application_status"] = status
        raw["workflow_status"] = status
        raw["status_updated_at"] = now

        if status == "APPLIED":
            raw["applied_at"] = now

        elif status == "INTERVIEW":
            raw["interview_at"] = now

        elif status == "ACCEPTED":
            raw["accepted_at"] = now

        elif status == "REJECTED":
            raw["rejected_at"] = now

        found = True
        break

    if not found:
        return False, "Application not found."

    save_json(TRACKER_FILE, data)

    return True, "Updated."


def next_application_id(items):
    """Return the next available APP-#### identifier."""
    highest = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_id = (
            item.get("application_id")
            or item.get("app_id")
            or item.get("id")
            or ""
        )
        match = re.search(r"(\d+)$", str(raw_id))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"APP-{highest + 1:04d}"


def move_job_to_trash(job, reason="Rejected"):
    """Store a rejected job in trash_jobs.json."""
    trash = load_trash()
    key = job_key(job)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = normalize_job(job)
    record.update({
        "job_state": "TRASH",
        "status": "REJECTED",
        "application_status": "REJECTED",
        "workflow_status": "REJECTED",
        "status_updated_at": now,
        "trashed_at": now,
        "trash_reason": reason,
    })

    result = []
    replaced = False
    for existing in trash:
        if job_key(existing) == key:
            if not replaced:
                result.append(record)
                replaced = True
        else:
            result.append(existing)
    if not replaced:
        result.append(record)
    save_json(TRASH_FILE, result)
    return record


def find_queue_job(job_key_value="", app_id=""):
    """Find a queue job by stable job key or application id."""
    queue = load_queue()
    wanted_key = str(job_key_value or "")
    wanted_id = str(app_id or "")

    if wanted_key:
        for job in queue:
            if job_key(job) == wanted_key:
                return job

    if wanted_id:
        for job in queue:
            current_id = str(
                job.get("application_id")
                or job.get("app_id")
                or job.get("id")
                or ""
            )
            if current_id == wanted_id:
                return job

    return None


def add_review_to_active(app_id="", job_key_value=""):
    """Move a manual-review job into the active tracker."""
    target = find_queue_job(job_key_value, app_id)
    if target is None:
        return False, "Manual-review job not found."

    key = job_key(target)
    applications = load_from_file(TRACKER_FILE)
    archive = load_archive()
    trash = load_trash()

    if key in application_keys(applications):
        return False, "Job is already active."
    if key in application_keys(archive):
        return False, "Job is already archived."
    if key in application_keys(trash):
        return False, "Job is already in trash."

    record = normalize_job(target)
    now = datetime.now().isoformat(timespec="seconds")
    record["application_id"] = next_application_id(applications + archive + trash)
    record["status"] = "NOT APPLIED"
    record["application_status"] = "NOT APPLIED"
    record["workflow_status"] = "NOT APPLIED"
    record["job_state"] = "ACTIVE"
    record["first_seen_at"] = str(record.get("first_seen_at") or now)
    record["last_seen_at"] = now

    applications.append(record)
    save_json(TRACKER_FILE, applications)
    return True, f"{record['application_id']} added to Active Applications."


def reject_review_to_trash(app_id="", job_key_value=""):
    """Move a manual-review job directly to Trash."""
    target = find_queue_job(job_key_value, app_id)
    if target is None:
        return False, "Manual-review job not found."
    move_job_to_trash(target, "Rejected during manual review")
    return True, "Job moved to Trash."


def reject_active_application_to_trash(app_id, job_key_value=""):
    """Move a rejected active application from tracker to Trash."""
    data = load_json(TRACKER_FILE)
    if isinstance(data, list):
        items = data
        wrapper_key = None
    elif isinstance(data, dict):
        items = []
        wrapper_key = None
        for key in ("applications", "jobs", "queue", "items", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                items = value
                wrapper_key = key
                break
    else:
        return False, "Application tracker is empty or invalid."

    target = None
    kept = []
    for raw in items:
        if not isinstance(raw, dict):
            kept.append(raw)
            continue
        current_id = (
            raw.get("application_id")
            or raw.get("app_id")
            or raw.get("id")
            or ""
        )
        normalized = normalize_job(raw)
        normalized_id = str(normalized.get("application_id") or "")
        current_key = job_key(raw)

        matches = (
            str(current_id) == str(app_id)
            or (normalized_id and normalized_id == str(app_id))
            or (job_key_value and current_key == str(job_key_value))
        )

        if matches and target is None:
            target = raw
        else:
            kept.append(raw)

    if target is None:
        return False, "Application not found."

    if wrapper_key is None:
        save_json(TRACKER_FILE, kept)
    else:
        updated = dict(data)
        updated[wrapper_key] = kept
        save_json(TRACKER_FILE, updated)

    move_job_to_trash(target, "Company rejection / application rejected")
    return True, f"{app_id} rejected and moved to Trash."


# =============================================================================
# REFRESH STATUS
# =============================================================================

def get_refresh_status():
    data = load_json(REFRESH_STATUS_FILE)

    if not isinstance(data, dict):
        return {
            "status": "IDLE",
            "progress": 0,
            "step": "Ready",
            "detail": "",
            "message": "Ready to refresh current job listings.",
            "started_at": "",
            "finished_at": "",
            "elapsed_seconds": 0,
            "eta_seconds": None,
        }

    return data


def run_refresh_job():
    global refresh_thread

    started = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:
        if not REFRESH_SCRIPT.exists():
            raise FileNotFoundError(
                f"Missing {REFRESH_SCRIPT.name}"
            )

        # Do not overwrite the refresh status here because refresh_jobs.py
        # owns the detailed progress file.
        with REFRESH_LOG_FILE.open(
            "w",
            encoding="utf-8",
        ) as log:

            log.write(
                f"Refresh started: {started}\n"
            )
            log.flush()

            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(REFRESH_SCRIPT),
                ],
                cwd=str(BASE_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )

            process.wait()

    except Exception as exc:
        finished = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        save_json(
            REFRESH_STATUS_FILE,
            {
                "status": "FAILED",
                "progress": 0,
                "step": "Dashboard",
                "detail": str(exc),
                "message": f"Refresh failed: {exc}",
                "started_at": started,
                "finished_at": finished,
                "elapsed_seconds": 0,
                "eta_seconds": None,
                "error": str(exc),
            },
        )

    finally:
        refresh_thread = None

        try:
            refresh_lock.release()
        except RuntimeError:
            pass


def start_refresh():
    global refresh_thread

    acquired = refresh_lock.acquire(
        blocking=False
    )

    if not acquired:
        return False, "A refresh is already running."

    refresh_thread = threading.Thread(
        target=run_refresh_job,
        daemon=True,
    )

    refresh_thread.start()

    return True, "Refresh started."


# =============================================================================
# HTML HELPERS
# =============================================================================

def status_badge(status):
    color = STATUS_COLORS.get(
        status,
        "#64748b",
    )

    return (
        '<span class="badge" style="background:'
        + color
        + '">'
        + esc(status)
        + "</span>"
    )


def recommendation_badge(job):
    recommendation = (
        job.get("recommendation")
        or ""
    ).strip()

    if not recommendation:
        return ""

    upper = recommendation.upper()

    colors = {
        "APPLY NOW": "#16a34a",
        "APPLY": "#16a34a",
        "STRONG APPLY": "#16a34a",
        "REVIEW": "#d97706",
        "VERIFY FIRST": "#7c3aed",
        "STRETCH": "#ea580c",
        "MAYBE": "#d97706",
    }

    color = colors.get(
        upper,
        "#64748b",
    )

    return (
        '<span class="badge" style="background:'
        + color
        + '">'
        + esc(recommendation)
        + "</span>"
    )


def skill_text(value):
    if isinstance(value, list):
        return ", ".join(
            str(item)
            for item in value
        )

    return str(value or "")


def experience_text(job):
    value = job.get("experience_required")

    if value is None or str(value).strip() == "":
        return "Not specified"

    try:
        number_value = float(value)

        if number_value.is_integer():
            return f"{int(number_value)} year(s)"

        return f"{number_value:g} year(s)"

    except (TypeError, ValueError):
        return str(value)


def render_status_form(job):
    app_id = esc(
        job.get("application_id")
    )

    status = normalize_status(
        job.get("status")
    )

    options = []

    for item in VALID_STATUSES:
        selected = (
            " selected"
            if item == status
            else ""
        )

        options.append(
            '<option value="'
            + esc(item)
            + '"'
            + selected
            + ">"
            + esc(item)
            + "</option>"
        )

    job_key_value = esc(job_key(job))

    return (
        '<form method="POST" action="/update" class="status-form">'
        '<input type="hidden" name="application_id" value="'
        + app_id
        + '">'
        '<input type="hidden" name="job_key" value="'
        + job_key_value
        + '">'
        '<label>Status</label>'
        '<select name="status">'
        + "".join(options)
        + "</select>"
        '<button type="submit">Update Status</button>'
        "</form>"
    )


# =============================================================================
# ACTIVE APPLICATION CARD
# =============================================================================

def render_application_card(job, new=False):
    title = esc(job.get("title"))
    company = esc(job.get("company"))
    location = esc(job.get("location"))
    app_id = esc(job.get("application_id"))
    url = esc(job.get("url") or "#")

    score = f'{number(job.get("match_score")):.0f}'
    priority = f'{number(job.get("priority")):.0f}'

    new_badge = (
        '<span class="new-badge">NEW THIS REFRESH</span>'
        if new
        else ""
    )

    return "".join(
        [
            '<article class="job-card">',
            '<div class="job-top">',
            '<div>',
            '<div class="app-id">',
            app_id,
            " ",
            new_badge,
            "</div>",
            "<h3>",
            title,
            "</h3>",
            '<div class="company">',
            company,
            "</div>",
            "</div>",
            '<div class="score"><strong>',
            score,
            '</strong><span>/100</span></div>',
            "</div>",
            '<div class="meta">',
            "<span>📍 ",
            location,
            "</span>",
            "<span>Priority: ",
            priority,
            "</span>",
            status_badge(job.get("status")),
            "</div>",
            '<div class="skills-row">',
            "<span><strong>Matched:</strong> ",
            esc(skill_text(job.get("matched_skills"))),
            "</span>",
            "</div>",
            '<div class="workflow">',
            render_status_form(job),
            '<a class="apply-link" href="',
            url,
            '" target="_blank" rel="noopener">Open Job ↗</a>',
            "</div>",
            "</article>",
        ]
    )


# =============================================================================
# MANUAL REVIEW CARD
# =============================================================================

def render_review_card(job, index):
    title = esc(job.get("title"))
    company = esc(job.get("company"))
    location = esc(job.get("location"))
    url = esc(job.get("url") or "#")
    key = esc(job_key(job))
    score = f'{number(job.get("match_score")):.0f}'
    skill_match = number(job.get("skill_match"))
    recommendation = job.get("recommendation") or "MANUAL REVIEW"
    matched = skill_text(job.get("matched_skills"))
    missing = skill_text(job.get("missing_skills"))
    exp_status = job.get("experience_status") or "Not specified"

    return "".join([
        '<article class="job-card review-card">',
        '<div class="job-top">',
        '<div>',
        '<div class="app-id">REVIEW #', str(index), '</div>',
        '<h3>', title, '</h3>',
        '<div class="company">', company, '</div>',
        '</div>',
        '<div class="score"><strong>', score, '</strong><span>/100</span></div>',
        '</div>',
        '<div class="meta">',
        '<span>📍 ', location, '</span>',
        '<span>Experience: ', esc(experience_text(job)), '</span>',
        '<span>Skill match: ', f"{skill_match:.0f}", '%</span>',
        recommendation_badge(job),
        '</div>',
        '<div class="review-reason"><strong>Why review?</strong><br>',
        'Experience status: ', esc(exp_status),
        '. This job is intentionally kept for manual review.</div>',
        '<div class="skill-grid">',
        '<div><strong>Matched skills</strong><br>', esc(matched or "None detected"), '</div>',
        '<div><strong>Missing skills</strong><br>', esc(missing or "None detected"), '</div>',
        '</div>',
        '<div class="workflow review-actions">',
        '<div class="review-button-group">',
        '<form method="POST" action="/review-action" class="inline-action-form">',
        '<input type="hidden" name="action" value="add_active">',
        '<input type="hidden" name="job_key" value="', key, '">',
        '<button type="submit" class="decision-button active-button">✓ Add to Active</button>',
        '</form>',
        '<form method="POST" action="/review-action" class="inline-action-form" ',
        'onsubmit="return confirm(\'Move this job to Trash?\');">',
        '<input type="hidden" name="action" value="reject">',
        '<input type="hidden" name="job_key" value="', key, '">',
        '<button type="submit" class="decision-button trash-button">🗑 Reject to Trash</button>',
        '</form>',
        '</div>',
        '<a class="apply-link" href="', url, '" target="_blank" rel="noopener">Open Job ↗</a>',
        '</div>',
        '</article>',
    ])


# =============================================================================
# ARCHIVE CARD
# =============================================================================

def render_archive_card(job):
    title = esc(job.get("title"))
    company = esc(job.get("company"))
    location = esc(job.get("location"))
    url = esc(job.get("url") or "#")

    score = f'{number(job.get("match_score")):.0f}'
    status = normalize_status(job.get("status"))

    archived_at = (
        job.get("archived_at")
        or "Unknown"
    )

    return (
        '<article class="archive-card">'
        '<div class="archive-main">'
        "<h3>"
        + title
        + "</h3>"
        '<div class="company">'
        + company
        + "</div>"
        '<div class="archive-meta">'
        "📍 "
        + location
        + " · Match "
        + score
        + "/100 · "
        + esc(status)
        + " · Archived "
        + esc(archived_at)
        + "</div>"
        "</div>"
        '<a class="archive-link" href="'
        + url
        + '" target="_blank" rel="noopener">Open ↗</a>'
        "</article>"
    )


def render_trash_card(job):
    title = esc(job.get("title"))
    company = esc(job.get("company"))
    location = esc(job.get("location"))
    url = esc(job.get("url") or "#")
    score = f'{number(job.get("match_score")):.0f}'
    reason = esc(job.get("trash_reason") or "Rejected")
    trashed_at = esc(job.get("trashed_at") or "Unknown")

    return "".join([
        '<article class="trash-card">',
        '<div class="trash-main">',
        '<h3>', title, '</h3>',
        '<div class="company">', company, '</div>',
        '<div class="archive-meta">📍 ', location,
        ' · Match ', score, '/100 · ', reason,
        ' · ', trashed_at, '</div>',
        '</div>',
        '<a class="archive-link" href="', url, '" target="_blank" rel="noopener">Open ↗</a>',
        '</article>',
    ])


# =============================================================================
# DASHBOARD
# =============================================================================

def render_dashboard(message=""):
    applications = load_applications()
    queue = load_queue()
    archive = load_archive()
    trash = load_trash()
    refresh_status = get_refresh_status()

    applications.sort(
        key=lambda job: (
            -number(job.get("priority")),
            -number(job.get("match_score")),
            job.get("company", "").lower(),
        )
    )

    new_jobs = get_new_jobs(
        applications,
        refresh_status,
    )

    new_keys = {
        job_key(job)
        for job in new_jobs
    }

    review_jobs = get_review_jobs(
        applications,
        queue,
        archive,
    )

    review_total = len(review_jobs)
    archive_total = len(archive)
    trash_total = len(trash)

    counts = {
        status: 0
        for status in VALID_STATUSES
    }

    for job in applications:
        counts[normalize_status(job.get("status"))] += 1

    active_cards = "".join(
        render_application_card(
            job,
            job_key(job) in new_keys,
        )
        for job in applications
    )

    if not active_cards:
        active_cards = (
            '<div class="empty">'
            "<h2>No active applications</h2>"
            "<p>Run a refresh to find current jobs.</p>"
            "</div>"
        )

    review_cards = "".join(
        render_review_card(job, index)
        for index, job in enumerate(
            review_jobs,
            start=1,
        )
    )

    if not review_cards:
        review_cards = (
            '<div class="empty">'
            "<h2>No manual-review jobs</h2>"
            "<p>"
            "The lenient review rules did not find additional jobs "
            "outside the active and archived lists."
            "</p>"
            "</div>"
        )

    archive_cards = "".join(
        render_archive_card(job)
        for job in reversed(archive)
    )

    if not archive_cards:
        archive_cards = (
            '<div class="empty">'
            "<h2>No archived jobs yet</h2>"
            "<p>"
            "Jobs that disappear from the active pipeline will appear here."
            "</p>"
            "</div>"
        )

    trash_cards = "".join(
        render_trash_card(job)
        for job in reversed(trash)
    )

    if not trash_cards:
        trash_cards = (
            '<div class="empty">'
            '<h2>Trash is empty</h2>'
            '<p>Rejected jobs will appear here.</p>'
            '</div>'
        )

    progress = number(
        refresh_status.get("progress"),
        0,
    )

    status = str(
        refresh_status.get("status")
        or "IDLE"
    )

    refresh_message = (
        refresh_status.get("message")
        or "Ready to refresh current job listings."
    )

    started_at = (
        refresh_status.get("started_at")
        or ""
    )

    finished_at = (
        refresh_status.get("finished_at")
        or ""
    )

    step = (
        refresh_status.get("step")
        or "Ready"
    )

    detail = (
        refresh_status.get("detail")
        or ""
    )

    elapsed = number(
        refresh_status.get("elapsed_seconds"),
        0,
    )

    eta = refresh_status.get(
        "eta_seconds"
    )

    eta_text = (
        "Complete"
        if status == "SUCCESS"
        else (
            f"{number(eta):.0f}s"
            if eta is not None
            else "--"
        )
    )

    if message:
        notice = (
            '<div class="notice">'
            + esc(message)
            + "</div>"
        )
    else:
        notice = ""

    if status == "RUNNING":
        refresh_button_text = "⏳ Refreshing..."
    elif status == "FAILED":
        refresh_button_text = "↻ Retry Refresh"
    else:
        refresh_button_text = "↻ Refresh Jobs"

    page = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Job Hunter</title>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, Arial, sans-serif;
  background: #eef2f7;
  color: #0f172a;
}

header {
  background: #0f172a;
  color: white;
  padding: 30px 20px;
}

.header-inner,
.container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin: 0 0 7px;
  font-size: 32px;
}

.subtitle {
  color: #cbd5e1;
  font-size: 16px;
}

.container {
  padding: 24px 20px 70px;
}

.notice {
  background: #dcfce7;
  border: 1px solid #86efac;
  color: #166534;
  padding: 12px 15px;
  border-radius: 10px;
  margin-bottom: 18px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.stat {
  background: white;
  border: 1px solid #dbe3ed;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.05);
}

.stat-number {
  font-size: 29px;
  font-weight: 800;
}

.stat-label {
  color: #64748b;
  margin-top: 4px;
  font-size: 13px;
}

.stat-new {
  border-left: 5px solid #16a34a;
}

.stat-review {
  border-left: 5px solid #d97706;
}

.stat-archive {
  border-left: 5px solid #64748b;
}

.panel {
  background: white;
  border: 1px solid #dbe3ed;
  border-radius: 15px;
  padding: 18px;
  margin-bottom: 20px;
}

.panel-title {
  font-size: 17px;
  font-weight: 800;
  margin-bottom: 12px;
}

.flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.flow-step {
  padding: 9px 13px;
  border-radius: 999px;
  color: white;
  font-size: 13px;
  font-weight: 800;
}

.arrow {
  color: #94a3b8;
  font-size: 20px;
}

.refresh-panel {
  background: white;
  border: 1px solid #dbe3ed;
  border-radius: 15px;
  padding: 18px;
  margin-bottom: 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
}

.refresh-info {
  flex: 1;
  min-width: 0;
}

.refresh-message {
  color: #64748b;
  font-size: 13px;
  margin-top: 5px;
}

.refresh-progress-wrap {
  margin-top: 13px;
}

.refresh-progress-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 7px;
  font-size: 13px;
}

.refresh-progress-track {
  width: 100%;
  height: 12px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.refresh-progress-bar {
  height: 100%;
  width: 0%;
  background: #16a34a;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.refresh-eta {
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
  margin-top: 6px;
}

.refresh-button,
.status-form button {
  border: 0;
  color: white;
  background: #16a34a;
  padding: 11px 17px;
  border-radius: 9px;
  cursor: pointer;
  font-weight: 800;
  white-space: nowrap;
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  margin: 28px 0 13px;
}

.section-header h2 {
  margin: 0;
  font-size: 22px;
}

.section-subtitle {
  color: #64748b;
  font-size: 13px;
  margin-top: 3px;
}

.reload {
  text-decoration: none;
  background: #0f172a;
  color: white;
  padding: 10px 15px;
  border-radius: 9px;
  font-weight: 700;
}

.jobs {
  display: grid;
  gap: 14px;
}

.job-card {
  background: white;
  border: 1px solid #dbe3ed;
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
}

.job-top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.app-id {
  font-size: 12px;
  color: #64748b;
  font-weight: 800;
  margin-bottom: 5px;
}

.job-card h3 {
  margin: 0 0 5px;
  font-size: 19px;
}

.company {
  color: #334155;
  font-weight: 700;
}

.score {
  min-width: 85px;
  text-align: right;
}

.score strong {
  font-size: 30px;
}

.score span {
  color: #64748b;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  align-items: center;
  margin: 16px 0;
  color: #475569;
  font-size: 13px;
}

.badge,
.new-badge {
  color: white;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.new-badge {
  background: #16a34a;
  color: white;
}

.skills-row {
  background: #f8fafc;
  border-radius: 9px;
  padding: 10px;
  color: #475569;
  font-size: 13px;
  margin-bottom: 15px;
}

.workflow {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 15px;
  border-top: 1px solid #e2e8f0;
  padding-top: 15px;
}

.status-form {
  display: flex;
  align-items: end;
  gap: 8px;
  flex-wrap: wrap;
}

.status-form label {
  display: block;
  font-size: 12px;
  color: #64748b;
}

.status-form select {
  min-width: 170px;
  padding: 9px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: white;
}

.status-form button {
  background: #2563eb;
}

.apply-link,
.archive-link {
  text-decoration: none;
  background: #e2e8f0;
  color: #0f172a;
  padding: 10px 14px;
  border-radius: 9px;
  font-weight: 800;
  white-space: nowrap;
}

.review-card {
  border-left: 5px solid #d97706;
}

.review-reason {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  padding: 11px;
  border-radius: 9px;
  font-size: 13px;
  line-height: 1.5;
}

.skill-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.skill-grid > div {
  background: #f8fafc;
  border-radius: 9px;
  padding: 10px;
  color: #475569;
  font-size: 13px;
}

.review-actions {
  align-items: center;
}

.review-note {
  color: #64748b;
  font-size: 12px;
}

.review-button-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inline-action-form {
  margin: 0;
}

.decision-button {
  border: 0;
  color: white;
  padding: 10px 13px;
  border-radius: 9px;
  cursor: pointer;
  font-weight: 800;
  white-space: nowrap;
}

.active-button {
  background: #16a34a;
}

.trash-button {
  background: #dc2626;
}

.trash-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  padding: 15px 19px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}

.trash-card:last-child {
  border-bottom: 0;
}

.trash-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.trash-wrap {
  margin-top: 22px;
}

.trash-details {
  background: white;
  border: 1px solid #fecaca;
  border-radius: 15px;
  overflow: hidden;
}

.trash-summary {
  cursor: pointer;
  padding: 17px 19px;
  font-weight: 800;
  list-style: none;
  color: #991b1b;
}

.trash-summary::-webkit-details-marker {
  display: none;
}

.trash-summary::after {
  content: "＋";
  float: right;
}

details[open] .trash-summary::after {
  content: "−";
}

.trash-list {
  border-top: 1px solid #fecaca;
}

.archive-wrap {
  margin-top: 30px;
}

.archive-details {
  background: white;
  border: 1px solid #dbe3ed;
  border-radius: 15px;
  overflow: hidden;
}

.archive-summary {
  cursor: pointer;
  padding: 17px 19px;
  font-weight: 800;
  list-style: none;
}

.archive-summary::-webkit-details-marker {
  display: none;
}

.archive-summary::after {
  content: "＋";
  float: right;
}

details[open] .archive-summary::after {
  content: "−";
}

.archive-list {
  border-top: 1px solid #e2e8f0;
}

.archive-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  padding: 15px 19px;
  border-bottom: 1px solid #e2e8f0;
}

.archive-card:last-child {
  border-bottom: 0;
}

.archive-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.archive-meta {
  color: #64748b;
  font-size: 12px;
  margin-top: 6px;
}

.empty {
  background: white;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
  padding: 32px;
  text-align: center;
  color: #64748b;
}

@media (max-width: 1000px) {
  .stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .refresh-panel,
  .workflow,
  .archive-card {
    flex-direction: column;
    align-items: stretch;
  }

  .refresh-button,
  .apply-link,
  .archive-link,
  .decision-button {
    width: 100%;
    text-align: center;
  }

  .review-button-group {
    width: 100%;
  }

  .inline-action-form {
    width: 100%;
  }

  .job-top {
    flex-direction: column;
  }

  .score {
    text-align: left;
  }

  .skill-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 500px) {
  .stats {
    grid-template-columns: 1fr;
  }
}
</style>
</head>

<body>

<header>
  <div class="header-inner">
    <h1>AI JOB HUNTER</h1>
    <div class="subtitle">
      Track new jobs, applications, manual reviews and archived jobs.
    </div>
  </div>
</header>

<main class="container">

__NOTICE__

<section class="stats">

  <div class="stat">
    <div class="stat-number">__ACTIVE_COUNT__</div>
    <div class="stat-label">ACTIVE APPLICATIONS</div>
  </div>

  <div class="stat stat-new">
    <div class="stat-number">__NEW_COUNT__</div>
    <div class="stat-label">NEW THIS REFRESH</div>
  </div>

  <div class="stat stat-review">
    <div class="stat-number">__REVIEW_COUNT__</div>
    <div class="stat-label">MANUAL REVIEW</div>
  </div>

  <div class="stat stat-archive">
    <div class="stat-number">__ARCHIVE_COUNT__</div>
    <div class="stat-label">ARCHIVED</div>
  </div>

  <div class="stat">
    <div class="stat-number">__INTERVIEW_COUNT__</div>
    <div class="stat-label">INTERVIEW</div>
  </div>

  <div class="stat">
    <div class="stat-number">__ACCEPTED_COUNT__</div>
    <div class="stat-label">ACCEPTED</div>
  </div>

</section>


<section class="panel">
  <div class="panel-title">Application workflow</div>

  <div class="flow">
    <span class="flow-step" style="background:#64748b">NOT APPLIED</span>
    <span class="arrow">→</span>
    <span class="flow-step" style="background:#2563eb">APPLIED</span>
    <span class="arrow">→</span>
    <span class="flow-step" style="background:#d97706">INTERVIEW</span>
    <span class="arrow">→</span>
    <span class="flow-step" style="background:#16a34a">ACCEPTED</span>
    <span class="arrow">/</span>
    <span class="flow-step" style="background:#dc2626">REJECTED</span>
  </div>
</section>


<section class="refresh-panel">

  <div class="refresh-info">
    <strong>Job data refresh</strong>

    <div id="refresh-message" class="refresh-message">
      __REFRESH_MESSAGE__
    </div>

    <div class="refresh-progress-wrap">

      <div class="refresh-progress-row">
        <span id="refresh-step">__REFRESH_STEP__</span>
        <strong id="refresh-percent">__PROGRESS__%</strong>
      </div>

      <div class="refresh-progress-track">
        <div
          id="refresh-progress-bar"
          class="refresh-progress-bar"
          style="width:__PROGRESS__%"
        ></div>
      </div>

      <div class="refresh-eta">
        <span id="refresh-elapsed">Elapsed: __ELAPSED__</span>
        <span id="refresh-eta">ETA: __ETA__</span>
      </div>

    </div>
  </div>

  <button
    id="refresh-button"
    class="refresh-button"
    type="button"
    onclick="startRefresh()"
    __REFRESH_DISABLED__
  >
    __REFRESH_BUTTON__
  </button>

</section>


<div class="section-header">
  <div>
    <h2>🆕 Active applications (__ACTIVE_COUNT__)</h2>
    <div class="section-subtitle">
      Jobs currently retained by the application tracker.
    </div>
  </div>

  <a class="reload" href="/">↻ Reload Dashboard</a>
</div>

<section class="jobs">
__ACTIVE_CARDS__
</section>


<div class="section-header">
  <div>
    <h2>🔎 Manual review (__REVIEW_COUNT__)</h2>
    <div class="section-subtitle">
      Lenient review bucket: 1-year, 2-year and 3-year jobs,
      unknown experience with a good match, plus REVIEW / VERIFY / STRETCH jobs.
    </div>
  </div>
</div>

<section class="jobs">
__REVIEW_CARDS__
</section>


<div class="archive-wrap">

  <details class="archive-details">

    <summary class="archive-summary">
      🗄️ Archived jobs (__ARCHIVE_COUNT__)
      — old/disappeared jobs are kept here for manual review
    </summary>

    <div class="archive-list">
__ARCHIVE_CARDS__
    </div>

  </details>

</div>

<div class="trash-wrap">

  <details class="trash-details">

    <summary class="trash-summary">
      🗑️ Trash / Rejected (__TRASH_COUNT__)
      — rejected jobs are kept here
    </summary>

    <div class="trash-list">
__TRASH_CARDS__
    </div>

  </details>

</div>

</main>


<script>
let refreshPoll = null;

function formatDuration(seconds) {
  if (
    seconds === null ||
    seconds === undefined ||
    !isFinite(seconds)
  ) {
    return "--";
  }

  seconds = Math.max(
    0,
    Math.round(Number(seconds))
  );

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return hours + "h " + minutes + "m";
  }

  if (minutes > 0) {
    return minutes + "m " + secs + "s";
  }

  return secs + "s";
}

async function getRefreshStatus() {
  try {
    const response = await fetch(
      "/refresh-status",
      { cache: "no-store" }
    );

    return await response.json();

  } catch (error) {
    return {
      status: "FAILED",
      progress: 0,
      message: "Could not contact dashboard."
    };
  }
}

function showRefreshStatus(data) {

  const message =
    document.getElementById("refresh-message");

  const button =
    document.getElementById("refresh-button");

  const bar =
    document.getElementById("refresh-progress-bar");

  const percent =
    document.getElementById("refresh-percent");

  const step =
    document.getElementById("refresh-step");

  const elapsed =
    document.getElementById("refresh-elapsed");

  const eta =
    document.getElementById("refresh-eta");

  if (!message || !button) {
    return;
  }

  const progress = Math.max(
    0,
    Math.min(
      100,
      Number(data.progress || 0)
    )
  );

  if (bar) {
    bar.style.width = progress + "%";
  }

  if (percent) {
    percent.textContent =
      Math.round(progress) + "%";
  }

  if (step) {
    const stepName =
      data.step || "Ready";

    const detail =
      data.detail
        ? " — " + data.detail
        : "";

    step.textContent =
      stepName + detail;
  }

  if (elapsed) {
    elapsed.textContent =
      "Elapsed: " +
      formatDuration(
        data.elapsed_seconds
      );
  }

  if (eta) {
    eta.textContent =
      "ETA: " +
      (
        data.status === "SUCCESS"
          ? "Complete"
          : formatDuration(
              data.eta_seconds
            )
      );
  }

  if (data.status === "RUNNING") {

    message.textContent =
      data.message ||
      "Refreshing jobs...";

    button.disabled = true;
    button.textContent =
      "⏳ Refreshing...";

    return;
  }

  if (data.status === "SUCCESS") {

    message.textContent =
      "Last refresh completed: " +
      (
        data.finished_at ||
        "just now"
      );

    button.disabled = false;
    button.textContent =
      "↻ Refresh Jobs";

    return;
  }

  if (data.status === "FAILED") {

    message.textContent =
      data.message ||
      "Refresh failed. Check refresh_jobs.log.";

    button.disabled = false;
    button.textContent =
      "↻ Retry Refresh";

    return;
  }

  message.textContent =
    "Ready to refresh current job listings.";

  button.disabled = false;
  button.textContent =
    "↻ Refresh Jobs";
}

async function pollRefresh() {

  const data =
    await getRefreshStatus();

  showRefreshStatus(data);

  if (data.status === "RUNNING") {

    if (!refreshPoll) {
      refreshPoll =
        setInterval(
          pollRefresh,
          1000
        );
    }

    return;
  }

  if (refreshPoll) {

    clearInterval(refreshPoll);
    refreshPoll = null;

    if (data.status === "SUCCESS") {

      setTimeout(
        function() {
          window.location.reload();
        },
        1000
      );
    }
  }
}

async function startRefresh() {

  const button =
    document.getElementById(
      "refresh-button"
    );

  if (button) {
    button.disabled = true;
    button.textContent =
      "⏳ Starting...";
  }

  try {

    const response =
      await fetch(
        "/refresh",
        {
          method: "POST"
        }
      );

    const data =
      await response.json();

    showRefreshStatus(data);

    if (data.status === "RUNNING") {
      pollRefresh();
    }

  } catch (error) {

    showRefreshStatus({
      status: "FAILED",
      progress: 0,
      message:
        "Could not start refresh."
    });
  }
}

pollRefresh();
</script>

</body>
</html>
"""

    replacements = {
        "__NOTICE__": notice,
        "__ACTIVE_COUNT__": str(len(applications)),
        "__NEW_COUNT__": str(len(new_jobs)),
        "__REVIEW_COUNT__": str(review_total),
        "__ARCHIVE_COUNT__": str(archive_total),
        "__TRASH_COUNT__": str(trash_total),
        "__INTERVIEW_COUNT__": str(counts["INTERVIEW"]),
        "__ACCEPTED_COUNT__": str(counts["ACCEPTED"]),
        "__REFRESH_MESSAGE__": esc(refresh_message),
        "__REFRESH_STEP__": esc(
            step + (
                " — " + detail
                if detail
                else ""
            )
        ),
        "__PROGRESS__": str(
            max(0, min(100, round(progress)))
        ),
        "__ELAPSED__": esc(
            format_duration_py(elapsed)
        ),
        "__ETA__": esc(eta_text),
        "__REFRESH_BUTTON__": refresh_button_text,
        "__REFRESH_DISABLED__": (
            "disabled"
            if status == "RUNNING"
            else ""
        ),
        "__ACTIVE_CARDS__": active_cards,
        "__REVIEW_CARDS__": review_cards,
        "__ARCHIVE_CARDS__": archive_cards,
        "__TRASH_CARDS__": trash_cards,
    }

    for placeholder, value in replacements.items():
        page = page.replace(
            placeholder,
            value,
        )

    return page


def format_duration_py(seconds):
    seconds = max(
        0,
        round(number(seconds)),
    )

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {secs}s"

    return f"{secs}s"


# =============================================================================
# HTTP SERVER
# =============================================================================

class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format_string, *args):
        return

    def send_html(self, page, status=200):
        encoded = page.encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(len(encoded)),
        )

        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, data, status=200):
        payload = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(len(payload)),
        )

        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_html(
                render_dashboard()
            )
            return

        if parsed.path == "/refresh-status":
            self.send_json(
                get_refresh_status()
            )
            return

        if parsed.path == "/health":
            self.send_html("OK")
            return

        self.send_html(
            "<h1>404 - Not Found</h1>",
            404,
        )

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/refresh":

            ok, message = start_refresh()
            status = get_refresh_status()

            status["message"] = message

            self.send_json(
                status,
                202 if ok else 409,
            )
            return

        if parsed.path == "/update":

            try:
                length = int(
                    self.headers.get(
                        "Content-Length",
                        "0",
                    )
                )
            except ValueError:
                length = 0

            body = (
                self.rfile
                .read(length)
                .decode("utf-8")
            )

            values = parse_qs(body)

            app_id = values.get(
                "application_id",
                [""],
            )[0]

            status = values.get(
                "status",
                ["NOT APPLIED"],
            )[0]

            job_key_value = values.get(
                "job_key",
                [""],
            )[0]

            if normalize_status(status) == "REJECTED":
                ok, update_message = reject_active_application_to_trash(
                    app_id,
                    job_key_value,
                )
            else:
                ok, update_message = update_application(
                    app_id,
                    status,
                    job_key_value,
                )

            if ok:
                self.send_html(
                    render_dashboard(
                        f"{app_id} updated to "
                        f"{normalize_status(status)}."
                    )
                )
            else:
                self.send_html(
                    render_dashboard(
                        f"Update failed: {update_message}"
                    ),
                    400,
                )

            return

        if parsed.path == "/review-action":

            try:
                length = int(
                    self.headers.get(
                        "Content-Length",
                        "0",
                    )
                )
            except ValueError:
                length = 0

            body = (
                self.rfile
                .read(length)
                .decode("utf-8")
            )

            values = parse_qs(body)
            action = values.get("action", [""])[0]
            app_id = values.get("application_id", [""])[0]
            review_job_key = values.get("job_key", [""])[0]

            if action == "add_active":
                ok, action_message = add_review_to_active(
                    app_id,
                    review_job_key,
                )
            elif action == "reject":
                ok, action_message = reject_review_to_trash(
                    app_id,
                    review_job_key,
                )
            else:
                ok = False
                action_message = "Unknown review action."

            self.send_html(
                render_dashboard(action_message),
                200 if ok else 400,
            )
            return

        self.send_html(
            "<h1>404 - Not Found</h1>",
            404,
        )


# =============================================================================
# MAIN
# =============================================================================

def main():
    applications = load_applications()
    archive = load_archive()
    trash = load_trash()
    queue = load_queue()

    print("=" * 95)
    print("                         AI JOB HUNTER")
    print("=" * 95)
    print()
    print(
        f"Active applications: {len(applications)}"
    )
    print(
        f"Manual-review candidates: "
        f"{len(get_review_jobs(applications, queue, archive))}"
    )
    print(
        f"Archived jobs: {len(archive)}"
    )
    print(
        f"Trash / rejected jobs: {len(trash)}"
    )
    print()
    print(
        "Application workflow:"
    )
    print(
        "NOT APPLIED  →  APPLIED  →  "
        "INTERVIEW  →  ACCEPTED / REJECTED"
    )
    print()
    print(
        f"Refresh script: "
        f"{REFRESH_SCRIPT.name} "
        f"({'FOUND' if REFRESH_SCRIPT.exists() else 'MISSING'})"
    )
    print()
    print(
        f"Dashboard running at:"
    )
    print(
        f"http://localhost:{PORT}"
    )
    print()
    print("Press Ctrl+C to stop.")
    print()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        DashboardHandler,
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping dashboard...")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()