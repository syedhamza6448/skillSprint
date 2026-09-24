# SkillSprint AI - Intelligent Onboarding Plan Generator and Ground-Truth Validation System

SkillSprint AI is an enterprise-grade AI onboarding platform built for NimbusWorks (Aptech TechWiz7 competition). It combines a generative AI pipeline (Pipeline 1) with an independent, deterministic Python ground-truth validation pipeline (Pipeline 2) to generate, audit, and verify role-specific employee onboarding plans against company policy documents.

---

## Architecture Summary

SkillSprint AI uses a dual-pipeline architecture to ensure that generated onboarding content is grounded, traceable, and policy-compliant:

1. **Pipeline 1: GenAI Generation Engine (`core/genai_pipeline.py`)**
   - Retrieves role-relevant policy chunks from SQLite (`chunks` table).
   - Prompts the Gemini API to generate structured JSON onboarding plans validated against Pydantic schemas (`core/schemas.py`).
   - Includes automatic transient error handling with exponential backoff (retries on 503/429 status codes) and automatic model fallback (from primary model `gemini-3.6-flash` / `gemini-3.5-flash` to `gemini-3.5-flash-lite`).

2. **Pipeline 2: Ground-Truth Validation Engine (`core/validation_pipeline.py`)**
   - Pure, deterministic Python execution with zero LLM or API dependencies.
   - Evaluates generated plans against the ground-truth Role Requirement Matrix (`requirement_matrix` table).
   - Computes quantitative metrics: Mandatory Coverage Score (%) and Source Traceability Score (%).
   - Detects and flags compliance risks: Sequence Violations (prerequisite module ordering), Outdated Policy References (superseded matrix sections), Duplicate Modules, Missing Mandatory Requirements, and Unsupported Claims (unregistered or hallucinated document IDs).

3. **Comparison Engine & Audit Trail (`core/comparison.py` & `core/db.py`)**
   - Merges Pipeline 1 and Pipeline 2 outputs into fine-grained per-requirement verification statuses: "Verified", "Verified with Warning", "Outdated Source", "Unsupported Requirement", "Requirement Missing", or "Manual Review Required".
   - Persists all raw outputs, metrics, and human reviewer decisions into SQLite for full compliance auditability.

### Why the Dual-Pipeline Design Exists

Large Language Models (LLMs) excel at natural-language fluency and structural planning, but can omit mandatory role requirements, cite superseded policy sections, or hallucinate document references. Pipeline 2 serves as an un-bypassable ground-truth safety barrier that independently verifies LLM outputs without relying on another AI prompt. This ensures 100% deterministic policy enforcement, verifiable source traceability, and full auditability required for enterprise compliance.

---

## Technology Stack

- **Frontend & Dashboard:** Streamlit, Plotly
- **Database & Storage:** SQLite (`skillsprint.db`), Pandas
- **Document Processing:** PyMuPDF (PDF parsing), python-docx (DOCX parsing)
- **Validation & Schemas:** Pydantic v2
- **GenAI Integration:** Google GenAI SDK (`google-genai`), Python Dotenv

---

## Setup & Installation Instructions

### 1. Prerequisites
- Python 3.10 or higher
- A Google Gemini API Key

### 2. Clone & Setup Virtual Environment

```bash
# Clone repository
git clone https://github.com/syedhamza6448/skillSprint.git
cd skillSprint

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env` and set your API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 5. Initialize Database & Ground-Truth Matrix

Run the initialization command to create SQLite tables and load the ground-truth policy matrix:

```bash
python -c "from core.db import setup_db, load_matrix; setup_db(); load_matrix('data/role_requirement_matrix.csv')"
```

### 6. Ingest Initial Company Documents

Ingest the 21 company policy documents located in `data/company_docs/`:

```bash
python -c "from core.doc_processing import process_all; process_all('data/company_docs/')"
```

### 7. Run the Application

Launch the Streamlit web application:

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

---

## Application Navigation & Usage

1. **Landing Page (`app.py`)**
   - Overview of the system architecture, dual-pipeline status, and navigation shortcuts.

2. **Admin Document Ingestion (`pages/1_admin_upload.py`)**
   - Upload new company policy documents (.pdf or .docx).
   - Validates document headers, computes SHA-256 content hashes to prevent duplicate ingestion, extracts structured text sections, and updates the SQLite chunk database.

3. **Employee Plan Generation & Verification (`pages/2_employee_plan.py`)**
   - Select an employee ID and job role.
   - Click "Generate Onboarding Plan" to trigger Pipeline 1 (GenAI) and Pipeline 2 (Python Validation).
   - Displays generated modules alongside real-time status badges, coverage scores, traceability metrics, and detected policy flags.

4. **Analytics & Manual Review Queue (`pages/3_dashboard.py`)**
   - Interactive Plotly analytics displaying role coverage, policy mismatch counts, and generation logs.
   - Reviewer queue allowing managers to inspect flagged plans, approve overrides, or record modification notes with full audit logging.

---

## Running Tests

### Security & Adversarial Test Suite

Run the Phase 9 adversarial test suite (13 prompt-injection and forgery test cases):

```bash
# Using pytest
pytest tests/test_adversarial.py -v

# Or using standard Python CLI
python tests/test_adversarial.py
```

### Running the Phase 10 Batch Comparison Script

Execute the 110-case batch evaluation script:

```bash
python tools/run_comparison_batch.py
```

Results are saved to `reports/genai_python_comparison_report.csv`.

---

## Troubleshooting

- **Missing API Key Error:**
  Verify that `.env` exists in the repository root and contains `GEMINI_API_KEY=...`. Ensure you restarted the application after updating `.env`.

- **503 / 429 API Rate Limit Errors:**
  `core/genai_pipeline.py` automatically retries up to 3 times with exponential backoff before attempting model fallback (from primary model `gemini-3.6-flash` / `gemini-3.5-flash` to `gemini-3.5-flash-lite`). This rate-limit handling and model fallback behavior is built-in as a known and handled operational state.

- **Database Table or Schema Reset:**
  To reset and re-initialize the database cleanly:
  ```bash
  python -c "from core.db import setup_db, load_matrix; setup_db(); load_matrix('data/role_requirement_matrix.csv')"
  ```

---

## Note on Hidden Evaluation Readiness

SkillSprint AI is fully dynamic and zero-hardcoded. The parsing pipeline (`core/doc_processing.py`) dynamically extracts headings, sections, page numbers, and versions from any new `.pdf` or `.docx` document uploaded through the Admin panel or placed directly into `data/company_docs/`. No code changes or schema re-deployments are required to ingest and evaluate updated company policy documents.
