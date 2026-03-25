# pages/6_Chargeback.py — Chargeback
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
from cwt_ui.services.chargeback_service import ALLOCATION_DIMENSIONS, get_chargeback_data, get_chargeback_summary
from cwt_ui.services.synthetic_data import SERVICE_TO_AWS_NAME
from cwt_ui.utils.money import format_usd

st.set_page_config(page_title="Chargeback", page_icon="📋", layout="wide")

# Card styles (match Overview / Spend / Budgets)
st.markdown("""
<style>
    .chargeback-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .chargeback-card-label { font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .chargeback-card-value { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; }
    .chargeback-data-badge { display: inline-block; background: #1e3a5f; color: #7dd3fc; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; margin-left: 8px; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Chargeback",
    subtitle="Showback / chargeback by team or product.",
    icon="📋",
)

data_source = st.session_state.get("data_source", "none")
result = get_chargeback_data()

if data_source == "synthetic":
    st.markdown('<span class="chargeback-data-badge">Using synthetic data</span>', unsafe_allow_html=True)
    st.caption("Allocation by cost allocation tags. Connect CUR with tags enabled for real chargeback.")

if not result:
    st.info(
        "**No chargeback data yet.** Load **synthetic data** from Overview to see allocation by Team, "
        "Environment, and Cost Center. With CUR, allocation uses your cost allocation tags."
    )
    st.caption("Chargeback requires spend data with cost allocation tags.")
    st.stop()

spend_df, total_usd = result

# Allocation dimension selector
st.markdown("### Allocation summary")
dim_key = st.radio(
    "Group by",
    options=[d[0] for d in ALLOCATION_DIMENSIONS],
    format_func=lambda x: next((d[1] for d in ALLOCATION_DIMENSIONS if d[0] == x), x),
    horizontal=True,
    key="chargeback_group_by",
    help="Allocate spend by team, environment, or cost center.",
)

summary_df = get_chargeback_summary(spend_df, total_usd, dim_key)
col1, col2 = st.columns([1, 2])
with col1:
    st.markdown(
        f'''
        <div class="chargeback-card">
            <div class="chargeback-card-label">Total allocated</div>
            <div class="chargeback-card-value">{format_usd(total_usd)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
with col2:
    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount ($)": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
            "% of total": st.column_config.NumberColumn("% of total", format="%.1f%%"),
        },
    )

# Detail table with filters
st.markdown("### Detail table")
st.caption("Filter by service, team, environment, or cost center.")

# Filters
detail = spend_df.copy()
detail["service_display"] = detail["service"].map(lambda s: SERVICE_TO_AWS_NAME.get(s, s))

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    services = sorted(detail["service_display"].dropna().unique().tolist())
    selected_services = st.multiselect("Service", options=services, default=services, key="chargeback_filter_service")
with filter_col2:
    teams = sorted(detail["team"].dropna().unique().tolist())
    selected_teams = st.multiselect("Team", options=teams, default=teams, key="chargeback_filter_team")
with filter_col3:
    environments = sorted(detail["environment"].dropna().unique().tolist())
    selected_envs = st.multiselect("Environment", options=environments, default=environments, key="chargeback_filter_env")

filtered = detail[
    detail["service_display"].isin(selected_services)
    & detail["team"].isin(selected_teams)
    & detail["environment"].isin(selected_envs)
]

if "cost_center" in filtered.columns:
    cost_centers = sorted(filtered["cost_center"].dropna().unique().tolist())
    selected_cc = st.multiselect("Cost Center", options=cost_centers, default=cost_centers, key="chargeback_filter_cc")
    filtered = filtered[filtered["cost_center"].isin(selected_cc)]

if filtered.empty:
    st.warning("No rows match the selected filters.")
else:
    display_df = filtered[["service_display", "region", "team", "environment", "cost_center", "amount_usd"]].copy()
    display_df = display_df.rename(columns={
        "service_display": "Service",
        "region": "Region",
        "team": "Team",
        "environment": "Environment",
        "cost_center": "Cost Center",
        "amount_usd": "Amount ($)",
    })
    display_df = display_df.sort_values("Amount ($)", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount ($)": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
        },
    )

    # CSV export
    st.markdown("---")
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="Export CSV",
        data=csv,
        file_name="chargeback_export.csv",
        mime="text/csv",
        key="chargeback_export",
        help="Download chargeback detail as CSV.",
    )
