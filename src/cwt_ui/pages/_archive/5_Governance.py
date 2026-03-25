# pages/5_Governance.py — Governance
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
from cwt_ui.services.governance_service import (
    get_open_violations_count,
    get_policies,
    get_violations,
    acknowledge_violation,
)

st.set_page_config(page_title="Governance", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .gov-card {
        background: linear-gradient(145deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .gov-card-label { font-size: 0.7rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .gov-card-value { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
    .gov-severity { display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; text-transform: uppercase; margin-left: 8px; }
    .gov-severity.critical { background: #7f1d1d; color: #fecaca; }
    .gov-severity.high { background: #78350f; color: #fde68a; }
    .gov-severity.medium { background: #1e3a5f; color: #93c5fd; }
    .gov-data-badge { display: inline-block; background: #1e3a5f; color: #7dd3fc; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; margin-left: 8px; }
</style>
""", unsafe_allow_html=True)

render_page_header(
    title="Governance",
    subtitle="Policies, violations, and approvals.",
    icon="🛡️",
)

data_source = st.session_state.get("data_source", "none")
if data_source == "synthetic":
    st.markdown('<span class="gov-data-badge">Using synthetic data</span>', unsafe_allow_html=True)
    st.caption("Violations derived from EC2 scan. Connect real policy engine for production.")

policies = get_policies()
violations = get_violations()

if not violations:
    st.info(
        "**No policy violations yet.** Load **synthetic data** from Overview to see sample policies and violations. "
        "With real scan data, violations are derived from EC2 (and eventually other resources)."
    )
    st.caption("Governance requires scan data. Load synthetic data or run a scan from Setup.")
    st.stop()

# ----- Policies list -----
st.markdown("### Policies")
st.caption("Open violation count per policy.")

for p in policies:
    sev_class = p.severity
    st.markdown(
        f'''
        <div class="gov-card">
            <div class="gov-card-label">{p.name}</div>
            <div class="gov-card-value">
                {p.violation_count} open
                <span class="gov-severity {sev_class}">{p.severity}</span>
            </div>
            <div style="font-size:0.8rem;color:#64748b;margin-top:4px;">Type: {p.policy_type}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ----- Violations table -----
st.markdown("### Violations")
st.caption("Resource ID, policy, account, date, status. Click Acknowledge to mark as reviewed.")

# Filter by status
status_filter = st.radio(
    "Filter by status",
    options=["All", "Open", "Acknowledged"],
    index=0,
    horizontal=True,
    key="gov_status_filter",
)
filtered = [v for v in violations if status_filter == "All" or v.status == status_filter]

# Filter by policy
policy_ids = sorted(set(v.policy_id for v in violations))
policy_filter = st.selectbox(
    "Filter by policy",
    options=["All"] + policy_ids,
    key="gov_policy_filter",
    format_func=lambda x: next((v.policy_name for v in violations if v.policy_id == x), x) if x != "All" else "All",
)
if policy_filter != "All":
    filtered = [v for v in filtered if v.policy_id == policy_filter]

if not filtered:
    st.warning("No violations match the selected filters.")
else:
    # Table view
    table_data = [
        {
            "Resource ID": v.resource_id,
            "Policy": v.policy_name,
            "Account": v.account,
            "Region": v.region,
            "Date": v.date,
            "Status": v.status,
            "Action": v.action_hint,
        }
        for v in filtered
    ]
    table_df = pd.DataFrame(table_data)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    # Acknowledge: one button per open violation
    open_filtered = [v for v in filtered if v.status == "Open"]
    if open_filtered:
        st.markdown("**Acknowledge**")
        for v in open_filtered:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.caption(f"{v.resource_id} — {v.action_hint}")
            with col_b:
                if st.button("Acknowledge", key=f"ack_{v.id}"):
                    acknowledge_violation(v.id)
                    st.rerun()

    st.markdown("---")
    st.caption("Acknowledged violations are stored in session state. Reload page or synthetic data to reset.")
