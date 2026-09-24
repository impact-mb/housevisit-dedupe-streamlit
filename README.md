# House Visit Data Quality Intelligence Platform (DQI)

Magic Bus internal Streamlit app for House Visit duplicate detection, clean-data summaries, remarks intelligence, and downloadable data quality reports.

## Deployment

Deploy on Streamlit Community Cloud using `app.py` as the entry point.

## Secrets

Configure Streamlit secrets:

```toml
[auth]
username = "north_admin"
password = "Magic@1234"
```

## Architecture

- `app.py` - main orchestrator
- `dqi/auth.py` - login/logout
- `dqi/config.py` - schema, rules, constants
- `dqi/processor.py` - cleaning and duplicate engine
- `dqi/remarks.py` - remarks intelligence
- `dqi/charts.py` - Plotly chart helpers
- `dqi/spatial.py` - India map / spatial analysis
- `dqi/exporter.py` - Excel, PDF, ZIP exports
- `dqi/faq.py` - methodology / FAQ
- `dqi/ui.py` - dashboard UI


---

## Executive Insights (CXO View)

Version 3.0.0 introduces a dedicated **Executive Insights** page for CXO / leadership review.

The page is designed to answer three questions quickly:

1. **What is the scale of delivery?**
2. **Where is delivery concentrated or potentially at risk?**
3. **What requires management attention?**

### CXO KPIs

| KPI | Definition |
|---|---|
| **Total Clean House Visits** | Number of records remaining after the application's configured duplicate-removal process. |
| **Unique Children Reached** | One record per `CHILD ID`, retaining the latest `HOUSE VISIT DATE`. |
| **Average Visits per Child** | `Total Clean House Visits / Unique Children Reached`. This is an engagement-intensity indicator. |
| **Duplicate Rate** | Share of uploaded records identified as duplicates using the configured house-visit duplicate logic. |
| **Regions Covered** | Number of distinct non-blank `REGION` values in clean data. |
| **States Covered** | Number of distinct non-blank `STATE` values in clean data. |
| **Districts Covered** | Number of distinct non-blank `DISTRICT` values in clean data. |
| **Program Launches** | Number of distinct non-blank `PROGRAM LAUNCH NAME` values in clean data. |
| **Children with 90+ Days Since Latest Visit** | Unique children whose retained latest house visit is more than 90 days before the latest valid `HOUSE VISIT DATE` available in the uploaded dataset. |
| **Children with 5+ House Visits** | Unique children with at least five clean house-visit records. This is a review flag, not automatically an error. |
| **Critical Data Quality Exception Rows** | Clean rows with a missing critical field (`CHILD ID`, `HOUSE VISIT DATE`, `REGION`, `STATE`, `DISTRICT`, `PROGRAM LAUNCH NAME`) or an invalid house-visit date. |

### Executive charts

The Executive Insights page includes:

- Top 5 Funders by House Visits
- Top 5 Districts by House Visits
- Latest House Visit Recency
- House Visit Frequency per Child

Each chart includes **CSV** and **Excel** download buttons inside the chart card.

### Latest House Visit Recency

Recency is calculated against the **latest valid `HOUSE VISIT DATE` in the uploaded dataset**, not the computer's current date.

Buckets used:

- 0–30 days
- 31–60 days
- 61–90 days
- 90+ days
- Invalid / Missing Date

### Attention Required

The page automatically surfaces management attention signals for:

- children whose latest visit is 90+ days old,
- children with 5+ clean house visits,
- critical missing/invalid data fields,
- duplicate-rate observations.

These are **review signals**, not automatic conclusions that programme delivery or data entry is incorrect. Operational validation should be completed using the detailed dashboard pages and source records.


---

## Version 3.1.0 - Performance Optimization

Version 3.1.0 keeps the same dashboard logic and CXO KPIs while reducing unnecessary processing on Streamlit Cloud.

### Performance changes

- **Cached file parsing:** uploaded CSV/Excel bytes are parsed once and reused.
- **Cached DQI analysis:** duplicate processing, clean summaries and Remarks Intelligence are cached against the uploaded file content.
- **Content-based file key:** SHA-256 is used so a genuinely different file is not mistaken for a previous upload with the same filename/size.
- **Lazy Excel/PDF generation:** the 15-sheet Excel workbook and PDF report are no longer created during initial analysis.
- **Prepare Download Files:** full Excel, PDF and ZIP packages are generated only when requested from the Downloads page.
- **Faster footer cleanup:** Power BI footer detection uses column-wise vectorised matching instead of row-by-row Python processing.
- **Optimized Remarks Intelligence:** remark text is normalized once, percentages use vectorised calculations, and theme expansion uses `explode()` instead of `iterrows()`.
- **Cached Unique Children dataset:** the one-latest-record-per-child calculation is reused across Streamlit reruns.

### Expected user experience

The first analysis still needs to read and analyse the uploaded file, but the dashboard should become available sooner because large downloadable reports are deferred.

Changing filters or interacting with the dashboard should also avoid repeating the full upload/analysis pipeline.

The first time a user clicks **Prepare Download Files**, there may still be a short wait while the Excel, PDF and ZIP files are created. This work is intentionally deferred until it is actually needed.


### Version 3.1.1 compatibility fix

Version 3.1.1 includes the matching `dqi/charts.py` required by the Executive Insights and chart-level CSV/Excel download features. This prevents deployment errors caused by an older chart helper that does not accept the new export arguments.


### Version 3.1.2 - Upload Validation

To improve stability on Streamlit Cloud, the application now applies a strict upload rule:

- Allowed file formats: **Excel** (`.xlsx`, `.xls`, `.xlsm`) and **CSV** (`.csv`) only.
- File size must be **less than 10 MB**.
- Files that are 10 MB or larger are rejected before DQI processing starts.
- `.streamlit/config.toml` also sets the Streamlit server upload limit to 10 MB.

For larger datasets, reduce the file size before upload by removing unnecessary columns/rows, saving as CSV where appropriate, or splitting the dataset by reporting period.
