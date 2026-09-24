"""
SkillSprint AI — Application Settings & Constants
Centralised configuration for all modules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
SAMPLE_DOCUMENTS_DIR = PROJECT_ROOT / "sample_documents"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"

# ---------------------------------------------------------------------------
# Environment / secrets
# ---------------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: Path = PROJECT_ROOT / "skillsprint.db"

# ---------------------------------------------------------------------------
# Document ingestion limits
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx")
MAX_FILE_SIZE_MB: int = 50                   # upload size cap
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# ---------------------------------------------------------------------------
# Chunking settings
# ---------------------------------------------------------------------------
# Headings at these levels start a new chunk
HEADING_LEVELS: tuple[int, ...] = (1, 2, 3)
# Regex patterns that signal a section boundary in plain-text docs
SECTION_BREAK_PATTERNS: list[str] = [
    r"^={10,}",           # ===...===
    r"^-{10,}",           # ---...---
    r"^SECTION\s+\d+",    # SECTION 1
    r"^\d+\.\d*\s+[A-Z]", # 1.1 TITLE
]
MIN_CHUNK_CHARS: int = 50  # discard chunks shorter than this

# ---------------------------------------------------------------------------
# GenAI settings
# ---------------------------------------------------------------------------
GEMINI_MODEL: str = "gemini-2.0-flash"
PROMPT_TEMPLATE_DIR: Path = SRC_ROOT / "prompt_templates"
ACTIVE_PROMPT_TEMPLATE: str = "onboarding_plan_prompt_v1.yaml"
MAX_GENERATION_RETRIES: int = 1   # per plan spec: retry once, then log failure

# ---------------------------------------------------------------------------
# Requirement Matrix
# ---------------------------------------------------------------------------
MATRIX_CSV_PATH: Path = SAMPLE_DATA_DIR / "requirement_matrix.csv"

# ---------------------------------------------------------------------------
# UI / Streamlit
# ---------------------------------------------------------------------------
APP_TITLE: str = "SkillSprint AI"
APP_ICON: str = "🚀"
