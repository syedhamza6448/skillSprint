import streamlit as st
from core.comparison import compare

st.set_page_config(page_title="Employee Plan - SkillSprint AI", page_icon="🎓", layout="wide")

if st.session_state.get('user_role') not in ['Admin', 'Employee']:
    st.warning("Please login from the main page.")
    st.stop()

st.title("Generate Onboarding Plan")

roles = [
    "Sales Executive", "Customer Support Executive", "HR Executive",
    "Finance Associate", "Operations Coordinator", "Marketing Executive",
    "Software Support Engineer", "Branch/Team Manager", "Data Analyst",
    "DevOps/IT Engineer"
]

emp_id = st.text_input("Employee ID (e.g. EMP-001)")
selected_role = st.selectbox("Select Role", roles)

# ── Status badge helper ────────────────────────────────────────────────────────
def _status_badge(status: str) -> str:
    COLORS = {
        "Pass":               "🟢",
        "Warning":            "🟡",
        "Fail":               "🔴",
        "Generation Failed":  "🔴",
    }
    icon = COLORS.get(status, "⚪")
    return f"{icon} **{status}**"

def _item_icon(item_status: str) -> str:
    if item_status == "Verified":
        return "✅"
    if item_status == "Verified with Warning":
        return "⚠️"
    if item_status in ("Requirement Missing", "Fail"):
        return "❌"
    if item_status == "Outdated Source":
        return "🕰️"
    if item_status == "Unsupported Requirement":
        return "🚫"
    return "ℹ️"

# ── Generate Plan button ───────────────────────────────────────────────────────
if st.button("Generate Plan"):
    if not emp_id:
        st.error("Please enter an Employee ID.")
    else:
        with st.spinner("Running Pipeline 1 (GenAI generation) + Pipeline 2 (validation)…"):
            result = compare(emp_id, selected_role)

        overall = result["overall_status"]
        p1      = result.get("pipeline1_output")
        p2      = result.get("pipeline2_output")

        # ── Overall status badge ───────────────────────────────────────────────
        st.markdown("---")
        st.subheader("Verification Status")
        st.markdown(f"### {_status_badge(overall)}")
        if result.get("model_used"):
            st.caption(f"Model used: `{result['model_used']}`")

        # ── Generation Failed guard ────────────────────────────────────────────
        if overall == "Generation Failed":
            st.error(f"Pipeline 1 failed to generate a plan: {p1.get('error', 'Unknown error')}")
            st.stop()

        # ── Pipeline 2 flags (prominent, above the plan) ──────────────────────
        flags = p2.get("flags", []) if p2 else []
        if flags:
            st.markdown("---")
            st.subheader("⚠️ Validation Flags")
            for flag in flags:
                ftype  = flag.get("type", "")
                detail = flag.get("detail", "")
                mname  = flag.get("module_name") or flag.get("requirement_id", "")
                if ftype == "Outdated-policy":
                    st.warning(f"**{ftype}** — `{mname}`: {detail}")
                elif ftype == "Unsupported-claim":
                    st.error(f"**{ftype}** — `{mname}`: {detail}")
                elif ftype == "Duplicate":
                    st.warning(f"**{ftype}** — `{mname}`: {detail}")
                elif ftype == "Missing-mandatory":
                    st.error(f"**{ftype}** — requirement `{mname}` not covered")
                else:
                    st.info(f"**{ftype}** — `{mname}`: {detail}")
        else:
            st.success("No validation flags — all checks passed.")

        # ── Pipeline 2 scores ─────────────────────────────────────────────────
        if p2:
            col1, col2 = st.columns(2)
            col1.metric("Coverage Score",      f"{p2.get('coverage_score', 0):.1f}%")
            col2.metric("Traceability Score",  f"{p2.get('traceability_score', 0):.1f}%")

        # ── Per-requirement verification table ────────────────────────────────
        per_req = result.get("per_requirement", [])
        if per_req:
            st.markdown("---")
            st.subheader("Per-Requirement Verification")
            for item in per_req:
                icon   = _item_icon(item["item_status"])
                label  = f"{icon} `{item['requirement_id'][:8]}…` — {item['requirement_text'][:80]}"
                with st.expander(label):
                    st.write(f"**Item Status:** {item['item_status']}")
                    st.write(f"**Covered by GenAI:** {'Yes' if item['covered'] else 'No'}")
                    st.write(f"**Source Section:** `{item.get('source_section', 'N/A')}`")
                    if item["flags"]:
                        st.write("**Flags:**")
                        for f in item["flags"]:
                            st.write(f"- `{f['type']}`: {f['detail']}")

        # ── Generated plan (modules / tasks / quiz) ───────────────────────────
        if p1:
            st.markdown("---")
            st.subheader(f"Generated Plan: {p1.get('employee_id', emp_id)} ({p1.get('role', selected_role)})")

            for mod in p1.get("modules", []):
                header = f"Module: {mod['module_name']} (Priority: {mod.get('priority', 'N/A')})"
                with st.expander(header):
                    st.write(f"**Mandatory:** {mod.get('mandatory', 'N/A')}")
                    st.write(f"**Due Stage:** {mod.get('due_stage', 'N/A')}")
                    st.write(f"**Assessment Topic:** {mod.get('assessment_topic', 'N/A')}")
                    st.write(f"**Source Doc ID:** `{mod.get('source_doc_id', 'N/A')}`")
                    st.write(f"**Source Section:** `{mod.get('source_section', 'N/A')}`")

                    tasks = mod.get("tasks", [])
                    if tasks:
                        st.write("**Tasks:**")
                        for task in tasks:
                            st.write(f"- {task}")

                    quiz = mod.get("quiz", [])
                    if quiz:
                        st.write("**Quiz:**")
                        for q in quiz:
                            st.write(f"- Q: {q['question']}")
                            st.write(f"  Options: {', '.join(q.get('options', []))}")
                            st.write(f"  *Answer: {q.get('answer', '')}*")
