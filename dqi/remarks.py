"""
Module Name : remarks.py

Purpose:
--------
Performance-optimized Remarks Intelligence engine.

Version:
--------
3.1.0
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
    text = (
        text.lower()
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def detect_themes_from_normalized(
    text_norm: str,
) -> str:
    """Assign themes to text that has already been normalized."""
    themes = [
        theme
        for theme, keywords
        in THEME_KEYWORDS.items()
        if any(
            keyword in text_norm
            for keyword in keywords
        )
    ]

    return (
        ", ".join(themes)
        if themes
        else "Unclassified"
    )


def detect_ai_from_normalized(
    text_norm: str,
) -> int:
    """Detect AI/prompt-copy phrases in already-normalized text."""
    return int(
        any(
            phrase in text_norm
            for phrase in AI_PROMPT_COPY_PHRASES
        )
    )


def template_detection_normalized(
    text_norm: str,
    theme_count: int,
    ai_flag: int,
) -> tuple:
    """
    Template detection without re-normalizing the same remark repeatedly.
    """
    if text_norm == "":
        return (
            0,
            0,
            "Blank remark",
        )

    score = 0
    reasons = []

    if any(
        text_norm.startswith(opening)
        for opening in COMMON_TEMPLATE_OPENINGS
    ):
        score += 25
        reasons.append(
            "Common opening phrase"
        )

    matched_generic = [
        phrase
        for phrase in GENERIC_TEMPLATE_PHRASES
        if phrase in text_norm
    ]

    if matched_generic:
        score += 20
        reasons.append(
            "Generic programme phrase"
        )

    if theme_count >= 3:
        score += 15
        reasons.append(
            "Multiple standard intervention keywords"
        )

    word_count = len(
        text_norm.split()
    )

    if (
        word_count >= 25
        and matched_generic
    ):
        score += 15
        reasons.append(
            "Long structured programme-style remark"
        )

    if ai_flag:
        score += 40
        reasons.append(
            "Possible AI/prompt copy phrase"
        )

    return (
        int(score >= 40),
        min(score, 100),
        (
            " + ".join(reasons)
            if reasons
            else "No template signal"
        ),
    )


def remarks_quality_band(
    word_count: int,
    blank_flag: int,
    ai_flag: int,
    same_flag: int,
    template_flag: int,
) -> str:
    """Create a row-level quality band for review prioritization."""
    if blank_flag == 1:
        return "Poor - Blank"
    if ai_flag == 1:
        return (
            "Critical Review - "
            "Possible AI/Prompt Copy"
        )
    if (
        same_flag == 1
        and template_flag == 1
    ):
        return (
            "High Review - "
            "Repeated Template"
        )
    if same_flag == 1:
        return (
            "Review - Repeated Remark"
        )
    if template_flag == 1:
        return (
            "Review - Template-like"
        )
    if word_count <= 5:
        return "Poor - Too Short"
    if word_count <= 15:
        return "Fair"
    if word_count <= 35:
        return "Good"
    return "Detailed"


class RemarksIntelligence:
    """OOP wrapper for remarks intelligence."""

    def create(
        self,
        clean_dataset: pd.DataFrame,
    ):
        """
        Build remarks intelligence using clean unique data only.

        Version 3.1 avoids repeatedly normalising the same remark and
        replaces the Python iterrows theme expansion with explode().
        """
        df = clean_dataset.copy()

        df["REMARKS_CONTEXT_KEY"] = make_key(
            df,
            REMARKS_CONTEXT_COLS,
        )

        df["REMARKS_CLEAN"] = (
            df["REMARKS"]
            .fillna("")
            .astype(str)
            .str.replace(
                r"\s+",
                " ",
                regex=True,
            )
            .str.strip()
        )

        # Normalize each remark once.
        df["REMARKS_CANONICAL"] = (
            df["REMARKS_CLEAN"]
            .map(normalize_text)
        )

        df["Blank_Remark"] = (
            df["REMARKS_CANONICAL"]
            .isin(
                [
                    "",
                    "nan",
                    "none",
                ]
            )
            .astype(int)
        )

        df["Remarks_Word_Count"] = (
            df["REMARKS_CANONICAL"]
            .str.split()
            .str.len()
            .fillna(0)
            .astype(int)
        )

        same_remark_group = (
            REMARK_REUSE_GROUP_COLS
            + ["REMARKS_CANONICAL"]
        )

        df["Same_Remark_Group_Size"] = (
            df.groupby(
                same_remark_group,
                dropna=False,
            )["REMARKS_CANONICAL"]
            .transform("count")
        )

        df["Same_Remark_Repeated"] = (
            (
                df["Same_Remark_Group_Size"]
                > 1
            )
            & (
                df["Blank_Remark"]
                == 0
            )
        ).astype(int)

        # Themes and AI checks are based on the already-normalized text.
        df["Remarks_Themes"] = (
            df["REMARKS_CANONICAL"]
            .map(
                detect_themes_from_normalized
            )
        )

        df["Theme_Count"] = (
            df["Remarks_Themes"]
            .map(
                lambda value:
                0
                if value == "Unclassified"
                else len(
                    value.split(", ")
                )
            )
        )

        df["Possible_AI_Prompt_Copy"] = (
            df["REMARKS_CANONICAL"]
            .map(
                detect_ai_from_normalized
            )
        )

        template_results = [
            template_detection_normalized(
                text_norm,
                int(theme_count),
                int(ai_flag),
            )
            for text_norm, theme_count, ai_flag
            in zip(
                df["REMARKS_CANONICAL"],
                df["Theme_Count"],
                df["Possible_AI_Prompt_Copy"],
            )
        ]

        template_results = pd.Series(
            template_results,
            index=df.index,
        )

        df["Template_Flag"] = (
            template_results
            .map(lambda result: result[0])
        )

        df["Template_Score"] = (
            template_results
            .map(lambda result: result[1])
        )

        df["Template_Reason"] = (
            template_results
            .map(lambda result: result[2])
        )

        df["Remarks_Quality_Band"] = [
            remarks_quality_band(
                word_count,
                blank_flag,
                ai_flag,
                same_flag,
                template_flag,
            )
            for (
                word_count,
                blank_flag,
                ai_flag,
                same_flag,
                template_flag,
            ) in zip(
                df["Remarks_Word_Count"],
                df["Blank_Remark"],
                df["Possible_AI_Prompt_Copy"],
                df["Same_Remark_Repeated"],
                df["Template_Flag"],
            )
        ]

        group_cols = [
            "REGION",
            "STATE",
            "DISTRICT",
            "PROGRAM LAUNCH NAME",
            "Sub Type",
        ]

        remarks_summary = (
            df.groupby(
                group_cols,
                dropna=False,
            )
            .agg(
                Clean_Unique_Records=(
                    "CHILD ID",
                    "count",
                ),
                Unique_Children=(
                    "CHILD ID",
                    "nunique",
                ),
                Blank_Remarks=(
                    "Blank_Remark",
                    "sum",
                ),
                Same_Remark_Repeated=(
                    "Same_Remark_Repeated",
                    "sum",
                ),
                Template_Flag=(
                    "Template_Flag",
                    "sum",
                ),
                Possible_AI_Prompt_Copy=(
                    "Possible_AI_Prompt_Copy",
                    "sum",
                ),
                Avg_Remarks_Word_Count=(
                    "Remarks_Word_Count",
                    "mean",
                ),
                Unique_Remarks=(
                    "REMARKS_CANONICAL",
                    "nunique",
                ),
            )
            .reset_index()
        )

        base = (
            remarks_summary[
                "Clean_Unique_Records"
            ]
            .replace(0, pd.NA)
        )

        remarks_summary[
            "Same_Remark_Repeated_%"
        ] = (
            remarks_summary[
                "Same_Remark_Repeated"
            ]
            .div(base)
            .mul(100)
            .fillna(0)
            .round(1)
        )

        remarks_summary[
            "Template_Flag_%"
        ] = (
            remarks_summary[
                "Template_Flag"
            ]
            .div(base)
            .mul(100)
            .fillna(0)
            .round(1)
        )

        remarks_summary[
            "Blank_Remark_%"
        ] = (
            remarks_summary[
                "Blank_Remarks"
            ]
            .div(base)
            .mul(100)
            .fillna(0)
            .round(1)
        )

        remarks_summary[
            "Avg_Remarks_Word_Count"
        ] = (
            remarks_summary[
                "Avg_Remarks_Word_Count"
            ]
            .round(1)
        )

        ym_summary = (
            df.groupby(
                [
                    "REGION",
                    "STATE",
                    "DISTRICT",
                    "TMO Name",
                    "YM Name",
                ],
                dropna=False,
            )
            .agg(
                Clean_Unique_Records=(
                    "CHILD ID",
                    "count",
                ),
                Unique_Children=(
                    "CHILD ID",
                    "nunique",
                ),
                Same_Remark_Repeated=(
                    "Same_Remark_Repeated",
                    "sum",
                ),
                Template_Flag=(
                    "Template_Flag",
                    "sum",
                ),
                Possible_AI_Prompt_Copy=(
                    "Possible_AI_Prompt_Copy",
                    "sum",
                ),
                Blank_Remarks=(
                    "Blank_Remark",
                    "sum",
                ),
                Avg_Word_Count=(
                    "Remarks_Word_Count",
                    "mean",
                ),
                Unique_Remarks=(
                    "REMARKS_CANONICAL",
                    "nunique",
                ),
            )
            .reset_index()
        )

        ym_base = (
            ym_summary[
                "Clean_Unique_Records"
            ]
            .replace(0, pd.NA)
        )

        ym_summary[
            "Copy_Paste_Score_%"
        ] = (
            ym_summary[
                "Same_Remark_Repeated"
            ]
            .div(ym_base)
            .mul(100)
            .fillna(0)
            .round(1)
        )

        ym_summary[
            "Template_Score_%"
        ] = (
            ym_summary[
                "Template_Flag"
            ]
            .div(ym_base)
            .mul(100)
            .fillna(0)
            .round(1)
        )

        ym_summary["Avg_Word_Count"] = (
            ym_summary[
                "Avg_Word_Count"
            ]
            .round(1)
        )

        ym_summary = (
            ym_summary
            .sort_values(
                [
                    "Copy_Paste_Score_%",
                    "Template_Score_%",
                ],
                ascending=False,
            )
        )

        repeated_remarks = (
            df[
                df["Blank_Remark"]
                == 0
            ]
            .groupby(
                REMARK_REUSE_GROUP_COLS
                + ["REMARKS_CLEAN"],
                dropna=False,
            )
            .agg(
                Reuse_Count=(
                    "REMARKS_CLEAN",
                    "count",
                ),
                Child_Count=(
                    "CHILD ID",
                    "nunique",
                ),
                First_House_Visit_Date=(
                    "HOUSE VISIT DATE",
                    "min",
                ),
                Last_House_Visit_Date=(
                    "HOUSE VISIT DATE",
                    "max",
                ),
            )
            .reset_index()
            .query(
                "Reuse_Count > 1"
            )
            .sort_values(
                "Reuse_Count",
                ascending=False,
            )
        )

        # Vectorized theme expansion instead of iterrows().
        theme_df = df[
            [
                "REGION",
                "STATE",
                "DISTRICT",
                "PROGRAM LAUNCH NAME",
                "Sub Type",
                "CHILD ID",
                "Remarks_Themes",
            ]
        ].copy()

        theme_df["Theme"] = (
            theme_df[
                "Remarks_Themes"
            ]
            .str.split(", ")
        )

        theme_df = (
            theme_df
            .explode("Theme")
            .drop(
                columns=[
                    "Remarks_Themes"
                ]
            )
        )

        if not theme_df.empty:
            theme_summary = (
                theme_df.groupby(
                    [
                        "REGION",
                        "STATE",
                        "DISTRICT",
                        "PROGRAM LAUNCH NAME",
                        "Sub Type",
                        "Theme",
                    ],
                    dropna=False,
                )
                .agg(
                    Records=(
                        "Theme",
                        "count",
                    ),
                    Unique_Children=(
                        "CHILD ID",
                        "nunique",
                    ),
                )
                .reset_index()
                .sort_values(
                    "Records",
                    ascending=False,
                )
            )
        else:
            theme_summary = pd.DataFrame(
                columns=[
                    "REGION",
                    "STATE",
                    "DISTRICT",
                    "PROGRAM LAUNCH NAME",
                    "Sub Type",
                    "Theme",
                    "Records",
                    "Unique_Children",
                ]
            )

        return (
            df,
            remarks_summary,
            ym_summary,
            repeated_remarks,
            theme_summary,
        )
