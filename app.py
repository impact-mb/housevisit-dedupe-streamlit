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
# CLICKABLE LOGO FUNCTION
# -------------------------------------------
def clickable_logo(img_path, link_url, width=150):
    """Displays a clickable image that opens a link in a new tab."""
    try:
        img_bytes = Path(img_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode()

        st.markdown(
            f"""
            <a href="{link_url}" target="_blank">
                <img src="data:image/png;base64,{encoded}" width="{width}" />
            </a>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        st.warning("⚠️ Logo file not found. Please keep 'magicbus_logo.png' in the same folder.")


# -------------------------------------------
# DE-DUPE LOGIC FUNCTION
# -------------------------------------------
def process_housevisit_dedupe(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Convert date columns
    for col in ["HOUSE VISIT DATE", "VISIT DATE"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    # Cleaner helper
    def safe_col(col):
        if col in df.columns:
            return df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        else:
            return pd.Series([""] * len(df), index=df.index)

    child_id = safe_col("CHILD ID").str.replace(r"\.0$", "", regex=True)
    hvd     = safe_col("HOUSE VISIT DATE")
    vd      = safe_col("VISIT DATE")
    group   = safe_col("GROUP ID")
    tmo     = safe_col("TMO Name")
    ym      = safe_col("YM Name")

    # COMBINED key
    df["COMBINED"] = (
        child_id + " | " + hvd + " | " + vd + " | " + group + " | " + tmo + " | " + ym
    )

    # Duplicate marker
    df["duplicat"] = df.groupby("COMBINED").cumcount()

    # Split outputs
    deduped = df[df["duplicat"] == 0].copy()
    removed = df[df["duplicat"] > 0].copy()

    stats = {
        "rows_before": len(df),
        "rows_after": len(deduped),
        "removed": len(removed),
    }

    # Excel Outputs in memory
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

# Clickable logo
clickable_logo("magicbus_logo.png", "https://www.magicbus.org/", width=140)

st.title("Duplicate House Visit Remover")

st.write(
    """
    This tool removes **duplicate House Visit records** based on:

    - CHILD ID  
    - HOUSE VISIT DATE  
    - VISIT DATE  
    - GROUP ID  
    - TMO Name  
    - YM Name  

    It generates **two Excel files**:
    - Cleaned file (deduped)
    - Removed rows file (all duplicates)
    - ZIP file containing both
    """
)

uploaded = st.file_uploader("Upload House Visit Excel File (.xlsx)", type=["xlsx", "xlsm"])

if uploaded:

    st.success(f"File uploaded: **{uploaded.name}**")

    if st.button("Run Tool"):
        try:
            df = pd.read_excel(uploaded)
            main_xlsx, removed_xlsx, stats = process_housevisit_dedupe(df)

            base_name = uploaded.name.rsplit(".", 1)[0]
            dedup_name = f"{base_name}__dedup.xlsx"
            removed_name = f"{base_name}_dupl_remove.xlsx"
            zip_name = f"{base_name}_dedupe_bundle.zip"

            # Summary
            st.subheader("Summary")
            st.write(f"- Total rows: **{stats['rows_before']}**")
            st.write(f"- After dedupe: **{stats['rows_after']}**")
            st.write(f"- Duplicates removed: **{stats['removed']}**")

            # Filenames display
            st.write("### Files ready:")
            st.write(f"- **{dedup_name}**")
            st.write(f"- **{removed_name}**")

            # Individual downloads
            st.download_button(
                "Download Deduped File",
                data=main_xlsx.getvalue(),
                file_name=dedup_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_dedup",
            )

            st.download_button(
                "Download Removed Rows File",
                data=removed_xlsx.getvalue(),
                file_name=removed_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_removed",
            )

            # ZIP download for both files
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
                key="dl_zip",
            )

        except Exception as e:
            st.error(f"Error: {e}")