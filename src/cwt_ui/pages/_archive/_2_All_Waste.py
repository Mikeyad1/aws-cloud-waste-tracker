# pages/_archive/_2_All_Waste.py — Hidden from nav (in subdir). Full list now inline on Waste page.
# Wedge: one number, one list. Kept for potential future use (tabs/filters/commitment).
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
from cwt_ui.components.optimization_tabs import render_commitment_tab
from cwt_ui.utils.money import format_usd
from cwt_ui.utils.resolved_persistence import load_resolved, load_excluded, save_resolved, save_excluded
from cwt_ui.utils.unified_recommendations import build_unified_what_to_turn_off

st.set_page_config(page_title="Waste (full list)", page_icon="🔧", layout="wide")

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
    div[data-testid="stTabs"] { margin-top: 12px; margin-bottom: 8px; }
    .waste-summary-row { display: flex; gap: 16px; align-items: stretch; flex-wrap: wrap; margin-bottom: 8px; }
    .waste-summary-row .overview-sec-card { flex: 1 1 0; min-width: 200px; margin-bottom: 0; display: flex; flex-direction: column; }
    .waste-summary-row .overview-sec-meta { margin-top: auto; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Waste (full list)",
    subtitle="All recommendations to lower your waste — compute, containers, serverless, commitments.",
    icon="🔧",
    data_source=st.session_state.get("data_source", "none"),
    last_scan_at=st.session_state.get("last_scan_at", ""),
)

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

total_savings_raw = (
    _sum_potential(ec2_df) + _sum_potential(lambda_df) + _sum_potential(fargate_df)
    + _sum_potential(storage_df) + _sum_potential(dt_df) + _sum_potential(db_df)
)
if "resolved_recommendations" not in st.session_state:
    st.session_state["resolved_recommendations"] = load_resolved()
if "excluded_recommendations" not in st.session_state:
    st.session_state["excluded_recommendations"] = load_excluded()
_resolved_for_summary = st.session_state["resolved_recommendations"]
_excluded_for_summary = st.session_state["excluded_recommendations"]
resolved_waste_summary = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in _resolved_for_summary)
excluded_waste_summary = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in _excluded_for_summary)
total_savings = max(0.0, total_savings_raw - resolved_waste_summary - excluded_waste_summary)

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

st.markdown('<p class="overview-section">Waste summary</p>', unsafe_allow_html=True)
total_saved_to_date = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in _resolved_for_summary)
st.markdown(
    f'''
    <div class="waste-summary-row">
        <div class="overview-sec-card">
            <div class="overview-sec-label">Total waste</div>
            <div class="overview-sec-value">{format_usd(total_savings)}</div>
            <div class="overview-sec-meta">Across EC2, Fargate, Lambda, Storage, Data Transfer, Databases.</div>
        </div>
        <div class="overview-sec-card">
            <div class="overview-sec-label">SP coverage by product</div>
            <div class="overview-sec-value">{sp_summary}</div>
            <div class="overview-sec-meta">EC2 Instance SP + Compute SP.</div>
        </div>
        <div class="overview-sec-card">
            <div class="overview-sec-label">Recommendations</div>
            <div class="overview-sec-value">{int(action_count)}</div>
            <div class="overview-sec-meta">Actionable stop, rightsize, or downsize suggestions.</div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)
if total_saved_to_date > 0:
    st.caption(f"**Wins:** {format_usd(total_saved_to_date)} saved to date from items you marked as resolved.")

unified_rows_raw = build_unified_what_to_turn_off(
    ec2_df if ec2_df is not None and not ec2_df.empty else None,
    lambda_df if lambda_df is not None and not lambda_df.empty else None,
    fargate_df if fargate_df is not None and not fargate_df.empty else None,
    storage_df if storage_df is not None and not storage_df.empty else None,
    dt_df if dt_df is not None and not dt_df.empty else None,
    db_df if db_df is not None and not db_df.empty else None,
)
resolved_list = st.session_state["resolved_recommendations"]
excluded_list = st.session_state["excluded_recommendations"]

def _resolved_key(row: dict) -> tuple:
    return (str(row.get("Service", "")), str(row.get("Resource", "")))

def _filter_unresolved(rows: list[dict], resolved: list[dict]) -> list[dict]:
    keys = {_resolved_key(r) for r in resolved}
    return [r for r in rows if _resolved_key(r) not in keys]

def _filter_not_excluded(rows: list[dict], excluded: list[dict]) -> list[dict]:
    keys = {_resolved_key(r) for r in excluded}
    return [r for r in rows if _resolved_key(r) not in keys]

for i, r in enumerate(unified_rows_raw):
    r["_stable_idx"] = i
unified_rows = _filter_not_excluded(unified_rows_raw, excluded_list) if unified_rows_raw else []
unified_rows = _filter_unresolved(unified_rows, resolved_list) if unified_rows else []
has_data_but_all_resolved = bool(unified_rows_raw and not unified_rows)

def _render_recommendations_with_resolve(rows: list[dict], key_prefix: str) -> None:
    if not rows:
        return
    for idx, r in enumerate(rows):
        key_safe = f"{key_prefix}_{r.get('_stable_idx', idx)}"
        with st.container():
            rec_col, btn_col = st.columns([5, 1])
            with rec_col:
                st.markdown(
                    f"**{r.get('Resource', '—')}** · {format_usd(float(r.get('Waste ($/mo)', 0) or 0))} · "
                    f"{r.get('Severity', '—')} · {r.get('Fix steps', '—')} · {r.get('Service', '—')} · {r.get('Action', '—')}"
                )
                st.caption(f"*Why:* {r.get('Reason', '—')}")
            with btn_col:
                if st.button("Mark as resolved", key=key_safe, type="secondary", use_container_width=True):
                    item = {"Service": r.get("Service", ""), "Resource": r.get("Resource", ""), "Waste ($/mo)": float(r.get("Waste ($/mo)", 0) or 0), "Fix steps": r.get("Fix steps", "")}
                    st.session_state["resolved_recommendations"].append(item)
                    save_resolved(st.session_state["resolved_recommendations"])
                    st.rerun()
                key_excl = f"{key_prefix}_excl_{r.get('_stable_idx', idx)}"
                if st.button("Exclude", key=key_excl, use_container_width=True, help="Hide from list. Restore in Settings."):
                    excl_item = {"Service": r.get("Service", ""), "Resource": r.get("Resource", ""), "Waste ($/mo)": float(r.get("Waste ($/mo)", 0) or 0)}
                    st.session_state["excluded_recommendations"].append(excl_item)
                    save_excluded(st.session_state["excluded_recommendations"])
                    st.rerun()
        st.divider()

def _apply_sort(rows: list, sort_option: str) -> list:
    if sort_option == "Waste (high first)":
        return sorted(rows, key=lambda x: float(x.get("Waste ($/mo)", 0) or 0), reverse=True)
    if sort_option == "Waste (low first)":
        return sorted(rows, key=lambda x: float(x.get("Waste ($/mo)", 0) or 0), reverse=False)
    if sort_option == "Service (A–Z)":
        return sorted(rows, key=lambda x: (str(x.get("Service") or ""), -float(x.get("Waste ($/mo)", 0) or 0)))
    rows = sorted(rows, key=lambda x: -float(x.get("Waste ($/mo)", 0) or 0))
    return sorted(rows, key=lambda x: str(x.get("Service") or ""), reverse=True)

def _safe_render_tab(render_fn, tab_name: str) -> None:
    try:
        render_fn()
    except Exception as e:
        st.error(f"Error loading **{tab_name}**: {e}")
        with st.expander("Technical details", expanded=False):
            st.code(traceback.format_exc())

tab_all, tab_by_action, tab_commitment = st.tabs(["All", "By action", "Commitment"])

with tab_all:
    st.markdown("Recommendations to lower it. Filter by service or action; sort by waste or service.")
    if unified_rows:
        services_present = sorted({r.get("Service", "") for r in unified_rows if r.get("Service")})
        action_options = ["All", "Stop or remove", "Right-size", "Move or change tier"]
        filter_col, sort_col = st.columns([2, 1])
        with filter_col:
            selected_services = st.multiselect("Filter by service", options=services_present, default=services_present, key="all_tab_services")
            selected_action = st.selectbox("Action", options=action_options, key="all_tab_action", help="Focus on one type of fix.")
        with sort_col:
            sort_option = st.selectbox("Sort by", options=["Waste (high first)", "Waste (low first)", "Service (A–Z)", "Service (Z–A)"], key="all_tab_sort")
        rows_all = [r for r in unified_rows if (r.get("Service") or "") in selected_services]
        if selected_action != "All":
            rows_all = [r for r in rows_all if r.get("Action") == selected_action]
        rows_all = _apply_sort(rows_all, sort_option)
        total_waste_all = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in rows_all)
        st.caption(f"**{len(rows_all)}** recommendations · **{format_usd(total_waste_all)}** total waste")
        if rows_all:
            _render_recommendations_with_resolve(rows_all, "all")
        else:
            st.info("No recommendations match the selected filters.")
        if resolved_list:
            with st.expander(f"Resolved this session ({len(resolved_list)})", expanded=False):
                for i, res in enumerate(resolved_list):
                    undo_key = f"undo_all_{res.get('Service','')}_{res.get('Resource','')}_{i}".replace(" ", "_").replace("|", "_")[:80]
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.caption(f"**{res.get('Resource', '—')}** · {format_usd(float(res.get('Waste ($/mo)', 0)))} · {res.get('Service', '—')} · {res.get('Fix steps', '—')}")
                    with c2:
                        if st.button("Undo", key=undo_key):
                            new_list = [x for x in resolved_list if _resolved_key(x) != _resolved_key(res)]
                            st.session_state["resolved_recommendations"] = new_list
                            save_resolved(new_list)
                            st.rerun()
    elif has_data_but_all_resolved:
        st.info("All recommendations are marked as resolved. Un-resolve from the list below or run a new scan.")
        if resolved_list:
            with st.expander(f"Resolved this session ({len(resolved_list)})", expanded=True):
                for i, res in enumerate(resolved_list):
                    undo_key = f"undo_all_{res.get('Service','')}_{res.get('Resource','')}_{i}".replace(" ", "_").replace("|", "_")[:80]
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
        st.info("No recommendations with positive savings. Load **synthetic data** from Your waste or run a scan from **Setup**.")

with tab_by_action:
    st.caption("Focus on one type of fix. Same list, filtered by action.")
    sub_stop, sub_right, sub_move = st.tabs(["Stop or remove", "Right-size", "Move or change tier"])
    for sub_tab, action_label, key_suffix in [
        (sub_stop, "Stop or remove", "stop"),
        (sub_right, "Right-size", "right"),
        (sub_move, "Move or change tier", "move"),
    ]:
        with sub_tab:
            rows_action = [r for r in unified_rows if r.get("Action") == action_label]
            rows_action = _apply_sort(rows_action, "Waste (high first)")
            total_action = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in rows_action)
            st.caption(f"**{len(rows_action)}** recommendations · **{format_usd(total_action)}** waste")
            if rows_action:
                _render_recommendations_with_resolve(rows_action, f"action_{key_suffix}")
            else:
                st.info(f"No recommendations for **{action_label}**.")

with tab_commitment:
    _safe_render_tab(render_commitment_tab, "Commitment")
