"""
SkillSprint AI — Document Parser
Extracts text + heading/section structure from PDF and DOCX files.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import IO


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ParsedSection:
    """One logical section extracted from a document."""
    section_number: str          # e.g. '3.1' or '' if not detected
    heading: str                 # heading text (empty if body paragraph)
    content: str                 # body text of the section
    page_or_para_ref: str        # 'page 3' | 'paragraph 12' | ''
    heading_level: int = 0       # 0 = body, 1/2/3 = h1/h2/h3


@dataclass
class ParsedDocument:
    """Full parsing result for one file."""
    filename: str
    file_type: str               # 'pdf' | 'docx'
    page_count: int = 0
    char_count: int = 0
    sections: list[ParsedSection] = field(default_factory=list)
    raw_text: str = ""
    parse_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Patterns for detecting section headings in plain-text / PDF content
_SECTION_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>[A-Z][^\n]{3,80})$",
    re.MULTILINE,
)
_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z\s&/\-:]{4,80}$")
_RULE_RE = re.compile(r"^[=\-]{5,}$")


def _split_into_sections(text: str, source_label: str = "page") -> list[ParsedSection]:
    """
    Heuristically split plain text (from PDF pages or DOCX paragraphs)
    into sections by detecting heading-like lines.
    """
    lines = text.splitlines()
    sections: list[ParsedSection] = []
    current_heading = ""
    current_section_num = ""
    current_body_lines: list[str] = []
    para_counter = 0
    current_ref = source_label

    def _flush(heading: str, sec_num: str, body: list[str], ref: str, level: int) -> None:
        content = "\n".join(body).strip()
        if content or heading:
            sections.append(
                ParsedSection(
                    section_number=sec_num,
                    heading=heading,
                    content=content,
                    page_or_para_ref=ref,
                    heading_level=level,
                )
            )

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Detect separator lines like ====== or ------
        if _RULE_RE.match(line):
            i += 1
            continue

        # Detect numbered section: "3.1 TITLE"
        m = _SECTION_RE.match(line)
        if m:
            _flush(current_heading, current_section_num, current_body_lines, current_ref, 2)
            current_heading = m.group("title").strip()
            current_section_num = m.group("num")
            current_body_lines = []
            current_ref = source_label
            i += 1
            continue

        # Detect ALL-CAPS headings (common in plain-text docs)
        if _ALLCAPS_RE.match(line) and len(line) > 5:
            _flush(current_heading, current_section_num, current_body_lines, current_ref, 1)
            current_heading = line.strip()
            current_section_num = ""
            current_body_lines = []
            current_ref = source_label
            i += 1
            continue

        # Regular body line
        para_counter += 1
        current_body_lines.append(line)
        i += 1

    # Flush the final section
    _flush(current_heading, current_section_num, current_body_lines, current_ref, 2)
    return sections


# ---------------------------------------------------------------------------
# PDF parser
# ---------------------------------------------------------------------------

def parse_pdf(file_bytes: bytes, filename: str) -> ParsedDocument:
    """
    Parse a PDF file using pdfplumber.
    Extracts text page-by-page, then splits into sections.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required. Run: pip install pdfplumber")

    doc = ParsedDocument(filename=filename, file_type="pdf")
    all_sections: list[ParsedSection] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        doc.page_count = len(pdf.pages)
        full_text_parts: list[str] = []

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            full_text_parts.append(text)
            if text.strip():
                page_sections = _split_into_sections(text, source_label=f"page {page_num}")
                all_sections.extend(page_sections)

        doc.raw_text = "\n".join(full_text_parts)
        doc.char_count = len(doc.raw_text)

    # If no sections were detected at all, treat the entire doc as one section
    if not all_sections and doc.raw_text.strip():
        all_sections = [
            ParsedSection(
                section_number="",
                heading="(Full Document)",
                content=doc.raw_text.strip(),
                page_or_para_ref="page 1",
            )
        ]
        doc.parse_warnings.append(
            "No section headings detected — entire document treated as one chunk."
        )

    doc.sections = all_sections
    return doc


# ---------------------------------------------------------------------------
# DOCX parser
# ---------------------------------------------------------------------------

def parse_docx(file_bytes: bytes, filename: str) -> ParsedDocument:
    """
    Parse a DOCX file using python-docx.
    Respects Word heading styles (Heading 1/2/3) to detect section boundaries.
    Falls back to heuristic splitting when heading styles are absent.
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        raise ImportError("python-docx is required. Run: pip install python-docx")

    doc = ParsedDocument(filename=filename, file_type="docx")
    word_doc = Document(io.BytesIO(file_bytes))

    sections: list[ParsedSection] = []
    current_heading = ""
    current_section_num = ""
    current_level = 0
    current_body_lines: list[str] = []
    para_index = 0

    def _flush() -> None:
        content = "\n".join(current_body_lines).strip()
        if content or current_heading:
            sections.append(
                ParsedSection(
                    section_number=current_section_num,
                    heading=current_heading,
                    content=content,
                    page_or_para_ref=f"paragraph {para_index}",
                    heading_level=current_level,
                )
            )

    all_text: list[str] = []

    for para_index, para in enumerate(word_doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue

        all_text.append(text)
        style_name = (para.style.name or "").lower()

        # Detect heading styles
        if "heading 1" in style_name:
            _flush()
            current_heading = text
            current_section_num = ""
            current_level = 1
            current_body_lines = []
        elif "heading 2" in style_name:
            _flush()
            current_heading = text
            current_section_num = ""
            current_level = 2
            current_body_lines = []
        elif "heading 3" in style_name:
            _flush()
            current_heading = text
            current_section_num = ""
            current_level = 3
            current_body_lines = []
        else:
            # Check for numbered section pattern even in non-heading styles
            m = _SECTION_RE.match(text)
            if m:
                _flush()
                current_heading = m.group("title").strip()
                current_section_num = m.group("num")
                current_level = 2
                current_body_lines = []
            else:
                current_body_lines.append(text)

    _flush()
    doc.raw_text = "\n".join(all_text)
    doc.char_count = len(doc.raw_text)
    doc.page_count = 0  # DOCX has no fixed page count without rendering

    # If still empty, fall back to full-text heuristic split
    if not sections and doc.raw_text.strip():
        sections = _split_into_sections(doc.raw_text, source_label="paragraph 1")
        if not sections:
            sections = [
                ParsedSection(
                    section_number="",
                    heading="(Full Document)",
                    content=doc.raw_text.strip(),
                    page_or_para_ref="paragraph 1",
                )
            ]
            doc.parse_warnings.append(
                "No section headings detected in DOCX — treated as single chunk."
            )

    doc.sections = sections
    return doc


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def parse_document(file_bytes: bytes, filename: str, file_type: str) -> ParsedDocument:
    """
    Parse a document based on its detected file type.

    Args:
        file_bytes: Raw bytes of the file.
        filename:   Original filename.
        file_type:  'pdf' or 'docx' (from validator).

    Returns:
        ParsedDocument with sections list populated.
    """
    if file_type == "pdf":
        return parse_pdf(file_bytes, filename)
    elif file_type == "docx":
        return parse_docx(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file_type: '{file_type}'")
