# Optimization > Databases (RDS, DynamoDB) tab
from __future__ import annotations

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


_REQUIRED_DB_COLS = ["resource_id", "service", "instance_type", "region", "monthly_cost_usd", "recommendation", "potential_savings_usd"]


def render_databases_tab() -> None:
    db_df = st.session_state.get("databases_df", pd.DataFrame())
    data_source = st.session_state.get("data_source", "none")
    if db_df is None or db_df.empty:
        if data_source == "synthetic":
            st.info("Database data not loaded. Reload synthetic data from **Your waste**.")
        else:
            st.info("**Database** (RDS, DynamoDB) recommendations to lower waste require Cost Explorer or CUR data. Load **synthetic data** from Your waste to explore this tab.")
        return
    missing = [c for c in _REQUIRED_DB_COLS if c not in db_df.columns]
    if missing:
        st.warning(f"Database data is missing columns: {', '.join(missing)}. Reload synthetic data from **Your waste** or use a compatible source.")
        return
    st.markdown("#### Filters")
    regions = sorted(db_df["region"].dropna().unique().tolist())
    services = sorted(db_df["service"].dropna().unique().tolist())
    col1, col2 = st.columns(2)
    with col1:
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="db_tab_regions")
    with col2:
        selected_services = st.multiselect("Service", options=services, default=services, key="db_tab_service")
    filtered = db_df[db_df["region"].isin(selected_regions) & db_df["service"].isin(selected_services)]
    if filtered.empty:
        st.warning("No databases match your filters.")
        return
    action_count = int((filtered["potential_savings_usd"] > 0).sum())
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        render_sec_card("Monthly spend", format_usd(filtered["monthly_cost_usd"].sum()), "RDS and DynamoDB cost.")
    with kpi_col2:
        render_sec_card("Waste", format_usd(filtered["potential_savings_usd"].sum()), "From instance or mode changes.")
    with kpi_col3:
        render_sec_card("Recommendations", action_count, "Databases with recommendations to lower it.")
    st.markdown("#### RDS & DynamoDB")
    display_df = filtered[["resource_id", "service", "instance_type", "region", "monthly_cost_usd", "recommendation", "potential_savings_usd"]].copy()
    display_df.columns = ["Resource ID", "Service", "Instance / mode", "Region", "Monthly cost", "Recommendation", "Waste"]
    display_df["Monthly cost"] = display_df["Monthly cost"].apply(lambda x: format_usd(x))
    display_df["Waste"] = display_df["Waste"].apply(lambda x: format_usd(x))
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    if data_source == "synthetic":
        st.caption("Synthetic data. Real database recommendations to lower waste require Cost Explorer, CUR, or RDS/DynamoDB APIs.")
