# Budgets service: consumed %, status, forecast from spend data.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


@dataclass
class Budget:
    name: str
    amount: float
    period: str
    scope: str
    consumed: float
    consumed_pct: float
    status: str  # "on_track" | "at_risk" | "over"
    forecast: float


# Synthetic budget definitions (name, amount, scope_type, scope_key, scope_value)
SYNTHETIC_BUDGET_DEFS = [
    ("Engineering", 3_500.0, "tag", "team", "Engineering"),
    ("Production", 6_000.0, "tag", "environment", "prod"),
    ("Total AWS", 10_000.0, "all", None, None),
]

# Days elapsed / days in period for forecast (simulate mid-month)
DAYS_ELAPSED = 15
DAYS_IN_PERIOD = 30


def _consumed_for_scope(spend_df: pd.DataFrame, scope_type: str, scope_key: str | None, scope_value: str | None) -> float:
    """Sum spend where scope matches."""
    if spend_df.empty:
        return 0.0
    if scope_type == "all":
        return float(pd.to_numeric(spend_df["amount_usd"], errors="coerce").fillna(0).sum())
    if scope_type == "tag" and scope_key and scope_value and scope_key in spend_df.columns:
        mask = spend_df[scope_key].astype(str) == str(scope_value)
        return float(pd.to_numeric(spend_df.loc[mask, "amount_usd"], errors="coerce").fillna(0).sum())
    return 0.0


def _status(consumed_pct: float) -> str:
    if consumed_pct >= 100:
        return "over"
    if consumed_pct >= 80:
        return "at_risk"
    return "on_track"


def _forecast(consumed: float) -> float:
    """At current run rate: forecast = consumed * (period_days / days_elapsed)."""
    if DAYS_ELAPSED <= 0:
        return consumed
    return round(consumed * (DAYS_IN_PERIOD / DAYS_ELAPSED), 2)


def get_budgets() -> list[Budget]:
    """
    Return budgets with consumed %, status, forecast.
    For synthetic: uses spend data and SYNTHETIC_BUDGET_DEFS.
    For real scan: returns empty (until CUR/budget integration exists).
    """
    if st.session_state.get("data_source") != "synthetic":
        return []
    try:
        from cwt_ui.services.synthetic_data import get_synthetic_spend
        _, spend_df = get_synthetic_spend(period="this_month", include_tags=True)
    except Exception:
        return []

    if spend_df.empty or "amount_usd" not in spend_df.columns:
        return []

    budgets: list[Budget] = []
    for name, amount, scope_type, scope_key, scope_value in SYNTHETIC_BUDGET_DEFS:
        consumed = _consumed_for_scope(spend_df, scope_type, scope_key, scope_value)
        consumed_pct = (consumed / amount * 100) if amount > 0 else 0.0
        status = _status(consumed_pct)
        forecast = _forecast(consumed)
        scope_label = "All spend" if scope_type == "all" else f"tag:{scope_key}={scope_value}"
        budgets.append(Budget(
            name=name,
            amount=amount,
            period="monthly",
            scope=scope_label,
            consumed=round(consumed, 2),
            consumed_pct=round(consumed_pct, 1),
            status=status,
            forecast=forecast,
        ))
    return budgets


def get_first_budget_consumption() -> tuple[float, float, str] | None:
    """
    For Overview KPI: return (consumed_pct, consumed, status) of first budget.
    Returns None if no budgets.
    """
    budgets = get_budgets()
    if not budgets:
        return None
    b = budgets[0]
    return (b.consumed_pct, b.consumed, b.status)
