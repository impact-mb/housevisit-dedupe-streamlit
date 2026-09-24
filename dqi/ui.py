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
3.0.0
"""

import base64
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from .charts import render_chart_box, render_labeled_bar_chart
from .config import APP_NAME, APP_VERSION, BUILD, OWNER, SPORTS_QUOTES
from .faq import render_faq
from .processor import pct, make_summary_table
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
        f'<div class="center-subtitle">Version {APP_VERSION} • Build {BUILD} • Owner: {OWNER}<br>Duplicate Detection • Clean Data Summary • Unique Children Analysis • Spatial Analysis • Remarks Intelligence • Field Data Quality</div>',
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




def build_unique_children_dataset(clean_dataset: pd.DataFrame) -> pd.DataFrame:
    """
    Keep exactly one row per CHILD ID using the latest HOUSE VISIT DATE.

    Source:
    -------
    Clean Unique Dataset (after the application's existing duplicate removal).

    Rule:
    -----
    1. Parse HOUSE VISIT DATE as datetime.
    2. Sort each CHILD ID by HOUSE VISIT DATE from oldest to newest.
    3. When more than one record exists on the same latest date, keep the
       last source row among those tied records.
    4. Return exactly one row per non-blank CHILD ID.
    """
    if clean_dataset is None or clean_dataset.empty:
        return clean_dataset.copy()

    required = ["CHILD ID", "HOUSE VISIT DATE"]
    missing = [col for col in required if col not in clean_dataset.columns]
    if missing:
        raise ValueError(
            "Unique Children Analysis requires column(s): "
            + ", ".join(missing)
        )

    unique_df = clean_dataset.copy()

    # Standardise CHILD ID for grouping.
    unique_df["CHILD ID"] = (
        unique_df["CHILD ID"]
        .astype("string")
        .str.strip()
    )

    # Ignore blank Child IDs because they cannot represent a unique child.
    unique_df = unique_df[
        unique_df["CHILD ID"].notna()
        & unique_df["CHILD ID"].ne("")
    ].copy()

    # Preserve original clean-dataset order to resolve same-date ties.
    unique_df["_source_order"] = range(len(unique_df))

    unique_df["_house_visit_date_sort"] = pd.to_datetime(
        unique_df["HOUSE VISIT DATE"],
        errors="coerce",
        dayfirst=True,
    )

    unique_df = (
        unique_df
        .sort_values(
            [
                "CHILD ID",
                "_house_visit_date_sort",
                "_source_order",
            ],
            ascending=[True, True, True],
            na_position="first",
            kind="mergesort",
        )
        .drop_duplicates(
            subset=["CHILD ID"],
            keep="last",
        )
        .drop(
            columns=[
                "_source_order",
                "_house_visit_date_sort",
            ]
        )
        .reset_index(drop=True)
    )

    return unique_df


def render_dashboard(full_dataset, clean_dataset, duplicate_dataset, duplicate_summary,
                     clean_summary_tables, remarks_dataset, remarks_summary, ym_summary,
                     repeated_remarks, theme_summary, output_xlsx, charts_pdf, uploaded_name: str):
    """Render complete dashboard after analysis."""
    total_records = len(full_dataset)
    clean_records = len(clean_dataset)
    duplicate_records = len(duplicate_dataset)
    duplicate_rate = pct(duplicate_records, total_records)

    # Version 2: one latest record per CHILD ID.
    unique_children_dataset = build_unique_children_dataset(clean_dataset)
    unique_children_count = len(unique_children_dataset)
    child_ids_with_hv = (
        clean_dataset["CHILD ID"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
        if "CHILD ID" in clean_dataset.columns
        else 0
    )


    # ============================================================
    # VERSION 3: CXO / EXECUTIVE INSIGHTS
    # ============================================================

    avg_visits_per_child = (
        clean_records / unique_children_count
        if unique_children_count
        else 0
    )

    coverage_region_count = (
        clean_dataset["REGION"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
        if "REGION" in clean_dataset.columns
        else 0
    )

    coverage_state_count = (
        clean_dataset["STATE"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
        if "STATE" in clean_dataset.columns
        else 0
    )

    coverage_district_count = (
        clean_dataset["DISTRICT"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
        if "DISTRICT" in clean_dataset.columns
        else 0
    )

    coverage_program_count = (
        clean_dataset["PROGRAM LAUNCH NAME"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .nunique()
        if "PROGRAM LAUNCH NAME" in clean_dataset.columns
        else 0
    )

    # House visit count per unique child
    if "CHILD ID" in clean_dataset.columns:
        child_visit_frequency = (
            clean_dataset.assign(
                _child_id=(
                    clean_dataset["CHILD ID"]
                    .astype("string")
                    .str.strip()
                )
            )
            .query("_child_id.notna() and _child_id != ''")
            .groupby("_child_id", as_index=False)
            .size()
            .rename(
                columns={
                    "_child_id": "CHILD ID",
                    "size": "House Visits",
                }
            )
            .sort_values(
                "House Visits",
                ascending=False,
            )
            .reset_index(drop=True)
        )
    else:
        child_visit_frequency = pd.DataFrame(
            columns=[
                "CHILD ID",
                "House Visits",
            ]
        )

    high_frequency_threshold = 5

    high_frequency_cases = (
        child_visit_frequency[
            child_visit_frequency["House Visits"]
            >= high_frequency_threshold
        ]
        .copy()
    )

    high_frequency_children = len(
        high_frequency_cases
    )

    # ------------------------------------------------------------
    # RECENCY OF LATEST HOUSE VISIT
    # Relative to latest valid HOUSE VISIT DATE in uploaded data.
    # ------------------------------------------------------------

    recency_df = unique_children_dataset.copy()

    if (
        not recency_df.empty
        and "HOUSE VISIT DATE" in recency_df.columns
    ):
        recency_df["_Latest_HV_Date"] = pd.to_datetime(
            recency_df["HOUSE VISIT DATE"],
            errors="coerce",
            dayfirst=True,
        )

        reference_date = (
            recency_df["_Latest_HV_Date"].max()
        )

        if pd.notna(reference_date):
            recency_df["Days_Since_Latest_Visit"] = (
                reference_date
                - recency_df["_Latest_HV_Date"]
            ).dt.days

            def _recency_bucket(days):
                if pd.isna(days):
                    return "Invalid / Missing Date"
                if days <= 30:
                    return "0-30 days"
                if days <= 60:
                    return "31-60 days"
                if days <= 90:
                    return "61-90 days"
                return "90+ days"

            recency_df["Visit Recency"] = (
                recency_df["Days_Since_Latest_Visit"]
                .apply(_recency_bucket)
            )
        else:
            reference_date = pd.NaT
            recency_df["Days_Since_Latest_Visit"] = pd.NA
            recency_df["Visit Recency"] = (
                "Invalid / Missing Date"
            )
    else:
        reference_date = pd.NaT
        recency_df["Days_Since_Latest_Visit"] = pd.NA
        recency_df["Visit Recency"] = (
            "Invalid / Missing Date"
        )

    recency_order = [
        "0-30 days",
        "31-60 days",
        "61-90 days",
        "90+ days",
        "Invalid / Missing Date",
    ]

    recency_summary = (
        recency_df["Visit Recency"]
        .value_counts()
        .reindex(
            recency_order,
            fill_value=0,
        )
        .rename_axis("Visit Recency")
        .reset_index(name="Unique Children")
    )

    children_90_plus = int(
        recency_summary.loc[
            recency_summary["Visit Recency"]
            == "90+ days",
            "Unique Children",
        ].sum()
    )

    # ------------------------------------------------------------
    # TOP FUNDER / DISTRICT
    # ------------------------------------------------------------

    top_funders_cxo = (
        make_summary_table(
            clean_dataset,
            "Funder",
            top_n=5,
        )
        if "Funder" in clean_dataset.columns
        else pd.DataFrame()
    )

    top_districts_cxo = (
        make_summary_table(
            clean_dataset,
            "DISTRICT",
            top_n=5,
        )
        if "DISTRICT" in clean_dataset.columns
        else pd.DataFrame()
    )

    # ------------------------------------------------------------
    # CRITICAL DATA-QUALITY EXCEPTIONS
    # ------------------------------------------------------------

    critical_fields = [
        "CHILD ID",
        "HOUSE VISIT DATE",
        "REGION",
        "STATE",
        "DISTRICT",
        "PROGRAM LAUNCH NAME",
    ]

    dq_exception_rows = pd.Series(
        False,
        index=clean_dataset.index,
    )

    dq_exception_breakdown = []

    for col in critical_fields:
        if col in clean_dataset.columns:
            col_values = (
                clean_dataset[col]
                .astype("string")
                .str.strip()
            )

            missing_mask = (
                col_values.isna()
                | col_values.eq("")
            )

            dq_exception_rows = (
                dq_exception_rows
                | missing_mask
            )

            dq_exception_breakdown.append({
                "Field": col,
                "Missing Records": int(
                    missing_mask.sum()
                ),
            })

    if "HOUSE VISIT DATE" in clean_dataset.columns:
        parsed_hv_date = pd.to_datetime(
            clean_dataset["HOUSE VISIT DATE"],
            errors="coerce",
            dayfirst=True,
        )

        invalid_date_mask = (
            parsed_hv_date.isna()
            & clean_dataset["HOUSE VISIT DATE"]
            .notna()
        )

        dq_exception_rows = (
            dq_exception_rows
            | invalid_date_mask
        )

        dq_exception_breakdown.append({
            "Field": "Invalid HOUSE VISIT DATE",
            "Missing Records": int(
                invalid_date_mask.sum()
            ),
        })

    dq_exception_count = int(
        dq_exception_rows.sum()
    )

    dq_exception_breakdown = pd.DataFrame(
        dq_exception_breakdown
    )

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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Executive Insights",
        "Clean Data Summary",
        "Unique Children Analysis",
        "Spatial Data Analysis",
        "Duplicate Intelligence",
        "Remarks Intelligence",
        "Methodology / FAQ",
        "Downloads",
    ])

    with tab1:
        st.subheader("Executive Insights")
        st.caption(
            "CXO-level view of delivery intensity, reach, coverage, "
            "recency and data-quality signals."
        )

        # --------------------------------------------------------
        # CXO KPI ROW 1
        # --------------------------------------------------------
        k1, k2, k3, k4 = st.columns(4)

        k1.metric(
            "Total Clean House Visits",
            f"{clean_records:,}",
        )

        k2.metric(
            "Unique Children Reached",
            f"{unique_children_count:,}",
        )

        k3.metric(
            "Average Visits per Child",
            f"{avg_visits_per_child:.2f}",
        )

        k4.metric(
            "Duplicate Rate",
            f"{duplicate_rate:.1f}%",
        )

        # --------------------------------------------------------
        # CXO KPI ROW 2
        # --------------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Regions Covered",
            f"{coverage_region_count:,}",
        )

        c2.metric(
            "States Covered",
            f"{coverage_state_count:,}",
        )

        c3.metric(
            "Districts Covered",
            f"{coverage_district_count:,}",
        )

        c4.metric(
            "Program Launches",
            f"{coverage_program_count:,}",
        )

        # --------------------------------------------------------
        # ATTENTION KPIs
        # --------------------------------------------------------
        a1, a2, a3 = st.columns(3)

        a1.metric(
            "Children with 90+ Days Since Latest Visit",
            f"{children_90_plus:,}",
        )

        a2.metric(
            f"Children with {high_frequency_threshold}+ House Visits",
            f"{high_frequency_children:,}",
        )

        a3.metric(
            "Critical Data Quality Exception Rows",
            f"{dq_exception_count:,}",
        )

        if pd.notna(reference_date):
            st.caption(
                "Visit recency is calculated relative to the latest "
                f"valid HOUSE VISIT DATE in the uploaded data: "
                f"{reference_date.strftime('%d %b %Y')}."
            )

        # --------------------------------------------------------
        # COVERAGE + CONCENTRATION CHARTS
        # --------------------------------------------------------
        x1, x2 = st.columns(2)

        with x1:
            if not top_funders_cxo.empty:
                render_chart_box(
                    "Top 5 Funders by House Visits",
                    "Shows where clean house-visit volume is concentrated.",
                    "bar",
                    top_funders_cxo,
                    "Funder",
                    "House Visits",
                    orientation="h",
                    export_data=top_funders_cxo,
                    export_file_stub=f"{base_name}_Executive_Top_Funders",
                    export_key="executive_top_funders",
                    export_sheet_name="Top Funders",
                )
            else:
                st.info(
                    "Funder information is not available in the uploaded file."
                )

        with x2:
            if not top_districts_cxo.empty:
                render_chart_box(
                    "Top 5 Districts by House Visits",
                    "Shows where clean house-visit volume is concentrated.",
                    "bar",
                    top_districts_cxo,
                    "DISTRICT",
                    "House Visits",
                    orientation="h",
                    export_data=top_districts_cxo,
                    export_file_stub=f"{base_name}_Executive_Top_Districts",
                    export_key="executive_top_districts",
                    export_sheet_name="Top Districts",
                )
            else:
                st.info(
                    "District information is not available in the uploaded file."
                )

        # --------------------------------------------------------
        # RECENCY + HIGH FREQUENCY
        # --------------------------------------------------------
        x3, x4 = st.columns(2)

        with x3:
            render_chart_box(
                "Latest House Visit Recency",
                "Unique children grouped by days since their latest house visit.",
                "bar",
                recency_summary,
                "Visit Recency",
                "Unique Children",
                orientation="v",
                export_data=recency_summary,
                export_file_stub=f"{base_name}_Executive_Visit_Recency",
                export_key="executive_recency",
                export_sheet_name="Visit Recency",
            )

        with x4:
            if not child_visit_frequency.empty:
                visit_frequency_summary = (
                    child_visit_frequency[
                        "House Visits"
                    ]
                    .value_counts()
                    .sort_index()
                    .rename_axis("House Visits per Child")
                    .reset_index(
                        name="Unique Children"
                    )
                )

                render_chart_box(
                    "House Visit Frequency per Child",
                    "Distribution of clean house visits received by each unique child.",
                    "bar",
                    visit_frequency_summary,
                    "House Visits per Child",
                    "Unique Children",
                    orientation="v",
                    export_data=visit_frequency_summary,
                    export_file_stub=f"{base_name}_Executive_Visit_Frequency",
                    export_key="executive_visit_frequency",
                    export_sheet_name="Visit Frequency",
                )
            else:
                st.info(
                    "Child-level house visit frequency could not be calculated."
                )

        # --------------------------------------------------------
        # ACTION / ATTENTION AREA
        # --------------------------------------------------------
        st.markdown("### Attention Required")

        action_rows = []

        if children_90_plus > 0:
            action_rows.append({
                "Priority Area": "Follow-up Recency",
                "Signal": (
                    f"{children_90_plus:,} children have a latest "
                    "house visit more than 90 days before the reference date."
                ),
                "Suggested Review": (
                    "Review whether these children require follow-up "
                    "or whether programme schedules explain the gap."
                ),
            })

        if high_frequency_children > 0:
            action_rows.append({
                "Priority Area": "High Visit Frequency",
                "Signal": (
                    f"{high_frequency_children:,} children have "
                    f"{high_frequency_threshold}+ clean house visits."
                ),
                "Suggested Review": (
                    "Check whether high-frequency visits are expected "
                    "for the programme or require operational review."
                ),
            })

        if dq_exception_count > 0:
            action_rows.append({
                "Priority Area": "Data Quality",
                "Signal": (
                    f"{dq_exception_count:,} clean rows have at least "
                    "one critical missing/invalid field."
                ),
                "Suggested Review": (
                    "Prioritise correction of Child ID, date, geography "
                    "and Program Launch information."
                ),
            })

        if duplicate_rate > 0:
            action_rows.append({
                "Priority Area": "Duplicate Data",
                "Signal": (
                    f"{duplicate_rate:.1f}% of uploaded records were "
                    "identified as duplicates under the configured logic."
                ),
                "Suggested Review": (
                    "Monitor source-system entry practices and repeat "
                    "duplicate patterns."
                ),
            })

        if action_rows:
            st.dataframe(
                pd.DataFrame(action_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success(
                "No major CXO attention signals were identified "
                "from the currently uploaded dataset."
            )

        # --------------------------------------------------------
        # DATA QUALITY BREAKDOWN
        # --------------------------------------------------------
        if not dq_exception_breakdown.empty:
            st.markdown(
                "### Critical Field Quality"
            )

            st.dataframe(
                dq_exception_breakdown,
                use_container_width=True,
                hide_index=True,
            )

        st.info(
            "Executive Insights are intended for leadership review. "
            "Operational investigation should continue in Clean Data Summary, "
            "Unique Children Analysis, Duplicate Intelligence and Remarks Intelligence."
        )

    with tab2:
        st.subheader("Clean Data Summary After Deduplication")
        st.caption("All charts and summary tables below use the Clean Unique Dataset and respond dynamically to the filters.")

        # ------------------------------------------------------------
        # DYNAMIC FILTER ROW
        # ------------------------------------------------------------
        st.markdown("### Filters")

        # Keep one working dataframe and apply filters from left to right.
        # An empty selection means All.
        filtered_clean = clean_dataset.copy()

        def _filter_options(frame: pd.DataFrame, column: str):
            if column not in frame.columns:
                return []
            values = (
                frame[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )
            return sorted([v for v in values.unique().tolist() if v])

        f1, f2, f3, f4, f5 = st.columns(5)

        with f1:
            funder_values = st.multiselect(
                "Funder",
                options=_filter_options(filtered_clean, "Funder"),
                key="clean_summary_filter_funder",
                placeholder="All Funders",
            )
        if funder_values:
            filtered_clean = filtered_clean[filtered_clean["Funder"].isin(funder_values)].copy()

        with f2:
            region_values = st.multiselect(
                "Region",
                options=_filter_options(filtered_clean, "REGION"),
                key="clean_summary_filter_region",
                placeholder="All Regions",
            )
        if region_values:
            filtered_clean = filtered_clean[filtered_clean["REGION"].isin(region_values)].copy()

        with f3:
            state_values = st.multiselect(
                "State",
                options=_filter_options(filtered_clean, "STATE"),
                key="clean_summary_filter_state",
                placeholder="All States",
            )
        if state_values:
            filtered_clean = filtered_clean[filtered_clean["STATE"].isin(state_values)].copy()

        with f4:
            district_values = st.multiselect(
                "District",
                options=_filter_options(filtered_clean, "DISTRICT"),
                key="clean_summary_filter_district",
                placeholder="All Districts",
            )
        if district_values:
            filtered_clean = filtered_clean[filtered_clean["DISTRICT"].isin(district_values)].copy()

        with f5:
            program_values = st.multiselect(
                "Program Launch Name",
                options=_filter_options(filtered_clean, "PROGRAM LAUNCH NAME"),
                key="clean_summary_filter_program",
                placeholder="All Program Launches",
            )
        if program_values:
            filtered_clean = filtered_clean[filtered_clean["PROGRAM LAUNCH NAME"].isin(program_values)].copy()

        # Rebuild summary tables from the filtered clean data.
        filtered_summary_tables = {
            "House_Visit_Type_Wise": make_summary_table(filtered_clean, "HOUSE VISIT TYPE", top_n=20),
            "Region_Wise_House_Visits": make_summary_table(filtered_clean, "REGION", top_n=50),
            "State_Wise_House_Visits": make_summary_table(filtered_clean, "STATE", top_n=50),
            "Funder_Wise_House_Visits": make_summary_table(filtered_clean, "Funder", top_n=50),
            "TMO_Wise_House_Visits": make_summary_table(filtered_clean, "TMO Name", top_n=30),
            "YM_Wise_House_Visits": make_summary_table(filtered_clean, "YM Name", top_n=30),
        }

        selected_records = len(filtered_clean)
        total_clean_records = len(clean_dataset)
        selected_share = pct(selected_records, total_clean_records)

        m1, m2 = st.columns(2)
        m1.metric("Filtered Clean House Visits", f"{selected_records:,}")
        m2.metric("Share of Clean Dataset", f"{selected_share:.1f}%")

        if filtered_clean.empty:
            st.warning(
                "No records match the selected filters. "
                "Please change or clear one or more filters."
            )
        else:
            render_chart_box(
                "1. House Visit Type-wise visits",
                "Distribution by HOUSE VISIT TYPE for the selected filters.",
                "pie",
                filtered_summary_tables["House_Visit_Type_Wise"],
                "HOUSE VISIT TYPE",
                "House Visits",
                export_data=filtered_summary_tables["House_Visit_Type_Wise"],
                export_file_stub=f"{base_name}_CleanSummary_HouseVisitType",
                export_key="clean_summary_hv_type",
                export_sheet_name="House Visit Type",
            )

            c1, c2 = st.columns(2)

            with c1:
                render_chart_box(
                    "2. Region-wise house visits",
                    "Clean unique house visits by region for the selected filters.",
                    "bar",
                    filtered_summary_tables["Region_Wise_House_Visits"],
                    "REGION",
                    "House Visits",
                    orientation="v",
                    export_data=filtered_summary_tables[
                        "Region_Wise_House_Visits"
                    ],
                    export_file_stub=f"{base_name}_CleanSummary_Region",
                    export_key="clean_summary_region",
                    export_sheet_name="Region",
                )

            with c2:
                render_chart_box(
                    "3. State-wise house visits",
                    "Clean unique house visits by state for the selected filters.",
                    "bar",
                    filtered_summary_tables["State_Wise_House_Visits"],
                    "STATE",
                    "House Visits",
                    orientation="h",
                    export_data=filtered_summary_tables[
                        "State_Wise_House_Visits"
                    ],
                    export_file_stub=f"{base_name}_CleanSummary_State",
                    export_key="clean_summary_state",
                    export_sheet_name="State",
                )

            c3, c4 = st.columns(2)

            with c3:
                render_chart_box(
                    "4. Funder-wise house visits",
                    "Clean unique house visits by funder for the selected filters.",
                    "bar",
                    filtered_summary_tables["Funder_Wise_House_Visits"],
                    "Funder",
                    "House Visits",
                    orientation="h",
                    export_data=filtered_summary_tables[
                        "Funder_Wise_House_Visits"
                    ],
                    export_file_stub=f"{base_name}_CleanSummary_Funder",
                    export_key="clean_summary_funder",
                    export_sheet_name="Funder",
                )

            with c4:
                render_chart_box(
                    "5. TMO-wise house visits",
                    "Top TMO-wise house visit volume for the selected filters.",
                    "bar",
                    filtered_summary_tables["TMO_Wise_House_Visits"],
                    "TMO Name",
                    "House Visits",
                    orientation="h",
                    export_data=filtered_summary_tables[
                        "TMO_Wise_House_Visits"
                    ],
                    export_file_stub=f"{base_name}_CleanSummary_TMO",
                    export_key="clean_summary_tmo",
                    export_sheet_name="TMO",
                )

            render_chart_box(
                "6. YM-wise house visits",
                "Top YM-wise house visit volume for the selected filters.",
                "bar",
                filtered_summary_tables["YM_Wise_House_Visits"],
                "YM Name",
                "House Visits",
                orientation="h",
                export_data=filtered_summary_tables["YM_Wise_House_Visits"],
                export_file_stub=f"{base_name}_CleanSummary_YM",
                export_key="clean_summary_ym",
                export_sheet_name="YM",
            )

            st.markdown("### Summary Tables")

            labels = [
                ("House Visit Type", "House_Visit_Type_Wise"),
                ("Region", "Region_Wise_House_Visits"),
                ("State", "State_Wise_House_Visits"),
                ("Funder", "Funder_Wise_House_Visits"),
                ("TMO", "TMO_Wise_House_Visits"),
                ("YM", "YM_Wise_House_Visits"),
            ]

            table_tabs = st.tabs(
                [label for label, _ in labels]
            )

            for table_tab, (_, key) in zip(
                table_tabs,
                labels,
            ):
                with table_tab:
                    st.dataframe(
                        filtered_summary_tables[key],
                        use_container_width=True,
                        hide_index=True,
                    )


    with tab3:
        st.subheader("Unique Children Analysis")
        st.caption(
            "One latest record is retained for each CHILD ID using HOUSE VISIT DATE. "
            "This page uses the Clean Unique Dataset after the existing duplicate-removal process."
        )

        u1, u2, u3 = st.columns(3)
        u1.metric(
            "Clean House Visit Records",
            f"{clean_records:,}",
        )
        u2.metric(
            "Unique Children",
            f"{unique_children_count:,}",
        )
        u3.metric(
            "House Visit Records Removed for Latest-Child View",
            f"{max(clean_records - unique_children_count, 0):,}",
        )

        st.info(
            "Rule: if a CHILD ID appears multiple times, the record with the latest "
            "HOUSE VISIT DATE is retained. If the same child has more than one record "
            "on the same latest date, the last record in the clean source order is retained."
        )

        # --------------------------------------------------------
        # FILTERS
        # --------------------------------------------------------
        st.markdown("### Filters")

        filtered_unique = unique_children_dataset.copy()

        def _unique_filter_options(frame: pd.DataFrame, column: str):
            if column not in frame.columns:
                return []
            values = (
                frame[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )
            return sorted(
                [
                    value
                    for value in values.unique().tolist()
                    if value
                ]
            )

        uf1, uf2, uf3, uf4, uf5 = st.columns(5)

        with uf1:
            unique_funders = st.multiselect(
                "Funder",
                options=_unique_filter_options(
                    filtered_unique,
                    "Funder",
                ),
                key="unique_children_filter_funder",
                placeholder="All Funders",
            )

        if unique_funders:
            filtered_unique = filtered_unique[
                filtered_unique["Funder"].isin(unique_funders)
            ].copy()

        with uf2:
            unique_regions = st.multiselect(
                "Region",
                options=_unique_filter_options(
                    filtered_unique,
                    "REGION",
                ),
                key="unique_children_filter_region",
                placeholder="All Regions",
            )

        if unique_regions:
            filtered_unique = filtered_unique[
                filtered_unique["REGION"].isin(unique_regions)
            ].copy()

        with uf3:
            unique_states = st.multiselect(
                "State",
                options=_unique_filter_options(
                    filtered_unique,
                    "STATE",
                ),
                key="unique_children_filter_state",
                placeholder="All States",
            )

        if unique_states:
            filtered_unique = filtered_unique[
                filtered_unique["STATE"].isin(unique_states)
            ].copy()

        with uf4:
            unique_districts = st.multiselect(
                "District",
                options=_unique_filter_options(
                    filtered_unique,
                    "DISTRICT",
                ),
                key="unique_children_filter_district",
                placeholder="All Districts",
            )

        if unique_districts:
            filtered_unique = filtered_unique[
                filtered_unique["DISTRICT"].isin(unique_districts)
            ].copy()

        with uf5:
            unique_programs = st.multiselect(
                "Program Launch Name",
                options=_unique_filter_options(
                    filtered_unique,
                    "PROGRAM LAUNCH NAME",
                ),
                key="unique_children_filter_program",
                placeholder="All Program Launches",
            )

        if unique_programs:
            filtered_unique = filtered_unique[
                filtered_unique["PROGRAM LAUNCH NAME"].isin(unique_programs)
            ].copy()

        filtered_unique_count = len(filtered_unique)
        unique_share = pct(
            filtered_unique_count,
            unique_children_count,
        )

        um1, um2 = st.columns(2)
        um1.metric(
            "Filtered Unique Children",
            f"{filtered_unique_count:,}",
        )
        um2.metric(
            "Share of Unique Children",
            f"{unique_share:.1f}%",
        )

        if filtered_unique.empty:
            st.warning(
                "No unique-child records match the selected filters."
            )
        else:
            # ----------------------------------------------------
            # SUMMARY CHARTS
            # ----------------------------------------------------
            unique_region_summary = make_summary_table(
                filtered_unique,
                "REGION",
                top_n=50,
            )

            unique_state_summary = make_summary_table(
                filtered_unique,
                "STATE",
                top_n=50,
            )

            unique_funder_summary = make_summary_table(
                filtered_unique,
                "Funder",
                top_n=50,
            )

            unique_program_summary = make_summary_table(
                filtered_unique,
                "PROGRAM LAUNCH NAME",
                top_n=30,
            )

            c1, c2 = st.columns(2)

            with c1:
                render_chart_box(
                    "1. Region-wise unique children",
                    "Latest retained record per CHILD ID for the selected filters.",
                    "bar",
                    unique_region_summary,
                    "REGION",
                    "House Visits",
                    orientation="v",
                    export_data=unique_region_summary.rename(
                        columns={"House Visits": "Unique Children"}
                    ),
                    export_file_stub=f"{base_name}_UniqueChildren_Region",
                    export_key="unique_children_region",
                    export_sheet_name="Region",
                )

            with c2:
                render_chart_box(
                    "2. State-wise unique children",
                    "Latest retained record per CHILD ID for the selected filters.",
                    "bar",
                    unique_state_summary,
                    "STATE",
                    "House Visits",
                    orientation="h",
                    export_data=unique_state_summary.rename(
                        columns={"House Visits": "Unique Children"}
                    ),
                    export_file_stub=f"{base_name}_UniqueChildren_State",
                    export_key="unique_children_state",
                    export_sheet_name="State",
                )

            c3, c4 = st.columns(2)

            with c3:
                render_chart_box(
                    "3. Funder-wise unique children",
                    "Latest retained record per CHILD ID for the selected filters.",
                    "bar",
                    unique_funder_summary,
                    "Funder",
                    "House Visits",
                    orientation="h",
                    export_data=unique_funder_summary.rename(
                        columns={"House Visits": "Unique Children"}
                    ),
                    export_file_stub=f"{base_name}_UniqueChildren_Funder",
                    export_key="unique_children_funder",
                    export_sheet_name="Funder",
                )

            with c4:
                render_chart_box(
                    "4. Program Launch-wise unique children",
                    "Latest retained record per CHILD ID for the selected filters.",
                    "bar",
                    unique_program_summary,
                    "PROGRAM LAUNCH NAME",
                    "House Visits",
                    orientation="h",
                    export_data=unique_program_summary.rename(
                        columns={"House Visits": "Unique Children"}
                    ),
                    export_file_stub=(
                        f"{base_name}_UniqueChildren_ProgramLaunch"
                    ),
                    export_key="unique_children_program",
                    export_sheet_name="Program Launch",
                )

            st.markdown("### Latest Record for Each Child")

            st.dataframe(
                filtered_unique,
                use_container_width=True,
                hide_index=True,
            )


    with tab4:
        render_india_state_map(clean_summary_tables["State_Wise_House_Visits"])

    with tab5:
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

    with tab6:
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

    with tab7:
        render_faq()

    with tab8:
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
