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

