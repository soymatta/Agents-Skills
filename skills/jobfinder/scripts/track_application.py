#!/usr/bin/env python3
"""Track job applications in a CSV file."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

TRACKER_FILE = "job_search_tracker.csv"
HEADERS = ["company", "role", "date_applied", "status", "source",
           "cv_file", "cover_letter_file", "notes"]


def init_tracker(tracker_path: str = TRACKER_FILE) -> Path:
    """Create tracker CSV if it doesn't exist."""
    path = Path(tracker_path)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
    return path


def add_application(company: str, role: str, source: str = "",
                    cv_file: str = "", cover_letter_file: str = "",
                    notes: str = "", tracker_path: str = TRACKER_FILE) -> None:
    """Add a new application to the tracker."""
    path = init_tracker(tracker_path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            company, role, datetime.now().strftime("%Y-%m-%d"),
            "applied", source, cv_file, cover_letter_file, notes
        ])
    print(f"  Tracked: {role} at {company}")


def update_status(company: str, role: str, status: str,
                  notes: str = "", tracker_path: str = TRACKER_FILE) -> bool:
    """Update the status of an application."""
    path = Path(tracker_path)
    if not path.exists():
        return False

    rows = []
    updated = False
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["company"] == company and row["role"] == role:
                row["status"] = status
                if notes:
                    row["notes"] = notes
                updated = True
            rows.append(row)

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Updated: {role} at {company} -> {status}")
    return updated


def list_applications(status_filter: str = "", tracker_path: str = TRACKER_FILE) -> list[dict]:
    """List all applications, optionally filtered by status."""
    path = Path(tracker_path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        apps = list(reader)

    if status_filter:
        apps = [a for a in apps if a["status"] == status_filter]
    return apps


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Track job applications")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add application")
    add_p.add_argument("--company", required=True)
    add_p.add_argument("--role", required=True)
    add_p.add_argument("--source", default="")
    add_p.add_argument("--cv", default="")
    add_p.add_argument("--cover-letter", default="")
    add_p.add_argument("--notes", default="")

    update_p = sub.add_parser("update", help="Update status")
    update_p.add_argument("--company", required=True)
    update_p.add_argument("--role", required=True)
    update_p.add_argument("--status", required=True)
    update_p.add_argument("--notes", default="")

    list_p = sub.add_parser("list", help="List applications")
    list_p.add_argument("--status", default="")

    args = parser.parse_args()

    if args.command == "add":
        add_application(args.company, args.role, args.source,
                        args.cv, args.cover_letter, args.notes)
    elif args.command == "update":
        update_status(args.company, args.role, args.status, args.notes)
    elif args.command == "list":
        apps = list_applications(args.status)
        for app in apps:
            print(f"  [{app['status']}] {app['role']} @ {app['company']} ({app['date_applied']})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
