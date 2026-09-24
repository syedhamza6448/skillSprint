"""
SkillSprint AI — Requirement Matrix Viewer & Loader UI
Inspect the role requirement matrix ground truth.
"""

from pathlib import Path
import streamlit as st
import pandas as pd

from src.config.settings import MATRIX_CSV_PATH
from src.database.queries import (
    get_all_requirements,
    get_distinct_roles,
    get_distinct_departments,
    get_requirements_for_role,
    get_requirement_count,
)
from src.database.load_sample_matrix import load_matrix


def render() -> None:
    st.title("📋 Role Requirement Matrix")
    st.caption("Ground-truth mapping: Roles ➔ Mandatory & Optional Requirements ➔ Source Documents.")

    count = get_requirement_count()

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.write(
            f"Currently loaded: **{count} requirements** in the database. "
            "This matrix serves as the ground truth for Python validation in later phases."
        )
    with col_btn:
        if st.button("🔄 Import / Reload Matrix", type="primary"):
            with st.spinner("Loading matrix from CSV..."):
                loaded = load_matrix(str(MATRIX_CSV_PATH))
                st.success(f"Successfully loaded {loaded} requirements!")
                st.rerun()

    if count == 0:
        st.warning("No requirements in the database yet. Click **Import / Reload Matrix** above to load the CSV.")
        return

    # Filter row
    roles = get_distinct_roles()
    departments = get_distinct_departments()

    f1, f2, f3 = st.columns(3)
    with f1:
        sel_role = st.selectbox("Filter by Role", ["All Roles"] + roles)
    with f2:
        sel_dept = st.selectbox("Filter by Department", ["All Departments"] + departments)
    with f3:
        sel_mand = st.selectbox("Filter by Mandate", ["All", "Mandatory Only", "Optional Only"])

    # Query
    if sel_role != "All Roles":
        reqs = get_requirements_for_role(sel_role)
    else:
        reqs = get_all_requirements()

    # Apply remaining filters in-memory
    filtered = []
    for r in reqs:
        if sel_dept != "All Departments" and r["department"] != sel_dept:
            continue
        if sel_mand == "Mandatory Only" and r["mandatory_optional"].lower() != "mandatory":
            continue
        if sel_mand == "Optional Only" and r["mandatory_optional"].lower() != "optional":
            continue
        filtered.append(dict(r))

    st.subheader(f"Requirements ({len(filtered)} items)")

    if not filtered:
        st.info("No requirements match the selected filters.")
        return

    df = pd.DataFrame(filtered)
    # Display friendly column order
    cols_to_show = [
        "requirement_id", "role_id", "role_name", "department",
        "task_name", "mandatory_optional", "priority",
        "source_document_id", "source_section_id"
    ]
    existing_cols = [c for c in cols_to_show if c in df.columns]
    st.dataframe(df[existing_cols], use_container_width=True, hide_index=True)
