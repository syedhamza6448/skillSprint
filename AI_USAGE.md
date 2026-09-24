# AI Usage & Disclosure Report - SkillSprint AI

This document provides a transparent record of AI assistance utilized during the development of SkillSprint AI for the Aptech TechWiz7 competition.

---

## Tool Overview

- **Primary AI Assistant:** Antigravity (Agentic AI Coding Assistant, Google DeepMind)
- **Model Backbone:** Gemini 3.6 Flash / Claude Sonnet
- **Workflow Methodology:** Human-in-the-loop pair programming. The AI assistant proposed implementation plans, wrote code, and authored test suites under human supervision. Every phase's deliverables were manually reviewed, executed, and verified by the developer before proceeding to subsequent phases.

---

## Phase-by-Phase AI Assistance Breakdown

### Phase 0: Environment Setup & Scaffold
- **Purpose:** Initializing repository structure, configuring dependencies (`requirements.txt`), and wiring Google GenAI API connectivity.
- **Files Affected:** `PHASES.md`, `.env.example`, `requirements.txt`, `core/genai_pipeline.py`
- **Verification:** Ran test call script manually to confirm ping to Gemini API.

### Phase 1: Company Knowledge Base Authoring
- **Purpose:** Generating draft texts for 21 fictional NimbusWorks policy documents (HR, Leave, InfoSec, SOPs, Equipment, Remote Work, Travel) with explicit section headings.
- **Files Affected:** `tools/build_expanded_dataset.py`, `data/company_docs_drafts/*`, `data/company_docs/*`
- **Verification:** Converted markdown drafts into PDF and DOCX formats and visually verified section headers.

### Phase 2: Document Parsing & Chunking Pipeline
- **Purpose:** Designing document extraction logic using PyMuPDF and python-docx, heading regex chunking, content-hash deduplication, and SQLite storage.
- **Files Affected:** `core/doc_processing.py`, `core/db.py`
- **Verification:** Ran `process_all()` and queried SQLite `chunks` table to verify chunk metadata and text extraction.

### Phase 3: Role Requirement Matrix Development
- **Purpose:** Structuring ground-truth requirement matrix with 160 rows across 10 roles, including prerequisite chains, conflicting/ambiguous pairs, and policy-version pairs.
- **Files Affected:** `tools/build_expanded_dataset.py`, `data/role_requirement_matrix.csv`, `data/adversarial_test_cases.csv`
- **Verification:** Loaded matrix into SQLite and validated role coverage using Pandas dataframe analysis.

### Phase 4: App Skeleton & Navigation
- **Purpose:** Creating multi-page Streamlit web app layout, custom UI styling, and role navigation.
- **Files Affected:** `app.py`, `pages/1_admin_upload.py`, `pages/2_employee_plan.py`, `pages/3_dashboard.py`
- **Verification:** Launched Streamlit web server and navigated all multi-page routes.

### Phase 5: Pipeline 1 (GenAI Generation)
- **Purpose:** Writing Pydantic schemas for onboarding plans, building versioned prompt templates, and implementing retry + model fallback logic.
- **Files Affected:** `core/schemas.py`, `prompts/onboarding_v1.txt`, `core/genai_pipeline.py`
- **Verification:** Executed plan generation for sample roles and verified JSON schema compliance.

### Phase 6: Pipeline 2 (Ground-Truth Validation)
- **Purpose:** Creating standalone Python validation engine to measure mandatory coverage, traceability scores, outdated policy references, sequence violations, and unsupported claims.
- **Files Affected:** `core/validation_pipeline.py`, `tests/test_validation_pipeline.py`
- **Verification:** Ran unit tests against broken/mock plan outputs to confirm strict error catching without LLM calls.

### Phase 7: Comparison Engine & Verification Status
- **Purpose:** Implementing fine-grained per-requirement item statuses ("Verified", "Outdated Source", "Unsupported Requirement", "Requirement Missing", "Sequence Violation") and plan status calculation.
- **Files Affected:** `core/comparison.py`, `pages/2_employee_plan.py`
- **Verification:** Generated end-to-end plans in Streamlit and verified display of status badges and breakdown tables.

### Phase 8: Dashboards & Manual Review Queue
- **Purpose:** Building Plotly metric visualizers, reviewer action controls (approve/reject/modify), and persistent audit logging.
- **Files Affected:** `pages/3_dashboard.py`, `core/db.py`
- **Verification:** Simulated manager review actions in dashboard UI and verified decision persistence in SQLite.

### Phase 9: Security & Adversarial Testing
- **Purpose:** Authoring 13 comprehensive prompt-injection and forgery test cases (`test_adversarial.py`) and documenting security controls.
- **Files Affected:** `tests/test_adversarial.py`, `reports/security_testing_report.md`
- **Verification:** Executed test suite (`python tests/test_adversarial.py`); verified 13/13 test cases passed.

### Phase 10: Comparison Report & Documentation
- **Purpose:** Authoring batch evaluation script (`run_comparison_batch.py`), comprehensive README, AI disclosure report, and onboarding intelligence report.
- **Files Affected:** `tools/run_comparison_batch.py`, `README.md`, `AI_USAGE.md`, `reports/onboarding_intelligence_report.md`
- **Verification:** Verified script parameterization, markdown ASCII encoding, and documentation completeness.

---

## Real Bugs Identified & Fixed During Manual Verification

Human review was active and rigorous throughout development. Several critical bugs were caught and fixed during manual runtime testing:

1. **Validation Pipeline Rewrite (`core/validation_pipeline.py`):**
   An initial AI-generated draft of the validation pipeline used overly simple keyword matching that failed to catch prerequisite sequence violations and subtle policy version mismatches. The pipeline logic was completely rewritten to perform strict ID and sequence mapping against matrix ground-truth rows.

2. **Database Schema Gap (`core/db.py`):**
   During matrix ingestion testing, prerequisite chain flags were returning zero sequence violations. Manual database inspection revealed that the `requirement_matrix` SQLite table schema had been defined before the `prerequisite_requirement_id` column was added to the matrix CSV, causing SQLite to silently drop the prerequisite column during query execution. The `CREATE TABLE` and `SELECT` queries in `core/db.py` were updated and verified with PRAGMA checks.

3. **Document Hash Deduplication (`core/doc_processing.py`):**
   The initial document parser relied on raw file-path hashes, which allowed modified or re-saved files with different metadata to bypass duplicate checking. The ingestion logic was changed to compute SHA-256 content hashes of extracted text, preventing duplicate chunk insertion regardless of file naming.

---

## Human Supervision Statement

All architectural decisions, database schemas, security boundary definitions, and validation rules were defined and verified by the developer. AI outputs were systematically audited, modified when necessary, and validated through local runtime execution before being accepted into the repository.
