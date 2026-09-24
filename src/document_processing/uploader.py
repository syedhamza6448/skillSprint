"""
SkillSprint AI — Document Upload Orchestrator
Ties together: validate → parse → chunk → store in DB.
Returns a structured result for the UI to display.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.config.settings import ALLOWED_EXTENSIONS
from src.database.init_db import init_db
from src.database.queries import (
    insert_document,
    insert_chunks,
    get_document_by_hash,
    get_document_by_id,
    delete_document,
)
from src.document_processing.validator import validate_uploaded_file
from src.document_processing.parser import parse_document
from src.document_processing.chunker import chunk_document


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class UploadResult:
    success: bool = False
    document_id: str = ""
    filename: str = ""
    file_type: str = ""
    chunk_count: int = 0
    char_count: int = 0
    page_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _extract_doc_id_from_filename(filename: str) -> str | None:
    """Extract document ID like DOC-001 from filename if present."""
    m = re.search(r"(DOC-\d+)", filename, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def _next_document_id(filename: str = "") -> str:
    """
    Generate or extract the DOC-XXX ID.
    If the filename already contains a DOC-XXX prefix/marker, preserve it.
    Otherwise generate the next sequence number.
    """
    explicit_id = _extract_doc_id_from_filename(filename)
    if explicit_id:
        return explicit_id

    from src.database.queries import get_all_documents

    docs = get_all_documents()
    existing_nums: list[int] = []
    for doc in docs:
        m = re.match(r"DOC-(\d+)", doc["document_id"])
        if m:
            existing_nums.append(int(m.group(1)))

    next_num = max(existing_nums, default=0) + 1
    return f"DOC-{next_num:03d}"


def _extract_version_from_filename(filename: str) -> str:
    """Try to parse a version string from the filename, e.g. '_v2_' → 'v2'."""
    m = re.search(r"[_\-]v(\d+)[_\-\.]", filename, re.IGNORECASE)
    if m:
        return f"v{m.group(1)}"
    return "v1"


# ---------------------------------------------------------------------------
# Main upload function
# ---------------------------------------------------------------------------

def process_upload(
    file_bytes: bytes,
    filename: str,
    version_override: str | None = None,
) -> UploadResult:
    """
    Full upload pipeline: validate → parse → chunk → persist.

    Args:
        file_bytes:       Raw bytes from the uploaded file.
        filename:         Original filename.
        version_override: If provided, use this version string instead of
                          one inferred from the filename.

    Returns:
        UploadResult describing what happened.
    """
    result = UploadResult(filename=filename)

    # ── Ensure DB exists ────────────────────────────────────────────────────
    init_db()

    # ── Step 1: Validate ────────────────────────────────────────────────────
    val = validate_uploaded_file(file_bytes, filename)
    result.errors.extend(val.errors)
    result.warnings.extend(val.warnings)
    result.file_type = val.file_type

    if not val.valid:
        result.message = "Validation failed. File was not ingested."
        return result

    # ── Step 2: Parse ───────────────────────────────────────────────────────
    try:
        parsed = parse_document(file_bytes, filename, val.file_type)
    except Exception as exc:
        result.errors.append(f"Parsing error: {exc}")
        result.message = "Parsing failed. File was not ingested."
        return result

    result.warnings.extend(parsed.parse_warnings)

    # Check for empty content after parsing
    if not parsed.raw_text.strip():
        result.errors.append(
            "Document appears to contain no readable text. "
            "The file may be scanned/image-only or corrupt."
        )
        result.message = "Empty document. File was not ingested."
        return result

    # ── Step 3: Assign IDs & metadata ───────────────────────────────────────
    document_id = _next_document_id(filename)
    version = version_override or _extract_version_from_filename(filename)
    uploaded_at = datetime.now(timezone.utc).isoformat()

    # ── Step 4: Chunk ───────────────────────────────────────────────────────
    chunks = chunk_document(parsed, document_id, version)

    if not chunks:
        result.errors.append(
            "No extractable sections found. Check that the document has readable text content."
        )
        result.message = "No chunks produced. File was not ingested."
        return result

    # ── Step 5: Persist ─────────────────────────────────────────────────────
    doc_record = {
        "document_id": document_id,
        "filename": Path(filename).name,
        "original_name": filename,
        "file_type": val.file_type,
        "file_size_bytes": val.file_size_bytes,
        "sha256_hash": val.sha256_hash,
        "version": version,
        "is_superseded": 0,
        "superseded_by": None,
        "uploaded_at": uploaded_at,
        "page_count": parsed.page_count,
        "char_count": parsed.char_count,
        "status": "active",
    }

    try:
        if get_document_by_id(document_id):
            delete_document(document_id)
        insert_document(doc_record)
        insert_chunks(chunks)
    except Exception as exc:
        result.errors.append(f"Database error: {exc}")
        result.message = "Database write failed. File was not ingested."
        return result

    # ── Done ────────────────────────────────────────────────────────────────
    result.success = True
    result.document_id = document_id
    result.chunk_count = len(chunks)
    result.char_count = parsed.char_count
    result.page_count = parsed.page_count
    result.message = (
        f"Successfully ingested as {document_id}. "
        f"{len(chunks)} section(s) extracted, {parsed.char_count:,} characters."
    )
    return result
