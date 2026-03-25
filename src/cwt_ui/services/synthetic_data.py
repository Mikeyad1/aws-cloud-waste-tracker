"""
Synthetic data for demo/development. Matches real scan schemas and calculations.
Target volume: mid-size enterprise (~80 EC2, ~40 Lambda, ~15 Fargate, 2 Savings Plans).
Switch source by running a real scan (overwrites session state) or loading synthetic again.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

# Target audience scale: mid-size enterprise
NUM_EC2 = 82
NUM_LAMBDA = 38
NUM_FARGATE = 14
NUM_SAVINGS_PLANS = 2
TREND_DAYS = 30

REGIONS = ["us-east-1", "us-east-2", "us-west-2", "eu-west-1", "ap-southeast-1"]
INSTANCE_TYPES = ["t3.small", "t3.medium", "t3.large", "m5.large", "m5.xlarge", "c5.large", "c5.xlarge"]
GPU_INSTANCE_TYPES = ["p3.2xlarge", "g4dn.xlarge"]  # For governance policy violations
DEPARTMENTS = ["Engineering", "Platform", "Data", "Product", "Unassigned"]
SYNTHETIC_ENVIRONMENTS_EC2 = ["prod", "staging", "dev"]
RUNTIMES = ["python3.11", "python3.12", "nodejs18.x", "nodejs20.x", "java17"]


def _idle_score(cpu_pct: float) -> float:
    """Same formula as real: (1 - cpu/100) * 100, clipped 0-100."""
    return max(0.0, min(100.0, (1.0 - (cpu_pct / 100.0)) * 100.0))


def _recommendation(cpu_pct: float) -> str:
    """Mirror real scanner logic."""
    if cpu_pct < 1.0:
        return "Stop instance - extremely low CPU usage"
    if cpu_pct < 3.0:
        return "Stop or downsize - very low CPU usage"
    if cpu_pct < 5.0:
        return "Consider downsizing - low CPU usage"
    return "OK - CPU usage is normal"


def _potential_savings(cpu_pct: float, monthly_cost: float) -> float:
    """Same as real: full cost for stop, fraction for downsize, 0 for OK."""
    if cpu_pct < 1.0 or cpu_pct < 3.0:
        return monthly_cost
    if cpu_pct < 5.0:
        return monthly_cost * 0.5
    return 0.0


def _build_ec2_df(run_seed: int | None = None) -> pd.DataFrame:
    """EC2 dataframe matching scanner + _normalize_ec2 schema."""
    random.seed((run_seed + 42) if run_seed is not None else 42)
    rows = []
    base_costs = {
        "t3.small": 15, "t3.medium": 30, "t3.large": 60, "m5.large": 70, "m5.xlarge": 140,
        "c5.large": 62, "c5.xlarge": 124, "p3.2xlarge": 2190, "g4dn.xlarge": 526,
    }
    for i in range(NUM_EC2):
        region = random.choice(REGIONS)
        itype = random.choice(GPU_INSTANCE_TYPES) if random.random() < 0.04 else random.choice(INSTANCE_TYPES)
        base_cost = base_costs.get(itype, 50)
        monthly_cost = round(base_cost * (0.85 + random.random() * 0.3), 2)
        # ~35% idle/low, rest normal (realistic distribution)
        r = random.random()
        if r < 0.12:
            cpu_pct = random.uniform(0.2, 0.9)
        elif r < 0.25:
            cpu_pct = random.uniform(1.0, 2.9)
        elif r < 0.35:
            cpu_pct = random.uniform(3.0, 4.9)
        else:
            cpu_pct = random.uniform(8.0, 75.0)
        state = "running" if random.random() < 0.92 else "stopped"
        if state == "stopped":
            monthly_cost = 0.0
        else:
            monthly_cost = round(monthly_cost, 2)
        rec = _recommendation(cpu_pct)
        pot = _potential_savings(cpu_pct, monthly_cost) if state == "running" else 0.0
        idle = _idle_score(cpu_pct)
        sp_covered = random.random() < 0.55  # ~55% on SP
        env = random.choice(SYNTHETIC_ENVIRONMENTS_EC2)
        rows.append({
            "instance_id": f"i-{hex(10000 + i)[2:].zfill(8)}",
            "name": f"app-{random.choice(['web', 'api', 'worker', 'batch'])}-{i % 20}",
            "instance_type": itype,
            "region": region,
            "state": state,
            "avg_cpu_7d": round(cpu_pct, 2),
            "monthly_cost_usd": monthly_cost,
            "recommendation": rec,
            "potential_savings_usd": round(pot, 2),
            "type": "ec2_instance",
            "billing_type": "SP-Covered" if sp_covered and state == "running" else "On-Demand",
            "department": random.choice(DEPARTMENTS),
            "idle_score": round(idle, 1),
            "environment": env,
        })
    df = pd.DataFrame(rows)
    df["scanned_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def _build_lambda_df(run_seed: int | None = None) -> pd.DataFrame:
    """Lambda dataframe with billing_type (Compute SP covers Lambda)."""
    random.seed((run_seed + 43) if run_seed is not None else 43)
    rows = []
    for i in range(NUM_LAMBDA):
        region = random.choice(REGIONS)
        mem = random.choice([128, 256, 512, 1024, 1536, 3008])
        timeout = random.choice([3, 10, 30, 60, 120, 300])
        dt = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90))
        monthly_cost = round((5 + mem / 64 + random.random() * 15), 2)
        sp_covered = random.random() < 0.45  # ~45% on Compute SP
        rec = "Right-size memory" if mem > 512 and random.random() < 0.3 else "OK"
        pot = round(monthly_cost * 0.15, 2) if "Right-size" in rec else 0.0
        rows.append({
            "function_name": f"fn-{random.choice(['sync', 'async', 'processor', 'handler'])}-{i}",
            "region": region,
            "runtime": random.choice(RUNTIMES),
            "memory_size_mb": mem,
            "timeout_seconds": timeout,
            "last_modified": dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "monthly_cost_usd": monthly_cost,
            "billing_type": "SP-Covered" if sp_covered else "On-Demand",
            "recommendation": rec,
            "potential_savings_usd": pot,
        })
    return pd.DataFrame(rows)


def _build_fargate_df(run_seed: int | None = None) -> pd.DataFrame:
    """Fargate dataframe with billing_type (Compute SP covers Fargate)."""
    random.seed((run_seed + 44) if run_seed is not None else 44)
    rows = []
    clusters = [f"cluster-{x}" for x in ["prod", "staging", "data"]]
    for i in range(NUM_FARGATE):
        region = random.choice(REGIONS)
        cpu = random.choice([256, 512, 1024, 2044, 4096])
        memory_mb = random.choice([512, 1024, 2048, 4096, 8192])
        dt = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14))
        status = "RUNNING" if random.random() < 0.9 else "STOPPED"
        monthly_cost = 0.0 if status == "STOPPED" else round((cpu / 1024 * 0.04048 + memory_mb / 1024 * 0.004445) * 730 * (0.9 + random.random() * 0.2), 2)
        sp_covered = random.random() < 0.50 and status == "RUNNING"  # ~50% on Compute SP
        rec = "Right-size CPU/memory" if cpu >= 2044 and random.random() < 0.25 else "OK"
        pot = round(monthly_cost * 0.2, 2) if "Right-size" in rec else 0.0
        rows.append({
            "service_name": f"svc-{random.choice(['api', 'worker', 'web'])}-{i % 5}" if random.random() < 0.8 else "Standalone Task",
            "cluster_name": random.choice(clusters),
            "task_definition_family": f"task-{i % 10}:{random.randint(1, 5)}",
            "region": region,
            "cpu": str(cpu),
            "memory_mb": memory_mb,
            "platform_version": "1.4.0",
            "status": status,
            "container_names": "app",
            "started_at": dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "monthly_cost_usd": monthly_cost,
            "billing_type": "SP-Covered" if sp_covered else "On-Demand",
            "recommendation": rec,
            "potential_savings_usd": pot,
        })
    return pd.DataFrame(rows)


def _build_sp_df() -> pd.DataFrame:
    """Savings Plans list: EC2 Instance SP (EC2 only) + Compute SP (EC2, Fargate, Lambda)."""
    rows = [
        {"SP ID": "sp-ec2-1", "Type": "EC2", "Region": "us-east-1", "Commitment ($/hr)": 2.5, "Actual Usage ($/hr)": 2.1, "Utilization %": 84.0, "Coverage %": 72.0, "Forecast Utilization %": 85.0, "Unused Commitment ($/hr)": 0.4, "Expiration Date": "2026-06-30", "Savings Plan Arn": "arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-ec2-1", "Covers": "EC2 only"},
        {"SP ID": "sp-compute-1", "Type": "Compute", "Region": "Multi-region", "Commitment ($/hr)": 1.8, "Actual Usage ($/hr)": 1.5, "Utilization %": 83.3, "Coverage %": 68.0, "Forecast Utilization %": 82.0, "Unused Commitment ($/hr)": 0.3, "Expiration Date": "2026-09-15", "Savings Plan Arn": "arn:aws:savingsplans:us-east-1:123456789012:savingsplan/sp-compute-1", "Covers": "EC2, Fargate, Lambda"},
    ]
    return pd.DataFrame(rows[:NUM_SAVINGS_PLANS])


def _build_sp_util_trend() -> pd.DataFrame:
    """Utilization trend: date, used_per_hour, commitment_per_hour, utilization_pct."""
    base_commit = 4.3
    base_used = 3.6
    rows = []
    for d in range(TREND_DAYS):
        dt = (datetime.now(timezone.utc) - timedelta(days=TREND_DAYS - d)).date()
        used = base_used * (0.9 + random.random() * 0.2)
        commit = base_commit
        util = (used / commit * 100.0) if commit else 0.0
        rows.append({"date": dt.isoformat(), "used_per_hour": round(used, 4), "commitment_per_hour": round(commit, 4), "utilization_pct": round(util, 2)})
    return pd.DataFrame(rows)


def _build_sp_coverage_trend() -> pd.DataFrame:
    """Coverage trend: date, covered_spend, ondemand_spend (daily totals)."""
    rows = []
    for d in range(TREND_DAYS):
        dt = (datetime.now(timezone.utc) - timedelta(days=TREND_DAYS - d)).date()
        covered = 150.0 * (0.85 + random.random() * 0.2)  # daily
        ondemand = 60.0 * (0.8 + random.random() * 0.3)
        rows.append({"date": dt.isoformat(), "covered_spend": round(covered, 2), "ondemand_spend": round(ondemand, 2)})
    return pd.DataFrame(rows)


def _build_sp_summary() -> dict[str, Any]:
    """Summary dict matching scanner."""
    return {
        "overall_utilization_pct": 83.5,
        "total_commitment_per_hour": 4.3,
        "total_used_per_hour": 3.6,
        "unused_commitment_per_hour": 0.7,
        "forecast_utilization_pct": 84.0,
    }


# Full service list for MVP spend (mid-market FinOps target)
SYNTHETIC_SPEND_SERVICES = [
    ("EC2-Instances", "—", None),  # from ec2_df
    ("EC2-Other", "—", 420.0),     # EBS, etc.
    ("Lambda", "—", 380.0),
    ("Elastic Container Service", "—", 520.0),
    ("EC2 Container Registry (ECR)", "—", 85.0),
    ("S3", "—", 2140.0),
    ("Data Transfer", "—", 890.0),
    ("CloudWatch", "—", 340.0),
    ("VPC", "—", 180.0),
    ("RDS", "—", 1650.0),
    ("DynamoDB", "—", 420.0),
    ("CloudFront", "—", 280.0),
    ("Savings Plans (covered)", "—", None),  # from SP_COVERAGE_TREND
    ("Savings Plans (on-demand)", "—", None),  # from SP_COVERAGE_TREND
    ("Other", "—", 195.0),         # KMS, SNS, SQS, Glue, etc.
]

# AWS Usage Types (Cost Explorer / CUR style) — service → default usage_type
SERVICE_TO_USAGE_TYPE: dict[str, str] = {
    "EC2-Other": "EBS:VolumeUsage.gp3",
    "Lambda": "Lambda-GB-Second",
    "Elastic Container Service": "Fargate-vCPU-Hour",
    "EC2 Container Registry (ECR)": "ECR:Storage",
    "S3": "TimedStorage-ByteHrs",
    "Data Transfer": "EU-DataTransfer-Out-Bytes",
    "CloudWatch": "CW:PutMetricData",
    "VPC": "NatGateway-Hours",
    "RDS": "USE1-BoxUsage:db.t3.medium",
    "DynamoDB": "DynamoDB:ReadRequestUnits",
    "CloudFront": "CF:DataTransfer-Out-Bytes",
    "Savings Plans (covered)": "SavingsPlan-CoveredUsage",
    "Savings Plans (on-demand)": "SavingsPlan-OnDemandEquivalent",
    "Other": "Other",
}

# AWS service names (Cost Explorer / Billing Console style)
SERVICE_TO_AWS_NAME: dict[str, str] = {
    "EC2-Instances": "Amazon EC2",
    "EC2-Other": "Amazon EC2 (Other)",
    "Lambda": "AWS Lambda",
    "Elastic Container Service": "Amazon Elastic Container Service",
    "EC2 Container Registry (ECR)": "Amazon EC2 Container Registry (ECR)",
    "S3": "Amazon Simple Storage Service",
    "Data Transfer": "AWS Data Transfer",
    "CloudWatch": "Amazon CloudWatch",
    "VPC": "Amazon VPC",
    "RDS": "Amazon Relational Database Service",
    "DynamoDB": "Amazon DynamoDB",
    "CloudFront": "Amazon CloudFront",
    "Savings Plans (covered)": "Savings Plans (covered)",
    "Savings Plans (on-demand)": "Savings Plans (on-demand)",
    "Other": "Other",
}

# Cost allocation tags for synthetic view (matches CUR / Cost Explorer tags)
SYNTHETIC_ENVIRONMENTS = ["prod", "staging", "dev", "shared"]
SYNTHETIC_TEAMS = ["Engineering", "Platform", "Data", "Product"]
SYNTHETIC_COST_CENTERS = ["CC-1001", "CC-1002", "CC-1003"]

# Synthetic linked accounts (multi-account AWS / Organizations)
SYNTHETIC_LINKED_ACCOUNTS = [
    ("123456789012", "Prod-Account"),
    ("234567890123", "Staging-Account"),
    ("345678901234", "Dev-Account"),
    ("456789012345", "Shared-Services"),
]
ENV_TO_LINKED_ACCOUNT_ID: dict[str, str] = {
    "prod": "123456789012",
    "staging": "234567890123",
    "dev": "345678901234",
    "shared": "456789012345",
}
LINKED_ACCOUNT_DISPLAY: dict[str, str] = {
    "123456789012": "Prod-Account (123456789012)",
    "234567890123": "Staging-Account (234567890123)",
    "345678901234": "Dev-Account (345678901234)",
    "456789012345": "Shared-Services (456789012345)",
}


def _apply_period_variance(amount: float, period: str) -> float:
    """Apply synthetic MoM variance: last_month is ~4% lower than this_month (deterministic)."""
    if period == "last_month":
        return round(amount * 0.96, 2)  # ~4% lower
    return amount


def _split_row_with_tags(row: dict, category_map: dict[str, str]) -> list[dict]:
    """Split a spend row across cost allocation tags (Environment, Team, CostCenter) and linked accounts."""
    seed = sum(ord(c) for c in str(row.get("service", ""))) + int(row.get("amount_usd", 0) * 100)
    random.seed(seed % (2**32))
    n = random.randint(2, 4)
    weights = [random.random() for _ in range(n)]
    weights = [w / sum(weights) for w in weights]
    allocations = []
    allocated = 0.0
    for i, w in enumerate(weights):
        env = SYNTHETIC_ENVIRONMENTS[i % len(SYNTHETIC_ENVIRONMENTS)]
        team = SYNTHETIC_TEAMS[i % len(SYNTHETIC_TEAMS)]
        cc = SYNTHETIC_COST_CENTERS[i % len(SYNTHETIC_COST_CENTERS)]
        linked_account_id = ENV_TO_LINKED_ACCOUNT_ID.get(env, "456789012345")
        linked_account_name = LINKED_ACCOUNT_DISPLAY.get(linked_account_id, linked_account_id)
        amt = round(row["amount_usd"] * w, 2)
        if i == len(weights) - 1:
            amt = round(row["amount_usd"] - allocated, 2)
        if amt > 0:
            allocated += amt
            alloc = {
                "service": row["service"],
                "region": row["region"],
                "amount_usd": amt,
                "category": category_map.get(row["service"], "Other"),
                "environment": env,
                "team": team,
                "cost_center": cc,
                "linked_account_id": linked_account_id,
                "linked_account_name": linked_account_name,
            }
            if "usage_type" in row:
                alloc["usage_type"] = row["usage_type"]
            allocations.append(alloc)
    return allocations


def get_synthetic_spend(
    period: str = "this_month",
    include_tags: bool = True,
) -> tuple[float, pd.DataFrame]:
    """
    Build full spend for all MVP services when using synthetic data.
    Uses ec2_df and SP_COVERAGE_TREND for compute/commitment; fills rest with synthetic amounts.
    Returns (total_usd, df) with columns: service, region, amount_usd, category[, environment, team, cost_center].
    """
    rows: list[dict] = []
    total = 0.0
    category_map = {
        "EC2-Instances": "Compute",
        "EC2-Other": "Compute",
        "Lambda": "Compute",
        "Elastic Container Service": "Containers",
        "EC2 Container Registry (ECR)": "Containers",
        "S3": "Storage",
        "Data Transfer": "Networking",
        "CloudWatch": "Monitoring",
        "VPC": "Networking",
        "RDS": "Databases",
        "DynamoDB": "Databases",
        "CloudFront": "Networking",
        "Savings Plans (covered)": "Commitment",
        "Savings Plans (on-demand)": "Commitment",
        "Other": "Other",
    }

    # EC2-Instances from ec2_df — group by region and instance_type for usage_type
    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    itype_col = next((c for c in ["instance_type", "Instance Type"] if c in ec2_df.columns), None) if ec2_df is not None else None
    if ec2_df is not None and not ec2_df.empty:
        cost_col = next((c for c in ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost"] if c in ec2_df.columns), None)
        region_col = next((c for c in ["region", "Region"] if c in ec2_df.columns), None)
        if cost_col:
            amounts = pd.to_numeric(ec2_df[cost_col], errors="coerce").fillna(0)
            ec2_total = float(amounts.sum())
            ec2_total = _apply_period_variance(ec2_total, period)
            total += ec2_total
            if region_col and itype_col:
                grp_cols = [region_col, itype_col]
                by_region_type = (
                    ec2_df.groupby(grp_cols)[cost_col]
                    .apply(lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum())
                    .reset_index()
                )
                by_region_type.columns = ["region", "instance_type", "amount_usd"]
                for _, r in by_region_type.iterrows():
                    amt = _apply_period_variance(float(r["amount_usd"]), period)
                    usage_type = f"BoxUsage:{r['instance_type']}"
                    rows.append({
                        "service": "EC2-Instances",
                        "region": str(r["region"]),
                        "amount_usd": amt,
                        "category": "Compute",
                        "usage_type": usage_type,
                    })
            elif region_col:
                by_region = ec2_df.groupby(region_col)[cost_col].apply(
                    lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()
                ).reset_index()
                by_region.columns = ["region", "amount_usd"]
                for _, r in by_region.iterrows():
                    amt = _apply_period_variance(float(r["amount_usd"]), period)
                    rows.append({
                        "service": "EC2-Instances",
                        "region": str(r["region"]),
                        "amount_usd": amt,
                        "category": "Compute",
                        "usage_type": "BoxUsage",
                    })
            else:
                rows.append({
                    "service": "EC2-Instances",
                    "region": "—",
                    "amount_usd": ec2_total,
                    "category": "Compute",
                    "usage_type": "BoxUsage",
                })

    # Savings Plans from SP_COVERAGE_TREND
    sp_coverage = st.session_state.get("SP_COVERAGE_TREND", pd.DataFrame())
    if sp_coverage is not None and not sp_coverage.empty:
        covered = 0.0
        ondemand = 0.0
        for c in ["covered_spend", "Covered Spend"]:
            if c in sp_coverage.columns:
                covered = float(pd.to_numeric(sp_coverage[c], errors="coerce").fillna(0).sum())
                break
        for c in ["ondemand_spend", "On-Demand Spend"]:
            if c in sp_coverage.columns:
                ondemand = float(pd.to_numeric(sp_coverage[c], errors="coerce").fillna(0).sum())
                break
        if covered > 0 or ondemand > 0:
            covered = _apply_period_variance(covered, period)
            ondemand = _apply_period_variance(ondemand, period)
            total += covered + ondemand
            rows.append({
                "service": "Savings Plans (covered)",
                "region": "—",
                "amount_usd": covered,
                "category": "Commitment",
                "usage_type": SERVICE_TO_USAGE_TYPE["Savings Plans (covered)"],
            })
            rows.append({
                "service": "Savings Plans (on-demand)",
                "region": "—",
                "amount_usd": ondemand,
                "category": "Commitment",
                "usage_type": SERVICE_TO_USAGE_TYPE["Savings Plans (on-demand)"],
            })

    # Synthetic amounts for other services
    for svc, region, amt in SYNTHETIC_SPEND_SERVICES:
        if amt is not None and svc not in ("EC2-Instances", "Savings Plans (covered)", "Savings Plans (on-demand)"):
            amt = _apply_period_variance(amt, period)
            total += amt
            usage_type = SERVICE_TO_USAGE_TYPE.get(svc, "Other")
            rows.append({
                "service": svc,
                "region": region,
                "amount_usd": amt,
                "category": category_map.get(svc, "Other"),
                "usage_type": usage_type,
            })

    # Expand rows with cost allocation tags if requested
    if include_tags and rows:
        expanded: list[dict] = []
        for row in rows:
            expanded.extend(_split_row_with_tags(row, category_map))
        rows = expanded

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["service", "region", "amount_usd", "category"])
    return total, df


def get_synthetic_spend_last_month() -> tuple[float, pd.DataFrame]:
    """Convenience: return last month's spend for MoM comparison."""
    return get_synthetic_spend(period="last_month", include_tags=True)


def get_synthetic_daily_spend(period: str = "this_month") -> pd.DataFrame:
    """
    Daily spend for the current month (synthetic). Used for "Daily Unblended Cost" chart.
    Returns DataFrame with columns: date, service, amount_usd.
    Realistic variance: weekday vs weekend (weekend ~10% lower), slight growth (~3% over month).
    """
    _, spend_df = get_synthetic_spend(period=period, include_tags=False)
    if spend_df.empty or "amount_usd" not in spend_df.columns:
        return pd.DataFrame(columns=["date", "service", "amount_usd"])

    by_service = spend_df.groupby("service", as_index=False)["amount_usd"].sum()
    now = datetime.now(timezone.utc)
    if period == "last_month":
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    else:
        start_date = now.replace(day=1)
    days_in_month = 30

    random.seed(60 if period == "this_month" else 61)
    weights = []
    for d in range(days_in_month):
        dt = start_date + timedelta(days=d)
        is_weekend = dt.weekday() >= 5
        weekday_factor = 0.92 + random.random() * 0.08 if not is_weekend else 0.82 + random.random() * 0.10
        growth = 0.97 + (d / max(1, days_in_month - 1)) * 0.06
        variance = 0.92 + random.random() * 0.16
        weights.append(weekday_factor * growth * variance)
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    rows: list[dict] = []
    for _, row in by_service.iterrows():
        service = row["service"]
        monthly = float(row["amount_usd"])
        for d in range(days_in_month):
            dt = start_date + timedelta(days=d)
            daily_amount = round(monthly * weights[d], 2)
            rows.append({"date": dt.strftime("%Y-%m-%d"), "service": service, "amount_usd": daily_amount})

    return pd.DataFrame(rows)


def _build_storage_df(run_seed: int | None = None) -> pd.DataFrame:
    """S3 buckets with storage class and optimization recommendations (synthetic)."""
    random.seed((run_seed + 50) if run_seed is not None else 50)
    buckets = [
        ("logs-prod", "us-east-1", "STANDARD", 4500, "Enable lifecycle to Glacier", 120),
        ("backups-acct", "us-east-1", "STANDARD", 8900, "Move to S3 IA or Glacier", 210),
        ("assets-cdn", "us-west-2", "STANDARD", 1200, "Consider CloudFront for infrequent access", 45),
        ("data-lake", "us-east-1", "STANDARD", 25000, "Use Intelligent-Tiering", 380),
        ("temp-processing", "us-east-2", "STANDARD", 800, "Enable lifecycle delete after 7 days", 65),
        ("archive-compliance", "eu-west-1", "GLACIER", 50000, "OK — already in Glacier", 0),
    ]
    rows = []
    for bucket, region, storage_class, size_gb, rec, pot in buckets:
        base_cost = 0.023 * size_gb if storage_class == "STANDARD" else 0.004 * size_gb
        monthly = round(base_cost * (0.9 + random.random() * 0.2), 2)
        rows.append({
            "bucket_name": bucket,
            "region": region,
            "storage_class": storage_class,
            "size_gb": size_gb,
            "monthly_cost_usd": monthly,
            "recommendation": rec,
            "potential_savings_usd": round(pot * (0.8 + random.random() * 0.4), 2),
        })
    return pd.DataFrame(rows)


def _build_data_transfer_df(run_seed: int | None = None) -> pd.DataFrame:
    """Data transfer records with optimization recommendations (synthetic)."""
    random.seed((run_seed + 51) if run_seed is not None else 51)
    transfers = [
        ("us-east-1", "USE1-DataTransfer-Out-Bytes", "Internet", "egress", 1200, "Review CloudFront for static content", 180),
        ("us-west-2", "USW2-DataTransfer-Regional-Bytes", "Inter-region", "us-east-1", 450, "Consolidate regions or use VPC peering", 90),
        ("eu-west-1", "EUW1-DataTransfer-Out-Bytes", "Internet", "egress", 800, "Enable compression", 60),
        ("us-east-1", "USE1-AWS-In-Bytes", "Internet", "egress", 2000, "Review CDN usage", 250),
    ]
    rows = []
    for region, usage_type, transfer_type, dest, gb, rec, pot in transfers:
        monthly = round(0.09 * gb * (0.9 + random.random() * 0.2), 2)
        rows.append({
            "region": region,
            "usage_type": usage_type,
            "transfer_type": transfer_type,
            "destination": dest,
            "data_gb": gb,
            "monthly_cost_usd": monthly,
            "recommendation": rec,
            "potential_savings_usd": round(pot * (0.8 + random.random() * 0.4), 2),
        })
    return pd.DataFrame(rows)


def _build_databases_df(run_seed: int | None = None) -> pd.DataFrame:
    """RDS and DynamoDB with optimization recommendations (synthetic)."""
    random.seed((run_seed + 52) if run_seed is not None else 52)
    rows = [
        ("rds-prod-1", "RDS", "db.t3.medium", "us-east-1", 95.0, "Review reserved instance eligibility", 28),
        ("rds-staging", "RDS", "db.t3.small", "us-east-1", 35.0, "Consider Aurora Serverless for variable load", 12),
        ("rds-analytics", "RDS", "db.r5.xlarge", "us-east-2", 420.0, "Right-size — low CPU utilization", 95),
        ("ddb-sessions", "DynamoDB", "On-Demand", "us-east-1", 180.0, "Consider provisioned for steady load", 45),
        ("ddb-events", "DynamoDB", "On-Demand", "us-west-2", 95.0, "OK — usage is variable", 0),
    ]
    out = []
    for db_id, db_type, instance_or_mode, region, monthly, rec, pot in rows:
        out.append({
            "resource_id": db_id,
            "service": db_type,
            "instance_type": instance_or_mode,
            "region": region,
            "monthly_cost_usd": round(monthly * (0.9 + random.random() * 0.2), 2),
            "recommendation": rec,
            "potential_savings_usd": round(pot * (0.8 + random.random() * 0.4), 2),
        })
    return pd.DataFrame(out)


def _build_ec2_sp_alignment_df(ec2_df: pd.DataFrame) -> pd.DataFrame:
    """Alignment dataframe from EC2 (same columns as real alignment scanner output)."""
    rows = []
    for _, row in ec2_df.iterrows():
        if row["state"] != "running":
            continue
        cpu = row["avg_cpu_7d"]
        monthly = row["monthly_cost_usd"]
        ondemand_hr = monthly / (24 * 30) if monthly else 0.0
        idle = row["idle_score"]
        sp_covered = row.get("billing_type", "On-Demand") == "SP-Covered"
        sp_hr = ondemand_hr if sp_covered else 0.0
        if sp_covered and cpu < 20:
            flag = "Low-util consuming SP"
            rec = "Rightsize/Stop" if cpu >= 5 else "Stop instance"
            pot = monthly * 0.6 if cpu >= 5 else monthly
        elif sp_covered:
            flag = "Aligned"
            rec = "No action"
            pot = 0.0
        elif cpu >= 50:
            flag = "Not covered high-util"
            rec = "Purchase SP"
            pot = ondemand_hr * 0.35 * 24 * 30
        else:
            flag = "Not covered medium-util" if cpu >= 20 else "Not covered low-util"
            rec = "Consider SP" if cpu >= 20 else "Review instance sizing"
            pot = ondemand_hr * 0.3 * 24 * 30 if cpu >= 20 else 0.0
        rows.append({
            "Instance ID": row["instance_id"],
            "Region": row["region"],
            "State": row["state"].title(),
            "CPU Utilization %": round(cpu, 1),
            "Idle Score": idle,
            "On-Demand Rate ($/hr)": round(ondemand_hr, 4),
            "SP Coverage ($/hr)": round(sp_hr, 4),
            "Alignment Flag": flag,
            "Potential Savings (Monthly)": round(pot, 2),
            "Recommendation": rec,
            "Instance Type": row["instance_type"],
        })
    return pd.DataFrame(rows)


def load_synthetic_data_into_session() -> None:
    """Populate session state with synthetic data. Real scan overwrites when run.
    Sets storage_df, data_transfer_df, databases_df so all tabs (Storage, Data Transfer, Databases) work; data_source = "synthetic".
    Uses a time-based seed so each load/refresh produces different amounts and recommendations.
    """
    from cwt_ui.services.spend_aggregate import get_unified_optimization_metrics, get_spend_from_scan
    # Time-based seed so each load gives different synthetic data (amounts and recommendations)
    run_seed = int(datetime.now(timezone.utc).timestamp() * 1000)
    # Reset "Mark as resolved" state when loading new data
    st.session_state["resolved_recommendations"] = []
    try:
        from cwt_ui.utils.resolved_persistence import clear_resolved
        clear_resolved()
    except Exception:
        pass
    # Store previous metrics for "vs last scan" before overwriting
    prev_opt = st.session_state.get("optimization_potential", 0)
    prev_act = st.session_state.get("action_count", 0)
    try:
        prev_total, _ = get_spend_from_scan()
        st.session_state["previous_spend_total"] = float(prev_total or 0)
    except Exception:
        st.session_state["previous_spend_total"] = None
    ec2_df = _build_ec2_df(run_seed)
    st.session_state["ec2_df"] = ec2_df
    st.session_state["lambda_df"] = _build_lambda_df(run_seed)
    st.session_state["fargate_df"] = _build_fargate_df(run_seed)
    st.session_state["SP_DF"] = _build_sp_df()
    st.session_state["SP_SUMMARY"] = _build_sp_summary()
    st.session_state["SP_UTIL_TREND"] = _build_sp_util_trend()
    st.session_state["SP_COVERAGE_TREND"] = _build_sp_coverage_trend()
    st.session_state["EC2_SP_ALIGNMENT_DF"] = _build_ec2_sp_alignment_df(ec2_df)
    st.session_state["storage_df"] = _build_storage_df(run_seed)
    st.session_state["data_transfer_df"] = _build_data_transfer_df(run_seed)
    st.session_state["databases_df"] = _build_databases_df(run_seed)
    # Set waste hero from unified metrics (EC2 + Lambda + Fargate + Storage + Data Transfer + Databases)
    opt, act = get_unified_optimization_metrics()
    st.session_state["previous_optimization_potential"] = prev_opt
    st.session_state["previous_action_count"] = prev_act
    st.session_state["optimization_potential"] = opt
    st.session_state["action_count"] = act
    st.session_state["last_scan_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["data_source"] = "synthetic"
