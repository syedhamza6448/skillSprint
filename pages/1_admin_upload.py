import streamlit as st
import os
import uuid
from core.doc_processing import validate_document, parse_pdf, parse_docx, chunk_document, extract_metadata
from core.db import insert_document, insert_chunks, get_all_requirements_df

st.set_page_config(page_title="Admin Upload - SkillSprint AI", page_icon="📁", layout="wide")

if st.session_state.get('user_role') != 'Admin':
    st.warning("You must be logged in as an Admin to view this page.")
    st.stop()

st.title("Admin Upload & Data View")

st.header("Upload New Policy Document")
uploaded_file = st.file_uploader("Upload PDF or DOCX", type=['pdf', 'docx'])

if uploaded_file is not None:
    if st.button("Process Document"):
        with st.spinner("Processing..."):
            # Save uploaded file to a temporary location for processing
            save_dir = "data/company_docs"
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, uploaded_file.name)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            try:
                file_hash, file_type = validate_document(file_path)
                
                if file_type == '.pdf':
                    raw_blocks = parse_pdf(file_path)
                else:
                    raw_blocks = parse_docx(file_path)
                    
                full_text_start = "\n".join([b['text'] for b in raw_blocks[:20]])
                version, effective_date = extract_metadata(full_text_start)
                
                doc_id = str(uuid.uuid4())
                
                doc_data = {
                    'doc_id': doc_id,
                    'filename': uploaded_file.name,
                    'file_type': file_type,
                    'version': version,
                    'effective_date': effective_date,
                    'file_hash': file_hash
                }
                
                chunks = chunk_document(doc_id, raw_blocks, version)
                
                insert_document(doc_data)
                insert_chunks(chunks)
                
                st.success(f"Successfully processed! New doc_id: `{doc_id}`")
                st.info(f"Extracted {len(chunks)} chunks.")
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {e}")

st.divider()
st.header("Role Requirement Matrix")
try:
    df_reqs = get_all_requirements_df()
    st.dataframe(df_reqs, use_container_width=True)
except Exception as e:
    st.info("No matrix loaded yet.")
