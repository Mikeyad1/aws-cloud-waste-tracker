# pages/4_Optimization.py — Waste (all recommendations, rightsizing); filename kept for compatibility
from __future__ import annotations

import sys
import traceback
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.header import render_page_header
from cwt_ui.components.optimization_tabs import (
    render_ec2_tab,
    render_lambda_tab,
    render_fargate_tab,
    render_commitment_tab,
    render_storage_tab,
    render_data_transfer_tab,
    render_databases_tab,
)
from cwt_ui.utils.money import format_usd

st.set_page_config(page_title="Waste", page_icon="🔧", layout="wide")

# --- Card styles (match Overview page) ---
st.markdown("""
<style>
    .overview-root { --space-1: 8px; --space-2: 16px; --space-3: 24px; --space-4: 32px; }
    .overview-sec-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: var(--space-2, 16px);
        margin-bottom: var(--space-1, 8px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .overview-sec-label { font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .overview-sec-value { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; }
    .overview-sec-meta { font-size: 0.8rem; color: #64748b; margin-top: 4px; }
    .overview-section { font-size: 0.95rem; font-weight: 600; color: #cbd5e1; margin: var(--space-3, 24px) 0 var(--space-1, 8px) 0; padding-bottom: 8px; border-bottom: 1px solid #334155; }
    /* Context block: Tabs + filters */
    .opt-context-block {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 32px 0 24px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .opt-context-header { font-size: 0.8rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
    .opt-context-meta { font-size: 0.85rem; color: #64748b; margin-bottom: 20px; }
    /* Make Streamlit tabs feel like primary nav */
    div[data-testid="stTabs"] { margin-top: 12px; margin-bottom: 8px; }
    div[data-testid="stTabs"] > div:first-child { padding: 6px 0; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Waste",
    subtitle="All recommendations, rightsizing, and what to turn off — compute, containers, serverless, commitments.",
    icon="🔧",
)

# Cross-tab summary: total potential savings + SP coverage by product
def _sum_potential(df: pd.DataFrame, col: str = "potential_savings_usd") -> float:
    if df is None or df.empty or col not in df.columns:
        return 0.0
    return float(df[col].sum())

def _sp_coverage_pct(df: pd.DataFrame) -> float | None:
    if df is None or df.empty or "billing_type" not in df.columns or df["billing_type"].isna().all():
        return None
    covered = df["billing_type"].astype(str).str.contains("SP", case=False, na=False)
    total = len(df)
    return (covered.sum() / total * 100) if total else 0.0

ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
lambda_df = st.session_state.get("lambda_df", pd.DataFrame())
fargate_df = st.session_state.get("fargate_df", pd.DataFrame())
storage_df = st.session_state.get("storage_df", pd.DataFrame())
dt_df = st.session_state.get("data_transfer_df", pd.DataFrame())
db_df = st.session_state.get("databases_df", pd.DataFrame())

total_savings = (
    _sum_potential(ec2_df) + _sum_potential(lambda_df) + _sum_potential(fargate_df)
    + _sum_potential(storage_df) + _sum_potential(dt_df) + _sum_potential(db_df)
)

sp_ec2 = _sp_coverage_pct(ec2_df)
sp_fargate = _sp_coverage_pct(fargate_df)
sp_lambda = _sp_coverage_pct(lambda_df)
sp_summary = " | ".join(
    f"{k}: {p:.0f}%" for k, p in [("EC2", sp_ec2), ("Fargate", sp_fargate), ("Lambda", sp_lambda)]
    if p is not None
) or "—"

action_count = 0
for df in [ec2_df, lambda_df, fargate_df]:
    if df is not None and not df.empty and "recommendation" in df.columns:
        rec = df.get("recommendation", pd.Series()).astype(str).str.lower()
        action_count += rec.str.contains("stop|rightsize|downsize|right-size", na=False).sum()

# Summary cards (match Overview KPI card style)
st.markdown('<p class="overview-section">Waste summary</p>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f'''
        <div class="overview-sec-card">
            <div class="overview-sec-label">Total potential savings</div>
            <div class="overview-sec-value">{format_usd(total_savings)}</div>
            <div class="overview-sec-meta">Across EC2, Fargate, Lambda, Storage, Data Transfer, Databases.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f'''
        <div class="overview-sec-card">
            <div class="overview-sec-label">SP coverage by product</div>
            <div class="overview-sec-value">{sp_summary}</div>
            <div class="overview-sec-meta">EC2 Instance SP + Compute SP. See tabs below for details.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f'''
        <div class="overview-sec-card">
            <div class="overview-sec-label">Recommendations</div>
            <div class="overview-sec-value">{int(action_count)}</div>
            <div class="overview-sec-meta">Items with actionable stop, rightsize, or downsize suggestions.</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
# Context block: Scope & filters + Tabs
st.markdown(
    """
    <div class="opt-context-block">
        <div class="opt-context-header">Scope & filters</div>
        <p class="opt-context-meta">Choose resource type and region to narrow the view. Filters are applied per tab.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Region selector (page-level scope) — aligns with context block
scope_col1, scope_col2 = st.columns([1, 4])
with scope_col1:
    ec2_for_scope = st.session_state.get("ec2_df", pd.DataFrame())
    if not ec2_for_scope.empty and "region" in ec2_for_scope.columns:
        scope_regions = sorted(ec2_for_scope["region"].dropna().unique().tolist())
        if scope_regions:
            st.selectbox(
                "Region",
                options=["All regions"] + scope_regions,
                key="optimization_region",
            )
with scope_col2:
    st.caption("Select a tab below to view and filter resources.")

# Tabs: Compute, Containers, Serverless, Commitment, Storage, Data Transfer, Databases
tab_compute, tab_containers, tab_serverless, tab_commitment, tab_storage, tab_data_transfer, tab_databases = st.tabs(
    [
        "Compute (EC2)",
        "Containers (Fargate)",
        "Serverless (Lambda)",
        "Commitment (Savings Plans)",
        "Storage (S3)",
        "Data Transfer",
        "Databases (RDS, DynamoDB)",
    ]
)
def _safe_render_tab(render_fn, tab_name: str) -> None:
    """Render a tab; show error placeholder if it fails instead of crashing the page."""
    try:
        render_fn()
    except Exception as e:
        st.error(f"Error loading **{tab_name}**: {e}")
        st.caption("If this persists, check the console for details.")
        with st.expander("Technical details", expanded=False):
            st.code(traceback.format_exc())

with tab_compute:
    _safe_render_tab(render_ec2_tab, "Compute (EC2)")
with tab_containers:
    _safe_render_tab(render_fargate_tab, "Containers (Fargate)")
with tab_serverless:
    _safe_render_tab(render_lambda_tab, "Serverless (Lambda)")
with tab_commitment:
    _safe_render_tab(render_commitment_tab, "Commitment (Savings Plans)")
with tab_storage:
    _safe_render_tab(render_storage_tab, "Storage (S3)")
with tab_data_transfer:
    _safe_render_tab(render_data_transfer_tab, "Data Transfer")
with tab_databases:
    _safe_render_tab(render_databases_tab, "Databases (RDS, DynamoDB)")
