"""
Reusable waste number component for displaying "Your waste this month: $X"
with consistent styling across the application.
"""

from __future__ import annotations

import streamlit as st

from cwt_ui.utils.money import format_usd


def render_waste_number(
    waste_amount: float | None,
    period: str = "this month",
    subtitle: str | None = None,
    show_subtitle: bool = True,
    data_source_hint: str | None = None,
) -> None:
    """
    Render a prominent waste number display with consistent styling.

    Args:
        waste_amount: The waste amount in USD (float) or None if not available.
        period: Time period description (default: "this month").
        subtitle: Optional custom subtitle. If None, uses default subtitle.
        show_subtitle: Whether to show the subtitle (default: True).
        data_source_hint: Optional one-line label under the subtitle (e.g. "From your first sync." or "Demo data — run a scan in Setup for your real number.").
    """
    # Load CSS styles
    st.markdown("""
    <style>
        /* Waste number hero component */
        .waste-number-hero {
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.20), transparent 55%),
                linear-gradient(145deg, #020617, #020617);
            border: 1px solid #1f2937;
            border-radius: 18px;
            padding: 20px 22px 18px 22px;
            margin-bottom: 18px;
            box-shadow: 0 18px 46px rgba(15, 23, 42, 0.9);
        }
        .waste-number-top {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 20px;
            flex-wrap: wrap;
        }
        .waste-number-main {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .waste-number-label {
            font-size: 0.78rem;
            font-weight: 650;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .waste-number-value {
            font-size: 2.4rem;
            font-weight: 800;
            color: #22d3ee;
            line-height: 1.15;
            letter-spacing: -0.03em;
        }
        .waste-number-subtitle {
            font-size: 0.86rem;
            color: #9ca3af;
            margin-top: 10px;
        }
        .waste-number-data-source {
            font-size: 0.78rem;
            color: #6b7280;
            margin-top: 4px;
            font-style: italic;
        }
        .waste-number-yearly {
            padding: 8px 10px;
            border-radius: 12px;
            border: 1px solid #1f2937;
            background: rgba(15, 23, 42, 0.9);
            min-width: 180px;
        }
        .waste-number-yearly-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: #9ca3af;
            margin-bottom: 2px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .waste-number-yearly-value {
            font-size: 1rem;
            font-weight: 600;
            color: #e5e7eb;
            white-space: nowrap;
        }
    </style>
    """, unsafe_allow_html=True)

    # Format the waste amount
    if waste_amount is None or waste_amount == 0:
        display_value = "—"
        yearly_value = None
    else:
        display_value = format_usd(waste_amount)
        yearly_value = format_usd(waste_amount * 12)

    # Default subtitle if not provided
    if subtitle is None:
        subtitle = "Monthly waste you can eliminate. See recommendations below."

    # Build the HTML in one pass so Streamlit doesn't show raw tags
    subtitle_html = f'<div class="waste-number-subtitle">{subtitle}</div>' if show_subtitle else ""
    data_source_html = (
        f'<div class="waste-number-data-source">{data_source_hint}</div>' if data_source_hint else ""
    )
    if yearly_value is not None:
        yearly_block = (
            '<div class="waste-number-yearly">'
            '<div class="waste-number-yearly-label">Potential savings if fixed</div>'
            '<div class="waste-number-yearly-value">' + yearly_value + ' / year</div>'
            '</div>'
        )
    else:
        yearly_block = ""

    hero_html = (
        '<div class="waste-number-hero">'
        '<div class="waste-number-top">'
        '<div class="waste-number-main">'
        '<div class="waste-number-label">Your waste ' + period + '</div>'
        '<div class="waste-number-value">' + display_value + '</div>'
        '</div>'
        + yearly_block +
        '</div>'
        + subtitle_html
        + data_source_html
        + '</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)
