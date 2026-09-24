"""
SkillSprint AI — Document Management & Ingestion UI
Upload, validate, parse, chunk, and inspect company documents.
"""

from pathlib import Path
import streamlit as st
import pandas as pd

from src.config.settings import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    SAMPLE_DOCUMENTS_DIR,
)
from src.database.queries import (
    get_all_documents,
    get_chunks_for_document,
    delete_document,
    mark_document_superseded,
)
from src.document_processing.uploader import process_upload, UploadResult


def render() -> None:
    st.title("📄 Document Management & Ingestion")
    st.caption("Upload, validate, chunk, and inspect company policies, SOPs, and role descriptions.")

    tab_upload, tab_view, tab_chunks = st.tabs(["📤 Upload Documents", "📚 Ingested Documents", "🧩 Chunk Inspector"])

    # -------------------------------------------------------------------------
    # TAB 1: UPLOAD DOCUMENTS
    # -------------------------------------------------------------------------
    with tab_upload:
        st.subheader("Upload New Documents")
        st.write(
            f"Supported formats: **{', '.join(ALLOWED_EXTENSIONS)}** | "
            f"Max size: **{MAX_FILE_SIZE_MB} MB** per file."
        )

        col_upload, col_quick = st.columns([2, 1])

        with col_upload:
            uploaded_files = st.file_uploader(
                "Choose PDF or DOCX files",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                help="Files are validated, parsed, chunked by section, and stored in the database.",
            )

            version_override = st.text_input(
                "Version override (optional)",
                placeholder="e.g. v2 (leave blank to infer from filename)",
                help="Applies to all files in this batch if specified.",
            )

            if st.button("🚀 Process & Ingest Files", type="primary", disabled=not uploaded_files):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results: list[UploadResult] = []

                for idx, uf in enumerate(uploaded_files):
                    status_text.text(f"Processing {uf.name} ({idx+1}/{len(uploaded_files)})...")
                    file_bytes = uf.getvalue()
                    res = process_upload(
                        file_bytes=file_bytes,
                        filename=uf.name,
                        version_override=version_override.strip() or None,
                    )
                    results.append(res)
                    progress_bar.progress((idx + 1) / len(uploaded_files))

                status_text.empty()
                progress_bar.empty()

                # Report outcomes
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count

                if success_count > 0:
                    st.success(f"Successfully ingested {success_count} document(s)!")
                if fail_count > 0:
                    st.error(f"{fail_count} file(s) failed validation or ingestion.")

                for r in results:
                    with st.expander(
                        f"{'✅' if r.success else '❌'} {r.filename} — {r.message}",
                        expanded=not r.success,
                    ):
                        if r.success:
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Doc ID", r.document_id)
                            c2.metric("Type", r.file_type.upper())
                            c3.metric("Chunks", r.chunk_count)
                            c4.metric("Chars", f"{r.char_count:,}")
                        if r.warnings:
                            for w in r.warnings:
                                st.warning(f"⚠️ {w}")
                        if r.errors:
                            for e in r.errors:
                                st.error(f"❌ {e}")

        with col_quick:
            st.info("💡 **Quick Ingestion for Evaluation**")
            st.write(
                "Quickly ingest all 22 sample documents from the repository in a balanced mix of "
                "PDF and DOCX formats."
            )
            if st.button("⚡ Ingest All 22 Sample Documents"):
                with st.spinner("Ingesting sample documents..."):
                    sample_dir = Path(SAMPLE_DOCUMENTS_DIR)
                    # Mix of 11 PDFs and 11 DOCXs
                    sample_files = []
                    for i in range(1, 23):
                        doc_num = f"{i:03d}"
                        # Alternating format mix: odd=pdf, even=docx
                        ext = ".pdf" if i % 2 != 0 else ".docx"
                        matching = list(sample_dir.glob(f"DOC-{doc_num}*{ext}"))
                        if matching:
                            sample_files.append(matching[0])

                    progress_bar = st.progress(0)
                    success_count = 0
                    errors = []

                    for idx, sfile in enumerate(sample_files):
                        data = sfile.read_bytes()
                        res = process_upload(data, sfile.name)
                        if res.success:
                            success_count += 1
                        else:
                            errors.extend(res.errors)
                        progress_bar.progress((idx + 1) / len(sample_files))

                    progress_bar.empty()
                    st.success(f"Ingested {success_count}/{len(sample_files)} sample documents!")
                    if errors:
                        for err in errors[:5]:
                            st.warning(err)
                    st.rerun()

    # -------------------------------------------------------------------------
    # TAB 2: INGESTED DOCUMENTS
    # -------------------------------------------------------------------------
    with tab_view:
        docs = get_all_documents()

        if not docs:
            st.info("No documents ingested yet. Upload documents using the 'Upload' tab above.")
        else:
            # Metrics bar
            total_docs = len(docs)
            total_chunks = sum(d["char_count"] for d in docs)
            pdf_count = sum(1 for d in docs if d["file_type"] == "pdf")
            docx_count = sum(1 for d in docs if d["file_type"] == "docx")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Documents", total_docs)
            m2.metric("PDF Documents", pdf_count)
            m3.metric("DOCX Documents", docx_count)
            m4.metric("Total Extracted Chars", f"{total_chunks:,}")

            st.divider()

            # Search bar
            search = st.text_input("🔍 Search documents by ID or filename", "").strip().lower()

            doc_rows = []
            for d in docs:
                if search and (search not in d["document_id"].lower() and search not in d["filename"].lower()):
                    continue
                doc_rows.append(
                    {
                        "ID": d["document_id"],
                        "Filename": d["filename"],
                        "Type": d["file_type"].upper(),
                        "Version": d["version"],
                        "Size (KB)": f"{d['file_size_bytes'] / 1024:.1f}",
                        "Pages": d["page_count"] if d["page_count"] > 0 else "—",
                        "Chars": f"{d['char_count']:,}",
                        "Status": "Superseded" if d["is_superseded"] else d["status"].capitalize(),
                        "Uploaded At": d["uploaded_at"][:19].replace("T", " "),
                    }
                )

            if doc_rows:
                df = pd.DataFrame(doc_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("No documents matched the search filter.")

            st.divider()

            # Document Action: Supersede or Delete
            st.subheader("Document Actions")
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                selected_doc_id = st.selectbox(
                    "Select Document to Manage",
                    options=[d["document_id"] + " — " + d["filename"] for d in docs],
                    key="manage_doc_select",
                )
                target_doc_id = selected_doc_id.split(" — ")[0] if selected_doc_id else ""

            with act_col2:
                btn_del_col, btn_sup_col = st.columns(2)
                with btn_del_col:
                    if st.button("🗑️ Delete Document", type="secondary"):
                        if target_doc_id:
                            delete_document(target_doc_id)
                            st.success(f"Deleted {target_doc_id} and all associated chunks.")
                            st.rerun()

                with btn_sup_col:
                    superseded_by_id = st.text_input("Superseded By (Doc ID)", placeholder="e.g. DOC-003")
                    if st.button("Mark as Superseded"):
                        if target_doc_id and superseded_by_id:
                            mark_document_superseded(target_doc_id, superseded_by_id.strip())
                            st.success(f"Marked {target_doc_id} as superseded by {superseded_by_id}.")
                            st.rerun()

    # -------------------------------------------------------------------------
    # TAB 3: CHUNK INSPECTOR
    # -------------------------------------------------------------------------
    with tab_chunks:
        docs = get_all_documents()
        if not docs:
            st.info("No documents ingested yet.")
        else:
            doc_options = {f"{d['document_id']} — {d['filename']}": d["document_id"] for d in docs}
            selected_label = st.selectbox("Select document to inspect chunks", list(doc_options.keys()))
            selected_id = doc_options[selected_label]

            chunks = get_chunks_for_document(selected_id)
            st.subheader(f"Chunks for {selected_id} ({len(chunks)} sections extracted)")

            if not chunks:
                st.warning("No chunks found for this document.")
            else:
                for c in chunks:
                    title = f"🏷️ **{c['chunk_id']}**"
                    if c["section_number"]:
                        title += f" | Section {c['section_number']}"
                    if c["heading"]:
                        title += f" — {c['heading']}"
                    title += f" ({c['char_count']} chars, {c['page_or_para_ref'] or 'N/A'})"

                    with st.expander(title):
                        st.markdown(c["content"])
                        st.caption(f"Created: {c['created_at']} | Version: {c['version']}")
