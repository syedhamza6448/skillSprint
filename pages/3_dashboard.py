import streamlit as st
import plotly.express as px
from core.db import get_dashboard_metrics, get_requirements_per_role_df

st.set_page_config(page_title="Dashboard - SkillSprint AI", page_icon="📊", layout="wide")

if st.session_state.get('user_role') != 'Admin':
    st.warning("You must be logged in as an Admin to view this page.")
    st.stop()

st.title("System Dashboard")

try:
    doc_count, chunk_count, req_count = get_dashboard_metrics()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", doc_count)
    col2.metric("Total Chunks", chunk_count)
    col3.metric("Total Matrix Requirements", req_count)
    
    st.divider()
    
    st.header("Requirements per Role")
    df_roles = get_requirements_per_role_df()
    
    if not df_roles.empty:
        fig = px.bar(df_roles, x='role', y='count', title="Requirement Counts by Role",
                     labels={'count': 'Number of Requirements', 'role': 'Role'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for roles.")
        
except Exception as e:
    st.error(f"Error loading dashboard data: {e}")
