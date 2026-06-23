"""
Module Name : spatial.py

Purpose:
--------
Spatial Data Analysis for India state-wise house visits using Plotly.
Attempts an India state choropleth from public GeoJSON; falls back to a state summary table/bar chart if unavailable.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import json
import urllib.request
import pandas as pd
import plotly.express as px
import streamlit as st
from .charts import render_labeled_bar_chart

INDIA_GEOJSON_URLS = [
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson",
    "https://raw.githubusercontent.com/plotly/datasets/master/india_states.geojson",
]

STATE_NORMALIZATION = {
    "NCT OF DELHI": "DELHI",
    "DELHI": "DELHI",
    "J&K": "JAMMU AND KASHMIR",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "JAMMU AND KASHMIR": "JAMMU AND KASHMIR",
    "ODISHA": "ODISHA",
    "ORISSA": "ODISHA",
    "TELANGANA": "TELANGANA",
    "ANDHRA PRADESH": "ANDHRA PRADESH",
    "TAMIL NADU": "TAMIL NADU",
    "UTTAR PRADESH": "UTTAR PRADESH",
    "MADHYA PRADESH": "MADHYA PRADESH",
    "WEST BENGAL": "WEST BENGAL",
    "MAHARASHTRA": "MAHARASHTRA",
    "RAJASTHAN": "RAJASTHAN",
    "KARNATAKA": "KARNATAKA",
    "GUJARAT": "GUJARAT",
    "HARYANA": "HARYANA",
    "PUNJAB": "PUNJAB",
    "BIHAR": "BIHAR",
    "JHARKHAND": "JHARKHAND",
    "ASSAM": "ASSAM",
    "CHHATTISGARH": "CHHATTISGARH",
    "KERALA": "KERALA",
    "HIMACHAL PRADESH": "HIMACHAL PRADESH",
    "LADAKH": "LADAKH",
}


def normalize_state_name(value: str) -> str:
    """Normalize state names for map joins."""
    value = "" if pd.isna(value) else str(value).strip().upper()
    return STATE_NORMALIZATION.get(value, value)


@st.cache_data(show_spinner=False)
def fetch_india_geojson():
    """Fetch India state GeoJSON from public open-source repositories."""
    last_error = None
    for url in INDIA_GEOJSON_URLS:
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not fetch India GeoJSON. Last error: {last_error}")


def _extract_feature_name_key(geojson: dict):
    """Find likely state-name property key in GeoJSON features."""
    candidates = ["NAME_1", "ST_NM", "state", "name", "NAME", "State_Name", "state_name"]
    features = geojson.get("features", [])
    if not features:
        return None
    props = features[0].get("properties", {})
    for key in candidates:
        if key in props:
            return key
    return next(iter(props.keys()), None) if props else None


def render_india_state_map(state_summary: pd.DataFrame):
    """Render state-wise house visits as India spatial analysis."""
    st.subheader("Spatial Data Analysis")
    st.caption("State-wise clean unique house visits. The map uses public India GeoJSON when available; otherwise a fallback chart is shown.")

    if state_summary.empty:
        st.info("No state-wise data available for spatial analysis.")
        return

    map_df = state_summary.copy()
    map_df["STATE_MAP"] = map_df["STATE"].apply(normalize_state_name)

    try:
        geojson = fetch_india_geojson()
        name_key = _extract_feature_name_key(geojson)
        if not name_key:
            raise RuntimeError("GeoJSON state name key not found.")

        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            props["STATE_MAP"] = normalize_state_name(props.get(name_key, ""))

        fig = px.choropleth(
            map_df,
            geojson=geojson,
            locations="STATE_MAP",
            featureidkey="properties.STATE_MAP",
            color="House Visits",
            hover_name="STATE",
            hover_data={"House Visits": ":,", "STATE_MAP": False},
            title="India map: State-wise house visits",
            color_continuous_scale="Blues",
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=650, margin=dict(l=0, r=0, t=60, b=0), title_x=0.02, paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning("Map layer could not be loaded in this environment. Showing state-wise fallback chart instead.")
        st.caption(str(exc))
        render_labeled_bar_chart(map_df, "STATE", "House Visits", "State-wise house visits", orientation="h")

    st.dataframe(state_summary, use_container_width=True, hide_index=True)
