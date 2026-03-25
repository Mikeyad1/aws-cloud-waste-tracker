# Aggregate spend from scan-derived data (EC2, SP) for Spend page and Overview.
# MVP command 23: all service DataFrames use recommendation + potential_savings_usd for unified logic.
from __future__ import annotations

import pandas as pd
import streamlit as st


def normalize_optimization_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of the DataFrame with canonical columns recommendation and potential_savings_usd.
    Copies from Recommendation / Potential Savings ($) / potential_savings if present.
    So unified recommendations list and unified metrics can assume the same column names.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if "recommendation" not in out.columns:
        for c in ["Recommendation", "recommendation"]:
            if c in out.columns:
                out["recommendation"] = out[c].astype(str)
                break
    if "potential_savings_usd" not in out.columns:
        for c in ["Potential Savings ($)", "potential_savings_usd", "potential_savings", "Potential Savings (Monthly)"]:
            if c in out.columns:
                out["potential_savings_usd"] = pd.to_numeric(out[c], errors="coerce").fillna(0)
                break
    return out


def get_spend_from_scan(period: str = "this_month") -> tuple[float, pd.DataFrame]:
    """
    Build spend total and by-service/region from session state.

    When data_source is "synthetic", returns full service list (EC2, S3, Data Transfer, etc.)
    from synthetic_data.get_synthetic_spend(). Otherwise uses ec2_df + SP data only.
    period: "this_month" | "last_month" (last_month only applies to synthetic).

    Returns:
        (total_usd, df) where df has columns: service, region, amount_usd[, category, environment, team, cost_center, linked_account_id, linked_account_name].
        total_usd is the sum of amount_usd. region may be "—" for service-level rows.
    """
    if st.session_state.get("data_source") == "synthetic":
        try:
            from cwt_ui.services.synthetic_data import get_synthetic_spend
            return get_synthetic_spend(period=period, include_tags=True)
        except Exception:
            pass  # fall through to scan-derived
    rows: list[dict] = []
    total = 0.0

    # EC2: sum monthly_cost_usd by region
    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    if ec2_df is not None and not ec2_df.empty:
        cost_col = None
        for c in ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost"]:
            if c in ec2_df.columns:
                cost_col = c
                break
        region_col = None
        for c in ["region", "Region"]:
            if c in ec2_df.columns:
                region_col = c
                break
        if cost_col:
            amounts = pd.to_numeric(ec2_df[cost_col], errors="coerce").fillna(0)
            total_ec2 = amounts.sum()
            total += float(total_ec2)
            if region_col:
                by_region = ec2_df.groupby(region_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_region.columns = ["region", "amount_usd"]
                for _, row in by_region.iterrows():
                    rows.append({"service": "EC2", "region": str(row["region"]), "amount_usd": float(row["amount_usd"]), "category": "Compute"})
            else:
                rows.append({"service": "EC2", "region": "—", "amount_usd": float(total_ec2), "category": "Compute"})

    # Savings Plans: from coverage trend (covered + on-demand) or summary
    sp_coverage = st.session_state.get("SP_COVERAGE_TREND", pd.DataFrame())
    if sp_coverage is not None and not sp_coverage.empty:
        covered = 0.0
        ondemand = 0.0
        for c in ["covered_spend", "Covered Spend"]:
            if c in sp_coverage.columns:
                covered = pd.to_numeric(sp_coverage[c], errors="coerce").fillna(0).sum()
                break
        for c in ["ondemand_spend", "On-Demand Spend"]:
            if c in sp_coverage.columns:
                ondemand = pd.to_numeric(sp_coverage[c], errors="coerce").fillna(0).sum()
                break
        if covered > 0 or ondemand > 0:
            total_sp = covered + ondemand
            total += total_sp
            rows.append({"service": "Savings Plans (covered)", "region": "—", "amount_usd": float(covered), "category": "Commitment"})
            rows.append({"service": "Savings Plans (on-demand)", "region": "—", "amount_usd": float(ondemand), "category": "Commitment"})

    # Storage (S3): real scanner data
    storage_df = st.session_state.get("storage_df", pd.DataFrame())
    if storage_df is not None and not storage_df.empty:
        cost_col = None
        for c in ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost"]:
            if c in storage_df.columns:
                cost_col = c
                break
        region_col = next((c for c in ["region", "Region"] if c in storage_df.columns), None)
        if cost_col:
            amounts = pd.to_numeric(storage_df[cost_col], errors="coerce").fillna(0)
            total_s3 = amounts.sum()
            total += float(total_s3)
            if region_col:
                by_region = storage_df.groupby(region_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_region.columns = ["region", "amount_usd"]
                for _, row in by_region.iterrows():
                    rows.append({"service": "S3", "region": str(row["region"]), "amount_usd": float(row["amount_usd"]), "category": "Storage"})
            else:
                rows.append({"service": "S3", "region": "—", "amount_usd": float(total_s3), "category": "Storage"})

    # Data Transfer: real scanner data
    data_transfer_df = st.session_state.get("data_transfer_df", pd.DataFrame())
    if data_transfer_df is not None and not data_transfer_df.empty:
        cost_col = None
        for c in ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost"]:
            if c in data_transfer_df.columns:
                cost_col = c
                break
        region_col = next((c for c in ["region", "Region"] if c in data_transfer_df.columns), None)
        if cost_col:
            amounts = pd.to_numeric(data_transfer_df[cost_col], errors="coerce").fillna(0)
            total_dt = amounts.sum()
            total += float(total_dt)
            if region_col:
                by_region = data_transfer_df.groupby(region_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_region.columns = ["region", "amount_usd"]
                for _, row in by_region.iterrows():
                    rows.append({"service": "Data Transfer", "region": str(row["region"]), "amount_usd": float(row["amount_usd"]), "category": "Network"})
            else:
                rows.append({"service": "Data Transfer", "region": "—", "amount_usd": float(total_dt), "category": "Network"})

    # Databases (RDS, DynamoDB): real scanner data
    databases_df = st.session_state.get("databases_df", pd.DataFrame())
    if databases_df is not None and not databases_df.empty:
        cost_col = None
        for c in ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost"]:
            if c in databases_df.columns:
                cost_col = c
                break
        region_col = next((c for c in ["region", "Region"] if c in databases_df.columns), None)
        service_col = next((c for c in ["service", "Service"] if c in databases_df.columns), None)
        if cost_col:
            amounts = pd.to_numeric(databases_df[cost_col], errors="coerce").fillna(0)
            total_db = amounts.sum()
            total += float(total_db)
            if region_col and service_col:
                by_svc_region = databases_df.groupby([service_col, region_col])[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_svc_region.columns = ["service", "region", "amount_usd"]
                for _, row in by_svc_region.iterrows():
                    rows.append({"service": str(row["service"]), "region": str(row["region"]), "amount_usd": float(row["amount_usd"]), "category": "Database"})
            elif service_col:
                by_svc = databases_df.groupby(service_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_svc.columns = ["service", "amount_usd"]
                for _, row in by_svc.iterrows():
                    rows.append({"service": str(row["service"]), "region": "—", "amount_usd": float(row["amount_usd"]), "category": "Database"})
            elif region_col:
                by_region = databases_df.groupby(region_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_region.columns = ["region", "amount_usd"]
                for _, row in by_region.iterrows():
                    rows.append({"service": "RDS/DynamoDB", "region": str(row["region"]), "amount_usd": float(row["amount_usd"]), "category": "Database"})
            else:
                rows.append({"service": "RDS/DynamoDB", "region": "—", "amount_usd": float(total_db), "category": "Database"})

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["service", "region", "amount_usd", "category"])
    return total, df


def get_spend_mom_for_synthetic() -> tuple[float, float] | None:
    """
    For synthetic data only: returns (this_month_total, last_month_total) for MoM comparison.
    Returns None if not synthetic.
    """
    if st.session_state.get("data_source") != "synthetic":
        return None
    try:
        from cwt_ui.services.synthetic_data import get_synthetic_spend
        this_total, _ = get_synthetic_spend(period="this_month", include_tags=True)
        last_total, _ = get_synthetic_spend(period="last_month", include_tags=True)
        return (this_total, last_total)
    except Exception:
        return None


def get_spend_mom_for_real() -> tuple[float, float] | None:
    """
    For real (live) data: returns (this_month_total, last_month_total) from Cost Explorer for MoM comparison.
    Returns None if not real, or if CE call fails (e.g. missing ce:GetCostAndUsage).
    """
    if st.session_state.get("data_source") != "real":
        return None
    try:
        from cwt_ui.services.scans import get_cost_explorer_client, fetch_spend_mom
        ce = get_cost_explorer_client()
        return fetch_spend_mom(ce)
    except Exception:
        return None


def _sum_potential_from_df(df: pd.DataFrame) -> float:
    """Sum potential_savings_usd from a single DataFrame (or 0 if missing/empty)."""
    if df is None or df.empty:
        return 0.0
    for col in ["potential_savings_usd", "Potential Savings ($)", "potential_savings"]:
        if col in df.columns:
            return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
    return 0.0


def _action_count_from_df(df: pd.DataFrame) -> int:
    """Count rows with positive potential savings (actionable recommendations)."""
    if df is None or df.empty:
        return 0
    for col in ["potential_savings_usd", "Potential Savings ($)", "potential_savings"]:
        if col in df.columns:
            return int((pd.to_numeric(df[col], errors="coerce").fillna(0) > 0).sum())
    return 0


def get_waste_number_trace(
    resolved_waste: float,
    excluded_waste: float,
) -> dict[str, float | list[dict[str, float | str]]]:
    """
    Explain the hero "Your waste" number: sum of potential_savings_usd per service DataFrame,
    minus resolved and excluded recommendation totals.

    Returns:
        by_service: rows with positive sums only, each { "service": str, "amount_usd": float }
        gross_total: sum of potential_savings_usd across all scanned service frames
        resolved_total, excluded_total: same as inputs
        net_total: max(0, gross - resolved - excluded) — matches the hero when logic is aligned
    """
    keys = [
        ("ec2_df", "EC2"),
        ("lambda_df", "Lambda"),
        ("fargate_df", "Fargate"),
        ("storage_df", "Amazon S3"),
        ("data_transfer_df", "Data Transfer"),
        ("databases_df", "RDS & DynamoDB"),
    ]
    by_service: list[dict[str, float | str]] = []
    gross_total = 0.0
    for state_key, label in keys:
        df = st.session_state.get(state_key, pd.DataFrame())
        if df is None or df.empty:
            continue
        df = normalize_optimization_df(df)
        part = _sum_potential_from_df(df)
        part = float(part)
        gross_total += part
        if part > 0:
            by_service.append({"service": label, "amount_usd": part})
    rw = float(resolved_waste or 0)
    ew = float(excluded_waste or 0)
    net_total = max(0.0, gross_total - rw - ew)
    return {
        "by_service": by_service,
        "gross_total": gross_total,
        "resolved_total": rw,
        "excluded_total": ew,
        "net_total": net_total,
    }


def get_unified_optimization_metrics() -> tuple[float, int]:
    """
    Total waste and action count aligned with the Waste page list (single source of truth).

    Sums the same ``Waste ($/mo)`` rows as ``build_unified_what_to_turn_off`` (filters, aggregation,
    and data-transfer grouping included). Raw per-DataFrame sums can differ and are not used here.
    Returns:
        (total_waste_usd, total_action_count) — total_action_count is the number of recommendation rows.
    """
    from cwt_ui.utils.unified_recommendations import build_unified_what_to_turn_off

    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    lambda_df = st.session_state.get("lambda_df", pd.DataFrame())
    fargate_df = st.session_state.get("fargate_df", pd.DataFrame())
    storage_df = st.session_state.get("storage_df", pd.DataFrame())
    data_transfer_df = st.session_state.get("data_transfer_df", pd.DataFrame())
    databases_df = st.session_state.get("databases_df", pd.DataFrame())

    rows = build_unified_what_to_turn_off(
        ec2_df if ec2_df is not None and not ec2_df.empty else None,
        lambda_df if lambda_df is not None and not lambda_df.empty else None,
        fargate_df if fargate_df is not None and not fargate_df.empty else None,
        storage_df if storage_df is not None and not storage_df.empty else None,
        data_transfer_df if data_transfer_df is not None and not data_transfer_df.empty else None,
        databases_df if databases_df is not None and not databases_df.empty else None,
    )
    total_waste = sum(float(r.get("Waste ($/mo)", 0) or 0) for r in rows)
    total_actions = len(rows)
    return total_waste, total_actions


def get_optimization_metrics(ec2_df: pd.DataFrame) -> tuple[float, int]:
    """
    Compute optimization potential (sum of potential_savings_usd) and action count
    (recommendations that are not OK / No action) from EC2 dataframe.
    Used when only EC2 is available (e.g. live scan). Prefer get_unified_optimization_metrics()
    when multiple service DataFrames may be in session state.
    """
    if ec2_df is None or ec2_df.empty:
        return 0.0, 0
    potential = _sum_potential_from_df(ec2_df)
    rec_col = None
    for col in ["recommendation", "Recommendation"]:
        if col in ec2_df.columns:
            rec_col = col
            break
    action_count = 0
    if rec_col:
        rec_upper = ec2_df[rec_col].astype(str).str.upper()
        action_count = int((~rec_upper.str.contains("OK|NO ACTION", na=True)).sum())
    else:
        action_count = _action_count_from_df(ec2_df)
    return potential, action_count
