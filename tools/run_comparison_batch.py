"""
tools/run_comparison_batch.py - Phase 10: Comparison Batch Execution Script

Runs core.comparison.compare() across 10 roles with 11 synthetic employees per role
(110 total comparison evaluation cases).

Exports results to reports/genai_python_comparison_report.csv with 8 standard columns:
  employee_id, role, coverage_score, traceability_score, overall_status,
  flag_count, flag_types, timestamp

Features:
  - Resumable: Skips employee_ids already present in output CSV.
  - Robust CSV Writing: Uses csv.DictWriter with safe field escaping.
  - Graceful Error Handling: Catches individual exceptions, logs "Generation Failed",
    writes clean row to CSV without unescaped raw error strings, and continues.
  - Rate-Limit Aware: 1.5s delay between API calls.
  - Progress Output: Prints "Case X/110: EMP-ID / Role -> Status".
"""

import sys
import os
import csv
import time
from datetime import datetime

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.comparison import compare
from core.db import setup_db, load_matrix

ROLES = [
    "Sales Executive",
    "Customer Support Executive",
    "HR Executive",
    "Finance Associate",
    "Operations Coordinator",
    "Marketing Executive",
    "Software Support Engineer",
    "Branch/Team Manager",
    "Data Analyst",
    "DevOps/IT Engineer",
]

SAMPLES_PER_ROLE = 11
DELAY_BETWEEN_CALLS = 1.5  # seconds pause between API calls

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "reports",
    "genai_python_comparison_report.csv",
)


def generate_employee_batch():
    """Generate structured list of (employee_id, role) tuples across all 10 roles."""
    batch = []
    role_slugs = {
        "Sales Executive": "SE",
        "Customer Support Executive": "CS",
        "HR Executive": "HR",
        "Finance Associate": "FA",
        "Operations Coordinator": "OC",
        "Marketing Executive": "ME",
        "Software Support Engineer": "SS",
        "Branch/Team Manager": "BM",
        "Data Analyst": "DA",
        "DevOps/IT Engineer": "DE",
    }
    for role in ROLES:
        slug = role_slugs.get(role, "EMP")
        for i in range(1, SAMPLES_PER_ROLE + 1):
            emp_id = f"EMP-{slug}-{i:03d}"
            batch.append((emp_id, role))
    return batch


def load_processed_ids(csv_file_path):
    """Read set of already processed employee_ids from output CSV for resumption support."""
    processed = set()
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("employee_id"):
                    processed.add(row["employee_id"])
    return processed


def run_batch():
    print("=" * 70)
    print("SkillSprint AI - Phase 10: Comparison Batch Execution")
    print("=" * 70)

    # Initialize DB tables and load Ground-Truth Requirement Matrix
    setup_db()
    matrix_csv = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "role_requirement_matrix.csv",
    )
    if os.path.exists(matrix_csv):
        load_matrix(matrix_csv)

    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    processed_ids = load_processed_ids(CSV_PATH)
    file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0

    batch = generate_employee_batch()
    total_cases = len(batch)

    print(f"Total target cases: {total_cases}")
    print(f"Already processed:  {len(processed_ids)}")
    print(f"Output CSV path:   {CSV_PATH}")
    print("-" * 70)

    fieldnames = [
        "employee_id",
        "role",
        "coverage_score",
        "traceability_score",
        "overall_status",
        "flag_count",
        "flag_types",
        "timestamp",
    ]

    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
            f.flush()

        completed_in_run = 0
        failed_in_run = 0

        for idx, (emp_id, role) in enumerate(batch, start=1):
            if emp_id in processed_ids:
                print(f"Case {idx}/{total_cases}: {emp_id} / {role} -> SKIPPED (Already in CSV)")
                continue

            timestamp = datetime.now().isoformat()
            try:
                res = compare(emp_id, role)
                p2 = res.get("pipeline2_output") or {}

                coverage_score = float(p2.get("coverage_score", 0.0)) if p2 else 0.0
                traceability_score = float(p2.get("traceability_score", 0.0)) if p2 else 0.0
                overall_status = res.get("overall_status", "Generation Failed")

                flags = p2.get("flags", []) if isinstance(p2.get("flags"), list) else []
                flag_count = len(flags)
                flag_types_list = sorted(list(set(f.get("type", "") for f in flags if f.get("type"))))
                flag_types_str = ";".join(flag_types_list)

                writer.writerow({
                    "employee_id": emp_id,
                    "role": role,
                    "coverage_score": round(coverage_score, 2),
                    "traceability_score": round(traceability_score, 2),
                    "overall_status": overall_status,
                    "flag_count": flag_count,
                    "flag_types": flag_types_str,
                    "timestamp": timestamp,
                })
                f.flush()
                completed_in_run += 1

                print(f"Case {idx}/{total_cases}: {emp_id} / {role} -> {overall_status}")

            except Exception as e:
                failed_in_run += 1
                print(f"Case {idx}/{total_cases}: {emp_id} / {role} -> Generation Failed (Error: {e})")
                writer.writerow({
                    "employee_id": emp_id,
                    "role": role,
                    "coverage_score": 0.0,
                    "traceability_score": 0.0,
                    "overall_status": "Generation Failed",
                    "flag_count": 0,
                    "flag_types": "ScriptError",
                    "timestamp": timestamp,
                })
                f.flush()

            time.sleep(DELAY_BETWEEN_CALLS)

    print("=" * 70)
    print("Batch Run Summary:")
    print(f"  Newly completed: {completed_in_run}")
    print(f"  Newly failed:    {failed_in_run}")
    print(f"  Total records:   {len(load_processed_ids(CSV_PATH))}/{total_cases}")
    print("=" * 70)


if __name__ == "__main__":
    run_batch()
