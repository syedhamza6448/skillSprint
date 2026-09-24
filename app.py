import streamlit as st

st.set_page_config(
    page_title="SkillSprint AI — Onboarding Planner",
    page_icon="⚡",
    layout="wide",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Accent palette ── */
    :root {
        --accent: #6366f1;          /* indigo-500 */
        --accent-light: #818cf8;    /* indigo-400 */
        --accent-dark: #4338ca;     /* indigo-700 */
        --pass-bg: #dcfce7;
        --pass-fg: #15803d;
        --warn-bg: #fef9c3;
        --warn-fg: #a16207;
        --fail-bg: #fee2e2;
        --fail-fg: #b91c1c;
    }

    /* ── Hero banner ── */
    .ss-hero {
        background: linear-gradient(135deg, #4338ca 0%, #6366f1 50%, #818cf8 100%);
        border-radius: 16px;
        padding: 2.5rem 2rem 2rem 2rem;
        color: #fff;
        margin-bottom: 1.5rem;
    }
    .ss-hero h1 { font-size: 2.6rem; font-weight: 800; margin: 0; letter-spacing: -1px; }
    .ss-hero p  { font-size: 1.1rem; opacity: 0.9; margin: 0.4rem 0 0 0; }

    /* ── Card / container ── */
    .ss-card {
        background: #fff;
        border: 1px solid #e0e7ff;
        border-left: 5px solid var(--accent);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 6px rgba(99,102,241,0.07);
    }

    /* ── Status badges ── */
    .badge-pass    { background:var(--pass-bg); color:var(--pass-fg); padding:3px 10px; border-radius:99px; font-weight:600; font-size:0.9rem; }
    .badge-warning { background:var(--warn-bg); color:var(--warn-fg); padding:3px 10px; border-radius:99px; font-weight:600; font-size:0.9rem; }
    .badge-fail    { background:var(--fail-bg); color:var(--fail-fg); padding:3px 10px; border-radius:99px; font-weight:600; font-size:0.9rem; }

    /* ── Metric card tweaks ── */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; color: var(--accent-dark); }

    /* ── Sidebar role chip ── */
    .role-chip {
        display: inline-block;
        background: var(--accent);
        color: #fff;
        padding: 4px 14px;
        border-radius: 99px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-top: 6px;
    }

    /* ── Section spacing ── */
    .section-gap { margin-top: 2rem; }

    /* ── Queue row colour bands ── */
    .queue-fail    { border-left: 5px solid #ef4444 !important; }
    .queue-warning { border-left: 5px solid #f59e0b !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero banner ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="ss-hero">
        <h1>⚡ SkillSprint AI</h1>
        <p>Intelligent Onboarding Planner — powered by Generative AI &amp; Ground-Truth Validation</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Role selector ──────────────────────────────────────────────────────────────
col_role, col_info = st.columns([1, 2])

with col_role:
    st.markdown('<div class="ss-card">', unsafe_allow_html=True)
    st.subheader("🔐 Select Your Role")
    role_choice = st.selectbox(
        "Login as:",
        ["Employee", "Admin"],
        key="role_selectbox",
        label_visibility="collapsed",
    )
    st.session_state["user_role"] = role_choice
    st.success(f"Logged in as **{role_choice}**")
    st.markdown("</div>", unsafe_allow_html=True)

with col_info:
    if role_choice == "Admin":
        st.markdown(
            """
            <div class="ss-card">
            <strong>Admin access enabled.</strong><br>
            You can upload policy documents, view the Role Requirement Matrix,
            monitor system-wide KPIs, and manage the manual review queue.<br><br>
            👉 Use the <b>sidebar</b> to navigate.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="ss-card">
            <strong>Employee access enabled.</strong><br>
            Enter your Employee ID, select your role, and generate a personalised
            onboarding plan that is validated against company policy in real time.<br><br>
            👉 Use the <b>sidebar</b> to navigate.
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Sidebar role indicator (shared across all pages via session_state) ─────────
with st.sidebar:
    st.markdown("---")
    role_label = st.session_state.get("user_role", "Not set")
    icon = "🛡️" if role_label == "Admin" else "👤"
    st.markdown(
        f"**Active Role**<br><span class='role-chip'>{icon} {role_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("SkillSprint AI · Aptech TechWiz7")
