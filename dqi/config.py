"""
Module Name : config.py

Purpose:
--------
Central configuration for House Visit Data Quality Intelligence Platform (DQI):
schema, business keys, remarks rules, themes, and dashboard constants.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

APP_NAME = "House Visit Data Quality Intelligence Platform (DQI)"
APP_VERSION = "1.0.0"
BUILD = "2026.06"
OWNER = "Magic Bus Data Team"

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
    "Program Awareness": ["magic bus", "magicbus", "program", "programme", "three year", "three-year journey"],
}

COMMON_TEMPLATE_OPENINGS = [
    "we met", "we discussed", "met with parents", "met with the parents",
    "during the home visit", "today we met", "today, we met", "explain about",
    "explained about", "discussed about", "we explained", "we meet",
]

GENERIC_TEMPLATE_PHRASES = [
    "overall development", "importance of education", "study corner and kitchen garden",
    "kitchen garden and study corner", "daily study plans", "academic progress",
    "magic bus program", "magic bus programme", "life skills sessions", "digital literacy sessions",
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

EXCEL_SHEETS = [
    ("01_Full_Data_Duplicate_Flag", "Full cleaned input with Duplicate = 0/1, duplicate key, duplicate order, and duplicate group size."),
    ("02_Clean_Unique_Data", "Final clean unique house visit dataset after duplicate removal."),
    ("03_Duplicate_Only", "Rows removed as duplicate records."),
    ("04_Duplicate_Summary", "Duplicate groups with records in key, duplicate removed count, HouseVisitID list, and sample remarks."),
    ("05_Region_Summary", "Clean unique house visit count by Region."),
    ("06_State_Summary", "Clean unique house visit count by State."),
    ("07_Funder_Summary", "Clean unique house visit count by Funder."),
    ("08_TMO_Summary", "Clean unique house visit count by TMO."),
    ("09_YM_Summary", "Clean unique house visit count by YM."),
    ("10_HV_Type_Summary", "Clean unique house visit count by HOUSE VISIT TYPE."),
    ("11_Remarks_Row_Level", "Row-level remarks intelligence with repeated remark, template, AI/prompt, theme, word count, and quality band."),
    ("12_Remarks_Summary", "Remarks quality summary by Region, State, District, Program Launch Name, and Sub Type."),
    ("13_YM_Leaderboard", "YM/TMO-level review table showing copy-paste score, template score, blank remarks, and average word count."),
    ("14_Repeated_Remarks", "Exact repeated remarks by operational context with reuse count and child count."),
    ("15_Theme_Summary", "Theme-level summary showing which field topics appear most often."),
]
