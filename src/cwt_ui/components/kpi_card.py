from __future__ import annotations

from typing import Optional

import streamlit as st


def render_kpi(label: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None) -> None:
    """
    Render a standardized KPI metric card.

    Args:
        label: KPI title.
        value: Primary value to display (already formatted).
        delta: Optional delta/secondary value string.
        help_text: Optional tooltip/help string.
    """
    metric_kwargs: dict[str, str] = {"label": label, "value": value}
    if delta is not None:
        metric_kwargs["delta"] = delta

    container = st.container()
    with container:
        st.metric(**metric_kwargs)
        if help_text:
            st.caption(help_text)

