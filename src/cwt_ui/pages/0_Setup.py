# pages/0_Setup.py — Setup (connect to find waste)
from __future__ import annotations

import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
for candidate in [CURRENT_DIR, *CURRENT_DIR.parents]:
    candidate_src = candidate / "src"
    if candidate_src.exists():
        if str(candidate_src) not in sys.path:
            sys.path.insert(0, str(candidate_src))
        break

import streamlit as st
from cwt_ui.components.ui.header import render_page_header
from cwt_ui.components.setup_aws_content import render_aws_setup_content

st.set_page_config(page_title="Connect to find waste", page_icon="🔐", layout="wide")

render_page_header(
    title="Connect to find waste",
    subtitle="See your waste in one sync.",
    icon="🔐",
    data_source=st.session_state.get("data_source", "none"),
    last_scan_at=st.session_state.get("last_scan_at", ""),
)

st.caption("Connect once, run one scan — you’ll see your number.")

st.markdown("### Connect AWS")
render_aws_setup_content()

st.markdown("---")
st.markdown("### More data (coming later)")
with st.expander("Billing data: Cost Explorer vs CUR", expanded=False):
    st.markdown("""
    **Today:** With `ce:GetCostAndUsage` on your IAM role, we can query the **Cost Explorer API** for spend summaries where AWS exposes them for that account (see **Which AWS account** on Connect AWS).

    **Later:** For deeper FinOps (line items, chargeback, allocation tags at scale), many teams add **CUR (Cost and Usage Report)** to S3.

    | Source | What it provides | Status |
    |--------|------------------|--------|
    | **Cost Explorer API** | Spend by time range, service, and more (API-level). | In use (with IAM permission) |
    | **CUR** | Detailed rows in S3; best for allocation and history. | Planned |
    | **Manual CE export** | Upload CSV for a quick view without CUR. | Planned |

    **CUR** remains the gold standard for granular FinOps; **Cost Explorer** is the lighter path we use first.
    """)
    st.caption("Enable cost allocation tags in AWS Billing if you plan to use CUR or tag-based views later.")

st.markdown("---")
st.markdown("### Other clouds")
with st.expander("GCP / Azure", expanded=False):
    st.info("**Coming later.** Google Cloud and Microsoft Azure connections will be added here.")
