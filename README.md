# SkillSprint AI

A Generative AI-powered onboarding intelligence application. SkillSprint AI
analyzes a company's own policies, SOPs, role descriptions, and compliance
documents to generate **personalized, role-specific onboarding plans** —
learning modules, checklists, practical tasks, quizzes, and assessments —
with every generated item independently verified against a structured,
Python-based ground-truth Role Requirement Matrix.

Built for the Aptech TechWiz7 "Generative AI PowerPlay" competition
(Theme: OnboardVerse).

---

## What it does

1. **Ingests** company documents (PDF/DOCX) and extracts traceable,
   versioned chunks.
2. Maintains a **Role Requirement Matrix** — the ground-truth mapping of
   which policies/tasks/competencies each job role must cover.
3. Uses a **Generative AI pipeline** (Google Gemini) to generate a
   personalized, multi-stage onboarding plan for a given employee/role.
4. Runs an **independent Python validation pipeline** (no AI involved) that
   checks the generated plan against the Requirement Matrix — flagging
   missing requirements, unsupported claims, duplicates, contradictions, and
   calculating coverage/traceability scores.
5. Routes anything uncertain to a **manual review queue** where an admin can
   approve, reject, edit, or regenerate content — with a full audit trail.
6. Provides dashboards for **employees**, **admins**, and **role-level**
   reporting, plus exportable reports.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend + Backend | Streamlit |
| Language | Python 3.10+ |
| Generative AI | Google Gemini API |
| Database | SQLite |
| Document Processing | pdfplumber (PDF), python-docx (DOCX) |
| Validation | Pydantic, custom Python rule engine |
| Data Processing | Pandas |
| Visualization | Streamlit native charts |
| Version Control | Git / GitHub |
| Deployment | Streamlit Community Cloud |

---

## Project Structure

```
skillsprint-ai/
├── src/
│   ├── app.py                     # Streamlit entrypoint
│   ├── document_processing/       # upload, validate, parse, chunk
│   ├── knowledge_base/            # chunk storage, version control
│   ├── genai_pipeline/            # Pipeline 1 — Gemini calls, JSON parsing
│   ├── python_validation/         # Pipeline 2 — coverage/traceability/hallucination checks
│   ├── comparison_engine/         # GenAI vs. Python result comparison
│   ├── hallucination_checks/      # unsupported-claim detection
│   ├── security/                  # prompt-injection defenses
│   ├── complaint_rules/           # (n/a for this project — role/requirement rules live here)
│   ├── schemas/                   # Pydantic models / JSON schemas
│   ├── prompt_templates/          # versioned prompt files (not hard-coded)
│   ├── database/                  # SQLite models & queries
│   └── config/                    # settings, constants
├── templates/                     # any Streamlit component templates
├── static/                        # images/icons for the UI
├── sample_documents/              # sample PDF/DOCX company documents
├── sample_data/                   # Role Requirement Matrix CSV, sample employees
├── hidden_test_ready/             # scripts/notes for hidden-evaluation readiness
├── tests/                         # test scripts and test logs
├── documentation/                 # architecture diagrams, DFDs, screenshots
├── reports/                       # generated CSV/PDF reports
├── requirements.txt
├── .env.example
├── AI_USAGE.md
├── LICENSE
└── README.md
```

---

## Prerequisites

- Python 3.10 or higher
- A Google AI Studio account with a **free-tier Gemini API key**
  → https://aistudio.google.com/app/apikey
- Git

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/skillsprint-ai.git
   cd skillsprint-ai
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API key**

   Copy the example env file and add your key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   > ⚠️ Never commit your `.env` file or hardcode the API key in source code.
   > `.env` is already listed in `.gitignore`.

5. **Initialize the database**
   ```bash
   python src/database/init_db.py
   ```
   This creates `skillsprint.db` (SQLite) with the required tables:
   `documents`, `chunks`, `requirement_matrix`, `employees`, `roles`,
   `generation_log`, `validation_results`, `audit_trail`.

6. **Load the sample Role Requirement Matrix (optional, recommended for first run)**
   ```bash
   python src/database/load_sample_matrix.py sample_data/requirement_matrix.csv
   ```

---

## Running the Application

```bash
streamlit run src/app.py
```

The app will open automatically at:
```
http://localhost:8501
```

---

## First-Time Usage Guide

1. **Log in** using one of the seeded accounts (see `sample_data/users.csv`
   or create your own via the admin panel):
   - `admin` — full access, document upload, matrix management, manual review
   - `employee` — view own onboarding progress only

2. **Upload company documents** (Admin → Knowledge Base):
   - Go to the **Documents** page
   - Upload PDF or DOCX files (sample files provided in `sample_documents/`)
   - The app will validate, parse, and chunk each document automatically —
     you'll see a confirmation with the Document ID and section count

3. **Review the Role Requirement Matrix** (Admin → Requirement Matrix):
   - View or import the ground-truth matrix mapping roles to mandatory/
     optional requirements

4. **Generate an onboarding plan**:
   - Go to **Generate Plan**
   - Select an employee (or create one) and their role
   - Click **Generate** — this calls Pipeline 1 (Gemini) to produce the plan

5. **Review validation results**:
   - The **Validation** tab shows Pipeline 2's independent check: Coverage
     Score, Traceability Score, and any flagged items (missing requirement,
     unsupported claim, duplicate, contradiction)
   - Items needing attention appear in the **Manual Review Queue**

6. **Manual review** (Admin):
   - Approve, reject, edit, or regenerate any flagged item
   - Every decision is recorded in the audit trail alongside the original
     AI-generated result

7. **Track progress** (Employee dashboard):
   - View assigned modules, checklist completion, quiz scores, and overall
     onboarding progress

8. **Reports** (Admin → Reports):
   - Export coverage reports, GenAI/Python comparison reports, and
     traceability reports as CSV

---

## Running Tests

```bash
python -m pytest tests/
```

Test logs and screenshots for manual/exploratory tests (prompt injection,
hallucination detection, hidden-data readiness) are documented in
`tests/test_log.md`.

---

## Configuration Notes

- **Prompt templates** live in `src/prompt_templates/` as versioned text
  files — do not hardcode prompts inside Python source files.
- **JSON schema** for GenAI output is defined in `src/schemas/` using
  Pydantic models; any change to the expected output structure should be
  made there, not in the prompt alone.
- **Policy precedence rules** (which document wins in a conflict) are
  configured in `src/python_validation/precedence_rules.py`.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `GEMINI_API_KEY not found` | Confirm `.env` exists and is in the project root; restart the Streamlit server after editing it. |
| GenAI returns invalid JSON | The app retries once automatically and logs the failure to `generation_log`; check `reports/failed_generations.csv` for details. |
| Document upload fails | Confirm the file is `.pdf` or `.docx` and under the configured size limit (see `src/config/settings.py`). |
| App can't find `skillsprint.db` | Re-run `python src/database/init_db.py` from the project root. |
| Deployed app can't reach Gemini | Confirm the API key is set as a **Streamlit secret** (Settings → Secrets) on Streamlit Community Cloud, not just locally in `.env`. |

---

## Deployment (Streamlit Community Cloud)

1. Push your repository to GitHub (public).
2. Go to https://share.streamlit.io and connect your GitHub account.
3. Select the repo and set the entrypoint to `src/app.py`.
4. Under **Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```
5. Deploy. The public URL is what you submit as the "Deployed Application"
   deliverable.

---

## Important Notes for Evaluators

- The application processes **hidden/unseen documents** (introduced during
  evaluation) using the same pipelines shown above — no source code changes
  are required to handle new roles, policies, or adversarial documents.
- Generated content is never accepted as final without passing through the
  independent Python Ground-Truth Validation Pipeline (`src/python_validation/`).
- See `AI_USAGE.md` for a full declaration of any AI tool assistance used
  during development.

---

## License

See `LICENSE` file.
