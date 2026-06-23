"""
Module Name : exporter.py

Purpose:
--------
Excel, PDF, and ZIP export functions for House Visit DQI.
PDF export uses ReportLab only. No Matplotlib dependency.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import zipfile
from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from .config import EXCEL_SHEETS


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


def _summary_table_for_pdf(df: pd.DataFrame, name_col: str, value_col: str, title: str, max_rows: int = 20):
    """Build a compact ReportLab table for a summary section."""
    rows = [[title, "House Visits"]]
    for _, r in df.head(max_rows).iterrows():
        rows.append([str(r[name_col]), f"{int(r[value_col]):,}"])
    table = Table(rows, repeatRows=1, colWidths=[6.8 * inch, 1.6 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def create_clean_summary_pdf(clean_summary_tables: dict) -> BytesIO:
    """Create a ReportLab PDF containing all Clean Data Summary tables."""
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("House Visit Data Quality Intelligence Platform (DQI)", styles["Title"]))
    story.append(Paragraph("Clean Data Summary After Deduplication", styles["Heading2"]))
    story.append(Paragraph("This PDF uses clean unique house visits only. It is generated with ReportLab and does not use Matplotlib.", styles["BodyText"]))
    story.append(Spacer(1, 14))

    sections = [
        ("House_Visit_Type_Wise", "HOUSE VISIT TYPE", "House Visit Type-wise visits"),
        ("Region_Wise_House_Visits", "REGION", "Region-wise house visits"),
        ("State_Wise_House_Visits", "STATE", "State-wise house visits"),
        ("Funder_Wise_House_Visits", "Funder", "Funder-wise house visits"),
        ("TMO_Wise_House_Visits", "TMO Name", "Top TMO-wise house visits"),
        ("YM_Wise_House_Visits", "YM Name", "Top YM-wise house visits"),
    ]

    for idx, (key, col, title) in enumerate(sections):
        if idx > 0:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(_summary_table_for_pdf(clean_summary_tables[key], col, "House Visits", title, max_rows=25))

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer


def create_zip_bundle(files: dict) -> BytesIO:
    """Create a ZIP bundle from filename -> bytes mapping."""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer


def excel_sheet_explanation_df() -> pd.DataFrame:
    """Return Excel sheet explanations as a DataFrame."""
    return pd.DataFrame(EXCEL_SHEETS, columns=["Sheet", "Meaning"])
