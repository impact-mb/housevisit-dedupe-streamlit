"""
Module Name : charts.py

Purpose:
--------
Plotly-only chart helpers for House Visit DQI. No Matplotlib is used.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_labeled_bar_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str, orientation: str = "v"):
    """Render a Plotly bar chart with labels outside bars."""
    if data.empty:
        st.info(f"No data available for {title}.")
        return

    if orientation == "h":
        plot_df = data.sort_values(y_col, ascending=True)
        fig = px.bar(plot_df, x=y_col, y=x_col, orientation="h", text=y_col, title=title)
        fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis_title="", xaxis_title="House visits", height=max(420, 32 * len(plot_df)))
        max_value = plot_df[y_col].max() if not plot_df.empty else 0
        fig.update_xaxes(range=[0, max_value * 1.18 if max_value else 1])
    else:
        fig = px.bar(data, x=x_col, y=y_col, text=y_col, title=title)
        fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="House visits", height=460)
        max_value = data[y_col].max() if not data.empty else 0
        fig.update_yaxes(range=[0, max_value * 1.18 if max_value else 1])

    fig.update_layout(
        margin=dict(l=20, r=70, t=65, b=40),
        title_x=0.02,
        uniformtext_minsize=10,
        uniformtext_mode="show",
        bargap=0.22,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_labeled_pie_chart(data: pd.DataFrame, name_col: str, value_col: str, title: str):
    """Render a Plotly pie chart with labels and percentages outside slices."""
    if data.empty:
        st.info(f"No data available for {title}.")
        return

    fig = px.pie(data, names=name_col, values=value_col, title=title, hole=0.35)
    fig.update_traces(
        textposition="outside",
        textinfo="label+percent+value",
        hovertemplate="%{label}<br>House visits: %{value:,}<br>Share: %{percent}<extra></extra>",
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=65, b=20),
        title_x=0.02,
        height=520,
        showlegend=True,
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_chart_box(title: str, description: str, chart_type: str, data: pd.DataFrame, x_col: str, y_col: str, orientation: str = "h"):
    """Render one chart inside a bordered visual card."""
    with st.container(border=True):
        st.markdown(f"#### {title}")
        if description:
            st.caption(description)
        if chart_type == "pie":
            render_labeled_pie_chart(data, x_col, y_col, title)
        else:
            render_labeled_bar_chart(data, x_col, y_col, title, orientation=orientation)
