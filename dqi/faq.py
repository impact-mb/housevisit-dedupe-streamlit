"""
Module Name : faq.py

Purpose:
--------
Methodology and FAQ content for House Visit DQI.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import streamlit as st
from .config import EXCEL_SHEETS


def render_faq():
    """Render methodology and FAQ page."""
    st.subheader("Methodology / FAQ")
    st.markdown("""
    ### Data privacy / storage
    The app does not save uploaded files to a database or permanent folder. Your file is processed temporarily in the active Streamlit session/runtime to create the dashboard and Excel output. The app is providing a running space for analysis, not a data storage system.

    ### Quality Risk Snapshot
    This table converts important data-quality rates into a simple review band. Current rule: **0–20% = Low**, **21–50% = Watch**, and **above 50% = High**.

    ### Top Themes
    Top Themes are generated from clean unique remarks using keyword mapping. One remark can have multiple themes.

    ### Total Records Uploaded
    Total number of rows read after removing blank rows and Power BI footer rows such as Applied Filters.

    ### Clean Unique House Visits
    The retained dataset after duplicate removal. This is the main denominator used for charts and remarks intelligence.

    ### Duplicate Records Removed
    Repeated records after the first record within the same duplicate key.

    ### Remarks Quality Base
    Equal to Clean Unique House Visits. Remarks analysis is intentionally done on clean data only.

    ### Same Remark Repeated
    Flags records where the exact same cleaned remark is reused within the same operational context: PROGRAM LAUNCH NAME + Sub Type + HOUSE VISIT TYPE + TMO Name + YM Name.

    ### Template-like Remarks
    Rule-based flag for common opening phrases, generic programme phrases, multiple standard keywords, long structured wording, or possible prompt-copy phrases.

    ### Possible AI / Prompt Copy
    Catches obvious prompt-copy artefacts such as `Here is an improved version`, `additional relevant line`, `ChatGPT`, `draft`, or similar wording.

    ### Blank Remarks
    Counts clean unique house visit records where remarks are blank, missing, or equivalent to null-like values.

    ### Duplicate Intelligence
    Duplicate key: PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE.

    ### Remarks Intelligence
    Calculated on clean unique data only. Flags are overlapping and should not be added together.
    """)

    st.markdown("### Download Reports")
    st.write("The Excel output contains these sheets:")
    st.table([{"Sheet": s, "Meaning": m} for s, m in EXCEL_SHEETS])
