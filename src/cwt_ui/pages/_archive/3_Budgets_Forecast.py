# pages/3_Budgets_Forecast.py — Budgets & Forecast
from __future__ import annotations

import sys
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import streamlit as st

from cwt_ui.components.ui.header import render_page_header
from cwt_ui.services.budgets_service import get_budgets
from cwt_ui.utils.money import format_usd

st.set_page_config(page_title="Budgets & Forecast", page_icon="📈", layout="wide")

# Card styles (match Overview / Spend)
st.markdown("""
<style>
    .budget-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .budget-card-header { font-size: 0.9rem; font-weight: 600; color: #f1f5f9; margin-bottom: 4px; }
    .budget-card-scope { font-size: 0.75rem; color: #94a3b8; margin-bottom: 12px; }
    .budget-card-row { display: flex; flex-wrap: wrap; gap: 16px 24px; margin-bottom: 8px; }
    .budget-card-label { font-size: 0.7rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .budget-card-value { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
    .budget-status { display: inline-block; font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; text-transform: uppercase; }
    .budget-status.on_track { background: #064e3b; color: #6ee7b7; }
    .budget-status.at_risk { background: #78350f; color: #fde68a; }
    .budget-status.over { background: #7f1d1d; color: #fecaca; }
    .budget-progress { height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden; margin: 12px 0; }
    .budget-progress-bar { height: 100%; border-radius: 4px; transition: width 0.3s; }
    .budget-data-badge { display: inline-block; background: #1e3a5f; color: #7dd3fc; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; margin-left: 8px; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Budgets & Forecast",
    subtitle="Budgets, forecasts, and variance.",
    icon="📈",
)

data_source = st.session_state.get("data_source", "none")
budgets = get_budgets()

if data_source == "synthetic":
    st.markdown('<span class="budget-data-badge">Using synthetic data</span>', unsafe_allow_html=True)
    st.caption("Budgets are sample targets. Connect CUR to define real budgets.")

if not budgets:
    st.info(
        "**No budgets yet.** Load **synthetic data** from Overview to see sample budgets (Engineering, Production, Total AWS). "
        "With real spend data, you'll define budgets per account or tag."
    )
    st.caption("Budgets & Forecast requires spend data. Load synthetic data or connect CUR.")
    st.stop()

st.markdown("### Budget list")
st.caption("Consumed % = spend to date vs budget. Status: on track (<80%), at risk (80–100%), over (>100%).")

for b in budgets:
    pct_clamp = min(100.0, b.consumed_pct)
    bar_color = "#22c55e" if b.status == "on_track" else "#f59e0b" if b.status == "at_risk" else "#ef4444"
    status_label = "On track" if b.status == "on_track" else "At risk" if b.status == "at_risk" else "Over"
    st.markdown(
        f'''
        <div class="budget-card">
            <div class="budget-card-header">{b.name}</div>
            <div class="budget-card-scope">Scope: {b.scope} · Period: {b.period}</div>
            <div class="budget-progress">
                <div class="budget-progress-bar" style="width:{pct_clamp}%;background:{bar_color};"></div>
            </div>
            <div class="budget-card-row">
                <span><span class="budget-card-label">Target</span><br><span class="budget-card-value">{format_usd(b.amount)}</span></span>
                <span><span class="budget-card-label">Consumed</span><br><span class="budget-card-value">{format_usd(b.consumed)} ({b.consumed_pct:.1f}%)</span></span>
                <span><span class="budget-card-label">Status</span><br><span class="budget-status {b.status}">{status_label}</span></span>
                <span><span class="budget-card-label">Forecast (period end)</span><br><span class="budget-card-value">{format_usd(b.forecast)}</span></span>
            </div>
            <div style="font-size:0.8rem;color:#64748b;">At current run rate, period end = {format_usd(b.forecast)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown("### How forecasts work")
st.caption(
    "Forecast assumes spend continues at the same rate. With synthetic data we simulate ~15 days elapsed in a 30-day period. "
    "With real CUR data, we'll use actual date ranges."
)
try:
    st.page_link("pages/2_Spend.py", label="View spend breakdown →", icon="💰")
except Exception:
    st.markdown("[View **Spend** breakdown →](pages/2_Spend.py)")
