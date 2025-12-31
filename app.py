import streamlit as st
import pandas as pd
import base64
from io import BytesIO
import zipfile
from pathlib import Path

# -------------------------------------------
# CONFIG
# -------------------------------------------
st.set_page_config(page_title="House Visit Dedupe Tool", layout="centered")

# -------------------------------------------
# SCHEMA DEFINITION
# -------------------------------------------
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

# -------------------------------------------
# CLICKABLE LOGO FUNCTION
# -------------------------------------------
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
            unsafe_allow_html=True
        )
    except Exception:
        st.warning("Logo file not found. Please keep 'magicbus_logo.png' in the same folder.")

# -------------------------------------------
# REMOVE BLANK + FOOTER ROWS
# -------------------------------------------
def remove_footer_and_blank_rows(df: pd.DataFrame):
    df = df.copy()

    # Drop completely empty rows
    df = df.dropna(how="all")

    # Remove footer / metadata rows like "Applied filters"
    footer_mask = df.apply(
        lambda row: row.astype(str)
        .str.contains("Applied filters", case=False, na=False)
        .any(),
        axis=1
    )

    df = df[~footer_mask]

    return df.reset_index(drop=True)

# -------------------------------------------
# APPLY SCHEMA TYPES
# -------------------------------------------
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
                dayfirst=True
            ).dt.date
        else:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\s+", " ", regex=True)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

    return df

# -------------------------------------------
# DE-DUPE LOGIC
# -------------------------------------------
def process_housevisit_dedupe(df: pd.DataFrame):

    # 1️ Clean footer & blank rows
    df = remove_footer_and_blank_rows(df)

    #  Apply schema
    df = apply_schema_types(df)

    #  Build dedupe key (EXACT REQUIRED SEQUENCE)
    df["COMBINED"] = (
        df["HOUSE VISIT TYPE"] + " | " +
        df["CHILD ID"] + " | " +
        df["HOUSE VISIT DATE"].astype(str) + " | " +
        df["GROUP ID"] + " | " +
        df["REMARKS"] + " | " +
        df["HouseVisitID"] + " | " +
        df["TMO Name"] + " | " +
        df["YM Name"]
    )

    #  Identify duplicates
    df["duplicat"] = df.groupby("COMBINED").cumcount()

    deduped = df[df["duplicat"] == 0].copy()
    removed = df[df["duplicat"] > 0].copy()

    stats = {
        "rows_before": len(df),
        "rows_after": len(deduped),
        "removed": len(removed),
    }

    # Write Excel outputs (in memory)
    main_file = BytesIO()
    with pd.ExcelWriter(main_file, engine="openpyxl") as writer:
        deduped.to_excel(writer, index=False, sheet_name="Deduped")
        removed.to_excel(writer, index=False, sheet_name="Duplicates_Only")
    main_file.seek(0)

    removed_file = BytesIO()
    with pd.ExcelWriter(removed_file, engine="openpyxl") as writer:
        removed.to_excel(writer, index=False, sheet_name="Removed")
    removed_file.seek(0)

    return main_file, removed_file, stats

# -------------------------------------------
# STREAMLIT UI
# -------------------------------------------
clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=140)

st.title("Duplicate House Visit Remover")

st.write("""
This tool:
• Removes duplicates using this exact sequence:

HOUSE VISIT TYPE - CHILD ID - HOUSE VISIT DATE - GROUP ID -  
REMARKS - HouseVisitID - TMO Name - YM Name
""")

uploaded = st.file_uploader(
    "Upload House Visit Data File (.xlsx, .xls, .xlsm, .csv)",
    type=["xlsx", "xls", "xlsm", "csv"]
)

if uploaded:
    st.success(f"File uploaded: **{uploaded.name}**")

    if st.button("Run Tool"):
        try:
            file_name = uploaded.name.lower()

            if file_name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)

            main_xlsx, removed_xlsx, stats = process_housevisit_dedupe(df)

            base_name = uploaded.name.rsplit(".", 1)[0]
            dedup_name = f"{base_name}__dedup.xlsx"
            removed_name = f"{base_name}_dupl_remove.xlsx"
            zip_name = f"{base_name}_dedupe_bundle.zip"

            st.subheader("Summary")
            st.write(f"- Total rows read: **{stats['rows_before']}**")
            st.write(f"- After dedupe: **{stats['rows_after']}**")
            st.write(f"- Duplicates removed: **{stats['removed']}**")

            st.download_button(
                "Download Deduped File",
                data=main_xlsx.getvalue(),
                file_name=dedup_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.download_button(
                "Download Removed Rows File",
                data=removed_xlsx.getvalue(),
                file_name=removed_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(dedup_name, main_xlsx.getvalue())
                zf.writestr(removed_name, removed_xlsx.getvalue())
            zip_buffer.seek(0)

            st.download_button(
                "Download BOTH Files (ZIP)",
                data=zip_buffer,
                file_name=zip_name,
                mime="application/zip",
            )

        except Exception as e:
            st.error(f"Error: {e}")