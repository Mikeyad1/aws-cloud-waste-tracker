# src/cwt_ui/components/tables.py
from __future__ import annotations
import pandas as pd
import streamlit as st
from typing import Callable, Optional

Formatter = Callable[[object], str]
Highlighter = Callable[[object], str]  # returns an emoji or short marker

def _reorder_columns(df: pd.DataFrame, column_order: Optional[list[str]]) -> pd.DataFrame:
    if not column_order:
        return df
    existing = [c for c in column_order if c in df.columns]
    tail = [c for c in df.columns if c not in existing]
    return df[existing + tail]

def _apply_numeric_formatters(
    df: pd.DataFrame,
    numeric_formatters: Optional[dict[str, Formatter]]
) -> pd.DataFrame:
    if not numeric_formatters:
        return df
    df = df.copy()
    for col, fmt in numeric_formatters.items():
        if col in df.columns:
            try:
                df[col] = df[col].apply(fmt)
            except Exception:
                # If formatting fails, keep original values
                pass
    return df

def _apply_highlight_rules(
    df: pd.DataFrame,
    highlight_rules: Optional[dict[str, Highlighter]]
) -> pd.DataFrame:
    """
    Streamlit's st.dataframe does not support CSS-style highlighting.
    As a pragmatic MVP, we append an extra helper column for each rule,
    placing an emoji/marker next to the original column for visual emphasis.
    Example: for column 'recommendation' we may add 'recommendation_flag' with 🔴/🟢.
    """
    if not highlight_rules:
        return df
    df = df.copy()
    for col, fn in highlight_rules.items():
        if col in df.columns:
            flag_col = f"{col}_flag"
            try:
                df[flag_col] = df[col].apply(fn)
            except Exception:
                # On failure, leave the flag column empty
                df[flag_col] = ""
    return df

def render(
    df: pd.DataFrame,
    *,
    column_order: Optional[list[str]] = None,
    numeric_formatters: Optional[dict[str, Formatter]] = None,
    highlight_rules: Optional[dict[str, Highlighter]] = None
) -> None:
    """
    Render a DataFrame with:
      - optional column ordering
      - optional value formatting (currency, percent, GB, etc.)
      - optional "flags" columns based on highlight rules (emoji markers)
    Notes:
      - st.dataframe does not support CSS highlighting, so we use extra *_flag columns.
      - NaN values are filled with "-" for a cleaner display.
    """
    if df is None or df.empty:
        st.info("No data to display.")
        return

    # Work on a copy to avoid mutating caller's frame
    _df = df.copy()

    # If there is a "status" or "recommendation" column, ensure it's visible early
    # (Helpful default before reordering)
    default_priority = []
    for key in ("status", "recommendation"):
        if key in _df.columns:
            default_priority.append(key)
    if default_priority:
        others = [c for c in _df.columns if c not in default_priority]
        _df = _df[default_priority + others]

    # Apply formatting and flags
    _df = _apply_numeric_formatters(_df, numeric_formatters)
    _df = _apply_highlight_rules(_df, highlight_rules)

    # Reorder columns last (caller wins)
    _df = _reorder_columns(_df, column_order)

    # Replace NaN for cleaner UI
    _df = _df.fillna("-")

    # Display
    st.dataframe(_df, use_container_width=True)
