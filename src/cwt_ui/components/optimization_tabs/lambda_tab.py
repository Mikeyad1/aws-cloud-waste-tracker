# Optimization > Serverless (Lambda) tab
from __future__ import annotations

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


def render_lambda_tab() -> None:
    lambda_df = st.session_state.get("lambda_df", pd.DataFrame())
    if lambda_df is None or lambda_df.empty:
        st.info("Run a scan from **Setup** or load **synthetic data** from Your waste to load Lambda function data.")
        return
    st.markdown("#### Filters")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        regions = sorted(lambda_df["region"].dropna().unique().tolist())
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="lambda_tab_regions")
    with col2:
        runtimes = sorted(lambda_df["runtime"].dropna().unique().tolist())
        selected_runtimes = st.multiselect("Runtime", options=runtimes, default=runtimes, key="lambda_tab_runtimes")
    with col3:
        search_query = st.text_input("Search", value="", max_chars=60, key="lambda_tab_search")
    filtered = lambda_df.copy()
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_runtimes:
        filtered = filtered[filtered["runtime"].isin(selected_runtimes)]
    if search_query:
        q = search_query.lower()
        filtered = filtered[filtered["function_name"].str.lower().str.contains(q, na=False)]
    if filtered.empty:
        st.warning("No Lambda functions match your current filters.")
        return
    total_functions = len(filtered)
    monthly_spend = filtered["monthly_cost_usd"].sum() if "monthly_cost_usd" in filtered.columns else 0.0
    if "billing_type" in filtered.columns and filtered["billing_type"].notna().any():
        covered = filtered["billing_type"].str.contains("SP", case=False, na=False)
        coverage_pct = (covered.sum() / total_functions) * 100 if total_functions else 0.0
    else:
        coverage_pct = 0.0
    potential_savings = filtered["potential_savings_usd"].sum() if "potential_savings_usd" in filtered.columns else 0.0
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        render_sec_card("Total Functions", f"{total_functions:,}", "Lambda functions after filters.")
    with kpi_col2:
        render_sec_card("Regions", filtered["region"].nunique(), "Regions with functions.")
    with kpi_col3:
        render_sec_card("Monthly Spend", format_usd(monthly_spend), "Approximate monthly cost.")
    with kpi_col4:
        render_sec_card("% Covered by SP", f"{coverage_pct:.1f}%", "Compute SP covers Lambda.")
    with kpi_col5:
        render_sec_card("Waste", format_usd(potential_savings), "From recommendations to lower it.")
    st.markdown("#### Lambda Functions Inventory")
    base_cols = ["function_name", "region", "runtime", "memory_size_mb", "timeout_seconds", "last_modified"]
    extra_cols = [c for c in ["monthly_cost_usd", "billing_type", "recommendation", "potential_savings_usd"] if c in filtered.columns]
    table_df = filtered[base_cols + extra_cols].copy()
    table_df.columns = ["Function Name", "Region", "Runtime", "Memory Size (MB)", "Timeout (seconds)", "Last Modified"] + (
        ["Monthly Cost ($)", "Billing Type", "Recommendation", "Waste ($)"] if extra_cols else []
    )
    if "Last Modified" in table_df.columns:
        table_df["Last Modified"] = pd.to_datetime(table_df["Last Modified"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        table_df["Last Modified"] = table_df["Last Modified"].fillna("—")
    col_config = {}
    if "Monthly Cost ($)" in table_df.columns:
        col_config["Monthly Cost ($)"] = st.column_config.NumberColumn("Monthly Cost ($)", format="$%.2f")
    if "Waste ($)" in table_df.columns:
        col_config["Waste ($)"] = st.column_config.NumberColumn("Waste ($)", format="$%.2f")
    st.dataframe(table_df, use_container_width=True, hide_index=True, column_config=col_config or None)
