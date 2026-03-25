from __future__ import annotations

from typing import List

import pandas as pd


def underutilized_plans(plans_df: pd.DataFrame, threshold: float = 85.0) -> pd.DataFrame:
    """
    Return Savings Plans whose utilization percentage falls below the given threshold.
    """
    if plans_df is None or plans_df.empty:
        return pd.DataFrame()

    if "Utilization %" not in plans_df.columns:
        return pd.DataFrame()

    mask = pd.to_numeric(plans_df["Utilization %"], errors="coerce") < threshold
    return plans_df.loc[mask].copy()


def workload_shift_suggestions(
    coverage_history_df: pd.DataFrame,
    coverage_threshold: float = 80.0,
    spend_threshold: float = 10.0,
) -> List[str]:
    """
    Generate workload shift suggestions based on uncovered on-demand spend.

    Args:
        coverage_history_df: DataFrame containing coverage history with columns
            ['date', 'covered_spend', 'ondemand_spend', 'coverage_pct'].
        coverage_threshold: Coverage percentage below which to flag potential shifts.
        spend_threshold: Minimum on-demand spend (USD) to consider significant.
    """
    if coverage_history_df is None or coverage_history_df.empty:
        return []

    required_cols = {"date", "covered_spend", "ondemand_spend", "coverage_pct"}
    if not required_cols.issubset(set(coverage_history_df.columns)):
        return []

    df = coverage_history_df.copy()
    df["ondemand_spend"] = pd.to_numeric(df["ondemand_spend"], errors="coerce").fillna(0.0)
    df["coverage_pct"] = pd.to_numeric(df["coverage_pct"], errors="coerce").fillna(0.0)

    suggestions: List[str] = []
    filtered = df[(df["coverage_pct"] < coverage_threshold) & (df["ondemand_spend"] >= spend_threshold)]

    for _, row in filtered.nlargest(3, "ondemand_spend").iterrows():
        date_str = row["date"]
        uncovered = row["ondemand_spend"]
        coverage_pct = row["coverage_pct"]
        suggestions.append(
            f"On {date_str}, coverage dropped to {coverage_pct:.1f}% with ${uncovered:,.0f} in on-demand spend. "
            "Consider shifting suitable workloads to existing Savings Plan coverage or purchasing additional commitments."
        )

    return suggestions


def build_insights(
    plans_df: pd.DataFrame,
    coverage_history_df: pd.DataFrame,
    utilization_threshold: float = 85.0,
) -> List[str]:
    """
    Build a list of narrative insights for the Savings Plan dashboard.
    """
    insights: List[str] = []

    under_df = underutilized_plans(plans_df, threshold=utilization_threshold)
    if not under_df.empty:
        plan_list = ", ".join(under_df["SP ID"].astype(str).tolist())
        insights.append(
            f"The following Savings Plans are underutilized (< {utilization_threshold:.0f}%): {plan_list}. "
            "Investigate whether workloads can be consolidated or if commitments should be resized."
        )

    shift_suggestions = workload_shift_suggestions(coverage_history_df)
    insights.extend(shift_suggestions)

    if not insights:
        insights.append("All active Savings Plans appear healthy. No immediate optimization actions detected.")

    return insights

