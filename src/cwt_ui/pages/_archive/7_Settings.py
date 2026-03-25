# pages/7_Settings.py — Settings
from __future__ import annotations

import sys
from pathlib import Path

for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parent.parents]:
    if (p / "src").exists() and str(p / "src") not in sys.path:
        sys.path.insert(0, str(p / "src"))
        break

import streamlit as st
from cwt_ui.components.ui.header import render_page_header

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

render_page_header(
    title="Settings",
    subtitle="App preferences, notifications, and access.",
    icon="⚙️",
)

st.info("**Coming soon.** Currency, date format, default time range, notifications (email/Slack), and users & access will appear here.")
