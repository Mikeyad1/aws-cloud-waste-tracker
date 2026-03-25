# Optimization > Data Transfer tab
from __future__ import annotations

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


_REQUIRED_DT_COLS = ["region", "transfer_type", "destination", "data_gb", "monthly_cost_usd", "recommendation", "potential_savings_usd"]


def render_data_transfer_tab() -> None:
    dt_df = st.session_state.get("data_transfer_df", pd.DataFrame())
    data_source = st.session_state.get("data_source", "none")
    if dt_df is None or dt_df.empty:
        if data_source == "synthetic":
            st.info("Data transfer data not loaded. Reload synthetic data from **Your waste**.")
        else:
            st.info("**Data Transfer** recommendations to lower waste require Cost Explorer or CUR data. Load **synthetic data** from Your waste to explore this tab.")
        return
    missing = [c for c in _REQUIRED_DT_COLS if c not in dt_df.columns]
    if missing:
        st.warning(f"Data transfer data is missing columns: {', '.join(missing)}. Reload synthetic data from **Your waste** or use a compatible source.")
        return
    st.markdown("#### Filters")
    regions = sorted(dt_df["region"].dropna().unique().tolist())
    transfer_types = sorted(dt_df["transfer_type"].dropna().unique().tolist())
    col1, col2 = st.columns(2)
    with col1:
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="dt_tab_regions")
    with col2:
        selected_types = st.multiselect("Transfer type", options=transfer_types, default=transfer_types, key="dt_tab_type")
    filtered = dt_df[dt_df["region"].isin(selected_regions) & dt_df["transfer_type"].isin(selected_types)]
    if filtered.empty:
        st.warning("No data transfer records match your filters.")
        return
    action_count = int((filtered["potential_savings_usd"] > 0).sum())
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        render_sec_card("Monthly spend", format_usd(filtered["monthly_cost_usd"].sum()), "Data transfer cost.")
    with kpi_col2:
        render_sec_card("Waste", format_usd(filtered["potential_savings_usd"].sum()), "From region or transfer changes.")
    with kpi_col3:
        render_sec_card("Recommendations", action_count, "Records with recommendations to lower it.")
    st.markdown("#### Data transfer")
    display_df = filtered[["region", "transfer_type", "destination", "data_gb", "monthly_cost_usd", "recommendation", "potential_savings_usd"]].copy()
    display_df.columns = ["Region", "Type", "Destination", "Data (GB)", "Monthly cost", "Recommendation", "Waste"]
    display_df["Monthly cost"] = display_df["Monthly cost"].apply(lambda x: format_usd(x))
    display_df["Waste"] = display_df["Waste"].apply(lambda x: format_usd(x))
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    if data_source == "synthetic":
        st.caption("Synthetic data. Real data transfer recommendations to lower waste require Cost Explorer or CUR with data transfer breakdown.")
