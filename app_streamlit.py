import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from __future__ import annotations
import tempfile
import streamlit as st
from cat_underwriting.pipeline import run_pipeline

st.set_page_config(page_title="Cat Treaty Underwriting Assistant", layout="wide")
st.title("Cat Treaty Underwriting Assistant")
st.caption("MVP for extracting treaty terms and triaging catastrophe reinsurance submissions.")

uploaded = st.file_uploader("Upload a treaty slip", type=["pdf", "md", "txt", "csv", "xlsx"])
use_llm = st.checkbox("Use GitHub Models extraction", value=False, help="Requires GITHUB_TOKEN in your environment.")

if uploaded:
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / uploaded.name
        temp_path.write_bytes(uploaded.getvalue())
        assessment = run_pipeline(
            submission_path=temp_path,
            guideline_dir="data/guidelines",
            hazard_scores_path="data/hazard_data/county_hazard_scores.csv",
            historical_losses_path="data/synthetic_losses/historical_losses.csv",
            output_dir="outputs",
            use_llm=use_llm,
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk score", assessment.risk_score)
    col2.metric("Risk tier", assessment.risk_tier.value)
    col3.metric("Flags", len(assessment.flags))

    st.subheader("Underwriter Summary")
    st.write(assessment.underwriter_summary)

    st.subheader("Extracted Terms")
    st.json(assessment.treaty.model_dump(mode="json"))

    st.subheader("Risk Breakdown")
    st.json(assessment.breakdown.model_dump())

    st.subheader("Flags")
    if assessment.flags:
        for flag in assessment.flags:
            st.warning(f"{flag.severity.upper()} / {flag.flag_type}: {flag.message}")
            if flag.evidence:
                st.caption(flag.evidence)
    else:
        st.success("No flags detected.")
else:
    st.info("Upload a sample slip or use data/sample_slips/treaty_slip_hurricane_florida.md from the repo.")
