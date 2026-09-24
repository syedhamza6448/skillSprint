"""
pages/3_dashboard.py  —  Phase 8: Admin Dashboard & Manual Review Queue

Shows:
  - KPI metric row (plans generated, avg coverage, avg traceability, total flags)
  - Plans generated per role (bar chart)
  - Status distribution (pie chart)
  - Manual review queue (comparison results != Pass) with Approve/Reject/Regenerate
  - Audit trail: reviewer decisions are stored as linked records; original
    Pipeline 1/2 output is NEVER overwritten.
"""

import json
import streamlit as st
import plotly.express as px
import pandas as pd

from core.db import (
    get_dashboard_metrics,
    get_requirements_per_role_df,
    get_comparison_results_df,
    get_review_queue_df,
    log_review_decision,
    setup_db,
)
from core.comparison import compare

st.set_page_config(
    page_title="Admin Dashboard — SkillSprint AI",
    page_icon="📊",
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

    /* Queue row accent borders */
    .queue-fail    { border-left: 5px solid #ef4444 !important; background: #fff8f8; border-radius: 8px; padding: 0.5rem; margin-bottom: 0.4rem; }
    .queue-warning { border-left: 5px solid #f59e0b !important; background: #fffdf0; border-radius: 8px; padding: 0.5rem; margin-bottom: 0.4rem; }

    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; color: var(--accent-dark); }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }

    .role-chip {
        display: inline-block; background: var(--accent); color: #fff;
        padding: 4px 14px; border-radius: 99px; font-weight: 600;
        font-size: 0.85rem; margin-top: 6px;
    }

    /* Decision badge */
    .dec-approved { background:#dcfce7; color:#15803d; padding:2px 10px; border-radius:99px; font-weight:600; font-size:0.82rem; }
    .dec-rejected { background:#fee2e2; color:#b91c1c; padding:2px 10px; border-radius:99px; font-weight:600; font-size:0.82rem; }
    .dec-pending  { background:#f3f4f6; color:#374151; padding:2px 10px; border-radius:99px; font-weight:600; font-size:0.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Auth guard ────────────────────────────────────────────────────────────────
if st.session_state.get("user_role") != "Admin":
    st.warning("🔒 You must be logged in as an **Admin** to view this page.")
    st.info("Go to the Home page and select **Admin** as your role.")
    st.stop()

# Ensure all tables (including new ones) exist before querying
setup_db()

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
        <h2>📊 Admin Dashboard</h2>
        <p>System KPIs, plan analytics, and manual review queue for flagged onboarding plans.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 1. Top-level KPI metrics ──────────────────────────────────────────────────
try:
    doc_count, chunk_count, req_count = get_dashboard_metrics()
    comp_df = get_comparison_results_df()

    total_plans      = len(comp_df)
    avg_coverage     = comp_df["coverage_score"].mean()     if not comp_df.empty else 0.0
    avg_traceability = comp_df["traceability_score"].mean() if not comp_df.empty else 0.0

    # Count all flags across all runs; compute delta vs prior half of runs
    total_flags = 0
    if not comp_df.empty and "flags_json" in comp_df.columns:
        all_flag_counts = []
        for fj in comp_df["flags_json"].dropna():
            try:
                cnt = len(json.loads(fj))
                total_flags += cnt
                all_flag_counts.append(cnt)
            except (json.JSONDecodeError, TypeError):
                all_flag_counts.append(0)

        # delta: compare last 5 vs previous 5 flag totals
        if len(all_flag_counts) >= 2:
            mid = max(1, len(all_flag_counts) // 2)
            recent_flags = sum(all_flag_counts[mid:])
            older_flags  = sum(all_flag_counts[:mid])
            flag_delta   = recent_flags - older_flags
        else:
            flag_delta = None
    else:
        flag_delta = None

    # Pass rate
    pass_rate = None
    if not comp_df.empty and "overall_status" in comp_df.columns:
        pass_count = (comp_df["overall_status"] == "Pass").sum()
        pass_rate  = round(100 * pass_count / len(comp_df), 1)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📄 Documents Ingested",  doc_count)
    c2.metric("🧩 Chunks Indexed",      chunk_count)
    c3.metric("📋 Matrix Requirements", req_count)
    c4.metric("🤖 Plans Generated",     total_plans)
    c5.metric(
        "⚠️ Total Flags Raised",
        total_flags,
        delta=flag_delta,
        delta_color="inverse",
        help="Delta compares recent half vs older half of plan runs. Negative = improving.",
    )
    c6.metric(
        "✅ Pass Rate",
        f"{pass_rate}%" if pass_rate is not None else "N/A",
        help="Percentage of plans with overall_status = Pass.",
    )

except Exception as exc:
    st.error(f"Error loading KPIs: {exc}")
    comp_df = pd.DataFrame()

st.divider()

# ── 2. Charts — 2-column grid ─────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📦 Plans Generated per Role")
    try:
        if not comp_df.empty:
            role_counts = comp_df.groupby("role").size().reset_index(name="count")
            fig_bar = px.bar(
                role_counts,
                x="role", y="count",
                title="Plans Generated by Role",
                labels={"count": "Plans", "role": "Role"},
                color="count",
                color_continuous_scale="Blues",
            )
            fig_bar.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_tickangle=-30,
                margin=dict(t=40, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No plans generated yet.")
    except Exception as exc:
        st.error(f"Chart error: {exc}")

with chart_col2:
    st.subheader("🥧 Verification Status Distribution")
    try:
        if not comp_df.empty:
            status_counts = comp_df.groupby("overall_status").size().reset_index(name="count")
            STATUS_COLORS = {
                "Pass":              "#22c55e",
                "Warning":           "#f59e0b",
                "Fail":              "#ef4444",
                "Generation Failed": "#7c3aed",
            }
            fig_pie = px.pie(
                status_counts,
                names="overall_status",
                values="count",
                title="Plan Status Distribution",
                color="overall_status",
                color_discrete_map=STATUS_COLORS,
                hole=0.4,
            )
            fig_pie.update_layout(
                margin=dict(t=40, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No status data yet.")
    except Exception as exc:
        st.error(f"Chart error: {exc}")

# ── 3. Second chart row ────────────────────────────────────────────────────────
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.subheader("📈 Avg Traceability Score per Role")
    try:
        if not comp_df.empty:
            trace_df = comp_df.groupby("role")["traceability_score"].mean().reset_index()
            trace_df.columns = ["role", "avg_traceability"]
            fig_trace = px.bar(
                trace_df, x="role", y="avg_traceability",
                title="Avg Traceability Score by Role (%)",
                labels={"avg_traceability": "Avg Traceability (%)", "role": "Role"},
                color="avg_traceability",
                color_continuous_scale="Greens",
                range_y=[0, 100],
            )
            fig_trace.update_layout(
                coloraxis_showscale=False,
                xaxis_tickangle=-30,
                margin=dict(t=40, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_trace, use_container_width=True)
        else:
            st.info("No data yet.")
    except Exception as exc:
        st.error(f"Chart error: {exc}")

with chart_col4:
    st.subheader("📊 Avg Coverage Score per Role")
    try:
        if not comp_df.empty:
            cov_df = comp_df.groupby("role")["coverage_score"].mean().reset_index()
            cov_df.columns = ["role", "avg_coverage"]
            fig_cov = px.bar(
                cov_df, x="role", y="avg_coverage",
                title="Avg Coverage Score by Role (%)",
                labels={"avg_coverage": "Avg Coverage (%)", "role": "Role"},
                color="avg_coverage",
                color_continuous_scale="Purples",
                range_y=[0, 100],
            )
            fig_cov.update_layout(
                coloraxis_showscale=False,
                xaxis_tickangle=-30,
                margin=dict(t=40, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_cov, use_container_width=True)
        else:
            st.info("No data yet.")
    except Exception as exc:
        st.error(f"Chart error: {exc}")

st.divider()

# ── 4. Manual Review Queue ────────────────────────────────────────────────────
st.subheader("🔍 Manual Review Queue")
st.caption(
    "All plans with status **Warning**, **Fail**, or **Generation Failed**. "
    "Approve/Reject actions are stored as audit records — original outputs are **never** overwritten."
)

try:
    queue_df = get_review_queue_df()
except Exception as exc:
    st.error(f"Could not load review queue: {exc}")
    queue_df = pd.DataFrame()

if queue_df.empty:
    st.success("✅ Review queue is empty — no flagged plans require attention.")
else:
    STATUS_ICON = {
        "Warning":           "🟡",
        "Fail":              "🔴",
        "Generation Failed": "🔴",
    }

    for _, row in queue_df.iterrows():
        cid        = row["comparison_id"]
        emp_id     = row["employee_id"]
        role       = row["role"]
        status     = row["overall_status"]
        cov        = row.get("coverage_score", 0) or 0
        trace      = row.get("traceability_score", 0) or 0
        ts         = row.get("timestamp", "")
        decision   = row.get("reviewer_decision")
        notes_prev = row.get("reviewer_notes", "")

        # Parse flags
        flags = []
        try:
            flags = json.loads(row.get("flags_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            pass

        icon = STATUS_ICON.get(status, "⚪")

        # Decision badge
        if decision == "Approved":
            dec_html = '<span class="dec-approved">✅ Approved</span>'
        elif decision == "Rejected":
            dec_html = '<span class="dec-rejected">❌ Rejected</span>'
        else:
            dec_html = '<span class="dec-pending">⏳ Pending</span>'

        # Colour band class for the row (applied via markdown inside expander)
        row_css = "queue-fail" if status in ("Fail", "Generation Failed") else "queue-warning"

        header = (
            f"{icon} **{emp_id}** — {role} &nbsp;|&nbsp; "
            f"Status: `{status}` &nbsp;|&nbsp; "
            f"Flags: **{len(flags)}** &nbsp;|&nbsp; "
            f"Coverage: **{cov:.0f}%** &nbsp;|&nbsp; "
            f"_{ts}_"
        )

        with st.expander(header, expanded=(decision is None)):
            # Colour-coded marker strip
            st.markdown(
                f'<div class="{row_css}">Decision: {dec_html} &nbsp;|&nbsp; '
                f'Coverage: <b>{cov:.1f}%</b> &nbsp;|&nbsp; '
                f'Traceability: <b>{trace:.1f}%</b></div>',
                unsafe_allow_html=True,
            )

            # Flags breakdown — styled, colour-coded
            if flags:
                st.markdown("**⚠️ Validation Flags:**")
                error_flags   = [f for f in flags if f.get("type") in ("Fail", "Missing-mandatory", "Unsupported-claim")]
                warning_flags = [f for f in flags if f.get("type") in ("Warning", "Outdated-policy", "Duplicate")]
                info_flags    = [f for f in flags if f not in error_flags and f not in warning_flags]

                for f in error_flags:
                    st.error(f"`{f.get('type', '')}` — {f.get('module_name') or f.get('requirement_id', '')}: {f.get('detail', '')}")
                for f in warning_flags:
                    st.warning(f"`{f.get('type', '')}` — {f.get('module_name') or f.get('requirement_id', '')}: {f.get('detail', '')}")
                for f in info_flags:
                    st.info(f"`{f.get('type', '')}` — {f.get('module_name') or f.get('requirement_id', '')}: {f.get('detail', '')}")
            else:
                st.caption("_No flag details stored._")

            if decision:
                st.info(
                    f"**Current Decision:** {decision}"
                    + (f" — _{notes_prev}_" if notes_prev else "")
                )

            # Reviewer notes
            notes_key = f"notes_{cid}"
            notes = st.text_area(
                "📝 Reviewer notes (optional — stored in audit trail)",
                key=notes_key,
                placeholder="Add context or reasoning for this decision…",
                height=68,
            )

            # Action buttons — neatly side-by-side
            b1, b2, b3, _spacer = st.columns([1, 1, 1, 1])

            if b1.button("✅ Approve", key=f"approve_{cid}", use_container_width=True):
                log_review_decision(
                    comparison_id=cid,
                    employee_id=emp_id,
                    role=role,
                    original_status=status,
                    reviewer_decision="Approved",
                    reviewer_notes=notes or "",
                )
                st.success(f"✅ Approved: **{emp_id}** / {role}")
                st.rerun()

            if b2.button("❌ Reject", key=f"reject_{cid}", use_container_width=True):
                log_review_decision(
                    comparison_id=cid,
                    employee_id=emp_id,
                    role=role,
                    original_status=status,
                    reviewer_decision="Rejected",
                    reviewer_notes=notes or "",
                )
                st.warning(f"❌ Rejected: **{emp_id}** / {role}")
                st.rerun()

            if b3.button("🔄 Regenerate", key=f"regen_{cid}", use_container_width=True):
                with st.spinner(f"Regenerating plan for {emp_id} / {role}…"):
                    new_result = compare(emp_id, role)
                new_status = new_result.get("overall_status", "Unknown")
                st.info(
                    f"🔄 Regenerated. New status: **{new_status}**. "
                    "A new comparison record has been saved — original is preserved."
                )
                st.rerun()

st.divider()

# ── 5. Full comparison history table ─────────────────────────────────────────
with st.expander("📜 Full Comparison History", expanded=False):
    try:
        if not comp_df.empty:
            display_df = comp_df[[
                "employee_id", "role", "overall_status",
                "coverage_score", "traceability_score", "timestamp"
            ]].copy()
            display_df.columns = [
                "Employee ID", "Role", "Status",
                "Coverage %", "Traceability %", "Timestamp"
            ]
            display_df["Coverage %"]     = display_df["Coverage %"].round(1)
            display_df["Traceability %"] = display_df["Traceability %"].round(1)

            def _style_status(val):
                colors = {
                    "Pass":    "background-color:#dcfce7; color:#15803d; font-weight:600",
                    "Warning": "background-color:#fef9c3; color:#a16207; font-weight:600",
                    "Fail":    "background-color:#fee2e2; color:#b91c1c; font-weight:600",
                }
                return colors.get(val, "")

            styled = display_df.style.applymap(_style_status, subset=["Status"])

            st.dataframe(
                styled,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Coverage %":     st.column_config.NumberColumn(format="%.1f%%"),
                    "Traceability %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Timestamp":      st.column_config.TextColumn(width="medium"),
                },
            )
        else:
            st.info("No comparison history yet.")
    except Exception as exc:
        st.error(f"Error loading history: {exc}")
