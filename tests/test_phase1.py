"""
SkillSprint AI — Phase 1 Test Suite
Tests for document ingestion, validation, parsing, chunking, and database persistence.
"""

import os
import tempfile
from pathlib import Path
import pytest

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    SAMPLE_DOCUMENTS_DIR,
    SAMPLE_DATA_DIR,
)
from src.database.init_db import init_db
from src.database.queries import (
    insert_document,
    get_document_by_id,
    get_document_by_hash,
    get_all_documents,
    delete_document,
    insert_chunks,
    get_chunks_for_document,
    get_chunk_by_id,
)
from src.document_processing.validator import validate_uploaded_file, ValidationResult
from src.document_processing.parser import parse_document
from src.document_processing.chunker import chunk_document
from src.document_processing.uploader import process_upload, UploadResult
from src.database.load_sample_matrix import load_matrix


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """Ensure tests run against a clean temporary database."""
    test_db = tmp_path / "test_skillsprint.db"
    monkeypatch.setattr("src.config.settings.DB_PATH", test_db)
    monkeypatch.setattr("src.database.init_db.DB_PATH", test_db)
    monkeypatch.setattr("src.database.queries.DB_PATH", test_db)
    init_db(test_db)
    return test_db


# ---------------------------------------------------------------------------
# 1. Validation Tests
# ---------------------------------------------------------------------------

def test_validation_unsupported_extension():
    res = validate_uploaded_file(b"test content", "test.exe")
    assert not res.valid
    assert any("Unsupported file type" in e for e in res.errors)


def test_validation_empty_file():
    res = validate_uploaded_file(b"", "empty.pdf")
    assert not res.valid
    assert any("empty" in e.lower() for e in res.errors)


def test_validation_oversized_file(monkeypatch):
    monkeypatch.setattr("src.document_processing.validator.MAX_FILE_SIZE_BYTES", 100)
    res = validate_uploaded_file(b"A" * 150, "large.pdf")
    assert not res.valid
    assert any("too large" in e.lower() for e in res.errors)


def test_validation_invalid_pdf_header():
    res = validate_uploaded_file(b"not a valid pdf", "fake.pdf")
    assert not res.valid
    assert any("missing %PDF header" in e for e in res.errors)


def test_validation_duplicate_hash():
    # Insert a dummy document first
    sha = "test_hash_12345"
    insert_document({
        "document_id": "DOC-999",
        "filename": "existing.pdf",
        "original_name": "existing.pdf",
        "file_type": "pdf",
        "file_size_bytes": 100,
        "sha256_hash": sha,
        "version": "v1",
        "is_superseded": 0,
        "superseded_by": None,
        "uploaded_at": "2026-01-01T00:00:00",
        "page_count": 1,
        "char_count": 100,
        "status": "active"
    })

    # Try validating bytes that produce that same hash
    import hashlib
    class MockHash:
        @staticmethod
        def hexdigest():
            return sha

    # Mock hashlib.sha256 to return existing sha
    import unittest.mock as mock
    with mock.patch("hashlib.sha256", return_value=MockHash):
        res = validate_uploaded_file(b"%PDF-sample", "duplicate.pdf")
        assert not res.valid
        assert any("Duplicate detected" in e for e in res.errors)


# ---------------------------------------------------------------------------
# 2. Parsing Tests
# ---------------------------------------------------------------------------

def test_parse_sample_pdf():
    pdf_files = list(SAMPLE_DOCUMENTS_DIR.glob("*.pdf"))
    assert len(pdf_files) > 0, "No sample PDFs found"
    sample_pdf = pdf_files[0]
    data = sample_pdf.read_bytes()

    parsed = parse_document(data, sample_pdf.name, "pdf")
    assert parsed.file_type == "pdf"
    assert parsed.char_count > 100
    assert len(parsed.sections) > 0
    assert parsed.page_count >= 1


def test_parse_sample_docx():
    docx_files = list(SAMPLE_DOCUMENTS_DIR.glob("*.docx"))
    assert len(docx_files) > 0, "No sample DOCXs found"
    sample_docx = docx_files[0]
    data = sample_docx.read_bytes()

    parsed = parse_document(data, sample_docx.name, "docx")
    assert parsed.file_type == "docx"
    assert parsed.char_count > 100
    assert len(parsed.sections) > 0


# ---------------------------------------------------------------------------
# 3. Chunking Tests
# ---------------------------------------------------------------------------

def test_chunking_structure():
    docx_files = list(SAMPLE_DOCUMENTS_DIR.glob("*.docx"))
    sample_docx = docx_files[0]
    data = sample_docx.read_bytes()
    parsed = parse_document(data, sample_docx.name, "docx")

    chunks = chunk_document(parsed, "DOC-001", "v1")
    assert len(chunks) > 0
    first_chunk = chunks[0]
    
    assert "chunk_id" in first_chunk
    assert first_chunk["chunk_id"].startswith("DOC-001-CHK-")
    assert "document_id" in first_chunk
    assert "content" in first_chunk
    assert "char_count" in first_chunk
    assert first_chunk["char_count"] >= 50
    assert "version" in first_chunk


# ---------------------------------------------------------------------------
# 4. Database CRUD & Cascade Tests
# ---------------------------------------------------------------------------

def test_document_and_chunks_crud():
    doc = {
        "document_id": "DOC-101",
        "filename": "policy.pdf",
        "original_name": "policy.pdf",
        "file_type": "pdf",
        "file_size_bytes": 1024,
        "sha256_hash": "hash_xyz",
        "version": "v1",
        "is_superseded": 0,
        "superseded_by": None,
        "uploaded_at": "2026-01-01T00:00:00",
        "page_count": 2,
        "char_count": 500,
        "status": "active"
    }
    insert_document(doc)

    retrieved = get_document_by_id("DOC-101")
    assert retrieved is not None
    assert retrieved["filename"] == "policy.pdf"

    chunks = [
        {
            "chunk_id": "DOC-101-CHK-001",
            "document_id": "DOC-101",
            "section_number": "1.0",
            "heading": "Intro",
            "content": "Introductory content for test document.",
            "page_or_para_ref": "page 1",
            "char_count": 40,
            "version": "v1",
            "created_at": "2026-01-01T00:00:00"
        }
    ]
    insert_chunks(chunks)

    doc_chunks = get_chunks_for_document("DOC-101")
    assert len(doc_chunks) == 1
    assert doc_chunks[0]["chunk_id"] == "DOC-101-CHK-001"

    # Test delete document cascades to chunks
    delete_document("DOC-101")
    assert get_document_by_id("DOC-101") is None
    assert len(get_chunks_for_document("DOC-101")) == 0


# ---------------------------------------------------------------------------
# 5. Full Ingestion Orchestrator Tests
# ---------------------------------------------------------------------------

def test_process_upload_pdf():
    pdf_files = list(SAMPLE_DOCUMENTS_DIR.glob("*.pdf"))
    sample_pdf = pdf_files[0]
    data = sample_pdf.read_bytes()

    res = process_upload(data, sample_pdf.name)
    assert res.success, f"Upload failed: {res.errors}"
    assert res.chunk_count > 0
    assert res.char_count > 0

    # Verify stored in DB
    db_doc = get_document_by_id(res.document_id)
    assert db_doc is not None
    db_chunks = get_chunks_for_document(res.document_id)
    assert len(db_chunks) == res.chunk_count


def test_process_upload_docx():
    docx_files = list(SAMPLE_DOCUMENTS_DIR.glob("*.docx"))
    sample_docx = docx_files[0]
    data = sample_docx.read_bytes()

    res = process_upload(data, sample_docx.name)
    assert res.success, f"Upload failed: {res.errors}"
    assert res.chunk_count > 0
    assert res.char_count > 0

    db_doc = get_document_by_id(res.document_id)
    assert db_doc is not None
    db_chunks = get_chunks_for_document(res.document_id)
    assert len(db_chunks) == res.chunk_count


# ---------------------------------------------------------------------------
# 6. Requirement Matrix Loader
# ---------------------------------------------------------------------------

def test_load_requirement_matrix():
    matrix_csv = SAMPLE_DATA_DIR / "requirement_matrix.csv"
    assert matrix_csv.exists(), "Matrix CSV not found"
    
    count = load_matrix(str(matrix_csv))
    assert count >= 150, f"Expected at least 150 requirements, got {count}"
