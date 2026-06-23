"""
Module Name : ui.py

Purpose:
--------
Streamlit UI rendering for House Visit DQI dashboard tabs and leadership views.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import base64
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from .charts import render_chart_box, render_labeled_bar_chart
from .config import APP_NAME, APP_VERSION, BUILD, OWNER, SPORTS_QUOTES
from .faq import render_faq
from .processor import pct
from .spatial import render_india_state_map
from .exporter import create_zip_bundle, excel_sheet_explanation_df


def inject_css():
    """Load dashboard CSS."""
    st.markdown(
        """
        <style>
            .main { background-color: #FAFAF7; }
            .center-title {text-align:center;font-size:34px;font-weight:850;color:#1f2937;margin-top:4px;margin-bottom:2px;}
            .center-subtitle {text-align:center;font-size:15px;color:#4b5563;margin-bottom:20px;}
            .quote-card {background:#fff7e6;border-left:6px solid #f59e0b;border-radius:14px;padding:15px 18px;color:#374151;font-size:15px;min-height:92px;box-shadow:0px 2px 8px rgba(0,0,0,0.03);}
            .date-card {background:#eef6ff;border-left:6px solid #2563eb;border-radius:14px;padding:15px 18px;color:#1f2937;font-size:15px;min-height:92px;text-align:right;box-shadow:0px 2px 8px rgba(0,0,0,0.03);}
            .section-card {background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;margin-top:10px;margin-bottom:10px;box-shadow:0px 2px 8px rgba(0,0,0,0.03);}
            .metric-note {font-size:13px;color:#6b7280;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def clickable_logo(img_path: str, link_url: str, width: int = 130):
    """Render clickable logo when available."""
    try:
        img_bytes = Path(img_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode()
        st.markdown(
            f"""
            <div style="text-align: center;">
                <a href="{link_url}" target="_blank">
                    <img src="data:image/png;base64,{encoded}" width="{width}" />
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        st.warning("Logo file not found. Please keep 'magicbus_logo.png' in the same folder.")


def render_header():
    """Render application header with centered title, quote, and report date."""
    clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=130)
    today = datetime.now().strftime("%d %b %Y")
    quote = SPORTS_QUOTES[datetime.now().day % len(SPORTS_QUOTES)]

    st.markdown(f'<div class="center-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="center-subtitle">Version {APP_VERSION} • Build {BUILD} • Owner: {OWNER}<br>Duplicate Detection • Clean Data Summary • Spatial Analysis • Remarks Intelligence • Field Data Quality</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([2, 1])
    with left:
        st.markdown(f'<div class="quote-card"><b>Sports mindset for data quality</b><br>“{quote}”</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div class="date-card"><b>Report Date</b><br>{today}<br><span class="metric-note">System date from deployment server</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        """
        <div class="section-card">
        <b>Data privacy note:</b> This app does not store uploaded data in any database or permanent storage. The uploaded file is processed temporarily in the running Streamlit session/runtime to generate the dashboard and downloadable reports. Once the session ends or the app reruns, the app does not retain your dataset.<br><br>
        <b>How to read this dashboard:</b><br>
        Duplicate records are identified first and removed from the clean dataset. Clean-data summaries and remarks intelligence are calculated only on the <b>Clean Unique Dataset</b>. Same Remark Repeated, Template-like Remarks, AI/Prompt Copy, and Blank Remarks are overlapping quality flags and should not be added together.
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_risk_label(rate: float) -> str:
    """Simple executive risk banding for rates."""
    if rate <= 20:
        return "Low"
    if rate <= 50:
        return "Watch"
    return "High"


def render_dashboard(full_dataset, clean_dataset, duplicate_dataset, duplicate_summary,
                     clean_summary_tables, remarks_dataset, remarks_summary, ym_summary,
                     repeated_remarks, theme_summary, output_xlsx, charts_pdf, uploaded_name: str):
    """Render complete dashboard after analysis."""
    total_records = len(full_dataset)
    clean_records = len(clean_dataset)
    duplicate_records = len(duplicate_dataset)
    duplicate_rate = pct(duplicate_records, total_records)

    same_remark_count = int(remarks_dataset["Same_Remark_Repeated"].sum())
    template_flag_count = int(remarks_dataset["Template_Flag"].sum())
    blank_remarks_count = int(remarks_dataset["Blank_Remark"].sum())
    ai_prompt_count = int(remarks_dataset["Possible_AI_Prompt_Copy"].sum())

    same_remark_rate = pct(same_remark_count, clean_records)
    template_rate = pct(template_flag_count, clean_records)
    blank_rate = pct(blank_remarks_count, clean_records)
    ai_rate = pct(ai_prompt_count, clean_records)

    base_name = uploaded_name.rsplit(".", 1)[0]
    output_name = f"{base_name}_DQI_Intelligence_Output.xlsx"
    charts_pdf_name = f"{base_name}_Clean_Data_Summary_Report.pdf"
    zip_name = f"{base_name}_DQI_Intelligence_Bundle.zip"

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Leadership Overview",
        "Clean Data Summary",
        "Spatial Data Analysis",
        "Duplicate Intelligence",
        "Remarks Intelligence",
        "Methodology / FAQ",
        "Downloads",
    ])

    with tab1:
        st.subheader("Leadership Data Quality Overview")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Records Uploaded", f"{total_records:,}")
        k2.metric("Clean Unique House Visits", f"{clean_records:,}")
        k3.metric("Duplicate Records Removed", f"{duplicate_records:,}")
        k4.metric("Remarks Quality Base", f"{clean_records:,}")

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("Same Remark Repeated", f"{same_remark_count:,}")
        k6.metric("Template-like Remarks", f"{template_flag_count:,}")
        k7.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}")
        k8.metric("Blank Remarks", f"{blank_remarks_count:,}")

        st.info("Percent labels are intentionally not shown on KPI cards. Detailed rates are available in the tables below.")

        r1, r2 = st.columns([1, 1])
        with r1:
            risk_df = pd.DataFrame({
                "Indicator": ["Duplicate Rate", "Same Remark Repeated Rate", "Template-like Remark Rate", "Possible AI/Prompt Copy Rate", "Blank Remark Rate"],
                "Rate %": [duplicate_rate, same_remark_rate, template_rate, ai_rate, blank_rate],
                "Risk": [get_risk_label(duplicate_rate), get_risk_label(same_remark_rate), get_risk_label(template_rate), get_risk_label(ai_rate), get_risk_label(blank_rate)],
            })
            st.markdown("### Quality Risk Snapshot")
            st.dataframe(risk_df, use_container_width=True, hide_index=True)
        with r2:
            st.markdown("### Top Themes")
            if not theme_summary.empty:
                theme_chart = theme_summary.groupby("Theme", as_index=False)["Records"].sum().sort_values("Records", ascending=False).head(10)
                render_labeled_bar_chart(theme_chart, "Theme", "Records", "Top 10 themes from clean remarks", orientation="h")
            else:
                st.write("No theme data available.")

        st.markdown("### Top YM / TMO Quality Review")
        st.dataframe(ym_summary.head(20), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Clean Data Summary After Deduplication")
        st.caption("All charts below use Clean Unique House Visits only. Labels are outside the graph marks for cleaner readability.")
        render_chart_box("1. House Visit Type-wise visits", "Distribution by HOUSE VISIT TYPE.", "pie", clean_summary_tables["House_Visit_Type_Wise"], "HOUSE VISIT TYPE", "House Visits")
        c1, c2 = st.columns(2)
        with c1:
            render_chart_box("2. Region-wise house visits", "Clean unique house visits by region.", "bar", clean_summary_tables["Region_Wise_House_Visits"], "REGION", "House Visits", orientation="v")
        with c2:
            render_chart_box("3. State-wise house visits", "Clean unique house visits by state.", "bar", clean_summary_tables["State_Wise_House_Visits"], "STATE", "House Visits", orientation="h")
        c3, c4 = st.columns(2)
        with c3:
            render_chart_box("4. Funder-wise house visits", "Clean unique house visits by funder.", "bar", clean_summary_tables["Funder_Wise_House_Visits"], "Funder", "House Visits", orientation="h")
        with c4:
            render_chart_box("5. TMO-wise house visits", "Top TMO-wise house visit volume.", "bar", clean_summary_tables["TMO_Wise_House_Visits"], "TMO Name", "House Visits", orientation="h")
        render_chart_box("6. YM-wise house visits", "Top YM-wise house visit volume.", "bar", clean_summary_tables["YM_Wise_House_Visits"], "YM Name", "House Visits", orientation="h")

        st.markdown("### Summary Tables")
        labels = [("House Visit Type", "House_Visit_Type_Wise"), ("Region", "Region_Wise_House_Visits"), ("State", "State_Wise_House_Visits"), ("Funder", "Funder_Wise_House_Visits"), ("TMO", "TMO_Wise_House_Visits"), ("YM", "YM_Wise_House_Visits")]
        table_tabs = st.tabs([x[0] for x in labels])
        for t, (_, key) in zip(table_tabs, labels):
            with t:
                st.dataframe(clean_summary_tables[key], use_container_width=True, hide_index=True)

    with tab3:
        render_india_state_map(clean_summary_tables["State_Wise_House_Visits"])

    with tab4:
        st.subheader("Duplicate Intelligence")
        st.caption("Duplicate logic: PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE")
        d1, d2, d3 = st.columns(3)
        d1.metric("Total Records", f"{total_records:,}")
        d2.metric("Clean Unique Records", f"{clean_records:,}")
        d3.metric("Duplicate Removed", f"{duplicate_records:,}")
        st.markdown("### Duplicate Summary")
        st.dataframe(duplicate_summary.head(200), use_container_width=True, hide_index=True)
        st.markdown("### Full Dataset with Duplicate Flag")
        st.dataframe(full_dataset.head(200), use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("Remarks Intelligence")
        st.caption("Remarks intelligence is calculated on clean unique data only to avoid duplicate inflation.")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Clean Records Analysed", f"{clean_records:,}")
        q2.metric("Same Remark Repeated", f"{same_remark_count:,}")
        q3.metric("Template-like Remarks", f"{template_flag_count:,}")
        q4.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}")
        st.markdown("### Remarks Summary by Geography / Program")
        st.dataframe(remarks_summary.head(200), use_container_width=True, hide_index=True)
        st.markdown("### Repeated Remarks")
        st.dataframe(repeated_remarks.head(200), use_container_width=True, hide_index=True)
        st.markdown("### Theme Summary")
        st.dataframe(theme_summary.head(200), use_container_width=True, hide_index=True)
        st.markdown("### Row-level Remarks Intelligence")
        row_cols = ["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type", "TMO Name", "YM Name", "CHILD ID", "HOUSE VISIT DATE", "REMARKS", "Same_Remark_Repeated", "Template_Flag", "Template_Score", "Template_Reason", "Possible_AI_Prompt_Copy", "Remarks_Themes", "Remarks_Word_Count", "Remarks_Quality_Band"]
        st.dataframe(remarks_dataset[row_cols].head(300), use_container_width=True, hide_index=True)

    with tab6:
        render_faq()

    with tab7:
        st.subheader("Download Reports")
        st.download_button("Download Complete DQI Intelligence Excel", data=output_xlsx.getvalue(), file_name=output_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", key="download_excel")
        st.download_button("Download Clean Data Summary Report PDF", data=charts_pdf.getvalue(), file_name=charts_pdf_name, mime="application/pdf", on_click="ignore", key="download_pdf")
        zip_buffer = create_zip_bundle({output_name: output_xlsx.getvalue(), charts_pdf_name: charts_pdf.getvalue()})
        st.download_button("Download ZIP Bundle", data=zip_buffer.getvalue(), file_name=zip_name, mime="application/zip", on_click="ignore", key="download_zip")
        st.markdown("### Excel sheets included")
        st.dataframe(excel_sheet_explanation_df(), use_container_width=True, hide_index=True)


def render_upload_prompt():
    """Render initial prompt before upload."""
    st.markdown(
        """
        <div class="section-card">
        <b>Upload a House Visit file to begin.</b><br>
        <b>Data privacy note:</b> The app does not store your uploaded dataset permanently. It processes the file temporarily in the running Streamlit session/runtime and provides downloadable outputs.<br><br>
        This app is designed for free Streamlit Cloud deployment and uses only open-source Python libraries.
        </div>
        """,
        unsafe_allow_html=True,
    )
