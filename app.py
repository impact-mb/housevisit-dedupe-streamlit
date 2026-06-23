
import streamlit as st
import pandas as pd
import base64
from io import BytesIO
import zipfile
from pathlib import Path
from datetime import datetime
import re
from difflib import SequenceMatcher

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(
    page_title="House Visit Data Quality Intelligence Platform (DQI)",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# LOGIN CONFIG - USE STREAMLIT SECRETS FOR WEB DEPLOYMENT
# ============================================================
def get_login_credentials():
    """
    Reads login credentials from Streamlit secrets.
    For Streamlit Cloud, add these secrets in App settings:

    [auth]
    username = "north_admin"
    password = "Magic@1234"
    """
    try:
        username = st.secrets["auth"]["username"]
        password = st.secrets["auth"]["password"]
        return username, password
    except Exception:
        return None, None


def render_login_page():
    st.markdown(
        """
        <style>
            .login-title {
                text-align: center;
                font-size: 30px;
                font-weight: 800;
                color: #1f2937;
                margin-top: 40px;
                margin-bottom: 5px;
            }
            .login-subtitle {
                text-align: center;
                font-size: 15px;
                color: #6b7280;
                margin-bottom: 28px;
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

    st.markdown('<div class="login-title">House Visit Data Quality Intelligence Platform (DQI)</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">Secure Access Layer</div>', unsafe_allow_html=True)

    expected_username, expected_password = get_login_credentials()

    if not expected_username or not expected_password:
        st.markdown(
            """
            <div class="login-warning">
                <b>Login secrets are not configured.</b><br>
                Add credentials in <code>.streamlit/secrets.toml</code> for local use or in Streamlit Cloud secrets for web deployment.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    col_left, col_mid, col_right = st.columns([1, 1.2, 1])
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
# CSS - CXO FRIENDLY UI
# ============================================================
st.markdown(
    """
    <style>
        .main {
            background-color: #FAFAF7;
        }
        .center-title {
            text-align: center;
            font-size: 34px;
            font-weight: 800;
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
        .top-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.04);
            min-height: 96px;
        }
        .quote-card {
            background: #fff7e6;
            border-left: 6px solid #f59e0b;
            border-radius: 14px;
            padding: 15px 18px;
            color: #374151;
            font-size: 15px;
            min-height: 92px;
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
        .metric-note {
            font-size: 13px;
            color: #6b7280;
        }
        .risk-good {
            color: #047857;
            font-weight: 700;
        }
        .risk-watch {
            color: #b45309;
            font-weight: 700;
        }
        .risk-high {
            color: #b91c1c;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# SCHEMA
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

# Duplicate key requested earlier
DEDUPE_KEY_COLS = [
    "PROGRAM LAUNCH NAME",
    "ProjectType",
    "CHILD ID",
    "TMO Name",
    "YM Name",
    "HOUSE VISIT DATE",
]

# Remarks context key requested by user
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
    "we met",
    "we discussed",
    "met with parents",
    "met with the parents",
    "during the home visit",
    "today we met",
    "today, we met",
    "explain about",
    "explained about",
    "discussed about",
    "we explained",
    "we meet",
]

GENERIC_TEMPLATE_PHRASES = [
    "overall development",
    "importance of education",
    "study corner and kitchen garden",
    "kitchen garden and study corner",
    "daily study plans",
    "academic progress",
    "magic bus program",
    "life skills sessions",
    "digital literacy sessions",
    "parents were requested",
    "parents actively participated",
    "provided updates",
]

AI_PROMPT_COPY_PHRASES = [
    "here is an improved version",
    "additional relevant line",
    "as an ai",
    "chatgpt",
    "generated response",
    "improved version",
    "relevant line",
    "draft",
    "rewrite",
]

SPORTS_QUOTES = [
    "Champions keep playing until they get it right.",
    "You miss 100% of the shots you don’t take.",
    "Discipline turns practice into performance.",
    "Pressure is a privilege.",
    "Consistency beats intensity when the season is long.",
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def clickable_logo(img_path, link_url, width=130):
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
    df = df.copy()
    df = df.dropna(how="all")

    footer_mask = df.apply(
        lambda row: row.astype(str)
        .str.contains("Applied filters", case=False, na=False)
        .any(),
        axis=1,
    )

    df = df[~footer_mask]
    return df.reset_index(drop=True)


def apply_schema_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for col, dtype in SCHEMA.items():
        if col not in df.columns:
            df[col] = ""
            continue

        if dtype == "date":
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=True,
            ).dt.date
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
    text = "" if pd.isna(text) else str(text)
    text = text.lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_key(df: pd.DataFrame, cols: list) -> pd.Series:
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


def detect_themes(text: str) -> str:
    text_norm = normalize_text(text)
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(k in text_norm for k in keywords):
            themes.append(theme)
    return ", ".join(themes) if themes else "Unclassified"


def count_themes(text: str) -> int:
    theme_string = detect_themes(text)
    if theme_string == "Unclassified":
        return 0
    return len(theme_string.split(", "))


def detect_ai_prompt_copy(text: str) -> int:
    text_norm = normalize_text(text)
    return int(any(phrase in text_norm for phrase in AI_PROMPT_COPY_PHRASES))


def template_detection(text: str) -> tuple:
    """
    Returns Template_Flag, Template_Score, Template_Reason.
    This is rule-based and free/open-source friendly.
    """
    text_norm = normalize_text(text)
    if text_norm == "":
        return 0, 0, "Blank remark"

    score = 0
    reasons = []

    if any(text_norm.startswith(opening) for opening in COMMON_TEMPLATE_OPENINGS):
        score += 25
        reasons.append("Common opening phrase")

    matched_generic = [p for p in GENERIC_TEMPLATE_PHRASES if p in text_norm]
    if len(matched_generic) >= 1:
        score += 20
        reasons.append("Generic programme phrase")

    themes_count = count_themes(text_norm)
    if themes_count >= 3:
        score += 15
        reasons.append("Multiple standard intervention keywords")

    word_count = len(text_norm.split())
    if word_count >= 25 and matched_generic:
        score += 15
        reasons.append("Long structured programme-style remark")

    if detect_ai_prompt_copy(text_norm):
        score += 40
        reasons.append("Possible AI/prompt copy phrase")

    flag = int(score >= 40)
    return flag, min(score, 100), " + ".join(reasons) if reasons else "No template signal"


def remarks_quality_band(word_count: int, blank_flag: int, ai_flag: int, same_flag: int, template_flag: int) -> str:
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


def pct(num, den):
    return round((num / den * 100), 1) if den else 0.0


# ============================================================
# DQI DUPLICATE PROCESSING
# ============================================================
def process_housevisit_dqi(df: pd.DataFrame):
    df = remove_footer_and_blank_rows(df)
    df = apply_schema_types(df)

    df["DQI_DUPLICATE_KEY"] = make_key(df, DEDUPE_KEY_COLS)

    df["Duplicate_Order"] = df.groupby("DQI_DUPLICATE_KEY").cumcount()
    df["Duplicate_Group_Size"] = df.groupby("DQI_DUPLICATE_KEY")["DQI_DUPLICATE_KEY"].transform("count")

    # 0 = Unique / first valid record
    # 1 = Duplicate / repeated record
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
# REMARKS INTELLIGENCE
# ============================================================
def create_remarks_intelligence(clean_dataset: pd.DataFrame):
    """
    Important: Remarks intelligence is calculated on clean unique data only.
    This avoids duplicate rows inflating copy-paste/template results.
    """
    df = clean_dataset.copy()

    df["REMARKS_CONTEXT_KEY"] = make_key(df, REMARKS_CONTEXT_COLS)

    df["REMARKS_CLEAN"] = (
        df["REMARKS"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    df["REMARKS_CANONICAL"] = df["REMARKS_CLEAN"].apply(normalize_text)
    df["Blank_Remark"] = df["REMARKS_CANONICAL"].apply(lambda x: 1 if x == "" or x in ["nan", "none"] else 0)
    df["Remarks_Word_Count"] = df["REMARKS_CANONICAL"].apply(lambda x: len(x.split()) if x else 0)

    # Same remark repeated: exact same canonical remark reused by the same TMO/YM/program/visit-type context.
    same_remark_group = REMARK_REUSE_GROUP_COLS + ["REMARKS_CANONICAL"]
    df["Same_Remark_Group_Size"] = df.groupby(same_remark_group, dropna=False)["REMARKS_CANONICAL"].transform("count")
    df["Same_Remark_Repeated"] = ((df["Same_Remark_Group_Size"] > 1) & (df["Blank_Remark"] == 0)).astype(int)

    # Template detection
    template_results = df["REMARKS_CLEAN"].apply(template_detection)
    df["Template_Flag"] = template_results.apply(lambda x: x[0])
    df["Template_Score"] = template_results.apply(lambda x: x[1])
    df["Template_Reason"] = template_results.apply(lambda x: x[2])

    df["Possible_AI_Prompt_Copy"] = df["REMARKS_CLEAN"].apply(detect_ai_prompt_copy)

    # Theme tagging
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

    # Executive-level summaries
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

    remarks_summary["Same_Remark_Repeated_%"] = remarks_summary.apply(
        lambda r: pct(r["Same_Remark_Repeated"], r["Clean_Unique_Records"]), axis=1
    )
    remarks_summary["Template_Flag_%"] = remarks_summary.apply(
        lambda r: pct(r["Template_Flag"], r["Clean_Unique_Records"]), axis=1
    )
    remarks_summary["Blank_Remark_%"] = remarks_summary.apply(
        lambda r: pct(r["Blank_Remarks"], r["Clean_Unique_Records"]), axis=1
    )
    remarks_summary["Avg_Remarks_Word_Count"] = remarks_summary["Avg_Remarks_Word_Count"].round(1)

    # Leaderboard by YM
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
    ym_summary["Copy_Paste_Score_%"] = ym_summary.apply(
        lambda r: pct(r["Same_Remark_Repeated"], r["Clean_Unique_Records"]), axis=1
    )
    ym_summary["Template_Score_%"] = ym_summary.apply(
        lambda r: pct(r["Template_Flag"], r["Clean_Unique_Records"]), axis=1
    )
    ym_summary["Avg_Word_Count"] = ym_summary["Avg_Word_Count"].round(1)
    ym_summary = ym_summary.sort_values(["Copy_Paste_Score_%", "Template_Score_%"], ascending=False)

    # Top repeated remarks
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

    # Theme summary
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
                         remarks_dataset, remarks_summary, ym_summary, repeated_remarks, theme_summary):
    output_file = BytesIO()
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        full_dataset.to_excel(writer, index=False, sheet_name="01_Full_Data_Duplicate_Flag")
        clean_dataset.to_excel(writer, index=False, sheet_name="02_Clean_Unique_Data")
        duplicate_dataset.to_excel(writer, index=False, sheet_name="03_Duplicate_Only")
        duplicate_summary.to_excel(writer, index=False, sheet_name="04_Duplicate_Summary")
        remarks_dataset.to_excel(writer, index=False, sheet_name="05_Remarks_Row_Level")
        remarks_summary.to_excel(writer, index=False, sheet_name="06_Remarks_Summary")
        ym_summary.to_excel(writer, index=False, sheet_name="07_YM_Leaderboard")
        repeated_remarks.to_excel(writer, index=False, sheet_name="08_Repeated_Remarks")
        theme_summary.to_excel(writer, index=False, sheet_name="09_Theme_Summary")

    output_file.seek(0)
    return output_file


def get_risk_label(rate):
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
    '<div class="center-subtitle">Duplicate Detection • Remarks Intelligence • Copy-Paste Review • Template Detection • Field Data Quality</div>',
    unsafe_allow_html=True
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
        unsafe_allow_html=True
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
        unsafe_allow_html=True
    )

st.markdown("---")

st.markdown(
    """
    <div class="section-card">
    <b>How to read the DQI dashboard:</b><br>
    Duplicate records are removed first. Remarks intelligence is then calculated only on the <b>Clean Unique Dataset</b>.
    Therefore, Same Remark Repeated, Template Flag, Blank Remarks, and AI/Prompt Copy are quality flags within the clean data.
    These flags can overlap, so they should not be added together.
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# UPLOAD
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
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            full_dataset, clean_dataset, duplicate_dataset, duplicate_summary = process_housevisit_dqi(df)
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

            base_name = uploaded.name.rsplit(".", 1)[0]
            output_name = f"{base_name}_DQI_Intelligence_Output.xlsx"
            zip_name = f"{base_name}_DQI_Intelligence_Bundle.zip"

            output_xlsx = create_excel_outputs(
                full_dataset, clean_dataset, duplicate_dataset, duplicate_summary,
                remarks_dataset, remarks_summary, ym_summary, repeated_remarks, theme_summary
            )

            tab1, tab2, tab3, tab4 = st.tabs([
                "Executive Summary",
                "Duplicate Intelligence",
                "Remarks Intelligence",
                "Downloads"
            ])

            with tab1:
                st.subheader("CXO Summary")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Records Uploaded", f"{total_records:,}")
                col2.metric("Clean Unique Records", f"{clean_records:,}")
                col3.metric("Duplicate Records Removed", f"{duplicate_records:,}", f"{duplicate_rate}%")
                col4.metric("Remarks Quality Base", f"{clean_records:,}", "Clean data only")

                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Same Remark Repeated", f"{same_remark_count:,}", f"{same_remark_rate}% of clean")
                col6.metric("Template-like Remarks", f"{template_flag_count:,}", f"{template_rate}% of clean")
                col7.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}", f"{ai_rate}% of clean")
                col8.metric("Blank Remarks", f"{blank_remarks_count:,}", f"{blank_rate}% of clean")

                st.info(
                    "Important: Same Remark Repeated and Template-like Remarks are overlapping quality flags. "
                    "A single clean record can be counted in both categories."
                )

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("### Quality Risk Snapshot")
                    risk_df = pd.DataFrame({
                        "Indicator": [
                            "Duplicate Rate",
                            "Same Remark Repeated Rate",
                            "Template-like Remark Rate",
                            "Possible AI/Prompt Copy Rate",
                            "Blank Remark Rate",
                        ],
                        "Rate %": [
                            duplicate_rate,
                            same_remark_rate,
                            template_rate,
                            ai_rate,
                            blank_rate,
                        ],
                        "Risk": [
                            get_risk_label(duplicate_rate),
                            get_risk_label(same_remark_rate),
                            get_risk_label(template_rate),
                            get_risk_label(ai_rate),
                            get_risk_label(blank_rate),
                        ]
                    })
                    st.dataframe(risk_df, use_container_width=True, hide_index=True)

                with c2:
                    st.markdown("### Theme Distribution")
                    if not theme_summary.empty:
                        theme_chart = (
                            theme_summary.groupby("Theme", as_index=False)["Records"].sum()
                            .sort_values("Records", ascending=False)
                            .head(10)
                        )
                        st.bar_chart(theme_chart.set_index("Theme"))
                    else:
                        st.write("No theme data available.")

                st.markdown("### Top YM / TMO Quality Review")
                st.dataframe(
                    ym_summary.head(20),
                    use_container_width=True,
                    hide_index=True
                )

            with tab2:
                st.subheader("Duplicate Intelligence")
                st.caption(
                    "Duplicate logic: PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE"
                )

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Records", f"{total_records:,}")
                col2.metric("Clean Unique Records", f"{clean_records:,}")
                col3.metric("Duplicate Removed", f"{duplicate_records:,}", f"{duplicate_rate}%")

                st.markdown("### Duplicate Summary")
                st.dataframe(duplicate_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Full Dataset with Duplicate Flag")
                st.dataframe(full_dataset.head(200), use_container_width=True, hide_index=True)

            with tab3:
                st.subheader("Remarks Intelligence")
                st.caption(
                    "Remarks intelligence is calculated on clean unique data only to avoid duplicate inflation."
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Clean Records Analysed", f"{clean_records:,}")
                c2.metric("Same Remark Repeated", f"{same_remark_count:,}", f"{same_remark_rate}%")
                c3.metric("Template-like Remarks", f"{template_flag_count:,}", f"{template_rate}%")
                c4.metric("Possible AI / Prompt Copy", f"{ai_prompt_count:,}", f"{ai_rate}%")

                st.markdown("### Remarks Summary by Geography / Program")
                st.dataframe(remarks_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Repeated Remarks")
                st.dataframe(repeated_remarks.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Theme Summary")
                st.dataframe(theme_summary.head(200), use_container_width=True, hide_index=True)

                st.markdown("### Row Level Remarks Intelligence")
                st.dataframe(
                    remarks_dataset[
                        [
                            "REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type",
                            "TMO Name", "YM Name", "CHILD ID", "HOUSE VISIT DATE",
                            "REMARKS", "Same_Remark_Repeated", "Template_Flag",
                            "Template_Score", "Template_Reason", "Possible_AI_Prompt_Copy",
                            "Remarks_Themes", "Remarks_Word_Count", "Remarks_Quality_Band"
                        ]
                    ].head(300),
                    use_container_width=True,
                    hide_index=True
                )

            with tab4:
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

                st.markdown("### Excel Sheets Included")
                st.write(
                    """
                    01_Full_Data_Duplicate_Flag  
                    02_Clean_Unique_Data  
                    03_Duplicate_Only  
                    04_Duplicate_Summary  
                    05_Remarks_Row_Level  
                    06_Remarks_Summary  
                    07_YM_Leaderboard  
                    08_Repeated_Remarks  
                    09_Theme_Summary  
                    """
                )

        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.markdown(
        """
        <div class="section-card">
        <b>Upload a House Visit file to begin.</b><br>
        The app is designed for free Streamlit Cloud deployment and uses only open-source Python libraries:
        <code>streamlit</code>, <code>pandas</code>, and <code>openpyxl</code>.
        </div>
        """,
        unsafe_allow_html=True
    )
