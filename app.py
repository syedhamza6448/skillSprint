import streamlit as st

st.set_page_config(page_title="SkillSprint AI", page_icon="⚡", layout="wide")

st.title("SkillSprint AI")
st.write("Welcome to the SkillSprint AI Onboarding Planner.")

# Note: In a production environment, this would use real authentication (e.g., OAuth, JWT).
# This simple selectbox is a placeholder for the competition demo to simulate roles.
role_choice = st.selectbox("Select Login Role:", ["Employee", "Admin"])

st.session_state['user_role'] = role_choice

st.success(f"Logged in as {role_choice}")

st.info("Please select a page from the sidebar to continue.")
