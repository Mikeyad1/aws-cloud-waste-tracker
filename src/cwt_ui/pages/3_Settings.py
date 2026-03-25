# pages/3_Settings.py — Minimal Settings (MVP command 26: region, data source, link to Setup)
from __future__ import annotations

import os
import sys
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import streamlit as st

from cwt_ui.components.ui.header import render_page_header
from cwt_ui.utils.money import format_usd
from cwt_ui.utils.resolved_persistence import load_excluded, save_excluded

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

render_page_header(
    title="Settings",
    subtitle="Region preference and data source.",
    icon="⚙️",
    data_source=st.session_state.get("data_source", "none"),
    last_scan_at=st.session_state.get("last_scan_at", ""),
)

# Link to Setup (Connect to find waste)
st.markdown("**Connect to find waste**")
try:
    st.page_link("pages/0_Setup.py", label="Connect and run a scan →", icon="🔐", help="Configure AWS and run a scan to see your waste number.")
except Exception:
    st.markdown("[**Connect and run a scan** →](pages/0_Setup.py)")
st.caption("Configure credentials and run a scan from Setup to get your live waste number.")
st.markdown("---")

# Data source (read-only label)
st.markdown("**Data source**")
data_source = st.session_state.get("data_source", "none")
if data_source == "synthetic":
    source_label = "Demo data (synthetic)"
else:
    source_label = "Live scan"
st.info(f"**{source_label}** — To switch to live data: open **Setup** and run a scan. To use demo data: open **Your waste** and click **Load synthetic data**.")
st.markdown("---")

# Selected regions for scan (read-only; actual selection is in Setup)
st.markdown("**Regions for scan**")
scan_regions = st.session_state.get("scan_regions")
if scan_regions and len(scan_regions) > 0:
    st.caption(f"**{len(scan_regions)} region(s)** selected: {', '.join(sorted(scan_regions)[:5])}{'…' if len(scan_regions) > 5 else ''}. Change in **Setup** before running a scan.")
else:
    st.caption("**Auto-discover** — Scan will use all enabled regions. To pick specific regions, open **Setup** and choose regions before running a scan.")
st.markdown("---")

# Default AWS region (used by Setup and scans)
DEFAULT_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-west-2",
    "eu-central-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
]
current = st.session_state.get("aws_default_region", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
options = [r for r in DEFAULT_REGIONS if r != current]
options = [current] + options
idx = 0
new_region = st.selectbox(
    "Default AWS region",
    options=options,
    index=0,
    key="settings_default_region",
    help="Default region for scans and resource discovery. You can override per scan in Setup.",
)
if new_region != current:
    st.session_state["aws_default_region"] = new_region
    st.success(f"Default region set to **{new_region}**. It will be used on the next scan.")
else:
    st.session_state["aws_default_region"] = new_region

# Excluded resources (hide from list; restore here)
st.markdown("---")
st.markdown("**Excluded from list**")
if "excluded_recommendations" not in st.session_state:
    st.session_state["excluded_recommendations"] = load_excluded()
excluded_list = st.session_state["excluded_recommendations"]

def _excluded_key(r):
    return (str(r.get("Service", "")), str(r.get("Resource", "")))

if excluded_list:
    st.caption(f"**{len(excluded_list)}** resource(s) are hidden from recommendations and excluded from your waste total. Restore to show them again.")
    for i, ex in enumerate(excluded_list):
        restore_key = f"restore_excluded_{ex.get('Service','')}_{ex.get('Resource','')}_{i}".replace(" ", "_").replace("|", "_")[:80]
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"**{ex.get('Resource', '—')}** · {format_usd(float(ex.get('Waste ($/mo)', 0)))} · {ex.get('Service', '—')}")
        with c2:
            if st.button("Restore", key=restore_key):
                new_list = [x for x in excluded_list if _excluded_key(x) != _excluded_key(ex)]
                st.session_state["excluded_recommendations"] = new_list
                save_excluded(new_list)
                st.rerun()
else:
    st.caption("No excluded resources. Use **Exclude** on a recommendation (Your waste or Waste full list) to hide it from the list and waste total.")
