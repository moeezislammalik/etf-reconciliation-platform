"""Reusable chart components for Streamlit dashboard."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from dashboard.utils.data_access import COLORS, PLOTLY_TEMPLATE


def kpi_card(label: str, value: str, delta: str | None = None, delta_color: str = "normal") -> None:
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def line_chart(df: pd.DataFrame, x: str, y: str | list, title: str, color: str | None = None) -> None:
    if df.empty:
        st.info("No data available")
        return
    if isinstance(y, list):
        fig = px.line(df, x=x, y=y, title=title, template=PLOTLY_TEMPLATE)
    elif color:
        fig = px.line(df, x=x, y=y, color=color, title=title, template=PLOTLY_TEMPLATE)
    else:
        fig = px.line(df, x=x, y=y, title=title, template=PLOTLY_TEMPLATE)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None) -> None:
    if df.empty:
        st.info("No data available")
        return
    fig = px.bar(df, x=x, y=y, color=color, title=title, template=PLOTLY_TEMPLATE,
                 color_discrete_sequence=COLORS["chart_palette"])
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str) -> None:
    if df.empty:
        st.info("No data available")
        return
    fig = px.pie(df, names=names, values=values, title=title, template=PLOTLY_TEMPLATE,
                 color_discrete_sequence=COLORS["chart_palette"])
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)


def treemap_chart(df: pd.DataFrame, path: list, values: str, title: str) -> None:
    if df.empty:
        st.info("No data available")
        return
    fig = px.treemap(df, path=path, values=values, title=title, template=PLOTLY_TEMPLATE,
                     color_discrete_sequence=COLORS["chart_palette"])
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=450)
    st.plotly_chart(fig, use_container_width=True)


def heatmap_chart(df: pd.DataFrame, x: str, y: str, z: str, title: str) -> None:
    if df.empty:
        st.info("No data available")
        return
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale="RdYlGn_r", template=PLOTLY_TEMPLATE,
    ))
    fig.update_layout(title=title, margin=dict(l=20, r=20, t=40, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)


def candlestick_chart(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        st.info("No data available")
        return
    fig = go.Figure(data=[go.Candlestick(
        x=df["price_date"], open=df["open_price"], high=df["high_price"],
        low=df["low_price"], close=df["close_price"],
    )])
    fig.update_layout(title=title, template=PLOTLY_TEMPLATE,
                      margin=dict(l=20, r=20, t=40, b=20), height=450)
    st.plotly_chart(fig, use_container_width=True)


def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None, size: str | None = None) -> None:
    if df.empty:
        st.info("No data available")
        return
    fig = px.scatter(df, x=x, y=y, color=color, size=size, title=title, template=PLOTLY_TEMPLATE)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)
