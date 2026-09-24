import streamlit as st
from core.comparison import compare

st.set_page_config(
    page_title="Onboarding Plan — SkillSprint AI",
    page_icon="🎓",
    layout="wide",
)

# ── Shared CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root { --accent: #6366f1; --accent-dark: #4338ca; }

    .page-header {
        background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%);
        border-radius: 12px;
        padding: 1.5rem 2rem;
        color: #fff;
        margin-bottom: 1.5rem;
    }
    .page-header h2 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .page-header p  { margin: 0.3rem 0 0; opacity: 0.85; }

    /* Overall status banner */
    .status-pass {
        background: #dcfce7; border: 1.5px solid #22c55e; border-radius: 12px;
        padding: 1rem 1.5rem; font-size: 1.2rem; font-weight: 700; color: #15803d;
        margin-bottom: 1rem;
    }
    .status-warning {
        background: #fef9c3; border: 1.5px solid #f59e0b; border-radius: 12px;
        padding: 1rem 1.5rem; font-size: 1.2rem; font-weight: 700; color: #a16207;
        margin-bottom: 1rem;
    }
    .status-fail {
        background: #fee2e2; border: 1.5px solid #ef4444; border-radius: 12px;
        padding: 1rem 1.5rem; font-size: 1.2rem; font-weight: 700; color: #b91c1c;
        margin-bottom: 1rem;
    }

    /* Priority badge */
    .pri-high   { background:#fee2e2; color:#b91c1c; padding:2px 8px; border-radius:99px; font-size:0.8rem; font-weight:600; }
    .pri-medium { background:#fef9c3; color:#a16207; padding:2px 8px; border-radius:99px; font-size:0.8rem; font-weight:600; }
    .pri-low    { background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:99px; font-size:0.8rem; font-weight:600; }

    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; color: var(--accent-dark); }

    .role-chip {
        display: inline-block; background: var(--accent); color: #fff;
        padding: 4px 14px; border-radius: 99px; font-weight: 600;
        font-size: 0.85rem; margin-top: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Auth guard ─────────────────────────────────────────────────────────────────
if st.session_state.get("user_role") not in ["Admin", "Employee"]:
    st.warning("🔒 Please login from the Home page first.")
    st.stop()

# ── Sidebar role chip ──────────────────────────────────────────────────────────
_role = st.session_state.get("user_role", "Employee")
_icon = "🛡️" if _role == "Admin" else "👤"
with st.sidebar:
    st.markdown("---")
    st.markdown(
        f"<b>Active Role</b><br><span class='role-chip'>{_icon} {_role}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("SkillSprint AI · Aptech TechWiz7")

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h2>🎓 Generate Onboarding Plan</h2>
        <p>AI-generated, policy-validated personalised onboarding plans.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Role / employee inputs ─────────────────────────────────────────────────────
roles = [
    "Sales Executive", "Customer Support Executive", "HR Executive",
    "Finance Associate", "Operations Coordinator", "Marketing Executive",
    "Software Support Engineer", "Branch/Team Manager", "Data Analyst",
    "DevOps/IT Engineer",
]

input_col1, input_col2, input_col3 = st.columns([2, 2, 1])
with input_col1:
    emp_id = st.text_input("🪪 Employee ID", placeholder="e.g. EMP-001")
with input_col2:
    selected_role = st.selectbox("💼 Role", roles)
with input_col3:
    st.write("")
    st.write("")
    generate_clicked = st.button("🚀 Generate Plan", type="primary", use_container_width=True)

# ── Helper: priority badge HTML ────────────────────────────────────────────────
def _priority_badge(priority: str) -> str:
    p = (priority or "").lower()
    css = "pri-high" if p == "high" else ("pri-medium" if p == "medium" else "pri-low")
    return f'<span class="{css}">{priority or "N/A"}</span>'


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


# ── Generate ───────────────────────────────────────────────────────────────────
if generate_clicked:
    if not emp_id.strip():
        st.error("❌ Please enter an Employee ID before generating.")
    else:
        with st.spinner("⚙️ Running Pipeline 1 (GenAI generation) + Pipeline 2 (validation)…"):
            result = compare(emp_id.strip(), selected_role)

        overall = result["overall_status"]
        p1 = result.get("pipeline1_output")
        p2 = result.get("pipeline2_output")

        st.markdown("---")

        # ── Overall status banner ──────────────────────────────────────────────
        STATUS_HTML = {
            "Pass":              ("status-pass",    "🟢 PASS — All validation checks passed."),
            "Warning":           ("status-warning",  "🟡 WARNING — Minor issues detected; review flags below."),
            "Fail":              ("status-fail",     "🔴 FAIL — Critical validation issues found."),
            "Generation Failed": ("status-fail",     "🔴 GENERATION FAILED — Pipeline 1 could not produce a plan."),
        }
        css_cls, label = STATUS_HTML.get(overall, ("status-fail", f"⚪ {overall}"))
        st.markdown(f'<div class="{css_cls}">{label}</div>', unsafe_allow_html=True)

        if result.get("model_used"):
            st.caption(f"Model: `{result['model_used']}`")

        if overall == "Generation Failed":
            st.error(f"Pipeline 1 error: {p1.get('error', 'Unknown error') if p1 else 'No output returned.'}")
            st.stop()

        # ── Scores row ────────────────────────────────────────────────────────
        if p2:
            flags = p2.get("flags", [])
            c1, c2, c3 = st.columns(3)
            c1.metric("📈 Coverage Score",      f"{p2.get('coverage_score', 0):.1f}%")
            c2.metric("🔗 Traceability Score",  f"{p2.get('traceability_score', 0):.1f}%")
            c3.metric("⚠️ Total Flags",         len(flags))
        else:
            flags = []

        # ── Validation flags ───────────────────────────────────────────────────
        st.markdown("---")
        if flags:
            st.subheader("⚠️ Validation Flags")
            # Group by type for readability
            error_flags   = [f for f in flags if f.get("type") in ("Missing-mandatory", "Unsupported-claim", "Fail")]
            warning_flags = [f for f in flags if f.get("type") in ("Outdated-policy", "Duplicate", "Sequence-violation", "Warning")]
            info_flags    = [f for f in flags if f not in error_flags and f not in warning_flags]

            for flag in error_flags:
                ftype  = flag.get("type", "")
                detail = flag.get("detail", "")
                mname  = flag.get("module_name") or flag.get("requirement_id", "")
                st.error(f"**{ftype}** — `{mname}`: {detail}")

            for flag in warning_flags:
                ftype  = flag.get("type", "")
                detail = flag.get("detail", "")
                mname  = flag.get("module_name") or flag.get("requirement_id", "")
                st.warning(f"**{ftype}** — `{mname}`: {detail}")

            for flag in info_flags:
                ftype  = flag.get("type", "")
                detail = flag.get("detail", "")
                mname  = flag.get("module_name") or flag.get("requirement_id", "")
                st.info(f"**{ftype}** — `{mname}`: {detail}")
        else:
            st.success("✅ No validation flags — all checks passed.")

        # ── Per-requirement verification ───────────────────────────────────────
        per_req = result.get("per_requirement", [])
        if per_req:
            st.markdown("---")
            st.subheader("🔍 Per-Requirement Verification")
            for item in per_req:
                icon  = _item_icon(item["item_status"])
                label = (
                    f"{icon} `{item['requirement_id'][:8]}…` — "
                    f"{item['requirement_text'][:80]}"
                )
                with st.expander(label, expanded=False):
                    col_a, col_b = st.columns(2)
                    col_a.markdown(f"**Item Status:** {item['item_status']}")
                    col_b.markdown(f"**Covered by GenAI:** {'✅ Yes' if item['covered'] else '❌ No'}")
                    st.markdown(f"**Source Section:** `{item.get('source_section', 'N/A')}`")
                    if item["flags"]:
                        st.markdown("**Flags:**")
                        for f in item["flags"]:
                            if f["type"] in ("Missing-mandatory", "Unsupported-claim", "Fail"):
                                st.error(f"`{f['type']}`: {f['detail']}")
                            elif f["type"] in ("Outdated-policy", "Duplicate", "Sequence-violation"):
                                st.warning(f"`{f['type']}`: {f['detail']}")
                            else:
                                st.info(f"`{f['type']}`: {f['detail']}")

        # ── Generated plan ─────────────────────────────────────────────────────
        if p1:
            st.markdown("---")
            plan_emp  = p1.get("employee_id", emp_id)
            plan_role = p1.get("role", selected_role)
            st.subheader(f"📚 Generated Onboarding Plan")
            st.caption(f"Employee: **{plan_emp}** · Role: **{plan_role}**")

            modules = p1.get("modules", [])
            if not modules:
                st.info("No modules were returned in the plan.")
            else:
                for idx, mod in enumerate(modules, 1):
                    mname    = mod.get("module_name", f"Module {idx}")
                    priority = mod.get("priority", "N/A")
                    pri_html = _priority_badge(priority)

                    expander_label = f"📦 Module {idx}: {mname}"
                    with st.expander(expander_label, expanded=False):
                        # Module metadata row
                        st.markdown(
                            f"**Priority:** {pri_html} &nbsp;&nbsp;"
                            f"**Mandatory:** {'✅' if mod.get('mandatory') else '❌'} &nbsp;&nbsp;"
                            f"**Due Stage:** `{mod.get('due_stage', 'N/A')}`",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"**Assessment Topic:** {mod.get('assessment_topic', 'N/A')}  \n"
                            f"**Source Doc:** `{mod.get('source_doc_id', 'N/A')}` · "
                            f"**Section:** `{mod.get('source_section', 'N/A')}`"
                        )

                        # Tasks
                        tasks = mod.get("tasks", [])
                        if tasks:
                            st.markdown("**📝 Tasks:**")
                            for task in tasks:
                                st.markdown(f"- {task}")

                        # Quiz
                        quiz = mod.get("quiz", [])
                        if quiz:
                            st.markdown("**🧩 Quiz:**")
                            for qi, q in enumerate(quiz, 1):
                                st.markdown(f"**Q{qi}.** {q['question']}")
                                opts = q.get("options", [])
                                if opts:
                                    for opt in opts:
                                        st.markdown(f"&nbsp;&nbsp;&nbsp;• {opt}", unsafe_allow_html=True)
                                st.caption(f"✔ Answer: {q.get('answer', '')}")
                                if qi < len(quiz):
                                    st.markdown("---")
