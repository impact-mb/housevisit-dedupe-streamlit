"""
House Visit Data Quality Intelligence Platform (DQI)
===================================================

Purpose
-------
This Streamlit application helps Magic Bus data / M&E teams assess House Visit data quality.

Core modules
------------
1. Secure login layer using Streamlit secrets.
2. Duplicate detection using the agreed business key:
   PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE
3. Clean unique dataset generation after duplicate removal.
4. CXO-friendly executive dashboard with clear denominators and percentage metrics.
5. Clean-data summary charts after data cleaning:
   - Region-wise house visits
   - State-wise house visits
   - Funder-wise house visits
   - TMO-wise house visits
   - YM-wise house visits
   - House Visit Type-wise visits
6. Methodology / FAQ page explaining every KPI, dashboard section, and downloadable sheet.
7. Remarks intelligence using clean unique data only:
   - Same remark repeated flag
   - Copy-paste score
   - Template detection
   - Possible AI / prompt-copy detection
   - Theme classification
7. Excel export with all row-level and summary outputs.

Deployment notes
----------------
This app is designed for free Streamlit Cloud deployment using open-source packages:
streamlit, pandas, openpyxl, plotly.

Do not hard-code production passwords in this file. Use .streamlit/secrets.toml locally
and Streamlit Cloud secrets online.
"""

import base64
import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="House Visit Data Quality Intelligence Platform (DQI)",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# LOGIN CONFIG - STREAMLIT SECRETS BASED
# ============================================================
def get_login_credentials():
    """
    Read login credentials from Streamlit secrets.

    Local setup:
    .streamlit/secrets.toml

    [auth]
    username = "north_admin"
    password = "Magic@1234"

    Streamlit Cloud setup:
    App > Settings > Secrets, then paste the same TOML block.
    """
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return None, None


def render_login_page():
    """Render a simple secure access layer before the main app loads."""
    st.markdown(
        """
        <style>
            .login-page-title {
                text-align: center;
                font-size: 34px;
                font-weight: 850;
                color: #1f2937;
                margin-top: 48px;
                margin-bottom: 4px;
            }
            .login-page-subtitle {
                text-align: center;
                font-size: 15px;
                color: #6b7280;
                margin-bottom: 30px;
            }
            .login-warning {
                background: #fff7e6;
                border-left: 6px solid #f59e0b;
                border-radius: 12px;
                padding: 14px 16px;
                margin-top: 15px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-page-title">House Visit Data Quality Intelligence Platform (DQI)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="login-page-subtitle">Secure access for internal data quality review</div>',
        unsafe_allow_html=True,
    )

    expected_username, expected_password = get_login_credentials()

    if not expected_username or not expected_password:
        st.markdown(
            """
            <div class="login-warning">
                <b>Login secrets are not configured.</b><br>
                Add credentials in <code>.streamlit/secrets.toml</code> locally or in Streamlit Cloud secrets online.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    col_left, col_mid, col_right = st.columns([1, 1.15, 1])
    with col_mid:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

            if submitted:
                if username == expected_username and password == expected_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    render_login_page()
    st.stop()


# ============================================================
# CSS - CXO-FRIENDLY UI
# ============================================================
st.markdown(
    """
    <style>
        .main { background-color: #FAFAF7; }
        .center-title {
            text-align: center;
            font-size: 34px;
            font-weight: 850;
            color: #1f2937;
            margin-top: 4px;
            margin-bottom: 2px;
        }
        .center-subtitle {
            text-align: center;
            font-size: 15px;
            color: #4b5563;
            margin-bottom: 20px;
        }
        .quote-card {
            background: #fff7e6;
            border-left: 6px solid #f59e0b;
            border-radius: 14px;
            padding: 15px 18px;
            color: #374151;
            font-size: 15px;
            min-height: 92px;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.03);
        }
        .date-card {
            background: #eef6ff;
            border-left: 6px solid #2563eb;
            border-radius: 14px;
            padding: 15px 18px;
            color: #1f2937;
            font-size: 15px;
            min-height: 92px;
            text-align: right;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.03);
        }
        .section-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 18px;
            margin-top: 10px;
            margin-bottom: 10px;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.03);
        }
        .metric-note { font-size: 13px; color: #6b7280; }
        .block-title {
            font-size: 19px;
            font-weight: 750;
            color: #111827;
            margin-top: 8px;
            margin-bottom: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SCHEMA AND BUSINESS RULES
# ============================================================
SCHEMA = {
    "Funder": "string",
    "COUNTRY": "string",
    "REGION": "string",
    "STATE": "string",
    "DISTRICT": "string",
    "PROGRAM LAUNCH NAME": "string",
    "Sub Type": "string",
    "FunderID": "string",
    "ProjectID": "string",
    "ProjectType": "string",
    "HOUSE VISIT TYPE": "string",
    "CHILD ID": "string",
    "Child Name": "string",
    "PARENT NAME": "string",
    "HOUSE VISIT DATE": "date",
    "GROUP ID": "string",
    "REMARKS": "string",
    "HouseVisitID": "string",
    "TMO Name": "string",
    "YM Name": "string",
}

DEDUPE_KEY_COLS = [
    "PROGRAM LAUNCH NAME",
    "ProjectType",
    "CHILD ID",
    "TMO Name",
    "YM Name",
    "HOUSE VISIT DATE",
]

REMARKS_CONTEXT_COLS = [
    "PROGRAM LAUNCH NAME",
    "Sub Type",
    "HOUSE VISIT TYPE",
    "TMO Name",
    "YM Name",
    "CHILD ID",
    "HOUSE VISIT DATE",
]

REMARK_REUSE_GROUP_COLS = [
    "PROGRAM LAUNCH NAME",
    "Sub Type",
    "HOUSE VISIT TYPE",
    "TMO Name",
    "YM Name",
]

THEME_KEYWORDS = {
    "Education / Study": ["education", "study", "studies", "academic", "timetable", "homework", "school", "learning"],
    "Exam Readiness": ["exam", "exams", "final exam", "10th", "ssc", "preparation"],
    "Study Corner": ["study corner", "studycorner"],
    "Kitchen Garden": ["kitchen garden", "kitchen", "garden", "kicthen"],
    "Life Skills": ["life skill", "life skills", "communication", "leadership", "critical thinking"],
    "Digital Literacy": ["digital", "computer", "technology", "ai", "artificial intelligence"],
    "Career Awareness": ["career", "job", "future", "aspiration"],
    "Parent Engagement": ["parent", "parents", "mother", "father", "guardian", "parents meeting"],
    "Health / Wellbeing": ["health", "discipline", "hygiene", "wellbeing", "nutrition"],
    "Program Awareness": ["magic bus", "magicbus", "program", "programme", "three-year journey"],
}

COMMON_TEMPLATE_OPENINGS = [
    "we met", "we discussed", "met with parents", "met with the parents",
    "during the home visit", "today we met", "today, we met", "explain about",
    "explained about", "discussed about", "we explained", "we meet",
]

GENERIC_TEMPLATE_PHRASES = [
    "overall development", "importance of education", "study corner and kitchen garden",
    "kitchen garden and study corner", "daily study plans", "academic progress",
    "magic bus program", "life skills sessions", "digital literacy sessions",
    "parents were requested", "parents actively participated", "provided updates",
]

AI_PROMPT_COPY_PHRASES = [
    "here is an improved version", "additional relevant line", "as an ai", "chatgpt",
    "generated response", "improved version", "relevant line", "draft", "rewrite",
]

SPORTS_QUOTES = [
    "Champions keep playing until they get it right.",
    "You miss 100% of the shots you don’t take.",
    "Discipline turns practice into performance.",
    "Pressure is a privilege.",
    "Consistency beats intensity when the season is long.",
]


# ============================================================
# DATA CLEANING HELPERS
# ============================================================
def clickable_logo(img_path: str, link_url: str, width: int = 130):
    """Render a clickable logo when the logo file exists."""
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


def remove_footer_and_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove empty rows and Power BI footer rows such as Applied filters."""
    df = df.copy().dropna(how="all")
    footer_mask = df.apply(
        lambda row: row.astype(str).str.contains("Applied filters", case=False, na=False).any(),
        axis=1,
    )
    return df[~footer_mask].reset_index(drop=True)


def apply_schema_types(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize expected columns, dates, IDs, and text spacing."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col, dtype in SCHEMA.items():
        if col not in df.columns:
            df[col] = ""
            continue

        if dtype == "date":
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True).dt.date
        else:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

    return df


def normalize_text(text: str) -> str:
    """Create a canonical text version for matching and rule-based analytics."""
    text = "" if pd.isna(text) else str(text)
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_key(df: pd.DataFrame, cols: list) -> pd.Series:
    """Concatenate selected columns into a stable business key."""
    parts = []
    for col in cols:
        if col == "HOUSE VISIT DATE":
            parts.append(df[col].astype(str))
        else:
            parts.append(df[col].fillna("").astype(str))
    key = parts[0]
    for p in parts[1:]:
        key = key + " | " + p
    return key


def pct(num: float, den: float) -> float:
    """Safe percentage calculation."""
    return round((num / den * 100), 1) if den else 0.0


# ============================================================
# CHART HELPERS
# ============================================================
def make_summary_table(df: pd.DataFrame, group_col: str, top_n: int = 20) -> pd.DataFrame:
    """Create a house-visit count summary from clean unique data."""
    if group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "House Visits"])

    out = (
        df.groupby(group_col, dropna=False)
        .size()
        .reset_index(name="House Visits")
        .sort_values("House Visits", ascending=False)
        .head(top_n)
    )
    out[group_col] = out[group_col].replace("", "Not Available")
    return out


def render_labeled_bar_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str, orientation: str = "v"):
    """Render a Plotly bar chart with value labels for CXO-friendly readability."""
    if data.empty:
        st.info(f"No data available for {title}.")
        return

    if orientation == "h":
        plot_df = data.sort_values(y_col, ascending=True)
        fig = px.bar(
            plot_df,
            x=y_col,
            y=x_col,
            orientation="h",
            text=y_col,
            title=title,
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis_title="", xaxis_title="House visits", height=max(420, 28 * len(plot_df)))
    else:
        fig = px.bar(data, x=x_col, y=y_col, text=y_col, title=title)
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="House visits", height=460)

    fig.update_layout(
        margin=dict(l=20, r=40, t=60, b=40),
        title_x=0.02,
        uniformtext_minsize=10,
        uniformtext_mode="show",
    )
    st.plotly_chart(fig, use_container_width=True)


def create_clean_summary(clean_dataset: pd.DataFrame):
    """Create clean-data house visit summaries for dashboard charts and Excel export."""
    return {
        "Region_Wise_House_Visits": make_summary_table(clean_dataset, "REGION", top_n=50),
        "State_Wise_House_Visits": make_summary_table(clean_dataset, "STATE", top_n=50),
        "Funder_Wise_House_Visits": make_summary_table(clean_dataset, "Funder", top_n=50),
        "TMO_Wise_House_Visits": make_summary_table(clean_dataset, "TMO Name", top_n=30),
        "YM_Wise_House_Visits": make_summary_table(clean_dataset, "YM Name", top_n=30),
        "House_Visit_Type_Wise": make_summary_table(clean_dataset, "HOUSE VISIT TYPE", top_n=20),
    }


# ============================================================
# REMARKS INTELLIGENCE HELPERS
# ============================================================
def detect_themes(text: str) -> str:
    """Assign one or more themes to a remark based on keyword rules."""
    text_norm = normalize_text(text)
    themes = [theme for theme, keywords in THEME_KEYWORDS.items() if any(k in text_norm for k in keywords)]
    return ", ".join(themes) if themes else "Unclassified"


def count_themes(text: str) -> int:
    theme_string = detect_themes(text)
    return 0 if theme_string == "Unclassified" else len(theme_string.split(", "))


def detect_ai_prompt_copy(text: str) -> int:
    """Flag clear copy-paste remnants from AI/prompt interfaces."""
    text_norm = normalize_text(text)
    return int(any(phrase in text_norm for phrase in AI_PROMPT_COPY_PHRASES))


def template_detection(text: str) -> tuple:
    """Rule-based template detection using opening phrases, generic phrases, and theme density."""
    text_norm = normalize_text(text)
    if text_norm == "":
        return 0, 0, "Blank remark"

    score = 0
    reasons = []

    if any(text_norm.startswith(opening) for opening in COMMON_TEMPLATE_OPENINGS):
        score += 25
        reasons.append("Common opening phrase")

    matched_generic = [p for p in GENERIC_TEMPLATE_PHRASES if p in text_norm]
    if matched_generic:
        score += 20
        reasons.append("Generic programme phrase")

    if count_themes(text_norm) >= 3:
        score += 15
        reasons.append("Multiple standard intervention keywords")

    word_count = len(text_norm.split())
    if word_count >= 25 and matched_generic:
        score += 15
        reasons.append("Long structured programme-style remark")

    if detect_ai_prompt_copy(text_norm):
        score += 40
        reasons.append("Possible AI/prompt copy phrase")

    return int(score >= 40), min(score, 100), " + ".join(reasons) if reasons else "No template signal"


def remarks_quality_band(word_count: int, blank_flag: int, ai_flag: int, same_flag: int, template_flag: int) -> str:
    """Create a row-level quality band for review prioritization."""
    if blank_flag == 1:
        return "Poor - Blank"
    if ai_flag == 1:
        return "Critical Review - Possible AI/Prompt Copy"
    if same_flag == 1 and template_flag == 1:
        return "High Review - Repeated Template"
    if same_flag == 1:
        return "Review - Repeated Remark"
    if template_flag == 1:
        return "Review - Template-like"
    if word_count <= 5:
        return "Poor - Too Short"
    if word_count <= 15:
        return "Fair"
    if word_count <= 35:
        return "Good"
    return "Detailed"


# ============================================================
# DQI DUPLICATE PROCESSING
# ============================================================
def process_housevisit_dqi(df: pd.DataFrame):
    """Clean input data, identify duplicates, and create full/clean/duplicate datasets."""
    df = remove_footer_and_blank_rows(df)
    df = apply_schema_types(df)

    df["DQI_DUPLICATE_KEY"] = make_key(df, DEDUPE_KEY_COLS)
    df["Duplicate_Order"] = df.groupby("DQI_DUPLICATE_KEY").cumcount()
    df["Duplicate_Group_Size"] = df.groupby("DQI_DUPLICATE_KEY")["DQI_DUPLICATE_KEY"].transform("count")

    # Required dichotomous variable:
    # Duplicate = 1 means duplicate/repeated record.
    # Duplicate = 0 means unique/first record retained in clean data.
    df["Duplicate"] = (df["Duplicate_Order"] > 0).astype(int)

    full_dataset = df.copy()
    clean_dataset = df[df["Duplicate"] == 0].copy()
    duplicate_dataset = df[df["Duplicate"] == 1].copy()

    duplicate_summary = (
        df[df["Duplicate_Group_Size"] > 1]
        .groupby(DEDUPE_KEY_COLS, dropna=False)
        .agg(
            Records_In_Key=("DQI_DUPLICATE_KEY", "count"),
            Duplicate_Removed=("Duplicate", "sum"),
            HouseVisitID_List=("HouseVisitID", lambda x: ", ".join(x.astype(str))),
            Remarks_List=("REMARKS", lambda x: " || ".join(pd.Series(x.astype(str).unique()).head(5))),
        )
        .reset_index()
        .sort_values("Records_In_Key", ascending=False)
    )

    return full_dataset, clean_dataset, duplicate_dataset, duplicate_summary


# ============================================================
# REMARKS INTELLIGENCE PROCESSING
# ============================================================
def create_remarks_intelligence(clean_dataset: pd.DataFrame):
    """
    Build remarks intelligence using clean unique data only.

    This prevents duplicate records from inflating copy-paste or template scores.
    """
    df = clean_dataset.copy()
    df["REMARKS_CONTEXT_KEY"] = make_key(df, REMARKS_CONTEXT_COLS)
    df["REMARKS_CLEAN"] = df["REMARKS"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df["REMARKS_CANONICAL"] = df["REMARKS_CLEAN"].apply(normalize_text)
    df["Blank_Remark"] = df["REMARKS_CANONICAL"].apply(lambda x: 1 if x == "" or x in ["nan", "none"] else 0)
    df["Remarks_Word_Count"] = df["REMARKS_CANONICAL"].apply(lambda x: len(x.split()) if x else 0)

    same_remark_group = REMARK_REUSE_GROUP_COLS + ["REMARKS_CANONICAL"]
    df["Same_Remark_Group_Size"] = df.groupby(same_remark_group, dropna=False)["REMARKS_CANONICAL"].transform("count")
    df["Same_Remark_Repeated"] = ((df["Same_Remark_Group_Size"] > 1) & (df["Blank_Remark"] == 0)).astype(int)

    template_results = df["REMARKS_CLEAN"].apply(template_detection)
    df["Template_Flag"] = template_results.apply(lambda x: x[0])
    df["Template_Score"] = template_results.apply(lambda x: x[1])
    df["Template_Reason"] = template_results.apply(lambda x: x[2])
    df["Possible_AI_Prompt_Copy"] = df["REMARKS_CLEAN"].apply(detect_ai_prompt_copy)
    df["Remarks_Themes"] = df["REMARKS_CLEAN"].apply(detect_themes)
    df["Theme_Count"] = df["REMARKS_CLEAN"].apply(count_themes)

    df["Remarks_Quality_Band"] = df.apply(
        lambda r: remarks_quality_band(
            r["Remarks_Word_Count"],
            r["Blank_Remark"],
            r["Possible_AI_Prompt_Copy"],
            r["Same_Remark_Repeated"],
            r["Template_Flag"],
        ),
        axis=1,
    )

    group_cols = ["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type"]
    remarks_summary = (
        df.groupby(group_cols, dropna=False)
        .agg(
            Clean_Unique_Records=("CHILD ID", "count"),
            Unique_Children=("CHILD ID", "nunique"),
            Blank_Remarks=("Blank_Remark", "sum"),
            Same_Remark_Repeated=("Same_Remark_Repeated", "sum"),
            Template_Flag=("Template_Flag", "sum"),
            Possible_AI_Prompt_Copy=("Possible_AI_Prompt_Copy", "sum"),
            Avg_Remarks_Word_Count=("Remarks_Word_Count", "mean"),
            Unique_Remarks=("REMARKS_CANONICAL", "nunique"),
        )
        .reset_index()
    )
    remarks_summary["Same_Remark_Repeated_%"] = remarks_summary.apply(lambda r: pct(r["Same_Remark_Repeated"], r["Clean_Unique_Records"]), axis=1)
    remarks_summary["Template_Flag_%"] = remarks_summary.apply(lambda r: pct(r["Template_Flag"], r["Clean_Unique_Records"]), axis=1)
    remarks_summary["Blank_Remark_%"] = remarks_summary.apply(lambda r: pct(r["Blank_Remarks"], r["Clean_Unique_Records"]), axis=1)
    remarks_summary["Avg_Remarks_Word_Count"] = remarks_summary["Avg_Remarks_Word_Count"].round(1)

    ym_summary = (
        df.groupby(["REGION", "STATE", "DISTRICT", "TMO Name", "YM Name"], dropna=False)
        .agg(
            Clean_Unique_Records=("CHILD ID", "count"),
            Unique_Children=("CHILD ID", "nunique"),
            Same_Remark_Repeated=("Same_Remark_Repeated", "sum"),
            Template_Flag=("Template_Flag", "sum"),
            Possible_AI_Prompt_Copy=("Possible_AI_Prompt_Copy", "sum"),
            Blank_Remarks=("Blank_Remark", "sum"),
            Avg_Word_Count=("Remarks_Word_Count", "mean"),
            Unique_Remarks=("REMARKS_CANONICAL", "nunique"),
        )
        .reset_index()
    )
    ym_summary["Copy_Paste_Score_%"] = ym_summary.apply(lambda r: pct(r["Same_Remark_Repeated"], r["Clean_Unique_Records"]), axis=1)
    ym_summary["Template_Score_%"] = ym_summary.apply(lambda r: pct(r["Template_Flag"], r["Clean_Unique_Records"]), axis=1)
    ym_summary["Avg_Word_Count"] = ym_summary["Avg_Word_Count"].round(1)
    ym_summary = ym_summary.sort_values(["Copy_Paste_Score_%", "Template_Score_%"], ascending=False)

    repeated_remarks = (
        df[df["Blank_Remark"] == 0]
        .groupby(REMARK_REUSE_GROUP_COLS + ["REMARKS_CLEAN"], dropna=False)
        .agg(
            Reuse_Count=("REMARKS_CLEAN", "count"),
            Child_Count=("CHILD ID", "nunique"),
            First_House_Visit_Date=("HOUSE VISIT DATE", "min"),
            Last_House_Visit_Date=("HOUSE VISIT DATE", "max"),
        )
        .reset_index()
        .query("Reuse_Count > 1")
        .sort_values("Reuse_Count", ascending=False)
    )

    theme_rows = []
    for _, row in df.iterrows():
        themes = row["Remarks_Themes"].split(", ") if row["Remarks_Themes"] != "Unclassified" else ["Unclassified"]
        for theme in themes:
            theme_rows.append({
                "REGION": row["REGION"],
                "STATE": row["STATE"],
                "DISTRICT": row["DISTRICT"],
                "PROGRAM LAUNCH NAME": row["PROGRAM LAUNCH NAME"],
                "Sub Type": row["Sub Type"],
                "Theme": theme,
                "CHILD ID": row["CHILD ID"],
            })

    if theme_rows:
        theme_df = pd.DataFrame(theme_rows)
        theme_summary = (
            theme_df.groupby(["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type", "Theme"], dropna=False)
            .agg(Records=("Theme", "count"), Unique_Children=("CHILD ID", "nunique"))
            .reset_index()
            .sort_values("Records", ascending=False)
        )
    else:
        theme_summary = pd.DataFrame(columns=["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type", "Theme", "Records", "Unique_Children"])

    return df, remarks_summary, ym_summary, repeated_remarks, theme_summary


# ============================================================
# EXCEL EXPORT
# ============================================================
def create_excel_outputs(full_dataset, clean_dataset, duplicate_dataset, duplicate_summary,
                         clean_summary_tables, remarks_dataset, remarks_summary, ym_summary,
                         repeated_remarks, theme_summary):
    """Create a multi-sheet Excel workbook for download."""
    output_file = BytesIO()
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        full_dataset.to_excel(writer, index=False, sheet_name="01_Full_Data_Duplicate_Flag")
        clean_dataset.to_excel(writer, index=False, sheet_name="02_Clean_Unique_Data")
        duplicate_dataset.to_excel(writer, index=False, sheet_name="03_Duplicate_Only")
        duplicate_summary.to_excel(writer, index=False, sheet_name="04_Duplicate_Summary")
        clean_summary_tables["Region_Wise_House_Visits"].to_excel(writer, index=False, sheet_name="05_Region_Summary")
        clean_summary_tables["State_Wise_House_Visits"].to_excel(writer, index=False, sheet_name="06_State_Summary")
        clean_summary_tables["Funder_Wise_House_Visits"].to_excel(writer, index=False, sheet_name="07_Funder_Summary")
        clean_summary_tables["TMO_Wise_House_Visits"].to_excel(writer, index=False, sheet_name="08_TMO_Summary")
        clean_summary_tables["YM_Wise_House_Visits"].to_excel(writer, index=False, sheet_name="09_YM_Summary")
        clean_summary_tables["House_Visit_Type_Wise"].to_excel(writer, index=False, sheet_name="10_HV_Type_Summary")
        remarks_dataset.to_excel(writer, index=False, sheet_name="11_Remarks_Row_Level")
        remarks_summary.to_excel(writer, index=False, sheet_name="12_Remarks_Summary")
        ym_summary.to_excel(writer, index=False, sheet_name="13_YM_Leaderboard")
        repeated_remarks.to_excel(writer, index=False, sheet_name="14_Repeated_Remarks")
        theme_summary.to_excel(writer, index=False, sheet_name="15_Theme_Summary")
    output_file.seek(0)
    return output_file


def get_risk_label(rate: float) -> str:
    """Simple executive risk banding for rates."""
    if rate <= 20:
        return "Low"
    if rate <= 50:
        return "Watch"
    return "High"


# ============================================================
# HEADER
# ============================================================
clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=130)

logout_col1, logout_col2 = st.columns([8, 1])
with logout_col2:
    if st.button("Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

today = datetime.now().strftime("%d %b %Y")
quote = SPORTS_QUOTES[datetime.now().day % len(SPORTS_QUOTES)]

st.markdown('<div class="center-title">House Visit Data Quality Intelligence Platform (DQI)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="center-subtitle">Duplicate Detection • Clean Data Summary • Remarks Intelligence • Template Detection • Field Data Quality</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([2, 1])
with left:
    st.markdown(
        f"""
        <div class="quote-card">
            <b>Sports mindset for data quality</b><br>
            “{quote}”
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    st.markdown(
        f"""
        <div class="date-card">
            <b>Report Date</b><br>
            {today}<br>
            <span class="metric-note">System date from deployment server</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

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


# ============================================================
# UPLOAD AND RUN
# ============================================================
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

            full_dataset, clean_dataset, duplicate_dataset, duplicate_summary = process_housevisit_dqi(raw_df)
            clean_summary_tables = create_clean_summary(clean_dataset)
            remarks_dataset, remarks_summary, ym_summary, repeated_remarks, theme_summary = create_remarks_intelligence(clean_dataset)

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

            base_name = uploaded.name.rsplit(".", 1)[0]
            output_name = f"{base_name}_DQI_Intelligence_Output.xlsx"
            zip_name = f"{base_name}_DQI_Intelligence_Bundle.zip"

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Leadership Overview",
                "Clean Data Summary",
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
                k3.metric("Duplicate Records Removed", f"{duplicate_records:,}", f"{duplicate_rate}%")
                k4.metric("Remarks Quality Base", f"{clean_records:,}", "Clean data only")

                k5, k6, k7, k8 = st.columns(4)
                k5.metric("Same Remark Repeated", f"{same_remark_count:,}", f"{same_remark_rate}% of clean")
                k6.metric("Template-like Remarks", f"{template_flag_count:,}", f"{template_rate}% of clean")
                k7.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}", f"{ai_rate}% of clean")
                k8.metric("Blank Remarks", f"{blank_remarks_count:,}", f"{blank_rate}% of clean")

                st.info(
                    "Clean Unique House Visits is the base for all summary charts. Remarks flags can overlap, so the counts will not add up to clean records."
                )

                r1, r2 = st.columns([1, 1])
                with r1:
                    risk_df = pd.DataFrame({
                        "Indicator": [
                            "Duplicate Rate",
                            "Same Remark Repeated Rate",
                            "Template-like Remark Rate",
                            "Possible AI/Prompt Copy Rate",
                            "Blank Remark Rate",
                        ],
                        "Rate %": [duplicate_rate, same_remark_rate, template_rate, ai_rate, blank_rate],
                        "Risk": [
                            get_risk_label(duplicate_rate),
                            get_risk_label(same_remark_rate),
                            get_risk_label(template_rate),
                            get_risk_label(ai_rate),
                            get_risk_label(blank_rate),
                        ],
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
                st.caption("All charts below use Clean Unique House Visits only and include value labels.")

                c1, c2 = st.columns(2)
                with c1:
                    render_labeled_bar_chart(clean_summary_tables["Region_Wise_House_Visits"], "REGION", "House Visits", "Region-wise house visits", orientation="v")
                with c2:
                    render_labeled_bar_chart(clean_summary_tables["State_Wise_House_Visits"], "STATE", "House Visits", "State-wise house visits", orientation="h")

                c3, c4 = st.columns(2)
                with c3:
                    render_labeled_bar_chart(clean_summary_tables["Funder_Wise_House_Visits"], "Funder", "House Visits", "Funder-wise house visits", orientation="h")
                with c4:
                    render_labeled_bar_chart(clean_summary_tables["TMO_Wise_House_Visits"], "TMO Name", "House Visits", "Top TMO-wise house visits", orientation="h")

                st.markdown("### Top YM-wise house visits")
                render_labeled_bar_chart(clean_summary_tables["YM_Wise_House_Visits"], "YM Name", "House Visits", "Top YM-wise house visits", orientation="h")

                st.markdown("### House Visit Type-wise visits")
                st.caption("This chart shows whether house visits are regular, irregular, issue-based, or any other type available in the HOUSE VISIT TYPE field.")
                render_labeled_bar_chart(clean_summary_tables["House_Visit_Type_Wise"], "HOUSE VISIT TYPE", "House Visits", "House Visit Type-wise house visits", orientation="h")

                st.markdown("### Summary Tables")
                table_tab1, table_tab2, table_tab3, table_tab4, table_tab5, table_tab6 = st.tabs(["Region", "State", "Funder", "TMO", "YM", "House Visit Type"])
                with table_tab1:
                    st.dataframe(clean_summary_tables["Region_Wise_House_Visits"], use_container_width=True, hide_index=True)
                with table_tab2:
                    st.dataframe(clean_summary_tables["State_Wise_House_Visits"], use_container_width=True, hide_index=True)
                with table_tab3:
                    st.dataframe(clean_summary_tables["Funder_Wise_House_Visits"], use_container_width=True, hide_index=True)
                with table_tab4:
                    st.dataframe(clean_summary_tables["TMO_Wise_House_Visits"], use_container_width=True, hide_index=True)
                with table_tab5:
                    st.dataframe(clean_summary_tables["YM_Wise_House_Visits"], use_container_width=True, hide_index=True)
                with table_tab6:
                    st.dataframe(clean_summary_tables["House_Visit_Type_Wise"], use_container_width=True, hide_index=True)

            with tab3:
                st.subheader("Duplicate Intelligence")
                st.caption("Duplicate logic: PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE")

                d1, d2, d3 = st.columns(3)
                d1.metric("Total Records", f"{total_records:,}")
                d2.metric("Clean Unique Records", f"{clean_records:,}")
                d3.metric("Duplicate Removed", f"{duplicate_records:,}", f"{duplicate_rate}%")

                st.markdown("### Duplicate Summary")
                st.dataframe(duplicate_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Full Dataset with Duplicate Flag")
                st.dataframe(full_dataset.head(200), use_container_width=True, hide_index=True)

            with tab4:
                st.subheader("Remarks Intelligence")
                st.caption("Remarks intelligence is calculated on clean unique data only to avoid duplicate inflation.")

                q1, q2, q3, q4 = st.columns(4)
                q1.metric("Clean Records Analysed", f"{clean_records:,}")
                q2.metric("Same Remark Repeated", f"{same_remark_count:,}", f"{same_remark_rate}%")
                q3.metric("Template-like Remarks", f"{template_flag_count:,}", f"{template_rate}%")
                q4.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}", f"{ai_rate}%")

                st.markdown("### Remarks Summary by Geography / Program")
                st.dataframe(remarks_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Repeated Remarks")
                st.dataframe(repeated_remarks.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Theme Summary")
                st.dataframe(theme_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Row-level Remarks Intelligence")
                row_cols = [
                    "REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type",
                    "TMO Name", "YM Name", "CHILD ID", "HOUSE VISIT DATE", "REMARKS",
                    "Same_Remark_Repeated", "Template_Flag", "Template_Score", "Template_Reason",
                    "Possible_AI_Prompt_Copy", "Remarks_Themes", "Remarks_Word_Count", "Remarks_Quality_Band",
                ]
                st.dataframe(remarks_dataset[row_cols].head(300), use_container_width=True, hide_index=True)

            with tab5:
                st.subheader("Methodology / FAQ")
                st.markdown("""
                ### Data privacy / storage
                The app does not save uploaded files to a database or permanent folder. Your file is processed temporarily in the active Streamlit session/runtime to create the dashboard and Excel output. The app is providing a running space for analysis, not a data storage system.

                ### Quality Risk Snapshot
                This table converts important data-quality rates into a simple review band. Currently, the rule is: **0–20% = Low**, **21–50% = Watch**, and **above 50% = High**. The rates shown are duplicate rate, same remark repeated rate, template-like remark rate, possible AI/prompt-copy rate, and blank remark rate. These are operational review signals, not final audit conclusions.

                ### Top Themes
                Top Themes are generated from clean unique remarks using keyword mapping. For example, words like `exam`, `study`, and `academic` are mapped to Education / Exam Readiness; words like `kitchen garden`, `study corner`, `digital`, `career`, and `parents` are mapped to respective intervention themes. One remark can have multiple themes.

                ### Total Records Uploaded
                This is the total number of rows read after removing completely blank rows and Power BI footer rows such as Applied Filters. It represents the raw usable input volume before duplicate removal.

                ### Clean Unique House Visits
                This is the retained dataset after duplicate removal. One record is retained for each duplicate business key. This is the main denominator used for clean-data charts and remarks intelligence.

                ### Duplicate Records Removed
                These are repeated records after the first record within the same duplicate key. Duplicate percentage = Duplicate Records Removed / Total Records Uploaded × 100.

                ### Remarks Quality Base
                Remarks Quality Base is equal to Clean Unique House Visits. Remarks analysis is intentionally done on clean data only so duplicate rows do not inflate copy-paste or template metrics.

                ### Same Remark Repeated
                This flags records where the exact same cleaned remark is reused within the same operational context: PROGRAM LAUNCH NAME + Sub Type + HOUSE VISIT TYPE + TMO Name + YM Name. This is the copy-paste signal. It is calculated as a count and as % of clean data.

                ### Template-like Remarks
                This is a rule-based flag. A remark is marked as template-like when it has signals such as common opening phrases, generic programme phrases, multiple standard intervention keywords, long structured wording, or possible prompt-copy phrases. This can overlap with Same Remark Repeated.

                ### Possible AI / Prompt Copy
                This catches obvious prompt-copy artefacts such as `Here is an improved version`, `additional relevant line`, `ChatGPT`, `draft`, or similar wording. It is a strong review signal because such text usually should not appear in field remarks.

                ### Blank Remarks
                This counts clean unique house visit records where remarks are blank, missing, or equivalent to null-like values.

                ### Duplicate Intelligence
                Duplicate Intelligence uses this key: PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE. The first record in a key is retained as unique; repeated rows in the same key are marked Duplicate = 1.

                ### Remarks Intelligence
                Remarks Intelligence is calculated on clean unique data only. It gives row-level flags, geography/program summaries, YM-level review metrics, repeated remarks, and theme summaries. Same Remark Repeated, Template-like Remarks, Possible AI/Prompt Copy, and Blank Remarks are overlapping flags, so they should not be added together.

                ### Download Reports
                The Excel output contains multiple sheets explained below.

                | Sheet | Meaning |
                |---|---|
                | 01_Full_Data_Duplicate_Flag | Full cleaned input with Duplicate = 0/1, duplicate key, duplicate order, and group size. |
                | 02_Clean_Unique_Data | Final unique house visit dataset after removing duplicates. |
                | 03_Duplicate_Only | Rows removed as duplicates. |
                | 04_Duplicate_Summary | Duplicate groups with record count, removed count, HouseVisitID list, and sample remarks. |
                | 05_Region_Summary | Clean unique house visit count by Region. |
                | 06_State_Summary | Clean unique house visit count by State. |
                | 07_Funder_Summary | Clean unique house visit count by Funder. |
                | 08_TMO_Summary | Clean unique house visit count by TMO. |
                | 09_YM_Summary | Clean unique house visit count by YM. |
                | 10_HV_Type_Summary | Clean unique house visit count by HOUSE VISIT TYPE, such as regular, irregular, or issue-based. |
                | 11_Remarks_Row_Level | Row-level remarks intelligence with repeated remark flag, template flag, AI/prompt flag, themes, word count, and quality band. |
                | 12_Remarks_Summary | Remarks quality summary by Region, State, District, Program, and Sub Type. |
                | 13_YM_Leaderboard | YM/TMO-level review table showing copy-paste score, template score, blank remarks, and average word count. |
                | 14_Repeated_Remarks | Exact repeated remarks by operational context, with reuse count and child count. |
                | 15_Theme_Summary | Theme-level summary showing which field topics appear most often. |
                """)

            with tab6:
                st.subheader("Download Reports")
                st.download_button(
                    "Download Complete DQI Intelligence Excel",
                    data=output_xlsx.getvalue(),
                    file_name=output_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(output_name, output_xlsx.getvalue())
                zip_buffer.seek(0)

                st.download_button(
                    "Download ZIP Bundle",
                    data=zip_buffer,
                    file_name=zip_name,
                    mime="application/zip",
                )

                st.markdown("### Excel sheets included")
                st.write(
                    """
                    01_Full_Data_Duplicate_Flag  
                    02_Clean_Unique_Data  
                    03_Duplicate_Only  
                    04_Duplicate_Summary  
                    05_Region_Summary  
                    06_State_Summary  
                    07_Funder_Summary  
                    08_TMO_Summary  
                    09_YM_Summary  
                    10_HV_Type_Summary  
                    11_Remarks_Row_Level  
                    12_Remarks_Summary  
                    13_YM_Leaderboard  
                    14_Repeated_Remarks  
                    15_Theme_Summary
                    """
                )

        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.markdown(
        """
        <div class="section-card">
        <b>Upload a House Visit file to begin.</b><br>
        <b>Data privacy note:</b> The app does not store your uploaded dataset permanently. It processes the file temporarily in the running Streamlit session/runtime and provides downloadable outputs.<br><br>
        This app is designed for free Streamlit Cloud deployment and uses only open-source Python libraries:
        <code>streamlit</code>, <code>pandas</code>, <code>openpyxl</code>, and <code>plotly</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )
