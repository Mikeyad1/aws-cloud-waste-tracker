# pages/1_Waste.py — Waste home (Your waste + recommendations to lower it); sidebar label "1 Waste"
from __future__ import annotations

import os
import sys
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import pandas as pd
import streamlit as st

from cwt_ui.components.ui.header import render_page_header
from cwt_ui.components.ui.waste_number import render_waste_number
from cwt_ui.services.spend_aggregate import (
    get_spend_from_scan,
    get_spend_mom_for_synthetic,
    get_spend_mom_for_real,
)
from cwt_ui.services.budgets_service import get_first_budget_consumption
from cwt_ui.services.chargeback_service import get_chargeback_summary_for_overview
from cwt_ui.services.governance_service import get_open_violations_count
from cwt_ui.services.synthetic_data import load_synthetic_data_into_session
from cwt_ui.utils.money import format_usd
from cwt_ui.utils.resolved_persistence import load_resolved, load_excluded, save_resolved, save_excluded
from cwt_ui.services.ce_billing_lines import attach_ce_billing_lines_to_rows, ensure_ce_billing_lines_cache
from cwt_ui.utils.unified_recommendations import build_unified_what_to_turn_off
from cwt_ui.utils.policy_notices import render_waste_policy_footer

st.set_page_config(page_title="Waste", page_icon="📊", layout="wide")

# Feature flag so we can hide secondary expanders without deleting code
SHOW_EXTRA_METRICS = os.getenv("CWT_SHOW_EXTRA_METRICS", "").lower() in ("1", "true", "yes")

# --- Waste page: 8pt grid, clear hierarchy, polished cards ---
st.markdown("""
<style>
    /* Page rhythm and max-width for readability */
    .waste-page-content { --space-1: 8px; --space-2: 16px; --space-3: 24px; --space-4: 32px; --space-5: 40px; }
    /* Section titles — clear hierarchy */
    .waste-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f9fafb;
        margin: var(--space-4, 32px) 0 var(--space-2, 16px) 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #1f2937;
        letter-spacing: -0.01em;
    }
    .waste-section-title:first-of-type { margin-top: var(--space-4, 32px); }
    .waste-section-title + .waste-category-wrap { margin-top: var(--space-2, 16px); }
    .waste-hero-secondary {
        font-size: 0.9rem;
        color: #9ca3af;
        margin-top: 6px;
        margin-bottom: 0;
    }
    .waste-hero-secondary strong {
        color: #e5e7eb;
        font-weight: 600;
    }
    /* Category cards — cohesive block matching recommendation style */
    .waste-category-wrap {
        margin-bottom: var(--space-4, 32px);
    }
    .overview-sec-card {
        background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 55%),
            linear-gradient(150deg, #020617, #020617);
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 16px 18px 14px 18px;
        margin-bottom: 0;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.75);
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 8px;
        transition: border-color 0.15s ease-out, box-shadow 0.15s ease-out, transform 0.15s ease-out;
    }
    .overview-sec-card:hover {
        border-color: #38bdf8;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.95);
        transform: translateY(-1px);
    }
    .overview-sec-header {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .overview-sec-icon {
        width: 22px;
        height: 22px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem;
        background: radial-gradient(circle at 30% 0%, rgba(56, 189, 248, 0.35), rgba(15, 23, 42, 0.96));
        color: #e0f2fe;
    }
    .overview-sec-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .overview-sec-label {
        font-size: 0.72rem;
        font-weight: 650;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .overview-sec-meta {
        font-size: 0.78rem;
        color: #6b7280;
    }
    .overview-sec-bottom {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
    }
    .overview-sec-value {
        font-size: 1.4rem;
        font-weight: 800;
        color: #f9fafb;
        letter-spacing: -0.02em;
    }
    .overview-sec-chip {
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid #1f2937;
        background: rgba(15, 23, 42, 0.9);
        font-size: 0.72rem;
        color: #9ca3af;
        white-space: nowrap;
    }
    /* Legacy section class */
    .overview-section { font-size: 0.95rem; font-weight: 600; color: #cbd5e1; margin: var(--space-3, 24px) 0 var(--space-1, 8px) 0; padding-bottom: 8px; border-bottom: 1px solid #334155; }
    /* Spend bar (stacked proportions) */
    .overview-spend-bar { display: flex; height: 24px; border-radius: 8px; overflow: hidden; margin: 8px 0; background: #1e293b; }
    .overview-spend-seg { flex-grow: 0; flex-shrink: 0; min-width: 4px; }
    /* EC2 + SP cost breakdown card */
    .overview-breakdown-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .overview-breakdown-title { font-size: 0.85rem; font-weight: 600; color: #94a3b8; margin-bottom: 4px; }
    .overview-breakdown-total { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; margin-bottom: 16px; }
    .overview-breakdown-bar { display: flex; height: 28px; border-radius: 8px; overflow: hidden; margin: 12px 0; background: #0f172a; }
    .overview-breakdown-seg { flex-grow: 0; flex-shrink: 0; min-width: 6px; }
    .overview-breakdown-legend { display: flex; flex-wrap: wrap; gap: 20px 24px; margin-top: 12px; font-size: 0.9rem; }
    .overview-breakdown-legend-item { display: flex; align-items: center; gap: 6px; }
    .overview-breakdown-legend-dot { width: 10px; height: 10px; border-radius: 4px; }
    .overview-breakdown-legend-label { color: #cbd5e1; }
    .overview-breakdown-legend-value { font-weight: 600; color: #f1f5f9; }
    .overview-breakdown-context { font-size: 0.8rem; color: #64748b; margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; }
    /* What changed */
    .overview-delta-box { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; margin-top: 8px; }
    .overview-delta-item { font-size: 0.9rem; color: #cbd5e1; margin-bottom: 4px; }
    .overview-delta-item .up { color: #22c55e; }
    .overview-delta-item .down { color: #f59e0b; }
    /* Recommendation cards — structured layout, strong hierarchy */
    .rec-card-box {
        background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.14), transparent 55%),
            linear-gradient(145deg, #020617, #020617);
        border-radius: 16px;
        border: 1px solid #1f2937;
        padding: 18px 20px 14px 20px;
        margin-bottom: 16px;
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.8);
        display: flex;
        flex-direction: column;
        gap: 10px;
        transition: transform 0.15s ease-out, box-shadow 0.15s ease-out, border-color 0.15s ease-out, background 0.15s ease-out;
    }
    .rec-card-box--top {
        border-color: #22d3ee;
        box-shadow: 0 18px 46px rgba(8, 47, 73, 0.95);
    }
    .rec-card-box:hover {
        transform: translateY(-1px);
        border-color: #38bdf8;
        box-shadow: 0 22px 56px rgba(15, 23, 42, 1);
    }
    .rec-card-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
    }
    .rec-card-title-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .rec-card-rank {
        min-width: 22px;
        height: 22px;
        border-radius: 999px;
        border: 1px solid #1e293b;
        background: radial-gradient(circle at 30% 0%, #0f172a, #020617);
        font-size: 0.7rem;
        font-weight: 600;
        color: #64748b;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .rec-card-box--top .rec-card-rank {
        border-color: rgba(34, 211, 238, 0.85);
        color: #7dd3fc;
    }
    .rec-card-title {
        font-size: 1.02rem;
        font-weight: 650;
        color: #e5e7eb;
        line-height: 1.4;
        letter-spacing: -0.01em;
    }
    .rec-card-impact {
        text-align: right;
        min-width: 170px;
    }
    .rec-card-impact-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        font-weight: 600;
        color: #64748b;
        letter-spacing: 0.08em;
        margin-bottom: 2px;
    }
    .rec-card-waste {
        font-size: 1.4rem;
        font-weight: 800;
        color: #22d3ee;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .rec-card-waste-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 2px;
    }
    .rec-card-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 16px;
        align-items: center;
    }
    .rec-card-meta {
        font-size: 0.82rem;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .rec-card-meta .rec-meta-label {
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.7rem;
    }
    .rec-card-meta .rec-meta-value {
        color: #e2e8f0;
        font-weight: 500;
    }
    .rec-service-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 9px;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #1e293b;
        font-size: 0.78rem;
        color: #cbd5e1;
    }
    .rec-service-pill-icon {
        width: 18px;
        height: 18px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        background: radial-gradient(circle at 30% 0%, rgba(56, 189, 248, 0.32), rgba(15, 23, 42, 0.92));
        color: #e0f2fe;
    }
    .rec-service-pill-label {
        font-weight: 500;
    }
    .rec-card-body {
        border-top: 1px solid #111827;
        margin-top: 6px;
        padding-top: 8px;
    }
    .rec-card-why {
        font-size: 0.85rem;
        color: #9ca3af;
        line-height: 1.5;
        margin-bottom: 4px;
    }
    .rec-card-why .rec-why-label {
        color: #6b7280;
        font-weight: 500;
    }
    .rec-card-why .rec-why-text {
        color: #e5e7eb;
    }
    .rec-card-what {
        font-size: 0.84rem;
        color: #9ca3af;
        line-height: 1.45;
        margin-top: 2px;
    }
    .rec-card-what .rec-what-label {
        color: #6b7280;
        font-weight: 500;
    }
    .rec-card-what .rec-what-text {
        color: #d1d5db;
    }
    .rec-actions-spacer {
        height: 2px;
        margin: 0 0 6px 0;
        background: transparent;
    }
    .rec-actions-row {
        display: flex;
        gap: 10px;
        justify-content: flex-end;
        align-items: center;
        margin-bottom: 12px;
    }
    .rec-actions-row [data-testid="baseButton-secondary"],
    .rec-actions-row [data-testid="baseButton-primary"] {
        border-radius: 999px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }
    .waste-demo-banner {
        font-size: 0.86rem;
        color: #e5e7eb;
        background:
            radial-gradient(circle at top left, rgba(248, 250, 252, 0.12), transparent 55%),
            linear-gradient(145deg, #0b1120, #020617);
        border: 1px solid #4b5563;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.85);
    }
    .waste-demo-banner-pill {
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid #eab308;
        background: rgba(250, 204, 21, 0.12);
        font-size: 0.75rem;
        font-weight: 650;
        color: #eab308;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        white-space: nowrap;
    }
    .waste-demo-banner-body {
        font-size: 0.86rem;
        color: #e5e7eb;
    }
    .waste-demo-banner strong { color: #e5e7eb; }
    .overview-rec-card {
        background: #1e293b; border: 1px solid #334155; border-radius: 12px;
        padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    .overview-rec-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
    .overview-rec-severity { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 6px; }
    .overview-rec-severity.critical { background: #7f1d1d; color: #fecaca; }
    .overview-rec-severity.moderate { background: #78350f; color: #fde68a; }
    .overview-rec-severity.low { background: #1e3a5f; color: #93c5fd; }
    .overview-rec-id { font-weight: 600; color: #f1f5f9; }
    .overview-rec-savings { color: #22c55e; font-weight: 600; font-size: 0.9rem; }
    .overview-rec-text { font-size: 0.9rem; color: #94a3b8; margin: 8px 0; }
    .overview-rec-meta { font-size: 0.8rem; color: #64748b; }
    /* Data badge */
    .overview-data-badge { display: inline-block; background: #334155; color: #94a3b8; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; margin-left: 8px; }
    .overview-data-badge.synthetic { background: #1e3a5f; color: #7dd3fc; }
    /* CTA block */
    .overview-cta-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 16px; }
    /* Mobile tweaks for recommendation cards */
    @media (max-width: 640px) {
        .rec-card-box {
            padding: 16px 14px 12px 14px;
        }
        .rec-card-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .rec-card-impact {
            text-align: left;
            min-width: 0;
            width: 100%;
        }
        .rec-card-waste {
            font-size: 1.25rem;
        }
        .rec-card-meta-row {
            align-items: flex-start;
        }
        .rec-actions-row {
            flex-direction: column;
            align-items: stretch;
        }
    }
</style>
""", unsafe_allow_html=True)

# Persistent data source indicator in header (MVP command 15)
_data_source = st.session_state.get("data_source", "none")
_last_scan_at = st.session_state.get("last_scan_at", "")
render_page_header(
    title="Your waste",
    subtitle="One number. One list. Your cloud waste.",
    icon="📊",
    data_source=_data_source,
    last_scan_at=_last_scan_at,
)

# Check if we have data
_ec2 = st.session_state.get("ec2_df")
_has_data = (_ec2 is not None and not _ec2.empty) or _data_source == "synthetic"
data_source = _data_source

# Empty state: auto-load synthetic so users see the wedge immediately (no click required)
if not _has_data:
    load_synthetic_data_into_session()
    st.rerun()
    st.stop()

# --- Resolved and Excluded (persisted to file so it survives refresh) ---
if "resolved_recommendations" not in st.session_state:
    st.session_state["resolved_recommendations"] = load_resolved()
if "excluded_recommendations" not in st.session_state:
    st.session_state["excluded_recommendations"] = load_excluded()  # list of {Service, Resource, "Waste ($/mo)"}

def _resolved_key(row: dict) -> tuple:
    return (str(row.get("Service", "")), str(row.get("Resource", "")))

def _filter_unresolved(rows: list[dict], resolved: list[dict]) -> list[dict]:
    keys = {_resolved_key(r) for r in resolved}
    return [r for r in rows if _resolved_key(r) not in keys]

def _filter_not_excluded(rows: list[dict], excluded: list[dict]) -> list[dict]:
    keys = {_resolved_key(r) for r in excluded}
    return [r for r in rows if _resolved_key(r) not in keys]

def _category_icon(category: str) -> str:
    c = (category or "").strip()
    if c == "Compute":
        return "🖥"
    if c == "Storage":
        return "🗄"
    if c == "Network":
        return "📡"
    if c == "Databases":
        return "🗃"
    return "☁️"

def _service_icon(service: str) -> str:
    s = (service or "").strip()
    if s == "EC2":
        return "🖥"
    if s in ("Lambda", "AWS Lambda"):
        return "λ"
    if s in ("Fargate", "ECS", "ECS/Fargate"):
        return "📦"
    if s in ("S3", "Amazon S3"):
        return "🗄"
    if s == "Data Transfer":
        return "📡"
    if s == "CloudFront":
        return "🌐"
    if "RDS" in s or "Aurora" in s or "DynamoDB" in s:
        return "🗃"
    return "☁️"

# --- Data from session state ---
ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
lambda_df = st.session_state.get("lambda_df", pd.DataFrame())
fargate_df = st.session_state.get("fargate_df", pd.DataFrame())
storage_df = st.session_state.get("storage_df", pd.DataFrame())
data_transfer_df = st.session_state.get("data_transfer_df", pd.DataFrame())
databases_df = st.session_state.get("databases_df", pd.DataFrame())
last_scan_at = _last_scan_at
spend_total_usd, spend_df = get_spend_from_scan()
mom = get_spend_mom_for_synthetic() if data_source == "synthetic" else get_spend_mom_for_real() if data_source == "real" else None
budget_kpi = get_first_budget_consumption()
chargeback_summary = get_chargeback_summary_for_overview()

resolved_list = st.session_state["resolved_recommendations"]
excluded_list = st.session_state["excluded_recommendations"]
resolved_waste = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in resolved_list)
excluded_waste = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in excluded_list)

# Same list as "Top actions" cards — headline total = sum of these rows (before resolve/exclude)
unified_rows = build_unified_what_to_turn_off(
    ec2_df if ec2_df is not None and not ec2_df.empty else None,
    lambda_df if lambda_df is not None and not lambda_df.empty else None,
    fargate_df if fargate_df is not None and not fargate_df.empty else None,
    storage_df if storage_df is not None and not storage_df.empty else None,
    data_transfer_df if data_transfer_df is not None and not data_transfer_df.empty else None,
    databases_df if databases_df is not None and not databases_df.empty else None,
)
if unified_rows:
    _ce_cache = ensure_ce_billing_lines_cache(st.session_state, unified_rows, str(last_scan_at or ""))
    attach_ce_billing_lines_to_rows(unified_rows, cache=_ce_cache, data_source=data_source)
for i, r in enumerate(unified_rows):
    r["_stable_idx"] = i

gross_waste = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in unified_rows)
action_count = len(unified_rows)
optimization_potential = max(0.0, gross_waste - resolved_waste - excluded_waste)
prev_opt = st.session_state.get("previous_optimization_potential")
prev_act = st.session_state.get("previous_action_count")
has_prev = prev_opt is not None and prev_act is not None

# ----- 1. Hero: Your Waste -----
# One-line data-source label under the waste number (MVP command 7)
if _has_data and data_source != "synthetic":
    data_source_hint = "From your first sync."
else:
    data_source_hint = None
hero_col, _ = st.columns([2, 1])
with hero_col:
    render_waste_number(
        waste_amount=optimization_potential if optimization_potential else None,
        period="this month",
        subtitle="Monthly waste you can eliminate. Open **Where this number comes from** on any row for the breakdown.",
        data_source_hint=data_source_hint,
    )
    # Total saved to date (Wins) — from resolved items, persisted
    total_saved_to_date = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in resolved_list)
    if total_saved_to_date > 0:
        st.caption(f"**Wins:** {format_usd(total_saved_to_date)} saved to date from items you marked as resolved.")

if data_source == "synthetic":
    st.markdown(
        '<div class="waste-demo-banner">'
        '<div class="waste-demo-banner-pill">Demo mode</div>'
        '<div class="waste-demo-banner-body">'
        '<strong>These numbers are sample data.</strong> Connect your AWS account in Setup to see your real waste and savings opportunities.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ----- Waste by category (where the waste is coming from) -----
def _service_to_category(service: str) -> str:
    s = (service or "").strip()
    if s in ("EC2", "Lambda", "Fargate"):
        return "Compute"
    if s == "S3":
        return "Storage"
    if s == "Data Transfer":
        return "Network"
    if s and s != "—":
        return "Databases"  # RDS, DynamoDB, etc.
    return "Other"

# Filter unified list (categories and recommendations)
rows_visible_all = _filter_not_excluded(unified_rows, excluded_list) if unified_rows else []
rows_visible_all = _filter_unresolved(rows_visible_all, resolved_list) if rows_visible_all else []

# When set, the "Top actions" list below will show only recommendations whose
# Service maps to this category (Compute/Storage/Network/Databases/Other).
st.session_state.setdefault("waste_category_filter", None)
selected_category = st.session_state.get("waste_category_filter")

display_rows_all = (
    rows_visible_all
    if not selected_category
    else [r for r in rows_visible_all if _service_to_category(r.get("Service", "")) == selected_category]
)
st.session_state.setdefault("show_full_list", False)
show_full_list = st.session_state.get("show_full_list", False)
TOP_N = 12
display_rows = display_rows_all[:TOP_N] if not show_full_list else display_rows_all

# Category totals from visible recommendations
category_totals: dict[str, float] = {}
for r in rows_visible_all:
    cat = _service_to_category(r.get("Service", ""))
    category_totals[cat] = category_totals.get(cat, 0.0) + float(r.get("Waste ($/mo)", 0) or 0)
# Show only categories that have waste; order: Compute, Storage, Network, Databases, Other
cat_order = ["Compute", "Storage", "Network", "Databases", "Other"]
category_totals = {k: category_totals.get(k, 0.0) for k in cat_order if category_totals.get(k, 0.0) > 0}
if category_totals:
    st.markdown('<p class="waste-section-title">Waste by category</p>', unsafe_allow_html=True)
    st.markdown('<div class="waste-category-wrap">', unsafe_allow_html=True)
    cols = st.columns(min(len(category_totals), 4))
    total_cat_amt = sum(category_totals.values())
    scale_factor = 1.0
    if total_cat_amt > 0 and optimization_potential:
        # Scale category tiles so they form a breakdown of the hero number
        scale_factor = float(optimization_potential) / float(total_cat_amt)
    for idx, (cat, amt) in enumerate(category_totals.items()):
        scaled_amt = amt * scale_factor
        pct = (scaled_amt / optimization_potential * 100.0) if optimization_potential else 0.0
        icon = _category_icon(cat)
        with cols[idx % len(cols)]:
            st.markdown(
                f'<div class="overview-sec-card">'
                f'  <div class="overview-sec-header">'
                f'    <div class="overview-sec-icon">{icon}</div>'
                f'    <div class="overview-sec-text">'
                f'      <div class="overview-sec-label">{cat}</div>'
                f'      <div class="overview-sec-meta">Estimated monthly waste</div>'
                f'    </div>'
                f'  </div>'
                f'  <div class="overview-sec-bottom">'
                f'    <div class="overview-sec-value">{format_usd(scaled_amt)}</div>'
                f'    <div class="overview-sec-chip">{pct:.0f}% of visible waste</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

if selected_category:
    st.caption(f"Filtering recommendations to: {selected_category}")
    if st.button(
        "Clear category filter",
        key="clear_waste_category_filter",
        type="secondary",
        use_container_width=False,
    ):
        st.session_state["waste_category_filter"] = None
        st.session_state["show_full_list"] = False
        st.rerun()

# ----- Top actions to reduce waste -----
st.markdown('<p class="waste-section-title">Top actions to reduce your waste</p>', unsafe_allow_html=True)
st.caption(
    "Savings shown below are estimated per month. Open **Where this number comes from** on any row to see the source. "
    "Fixing the top items first usually delivers the biggest wins fastest."
)

def _escape_html(s: str) -> str:
    """Minimal escape for use inside HTML."""
    if not s:
        return ""
    out = str(s)
    out = out.replace("&", "&amp;")
    out = out.replace("<", "&lt;")
    out = out.replace(">", "&gt;")
    out = out.replace('"', '&quot;')
    return out


def _billing_lines_expander_title(r: dict) -> str:
    """Distinguish embedded CE lines vs verification-only."""
    items = r.get("billing_line_items") or []
    ver_note = r.get("billing_verification_note")
    svc = r.get("Service", "")
    src = r.get("billing_lines_source")
    demo = data_source == "synthetic"
    if items and ver_note:
        if demo:
            return "What billing shows (sample)"
        return "Billing lines & verify"
    if items:
        if demo:
            return "What billing shows (sample)"
        if svc == "Data Transfer":
            return "Billing lines (month to date)"
        if src == "ce":
            return "Billing lines (month to date)"
        return "Billing line items"
    if ver_note:
        return "How to verify in AWS Billing"
    return "View billing line items"


def _render_billing_line_items_block(r: dict) -> None:
    """Cost Explorer / billing verification: line items when available, else how to verify in AWS."""
    items = r.get("billing_line_items") or []
    ver_note = r.get("billing_verification_note")
    if not items and not ver_note:
        return
    # Sample data: never show fake Cost Explorer / billing dollar amounts in this panel.
    hide_amounts = data_source == "synthetic" or bool(r.get("billing_hide_amounts"))
    with st.expander(_billing_lines_expander_title(r), expanded=False):
        if items:
            intro = r.get("billing_intro", "")
            period = r.get("billing_period_label", "")
            if hide_amounts and r.get("Service") == "Data Transfer":
                intro = "**Sample mode:** Example line labels only — connect AWS for real billing lines (no fake amounts here)."
            if intro:
                st.markdown(intro)
            if period and not hide_amounts:
                st.caption(period)
            for i, entry in enumerate(items, 1):
                line = entry.get("line", "—")
                if hide_amounts:
                    st.markdown(f"**Line {i}**  \n{line}")
                else:
                    amt = float(entry.get("amount_usd", 0) or 0)
                    st.markdown(
                        f"**Line {i}**  \n{line}  \n**Billed amount (month to date):** {format_usd(amt)}"
                    )
            if not hide_amounts:
                total = sum(float(x.get("amount_usd", 0) or 0) for x in items)
                st.markdown(f"**Total for these billing lines** — {format_usd(total)}")
        if ver_note:
            if items:
                st.markdown("---")
            st.markdown(ver_note)

if display_rows:
    # Card per recommendation: Resource, Type, Why, What to do, Potential savings, actions
    for idx, r in enumerate(display_rows):
        key_safe = f"resolve_{r['_stable_idx']}"
        key_excl = f"exclude_{r['_stable_idx']}"
        action_title = r.get("Action title") or r.get("Fix steps", "—")
        fix_steps = r.get("Fix steps", "—")
        waste_usd = float(r.get("Waste ($/mo)", 0) or 0)
        resource = r.get("Resource", "—")
        service = r.get("Service", "—")
        rec_type = r.get("Action", "—")
        reason = r.get("Reason", "—")
        waste_str = format_usd(waste_usd)
        rank = idx + 1
        is_top = idx < 3
        service_icon = _service_icon(service)
        title_esc = _escape_html(action_title)
        fix_esc = _escape_html(fix_steps)
        resource_esc = _escape_html(resource)
        service_esc = _escape_html(service)
        type_esc = _escape_html(rec_type)
        reason_esc = _escape_html(reason)
        what_block = ""
        if fix_steps and fix_steps != "—" and fix_steps != action_title:
            what_block = f'<div class="rec-card-what"><span class="rec-what-label">What to do:</span> <span class="rec-what-text">{fix_esc}</span></div>'
        card_html = (
            f'<div class="rec-card-box{" rec-card-box--top" if is_top else ""}">'
            '<div class="rec-card-header">'
            '<div class="rec-card-title-wrap">'
            f'<div class="rec-card-rank">#{rank}</div>'
            f'<div class="rec-card-title">{title_esc}</div>'
            '</div>'
            '<div class="rec-card-impact">'
            '<div class="rec-card-impact-label">Potential savings</div>'
            f'<div class="rec-card-waste">{waste_str}</div>'
            '<div class="rec-card-waste-sub">per month</div>'
            '</div>'
            '</div>'
            '<div class="rec-card-meta-row">'
            f'<div class="rec-card-meta"><span class="rec-meta-label">Resource</span><span class="rec-meta-value">{resource_esc}</span></div>'
            f'<div class="rec-card-meta rec-service-pill"><span class="rec-service-pill-icon">{service_icon}</span><span class="rec-service-pill-label">{service_esc}</span></div>'
            f'<div class="rec-card-meta"><span class="rec-meta-label">Type</span><span class="rec-meta-value">{type_esc}</span></div>'
            '</div>'
            '<div class="rec-card-body">'
            f'<div class="rec-card-why"><span class="rec-why-label">Why:</span> <span class="rec-why-text">{reason_esc}</span></div>'
            f'{what_block}'
            '</div>'
            '</div>'
        )
        with st.container():
            st.markdown(card_html, unsafe_allow_html=True)
            calc_md = (r.get("Calculation") or "").strip()
            if calc_md:
                with st.expander("Where this number comes from", expanded=False):
                    st.markdown(calc_md)
            _render_billing_line_items_block(r)
            st.markdown('<div class="rec-actions-spacer"></div>', unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns([3, 1])
            with btn_col1:
                if st.button("Mark as resolved", key=key_safe, type="primary", use_container_width=True, help="Move this item to your resolved list and subtract its waste from the total."):
                    item = {
                        "Service": r.get("Service", ""),
                        "Resource": r.get("Resource", ""),
                        "Waste ($/mo)": float(r.get("Waste ($/mo)", 0) or 0),
                        "Fix steps": r.get("Fix steps", ""),
                    }
                    st.session_state["resolved_recommendations"].append(item)
                    save_resolved(st.session_state["resolved_recommendations"])
                    st.rerun()
            with btn_col2:
                if st.button("Exclude", key=key_excl, use_container_width=True, help="Hide this recommendation and exclude its waste from your total. You can restore it later in Settings."):
                    excl_item = {
                        "Service": r.get("Service", ""),
                        "Resource": r.get("Resource", ""),
                        "Waste ($/mo)": float(r.get("Waste ($/mo)", 0) or 0),
                    }
                    st.session_state["excluded_recommendations"].append(excl_item)
                    save_excluded(st.session_state["excluded_recommendations"])
                    st.rerun()
    total_rec_count = len(display_rows_all)
    if show_full_list:
        if st.button("Show top 12 only", key="show_top_12", type="secondary", use_container_width=False):
            st.session_state["show_full_list"] = False
            st.rerun()
    elif total_rec_count > TOP_N:
        if st.button(f"View all {total_rec_count} in Waste →", key="view_all_waste", type="secondary", use_container_width=False, help="Expand to see the full list on this page."):
            st.session_state["show_full_list"] = True
            st.rerun()
    # Resolved this session
    if resolved_list:
        with st.expander(f"Resolved this session ({len(resolved_list)})", expanded=False):
            for i, res in enumerate(resolved_list):
                undo_key = f"undo_{res.get('Service','')}_{res.get('Resource','')}_{i}".replace(" ", "_").replace("|", "_")[:80]
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.caption(f"**{res.get('Resource', '—')}** · {format_usd(float(res.get('Waste ($/mo)', 0)))} · {res.get('Service', '—')} · {res.get('Fix steps', '—')}")
                with c2:
                    if st.button("Undo", key=undo_key):
                        new_list = [x for x in resolved_list if _resolved_key(x) != _resolved_key(res)]
                        st.session_state["resolved_recommendations"] = new_list
                        save_resolved(new_list)
                        st.rerun()
elif unified_rows:
    st.markdown("All visible recommendations are marked as resolved. Un-resolve from the list below or run a new scan.")
    if resolved_list:
        with st.expander(f"Resolved this session ({len(resolved_list)})", expanded=True):
            for i, res in enumerate(resolved_list):
                undo_key = f"undo_{res.get('Service','')}_{res.get('Resource','')}_{i}".replace(" ", "_").replace("|", "_")[:80]
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.caption(f"**{res.get('Resource', '—')}** · {format_usd(float(res.get('Waste ($/mo)', 0)))} · {res.get('Service', '—')} · {res.get('Fix steps', '—')}")
                with c2:
                    if st.button("Undo", key=undo_key):
                        new_list = [x for x in resolved_list if _resolved_key(x) != _resolved_key(res)]
                        st.session_state["resolved_recommendations"] = new_list
                        save_resolved(new_list)
                        st.rerun()
else:
    st.markdown("No recommendations yet. Load **synthetic data** or run a scan from **Setup**, then open **Waste**.")

if SHOW_EXTRA_METRICS:
    # ----- 3. Other metrics: below the fold, behind "See more" (MVP command 25) -----
    # Above the fold = hero + categories + action list only; spend, budget, violations in expander.
    with st.expander("See more (spend, budget, violations)", expanded=False):
        # Data source bar (moved from above the fold for time-to-value)
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("📥 Load synthetic data", type="secondary", key="load_synthetic_see_more", help="Load demo data to explore without an active AWS account."):
                load_synthetic_data_into_session()
                st.rerun()
        with c2:
            if data_source == "synthetic":
                st.markdown('<span class="overview-data-badge synthetic">Using synthetic data</span>', unsafe_allow_html=True)
                st.caption("Run a scan from **Setup** to replace with live AWS data.")
        st.markdown("---")
        st.markdown("Secondary metrics — not part of the main Waste view.")
        context_col1, context_col2, context_col3 = st.columns(3)
        with context_col1:
            if spend_total_usd and spend_total_usd > 0:
                spend_meta = "Full service list" if data_source == "synthetic" else "EC2 + SP + S3 + Data Transfer + RDS/DynamoDB"
                if mom:
                    this_total, last_total = mom
                    if last_total and last_total > 0:
                        mom_pct = round((this_total - last_total) / last_total * 100, 1)
                        mom_dir = "↑" if mom_pct > 0 else "↓"
                        spend_meta = f"{spend_meta}. {mom_dir} {abs(mom_pct):.1f}% vs last month"
                st.markdown(f"**💰 Total spend:** {format_usd(spend_total_usd)}")
                st.caption(spend_meta)
            else:
                st.caption("No spend data yet")
        with context_col2:
            if budget_kpi:
                consumed_pct, consumed, status = budget_kpi
                status_label = "On track" if status == "on_track" else "At risk" if status == "at_risk" else "Over"
                st.markdown(f"**📈 Budget:** {consumed_pct:.0f}% used ({status_label})")
                st.caption(f"{format_usd(consumed)} of budget")
            else:
                st.caption("📈 Set up budgets (see pages/_archive when restored)")
        with context_col3:
            open_violations = get_open_violations_count()
            if open_violations > 0:
                st.markdown(f"**🛡️ {open_violations} open violations**")
            else:
                st.caption("🛡️ No open violations")

    st.markdown("")  # spacing

    # ----- Spend breakdown (collapsible) -----
    if not spend_df.empty and spend_total_usd and spend_total_usd > 0:
        with st.expander("📊 See spend breakdown", expanded=False):
            CATEGORY_COLORS = {
                "Compute": "#f59e0b",
                "Storage": "#3b82f6",
                "Containers": "#ec4899",
                "Networking": "#06b6d4",
                "Databases": "#8b5cf6",
                "Monitoring": "#10b981",
                "Commitment": "#22c55e",
                "Other": "#64748b",
            }
            by_service = spend_df.groupby("service", as_index=False)["amount_usd"].sum().sort_values("amount_usd", ascending=False)
            top5 = by_service.head(5)
            top_drivers = " · ".join([f"<strong>{r['service']}</strong> {format_usd(r['amount_usd'])}" for _, r in top5.iterrows()])
            by_account_html = ""
            if "linked_account_id" in spend_df.columns and spend_df["linked_account_id"].notna().any():
                by_account = spend_df.groupby("linked_account_name", as_index=False)["amount_usd"].sum().sort_values("amount_usd", ascending=False)
                top3_accounts = " · ".join([f"<strong>{r['linked_account_name']}</strong> {format_usd(r['amount_usd'])}" for _, r in by_account.head(3).iterrows()])
                by_account_html = f'<div class="overview-breakdown-context" style="margin-bottom:8px;"><strong>Spend by linked account:</strong> {top3_accounts}</div>'

            if "category" in spend_df.columns and spend_df["category"].notna().any():
                by_cat = spend_df.groupby("category", as_index=False)["amount_usd"].sum().sort_values("amount_usd", ascending=False)
                total_cat = by_cat["amount_usd"].sum()
                if total_cat > 0:
                    segs = []
                    leg_items = []
                    for _, row in by_cat.iterrows():
                        cat = row["category"]
                        amt = float(row["amount_usd"])
                        pct = round(100 * amt / total_cat, 1)
                        color = CATEGORY_COLORS.get(cat, "#64748b")
                        segs.append(f'<div class="overview-breakdown-seg" style="width:{max(0.5, 100*amt/total_cat)}%;background:{color};" title="{cat} {format_usd(amt)}"></div>')
                        leg_items.append(
                            f'<span class="overview-breakdown-legend-item">'
                            f'<span class="overview-breakdown-legend-dot" style="background:{color};"></span>'
                            f'<span class="overview-breakdown-legend-label">{cat}</span>'
                            f'<span class="overview-breakdown-legend-value">{format_usd(amt)} ({pct}%)</span></span>'
                        )
                    bar_html = (
                        f'<div class="overview-breakdown-bar">{"".join(segs)}</div>'
                        f'<div class="overview-breakdown-legend">{"".join(leg_items)}</div>'
                    )
                else:
                    bar_html = ""
            else:
                covered_usd = float(by_service.loc[by_service["service"] == "Savings Plans (covered)", "amount_usd"].sum())
                ondemand_services = ["EC2", "EC2-Instances", "EC2-Other", "Savings Plans (on-demand)"]
                ondemand_usd = float(by_service.loc[by_service["service"].isin(ondemand_services), "amount_usd"].sum())
                total_breakdown = covered_usd + ondemand_usd
                if total_breakdown > 0:
                    covered_pct = round(100 * covered_usd / total_breakdown, 1)
                    ondemand_pct = round(100 * ondemand_usd / total_breakdown, 1)
                    bar_html = (
                        f'<div class="overview-breakdown-bar">'
                        f'<div class="overview-breakdown-seg" style="width:{max(0.5, 100*covered_usd/total_breakdown)}%;background:#10b981;" title="Covered by SP"></div>'
                        f'<div class="overview-breakdown-seg" style="width:{max(0.5, 100*ondemand_usd/total_breakdown)}%;background:#ea580c;" title="On-Demand"></div>'
                        f'</div>'
                        f'<div class="overview-breakdown-legend">'
                        f'<span class="overview-breakdown-legend-item"><span class="overview-breakdown-legend-dot" style="background:#10b981;"></span>'
                        f'<span class="overview-breakdown-legend-label">Covered by Savings Plans</span>'
                        f'<span class="overview-breakdown-legend-value">{format_usd(covered_usd)} ({covered_pct}%)</span></span>'
                        f'<span class="overview-breakdown-legend-item"><span class="overview-breakdown-legend-dot" style="background:#ea580c;"></span>'
                        f'<span class="overview-breakdown-legend-label">On-Demand</span>'
                        f'<span class="overview-breakdown-legend-value">{format_usd(ondemand_usd)} ({ondemand_pct}%)</span></span>'
                        f'</div>'
                    )
                else:
                    bar_html = ""
            context_parts = []
            if last_scan_at:
                context_parts.append("Re-run a scan from Setup to refresh.")
            context_html = " ".join(context_parts) if context_parts else "Other views (coming later)."
            st.markdown(
                f'''
                <div class="overview-breakdown-card">
                    <div class="overview-breakdown-title">Total cloud spend</div>
                    <div class="overview-breakdown-total">{format_usd(spend_total_usd)}</div>
                    <div class="overview-breakdown-context" style="margin-bottom:8px;"><strong>Top cost drivers:</strong> {top_drivers}</div>
                    {by_account_html}
                    {bar_html}
                    <div class="overview-breakdown-context">{context_html}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.caption("Other views (coming later).")

    # ----- Cost by team (chargeback summary - collapsible) -----
    if chargeback_summary:
        with st.expander("📋 See cost by team", expanded=False):
            st.markdown('<p class="overview-section">Cost by team</p>', unsafe_allow_html=True)
            top_items = " · ".join([f"<strong>{team}</strong> {format_usd(amt)}" for team, amt in chargeback_summary])
            st.markdown(
                f'''
                <div class="overview-breakdown-card">
                    <div class="overview-breakdown-title">Chargeback summary</div>
                    <div class="overview-breakdown-context" style="margin-bottom:8px;">{top_items}</div>
                    <div class="overview-breakdown-context">Allocated by cost allocation tags. Other views (coming later).</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.caption("Other views (coming later).")

# ----- Data & changes (minimal footer) -----
last_scan_display = (last_scan_at[:16] if last_scan_at and len(last_scan_at) > 16 else last_scan_at) or "Never"
footer_parts = [f"Last scan: {last_scan_display}"]
if has_prev and (prev_opt is not None or prev_act is not None):
    change_lines = []
    if prev_opt is not None:
        diff = optimization_potential - float(prev_opt)
        if diff > 0:
            change_lines.append(f'Waste ↑ {format_usd(diff)}')
        elif diff < 0:
            change_lines.append(f'Waste ↓ {format_usd(-diff)}')
    if prev_act is not None:
        d = action_count - int(prev_act)
        if d > 0:
            change_lines.append(f'Actions ↑ {d}')
        elif d < 0:
            change_lines.append(f'Actions ↓ {-d}')
    if change_lines:
        footer_parts.append(" · ".join(change_lines))
else:
    footer_parts.append("Run another scan from Setup to see changes")
if total_saved_to_date > 0:
    footer_parts.append(f"Wins: {format_usd(total_saved_to_date)} saved to date")
st.caption(" · ".join(footer_parts))

# ----- Disclaimer (estimates / recommendations) -----
render_waste_policy_footer()

# ----- Quick links (wedge: one number, one list; All Waste hidden from nav) -----
st.markdown("---")
st.markdown("**Quick links:** ", unsafe_allow_html=True)
try:
    link_col1, link_col2 = st.columns(2)
    with link_col1:
        st.page_link("pages/0_Setup.py", label="Setup", icon="🔐", help="Connect AWS and run scans.")
    with link_col2:
        st.page_link("pages/3_Settings.py", label="Settings", icon="⚙️", help="Region preference and data source.")
except Exception:
    st.markdown("- **Setup** · **Settings**")
st.caption("Setup · Settings.")
