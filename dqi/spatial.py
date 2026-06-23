"""
Module Name : spatial.py

Purpose:
--------
Spatial Data Analysis for House Visit DQI.

This module renders a dynamic full India state/UT map:
- Full India map is visible by default.
- All states/UTs are shown.
- States/UTs with house visit data are highlighted by value.
- States/UTs without data remain grey.
- State labels are displayed on the map.
- A state-wise table is shown beside/below the map.

Owner:
------
Magic Bus Data Team

Version:
--------
1.1.0
"""

from __future__ import annotations

import json
import urllib.request
from typing import Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .charts import render_labeled_bar_chart


# Public open-source GeoJSON sources. Streamlit Cloud normally has internet access.
# If all sources fail, the module falls back to a labelled centroid map + bar chart.
INDIA_GEOJSON_URLS = [
    "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson",
    "https://raw.githubusercontent.com/plotly/datasets/master/india_states.geojson",
]


# Full India state/UT reference list for reporting and map completion.
# This helps the dashboard show the full India footprint even when a state has no data.
ALL_INDIA_STATES_UTS = [
    "ANDAMAN AND NICOBAR ISLANDS",
    "ANDHRA PRADESH",
    "ARUNACHAL PRADESH",
    "ASSAM",
    "BIHAR",
    "CHANDIGARH",
    "CHHATTISGARH",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DELHI",
    "GOA",
    "GUJARAT",
    "HARYANA",
    "HIMACHAL PRADESH",
    "JAMMU AND KASHMIR",
    "JHARKHAND",
    "KARNATAKA",
    "KERALA",
    "LADAKH",
    "LAKSHADWEEP",
    "MADHYA PRADESH",
    "MAHARASHTRA",
    "MANIPUR",
    "MEGHALAYA",
    "MIZORAM",
    "NAGALAND",
    "ODISHA",
    "PUDUCHERRY",
    "PUNJAB",
    "RAJASTHAN",
    "SIKKIM",
    "TAMIL NADU",
    "TELANGANA",
    "TRIPURA",
    "UTTAR PRADESH",
    "UTTARAKHAND",
    "WEST BENGAL",
]


# Approximate label coordinates for Indian states/UTs.
# Used for state names and counts on the map.
STATE_LABEL_COORDS: Dict[str, tuple[float, float]] = {
    "ANDAMAN AND NICOBAR ISLANDS": (11.7401, 92.6586),
    "ANDHRA PRADESH": (15.9129, 79.7400),
    "ARUNACHAL PRADESH": (28.2180, 94.7278),
    "ASSAM": (26.2006, 92.9376),
    "BIHAR": (25.0961, 85.3131),
    "CHANDIGARH": (30.7333, 76.7794),
    "CHHATTISGARH": (21.2787, 81.8661),
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": (20.3974, 72.8328),
    "DELHI": (28.7041, 77.1025),
    "GOA": (15.2993, 74.1240),
    "GUJARAT": (22.2587, 71.1924),
    "HARYANA": (29.0588, 76.0856),
    "HIMACHAL PRADESH": (31.1048, 77.1734),
    "JAMMU AND KASHMIR": (33.7782, 76.5762),
    "JHARKHAND": (23.6102, 85.2799),
    "KARNATAKA": (15.3173, 75.7139),
    "KERALA": (10.8505, 76.2711),
    "LADAKH": (34.1526, 77.5771),
    "LAKSHADWEEP": (10.5667, 72.6417),
    "MADHYA PRADESH": (22.9734, 78.6569),
    "MAHARASHTRA": (19.7515, 75.7139),
    "MANIPUR": (24.6637, 93.9063),
    "MEGHALAYA": (25.4670, 91.3662),
    "MIZORAM": (23.1645, 92.9376),
    "NAGALAND": (26.1584, 94.5624),
    "ODISHA": (20.9517, 85.0985),
    "PUDUCHERRY": (11.9416, 79.8083),
    "PUNJAB": (31.1471, 75.3412),
    "RAJASTHAN": (27.0238, 74.2179),
    "SIKKIM": (27.5330, 88.5122),
    "TAMIL NADU": (11.1271, 78.6569),
    "TELANGANA": (18.1124, 79.0193),
    "TRIPURA": (23.9408, 91.9882),
    "UTTAR PRADESH": (26.8467, 80.9462),
    "UTTARAKHAND": (30.0668, 79.0193),
    "WEST BENGAL": (22.9868, 87.8550),
}


STATE_NORMALIZATION = {
    "NCT OF DELHI": "DELHI",
    "NATIONAL CAPITAL TERRITORY OF DELHI": "DELHI",
    "DELHI": "DELHI",
    "J&K": "JAMMU AND KASHMIR",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "JAMMU AND KASHMIR": "JAMMU AND KASHMIR",
    "JAMMU AND KASHMIR STATE": "JAMMU AND KASHMIR",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "ANDAMAN & NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "PONDICHERRY": "PUDUCHERRY",
    "PUDUCHERRY": "PUDUCHERRY",
    "ORISSA": "ODISHA",
    "ODISHA": "ODISHA",
    "UTTARANCHAL": "UTTARAKHAND",
    "UTTARAKHAND": "UTTARAKHAND",
    "TELANGANA": "TELANGANA",
    "LADAKH": "LADAKH",
}


def normalize_state_name(value: str) -> str:
    """Normalize state/UT names for map joins and table consistency."""
    value = "" if pd.isna(value) else str(value).strip().upper()
    value = " ".join(value.replace(".", "").replace("-", " ").split())
    return STATE_NORMALIZATION.get(value, value)


def title_state_name(value: str) -> str:
    """Convert normalized uppercase state names to readable title case."""
    special = {
        "DELHI": "Delhi",
        "ODISHA": "Odisha",
        "TELANGANA": "Telangana",
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "Dadra & Nagar Haveli and Daman & Diu",
        "ANDAMAN AND NICOBAR ISLANDS": "Andaman & Nicobar Islands",
    }
    return special.get(value, value.title())


@st.cache_data(show_spinner=False)
def fetch_india_geojson() -> dict:
    """Fetch India state GeoJSON from public open-source repositories."""
    last_error: Optional[Exception] = None
    for url in INDIA_GEOJSON_URLS:
        try:
            with urllib.request.urlopen(url, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - depends on deployment network
            last_error = exc
    raise RuntimeError(f"Could not fetch India GeoJSON. Last error: {last_error}")


def _extract_feature_name_key(geojson: dict) -> Optional[str]:
    """Find likely state-name property key in GeoJSON features."""
    candidates = ["NAME_1", "ST_NM", "st_nm", "state", "name", "NAME", "State_Name", "state_name"]
    features = geojson.get("features", [])
    if not features:
        return None
    props = features[0].get("properties", {})
    for key in candidates:
        if key in props:
            return key
    return next(iter(props.keys()), None) if props else None


def _prepare_geojson(geojson: dict) -> tuple[dict, list[str]]:
    """Normalize GeoJSON feature names and return available state names."""
    name_key = _extract_feature_name_key(geojson)
    if not name_key:
        raise RuntimeError("GeoJSON state name key not found.")

    geo_states = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        state_norm = normalize_state_name(props.get(name_key, ""))
        props["STATE_MAP"] = state_norm
        props["STATE_LABEL"] = title_state_name(state_norm)
        geo_states.append(state_norm)

    return geojson, sorted(set([s for s in geo_states if s]))


def build_full_state_dataset(state_summary: pd.DataFrame, geo_states: Optional[list[str]] = None) -> pd.DataFrame:
    """
    Build a complete India state/UT dataset.

    States with no house visit data are retained with House Visits = 0.
    This enables the dashboard to show the full India map by default.
    """
    if state_summary.empty:
        data_df = pd.DataFrame(columns=["STATE_MAP", "House Visits"])
    else:
        data_df = state_summary.copy()
        data_df["STATE_MAP"] = data_df["STATE"].apply(normalize_state_name)
        data_df = data_df.groupby("STATE_MAP", as_index=False)["House Visits"].sum()

    universe = sorted(set(ALL_INDIA_STATES_UTS).union(set(geo_states or [])).union(set(data_df.get("STATE_MAP", []))))
    full_df = pd.DataFrame({"STATE_MAP": universe})
    full_df = full_df.merge(data_df, on="STATE_MAP", how="left")
    full_df["House Visits"] = full_df["House Visits"].fillna(0).astype(int)
    full_df["Presence"] = full_df["House Visits"].apply(lambda x: "Present" if x > 0 else "No Data")
    full_df["State / UT"] = full_df["STATE_MAP"].apply(title_state_name)
    full_df["Label"] = full_df.apply(
        lambda r: f"{r['State / UT']}<br>{r['House Visits']:,}" if r["House Visits"] > 0 else r["State / UT"],
        axis=1,
    )
    return full_df.sort_values("House Visits", ascending=False).reset_index(drop=True)


def _state_label_df(full_df: pd.DataFrame) -> pd.DataFrame:
    """Attach approximate latitude/longitude to state labels."""
    coord_df = pd.DataFrame(
        [{"STATE_MAP": k, "lat": v[0], "lon": v[1]} for k, v in STATE_LABEL_COORDS.items()]
    )
    return full_df.merge(coord_df, on="STATE_MAP", how="inner")


def _render_kpi_cards(full_df: pd.DataFrame):
    """Render spatial KPI cards."""
    total_states = len(full_df)
    active_states = int((full_df["House Visits"] > 0).sum())
    total_visits = int(full_df["House Visits"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total States / UTs", f"{total_states:,}")
    k2.metric("States with Data", f"{active_states:,}")
    k3.metric("Total House Visits", f"{total_visits:,}")
    k4.metric("States without Data", f"{total_states - active_states:,}")


def _render_choropleth_map(geojson: dict, full_df: pd.DataFrame):
    """Render full India map, highlighting only states with data."""
    max_value = int(full_df["House Visits"].max()) if not full_df.empty else 0

    colorscale = [
        [0.00, "#e5e7eb"],  # no data / zero
        [0.01, "#fff7bc"],
        [0.25, "#fec44f"],
        [0.50, "#fe9929"],
        [0.75, "#ec7014"],
        [1.00, "#cc4c02"],
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=full_df["STATE_MAP"],
            z=full_df["House Visits"],
            featureidkey="properties.STATE_MAP",
            colorscale=colorscale,
            zmin=0,
            zmax=max(max_value, 1),
            marker_line_color="white",
            marker_line_width=0.8,
            colorbar=dict(title="House Visits", tickformat=","),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "House visits: %{z:,}<br>"
                "Presence: %{customdata[1]}"
                "<extra></extra>"
            ),
            customdata=full_df[["State / UT", "Presence"]],
        )
    )

    labels_df = _state_label_df(full_df)

    # Labels for states with data: state name + value.
    active_labels = labels_df[labels_df["House Visits"] > 0]
    fig.add_trace(
        go.Scattergeo(
            lon=active_labels["lon"],
            lat=active_labels["lat"],
            text=active_labels["Label"],
            mode="text",
            textfont=dict(size=9, color="#111827"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Labels for states without data: state name only, lighter.
    inactive_labels = labels_df[labels_df["House Visits"] == 0]
    fig.add_trace(
        go.Scattergeo(
            lon=inactive_labels["lon"],
            lat=inactive_labels["lat"],
            text=inactive_labels["State / UT"],
            mode="text",
            textfont=dict(size=8, color="#6b7280"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_geos(
        visible=False,
        projection_type="mercator",
        lonaxis_range=[66, 99],
        lataxis_range=[5, 38],
        showcountries=False,
        showcoastlines=False,
        showland=True,
        landcolor="#f8fafc",
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        title="Full India map: States/UTs highlighted where house visit data is present",
        title_x=0.02,
        height=760,
        margin=dict(l=0, r=0, t=55, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_fallback_centroid_map(full_df: pd.DataFrame):
    """Render fallback labelled geo-scatter map when GeoJSON cannot be fetched."""
    labels_df = _state_label_df(full_df)
    fig = go.Figure()

    fig.add_trace(
        go.Scattergeo(
            lon=labels_df["lon"],
            lat=labels_df["lat"],
            text=labels_df["Label"],
            mode="markers+text",
            marker=dict(
                size=labels_df["House Visits"].apply(lambda x: 6 if x == 0 else min(26, 8 + x ** 0.35)),
                color=labels_df["House Visits"],
                colorscale="YlOrRd",
                colorbar=dict(title="House Visits"),
                line=dict(width=0.5, color="white"),
            ),
            textfont=dict(size=9, color="#111827"),
            hovertemplate="<b>%{customdata[0]}</b><br>House visits: %{customdata[1]:,}<extra></extra>",
            customdata=labels_df[["State / UT", "House Visits"]],
            showlegend=False,
        )
    )

    fig.update_geos(
        scope="asia",
        projection_type="mercator",
        lonaxis_range=[66, 99],
        lataxis_range=[5, 38],
        showland=True,
        landcolor="#f3f4f6",
        countrycolor="#d1d5db",
        showcountries=True,
        showcoastlines=True,
        coastlinecolor="#d1d5db",
    )
    fig.update_layout(
        title="India state label map: House visits by State/UT",
        title_x=0.02,
        height=700,
        margin=dict(l=0, r=0, t=55, b=0),
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_india_state_map(state_summary: pd.DataFrame):
    """
    Render full India spatial analysis.

    Input:
    ------
    state_summary: DataFrame with columns STATE and House Visits.

    Output:
    -------
    - Full India map.
    - States with house visit data highlighted by colour intensity.
    - States with no data shown in grey.
    - State labels displayed on map.
    - State-wise data table for export/review.
    """
    st.subheader("Spatial Data Analysis")
    st.caption(
        "Full India map is shown by default. States/UTs with data are highlighted with colour; "
        "states/UTs without data remain grey. Labels show State/UT names and values where data exists."
    )

    try:
        geojson = fetch_india_geojson()
        geojson, geo_states = _prepare_geojson(geojson)
        full_df = build_full_state_dataset(state_summary, geo_states=geo_states)
        _render_kpi_cards(full_df)
        _render_choropleth_map(geojson, full_df)
    except Exception as exc:
        # Full choropleth needs GeoJSON. If internet is restricted, show centroid-based India view and table.
        full_df = build_full_state_dataset(state_summary)
        _render_kpi_cards(full_df)
        st.warning("Full India polygon map could not be loaded in this environment. Showing labelled fallback India map.")
        st.caption(str(exc))
        _render_fallback_centroid_map(full_df)

    active_df = full_df[full_df["House Visits"] > 0].copy()
    inactive_df = full_df[full_df["House Visits"] == 0].copy()

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("### State/UT-wise House Visit Table")
        st.dataframe(
            full_df[["State / UT", "House Visits", "Presence"]].sort_values("House Visits", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        st.markdown("### Active Presence Summary")
        st.write(f"**States/UTs with data:** {len(active_df):,}")
        st.write(f"**States/UTs without data:** {len(inactive_df):,}")
        st.write(f"**Total house visits on map:** {int(full_df['House Visits'].sum()):,}")
        st.info("Use the table to confirm exact state names and house visit totals.")

    st.markdown("### Ranked States/UTs with Data")
    if active_df.empty:
        st.info("No active state/UT data available.")
    else:
        ranked = active_df[["State / UT", "House Visits"]].rename(columns={"State / UT": "STATE"})
        render_labeled_bar_chart(ranked, "STATE", "House Visits", "State/UT-wise house visits where data is present", orientation="h")
