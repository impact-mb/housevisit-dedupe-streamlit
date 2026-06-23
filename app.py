import streamlit as st
import pandas as pd
import base64
from io import BytesIO
import zipfile
from pathlib import Path
import re

st.set_page_config(
    page_title="House Visit Data Quality Intelligence Platform (DQI)",
    layout="wide"
)

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

REMARKS_CONTEXT_KEY_COLS = [
    "PROGRAM LAUNCH NAME",
    "Sub Type",
    "HOUSE VISIT TYPE",
    "TMO Name",
    "YM Name",
    "CHILD ID",
    "HOUSE VISIT DATE",
]

THEME_KEYWORDS = {
    "Education / Study": ["study", "education", "academic", "exam", "exms", "10th", "class", "timetable", "school", "homework", "learning"],
    "Kitchen Garden": ["kitchen garden", "kichen garden", "garden"],
    "Study Corner": ["study corner", "study corners"],
    "Life Skills": ["life skill", "life skills", "communication", "leadership", "critical thinking"],
    "Digital Literacy": ["digital", "computer", "online", "technology"],
    "Career Awareness": ["career", "career awareness", "job", "future"],
    "Parent Engagement": ["parent", "parents", "mother", "father", "guardian", "parents meeting", "parent meeting"],
    "Health / Wellbeing": ["health", "discipline", "hygiene", "wellbeing", "well-being"],
    "Program Awareness": ["magic bus", "magicbus", "program", "programme", "sessions"],
}

COMMON_TEMPLATE_PHRASES = [
    "we met", "we meet", "met with parents", "met with the parents",
    "during the home visit", "today we met", "we discussed", "discussed about",
    "explain about", "explained about", "we explained", "parents were requested",
    "we highlighted", "we also explained"
]

AI_SUSPICIOUS_PHRASES = [
    "here is an improved version", "additional relevant line", "improved version",
    "overall development", "actively participated", "expected outcomes"
]


def clickable_logo(img_path, link_url, width=150):
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


def remove_footer_and_blank_rows(df: pd.DataFrame):
    df = df.copy()
    df = df.dropna(how="all")

    footer_mask = df.apply(
        lambda row: row.astype(str).str.contains("Applied filters", case=False, na=False).any(),
        axis=1,
    )

    df = df[~footer_mask]
    return df.reset_index(drop=True)


def apply_schema_types(df: pd.DataFrame):
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


def clean_remarks_text(text):
    text = "" if pd.isna(text) else str(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_remarks_text(text):
    text = clean_remarks_text(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_themes(text):
    text_l = normalize_remarks_text(text)
    matched = []

    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            matched.append(theme)

    return " | ".join(matched) if matched else "Unclassified"


def detect_template_reason(text):
    text_l = normalize_remarks_text(text)
    reasons = []

    if len(text_l) == 0:
        return "Blank remarks"

    if any(text_l.startswith(p) or p in text_l for p in COMMON_TEMPLATE_PHRASES):
        reasons.append("Common field template phrase")

    keyword_hits = 0
    for keywords in THEME_KEYWORDS.values():
        if any(kw in text_l for kw in keywords):
            keyword_hits += 1

    if keyword_hits >= 3:
        reasons.append("Repeated intervention keyword pattern")

    if any(p in text_l for p in AI_SUSPICIOUS_PHRASES):
        reasons.append("Possible AI / copied prompt wording")

    words = text_l.split()
    if len(words) >= 25:
        generic_words = ["discussed", "explained", "importance", "parents", "children", "program", "study"]
        if sum(1 for w in generic_words if w in words) >= 4:
            reasons.append("Long generic narrative pattern")

    return " | ".join(reasons)


def remarks_quality_band(word_count):
    if word_count == 0:
        return "Blank"
    elif word_count <= 5:
        return "Poor"
    elif word_count <= 15:
        return "Fair"
    elif word_count <= 30:
        return "Good"
    else:
        return "Detailed"


def risk_band(score):
    if score <= 20:
        return "Low"
    elif score <= 50:
        return "Moderate"
    elif score <= 80:
        return "High"
    else:
        return "Very High"


def process_housevisit_dqi(df: pd.DataFrame):
    df = remove_footer_and_blank_rows(df)
    df = apply_schema_types(df)

    df["DQI_DUPLICATE_KEY"] = (
        df["PROGRAM LAUNCH NAME"] + " | " +
        df["ProjectType"] + " | " +
        df["CHILD ID"] + " | " +
        df["TMO Name"] + " | " +
        df["YM Name"] + " | " +
        df["HOUSE VISIT DATE"].astype(str)
    )

    df["Duplicate_Order"] = df.groupby("DQI_DUPLICATE_KEY").cumcount()
    df["Duplicate_Group_Size"] = df.groupby("DQI_DUPLICATE_KEY")["DQI_DUPLICATE_KEY"].transform("count")

    # 0 = Unique / first record, 1 = Duplicate / repeated record
    df["Duplicate"] = (df["Duplicate_Order"] > 0).astype(int)

    full_dataset = df.copy()
    clean_dataset = df[df["Duplicate"] == 0].copy()
    duplicate_dataset = df[df["Duplicate"] == 1].copy()

    duplicate_summary = (
        df[df["Duplicate_Group_Size"] > 1]
        .groupby(DEDUPE_KEY_COLS, dropna=False)
        .agg(
            Duplicate_Group_Size=("DQI_DUPLICATE_KEY", "count"),
            Duplicate_Removed=("Duplicate", "sum"),
            HouseVisitID_List=("HouseVisitID", lambda x: ", ".join(x.astype(str))),
            Remarks_List=("REMARKS", lambda x: " || ".join(x.astype(str).unique())),
        )
        .reset_index()
        .sort_values("Duplicate_Group_Size", ascending=False)
    )

    stats = {
        "rows_before": len(df),
        "clean_rows": len(clean_dataset),
        "duplicate_rows": len(duplicate_dataset),
        "duplicate_groups": len(duplicate_summary),
    }

    return full_dataset, clean_dataset, duplicate_dataset, duplicate_summary, stats


def create_remarks_intelligence(df: pd.DataFrame):
    df = remove_footer_and_blank_rows(df)
    df = apply_schema_types(df)

    df["REMARKS_CLEAN"] = df["REMARKS"].apply(clean_remarks_text)
    df["REMARKS_NORMALIZED"] = df["REMARKS"].apply(normalize_remarks_text)

    df["REMARKS_CONTEXT_KEY"] = (
        df["PROGRAM LAUNCH NAME"] + " | " +
        df["Sub Type"] + " | " +
        df["HOUSE VISIT TYPE"] + " | " +
        df["TMO Name"] + " | " +
        df["YM Name"] + " | " +
        df["CHILD ID"] + " | " +
        df["HOUSE VISIT DATE"].astype(str)
    )

    df["Remarks_Word_Count"] = df["REMARKS_CLEAN"].apply(lambda x: len(x.split()) if x else 0)
    df["Remarks_Quality_Band"] = df["Remarks_Word_Count"].apply(remarks_quality_band)

    df["REMARKS_STATUS"] = df["REMARKS_CLEAN"].apply(
        lambda x: "Blank / Missing" if x == "" or x.lower() in ["nan", "none"] else "Available"
    )

    # Same remark repeated within the same field context
    df["Same_Remark_Group_Size"] = (
        df.groupby(["REMARKS_CONTEXT_KEY", "REMARKS_NORMALIZED"])["REMARKS_NORMALIZED"]
        .transform("count")
    )
    df["Same_Remark_Order"] = df.groupby(["REMARKS_CONTEXT_KEY", "REMARKS_NORMALIZED"]).cumcount()
    df["Same_Remark_Repeated"] = (df["Same_Remark_Order"] > 0).astype(int)

    df["Template_Reason"] = df["REMARKS_CLEAN"].apply(detect_template_reason)
    df["Template_Flag"] = df["Template_Reason"].apply(lambda x: 1 if x not in ["", "Blank remarks"] else 0)
    df["Possible_AI_or_Prompt_Copy"] = df["Template_Reason"].str.contains("Possible AI", case=False, na=False).astype(int)
    df["Remarks_Theme"] = df["REMARKS_CLEAN"].apply(extract_themes)

    df["Global_Remark_Frequency"] = df.groupby("REMARKS_NORMALIZED")["REMARKS_NORMALIZED"].transform("count")
    df["Global_Repeated_Remark"] = (df["Global_Remark_Frequency"] > 1).astype(int)

    group_cols = ["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type", "TMO Name", "YM Name"]

    copy_paste_score = (
        df.groupby(group_cols, dropna=False)
        .agg(
            Total_Records=("CHILD ID", "count"),
            Unique_Children=("CHILD ID", "nunique"),
            Remarks_Available=("REMARKS_STATUS", lambda x: (x == "Available").sum()),
            Blank_Remarks=("REMARKS_STATUS", lambda x: (x == "Blank / Missing").sum()),
            Same_Remark_Repeated_Count=("Same_Remark_Repeated", "sum"),
            Template_Flag_Count=("Template_Flag", "sum"),
            Possible_AI_or_Prompt_Copy_Count=("Possible_AI_or_Prompt_Copy", "sum"),
            Avg_Word_Count=("Remarks_Word_Count", "mean"),
            Unique_Remarks=("REMARKS_NORMALIZED", "nunique"),
        )
        .reset_index()
    )

    copy_paste_score["Copy_Paste_Score_%"] = (
        copy_paste_score["Same_Remark_Repeated_Count"] / copy_paste_score["Total_Records"] * 100
    ).round(1)
    copy_paste_score["Template_Usage_%"] = (
        copy_paste_score["Template_Flag_Count"] / copy_paste_score["Total_Records"] * 100
    ).round(1)
    copy_paste_score["Blank_Remarks_%"] = (
        copy_paste_score["Blank_Remarks"] / copy_paste_score["Total_Records"] * 100
    ).round(1)
    copy_paste_score["Avg_Word_Count"] = copy_paste_score["Avg_Word_Count"].round(1)
    copy_paste_score["Copy_Paste_Risk_Band"] = copy_paste_score["Copy_Paste_Score_%"].apply(risk_band)

    summary_cols = ["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type"]
    remarks_summary = (
        df.groupby(summary_cols, dropna=False)
        .agg(
            Total_Records=("CHILD ID", "count"),
            Unique_Children=("CHILD ID", "nunique"),
            Remarks_Available=("REMARKS_STATUS", lambda x: (x == "Available").sum()),
            Blank_Remarks=("REMARKS_STATUS", lambda x: (x == "Blank / Missing").sum()),
            Same_Remark_Repeated_Count=("Same_Remark_Repeated", "sum"),
            Template_Flag_Count=("Template_Flag", "sum"),
            Possible_AI_or_Prompt_Copy_Count=("Possible_AI_or_Prompt_Copy", "sum"),
            Avg_Word_Count=("Remarks_Word_Count", "mean"),
            Unique_Remarks=("REMARKS_NORMALIZED", "nunique"),
        )
        .reset_index()
    )

    remarks_summary["Copy_Paste_Score_%"] = (
        remarks_summary["Same_Remark_Repeated_Count"] / remarks_summary["Total_Records"] * 100
    ).round(1)
    remarks_summary["Template_Usage_%"] = (
        remarks_summary["Template_Flag_Count"] / remarks_summary["Total_Records"] * 100
    ).round(1)
    remarks_summary["Blank_Remarks_%"] = (
        remarks_summary["Blank_Remarks"] / remarks_summary["Total_Records"] * 100
    ).round(1)
    remarks_summary["Avg_Word_Count"] = remarks_summary["Avg_Word_Count"].round(1)

    theme_rows = []
    for _, row in df.iterrows():
        for theme in str(row["Remarks_Theme"]).split(" | "):
            theme_rows.append({
                "REGION": row["REGION"],
                "STATE": row["STATE"],
                "DISTRICT": row["DISTRICT"],
                "PROGRAM LAUNCH NAME": row["PROGRAM LAUNCH NAME"],
                "Sub Type": row["Sub Type"],
                "TMO Name": row["TMO Name"],
                "YM Name": row["YM Name"],
                "Remarks_Theme": theme,
            })

    theme_df = pd.DataFrame(theme_rows)
    if not theme_df.empty:
        theme_summary = (
            theme_df.groupby(["REGION", "STATE", "DISTRICT", "PROGRAM LAUNCH NAME", "Sub Type", "Remarks_Theme"], dropna=False)
            .size()
            .reset_index(name="Theme_Count")
            .sort_values("Theme_Count", ascending=False)
        )
    else:
        theme_summary = pd.DataFrame()

    top_repeated_remarks = (
        df[df["REMARKS_STATUS"] == "Available"]
        .groupby("REMARKS_CLEAN")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    context_repeated_remarks = (
        df[df["Same_Remark_Group_Size"] > 1]
        .groupby(REMARKS_CONTEXT_KEY_COLS + ["REMARKS_CLEAN"], dropna=False)
        .agg(
            Same_Remark_Group_Size=("Same_Remark_Group_Size", "max"),
            HouseVisitID_List=("HouseVisitID", lambda x: ", ".join(x.astype(str))),
        )
        .reset_index()
        .sort_values("Same_Remark_Group_Size", ascending=False)
    )

    remarks_stats = {
        "total_records": len(df),
        "same_remark_repeated": int(df["Same_Remark_Repeated"].sum()),
        "template_flag": int(df["Template_Flag"].sum()),
        "blank_remarks": int((df["REMARKS_STATUS"] == "Blank / Missing").sum()),
        "possible_ai": int(df["Possible_AI_or_Prompt_Copy"].sum()),
    }

    return {
        "remarks_full": df,
        "remarks_summary": remarks_summary,
        "copy_paste_score": copy_paste_score,
        "theme_summary": theme_summary,
        "top_repeated_remarks": top_repeated_remarks,
        "context_repeated_remarks": context_repeated_remarks,
        "remarks_stats": remarks_stats,
    }


def create_excel_output(full_dataset, clean_dataset, duplicate_dataset, duplicate_summary, remarks_outputs):
    output_file = BytesIO()

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        full_dataset.to_excel(writer, index=False, sheet_name="Full_Data_Duplicate_Flag")
        clean_dataset.to_excel(writer, index=False, sheet_name="Clean_Unique_Data")
        duplicate_dataset.to_excel(writer, index=False, sheet_name="Duplicate_Only")
        duplicate_summary.to_excel(writer, index=False, sheet_name="Duplicate_Summary")
        remarks_outputs["remarks_full"].to_excel(writer, index=False, sheet_name="Remarks_Full_Intelligence")
        remarks_outputs["remarks_summary"].to_excel(writer, index=False, sheet_name="Remarks_Summary")
        remarks_outputs["copy_paste_score"].to_excel(writer, index=False, sheet_name="Copy_Paste_Score")
        remarks_outputs["theme_summary"].to_excel(writer, index=False, sheet_name="Theme_Summary")
        remarks_outputs["top_repeated_remarks"].to_excel(writer, index=False, sheet_name="Top_Repeated_Remarks")
        remarks_outputs["context_repeated_remarks"].to_excel(writer, index=False, sheet_name="Context_Repeated_Remarks")

    output_file.seek(0)
    return output_file


# -------------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------------
clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=140)

st.markdown(
    """
    <h1 style='text-align: center; color: #1f2937;'>
        House Visit Data Quality Intelligence Platform (DQI)
    </h1>
    <p style='text-align: center; font-size: 17px; color: #4b5563;'>
        Duplicate Detection | Remarks Intelligence | Copy Paste Score | Template Detection
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

with st.expander("DQI Logic Used in This Tool", expanded=False):
    st.write("""
    **Duplicate Detection Key**  
    PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE

    **Remarks Intelligence Context Key**  
    PROGRAM LAUNCH NAME + Sub Type + HOUSE VISIT TYPE + TMO Name + YM Name + CHILD ID + HOUSE VISIT DATE

    **New Variables Added**
    - Duplicate
    - DQI_DUPLICATE_KEY
    - REMARKS_CONTEXT_KEY
    - REMARKS_CLEAN
    - REMARKS_NORMALIZED
    - Same_Remark_Repeated
    - Same_Remark_Group_Size
    - Template_Flag
    - Template_Reason
    - Remarks_Theme
    - Remarks_Word_Count
    - Remarks_Quality_Band
    - Possible_AI_or_Prompt_Copy
    """)

uploaded = st.file_uploader(
    "Upload House Visit Data File (.xlsx, .xls, .xlsm, .csv)",
    type=["xlsx", "xls", "xlsm", "csv"],
)

if uploaded:
    st.success(f"File uploaded: **{uploaded.name}**")

    if st.button("Run DQI Tool"):
        try:
            file_name = uploaded.name.lower()

            if file_name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            full_dataset, clean_dataset, duplicate_dataset, duplicate_summary, dqi_stats = process_housevisit_dqi(df)
            remarks_outputs = create_remarks_intelligence(df)
            output_xlsx = create_excel_output(full_dataset, clean_dataset, duplicate_dataset, duplicate_summary, remarks_outputs)

            base_name = uploaded.name.rsplit(".", 1)[0]
            output_name = f"{base_name}_HouseVisit_DQI_Output.xlsx"
            zip_name = f"{base_name}_HouseVisit_DQI_Bundle.zip"

            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "DQI Summary",
                "Duplicate Detection",
                "Remarks Intelligence",
                "Copy Paste & Template Detection",
                "Downloads",
            ])

            with tab1:
                st.subheader("DQI Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Records", dqi_stats["rows_before"])
                col2.metric("Clean Unique Records", dqi_stats["clean_rows"])
                col3.metric("Duplicate Records", dqi_stats["duplicate_rows"])
                col4.metric("Duplicate Groups", dqi_stats["duplicate_groups"])

                rstats = remarks_outputs["remarks_stats"]
                col5, col6, col7, col8 = st.columns(4)
                col5.metric("Same Remark Repeated", rstats["same_remark_repeated"])
                col6.metric("Template Flag", rstats["template_flag"])
                col7.metric("Blank Remarks", rstats["blank_remarks"])
                col8.metric("Possible AI / Prompt Copy", rstats["possible_ai"])

            with tab2:
                st.subheader("Duplicate Summary")
                st.dataframe(duplicate_summary.head(200), use_container_width=True)
                st.subheader("Full Dataset with Duplicate Flag")
                st.dataframe(full_dataset.head(200), use_container_width=True)
                st.subheader("Clean Unique Dataset")
                st.dataframe(clean_dataset.head(200), use_container_width=True)

            with tab3:
                st.subheader("Remarks Summary")
                st.dataframe(remarks_outputs["remarks_summary"].head(200), use_container_width=True)
                st.subheader("Theme Summary")
                st.dataframe(remarks_outputs["theme_summary"].head(200), use_container_width=True)
                st.subheader("Top Repeated Remarks")
                st.dataframe(remarks_outputs["top_repeated_remarks"].head(100), use_container_width=True)

            with tab4:
                st.subheader("Copy Paste Score by Region / Program / TMO / YM")
                st.dataframe(remarks_outputs["copy_paste_score"].head(200), use_container_width=True)
                st.subheader("Same Remark Repeated within Remarks Context Key")
                st.dataframe(remarks_outputs["context_repeated_remarks"].head(200), use_container_width=True)
                st.subheader("Full Remarks Intelligence Dataset")
                st.dataframe(remarks_outputs["remarks_full"].head(200), use_container_width=True)

            with tab5:
                st.subheader("Download Final Output")
                st.download_button(
                    "Download House Visit DQI Excel Output",
                    data=output_xlsx.getvalue(),
                    file_name=output_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(output_name, output_xlsx.getvalue())
                zip_buffer.seek(0)

                st.download_button(
                    "Download Complete DQI Bundle ZIP",
                    data=zip_buffer,
                    file_name=zip_name,
                    mime="application/zip",
                )

        except Exception as e:
            st.error(f"Error: {e}")
