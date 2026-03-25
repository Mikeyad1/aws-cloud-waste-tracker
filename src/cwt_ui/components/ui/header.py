from __future__ import annotations

import streamlit as st

from .shared_css import load_beautiful_css


def render_page_header(
    title: str,
    subtitle: str | None = None,
    icon: str | None = None,
    *,
    data_source: str | None = None,
    last_scan_at: str | None = None,
) -> None:
    """
    Render a standardized gradient header consistent across all pages.

    Args:
        title: Main heading text.
        subtitle: Optional secondary line of text below the title.
        icon: Optional emoji/icon prefix for the title.
        data_source: Optional "synthetic" or "real" to show persistent indicator (Synthetic / Live).
        last_scan_at: Optional timestamp string for "Last scan: …" when data is live.
    """
    load_beautiful_css()

    heading = f"{icon} {title}" if icon else title
    subtitle_html = f'<p class="beautiful-header-subtitle">{subtitle}</p>' if subtitle else ""

    # Persistent data source indicator — centered, clear wording
    indicator_html = ""
    if data_source is not None and data_source != "none":
        if data_source == "synthetic":
            indicator_text = "Showing demo data"
        else:
            if last_scan_at:
                scan_display = last_scan_at[:16] if len(last_scan_at or "") > 16 else (last_scan_at or "Never")
                indicator_text = f"Live data from your account · Last scan: {scan_display}"
            else:
                indicator_text = "Live data from your account"
        indicator_html = f'<div class="header-data-source-pill">{indicator_text}</div>'

    st.markdown(
        f"""
        <style>
            .beautiful-header {{
                background:
                    radial-gradient(circle at top left, rgba(56,189,248,0.28), transparent 55%),
                    linear-gradient(145deg, #020617, #020617);
                padding: 1.4rem 1.6rem 1.6rem 1.6rem;
                border-radius: 18px;
                margin-bottom: 1.8rem;
                color: #e5e7eb;
                text-align: left;
                box-shadow: 0 18px 46px rgba(15,23,42,0.9);
                position: relative;
                overflow: hidden;
            }}
            .beautiful-header h1 {{
                font-size: 1.5rem;
                font-weight: 650;
                margin: 0;
                letter-spacing: -0.02em;
            }}
            .beautiful-header-subtitle {{
                font-size: 0.95rem;
                margin: 0.4rem 0 0 0;
                color: #9ca3af;
                max-width: 32rem;
            }}
            .header-data-source-pill {{
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.25rem 0.7rem;
                border-radius: 999px;
                border: 1px solid #1f2937;
                background: rgba(15, 23, 42, 0.9);
                font-size: 0.75rem;
                color: #9ca3af;
                margin-top: 0.75rem;
            }}
        </style>
        <div class="beautiful-header">
            <h1>{heading}</h1>
            {subtitle_html}
            {indicator_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

