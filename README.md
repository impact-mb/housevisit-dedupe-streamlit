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
