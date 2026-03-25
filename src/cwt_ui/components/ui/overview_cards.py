# Cards matching Overview page style (dark gradient, compact, scannable)
from __future__ import annotations

import html
import streamlit as st


def render_sec_card(label: str, value: str, meta: str = "") -> None:
    """
    Render a secondary KPI card matching Overview page style.
    Uses overview-sec-card CSS (must be loaded by parent page).
    """
    label_safe = html.escape(label)
    value_safe = html.escape(str(value))
    meta_html = f'<div class="overview-sec-meta">{html.escape(meta)}</div>' if meta else ""
    st.markdown(
        f'''
        <div class="overview-sec-card">
            <div class="overview-sec-label">{label_safe}</div>
            <div class="overview-sec-value">{value_safe}</div>
            {meta_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )
