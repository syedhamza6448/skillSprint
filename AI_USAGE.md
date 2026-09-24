# AI Usage & Disclosure Report - SkillSprint AI

This document provides a transparent record of AI assistance utilized during the development of SkillSprint AI for the Aptech TechWiz7 competition.

---

## Tool Overview

- **Primary AI Assistant:** Antigravity (Agentic AI Coding Assistant, Google DeepMind)
- **Model Backbone:** Gemini 3.6 Flash / Claude Sonnet
- **Workflow Methodology:** Human-in-the-loop pair programming. The AI assistant proposed implementation plans, wrote code, and authored test suites under human supervision. Every phase's deliverables were manually reviewed, executed, and verified by the developer before moving to subsequent phases.

---

## Phase-by-Phase AI Assistance Breakdown

### Phase 0: Environment Setup & Scaffold
- **Purpose:** Initializing project structure, configuring dependencies, and wiring Google GenAI API connectivity.
- **Files Affected:** `PHASES.md`, `.env.example`, `requirements.txt`, `core/genai_pipeline.py`
- **Verification:** API test script executed manually to confirm successful ping to Gemini API.

### Phase 1: Company Knowledge Base Authoring
- **Purpose:** Generating draft texts for 12 fictional NimbusWorks policy documents (HR, Leave, InfoSec, SOPs) with explicit section headings.
- **Files Affected:** `tools/convert_drafts.py`, `data/company_docs_drafts/*`, `data/company_docs/*`
- **Verification:** Converted drafts into PDF and DOCX formats and visually verified section headers.

### Phase 2: Document Parsing & Chunking Pipeline
- **Purpose:** Designing document extraction logic using PyMuPDF and python-docx, heading regex chunking, and SQLite storage.
- **Files Affected:** `core/doc_processing.py`, `core/db.py`
- **Verification:** Ran `process_all()` and queried SQLite `chunks` table to verify chunk metadata and text extraction.

### Phase 3: Role Requirement Matrix Development
- **Purpose:** Structuring ground-truth requirement matrix with 80+ rows across 10 roles, including legacy policy tags and adversarial test fixtures.
- **Files Affected:** `tools/generate_matrix.py`, `data/role_requirement_matrix.csv`, `data/adversarial_test_cases.csv`
- **Verification:** Loaded matrix into SQLite and validated role coverage using Pandas dataframe analysis.

### Phase 4: App Skeleton & Navigation
- **Purpose:** Creating multi-page Streamlit web app layout, custom UI styling, and basic role navigation.
- **Files Affected:** `app.py`, `pages/1_admin_upload.py`, `pages/2_employee_plan.py`, `pages/3_dashboard.py`
- **Verification:** Started Streamlit web server and navigated all multi-page routes.

### Phase 5: Pipeline 1 (GenAI Generation)
- **Purpose:** Writing Pydantic schemas for onboarding plans, building versioned prompt templates, and implementing retry + fallback model execution.
- **Files Affected:** `core/schemas.py`, `prompts/onboarding_v1.txt`, `core/genai_pipeline.py`
- **Verification:** Executed plan generation for sample roles and verified JSON schema compliance.

### Phase 6: Pipeline 2 (Ground-Truth Validation)
- **Purpose:** Creating standalone Python validation engine to measure mandatory coverage, traceability scores, outdated policy references, and unsupported claims.
- **Files Affected:** `core/validation_pipeline.py`, `tests/test_validation_pipeline.py`
- **Verification:** Ran unit tests against broken/mock plan outputs to confirm strict error catching without LLM calls.

### Phase 7: Comparison Engine & Verification Status
- **Purpose:** Implementing fine-grained per-requirement item statuses (`Verified`, `Outdated Source`, `Unsupported Requirement`, `Requirement Missing`) and plan status calculation.
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

## Human Supervision Statement

All architectural decisions, DB schemas, security boundary definitions, and validation rules were defined by the developer. AI outputs were systematically audited, modified when necessary, and validated through local runtime execution before being accepted into the codebase.
