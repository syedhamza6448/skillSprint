"""
SkillSprint AI — Database Query Helpers
Thin wrapper around sqlite3 for all DB interactions.
"""

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from src.config.settings import DB_PATH


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def get_conn(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield an auto-committing sqlite3 connection."""
    if db_path is None:
        import src.config.settings as s
        db_path = s.DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL") # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# documents table
# ---------------------------------------------------------------------------

def insert_document(doc: dict[str, Any]) -> None:
    """Insert a new document record."""
    sql = """
        INSERT INTO documents
            (document_id, filename, original_name, file_type, file_size_bytes,
             sha256_hash, version, is_superseded, superseded_by,
             uploaded_at, page_count, char_count, status)
        VALUES
            (:document_id, :filename, :original_name, :file_type, :file_size_bytes,
             :sha256_hash, :version, :is_superseded, :superseded_by,
             :uploaded_at, :page_count, :char_count, :status)
    """
    with get_conn() as conn:
        conn.execute(sql, doc)


def get_document_by_hash(sha256_hash: str) -> sqlite3.Row | None:
    """Return the document that matches a given SHA-256 hash, or None."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE sha256_hash = ?", (sha256_hash,)
        ).fetchone()


def get_document_by_id(document_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()


def get_all_documents() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()


def mark_document_superseded(document_id: str, superseded_by: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET is_superseded=1, superseded_by=?, status='superseded' "
            "WHERE document_id=?",
            (superseded_by, document_id),
        )


def delete_document(document_id: str) -> None:
    """Delete document and its chunks (cascaded manually)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))


# ---------------------------------------------------------------------------
# chunks table
# ---------------------------------------------------------------------------

def insert_chunks(chunks: list[dict[str, Any]]) -> None:
    """Bulk-insert chunks for a document."""
    sql = """
        INSERT INTO chunks
            (chunk_id, document_id, section_number, heading,
             content, page_or_para_ref, char_count, version, created_at)
        VALUES
            (:chunk_id, :document_id, :section_number, :heading,
             :content, :page_or_para_ref, :char_count, :version, :created_at)
    """
    with get_conn() as conn:
        conn.executemany(sql, chunks)


def get_chunks_for_document(document_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM chunks WHERE document_id=? ORDER BY chunk_id",
            (document_id,),
        ).fetchall()


def get_chunk_by_id(chunk_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()


def chunk_exists(chunk_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM chunks WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
    return row is not None


def get_all_chunks() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM chunks").fetchall()


# ---------------------------------------------------------------------------
# requirement_matrix table
# ---------------------------------------------------------------------------

def upsert_requirements(rows: list[dict[str, Any]]) -> None:
    """Insert or replace requirement matrix rows."""
    sql = """
        INSERT OR REPLACE INTO requirement_matrix
            (requirement_id, role, policy_requirement, process_requirement,
             competency, mandatory_optional, priority, source_document_id,
             source_section_id, assessment_requirement, loaded_at)
        VALUES
            (:requirement_id, :role, :policy_requirement, :process_requirement,
             :competency, :mandatory_optional, :priority, :source_document_id,
             :source_section_id, :assessment_requirement, :loaded_at)
    """
    with get_conn() as conn:
        conn.executemany(sql, rows)


def get_requirements_for_role(role: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM requirement_matrix WHERE role=? OR role='All Roles' "
            "ORDER BY mandatory_optional DESC, priority",
            (role,),
        ).fetchall()


def get_mandatory_requirements_for_role(role: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM requirement_matrix "
            "WHERE (role=? OR role='All Roles') AND mandatory_optional='Mandatory' "
            "ORDER BY priority",
            (role,),
        ).fetchall()


def get_all_roles() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT role FROM requirement_matrix WHERE role != 'All Roles' ORDER BY role"
        ).fetchall()
    return [r["role"] for r in rows]


def get_requirement_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM requirement_matrix").fetchone()[0]


# ---------------------------------------------------------------------------
# employees table
# ---------------------------------------------------------------------------

def insert_employee(emp: dict[str, Any]) -> None:
    sql = """
        INSERT INTO employees
            (employee_id, full_name, email, role, role_id, department,
             experience_level, start_date, status, created_at)
        VALUES
            (:employee_id, :full_name, :email, :role, :role_id, :department,
             :experience_level, :start_date, :status, :created_at)
    """
    with get_conn() as conn:
        conn.execute(sql, emp)


def get_all_employees() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM employees ORDER BY created_at DESC"
        ).fetchall()


def get_employee_by_id(employee_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM employees WHERE employee_id=?", (employee_id,)
        ).fetchone()


# ---------------------------------------------------------------------------
# generation_log
# ---------------------------------------------------------------------------

def insert_generation_log(log: dict[str, Any]) -> None:
    sql = """
        INSERT INTO generation_log
            (log_id, employee_id, role, prompt_version, model_name,
             source_doc_versions, status, retry_count, error_message, generated_at)
        VALUES
            (:log_id, :employee_id, :role, :prompt_version, :model_name,
             :source_doc_versions, :status, :retry_count, :error_message, :generated_at)
    """
    with get_conn() as conn:
        conn.execute(sql, log)


# ---------------------------------------------------------------------------
# onboarding_plans
# ---------------------------------------------------------------------------

def insert_plan(plan: dict[str, Any]) -> None:
    sql = """
        INSERT INTO onboarding_plans
            (plan_id, employee_id, log_id, plan_json, status, created_at, updated_at)
        VALUES
            (:plan_id, :employee_id, :log_id, :plan_json, :status, :created_at, :updated_at)
    """
    with get_conn() as conn:
        conn.execute(sql, plan)


def get_plans_for_employee(employee_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM onboarding_plans WHERE employee_id=? ORDER BY created_at DESC",
            (employee_id,),
        ).fetchall()


def get_plan_by_id(plan_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM onboarding_plans WHERE plan_id=?", (plan_id,)
        ).fetchone()


def update_plan_status(plan_id: str, status: str, updated_at: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE onboarding_plans SET status=?, updated_at=? WHERE plan_id=?",
            (status, updated_at, plan_id),
        )


# ---------------------------------------------------------------------------
# validation_results
# ---------------------------------------------------------------------------

def insert_validation_results(results: list[dict[str, Any]]) -> None:
    sql = """
        INSERT OR REPLACE INTO validation_results
            (result_id, plan_id, item_id, item_type, requirement_id,
             source_document_id, source_section_id, verification_status,
             coverage_flag, traceability_flag, duplicate_flag,
             contradiction_flag, hallucination_flag, notes, validated_at)
        VALUES
            (:result_id, :plan_id, :item_id, :item_type, :requirement_id,
             :source_document_id, :source_section_id, :verification_status,
             :coverage_flag, :traceability_flag, :duplicate_flag,
             :contradiction_flag, :hallucination_flag, :notes, :validated_at)
    """
    with get_conn() as conn:
        conn.executemany(sql, results)


def get_validation_results_for_plan(plan_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM validation_results WHERE plan_id=?", (plan_id,)
        ).fetchall()


# ---------------------------------------------------------------------------
# audit_trail
# ---------------------------------------------------------------------------

def insert_audit_entry(entry: dict[str, Any]) -> None:
    sql = """
        INSERT INTO audit_trail
            (audit_id, plan_id, item_id, reviewer_id, original_content,
             reviewer_decision, edited_content, decision_notes, decided_at)
        VALUES
            (:audit_id, :plan_id, :item_id, :reviewer_id, :original_content,
             :reviewer_decision, :edited_content, :decision_notes, :decided_at)
    """
    with get_conn() as conn:
        conn.execute(sql, entry)


def get_audit_trail_for_plan(plan_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM audit_trail WHERE plan_id=? ORDER BY decided_at",
            (plan_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# comparison_results
# ---------------------------------------------------------------------------

def insert_comparison_results(results: list[dict[str, Any]]) -> None:
    sql = """
        INSERT OR REPLACE INTO comparison_results
            (comparison_id, plan_id, requirement_id, python_expected,
             genai_result, match_status, source_ref, verification_status, compared_at)
        VALUES
            (:comparison_id, :plan_id, :requirement_id, :python_expected,
             :genai_result, :match_status, :source_ref, :verification_status, :compared_at)
    """
    with get_conn() as conn:
        conn.executemany(sql, results)


def get_comparison_results_for_plan(plan_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM comparison_results WHERE plan_id=? ORDER BY requirement_id",
            (plan_id,),
        ).fetchall()
