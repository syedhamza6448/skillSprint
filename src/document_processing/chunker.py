"""
SkillSprint AI — Document Chunker
Converts ParsedSections into DB-ready chunk records.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.config.settings import MIN_CHUNK_CHARS
from src.document_processing.parser import ParsedDocument, ParsedSection


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_document(
    parsed_doc: ParsedDocument,
    document_id: str,
    version: str = "v1",
) -> list[dict]:
    """
    Convert a ParsedDocument into a list of chunk dicts ready for DB insertion.

    Chunk ID format:  <document_id>-CHK-<zero-padded 3-digit index>
    e.g.              DOC-001-CHK-001

    Args:
        parsed_doc:  Output of parser.parse_document().
        document_id: The document's ID string (e.g. 'DOC-001').
        version:     Document version string (default 'v1').

    Returns:
        List of dicts matching the `chunks` table schema.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    chunks: list[dict] = []
    chunk_index = 0

    for section in parsed_doc.sections:
        # Skip trivially short sections
        content = _clean_content(section.content)
        if len(content) < MIN_CHUNK_CHARS:
            continue

        chunk_index += 1
        chunk_id = f"{document_id}-CHK-{chunk_index:03d}"

        chunks.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "section_number": section.section_number or "",
                "heading": section.heading or "",
                "content": content,
                "page_or_para_ref": section.page_or_para_ref or "",
                "char_count": len(content),
                "version": version,
                "created_at": created_at,
            }
        )

    return chunks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_content(text: str) -> str:
    """
    Light normalisation of extracted text:
    - Collapse runs of 3+ blank lines to 2
    - Strip leading/trailing whitespace
    """
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
