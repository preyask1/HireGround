import streamlit as st
import pandas as pd
import sys
import os

# Add parent directory to path to allow importing core and infrastructure
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.persistence.repository import SQLiteJobRepository
from core.domain.models import JobStatus

st.set_page_config(page_title="HireGround Job Copilot", page_icon="🕵️", layout="wide")

def load_data():
    repo = SQLiteJobRepository()
    # Get SCORED jobs
    jobs = repo.get_jobs_by_status(JobStatus.SCORED)
    
    data = []
    for job in jobs:
        score = repo.get_score_for_job(job.id)
        fit_score = score.fit_score if score else 0
        if fit_score > 70:
            data.append({
                "ID": job.id,
                "Company": job.company_id, # Can be enhanced to fetch company name
                "Title": job.title,
                "Location": job.location,
                "URL": job.url,
                "Score": fit_score,
                "Reasoning": score.reasoning_summary if score else ""
            })
            
    return pd.DataFrame(data), repo

st.title("HireGround Job Copilot 🕵️‍♂️")
st.markdown("Review high-scoring jobs and approve them for automatic application.")

df, repo = load_data()

if df.empty:
    st.info("No jobs with a fit score > 70 currently waiting for approval.")
else:
    # Display table
    st.subheader(f"Discovered Jobs ({len(df)})")
    
    for idx, row in df.iterrows():
        with st.expander(f"{row['Score']}/100 - {row['Title']} ({row['Location']})"):
            st.markdown(f"**URL**: [Link]({row['URL']})")
            st.markdown(f"**AI Reasoning**:\n{row['Reasoning']}")
            
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("Approve", key=f"approve_{row['ID']}"):
                    repo.update_job_status(row['ID'], JobStatus.APPROVED)
                    st.success("Approved!")
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject_{row['ID']}"):
                    repo.update_job_status(row['ID'], JobStatus.REJECTED)
                    st.warning("Rejected.")
                    st.rerun()
