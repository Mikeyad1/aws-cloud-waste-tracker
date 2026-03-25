# Optimization > Containers (Fargate) tab
from __future__ import annotations

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


def render_fargate_tab() -> None:
    fargate_df = st.session_state.get("fargate_df", pd.DataFrame())
    if fargate_df is None or fargate_df.empty:
        st.info("Run a scan from **Setup** or load **synthetic data** from Your waste to load Fargate task data.")
        return
    st.markdown("#### Filters")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        regions = sorted(fargate_df["region"].dropna().unique().tolist())
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="fargate_tab_regions")
    with col2:
        clusters = sorted(fargate_df["cluster_name"].dropna().unique().tolist())
        selected_clusters = st.multiselect("Cluster", options=clusters, default=clusters, key="fargate_tab_clusters")
    with col3:
        statuses = sorted(fargate_df["status"].dropna().unique().tolist())
        selected_statuses = st.multiselect("Status", options=statuses, default=statuses, key="fargate_tab_statuses")
    with col4:
        search_query = st.text_input("Search", value="", max_chars=60, key="fargate_tab_search")
    filtered = fargate_df.copy()
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_clusters:
        filtered = filtered[filtered["cluster_name"].isin(selected_clusters)]
    if selected_statuses:
        filtered = filtered[filtered["status"].isin(selected_statuses)]
    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["service_name"].str.lower().str.contains(q, na=False)
            | filtered["task_definition_family"].str.lower().str.contains(q, na=False)
            | filtered["cluster_name"].str.lower().str.contains(q, na=False)
        ]
    if filtered.empty:
        st.warning("No Fargate tasks match your current filters.")
        return
    total_tasks = len(filtered)
    running_tasks = len(filtered[filtered["status"] == "RUNNING"])
    total_memory_gb = filtered["memory_mb"].sum() / 1024
    monthly_spend = filtered["monthly_cost_usd"].sum() if "monthly_cost_usd" in filtered.columns else 0.0
    if "billing_type" in filtered.columns and filtered["billing_type"].notna().any():
        covered = filtered["billing_type"].str.contains("SP", case=False, na=False)
        coverage_pct = (covered.sum() / total_tasks) * 100 if total_tasks else 0.0
    else:
        coverage_pct = 0.0
    potential_savings = filtered["potential_savings_usd"].sum() if "potential_savings_usd" in filtered.columns else 0.0
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        render_sec_card("Total Tasks", f"{total_tasks:,}", "Fargate tasks after filters.")
    with kpi_col2:
        render_sec_card("Running Tasks", f"{running_tasks:,}", "Currently active tasks.")
    with kpi_col3:
        render_sec_card("Monthly Spend", format_usd(monthly_spend), "Approximate monthly cost.")
    with kpi_col4:
        render_sec_card("% Covered by SP", f"{coverage_pct:.1f}%", "Compute SP covers Fargate.")
    with kpi_col5:
        render_sec_card("Waste", format_usd(potential_savings), "From recommendations to lower it.")
    st.markdown("#### Fargate Tasks Inventory")
    base_cols = ["service_name", "cluster_name", "task_definition_family", "region", "cpu", "memory_mb", "platform_version", "status", "started_at"]
    extra_cols = [c for c in ["monthly_cost_usd", "billing_type", "recommendation", "potential_savings_usd"] if c in filtered.columns]
    table_df = filtered[base_cols + extra_cols].copy()
    table_df.columns = ["Service Name", "Cluster", "Task Definition", "Region", "CPU", "Memory (MB)", "Platform Version", "Status", "Started At"] + (
        ["Monthly Cost ($)", "Billing Type", "Recommendation", "Waste ($)"] if extra_cols else []
    )
    if "Started At" in table_df.columns:
        table_df["Started At"] = pd.to_datetime(table_df["Started At"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        table_df["Started At"] = table_df["Started At"].fillna("—")
    col_config = {}
    if "Monthly Cost ($)" in table_df.columns:
        col_config["Monthly Cost ($)"] = st.column_config.NumberColumn("Monthly Cost ($)", format="$%.2f")
    if "Waste ($)" in table_df.columns:
        col_config["Waste ($)"] = st.column_config.NumberColumn("Waste ($)", format="$%.2f")
    st.dataframe(table_df, use_container_width=True, hide_index=True, column_config=col_config or None)
