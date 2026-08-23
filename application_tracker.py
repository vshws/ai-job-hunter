import json
import os
import sys
from datetime import datetime, date


# ============================================================
# FILES
# ============================================================

QUEUE_FILE = "application_queue.json"
TRACKER_FILE = "application_tracker.json"
REPORT_FILE = "application_tracker.txt"


# ============================================================
# JOBS WE WANT TO TRACK
# ============================================================

TRACK_CATEGORIES = {
    "APPLY NOW",
    "APPLY",
    "STRONG APPLY",
}


# ============================================================
# VALID STATUSES
# ============================================================

VALID_APPLICATION_STATUSES = {
    "NOT APPLIED",
    "APPLIED",
    "SCREENING",
    "INTERVIEW",
    "FINAL ROUND",
    "OFFER",
    "REJECTED",
    "WITHDRAWN",
}


VALID_INTERVIEW_STATUSES = {
    "NOT STARTED",
    "SCHEDULED",
    "COMPLETED",
    "PASSED",
    "FAILED",
}


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            clean(x) for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            clean(v)
            for v in value.values()
        )

    return str(value).strip()


def normalize(value):
    return clean(value).lower().strip()


def today():
    return date.today().isoformat()


def now():
    return datetime.now().isoformat(timespec="seconds")


def safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# LOAD JSON
# ============================================================

def load_json(filename):

    if not os.path.exists(filename):
        return []

    try:
        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except Exception as error:

        print(
            f"ERROR reading {filename}: {error}"
        )

        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        for key in [
            "applications",
            "jobs",
            "queue",
            "results",
            "data",
        ]:

            if isinstance(
                data.get(key),
                list
            ):

                return data[key]

    return []


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# JOB KEY
# ============================================================

def job_key(job):

    url = normalize(
        job.get("url")
    )

    if url:

        # Remove tracking parameters
        return url.split("?")[0]

    return (
        normalize(job.get("company"))
        + "|"
        + normalize(job.get("title"))
        + "|"
        + normalize(job.get("location"))
    )


# ============================================================
# CREATE TRACKER ENTRY
# ============================================================

def create_entry(job, app_id):

    return {

        "id": app_id,

        "priority": safe_float(
            job.get("priority")
        ),

        "category": clean(
            job.get("category")
        ),

        "title": clean(
            job.get("title")
        ),

        "company": clean(
            job.get("company")
        ),

        "location": clean(
            job.get("location")
        ),

        "url": clean(
            job.get("url")
        ),

        "match_score": safe_float(
            job.get("match_score")
        ),

        "your_experience": safe_float(
            job.get("your_experience")
        ),

        "experience_required": safe_float(
            job.get("experience_required")
        ),

        "experience_status": clean(
            job.get("experience_status")
        ),

        "matched_skills": job.get(
            "matched_skills",
            []
        ),

        "missing_skills": job.get(
            "missing_skills",
            []
        ),

        # ----------------------------------------------------
        # APPLICATION DATA
        # ----------------------------------------------------

        "application_status":
            "NOT APPLIED",

        "date_applied":
            None,

        "resume_version":
            "MAIN",

        "interview_status":
            "NOT STARTED",

        "interview_date":
            None,

        "follow_up_date":
            None,

        "recruiter_contact":
            "",

        "notes":
            "",

        "created_at":
            now(),

        "last_updated":
            now(),
    }


# ============================================================
# LOAD EXISTING TRACKER
# ============================================================

def load_existing_tracker():

    if not os.path.exists(
        TRACKER_FILE
    ):

        return []

    data = load_json(
        TRACKER_FILE
    )

    if not isinstance(
        data,
        list
    ):

        return []

    return data


# ============================================================
# MERGE NEW JOBS WITHOUT RESETTING HISTORY
# ============================================================

def merge_jobs(
    existing,
    queue
):

    # --------------------------------------------------------
    # Existing jobs indexed by URL/title/company.
    # --------------------------------------------------------

    existing_by_key = {}

    for entry in existing:

        key = job_key(
            entry
        )

        if key:
            existing_by_key[key] = entry

    # --------------------------------------------------------
    # Find highest existing APP number.
    # --------------------------------------------------------

    highest_id = 0

    for entry in existing:

        app_id = clean(
            entry.get("id")
        )

        if app_id.startswith(
            "APP-"
        ):

            try:

                number = int(
                    app_id.replace(
                        "APP-",
                        ""
                    )
                )

                highest_id = max(
                    highest_id,
                    number
                )

            except ValueError:
                pass

    new_count = 0
    updated_count = 0

    # --------------------------------------------------------
    # Add / update jobs.
    # --------------------------------------------------------

    for job in queue:

        category = clean(
            job.get("category")
        )

        if category not in TRACK_CATEGORIES:
            continue

        key = job_key(
            job
        )

        if not key:
            continue

        # ----------------------------------------------------
        # Existing job:
        # Update job information but PRESERVE
        # application history.
        # ----------------------------------------------------

        if key in existing_by_key:

            old = existing_by_key[key]

            old["priority"] = safe_float(
                job.get("priority")
            )

            old["category"] = clean(
                job.get("category")
            )

            old["title"] = clean(
                job.get("title")
            )

            old["company"] = clean(
                job.get("company")
            )

            old["location"] = clean(
                job.get("location")
            )

            old["url"] = clean(
                job.get("url")
            )

            old["match_score"] = safe_float(
                job.get("match_score")
            )

            old["your_experience"] = safe_float(
                job.get("your_experience")
            )

            old["experience_required"] = safe_float(
                job.get("experience_required")
            )

            old["experience_status"] = clean(
                job.get("experience_status")
            )

            old["matched_skills"] = job.get(
                "matched_skills",
                []
            )

            old["missing_skills"] = job.get(
                "missing_skills",
                []
            )

            old["last_updated"] = now()

            updated_count += 1

        else:

            highest_id += 1

            entry = create_entry(
                job,
                f"APP-{highest_id:04d}"
            )

            existing.append(
                entry
            )

            existing_by_key[key] = entry

            new_count += 1

    return (
        existing,
        new_count,
        updated_count
    )


# ============================================================
# FIND APPLICATION
# ============================================================

def find_application(
    applications,
    app_id
):

    for app in applications:

        if normalize(
            app.get("id")
        ) == normalize(
            app_id
        ):

            return app

    return None


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

def update_status(
    applications,
    app_id,
    status
):

    status = status.upper()

    if status not in VALID_APPLICATION_STATUSES:

        print()

        print(
            "Invalid application status."
        )

        print()

        print(
            "Valid statuses:"
        )

        for item in sorted(
            VALID_APPLICATION_STATUSES
        ):

            print(
                f"  {item}"
            )

        return False

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return False

    app[
        "application_status"
    ] = status

    if status == "APPLIED":

        if not app.get(
            "date_applied"
        ):

            app[
                "date_applied"
            ] = today()

    if status in {
        "INTERVIEW",
        "FINAL ROUND",
    }:

        if app.get(
            "interview_status"
        ) == "NOT STARTED":

            app[
                "interview_status"
            ] = "SCHEDULED"

    if status == "OFFER":

        app[
            "interview_status"
        ] = "PASSED"

    if status == "REJECTED":

        app[
            "interview_status"
        ] = "FAILED"

    app[
        "last_updated"
    ] = now()

    print()

    print(
        f"{app_id} updated."
    )

    print(
        f"Status: {status}"
    )

    return True


# ============================================================
# MARK AS APPLIED
# ============================================================

def mark_applied(
    applications,
    app_id
):

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return False

    app[
        "application_status"
    ] = "APPLIED"

    app[
        "date_applied"
    ] = today()

    app[
        "last_updated"
    ] = now()

    print()

    print(
        f"✓ {app_id} marked as APPLIED."
    )

    print(
        f"Date applied: "
        f"{app['date_applied']}"
    )

    return True


# ============================================================
# UPDATE INTERVIEW STATUS
# ============================================================

def update_interview(
    applications,
    app_id,
    interview_status
):

    interview_status = (
        interview_status.upper()
    )

    if interview_status not in VALID_INTERVIEW_STATUSES:

        print()

        print(
            "Invalid interview status."
        )

        print()

        print(
            "Valid statuses:"
        )

        for item in sorted(
            VALID_INTERVIEW_STATUSES
        ):

            print(
                f"  {item}"
            )

        return False

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return False

    app[
        "interview_status"
    ] = interview_status

    if interview_status == "SCHEDULED":

        if not app.get(
            "application_status"
        ) in {
            "REJECTED",
            "OFFER",
        }:

            app[
                "application_status"
            ] = "INTERVIEW"

    if interview_status == "PASSED":

        app[
            "application_status"
        ] = "FINAL ROUND"

    if interview_status == "FAILED":

        app[
            "application_status"
        ] = "REJECTED"

    app[
        "last_updated"
    ] = now()

    print()

    print(
        f"✓ {app_id} interview updated."
    )

    print(
        f"Interview: "
        f"{interview_status}"
    )

    return True


# ============================================================
# UPDATE FOLLOW-UP DATE
# ============================================================

def update_followup(
    applications,
    app_id,
    follow_up_date
):

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return False

    app[
        "follow_up_date"
    ] = follow_up_date

    app[
        "last_updated"
    ] = now()

    print()

    print(
        f"✓ Follow-up date updated."
    )

    print(
        f"{app_id}: "
        f"{follow_up_date}"
    )

    return True


# ============================================================
# UPDATE NOTES
# ============================================================

def update_notes(
    applications,
    app_id,
    notes
):

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return False

    app[
        "notes"
    ] = notes

    app[
        "last_updated"
    ] = now()

    print()

    print(
        f"✓ Notes updated for {app_id}."
    )

    return True


# ============================================================
# SHOW ONE APPLICATION
# ============================================================

def show_application(
    applications,
    app_id
):

    app = find_application(
        applications,
        app_id
    )

    if app is None:

        print(
            f"Application {app_id} not found."
        )

        return

    print()

    print(
        "=" * 90
    )

    print(
        f"{app['id']} - "
        f"{app['title']}"
    )

    print(
        "=" * 90
    )

    print(
        f"Company: "
        f"{app['company']}"
    )

    print(
        f"Location: "
        f"{app['location']}"
    )

    print(
        f"Match Score: "
        f"{app['match_score']}/100"
    )

    print(
        f"Priority: "
        f"{app['priority']}"
    )

    print(
        f"Experience: "
        f"{app['experience_required']} required "
        f"vs {app['your_experience']}"
    )

    print(
        f"Application Status: "
        f"{app['application_status']}"
    )

    print(
        f"Date Applied: "
        f"{app['date_applied']}"
    )

    print(
        f"Resume Version: "
        f"{app['resume_version']}"
    )

    print(
        f"Interview Status: "
        f"{app['interview_status']}"
    )

    print(
        f"Interview Date: "
        f"{app['interview_date']}"
    )

    print(
        f"Follow-up Date: "
        f"{app['follow_up_date']}"
    )

    print(
        f"Recruiter: "
        f"{app['recruiter_contact']}"
    )

    print(
        f"Notes: "
        f"{app['notes']}"
    )

    print()

    print(
        f"URL: "
        f"{app['url']}"
    )

    print(
        "=" * 90
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    applications
):

    print()

    print(
        "=" * 90
    )

    print(
        "                         APPLICATION SUMMARY"
    )

    print(
        "=" * 90
    )

    statuses = [
        "NOT APPLIED",
        "APPLIED",
        "SCREENING",
        "INTERVIEW",
        "FINAL ROUND",
        "OFFER",
        "REJECTED",
        "WITHDRAWN",
    ]

    for status in statuses:

        count = sum(
            1
            for app in applications
            if app.get(
                "application_status"
            ) == status
        )

        print(
            f"{status:<15}: {count}"
        )

    print()

    print(
        "=" * 90
    )


# ============================================================
# REPORT
# ============================================================

def generate_report(
    applications
):

    lines = []

    lines.append(
        "=" * 100
    )

    lines.append(
        "                         APPLICATION TRACKER"
    )

    lines.append(
        "=" * 100
    )

    lines.append("")

    lines.append(
        f"Total applications: "
        f"{len(applications)}"
    )

    lines.append("")

    # --------------------------------------------------------
    # Status summary
    # --------------------------------------------------------

    statuses = [
        "NOT APPLIED",
        "APPLIED",
        "SCREENING",
        "INTERVIEW",
        "FINAL ROUND",
        "OFFER",
        "REJECTED",
        "WITHDRAWN",
    ]

    lines.append(
        "APPLICATION STATUS"
    )

    lines.append(
        "-" * 100
    )

    for status in statuses:

        count = sum(
            1
            for app in applications
            if app.get(
                "application_status"
            ) == status
        )

        lines.append(
            f"{status}: {count}"
        )

    lines.append("")

    # --------------------------------------------------------
    # Applications
    # --------------------------------------------------------

    lines.append(
        "=" * 100
    )

    lines.append(
        "                         APPLICATIONS"
    )

    lines.append(
        "=" * 100
    )

    for app in applications:

        lines.append("")

        lines.append(
            f"{app['id']} | "
            f"{app['application_status']}"
        )

        lines.append(
            f"TITLE: "
            f"{app['title']}"
        )

        lines.append(
            f"COMPANY: "
            f"{app['company']}"
        )

        lines.append(
            f"LOCATION: "
            f"{app['location']}"
        )

        lines.append(
            f"MATCH SCORE: "
            f"{app['match_score']}/100"
        )

        lines.append(
            f"PRIORITY: "
            f"{app['priority']}"
        )

        lines.append(
            f"DATE APPLIED: "
            f"{app['date_applied']}"
        )

        lines.append(
            f"RESUME: "
            f"{app['resume_version']}"
        )

        lines.append(
            f"INTERVIEW: "
            f"{app['interview_status']}"
        )

        lines.append(
            f"FOLLOW-UP: "
            f"{app['follow_up_date']}"
        )

        lines.append(
            f"NOTES: "
            f"{app['notes']}"
        )

        lines.append(
            f"URL: "
            f"{app['url']}"
        )

        lines.append(
            "-" * 100
        )

    return "\n".join(
        lines
    )


# ============================================================
# SAVE EVERYTHING
# ============================================================

def save_all(
    applications
):

    save_json(
        TRACKER_FILE,
        applications
    )

    report = generate_report(
        applications
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )


# ============================================================
# COMMAND HELP
# ============================================================

def print_help():

    print()

    print(
        "=" * 90
    )

    print(
        "                    APPLICATION TRACKER COMMANDS"
    )

    print(
        "=" * 90
    )

    print()

    print(
        "Create / update tracker:"
    )

    print(
        "  python application_tracker.py"
    )

    print()

    print(
        "Mark application as applied:"
    )

    print(
        "  python application_tracker.py --apply APP-0001"
    )

    print()

    print(
        "Change application status:"
    )

    print(
        "  python application_tracker.py --status APP-0001 INTERVIEW"
    )

    print()

    print(
        "Update interview status:"
    )

    print(
        "  python application_tracker.py --interview APP-0001 SCHEDULED"
    )

    print()

    print(
        "Set follow-up date:"
    )

    print(
        "  python application_tracker.py --followup APP-0001 2026-08-25"
    )

    print()

    print(
        "Add notes:"
    )

    print(
        '  python application_tracker.py --notes APP-0001 "Applied through referral"'
    )

    print()

    print(
        "Show one application:"
    )

    print(
        "  python application_tracker.py --show APP-0001"
    )

    print()

    print(
        "Show summary:"
    )

    print(
        "  python application_tracker.py --summary"
    )

    print()

    print(
        "=" * 90
    )


# ============================================================
# COMMAND PROCESSING
# ============================================================

def handle_command(
    applications,
    args
):

    if len(args) == 0:

        return False

    command = args[0].lower()

    # --------------------------------------------------------
    # --help
    # --------------------------------------------------------

    if command in {
        "--help",
        "-h",
    }:

        print_help()

        return True

    # --------------------------------------------------------
    # --summary
    # --------------------------------------------------------

    if command == "--summary":

        print_summary(
            applications
        )

        return True

    # --------------------------------------------------------
    # --show
    # --------------------------------------------------------

    if command == "--show":

        if len(args) < 2:

            print(
                "Usage: "
                "python application_tracker.py "
                "--show APP-0001"
            )

            return True

        show_application(
            applications,
            args[1]
        )

        return True

    # --------------------------------------------------------
    # --apply
    # --------------------------------------------------------

    if command == "--apply":

        if len(args) < 2:

            print(
                "Usage: "
                "python application_tracker.py "
                "--apply APP-0001"
            )

            return True

        changed = mark_applied(
            applications,
            args[1]
        )

        if changed:

            save_all(
                applications
            )

        return True

    # --------------------------------------------------------
    # --status
    # --------------------------------------------------------

    if command == "--status":

        if len(args) < 3:

            print(
                "Usage: "
                "python application_tracker.py "
                "--status APP-0001 INTERVIEW"
            )

            return True

        changed = update_status(
            applications,
            args[1],
            " ".join(args[2:])
        )

        if changed:

            save_all(
                applications
            )

        return True

    # --------------------------------------------------------
    # --interview
    # --------------------------------------------------------

    if command == "--interview":

        if len(args) < 3:

            print(
                "Usage: "
                "python application_tracker.py "
                "--interview APP-0001 SCHEDULED"
            )

            return True

        changed = update_interview(
            applications,
            args[1],
            " ".join(args[2:])
        )

        if changed:

            save_all(
                applications
            )

        return True

    # --------------------------------------------------------
    # --followup
    # --------------------------------------------------------

    if command == "--followup":

        if len(args) < 3:

            print(
                "Usage: "
                "python application_tracker.py "
                "--followup APP-0001 2026-08-25"
            )

            return True

        changed = update_followup(
            applications,
            args[1],
            args[2]
        )

        if changed:

            save_all(
                applications
            )

        return True

    # --------------------------------------------------------
    # --notes
    # --------------------------------------------------------

    if command == "--notes":

        if len(args) < 3:

            print(
                "Usage: "
                'python application_tracker.py '
                '--notes APP-0001 "Your notes"'
            )

            return True

        notes = " ".join(
            args[2:]
        )

        changed = update_notes(
            applications,
            args[1],
            notes
        )

        if changed:

            save_all(
                applications
            )

        return True

    print(
        f"Unknown command: {command}"
    )

    print_help()

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load application queue.
    # --------------------------------------------------------

    queue = load_json(
        QUEUE_FILE
    )

    # --------------------------------------------------------
    # Load existing tracker.
    # --------------------------------------------------------

    existing = load_existing_tracker()

    # --------------------------------------------------------
    # If a command is provided, use existing tracker first.
    # --------------------------------------------------------

    if len(sys.argv) > 1:

        if not existing:

            print(
                "ERROR: application_tracker.json "
                "does not exist yet."
            )

            print(
                "Run this first:"
            )

            print(
                "python application_tracker.py"
            )

            return

        handle_command(
            existing,
            sys.argv[1:]
        )

        return

    # --------------------------------------------------------
    # Normal tracker build/update.
    # --------------------------------------------------------

    print()

    print(
        "=" * 100
    )

    print(
        "                         APPLICATION TRACKER"
    )

    print(
        "=" * 100
    )

    print()

    print(
        f"Application queue loaded: "
        f"{len(queue)}"
    )

    print(
        f"Existing tracked applications: "
        f"{len(existing)}"
    )

    # --------------------------------------------------------
    # Merge queue with existing tracker.
    # --------------------------------------------------------

    applications, new_count, updated_count = (
        merge_jobs(
            existing,
            queue
        )
    )

    # --------------------------------------------------------
    # Sort by priority.
    # --------------------------------------------------------

    applications.sort(
        key=lambda x:
            x.get("priority")
            if x.get("priority") is not None
            else 0,
        reverse=True
    )

    # --------------------------------------------------------
    # Save.
    # --------------------------------------------------------

    save_all(
        applications
    )

    print()

    print(
        "=" * 100
    )

    print(
        "                    APPLICATION TRACKER READY"
    )

    print(
        "=" * 100
    )

    print()

    print(
        f"New applications added: "
        f"{new_count}"
    )

    print(
        f"Existing applications updated: "
        f"{updated_count}"
    )

    print(
        f"Total applications tracked: "
        f"{len(applications)}"
    )

    print()

    print_summary(
        applications
    )

    print()

    print(
        f"JSON saved: "
        f"{TRACKER_FILE}"
    )

    print(
        f"Report saved: "
        f"{REPORT_FILE}"
    )

    print()

    # --------------------------------------------------------
    # Show top NOT APPLIED jobs.
    # --------------------------------------------------------

    pending = [
        app
        for app in applications
        if app.get(
            "application_status"
        ) == "NOT APPLIED"
    ]

    print(
        "=" * 100
    )

    print(
        "                         NEXT APPLICATIONS"
    )

    print(
        "=" * 100
    )

    for index, app in enumerate(
        pending[:15],
        1
    ):

        print()

        print(
            f"{index}. "
            f"[{app['id']}] "
            f"{app['title']}"
        )

        print(
            f"   Company: "
            f"{app['company']}"
        )

        print(
            f"   Match: "
            f"{app['match_score']}/100"
        )

        print(
            f"   Priority: "
            f"{app['priority']}"
        )

        print(
            f"   URL: "
            f"{app['url']}"
        )

    print()

    print(
        "=" * 100
    )

    print(
        "Done."
    )

    print()

    print(
        "After applying, use:"
    )

    print(
        "python application_tracker.py --apply APP-0001"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()