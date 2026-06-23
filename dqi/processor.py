"""
Module Name : processor.py

Purpose:
--------
Data cleaning, schema standardization, duplicate detection, and clean summary tables.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import pandas as pd
from .config import SCHEMA, DEDUPE_KEY_COLS


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


def make_summary_table(df: pd.DataFrame, group_col: str, top_n: int = 20) -> pd.DataFrame:
    """Create a clean unique house-visit count summary."""
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


class DQIProcessor:
    """OOP wrapper for the data cleaning and duplicate engine."""

    def process(self, raw_df: pd.DataFrame):
        """Clean input data, identify duplicates, and produce full/clean/duplicate datasets."""
        df = remove_footer_and_blank_rows(raw_df)
        df = apply_schema_types(df)

        df["DQI_DUPLICATE_KEY"] = make_key(df, DEDUPE_KEY_COLS)
        df["Duplicate_Order"] = df.groupby("DQI_DUPLICATE_KEY").cumcount()
        df["Duplicate_Group_Size"] = df.groupby("DQI_DUPLICATE_KEY")["DQI_DUPLICATE_KEY"].transform("count")
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

    def clean_summary(self, clean_dataset: pd.DataFrame) -> dict:
        """Create all dashboard summary tables from clean unique data."""
        return {
            "House_Visit_Type_Wise": make_summary_table(clean_dataset, "HOUSE VISIT TYPE", top_n=20),
            "Region_Wise_House_Visits": make_summary_table(clean_dataset, "REGION", top_n=50),
            "State_Wise_House_Visits": make_summary_table(clean_dataset, "STATE", top_n=50),
            "Funder_Wise_House_Visits": make_summary_table(clean_dataset, "Funder", top_n=50),
            "TMO_Wise_House_Visits": make_summary_table(clean_dataset, "TMO Name", top_n=30),
            "YM_Wise_House_Visits": make_summary_table(clean_dataset, "YM Name", top_n=30),
        }
