# pages/2_Spend.py — Spend (where money goes)
from __future__ import annotations

import sys
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.header import render_page_header
from cwt_ui.services.spend_aggregate import get_spend_from_scan, get_spend_mom_for_synthetic
from cwt_ui.services.synthetic_data import (
    LINKED_ACCOUNT_DISPLAY,
    SERVICE_TO_AWS_NAME,
    get_synthetic_daily_spend,
    get_synthetic_spend,
)
from cwt_ui.utils.money import format_usd

st.set_page_config(page_title="Spend", page_icon="💰", layout="wide")

# Spend page CSS (consistent with Overview)
st.markdown("""
<style>
    .spend-summary-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .spend-summary-label { font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .spend-summary-value { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; }
    .spend-summary-delta { font-size: 0.85rem; margin-top: 4px; }
    .spend-summary-delta.up { color: #22c55e; }
    .spend-summary-delta.down { color: #f59e0b; }
    .spend-data-badge { display: inline-block; background: #334155; color: #94a3b8; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; margin-left: 8px; }
    .spend-data-badge.synthetic { background: #1e3a5f; color: #7dd3fc; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Spend",
    subtitle="Where money goes — by cloud, account, team, and time.",
    icon="💰",
)

# Time period selector (synthetic only)
data_source = st.session_state.get("data_source", "none")
period = "this_month"
if data_source == "synthetic":
    period = st.radio(
        "Time period",
        options=["This month", "Last month"],
        index=0,
        horizontal=True,
        key="spend_period",
        help="Compare spend across months. MoM available with synthetic data.",
    )
    period = "this_month" if period == "This month" else "last_month"

total_usd, spend_df = get_spend_from_scan(period=period)
last_scan_at = st.session_state.get("last_scan_at", "")
prev_spend = st.session_state.get("previous_spend_total")

# Linked Account filter (synthetic only, when linked_account_id present)
if "linked_account_id" in spend_df.columns and not spend_df.empty:
    account_ids = sorted(spend_df["linked_account_id"].dropna().unique().tolist())
    selected_accounts = st.multiselect(
        "Filter by Linked Account",
        options=account_ids,
        format_func=lambda aid: LINKED_ACCOUNT_DISPLAY.get(aid, aid),
        default=account_ids,
        key="spend_filter_account",
        help="AWS Cost Explorer–style linked account filter. Select one or more accounts.",
    )
    if selected_accounts:
        spend_df = spend_df[spend_df["linked_account_id"].isin(selected_accounts)].copy()
        total_usd = float(spend_df["amount_usd"].sum())

# MoM for synthetic
mom = get_spend_mom_for_synthetic() if data_source == "synthetic" else None

# Data source indicator
if data_source == "synthetic":
    st.markdown('<span class="spend-data-badge synthetic">Using synthetic data</span>', unsafe_allow_html=True)
    st.caption("Run a scan from **Setup** to replace with live AWS data.")
if last_scan_at:
    scope = "Full service list (synthetic)" if data_source == "synthetic" else "EC2 + Savings Plans from scan"
    st.caption(f"Last scan: {last_scan_at[:16] if len(last_scan_at) > 16 else last_scan_at} · Data scope: {scope}.")

# Summary row (cards)
st.markdown("### Summary")
col1, col2 = st.columns(2)
with col1:
    period_label = "This month" if period == "this_month" else "Last month"
    st.markdown(
        f'''
        <div class="spend-summary-card">
            <div class="spend-summary-label">Total spend ({period_label})</div>
            <div class="spend-summary-value">{format_usd(total_usd) if total_usd and total_usd > 0 else "—"}</div>
            <div class="spend-summary-delta">{"Full service list (synthetic)" if data_source == "synthetic" else "EC2 + Savings Plans"}. Re-run scan to refresh.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
with col2:
    vs_value = "—"
    vs_delta = ""
    vs_class = ""
    if mom and data_source == "synthetic":
        this_total, last_total = mom
        other_total = last_total if period == "this_month" else this_total
        diff = total_usd - other_total
        if diff > 0:
            vs_value = f"+{format_usd(diff)}"
            vs_delta = "vs last month" if period == "this_month" else "vs this month"
            vs_class = "up"
        elif diff < 0:
            vs_value = f"-{format_usd(-diff)}"
            vs_delta = "vs last month" if period == "this_month" else "vs this month"
            vs_class = "down"
        else:
            vs_value = "No change"
            vs_delta = "vs last month" if period == "this_month" else "vs this month"
    elif prev_spend is not None and total_usd is not None and total_usd > 0:
        diff = total_usd - float(prev_spend)
        if diff > 0:
            vs_value = f"+{format_usd(diff)}"
            vs_delta = "vs last scan"
            vs_class = "up"
        elif diff < 0:
            vs_value = f"-{format_usd(-diff)}"
            vs_delta = "vs last scan"
            vs_class = "down"
        else:
            vs_value = "No change"
            vs_delta = "vs last scan"
    else:
        vs_delta = "Run another scan to see change vs last run." if data_source != "synthetic" else "Select time period above."
    st.markdown(
        f'''
        <div class="spend-summary-card">
            <div class="spend-summary-label">MoM comparison</div>
            <div class="spend-summary-value spend-summary-delta {vs_class}">{vs_value}</div>
            <div class="spend-summary-delta" style="font-size:0.8rem;color:#64748b;">{vs_delta}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    st.caption("With synthetic data: month-over-month. With real scan: vs last scan. Connect CUR for full time-series.")

# Top spend anomalies (synthetic only, MoM by service)
if data_source == "synthetic":
    try:
        _, df_this = get_synthetic_spend(period="this_month", include_tags=False)
        _, df_last = get_synthetic_spend(period="last_month", include_tags=False)
    except Exception:
        df_this = pd.DataFrame()
        df_last = pd.DataFrame()
    if not df_this.empty and not df_last.empty and "service" in df_this.columns and "service" in df_last.columns:
        by_this = df_this.groupby("service")["amount_usd"].sum()
        by_last = df_last.groupby("service")["amount_usd"].sum()
        all_services = by_this.index.union(by_last.index)
        rows = []
        for svc in all_services:
            this_amt = float(by_this.get(svc, 0))
            last_amt = float(by_last.get(svc, 0))
            delta = this_amt - last_amt
            if last_amt > 0:
                pct = round((delta / last_amt) * 100, 1)
            else:
                pct = 100.0 if delta > 0 else 0.0
            rows.append({"service": svc, "delta": delta, "pct": pct})
        anomalies_df = pd.DataFrame(rows)
        anomalies_df["abs_delta"] = anomalies_df["delta"].abs()
        anomalies_df = anomalies_df.sort_values("abs_delta", ascending=False).head(5)
        total_this = float(df_this["amount_usd"].sum())
        total_last = float(df_last["amount_usd"].sum())
        if total_this > 0 and total_last > 0 and not anomalies_df.empty:
            st.markdown("### Top spend anomalies")
            for _, row in anomalies_df.iterrows():
                svc = row["service"]
                delta = row["delta"]
                pct = row["pct"]
                name = SERVICE_TO_AWS_NAME.get(svc, svc)
                if delta > 0:
                    line = f"**{name}:** +{format_usd(delta)} (+{pct:.1f}%)"
                elif delta < 0:
                    line = f"**{name}:** -{format_usd(-delta)} ({pct:.1f}%)"
                else:
                    line = f"**{name}:** No change"
                st.markdown(f"- {line}")
            st.caption("Where spend changed most vs last month — core FinOps visibility.")

# Daily spend chart (synthetic only, above table)
if data_source == "synthetic" and not spend_df.empty and total_usd and total_usd > 0:
    daily_df = get_synthetic_daily_spend(period=period)
    if not daily_df.empty:
        st.markdown("### Daily Unblended Cost")
        st.caption("AWS Cost Explorer–style daily spend. Stacked by top 5 services.")
        by_service_total = daily_df.groupby("service")["amount_usd"].sum().sort_values(ascending=False)
        top_services = by_service_total.head(5).index.tolist()
        pivot = daily_df.pivot_table(index="date", columns="service", values="amount_usd", aggfunc="sum").fillna(0)
        chart_cols = [c for c in top_services if c in pivot.columns]
        other_cols = [c for c in pivot.columns if c not in chart_cols]
        if other_cols:
            pivot["Other"] = pivot[other_cols].sum(axis=1)
        chart_df = pivot[chart_cols + (["Other"] if other_cols else [])].copy()
        chart_df.index = pd.to_datetime(chart_df.index)
        # Only show series with non-zero total so the legend matches what's visible in the chart
        non_zero = [c for c in chart_df.columns if chart_df[c].sum() > 0]
        chart_df = chart_df[non_zero]
        if not chart_df.empty and not chart_df.columns.empty:
            st.area_chart(chart_df)

# Build display table from spend_df
if spend_df.empty or not total_usd or total_usd == 0:
    st.info("No spend data yet. Run a scan from **Setup** or load **synthetic data** from Overview to populate EC2 (and Savings Plans) spend.")
    st.stop()

# Group by selector (affects table below only, not the chart above)
group_by_opts = ["Service", "Region", "Service and region"]
if "linked_account_id" in spend_df.columns and spend_df["linked_account_id"].notna().any():
    group_by_opts = ["Service", "Linked Account", "Region", "Service and region"]
if "category" in spend_df.columns and spend_df["category"].notna().any():
    group_by_opts = ["Service", "Category", "Region", "Service and region"]
    if "linked_account_id" in spend_df.columns and spend_df["linked_account_id"].notna().any():
        group_by_opts = ["Service", "Category", "Linked Account", "Region", "Service and region"]
has_tags = all(c in spend_df.columns for c in ["environment", "team", "cost_center"])
if has_tags:
    group_by_opts = ["Service", "Category", "Linked Account", "Region", "Service and region", "Environment", "Team", "Cost Center"]
if "usage_type" in spend_df.columns and spend_df["usage_type"].notna().any():
    if "Usage Type" not in group_by_opts:
        group_by_opts.insert(1, "Usage Type")  # After Service — AWS Cost Explorer style
group_by = st.radio(
    "Group by",
    options=group_by_opts,
    index=0,
    horizontal=True,
    key="spend_group_by",
    help="How to aggregate the table below. Cost allocation tags match CUR / Cost Explorer.",
)


def _to_aws_name(service: str) -> str:
    return SERVICE_TO_AWS_NAME.get(service, service)


# Aggregate by chosen group-by (use AWS service names for display)
use_aws_names = data_source == "synthetic"

if group_by == "Service":
    table_df = (
        spend_df.groupby("service", as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    if use_aws_names:
        table_df["service_display"] = table_df["service"].map(_to_aws_name)
    else:
        table_df["service_display"] = table_df["service"]
    table_df = table_df.rename(columns={"service_display": "Service", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
    table_df = table_df[["Service", "Amount ($)", "% of total"]]
elif group_by == "Usage Type" and "usage_type" in spend_df.columns:
    usage_df = spend_df[spend_df["usage_type"].notna() & (spend_df["usage_type"] != "")]
    if usage_df.empty:
        table_df = pd.DataFrame(columns=["Usage Type", "Amount ($)", "% of total"])
        st.caption("No usage type breakdown available.")
    else:
        table_df = (
            usage_df.groupby("usage_type", as_index=False)["amount_usd"]
            .sum()
            .sort_values("amount_usd", ascending=False)
        )
        table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
        table_df = table_df.rename(columns={"usage_type": "Usage Type", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
        table_df = table_df[["Usage Type", "Amount ($)", "% of total"]]
elif group_by == "Category":
    if "category" not in spend_df.columns:
        table_df = spend_df.groupby("service", as_index=False)["amount_usd"].sum()
        table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
        table_df = table_df.rename(columns={"service": "Service", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
    else:
        table_df = (
            spend_df.groupby("category", as_index=False)["amount_usd"]
            .sum()
            .sort_values("amount_usd", ascending=False)
        )
        table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
        table_df = table_df.rename(columns={"category": "Category", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
elif group_by == "Linked Account" and "linked_account_id" in spend_df.columns:
    by_account = spend_df.groupby("linked_account_name", as_index=False)["amount_usd"].sum()
    by_account = by_account.sort_values("amount_usd", ascending=False)
    table_df = by_account.copy()
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    table_df = table_df.rename(columns={"linked_account_name": "Linked Account", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
    table_df = table_df[["Linked Account", "Amount ($)", "% of total"]]
elif group_by == "Region":
    by_region = spend_df[spend_df["region"] != "—"]
    if by_region.empty:
        table_df = pd.DataFrame(columns=["Region", "Amount ($)", "% of total"])
        st.caption("No region breakdown (e.g. SP-only data). Use *Service* or *Service and region*.")
    else:
        table_df = (
            by_region.groupby("region", as_index=False)["amount_usd"]
            .sum()
            .sort_values("amount_usd", ascending=False)
        )
        table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
        table_df = table_df.rename(columns={"region": "Region", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
elif group_by == "Environment" and "environment" in spend_df.columns:
    table_df = (
        spend_df.groupby("environment", as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    table_df = table_df.rename(columns={"environment": "Environment", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
elif group_by == "Team" and "team" in spend_df.columns:
    table_df = (
        spend_df.groupby("team", as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    table_df = table_df.rename(columns={"team": "Team", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
elif group_by == "Cost Center" and "cost_center" in spend_df.columns:
    table_df = (
        spend_df.groupby("cost_center", as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    table_df = table_df.rename(columns={"cost_center": "Cost Center", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
else:
    # Service and region
    table_df = (
        spend_df.groupby(["service", "region"], as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    table_df["pct_of_total"] = (table_df["amount_usd"] / total_usd * 100).round(1)
    if use_aws_names:
        table_df["service_display"] = table_df["service"].map(_to_aws_name)
    else:
        table_df["service_display"] = table_df["service"]
    table_df = table_df.rename(columns={"service_display": "Service", "region": "Region", "amount_usd": "Amount ($)", "pct_of_total": "% of total"})
    table_df = table_df[["Service", "Region", "Amount ($)", "% of total"]]

st.markdown("### Spend by " + group_by.lower())
st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Amount ($)": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
        "% of total": st.column_config.NumberColumn("% of total", format="%.1f%%"),
    },
)

# Export CSV
st.markdown("---")
csv = table_df.to_csv(index=False)
st.download_button(
    label="Export CSV",
    data=csv,
    file_name="spend_export.csv",
    mime="text/csv",
    key="spend_export",
    help="Download spend breakdown as CSV.",
)
