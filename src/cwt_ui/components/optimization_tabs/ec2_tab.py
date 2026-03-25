# Optimization > Compute (EC2) tab
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from cwt_ui.components.ui.overview_cards import render_sec_card
from cwt_ui.utils.money import format_usd


def _safe_column(df: pd.DataFrame, names: list[str], default=None):
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(default, index=df.index)


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["instance_id"] = _safe_column(out, ["instance_id", "InstanceId"], "unknown")
    out["region"] = _safe_column(out, ["region", "Region"], "unknown")
    out["name"] = _safe_column(out, ["name", "Name", "tag_Name"], "").fillna("")
    out["monthly_cost_usd"] = (
        pd.to_numeric(_safe_column(out, ["monthly_cost_usd", "Monthly Cost (USD)"], 0.0), errors="coerce").fillna(0.0)
    )
    out["avg_cpu_7d"] = (
        pd.to_numeric(_safe_column(out, ["avg_cpu_7d", "CPU Utilization (%)"], np.nan), errors="coerce").clip(
            lower=0, upper=100
        )
    )
    out["state"] = _safe_column(out, ["state", "State"], "unknown").str.title()
    out["billing_type"] = (
        _safe_column(out, ["billing_type", "Billing Type"], "On-Demand")
        .fillna("On-Demand")
        .replace({"sp": "SP-Covered", "Savings Plans": "SP-Covered"})
    )
    department_columns = [col for col in out.columns if "department" in col.lower()]
    if department_columns:
        out["department"] = out[department_columns[0]].fillna("Unassigned")
    elif "tags" in out.columns and out["tags"].notna().any():
        out["department"] = out["tags"].apply(
            lambda tags: tags.get("department", "Unassigned") if isinstance(tags, dict) else "Unassigned"
        )
    else:
        out["department"] = "Unassigned"
    if "idle_score" in out.columns:
        out["idle_score"] = pd.to_numeric(out["idle_score"], errors="coerce").fillna(0.0)
    else:
        out["idle_score"] = (1 - (out["avg_cpu_7d"] / 100.0)).clip(lower=0, upper=1) * 100
    if "potential_savings_usd" not in out.columns:
        out["potential_savings_usd"] = out["monthly_cost_usd"] * (out["idle_score"] / 100.0)
    if "scanned_at" in out.columns:
        out["scanned_at_ts"] = pd.to_datetime(out["scanned_at"], errors="coerce")
    else:
        out["scanned_at_ts"] = pd.NaT
    out["recommendation"] = _safe_column(out, ["recommendation", "Recommendation"], "Review instance sizing").fillna(
        "Review instance sizing"
    )
    return out


def render_ec2_tab() -> None:
    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    if ec2_df is None or ec2_df.empty:
        st.info("Run a scan from **Setup** to populate EC2 instance data.")
        return
    ec2_df = _ensure_columns(ec2_df)

    regions = sorted(ec2_df["region"].dropna().unique().tolist())
    departments = sorted(ec2_df["department"].dropna().unique().tolist())
    st.markdown("#### Filters")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        selected_regions = st.multiselect("Region", options=regions, default=regions, key="ec2_tab_regions")
    with col2:
        selected_departments = st.multiselect("Department", options=departments, default=departments, key="ec2_tab_dept")
    with col3:
        idle_only = st.toggle("Show only idle instances", key="ec2_tab_idle")
    search_query = st.text_input("Search", value="", max_chars=60, key="ec2_tab_search")
    date_range = None
    if ec2_df["scanned_at_ts"].notna().any():
        min_date = ec2_df["scanned_at_ts"].min().date()
        max_date = ec2_df["scanned_at_ts"].max().date()
        default_start = max(min_date, max_date - timedelta(days=30))
        default_end = max_date
        if min_date == max_date:
            date_range = st.date_input(
                "Scan date", value=max_date, min_value=min_date, max_value=max_date, key="ec2_tab_dates"
            )
            date_range = (date_range, date_range) if date_range else None
        else:
            date_range = st.date_input(
                "Scan date range", value=(default_start, default_end), min_value=min_date, max_value=max_date, key="ec2_tab_dates"
            )
    filtered = ec2_df.copy()
    if selected_regions:
        filtered = filtered[filtered["region"].isin(selected_regions)]
    if selected_departments:
        filtered = filtered[filtered["department"].isin(selected_departments)]
    if idle_only:
        filtered = filtered[filtered["idle_score"] >= 70]
    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered["instance_id"].str.lower().str.contains(q) | filtered["name"].str.lower().str.contains(q)
        ]
    if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        if isinstance(start_date, date) and isinstance(end_date, date):
            mask = (
                filtered["scanned_at_ts"].notna()
                & (filtered["scanned_at_ts"].dt.date >= start_date)
                & (filtered["scanned_at_ts"].dt.date <= end_date)
            )
            filtered = filtered[mask]
    if filtered.empty:
        st.warning("No EC2 instances match your current filters.")
        return
    total_instances = len(filtered)
    monthly_spend = filtered["monthly_cost_usd"].sum()
    if filtered["billing_type"].notna().any():
        covered = filtered["billing_type"].str.contains("SP", case=False, na=False)
        coverage_pct = (covered.sum() / total_instances) * 100 if total_instances else 0.0
    else:
        coverage_pct = 0.0
    idle_cost = filtered.loc[filtered["idle_score"] >= 70, "monthly_cost_usd"].sum()
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        render_sec_card("Total EC2 Instances", f"{total_instances:,}", "Number of EC2 instances after filters.")
    with kpi_cols[1]:
        render_sec_card("Monthly EC2 Spend", format_usd(monthly_spend), "Approximate monthly cost.")
    with kpi_cols[2]:
        render_sec_card("% Covered by Savings Plans", f"{coverage_pct:.1f}%", "SP coverage.")
    with kpi_cols[3]:
        render_sec_card("Estimated Idle/Waste Cost", format_usd(idle_cost), "Monthly cost from highly idle.")
    table = pd.DataFrame(
        {
            "Instance ID": filtered["instance_id"],
            "Region": filtered["region"],
            "Name/Tag": filtered["name"].replace("", "—"),
            "Monthly Cost ($)": filtered["monthly_cost_usd"],
            "State": filtered["state"],
            "CPU Utilization (%)": filtered["avg_cpu_7d"].fillna(0.0),
            "Idle Score": filtered["idle_score"].round(1),
            "Billing Type": filtered["billing_type"],
            "Recommendation": filtered["recommendation"],
            "Waste ($)": filtered["potential_savings_usd"],
        }
    )
    def badge(row):
        if row["Idle Score"] >= 85:
            return "🔴 High Idle"
        if row["Recommendation"] and "rightsize" in str(row["Recommendation"]).lower():
            return "🟠 Rightsize"
        return ""
    table["Issue Badge"] = table.apply(badge, axis=1)
    st.markdown("#### EC2 Inventory")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monthly Cost ($)": st.column_config.NumberColumn("Monthly Cost ($)", format="$%.2f"),
            "CPU Utilization (%)": st.column_config.ProgressColumn("CPU %", min_value=0, max_value=100, format="%.1f%%"),
            "Idle Score": st.column_config.ProgressColumn("Idle Score", min_value=0, max_value=100, format="%.1f"),
            "Waste ($)": st.column_config.NumberColumn("Waste ($)", format="$%.2f"),
        },
    )
