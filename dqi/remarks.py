"""
Module Name : remarks.py

Purpose:
--------
Remarks Intelligence engine: copy-paste score, template detection, possible AI/prompt-copy detection,
theme tagging, and row-level quality bands.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import re
import pandas as pd
from .config import (
    AI_PROMPT_COPY_PHRASES,
    COMMON_TEMPLATE_OPENINGS,
    GENERIC_TEMPLATE_PHRASES,
    REMARK_REUSE_GROUP_COLS,
    REMARKS_CONTEXT_COLS,
    THEME_KEYWORDS,
)
from .processor import make_key, pct


def normalize_text(text: str) -> str:
    """Create a canonical text version for rule-based analytics."""
    text = "" if pd.isna(text) else str(text)
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_themes(text: str) -> str:
    """Assign one or more themes to a remark using keyword rules."""
    text_norm = normalize_text(text)
    themes = [theme for theme, keywords in THEME_KEYWORDS.items() if any(k in text_norm for k in keywords)]
    return ", ".join(themes) if themes else "Unclassified"


def count_themes(text: str) -> int:
    """Return number of detected themes."""
    theme_string = detect_themes(text)
    return 0 if theme_string == "Unclassified" else len(theme_string.split(", "))


def detect_ai_prompt_copy(text: str) -> int:
    """Flag clear copy-paste remnants from AI/prompt interfaces."""
    text_norm = normalize_text(text)
    return int(any(phrase in text_norm for phrase in AI_PROMPT_COPY_PHRASES))


def template_detection(text: str) -> tuple:
    """Rule-based template detection using openings, generic phrases, theme density, and AI artefacts."""
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


class RemarksIntelligence:
    """OOP wrapper for remarks intelligence."""

    def create(self, clean_dataset: pd.DataFrame):
        """Build remarks intelligence using clean unique data only."""
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
