# Chargeback service: allocation by Team, Environment, CostCenter.
from __future__ import annotations

import pandas as pd
import streamlit as st


ALLOCATION_DIMENSIONS = [
    ("team", "Team"),
    ("environment", "Environment"),
    ("cost_center", "Cost Center"),
]


def get_chargeback_data() -> tuple[pd.DataFrame, float] | None:
    """
    Return (spend_df with tags, total_usd) for chargeback.
    Only works with synthetic data (has environment, team, cost_center).
    Returns None if no tagged spend.
    """
    if st.session_state.get("data_source") != "synthetic":
        return None
    try:
        from cwt_ui.services.synthetic_data import get_synthetic_spend
        total, df = get_synthetic_spend(period="this_month", include_tags=True)
    except Exception:
        return None
    if df.empty or not all(c in df.columns for c in ["environment", "team", "cost_center"]):
        return None
    return (df, total)


def get_chargeback_summary(df: pd.DataFrame, total: float, dimension: str) -> pd.DataFrame:
    """Group spend by dimension, return summary with amount and % of total."""
    if df.empty or dimension not in df.columns:
        return pd.DataFrame(columns=[dimension, "Amount ($)", "% of total"])
    summary = (
        df.groupby(dimension, as_index=False)["amount_usd"]
        .sum()
        .sort_values("amount_usd", ascending=False)
    )
    summary["pct_of_total"] = (summary["amount_usd"] / total * 100).round(1)
    summary = summary.rename(columns={"amount_usd": "Amount ($)", "pct_of_total": "% of total"})
    dim_label = next((lbl for key, lbl in ALLOCATION_DIMENSIONS if key == dimension), dimension)
    summary = summary.rename(columns={dimension: dim_label})
    return summary


def get_chargeback_summary_for_overview() -> list[tuple[str, float]] | None:
    """Top 3 by team for Overview card. Returns [(team, amount), ...] or None."""
    result = get_chargeback_data()
    if not result:
        return None
    df, total = result
    if df.empty or "team" not in df.columns:
        return None
    by_team = df.groupby("team")["amount_usd"].sum().sort_values(ascending=False)
    return [(str(k), float(v)) for k, v in by_team.head(3).items()]
