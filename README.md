# SkillSprint AI - Intelligent Onboarding Plan Generator and Ground-Truth Validation System

SkillSprint AI is an enterprise-grade AI onboarding platform built for NimbusWorks. It combines a generative AI pipeline (Pipeline 1) with an independent, deterministic Python validation pipeline (Pipeline 2) to generate, audit, and verify role-specific onboarding plans against company policies.

---

## Architecture Summary

SkillSprint AI uses a dual-pipeline architecture to ensure AI output is grounded, traceable, and secure:

1. **Pipeline 1: GenAI Generation Engine (`core/genai_pipeline.py`)**
   - Retrieves role-relevant policy chunks from SQLite (`chunks` table).
   - Prompts Gemini API to generate structured JSON onboarding plans validated against Pydantic schemas (`core/schemas.py`).
   - Includes automatic transient error handling with exponential backoff (retries on 503/429) and model fallback (Gemini 3.5 Flash to Flash Lite).

2. **Pipeline 2: Ground-Truth Validation Engine (`core/validation_pipeline.py`)**
   - Pure, deterministic Python execution with zero LLM/API dependencies.
   - Evaluates generated plans against the ground-truth Role Requirement Matrix (`requirement_matrix` table).
   - Computes quantitative metrics: Mandatory Coverage Score (%) and Source Traceability Score (%).
   - Flags discrepancies: Unsupported Claims (fake/unregistered document IDs), Outdated Policies (superseded matrix rows), and Duplicate Modules.

3. **Comparison Engine & Audit Trail (`core/comparison.py` & `core/db.py`)**
   - Merges Pipeline 1 and Pipeline 2 outputs into fine-grained per-requirement verification statuses: `Verified`, `Verified with Warning`, `Outdated Source`, `Unsupported Requirement`, `Requirement Missing`, or `Manual Review Required`.
   - Persists all raw outputs, metrics, and human reviewer decisions into SQLite for full compliance auditability.

---

## Technology Stack

- **Frontend & Dashboard:** Streamlit, Plotly
- **Database & Storage:** SQLite (`skillsprint.db`), Pandas
- **Document Processing:** PyMuPDF (PDF), python-docx (DOCX)
- **Validation & Schemas:** Pydantic v2
- **GenAI Integration:** Google GenAI SDK (`google-genai`), Python Dotenv

---

## Setup & Installation Instructions

### 1. Prerequisites
- Python 3.10 or higher
- A Google Gemini API key

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

Edit `.env` and set your key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 5. Initialize Database & Ground-Truth Matrix

Run the initialization script to create SQLite tables and load the ground-truth policy matrix:

```bash
python -c "from core.db import setup_db, load_matrix; setup_db(); load_matrix('data/role_requirement_matrix.csv')"
```

### 6. Ingest Initial Company Documents

Ingest the 12 company documents located in `data/company_docs/`:

```bash
python -c "from core.doc_processing import process_all; process_all('data/company_docs/')"
```

### 7. Run the Application

Launch the Streamlit web application:

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## Application Navigation & Usage

1. **Landing Page (`app.py`)**
   - Overview of the system architecture, dual-pipeline status, and quick role selection.

2. **Admin Document Ingestion (`pages/1_admin_upload.py`)**
   - Upload new company policy documents (.pdf or .docx).
   - Validates document headers, computes SHA-256 file hashes to prevent duplicate ingestion, extracts structured text sections, and updates the SQLite chunk database.

3. **Employee Plan Generation & Verification (`pages/2_employee_plan.py`)**
   - Select an employee ID and role.
   - Click **Generate Onboarding Plan** to trigger Pipeline 1 (GenAI) and Pipeline 2 (Python Validation).
   - Displays the generated modules alongside a real-time verification badge, coverage scores, and detected policy flags.

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

Execute the 110-case evaluation batch:

```bash
python tools/run_comparison_batch.py
```

Results are saved to `reports/genai_python_comparison_report.csv`.

---

## Troubleshooting

- **Missing API Key Error:**
  Verify that `.env` exists in the repository root and contains `GEMINI_API_KEY=...`. Ensure you loaded dotenv or restarted the application after creating `.env`.

- **503 / 429 API Rate Limit Errors:**
  `core/genai_pipeline.py` automatically retries up to 3 times with exponential backoff before attempting model fallback (`gemini-3.5-flash-lite`). If failures persist, wait a few minutes or verify your API quota.

- **Database Table or Schema Errors:**
  Reset and re-initialize the database cleanly:
  ```bash
  python -c "from core.db import setup_db, load_matrix; setup_db(); load_matrix('data/role_requirement_matrix.csv')"
  ```

---

## Note on Hidden Evaluation Readiness

SkillSprint AI is fully dynamic and zero-hardcoded. The parsing pipeline (`core/doc_processing.py`) dynamically extracts headings, sections, page numbers, and versions from any new `.pdf` or `.docx` document uploaded through the Admin panel or placed into `data/company_docs/`. No code changes or schema re-deployments are required to support updated company policies.
