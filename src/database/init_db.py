"""
SkillSprint AI — Database Initialisation
Creates all SQLite tables required by the application.

Run from project root:
    python src/database/init_db.py
"""

import sqlite3
import sys
from pathlib import Path

# Allow running as a script from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.settings import DB_PATH


# ---------------------------------------------------------------------------
# DDL statements
# ---------------------------------------------------------------------------

DDL = """
-- ----------------------------------------------------------------
-- documents: one row per uploaded company document
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    document_id     TEXT PRIMARY KEY,          -- e.g. 'DOC-001'
    filename        TEXT NOT NULL,
    original_name   TEXT NOT NULL,
    file_type       TEXT NOT NULL,             -- 'pdf' | 'docx'
    file_size_bytes INTEGER NOT NULL,
    sha256_hash     TEXT NOT NULL UNIQUE,      -- duplicate detection
    version         TEXT NOT NULL DEFAULT 'v1',
    is_superseded   INTEGER NOT NULL DEFAULT 0, -- 1 = superseded by newer version
    superseded_by   TEXT,                      -- document_id of the successor
    uploaded_at     TEXT NOT NULL,             -- ISO 8601
    page_count      INTEGER,
    char_count      INTEGER,
    status          TEXT NOT NULL DEFAULT 'active'  -- 'active' | 'superseded' | 'error'
);

-- ----------------------------------------------------------------
-- chunks: sections/passages extracted from each document
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id            TEXT PRIMARY KEY,       -- e.g. 'DOC-001-CHK-001'
    document_id         TEXT NOT NULL REFERENCES documents(document_id),
    section_number      TEXT,                  -- e.g. '3.1'
    heading             TEXT,                  -- heading text
    content             TEXT NOT NULL,
    page_or_para_ref    TEXT,                  -- 'page 3' | 'paragraph 12'
    char_count          INTEGER NOT NULL,
    version             TEXT NOT NULL DEFAULT 'v1',
    created_at          TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- requirement_matrix: loaded from CSV (ground-truth)
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requirement_matrix (
    requirement_id          TEXT PRIMARY KEY,
    role                    TEXT NOT NULL,
    policy_requirement      TEXT NOT NULL,
    process_requirement     TEXT,
    competency              TEXT,
    mandatory_optional      TEXT NOT NULL,     -- 'Mandatory' | 'Optional'
    priority                TEXT NOT NULL,     -- 'High' | 'Medium' | 'Low'
    source_document_id      TEXT,
    source_section_id       TEXT,
    assessment_requirement  TEXT,
    loaded_at               TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- employees: people being onboarded
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id     TEXT PRIMARY KEY,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL,
    role_id         TEXT NOT NULL,
    department      TEXT NOT NULL,
    experience_level TEXT NOT NULL DEFAULT 'Junior',
    start_date      TEXT NOT NULL,             -- ISO 8601 date
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- generation_log: every AI plan generation attempt
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generation_log (
    log_id              TEXT PRIMARY KEY,
    employee_id         TEXT REFERENCES employees(employee_id),
    role                TEXT NOT NULL,
    prompt_version      TEXT NOT NULL,
    model_name          TEXT NOT NULL,
    source_doc_versions TEXT NOT NULL,         -- JSON array string
    status              TEXT NOT NULL,         -- 'success' | 'retry_success' | 'failed'
    retry_count         INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    generated_at        TEXT NOT NULL          -- ISO 8601
);

-- ----------------------------------------------------------------
-- onboarding_plans: the final structured plan for an employee
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_plans (
    plan_id         TEXT PRIMARY KEY,
    employee_id     TEXT NOT NULL REFERENCES employees(employee_id),
    log_id          TEXT REFERENCES generation_log(log_id),
    plan_json       TEXT NOT NULL,             -- full JSON blob
    status          TEXT NOT NULL DEFAULT 'draft',  -- 'draft'|'validated'|'approved'
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- validation_results: Pipeline 2 output per plan item
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_results (
    result_id           TEXT PRIMARY KEY,
    plan_id             TEXT NOT NULL REFERENCES onboarding_plans(plan_id),
    item_id             TEXT NOT NULL,         -- module/task/checklist/assessment id
    item_type           TEXT NOT NULL,         -- 'module'|'task'|'checklist'|'quiz'|'assessment'
    requirement_id      TEXT,
    source_document_id  TEXT,
    source_section_id   TEXT,
    verification_status TEXT NOT NULL,         -- 'Verified'|'Verified with Warning'|'Incomplete'|
                                               -- 'Unsupported'|'Contradictory'|'Manual Review Required'
    coverage_flag       INTEGER NOT NULL DEFAULT 0,   -- 1 = covers mandatory req
    traceability_flag   INTEGER NOT NULL DEFAULT 0,   -- 1 = has valid source ref
    duplicate_flag      INTEGER NOT NULL DEFAULT 0,   -- 1 = duplicate detected
    contradiction_flag  INTEGER NOT NULL DEFAULT 0,   -- 1 = cites superseded doc
    hallucination_flag  INTEGER NOT NULL DEFAULT 0,   -- 1 = no valid source citation
    notes               TEXT,
    validated_at        TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- audit_trail: manual review decisions
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id            TEXT PRIMARY KEY,
    plan_id             TEXT NOT NULL REFERENCES onboarding_plans(plan_id),
    item_id             TEXT NOT NULL,
    reviewer_id         TEXT NOT NULL,
    original_content    TEXT NOT NULL,         -- AI-generated
    reviewer_decision   TEXT NOT NULL,         -- 'Approved'|'Rejected'|'Edited'|'Regenerate'
    edited_content      TEXT,                  -- if decision = 'Edited'
    decision_notes      TEXT,
    decided_at          TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- comparison_results: GenAI vs Python side-by-side
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comparison_results (
    comparison_id       TEXT PRIMARY KEY,
    plan_id             TEXT NOT NULL REFERENCES onboarding_plans(plan_id),
    requirement_id      TEXT NOT NULL,
    python_expected     TEXT NOT NULL,         -- from requirement_matrix
    genai_result        TEXT,                  -- from plan JSON
    match_status        TEXT NOT NULL,         -- 'Match'|'Mismatch'|'Missing'|'Extra'
    source_ref          TEXT,
    verification_status TEXT,
    compared_at         TEXT NOT NULL
);

-- ----------------------------------------------------------------
-- Indexes for common lookups
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_chunks_document    ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_matrix_role        ON requirement_matrix(role);
CREATE INDEX IF NOT EXISTS idx_matrix_mandatory   ON requirement_matrix(mandatory_optional);
CREATE INDEX IF NOT EXISTS idx_validation_plan    ON validation_results(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_plan         ON audit_trail(plan_id);
CREATE INDEX IF NOT EXISTS idx_comparison_plan    ON comparison_results(plan_id);
CREATE INDEX IF NOT EXISTS idx_plans_employee     ON onboarding_plans(employee_id);
"""


def init_db(db_path: Path | None = None, verbose: bool = False) -> None:
    """Create all tables if they do not already exist."""
    if db_path is None:
        import src.config.settings as s
        db_path = s.DB_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DDL)
        conn.commit()
        if verbose:
            print(f"[init_db] Database initialised at: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(verbose=True)
