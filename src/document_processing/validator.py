"""
SkillSprint AI — Document Validator
Checks file type, size, emptiness, and duplicate detection (SHA-256 hash).
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from src.config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from src.database.queries import get_document_by_hash


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sha256_hash: str = ""
    file_size_bytes: int = 0
    file_type: str = ""

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_uploaded_file(
    file_bytes: bytes,
    filename: str,
) -> ValidationResult:
    """
    Validate an uploaded document.

    Checks:
        1. File extension is .pdf or .docx
        2. File size is within limit
        3. File is not empty (zero bytes or pure whitespace)
        4. SHA-256 hash not already in the database (duplicate detection)

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename as provided by the uploader.

    Returns:
        ValidationResult with .valid=True if all checks pass.
    """
    result = ValidationResult()
    result.file_size_bytes = len(file_bytes)

    # ── 1. Extension check ──────────────────────────────────────────────────
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        result.add_error(
            f"Unsupported file type '{suffix}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        return result  # no point continuing

    result.file_type = suffix.lstrip(".")  # 'pdf' | 'docx'

    # ── 2. Size check ───────────────────────────────────────────────────────
    if result.file_size_bytes == 0:
        result.add_error("File is empty (0 bytes).")
        return result

    if result.file_size_bytes > MAX_FILE_SIZE_BYTES:
        mb = result.file_size_bytes / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        result.add_error(
            f"File is too large ({mb:.1f} MB). Maximum allowed: {limit_mb:.0f} MB."
        )

    # ── 3. Non-empty content check ──────────────────────────────────────────
    # For DOCX files we can't easily inspect bytes here; we do it after parse.
    # For PDF we just verify there are some bytes beyond the header.
    if suffix == ".pdf" and not file_bytes.startswith(b"%PDF"):
        result.add_error("File does not appear to be a valid PDF (missing %PDF header).")

    # ── 4. Duplicate detection via SHA-256 ──────────────────────────────────
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    result.sha256_hash = sha256

    existing = get_document_by_hash(sha256)
    if existing:
        result.add_error(
            f"Duplicate detected: this file was already uploaded as "
            f"'{existing['original_name']}' (ID: {existing['document_id']})."
        )

    return result


def compute_sha256(file_bytes: bytes) -> str:
    """Return hex SHA-256 of raw bytes."""
    return hashlib.sha256(file_bytes).hexdigest()
