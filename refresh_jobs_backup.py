#!/usr/bin/env python3



from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRACKER_FILE = BASE_DIR / "application_tracker.json"
ARCHIVE_FILE = BASE_DIR / "archived_jobs.json"
REFRESH_STATUS_FILE = BASE_DIR / ".refresh_status.json"


# ============================================================
# PIPELINE
# ============================================================

PIPELINE = [
    "job_search.py",
    "job_verifier.py",
    "resume_matcher.py",
    "application_ranker.py",
    "application_tracker.py",
]


# ============================================================
# JSON HELPERS
# ============================================================

def load_list(path: Path) -> list:
    """
    Load a JSON file and return a list.

    Supports both:
        [...]
    and:
        {"applications": [...]}
        {"jobs": [...]}
        {"data": [...]}
    """

    if not path.exists():
        return []

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        possible_keys = [
            "applications",
            "jobs",
            "items",
            "data",
            "queue",
            "results",
        ]

        for key in possible_keys:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


def save_json(
    path: Path,
    data
) -> None:

    temporary_file = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    temporary_file.replace(path)


# ============================================================
# NORMALIZATION
# ============================================================

def clean_url(
    url
) -> str:
    """
    Normalize URLs so the same job can be recognized
    even if tracking parameters change.
    """

    if not url:
        return ""

    url = str(url).strip()

    # Remove fragment
    url = url.split(
        "#",
        1
    )[0]

    # Remove common tracking parameters
    url = re.sub(
        r"[?&]utm_[^&#]*",
        "",
        url,
        flags=re.IGNORECASE
    )

    # Clean dangling separators
    url = url.replace(
        "?&",
        "?"
    )

    url = url.rstrip(
        "?&"
    )

    return url.lower()


def normalize_text(
    value
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower()
    )


# ============================================================
# JOB IDENTITY
# ============================================================

def job_key(
    item
) -> str:
    """
    Create a stable identity for a job.

    URL is preferred.

    If URL is unavailable:
        title + company + location
    """

    if not isinstance(
        item,
        dict
    ):
        return ""

    # Some pipeline files use:
    #
    # {
    #     "job": {...},
    #     "match": {...}
    # }
    #
    # Flatten the nested job data for lookup.

    nested_job = item.get(
        "job"
    )

    if isinstance(
        nested_job,
        dict
    ):

        merged = dict(
            nested_job
        )

        merged.update(
            {
                key: value
                for key, value in item.items()
                if key != "job"
            }
        )

        item = merged

    url = clean_url(
        item.get("url")
        or item.get("apply_url")
        or item.get("application_url")
    )

    if url:

        return (
            "URL:"
            + url
        )

    title = normalize_text(
        item.get("title")
        or item.get("job_title")
    )

    company = normalize_text(
        item.get("company")
        or item.get("company_name")
    )

    location = normalize_text(
        item.get("location")
        or item.get("job_location")
    )

    return (
        "TEXT:"
        + title
        + "|"
        + company
        + "|"
        + location
    )


# ============================================================
# REFRESH PROGRESS
# ============================================================

STEP_RANGES = {
    "job_search.py": (0, 25),
    "job_verifier.py": (25, 40),
    "resume_matcher.py": (40, 58),
    "application_ranker.py": (58, 72),
    "application_tracker.py": (72, 84),
    "application_prep.py": (84, 100),
}


def save_refresh_status(data: dict) -> None:
    try:
        tmp = REFRESH_STATUS_FILE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        tmp.replace(REFRESH_STATUS_FILE)
    except OSError:
        pass


def update_refresh_status(
    status: str,
    started_at: str,
    started_monotonic: float,
    progress: float,
    step: str,
    detail: str = "",
    message: str = "",
    finished_at: str = "",
    error: str = "",
) -> None:
    progress = max(0.0, min(100.0, float(progress)))
    elapsed = max(0.0, time.monotonic() - started_monotonic)
    eta = None
    if progress >= 0.5 and status == "RUNNING":
        eta = max(0.0, elapsed * (100.0 - progress) / progress)

    save_refresh_status({
        "status": status,
        "progress": round(progress, 1),
        "step": step,
        "detail": detail,
        "message": message,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": round(elapsed, 1),
        "eta_seconds": round(eta, 1) if eta is not None else None,
        "error": error,
        "process_pid": os.getpid(),
        "heartbeat_at": datetime.now().isoformat(timespec="seconds"),
    })


def run_step(
    script_name: str,
    started_at: str,
    started_monotonic: float,
) -> None:
    print()
    print("=" * 90)
    print(f"RUNNING: {script_name}")
    print("=" * 90)

    range_start, range_end = STEP_RANGES[script_name]

    update_refresh_status(
        "RUNNING",
        started_at,
        started_monotonic,
        range_start,
        script_name,
        "Starting...",
        f"Running {script_name}",
    )

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(BASE_DIR / script_name),
        ],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    last_progress = float(range_start)
    last_detail = "Starting..."
    stop_heartbeat = threading.Event()

    def heartbeat():
        nonlocal last_progress, last_detail

        while not stop_heartbeat.wait(2.0):
            if process.poll() is not None:
                break

            elapsed = time.monotonic() - started_monotonic

            # Keep the dashboard visibly alive while a child process is
            # doing work without printing output. Never cross the step's
            # real upper boundary here.
            gentle = min(
                float(range_end - 0.2),
                range_start + min(
                    max(0.5, elapsed / 30.0),
                    max(0.5, (range_end - range_start) * 0.35),
                ),
            )

            if gentle > last_progress:
                last_progress = gentle

            update_refresh_status(
                "RUNNING",
                started_at,
                started_monotonic,
                last_progress,
                script_name,
                last_detail,
                f"Running {script_name}",
            )

    heartbeat_thread = threading.Thread(
        target=heartbeat,
        daemon=True,
    )
    heartbeat_thread.start()

    try:
        if process.stdout is not None:
            for raw_line in process.stdout:
                line = raw_line.rstrip("\n")
                print(line, flush=True)

                detail = line.strip() or last_detail
                progress = last_progress

                # job_search.py prints lines such as:
                # Offset 500: 100 jobs / 1013 available
                if script_name == "job_search.py":
                    match = re.search(
                        r"Offset\s+(\d+).*?([\d,]+)\s+available",
                        line,
                        flags=re.IGNORECASE,
                    )

                    if match:
                        offset = int(match.group(1))
                        available = int(
                            match.group(2).replace(",", "")
                        )

                        if available > 0:
                            fraction = min(
                                1.0,
                                (offset + 100) / available,
                            )
                            progress = (
                                range_start
                                + fraction
                                * (range_end - range_start)
                            )
                            detail = (
                                "Searching jobs: "
                                f"{min(offset + 100, available):,}"
                                f" / {available:,}"
                            )

                progress = min(
                    float(range_end - 0.1),
                    max(progress, range_start),
                )
                last_progress = max(
                    last_progress,
                    progress,
                )
                last_detail = detail

                update_refresh_status(
                    "RUNNING",
                    started_at,
                    started_monotonic,
                    last_progress,
                    script_name,
                    last_detail,
                    f"Running {script_name}",
                )

        return_code = process.wait()

    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1.0)

    if return_code != 0:
        update_refresh_status(
            "FAILED",
            started_at,
            started_monotonic,
            last_progress,
            script_name,
            f"Exit code {return_code}",
            f"{script_name} failed",
            finished_at=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            error=(
                f"{script_name} failed "
                f"with exit code {return_code}"
            ),
        )
        raise RuntimeError(
            f"{script_name} failed "
            f"with exit code {return_code}"
        )

    update_refresh_status(
        "RUNNING",
        started_at,
        started_monotonic,
        range_end,
        script_name,
        "Completed",
        f"{script_name} completed",
    )


# ============================================================
# PRESERVE APPLICATION HISTORY
# ============================================================

def preserve_history(
    old_active: list,
    old_archive: list,
    new_active: list,
):
    """
    Refresh policy:

    * Every job that was ACTIVE before a refresh is moved to archive.
    * Existing archive is preserved.
    * Only genuinely unseen jobs become ACTIVE.
    * Application status/history is preserved in the archive.
    * Old jobs are never deleted.
    """

    now = datetime.now().isoformat(timespec="seconds")

    history_fields = [
        "application_id",
        "status",
        "application_status",
        "workflow_status",
        "status_updated_at",
        "notes",
        "applied_at",
        "interview_at",
        "accepted_at",
        "rejected_at",
    ]

    history = {}
    for item in old_archive + old_active:
        key = job_key(item)
        if key:
            history[key] = item

    archived_by_key = {}
    for item in old_archive:
        key = job_key(item)
        if key:
            archived_by_key[key] = dict(item)

    # Archive everything that was previously active.
    newly_archived = 0
    for item in old_active:
        if not isinstance(item, dict):
            continue

        key = job_key(item)
        if not key:
            continue

        record = dict(item)
        record["job_state"] = "ARCHIVED"
        record["archived_at"] = now
        if not record.get("last_seen_at"):
            record["last_seen_at"] = now

        archived_by_key[key] = record
        newly_archived += 1

    merged_active = []
    new_count = 0
    skipped_existing = 0

    for item in new_active:
        if not isinstance(item, dict):
            continue

        key = job_key(item)
        if not key:
            continue

        # If the job existed before this refresh, keep it archived rather
        # than allowing the pipeline to repopulate the ACTIVE list.
        if key in history:
            skipped_existing += 1

            previous = history[key]
            record = dict(
                archived_by_key.get(key, previous)
            )

            for field in history_fields:
                if field in previous:
                    record[field] = previous[field]

            record["job_state"] = "ARCHIVED"
            record.setdefault("archived_at", now)
            archived_by_key[key] = record
            continue

        record = dict(item)
        record["job_state"] = "ACTIVE"
        record["first_seen_at"] = now
        record["last_seen_at"] = now
        record["status"] = "NOT APPLIED"
        record["application_status"] = "NOT APPLIED"
        record["workflow_status"] = "NOT APPLIED"

        merged_active.append(record)
        new_count += 1

    return (
        merged_active,
        list(archived_by_key.values()),
        skipped_existing,
        new_count,
        newly_archived,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    started_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    started_monotonic = time.monotonic()

    update_refresh_status(
        "RUNNING",
        started_at,
        started_monotonic,
        0,
        "Preparing",
        "Loading previous application history...",
        "Preparing refresh",
    )

    print()
    print(
        "=" * 95
    )

    print(
        "                         AI JOB HUNTER"
    )

    print(
        "                    MASTER JOB REFRESH"
    )

    print(
        "=" * 95
    )

    print()

    print(
        "This will run:"
    )

    print(
        "  job_search.py"
            )

    print(
        "       ↓"
    )

    print(
        "  job_verifier.py"
    )

    print(
        "       ↓"
    )

    print(
        "  resume_matcher.py"
    )

    print(
        "       ↓"
    )

    print(
        "  application_ranker.py"
    )

    print(
        "       ↓"
    )

    print(
        "  application_tracker.py"
    )

    print(
        "       ↓"
    )

    print(
        "  application_prep.py"
    )

    print()

    # ========================================================
    # STEP 1
    # Load old history BEFORE running anything.
    # ========================================================

    old_active = load_list(
        TRACKER_FILE
    )

    old_archive = load_list(
        ARCHIVE_FILE
    )

    print(
        f"Existing active applications: "
        f"{len(old_active)}"
    )

    print(
        f"Existing archived jobs: "
        f"{len(old_archive)}"
    )

    print()

    # ========================================================
    # STEP 2
    # Run pipeline
    # ========================================================

    for script in PIPELINE:

        run_step(
            script,
            started_at,
            started_monotonic,
        )

    # ========================================================
    # STEP 3
    # Load freshly generated tracker
    # ========================================================

    new_active = load_list(
        TRACKER_FILE
    )

    if not new_active:

        raise RuntimeError(
            "Pipeline completed, "
            "but application_tracker.json "
            "is empty or missing."
        )

    print()
    print(
        "=" * 90
    )

    print(
        "MERGING APPLICATION HISTORY"
    )

    print(
        "=" * 90
    )

    # ========================================================
    # STEP 4
    # Preserve history + archive disappeared jobs
    # ========================================================

    (
        merged_active,
        merged_archive,
        restored_count,
        new_count,
        newly_archived,
    ) = preserve_history(
        old_active,
        old_archive,
        new_active
    )

    # ========================================================
    # STEP 5
    # Save active tracker
    # ========================================================

    save_json(
        TRACKER_FILE,
        merged_active
    )

    # ========================================================
    # STEP 6
    # Save archive
    # ========================================================

    save_json(
        ARCHIVE_FILE,
        merged_archive
    )

    # ========================================================
    # STEP 7
    # Prepare applications
    # ========================================================

    run_step(
        "application_prep.py",
        started_at,
        started_monotonic,
    )

    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_refresh_status(
        "SUCCESS",
        started_at,
        started_monotonic,
        100,
        "Complete",
        "All jobs refreshed and application history preserved.",
        "Job refresh completed successfully.",
        finished_at=finished_at,
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 95
    )

    print(
        "                     REFRESH COMPLETE"
    )

    print(
        "=" * 95
    )

    print()

    print(
        f"Started:                  {started_at}"
    )

    print(
        f"Finished:                 "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print()

    print(
        f"Active jobs:              "
        f"{len(merged_active)}"
    )

    print(
        f"Existing applications:    "
        f"{restored_count}"
    )

    print(
        f"New jobs:                 "
        f"{new_count}"
    )

    print(
        f"Newly archived:           "
        f"{newly_archived}"
    )

    print(
        f"Archived jobs total:      "
        f"{len(merged_archive)}"
    )

    print()

    print(
        f"Active tracker:           "
        f"{TRACKER_FILE.name}"
    )

    print(
        f"Archive:                  "
        f"{ARCHIVE_FILE.name}"
    )

    print()

    print(
        "Your application statuses "
        "have been preserved."
    )

    print()

    print(
        "Next time, you only need to run:"
    )

    print()

    print(
        "    python refresh_jobs.py"
    )

    print()

    print(
        "=" * 95
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()