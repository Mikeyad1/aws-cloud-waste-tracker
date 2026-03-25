from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Tuple

CURRENT_DIR = Path(__file__).resolve().parent
for candidate in [CURRENT_DIR, *CURRENT_DIR.parents]:
    candidate_src = candidate / "src"
    if candidate_src.exists():
        if str(candidate_src) not in sys.path:
            sys.path.insert(0, str(candidate_src))
        break

import altair as alt
import pandas as pd
import streamlit as st

from cwt_ui.components.kpi_card import render_kpi
from cwt_ui.components.ui.header import render_page_header
from cwt_ui.insights.sp_rules import build_insights
from cwt_ui.utils.money import format_usd

DEFAULT_LOOKBACK_DAYS = 30


@st.cache_data(show_spinner=False)
def compute_forecast_util(util_trend_df: pd.DataFrame) -> float:
    if util_trend_df is None or util_trend_df.empty:
        return 0.0
    tail = util_trend_df["utilization_pct"].tail(7)
    return float(tail.mean()) if not tail.empty else float(util_trend_df["utilization_pct"].mean())


@st.cache_data(show_spinner=False)
def compute_utilization_trend(history_df: pd.DataFrame) -> pd.DataFrame:
    if history_df is None or history_df.empty:
        return pd.DataFrame(columns=["date", "utilization_pct", "used_per_hour", "commitment_per_hour"])

    working = history_df.copy()
    working["date"] = pd.to_datetime(working["date"])
    grouped = (
        working.groupby("date")[["used_per_hour", "commitment_per_hour"]]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    grouped["utilization_pct"] = grouped.apply(
        lambda row: (row["used_per_hour"] / row["commitment_per_hour"]) * 100.0
        if row["commitment_per_hour"]
        else 0.0,
        axis=1,
    )
    return grouped


@st.cache_data(show_spinner=False)
def compute_coverage_trend(history_df: pd.DataFrame) -> pd.DataFrame:
    if history_df is None or history_df.empty:
        return pd.DataFrame(columns=["date", "covered_spend", "ondemand_spend", "coverage_pct"])

    working = history_df.copy()
    working["date"] = pd.to_datetime(working["date"])
    grouped = (
        working.groupby("date")[["covered_spend", "ondemand_spend"]]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    grouped["coverage_pct"] = grouped.apply(
        lambda row: (row["covered_spend"] / (row["covered_spend"] + row["ondemand_spend"])) * 100.0
        if (row["covered_spend"] + row["ondemand_spend"])
        else 0.0,
        axis=1,
    )
    return grouped


def plot_utilization_trend(util_trend_df: pd.DataFrame) -> alt.Chart | None:
    if util_trend_df.empty:
        return None

    data = util_trend_df.copy()
    data["date"] = pd.to_datetime(data["date"])

    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("utilization_pct:Q", title="Utilization %"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("utilization_pct:Q", title="Utilization %", format=".1f"),
                alt.Tooltip("used_per_hour:Q", title="Used ($/hr)", format=".2f"),
                alt.Tooltip("commitment_per_hour:Q", title="Commitment ($/hr)", format=".2f"),
            ],
        )
        .properties(height=280)
    )


def plot_coverage_vs_ondemand(coverage_df: pd.DataFrame) -> alt.Chart | None:
    if coverage_df.empty:
        return None

    data = coverage_df.copy()
    data["date"] = pd.to_datetime(data["date"])
    melted = data.melt(
        id_vars=["date"], value_vars=["covered_spend", "ondemand_spend"], var_name="category", value_name="amount"
    )
    category_names = {
        "covered_spend": "Covered Spend",
        "ondemand_spend": "On-Demand Spend",
    }
    melted["category"] = melted["category"].map(category_names)

    return (
        alt.Chart(melted)
        .mark_area(opacity=0.6)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("amount:Q", title="Spend (USD)"),
            color=alt.Color("category:N", title="Spend Type"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("category:N", title="Type"),
                alt.Tooltip("amount:Q", title="Spend (USD)", format="$.2f"),
            ],
        )
        .properties(height=280)
    )


def render_insights(plans_df: pd.DataFrame, coverage_history_df: pd.DataFrame) -> None:
    insights = build_insights(plans_df, coverage_history_df)
    for insight in insights:
        st.markdown(f"- {insight}")


def create_mock_sp_df() -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    today = pd.Timestamp.utcnow().normalize()
    plans = pd.DataFrame(
        [
            {
                "SP ID": "sp-001",
                "Type": "Compute",
                "Region": "us-east-1",
                "Commitment ($/hr)": 12.0,
                "Actual Usage ($/hr)": 10.4,
                "Utilization %": 86.7,
                "Coverage %": 78.2,
                "Forecast Utilization %": 88.0,
                "Unused Commitment ($/hr)": 1.6,
                "Expiration Date": (today + timedelta(days=180)).date().isoformat(),
                "Savings Plan Arn": "arn:aws:savingsplans:demo:1",
            },
            {
                "SP ID": "sp-002",
                "Type": "EC2 Instance",
                "Region": "us-west-2",
                "Commitment ($/hr)": 8.0,
                "Actual Usage ($/hr)": 5.8,
                "Utilization %": 72.5,
                "Coverage %": 64.3,
                "Forecast Utilization %": 74.1,
                "Unused Commitment ($/hr)": 2.2,
                "Expiration Date": (today + timedelta(days=300)).date().isoformat(),
                "Savings Plan Arn": "arn:aws:savingsplans:demo:2",
            },
            {
                "SP ID": "sp-003",
                "Type": "Compute",
                "Region": "Multi-region",
                "Commitment ($/hr)": 6.0,
                "Actual Usage ($/hr)": 6.0,
                "Utilization %": 100.0,
                "Coverage %": 92.0,
                "Forecast Utilization %": 99.0,
                "Unused Commitment ($/hr)": 0.0,
                "Expiration Date": (today + timedelta(days=90)).date().isoformat(),
                "Savings Plan Arn": "arn:aws:savingsplans:demo:3",
            },
        ]
    )

    summary = {
        "overall_utilization_pct": 85.9,
        "total_commitment_per_hour": 26.0,
        "total_used_per_hour": 22.2,
        "unused_commitment_per_hour": 3.8,
        "forecast_utilization_pct": 87.3,
    }

    util_history = []
    coverage_history = []
    for i in range(30):
        day = today - timedelta(days=29 - i)
        util_history.append(
            {
                "date": day.date().isoformat(),
                "savings_plan_arn": "arn:aws:savingsplans:demo:1",
                "utilization_pct": 85 + i * 0.1,
                "used_per_hour": 10 + i * 0.05,
                "commitment_per_hour": 12.0,
            }
        )
        util_history.append(
            {
                "date": day.date().isoformat(),
                "savings_plan_arn": "arn:aws:savingsplans:demo:2",
                "utilization_pct": 70 + i * 0.2,
                "used_per_hour": 5.5 + i * 0.03,
                "commitment_per_hour": 8.0,
            }
        )
        coverage_history.append(
            {
                "date": day.date().isoformat(),
                "savings_plan_arn": "arn:aws:savingsplans:demo:1",
                "coverage_pct": 80 + i * 0.1,
                "covered_spend": 10 + i * 0.05,
                "ondemand_spend": 2.0,
            }
        )
        coverage_history.append(
            {
                "date": day.date().isoformat(),
                "savings_plan_arn": "arn:aws:savingsplans:demo:2",
                "coverage_pct": 65 + i * 0.15,
                "covered_spend": 5.5 + i * 0.04,
                "ondemand_spend": 2.5 + (i % 3),
            }
        )

    util_history_df = pd.DataFrame(util_history)
    coverage_history_df = pd.DataFrame(coverage_history)
    return plans, summary, util_history_df, coverage_history_df


def _generate_mock_data() -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Backward-compatible alias."""
    return create_mock_sp_df()


def load_savings_plan_data() -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame, bool]:
    demo_mode = os.getenv("CWT_DEMO_MODE", "false").strip().lower() == "true"
    if demo_mode:
        plans, summary, util_history, coverage_history = create_mock_sp_df()
        return plans, summary, util_history, coverage_history, True

    plans_df = st.session_state.get("SP_DF")
    summary = st.session_state.get("SP_SUMMARY")
    if summary is None or not isinstance(summary, dict):
        summary = {}
    util_history_df = st.session_state.get("SP_UTIL_TREND")
    if util_history_df is None or not isinstance(util_history_df, pd.DataFrame):
        util_history_df = pd.DataFrame()
    coverage_history_df = st.session_state.get("SP_COVERAGE_TREND")
    if coverage_history_df is None or not isinstance(coverage_history_df, pd.DataFrame):
        coverage_history_df = pd.DataFrame()

    if plans_df is None or not isinstance(plans_df, pd.DataFrame):
        plans_df = pd.DataFrame()
    elif not plans_df.empty:
        # Require columns expected by this page (synthetic and live scan both provide these)
        required = ["Region", "Type", "Commitment ($/hr)", "Actual Usage ($/hr)", "Unused Commitment ($/hr)"]
        if not all(c in plans_df.columns for c in required):
            plans_df = pd.DataFrame()

    return plans_df.copy(), summary, util_history_df.copy(), coverage_history_df.copy(), False


# Page layout (skip when embedded in Optimization > Commitment tab)
if not os.environ.get("CWT_AS_TAB"):
    st.set_page_config(page_title="Savings Plans", page_icon="💰", layout="wide")
    render_page_header(
        title="Savings Plans",
        subtitle="Track spend coverage, utilization trends, and optimization opportunities for AWS Savings Plans.",
        icon="💰",
    )

plans_df, summary, util_history_df, coverage_history_df, is_demo = load_savings_plan_data()

if plans_df.empty:
    secrets_env = ""
    try:
        secrets_env = st.secrets.get("env", "")
    except Exception:
        secrets_env = ""
    is_dev_env = (
        os.getenv("CWT_ENV", "").strip().lower() == "development"
        or os.getenv("APP_ENV", "").strip().lower() == "development"
        or secrets_env.strip().lower() == "dev"
    )
    if is_dev_env:
        st.info("No Savings Plans detected. Click below to load demo data.")
        if st.button("Load Demo Data", type="primary"):
            plans, summary, util_history, coverage_history = create_mock_sp_df()
            st.session_state["SP_DF"] = plans
            st.session_state["SP_SUMMARY"] = summary
            st.session_state["SP_UTIL_TREND"] = util_history
            st.session_state["SP_COVERAGE_TREND"] = coverage_history
            st.session_state["SP_DF_DAILY"] = util_history
            st.rerun()
    else:
        st.info("Run a scan from the AWS Setup page to load Savings Plan data (global or regional).")
    st.stop()

if summary.get("warning"):
    st.warning(summary["warning"])

with st.expander("What do these metrics mean?", expanded=False):
    st.markdown(
        "- **Utilization %** measures how much of your committed Savings Plan spend you actually used.\n"
        "- **Coverage %** indicates the portion of total compute spend covered by Savings Plans versus on-demand."
    )

# Filters
available_regions = sorted(plans_df["Region"].dropna().unique().tolist())
available_types = sorted(plans_df["Type"].dropna().unique().tolist())

filter_cols = st.columns(3)
with filter_cols[0]:
    selected_regions = st.multiselect(
        "Region",
        options=available_regions,
        default=available_regions,
    )
with filter_cols[1]:
    selected_types = st.multiselect(
        "Savings Plan Type",
        options=available_types,
        default=available_types,
    )

date_parts = []
if "date" in util_history_df.columns:
    date_parts.append(pd.to_datetime(util_history_df["date"], errors="coerce"))
if "date" in coverage_history_df.columns:
    date_parts.append(pd.to_datetime(coverage_history_df["date"], errors="coerce"))
date_source = pd.concat(date_parts, ignore_index=True).dropna() if date_parts else pd.Series(dtype="datetime64[ns]")

if date_source.empty:
    default_start = date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    default_end = date.today()
else:
    default_start = date_source.min().date()
    default_end = date_source.max().date()

with filter_cols[2]:
    start_date, end_date = st.date_input(
        "Date range",
        value=(default_start, default_end),
        min_value=default_start,
        max_value=default_end,
    )

# Apply filters
filtered_plans = plans_df.copy()
if selected_regions:
    filtered_plans = filtered_plans[filtered_plans["Region"].isin(selected_regions)]
if selected_types:
    filtered_plans = filtered_plans[filtered_plans["Type"].isin(selected_types)]

# Util history: merge with plans only when per-ARN data exists; else use aggregated data
filtered_util_history = util_history_df.copy()
if not filtered_util_history.empty:
    has_util_arn = "savings_plan_arn" in filtered_util_history.columns
    has_plans_arn = not plans_df.empty and "Savings Plan Arn" in plans_df.columns
    if has_util_arn and has_plans_arn:
        filtered_util_history = filtered_util_history.merge(
            plans_df[["Savings Plan Arn", "Region", "Type"]],
            how="left",
            left_on="savings_plan_arn",
            right_on="Savings Plan Arn",
        )
        if selected_regions:
            filtered_util_history = filtered_util_history[filtered_util_history["Region"].isin(selected_regions)]
        if selected_types:
            filtered_util_history = filtered_util_history[filtered_util_history["Type"].isin(selected_types)]
    if "date" in filtered_util_history.columns:
        filtered_util_history = filtered_util_history[
            (pd.to_datetime(filtered_util_history["date"], errors="coerce") >= pd.to_datetime(start_date))
            & (pd.to_datetime(filtered_util_history["date"], errors="coerce") <= pd.to_datetime(end_date))
        ]
    util_cols = [c for c in ["date", "savings_plan_arn", "utilization_pct", "used_per_hour", "commitment_per_hour"] if c in filtered_util_history.columns]
    if util_cols:
        filtered_util_history = filtered_util_history[util_cols]

# Coverage history: same defensive handling
filtered_coverage_history = coverage_history_df.copy()
if not filtered_coverage_history.empty:
    has_cov_arn = "savings_plan_arn" in filtered_coverage_history.columns
    has_plans_arn = not plans_df.empty and "Savings Plan Arn" in plans_df.columns
    if has_cov_arn and has_plans_arn:
        filtered_coverage_history = filtered_coverage_history.merge(
            plans_df[["Savings Plan Arn", "Region", "Type"]],
            how="left",
            left_on="savings_plan_arn",
            right_on="Savings Plan Arn",
        )
        if selected_regions:
            filtered_coverage_history = filtered_coverage_history[filtered_coverage_history["Region"].isin(selected_regions)]
        if selected_types:
            filtered_coverage_history = filtered_coverage_history[filtered_coverage_history["Type"].isin(selected_types)]
    if "date" in filtered_coverage_history.columns:
        filtered_coverage_history = filtered_coverage_history[
            (pd.to_datetime(filtered_coverage_history["date"], errors="coerce") >= pd.to_datetime(start_date))
            & (pd.to_datetime(filtered_coverage_history["date"], errors="coerce") <= pd.to_datetime(end_date))
        ]
    cov_cols = [c for c in ["date", "savings_plan_arn", "coverage_pct", "covered_spend", "ondemand_spend"] if c in filtered_coverage_history.columns]
    if cov_cols:
        filtered_coverage_history = filtered_coverage_history[cov_cols]

util_trend_df = compute_utilization_trend(filtered_util_history)
coverage_trend_df = compute_coverage_trend(filtered_coverage_history)

# KPI calculations
total_commitment = pd.to_numeric(filtered_plans["Commitment ($/hr)"], errors="coerce").fillna(0.0).sum()
total_usage = pd.to_numeric(filtered_plans["Actual Usage ($/hr)"], errors="coerce").fillna(0.0).sum()
unused_commitment = pd.to_numeric(filtered_plans["Unused Commitment ($/hr)"], errors="coerce").fillna(0.0).sum()
current_utilization = (total_usage / total_commitment) * 100.0 if total_commitment else 0.0
forecast_util_pct = compute_forecast_util(util_trend_df)

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
with kpi_col1:
    render_kpi(
        "Total Commitment ($/hr)",
        format_usd(total_commitment),
        help_text="Hourly commitment across selected Savings Plans.",
    )
with kpi_col2:
    render_kpi(
        "Current Utilization %",
        f"{current_utilization:,.1f}%",
        help_text="How much of your committed spend was actually consumed.",
    )
with kpi_col3:
    render_kpi(
        "Unused Commitment ($/hr)",
        format_usd(unused_commitment),
        help_text="Commitment purchased but not currently used.",
    )
with kpi_col4:
    render_kpi(
        "Forecasted Utilization %",
        f"{forecast_util_pct:,.1f}%",
        help_text="Projected utilization based on the trailing 7-day trend.",
    )

st.markdown("### Savings Plans Inventory")
table_cols = [
    "SP ID",
    "Type",
    "Region",
    "Commitment ($/hr)",
    "Actual Usage ($/hr)",
    "Utilization %",
    "Coverage %",
    "Unused Commitment ($/hr)",
    "Forecast Utilization %",
    "Expiration Date",
]
if "Covers" in filtered_plans.columns:
    table_cols.insert(3, "Covers")  # After Type
table_df = filtered_plans[[c for c in table_cols if c in filtered_plans.columns]].copy()

table_df["Commitment ($/hr)"] = table_df["Commitment ($/hr)"].apply(lambda x: format_usd(x, 2))
table_df["Actual Usage ($/hr)"] = table_df["Actual Usage ($/hr)"].apply(lambda x: format_usd(x, 2))
table_df["Unused Commitment ($/hr)"] = table_df["Unused Commitment ($/hr)"].apply(lambda x: format_usd(x, 2))
table_df["Utilization %"] = table_df["Utilization %"].map(lambda x: f"{x:.2f}%")
table_df["Coverage %"] = table_df["Coverage %"].map(lambda x: f"{x:.2f}%")
table_df["Forecast Utilization %"] = table_df["Forecast Utilization %"].map(lambda x: f"{x:.2f}%")

st.dataframe(table_df, use_container_width=True, hide_index=True)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.markdown("#### Utilization Trend")
    util_chart = plot_utilization_trend(util_trend_df)
    if util_chart is not None:
        st.altair_chart(util_chart, use_container_width=True)
    else:
        st.info("Not enough data to plot utilization trend.")

with chart_col2:
    st.markdown("#### Coverage vs On-Demand Spend")
    coverage_chart = plot_coverage_vs_ondemand(coverage_trend_df)
    if coverage_chart is not None:
        st.altair_chart(coverage_chart, use_container_width=True)
    else:
        st.info("Not enough data to plot coverage history.")

st.markdown("### Insights & Recommendations")
render_insights(filtered_plans, coverage_trend_df)

if is_demo:
    st.caption("Showing demo data (CWT_DEMO_MODE enabled).")

