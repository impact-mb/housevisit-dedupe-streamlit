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

if uploaded:
    st.success(f"File uploaded: **{uploaded.name}**")

    if st.button("Run DQI Analysis", type="primary"):
        try:
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
            charts_pdf = create_clean_summary_pdf(clean_summary_tables)

            render_dashboard(
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
                output_xlsx,
                charts_pdf,
                uploaded.name,
            )
        except Exception as exc:
            st.error(f"Error: {exc}")
else:
    render_upload_prompt()
