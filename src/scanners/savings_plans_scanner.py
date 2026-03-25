from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
from boto3.session import Session
from botocore.exceptions import ClientError

LOOKBACK_DAYS = 30


def _utc_today() -> datetime:
    return datetime.utcnow()


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _hours_between(start: datetime, end: datetime) -> float:
    delta = end - start
    return max(delta.total_seconds() / 3600.0, 1.0)


def _empty_main_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "SP ID",
            "Type",
            "Region",
            "Commitment ($/hr)",
            "Actual Usage ($/hr)",
            "Utilization %",
            "Coverage %",
            "Forecast Utilization %",
            "Unused Commitment ($/hr)",
            "Expiration Date",
            "Savings Plan Arn",
        ]
    )


def _empty_util_trend() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "savings_plan_arn", "utilization_pct", "used_per_hour", "commitment_per_hour"]
    )


def _empty_coverage_trend() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "savings_plan_arn", "coverage_pct", "covered_spend", "ondemand_spend"]
    )


def _plan_region(plan: Dict) -> str:
    properties = plan.get("tags") or {}
    if isinstance(properties, dict):
        region_tag = properties.get("region") or properties.get("Region")
        if region_tag:
            return region_tag
    plan_region = plan.get("region")
    if plan_region:
        return plan_region
    for prop in plan.get("productTypes", []):
        if isinstance(prop, dict) and prop.get("name") == "region":
            return prop.get("value") or "Multi-region"
    return "Multi-region"


def scan_savings_plans() -> Tuple[pd.DataFrame, Dict[str, float], pd.DataFrame, pd.DataFrame]:
    """
    Fetch Savings Plans utilization and coverage metrics for the past LOOKBACK_DAYS.

    Returns:
        tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
            - Plan-level snapshot
            - Summary statistics
            - Utilization history (per-day)
            - Coverage history (per-day)
    """
    session = Session()

    try:
        savings_client = session.client("savingsplans")
        ce_client = session.client("ce", region_name="us-east-1")
    except Exception as exc:  # pragma: no cover - boto3 initialization errors
        raise RuntimeError(f"Failed to create AWS clients for Savings Plans: {exc}") from exc

    empty_summary = {
        "overall_utilization_pct": 0.0,
        "total_commitment_per_hour": 0.0,
        "total_used_per_hour": 0.0,
        "unused_commitment_per_hour": 0.0,
        "forecast_utilization_pct": 0.0,
    }

    plans: List[Dict] = []
    next_token: str | None = None

    try:
        while True:
            kwargs: Dict[str, str] = {}
            if next_token:
                kwargs["nextToken"] = next_token
            response = savings_client.describe_savings_plans(**kwargs)  # type: ignore[arg-type]
            plans.extend(response.get("savingsPlans", []))
            next_token = response.get("nextToken")
            if not next_token:
                break
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"AccessDeniedException", "UnauthorizedOperation"}:
            summary = empty_summary | {
                "warning": (
                    "Savings Plans permissions are missing (savingsplans:DescribeSavingsPlans). "
                    "Skipping Savings Plan analysis."
                ),
            }
            return _empty_main_frame(), summary, _empty_util_trend(), _empty_coverage_trend()
        raise RuntimeError(f"Failed to list Savings Plans: {exc}") from exc

    if not plans:
        return _empty_main_frame(), empty_summary, _empty_util_trend(), _empty_coverage_trend()

    end_dt = _utc_today().replace(hour=0, minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=LOOKBACK_DAYS)
    hours_in_window = _hours_between(start_dt, end_dt)

    utilization_by_arn: Dict[str, Dict[str, float]] = {}
    utilization_history_rows: List[Dict] = []
    next_token = None

    try:
        while True:
            params: Dict = {
                "TimePeriod": {"Start": _date_str(start_dt), "End": _date_str(end_dt)},
                "Granularity": "DAILY",
            }
            if next_token:
                params["NextToken"] = next_token
            resp = ce_client.get_savings_plans_utilization_details(**params)
            for detail in resp.get("SavingsPlansUtilizationDetails", []):
                arn = detail.get("SavingsPlanArn")
                if arn:
                    util = detail.get("Utilization", {}) or {}
                    totals = utilization_by_arn.setdefault(
                        arn,
                        {
                            "total_commitment": 0.0,
                            "used_commitment": 0.0,
                            "unused_commitment": 0.0,
                            "days": 0,
                        },
                    )
                    total_amt = float(util.get("TotalCommitment", {}).get("Amount", 0.0))
                    used_amt = float(util.get("UsedCommitment", {}).get("Amount", 0.0))
                    unused_amt = float(util.get("UnusedCommitment", {}).get("Amount", 0.0))
                    totals["total_commitment"] += total_amt
                    totals["used_commitment"] += used_amt
                    totals["unused_commitment"] += unused_amt
                    totals["days"] += 1

                    period = detail.get("TimePeriod", {}) or {}
                    day_start = period.get("Start", "")
                    hours_in_day = 24.0
                    utilization_history_rows.append(
                        {
                            "date": day_start,
                            "savings_plan_arn": arn,
                            "utilization_pct": float(util.get("UtilizationPercentage") or 0.0),
                            "used_per_hour": used_amt / hours_in_day if hours_in_day else 0.0,
                            "commitment_per_hour": total_amt / hours_in_day if hours_in_day else 0.0,
                        }
                    )
            next_token = resp.get("NextToken")
            if not next_token:
                break
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"AccessDeniedException", "UnauthorizedOperation"}:
            summary = empty_summary | {
                "warning": (
                    "Savings Plans permissions are missing (ce:GetSavingsPlansUtilizationDetails). "
                    "Skipping Savings Plan analysis."
                ),
            }
            return _empty_main_frame(), summary, _empty_util_trend(), _empty_coverage_trend()
        raise RuntimeError(f"Failed to retrieve Savings Plans utilization: {exc}") from exc

    coverage_by_arn: Dict[str, Dict[str, float]] = {}
    coverage_history_rows: List[Dict] = []
    next_token = None
    coverage_warning_message: str | None = None

    try:
        while True:
            params: Dict = {
                "TimePeriod": {"Start": _date_str(start_dt), "End": _date_str(end_dt)},
                "Granularity": "DAILY",
                "GroupBy": [{"Type": "DIMENSION", "Key": "SAVINGS_PLAN_ARN"}],
            }
            if next_token:
                params["NextToken"] = next_token
            resp = ce_client.get_savings_plans_coverage(**params)
            for entry in resp.get("SavingsPlansCoverages", []):
                coverage = entry.get("Coverage", {}) or {}
                attributes = entry.get("Attributes", {}) or {}
                arn = attributes.get("savingsPlanArn")
                if not arn:
                    continue
                coverage_stats = coverage_by_arn.setdefault(
                    arn,
                    {"covered_spend": 0.0, "ondemand_spend": 0.0, "count": 0},
                )
                covered_spend = float(coverage.get("SpendCoveredBySavingsPlans", {}).get("Amount", 0.0))
                ondemand_cost = float(coverage.get("OnDemandCost", {}).get("Amount", 0.0))
                coverage_stats["covered_spend"] += covered_spend
                coverage_stats["ondemand_spend"] += ondemand_cost
                coverage_stats["count"] += 1

                period = entry.get("TimePeriod", {}) or {}
                coverage_history_rows.append(
                    {
                        "date": period.get("Start", ""),
                        "savings_plan_arn": arn,
                        "coverage_pct": float(coverage.get("CoveragePercentage") or 0.0),
                        "covered_spend": covered_spend,
                        "ondemand_spend": ondemand_cost,
                    }
                )
            next_token = resp.get("NextToken")
            if not next_token:
                break
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"AccessDeniedException", "UnauthorizedOperation"}:
            coverage_warning_message = (
                "Savings Plans permissions are missing (ce:GetSavingsPlansCoverage). "
                "Coverage analytics may be incomplete."
            )
            coverage_by_arn = {}
            coverage_history_rows = []
        else:
            raise RuntimeError(f"Failed to retrieve Savings Plans coverage: {exc}") from exc

    rows: List[Dict[str, float | str]] = []
    total_commitment_per_hour = 0.0
    total_used_per_hour = 0.0
    total_unused_commitment_per_hour = 0.0

    for plan in plans:
        arn = plan.get("savingsPlanArn", "")
        plan_id = plan.get("savingsPlanId", arn[-12:] if arn else "Unknown")
        plan_type = plan.get("savingsPlanType", "Unknown")
        term_seconds = float(plan.get("termDurationInSeconds") or 0)
        term_months = term_seconds / (3600 * 24 * 30) if term_seconds else 0.0
        commitment_per_hour = float(plan.get("commitment") or 0.0) / hours_in_window if hours_in_window else 0.0

        util_stats = utilization_by_arn.get(
            arn, {"total_commitment": 0.0, "used_commitment": 0.0, "unused_commitment": 0.0, "days": 0}
        )
        total_commitment_amount = util_stats["total_commitment"]
        used_commitment_amount = util_stats["used_commitment"]
        unused_commitment_amount = util_stats["unused_commitment"]
        actual_usage_per_hour = used_commitment_amount / hours_in_window if hours_in_window else 0.0
        unused_commitment_per_hour = unused_commitment_amount / hours_in_window if hours_in_window else 0.0

        utilization_pct = (
            (used_commitment_amount / total_commitment_amount) * 100.0 if total_commitment_amount > 0 else 0.0
        )

        coverage_stats = coverage_by_arn.get(arn, {"covered_spend": 0.0, "ondemand_spend": 0.0, "count": 0})
        covered_spend = coverage_stats["covered_spend"]
        ondemand_spend = coverage_stats["ondemand_spend"]
        total_spend = covered_spend + ondemand_spend
        coverage_pct = (covered_spend / total_spend) * 100.0 if total_spend > 0 else 0.0

        total_commitment_per_hour += commitment_per_hour
        total_used_per_hour += actual_usage_per_hour
        total_unused_commitment_per_hour += unused_commitment_per_hour

        forecast_utilization_pct = utilization_pct  # basic placeholder; refined later via trend

        expiration_date = plan.get("termEndDate", "")
        region = _plan_region(plan)

        rows.append(
            {
                "SP ID": plan_id,
                "Type": plan_type,
                "Region": region,
                "Commitment ($/hr)": round(commitment_per_hour, 4),
                "Actual Usage ($/hr)": round(actual_usage_per_hour, 4),
                "Utilization %": round(utilization_pct, 2),
                "Coverage %": round(coverage_pct, 2),
                "Forecast Utilization %": round(forecast_utilization_pct, 2),
                "Unused Commitment ($/hr)": round(unused_commitment_per_hour, 4),
                "Expiration Date": expiration_date,
                "Savings Plan Arn": arn,
            }
        )

    overall_utilization_pct = (
        (total_used_per_hour / total_commitment_per_hour) * 100.0
        if total_commitment_per_hour > 0
        else 0.0
    )

    utilization_history_df = (
        pd.DataFrame(utilization_history_rows) if utilization_history_rows else _empty_util_trend()
    )
    if not utilization_history_df.empty:
        util_grouped = (
            utilization_history_df.groupby("date")[["used_per_hour", "commitment_per_hour"]]
            .sum()
            .reset_index()
        )
        util_grouped["utilization_pct"] = util_grouped.apply(
            lambda row: (row["used_per_hour"] / row["commitment_per_hour"]) * 100.0
            if row["commitment_per_hour"]
            else 0.0,
            axis=1,
        )
    else:
        util_grouped = _empty_util_trend()

    coverage_history_df = pd.DataFrame(coverage_history_rows) if coverage_history_rows else _empty_coverage_trend()
    if not coverage_history_df.empty:
        coverage_grouped = (
            coverage_history_df.groupby("date")[["covered_spend", "ondemand_spend"]]
            .sum()
            .reset_index()
        )
        coverage_grouped["coverage_pct"] = coverage_grouped.apply(
            lambda row: (row["covered_spend"] / (row["covered_spend"] + row["ondemand_spend"])) * 100.0
            if (row["covered_spend"] + row["ondemand_spend"])
            else 0.0,
            axis=1,
        )
    else:
        coverage_grouped = _empty_coverage_trend()

    if not util_grouped.empty:
        recent_points = util_grouped.tail(7)
        forecast_utilization_pct = float(recent_points["utilization_pct"].mean())
    else:
        forecast_utilization_pct = overall_utilization_pct

    summary = {
        "overall_utilization_pct": round(overall_utilization_pct, 2),
        "total_commitment_per_hour": round(total_commitment_per_hour, 4),
        "total_used_per_hour": round(total_used_per_hour, 4),
        "unused_commitment_per_hour": round(total_unused_commitment_per_hour, 4),
        "forecast_utilization_pct": round(forecast_utilization_pct, 2),
    }
    if coverage_warning_message:
        summary["warning"] = coverage_warning_message

    df = pd.DataFrame(rows)
    return df, summary, utilization_history_df, coverage_history_df

