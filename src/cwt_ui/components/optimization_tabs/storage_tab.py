# Optimization > Storage (S3) tab
from __future__ import annotations

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


_REQUIRED_STORAGE_COLS = ["bucket_name", "region", "storage_class", "size_gb", "monthly_cost_usd", "recommendation", "potential_savings_usd"]


def render_storage_tab() -> None:
    storage_df = st.session_state.get("storage_df", pd.DataFrame())
    data_source = st.session_state.get("data_source", "none")
    if storage_df is None or storage_df.empty:
        if data_source == "synthetic":
            st.info("Storage data not loaded. Reload synthetic data from **Your waste**.")
        else:
            st.info("**Storage (S3)** recommendations to lower waste require Cost Explorer or CUR data. Load **synthetic data** from Your waste to explore this tab.")
        return
    missing = [c for c in _REQUIRED_STORAGE_COLS if c not in storage_df.columns]
    if missing:
        st.warning(f"Storage data is missing columns: {', '.join(missing)}. Reload synthetic data from **Your waste** or use a compatible source.")
        return
    st.markdown("#### Filters")
    regions = sorted(storage_df["region"].dropna().unique().tolist())
    storage_classes = sorted(storage_df["storage_class"].dropna().unique().tolist())
    col1, col2 = st.columns(2)
    with col1:
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="storage_tab_regions")
    with col2:
        selected_classes = st.multiselect("Storage class", options=storage_classes, default=storage_classes, key="storage_tab_class")
    filtered = storage_df[storage_df["region"].isin(selected_regions) & storage_df["storage_class"].isin(selected_classes)]
    if filtered.empty:
        st.warning("No buckets match your filters.")
        return
    action_count = int((filtered["potential_savings_usd"] > 0).sum())
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        render_sec_card("Monthly spend", format_usd(filtered["monthly_cost_usd"].sum()), "S3 storage cost.")
    with kpi_col2:
        render_sec_card("Waste", format_usd(filtered["potential_savings_usd"].sum()), "From lifecycle or class changes.")
    with kpi_col3:
        render_sec_card("Recommendations", action_count, "Buckets with recommendations to lower it.")
    st.markdown("#### S3 buckets")
    display_df = filtered[["bucket_name", "region", "storage_class", "size_gb", "monthly_cost_usd", "recommendation", "potential_savings_usd"]].copy()
    display_df.columns = ["Bucket", "Region", "Storage class", "Size (GB)", "Monthly cost", "Recommendation", "Waste"]
    display_df["Monthly cost"] = display_df["Monthly cost"].apply(lambda x: format_usd(x))
    display_df["Waste"] = display_df["Waste"].apply(lambda x: format_usd(x))
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    if data_source == "synthetic":
        st.caption("Synthetic data. Real S3 recommendations to lower waste require Cost Explorer or CUR with storage breakdown.")
