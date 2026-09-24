"""
SkillSprint AI — Streamlit Application Entry Point

Run:
    streamlit run src/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so 'src.*' imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.config.settings import APP_TITLE, APP_ICON
from src.database.init_db import init_db

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Ensure DB tables exist ───────────────────────────────────────────────────
init_db()

# ── Sidebar navigation ───────────────────────────────────────────────────────
PAGES = {
    "🏠 Home": "home",
    "📄 Documents": "documents",
    "📋 Requirement Matrix": "matrix",
    "🤖 Generate Plan": "generate",
    "✅ Validation": "validation",
    "🔍 Manual Review": "review",
    "📊 Dashboards": "dashboards",
    "📁 Reports": "reports",
}

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/rocket.png", width=60)
    st.title(APP_TITLE)
    st.caption("AI-Powered Onboarding Intelligence")
    st.divider()
    selected = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Phase 1 — Document Ingestion ✅")

page = PAGES[selected]

# ── Home page (inline, lightweight) ─────────────────────────────────────────
def _render_home():
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.subheader("AI-Powered Onboarding Intelligence for NexaCore Solutions")
    st.markdown(
        """
        SkillSprint AI generates **personalised, role-specific onboarding plans** from
        your company's own policies, SOPs, and role descriptions — and independently
        **validates every generated item** against a structured Role Requirement Matrix.

        ---
        ### How it works
        | Step | Description |
        |------|-------------|
        | 📄 **Upload Documents** | Upload company PDFs/DOCXs — they are parsed, chunked, and stored |
        | 📋 **Requirement Matrix** | Load the ground-truth role → requirement mapping |
        | 🤖 **Generate Plan** | Gemini generates a structured onboarding plan for an employee |
        | ✅ **Validate** | Python pipeline checks coverage, traceability, duplicates & contradictions |
        | 🔍 **Review** | Admin approves, edits, or regenerates flagged items |
        | 📊 **Dashboard** | Track progress across employees and roles |

        ---
        ### Quick start
        1. Go to **📄 Documents** → upload your company documents
        2. Go to **📋 Requirement Matrix** → import the matrix CSV
        3. Go to **🤖 Generate Plan** → select a role and generate a plan
        """
    )

    # Stats row
    from src.database.queries import get_all_documents, get_requirement_count
    docs = get_all_documents()
    req_count = get_requirement_count()

    c1, c2, c3 = st.columns(3)
    c1.metric("Documents Ingested", len(docs))
    c2.metric("Requirements Loaded", req_count)
    c3.metric("Plans Generated", 0)  # updated in Phase 3


# ── Page routing ─────────────────────────────────────────────────────────────
if page == "home":
    _render_home()
elif page == "documents":
    from src.pages.documents import render as _render_docs
    _render_docs()
elif page == "matrix":
    from src.pages.matrix import render as _render_matrix
    _render_matrix()
elif page == "generate":
    st.title("🤖 Generate Onboarding Plan")
    st.info("Coming in Phase 3 — GenAI Pipeline.")
elif page == "validation":
    st.title("✅ Validation Results")
    st.info("Coming in Phase 4 — Python Validation Pipeline.")
elif page == "review":
    st.title("🔍 Manual Review Queue")
    st.info("Coming in Phase 6 — Manual Review.")
elif page == "dashboards":
    st.title("📊 Dashboards")
    st.info("Coming in Phase 8 — Dashboards & UI Polish.")
elif page == "reports":
    st.title("📁 Reports & Export")
    st.info("Coming in Phase 9 — Reports & Export.")
