"""
SkillSprint AI — Load Sample Requirement Matrix
Reads the Phase-0 CSV and upserts every row into the requirement_matrix table.

Usage:
    python src/database/load_sample_matrix.py
    python src/database/load_sample_matrix.py path/to/requirement_matrix.csv
"""

import sys
import csv
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.settings import MATRIX_CSV_PATH
from src.database.queries import upsert_requirements, get_requirement_count
from src.database.init_db import init_db


def load_matrix(csv_path: Path | str = MATRIX_CSV_PATH) -> int:
    """
    Load a requirement matrix CSV into the database.

    Returns:
        Number of rows loaded.
    """
    if isinstance(csv_path, str):
        csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Matrix CSV not found: {csv_path}")

    rows: list[dict] = []
    loaded_at = datetime.now(timezone.utc).isoformat()

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                {
                    "requirement_id": row["requirement_id"].strip(),
                    "role": row["role"].strip(),
                    "policy_requirement": row["policy_requirement"].strip(),
                    "process_requirement": row.get("process_requirement", "").strip(),
                    "competency": row.get("competency", "").strip(),
                    "mandatory_optional": row["mandatory_optional"].strip(),
                    "priority": row["priority"].strip(),
                    "source_document_id": row.get("source_document_id", "").strip(),
                    "source_section_id": row.get("source_section_id", "").strip(),
                    "assessment_requirement": row.get("assessment_requirement", "").strip(),
                    "loaded_at": loaded_at,
                }
            )

    if not rows:
        raise ValueError("CSV file is empty or has no data rows.")

    upsert_requirements(rows)
    return len(rows)


if __name__ == "__main__":
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else MATRIX_CSV_PATH

    # Ensure DB exists before loading
    init_db()

    count = load_matrix(csv_path)
    total = get_requirement_count()
    print(f"[load_matrix] Loaded {count} rows from {csv_path}")
    print(f"[load_matrix] Total requirements in DB: {total}")
