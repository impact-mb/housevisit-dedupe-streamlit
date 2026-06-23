"""
House Visit Data Quality Intelligence Platform (DQI)
===================================================

Purpose
-------
Main Streamlit orchestrator for the modular House Visit DQI application.

Core Modules
------------
1. Secure login using Streamlit secrets.
2. Duplicate detection using the agreed business key.
3. Clean unique dataset generation.
4. Leadership dashboard and clean-data summary charts.
5. Spatial Data Analysis using India state-wise house visit map.
6. Remarks Intelligence on clean unique data only.
7. Excel, PDF, and ZIP downloads.

Deployment
----------
Designed for Streamlit Community Cloud using open-source packages.
No Matplotlib is used.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from dqi.auth import require_login, render_logout_button
from dqi.config import APP_NAME
from dqi.exporter import create_clean_summary_pdf, create_excel_outputs
from dqi.processor import DQIProcessor
from dqi.remarks import RemarksIntelligence
from dqi.ui import inject_css, render_dashboard, render_header, render_upload_prompt


st.set_page_config(
    page_title=APP_NAME,
    layout="wide",
    initial_sidebar_state="collapsed",
)

require_login()
inject_css()
render_logout_button()
render_header()

uploaded = st.file_uploader(
    "Upload House Visit Data File (.xlsx, .xls, .xlsm, .csv)",
    type=["xlsx", "xls", "xlsm", "csv"],
)

# Session-state storage keeps the analysed dashboard visible after widget reruns.
# This is important on Streamlit Cloud because users may download reports directly online
# without being able to test locally.
if "dqi_result" not in st.session_state:
    st.session_state["dqi_result"] = None
if "dqi_file_key" not in st.session_state:
    st.session_state["dqi_file_key"] = None

if uploaded:
    st.success(f"File uploaded: **{uploaded.name}**")
    uploaded_size = getattr(uploaded, "size", None)
    file_key = f"{uploaded.name}_{uploaded_size}"

    # If a different file is uploaded, clear the previous analysis.
    if st.session_state["dqi_file_key"] not in (None, file_key):
        st.session_state["dqi_result"] = None

    if st.button("Run DQI Analysis", type="primary"):
        try:
            report_date = datetime.now().strftime("%d %b %Y")
            file_name = uploaded.name.lower()
            if file_name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded)
            else:
                raw_df = pd.read_excel(uploaded)

            processor = DQIProcessor()
            remarks_engine = RemarksIntelligence()

            full_dataset, clean_dataset, duplicate_dataset, duplicate_summary = processor.process(raw_df)
            clean_summary_tables = processor.clean_summary(clean_dataset)
            remarks_dataset, remarks_summary, ym_summary, repeated_remarks, theme_summary = remarks_engine.create(clean_dataset)

            output_xlsx = create_excel_outputs(
                full_dataset,
                clean_dataset,
                duplicate_dataset,
                duplicate_summary,
                clean_summary_tables,
                remarks_dataset,
                remarks_summary,
                ym_summary,
                repeated_remarks,
                theme_summary,
            )
            charts_pdf = create_clean_summary_pdf(clean_summary_tables, report_date=report_date)

            st.session_state["dqi_file_key"] = file_key
            st.session_state["dqi_result"] = {
                "full_dataset": full_dataset,
                "clean_dataset": clean_dataset,
                "duplicate_dataset": duplicate_dataset,
                "duplicate_summary": duplicate_summary,
                "clean_summary_tables": clean_summary_tables,
                "remarks_dataset": remarks_dataset,
                "remarks_summary": remarks_summary,
                "ym_summary": ym_summary,
                "repeated_remarks": repeated_remarks,
                "theme_summary": theme_summary,
                "output_xlsx": output_xlsx,
                "charts_pdf": charts_pdf,
                "uploaded_name": uploaded.name,
            }
        except Exception as exc:
            st.error(f"Error: {exc}")

    if st.session_state["dqi_result"] is not None and st.session_state["dqi_file_key"] == file_key:
        result = st.session_state["dqi_result"]
        render_dashboard(
            result["full_dataset"],
            result["clean_dataset"],
            result["duplicate_dataset"],
            result["duplicate_summary"],
            result["clean_summary_tables"],
            result["remarks_dataset"],
            result["remarks_summary"],
            result["ym_summary"],
            result["repeated_remarks"],
            result["theme_summary"],
            result["output_xlsx"],
            result["charts_pdf"],
            result["uploaded_name"],
        )
else:
    st.session_state["dqi_result"] = None
    st.session_state["dqi_file_key"] = None
    render_upload_prompt()
