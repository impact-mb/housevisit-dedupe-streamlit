import streamlit as st
import pandas as pd
import base64
from io import BytesIO
import zipfile
from pathlib import Path

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
        lambda row: row.astype(str)
        .str.contains("Applied filters", case=False, na=False)
        .any(),
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

    # Required dichotomous variable
    # 0 = Unique / first valid record
    # 1 = Duplicate / repeated record
    df["Duplicate"] = df["Duplicate_Order"].apply(lambda x: 1 if x > 0 else 0)

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

    output_file = BytesIO()
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        full_dataset.to_excel(writer, index=False, sheet_name="Full_Data_With_Duplicate_Flag")
        clean_dataset.to_excel(writer, index=False, sheet_name="Clean_Unique_Data")
        duplicate_dataset.to_excel(writer, index=False, sheet_name="Duplicate_Only")
        duplicate_summary.to_excel(writer, index=False, sheet_name="Duplicate_Summary")

    output_file.seek(0)

    return full_dataset, clean_dataset, duplicate_dataset, duplicate_summary, output_file, stats

def create_remarks_analysis(df: pd.DataFrame):
    df = remove_footer_and_blank_rows(df)
    df = apply_schema_types(df)

    group_cols = [
        "REGION",
        "STATE",
        "DISTRICT",
        "PROGRAM LAUNCH NAME",
        "Sub Type",
    ]

    df["REMARKS_CLEAN"] = (
        df["REMARKS"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    df["REMARKS_STATUS"] = df["REMARKS_CLEAN"].apply(
        lambda x: "Blank / Missing"
        if x == "" or x.lower() in ["nan", "none"]
        else "Available"
    )

    summary = (
        df.groupby(group_cols, dropna=False)
        .agg(
            Total_Records=("CHILD ID", "count"),
            Unique_Children=("CHILD ID", "nunique"),
            Remarks_Available=("REMARKS_STATUS", lambda x: (x == "Available").sum()),
            Remarks_Blank=("REMARKS_STATUS", lambda x: (x == "Blank / Missing").sum()),
            Unique_Remarks=("REMARKS_CLEAN", "nunique"),
        )
        .reset_index()
    )

    summary["Remarks_Available_%"] = (
        summary["Remarks_Available"] / summary["Total_Records"] * 100
    ).round(1)

    summary["Remarks_Blank_%"] = (
        summary["Remarks_Blank"] / summary["Total_Records"] * 100
    ).round(1)

    top_remarks = (
        df[df["REMARKS_STATUS"] == "Available"]
        .groupby("REMARKS_CLEAN")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    blank_remarks = df[df["REMARKS_STATUS"] == "Blank / Missing"].copy()

    analysis_file = BytesIO()
    with pd.ExcelWriter(analysis_file, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Remarks_Summary")
        top_remarks.to_excel(writer, index=False, sheet_name="Top_Remarks")
        blank_remarks.to_excel(writer, index=False, sheet_name="Blank_Remarks")

    analysis_file.seek(0)

    return summary, top_remarks, blank_remarks, analysis_file

clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=140)

st.title("House Visit Data Quality Intelligence Platform (DQI)")

st.write("""
This tool identifies duplicate House Visit records using:

PROGRAM LAUNCH NAME + ProjectType + CHILD ID + TMO Name + YM Name + HOUSE VISIT DATE

It creates:
1. Full dataset with Duplicate flag  
2. Clean unique dataset only  
3. Duplicate-only dataset  
4. Duplicate summary  
5. Remarks quality analysis  
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

            (
                full_dataset,
                clean_dataset,
                duplicate_dataset,
                duplicate_summary,
                dqi_xlsx,
                stats,
            ) = process_housevisit_dqi(df)

            remarks_summary, top_remarks, blank_remarks, remarks_xlsx = create_remarks_analysis(df)

            base_name = uploaded.name.rsplit(".", 1)[0]
            dqi_name = f"{base_name}_DQI_Output.xlsx"
            remarks_name = f"{base_name}_Remarks_Analysis.xlsx"
            zip_name = f"{base_name}_DQI_Bundle.zip"

            st.subheader("DQI Summary")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Records", stats["rows_before"])
            col2.metric("Clean Unique Records", stats["clean_rows"])
            col3.metric("Duplicate Records", stats["duplicate_rows"])
            col4.metric("Duplicate Groups", stats["duplicate_groups"])

            st.subheader("Duplicate Summary")
            st.dataframe(duplicate_summary.head(100), use_container_width=True)

            st.subheader("Full Dataset with Duplicate Flag")
            st.dataframe(full_dataset.head(100), use_container_width=True)

            st.subheader("Clean Unique Dataset")
            st.dataframe(clean_dataset.head(100), use_container_width=True)

            st.subheader("Remarks Analysis")
            st.dataframe(remarks_summary.head(100), use_container_width=True)

            st.download_button(
                "Download DQI Output Excel",
                data=dqi_xlsx.getvalue(),
                file_name=dqi_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                "Download Remarks Analysis Excel",
                data=remarks_xlsx.getvalue(),
                file_name=remarks_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(dqi_name, dqi_xlsx.getvalue())
                zf.writestr(remarks_name, remarks_xlsx.getvalue())

            zip_buffer.seek(0)

            st.download_button(
                "Download Complete DQI Bundle ZIP",
                data=zip_buffer,
                file_name=zip_name,
                mime="application/zip",
            )

        except Exception as e:
            st.error(f"Error: {e}")