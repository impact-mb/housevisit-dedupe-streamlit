"""
House Visit Data Quality Intelligence Platform (DQI)
===================================================

Version 3.1.0
-------------
Performance-optimized Streamlit orchestrator.

Key changes
-----------
1. Uploaded file parsing is cached.
2. Core DQI + Remarks Intelligence analysis is cached.
3. Large Excel/PDF reports are NOT generated during initial analysis.
4. Download reports are prepared only when requested from the Downloads page.
"""

from io import BytesIO
import hashlib

import pandas as pd
import streamlit as st

from dqi.auth import require_login, render_logout_button
from dqi.config import APP_NAME
from dqi.processor import DQIProcessor
from dqi.remarks import RemarksIntelligence
from dqi.ui import (
    inject_css,
    render_dashboard,
    render_header,
    render_upload_prompt,
)


st.set_page_config(
    page_title=APP_NAME,
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(
    show_spinner=False,
    max_entries=5,
)
def read_uploaded_file(
    file_bytes: bytes,
    file_name: str,
) -> pd.DataFrame:
    """Read an uploaded CSV/Excel file once and cache the parsed DataFrame."""
    buffer = BytesIO(file_bytes)
    lower_name = file_name.lower()

    if lower_name.endswith(".csv"):
        return pd.read_csv(buffer)

    return pd.read_excel(buffer)


@st.cache_data(
    show_spinner=False,
    max_entries=5,
)
def run_cached_analysis(
    file_bytes: bytes,
    file_name: str,
):
    """
    Parse and analyse one uploaded file.

    Streamlit caches this result by file content + filename, so reruns caused
    by filters/tabs do not repeat the expensive cleaning and remarks analysis.
    """
    raw_df = read_uploaded_file(
        file_bytes,
        file_name,
    )

    processor = DQIProcessor()
    remarks_engine = RemarksIntelligence()

    (
        full_dataset,
        clean_dataset,
        duplicate_dataset,
        duplicate_summary,
    ) = processor.process(raw_df)

    clean_summary_tables = processor.clean_summary(
        clean_dataset
    )

    (
        remarks_dataset,
        remarks_summary,
        ym_summary,
        repeated_remarks,
        theme_summary,
    ) = remarks_engine.create(
        clean_dataset
    )

    return {
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
    }


require_login()
inject_css()
render_logout_button()
render_header()

uploaded = st.file_uploader(
    "Upload House Visit Data File (.xlsx, .xls, .xlsm, .csv)",
    type=[
        "xlsx",
        "xls",
        "xlsm",
        "csv",
    ],
)

# Session state keeps analysed data available across widget reruns.
if "dqi_result" not in st.session_state:
    st.session_state["dqi_result"] = None

if "dqi_file_key" not in st.session_state:
    st.session_state["dqi_file_key"] = None

# Download packages are intentionally generated later.
if "dqi_download_package" not in st.session_state:
    st.session_state["dqi_download_package"] = None

if uploaded:
    st.success(
        f"File uploaded: **{uploaded.name}**"
    )

    # Read bytes once. A content hash is safer than filename + size because
    # two files can have the same name and byte size but different content.
    uploaded_bytes = uploaded.getvalue()
    file_hash = hashlib.sha256(
        uploaded_bytes
    ).hexdigest()

    file_key = (
        f"{uploaded.name}_{file_hash}"
    )

    # New file = clear previous analysis and generated reports.
    if (
        st.session_state["dqi_file_key"]
        not in (None, file_key)
    ):
        st.session_state["dqi_result"] = None
        st.session_state["dqi_download_package"] = None

    if st.button(
        "Run DQI Analysis",
        type="primary",
    ):
        try:
            with st.spinner(
                "Analysing uploaded data..."
            ):
                result = run_cached_analysis(
                    uploaded_bytes,
                    uploaded.name,
                )

            result["uploaded_name"] = uploaded.name

            st.session_state["dqi_file_key"] = (
                file_key
            )

            st.session_state["dqi_result"] = (
                result
            )

            # A fresh analysis invalidates previously generated reports.
            st.session_state[
                "dqi_download_package"
            ] = None

        except Exception as exc:
            st.error(
                f"Error: {exc}"
            )

    if (
        st.session_state["dqi_result"]
        is not None
        and st.session_state["dqi_file_key"]
        == file_key
    ):
        result = st.session_state[
            "dqi_result"
        ]

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
            result["uploaded_name"],
        )

else:
    st.session_state["dqi_result"] = None
    st.session_state["dqi_file_key"] = None
    st.session_state["dqi_download_package"] = None
    render_upload_prompt()
