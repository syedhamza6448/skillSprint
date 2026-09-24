import streamlit as st
import os
import uuid
from core.doc_processing import validate_document, parse_pdf, parse_docx, chunk_document, extract_metadata
from core.db import insert_document, insert_chunks, get_all_requirements_df

st.set_page_config(
    page_title="Admin Upload — SkillSprint AI",
    page_icon="📁",
    layout="wide",
)

# ── Shared CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root { --accent: #6366f1; --accent-dark: #4338ca; }
    .ss-card {
        background: #fff;
        border: 1px solid #e0e7ff;
        border-left: 5px solid var(--accent);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 6px rgba(99,102,241,0.07);
    }
    .page-header {
        background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        color: #fff;
        margin-bottom: 1.5rem;
    }
    .page-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .page-header p  { margin: 0.3rem 0 0; opacity: 0.85; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; color: var(--accent-dark); }
    .role-chip {
        display: inline-block; background: var(--accent); color: #fff;
        padding: 4px 14px; border-radius: 99px; font-weight: 600; font-size: 0.85rem; margin-top: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Auth guard ─────────────────────────────────────────────────────────────────
if st.session_state.get("user_role") != "Admin":
    st.warning("🔒 You must be logged in as an **Admin** to view this page.")
    st.info("Go to the Home page and select **Admin** as your role.")
    st.stop()

# ── Sidebar role chip ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown(
        "<b>Active Role</b><br><span class='role-chip'>🛡️ Admin</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("SkillSprint AI · Aptech TechWiz7")

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h2>📁 Admin — Document Upload &amp; Matrix View</h2>
        <p>Upload policy PDFs/DOCX, auto-parse, and inspect the Role Requirement Matrix.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Upload section ─────────────────────────────────────────────────────────────
st.subheader("📤 Upload New Policy Document")

uploaded_file = st.file_uploader(
    "Drop a PDF or DOCX file here, or click to browse",
    type=["pdf", "docx"],
    help="Supported formats: PDF, DOCX. File will be parsed, chunked, and stored.",
)

if uploaded_file is not None:
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        process_clicked = st.button("⚙️ Process Document", type="primary", use_container_width=True)
    with col_info:
        st.caption(f"File ready: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    if process_clicked:
        with st.spinner("🔄 Parsing, chunking, and storing document…"):
            save_dir = "data/company_docs"
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, uploaded_file.name)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                file_hash, file_type = validate_document(file_path)

                if file_type == ".pdf":
                    raw_blocks = parse_pdf(file_path)
                else:
                    raw_blocks = parse_docx(file_path)

                full_text_start = "\n".join([b["text"] for b in raw_blocks[:20]])
                version, effective_date = extract_metadata(full_text_start)

                doc_id = str(uuid.uuid4())

                doc_data = {
                    "doc_id": doc_id,
                    "filename": uploaded_file.name,
                    "file_type": file_type,
                    "version": version,
                    "effective_date": effective_date,
                    "file_hash": file_hash,
                }

                chunks = chunk_document(doc_id, raw_blocks, version)

                insert_document(doc_data)
                insert_chunks(chunks)

                # ── Success summary ────────────────────────────────────────────
                st.success(f"✅ **Document processed successfully!**")

                m1, m2, m3 = st.columns(3)
                m1.metric("📄 File", uploaded_file.name)
                m2.metric("🧩 Chunks Created", len(chunks))
                m3.metric("🔖 Version Detected", version or "N/A")

                with st.expander("🆔 Document Details", expanded=False):
                    st.markdown(f"- **Doc ID:** `{doc_id}`")
                    st.markdown(f"- **File Type:** `{file_type}`")
                    st.markdown(f"- **Effective Date:** `{effective_date or 'Not detected'}`")
                    st.markdown(f"- **SHA-256 Hash:** `{file_hash}`")

            except Exception as e:
                st.error(f"❌ **Processing failed for `{uploaded_file.name}`**")
                with st.expander("Error details"):
                    st.code(str(e))

st.divider()

# ── Role Requirement Matrix ────────────────────────────────────────────────────
st.subheader("📋 Role Requirement Matrix")
st.caption("All role-based requirements extracted from ingested policy documents.")

try:
    df_reqs = get_all_requirements_df()
    if df_reqs.empty:
        st.info("ℹ️ No requirements loaded yet. Upload and process a document above.")
    else:
        # Build column config for readability
        col_cfg = {}

        if "requirement_text" in df_reqs.columns:
            col_cfg["requirement_text"] = st.column_config.TextColumn(
                "Requirement", width="large"
            )
        if "role" in df_reqs.columns:
            col_cfg["role"] = st.column_config.TextColumn("Role", width="medium")
        if "priority" in df_reqs.columns:
            col_cfg["priority"] = st.column_config.TextColumn("Priority", width="small")
        if "mandatory" in df_reqs.columns:
            col_cfg["mandatory"] = st.column_config.CheckboxColumn("Mandatory")

        st.dataframe(
            df_reqs,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg if col_cfg else None,
        )
        st.caption(f"Showing **{len(df_reqs)}** requirement(s) across all roles and documents.")

except Exception as e:
    st.info("ℹ️ No matrix loaded yet — upload a document to populate the table.")
