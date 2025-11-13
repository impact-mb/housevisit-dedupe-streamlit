# housevisit-dedupe-streamlit

House Visit Dedupe Tool (Streamlit Web App)

A simple and fast web-based House Visit duplicate remover built using Python + Streamlit.
Anyone can upload their Excel file and instantly get:
  A deduped Excel file (keeps only 1st occurrence)
  A separate file of removed duplicates (for audit)
  Zero installation — works fully in browser
  Safe, local processing — file never leaves your browser session

Features
  Upload any .xlsx House Visit file
  Automatically checks duplicates using key fields:
      CHILD ID
      HOUSE VISIT DATE
      VISIT DATE
      GROUP ID
      TMO Name
      YM Name

Generates two Excel files:
  filename__dedup.xlsx → Cleaned file
  filename_dupl_remove.xlsx → All removed rows

No login, no coding — 100% browser-based
Works on mobile, laptop, or tablet
Ideal for multi-state teams needing quick data fixes

How It Works

User uploads an Excel file
  System cleans & standardizes key columns
  A COMBINED key is created for each row
  Duplicates are detected using groupby().cumcount()
  First row is kept, the rest are moved to “removed” sheet
  Two downloadable Excel files are returned
