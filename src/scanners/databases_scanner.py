# src/scanners/databases_scanner.py
"""
Real Databases (RDS + DynamoDB) scanner. Returns rows matching the Databases tab contract
(databases_tab._REQUIRED_DB_COLS). One entry point returns combined RDS + DynamoDB rows.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# ----------------------
# Settings / constants
# ----------------------
DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

REQUIRED_DB_COLS = [
    "resource_id",
    "service",
    "instance_type",
    "region",
    "monthly_cost_usd",
    "recommendation",
    "potential_savings_usd",
]

# Lookback for RDS CPU metric (days)
RDS_CPU_LOOKBACK_DAYS = 7
# Below this average CPU we suggest right-size or reserved
RDS_LOW_CPU_THRESHOLD = 25.0

# Rough RDS monthly $ (single-AZ, ~720h) for common instance classes; else estimate
RDS_MONTHLY_ESTIMATE = {
    "db.t3.micro": 15.0,
    "db.t3.small": 30.0,
    "db.t3.medium": 60.0,
    "db.t3.large": 120.0,
    "db.t4g.micro": 13.0,
    "db.t4g.small": 26.0,
    "db.t4g.medium": 52.0,
    "db.m5.large": 140.0,
    "db.m5.xlarge": 280.0,
    "db.r5.large": 200.0,
    "db.r5.xlarge": 400.0,
}


# ----------------------
# Helpers
# ----------------------
def _aws_client(
    service: str,
    region: str,
    aws_credentials: Optional[Dict[str, str]] = None,
):
    """Create AWS client; credentials from dict or env (e.g. _temporary_env)."""
    if aws_credentials and aws_credentials.get("AWS_ACCESS_KEY_ID"):
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=aws_credentials.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_credentials.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=aws_credentials.get("AWS_SESSION_TOKEN"),
        )
    return boto3.client(
        service,
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def _rds_monthly_estimate(instance_class: str) -> float:
    """Rough monthly USD for RDS instance class; 0 if unknown."""
    if not instance_class:
        return 0.0
    return RDS_MONTHLY_ESTIMATE.get(instance_class, 0.0)


def _rds_avg_cpu(
    cw_client: Any,
    db_instance_id: str,
    region: str,
    lookback_days: int = RDS_CPU_LOOKBACK_DAYS,
) -> Optional[float]:
    """Return average CPU utilization over lookback period, or None if unavailable."""
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days)
        resp = cw_client.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_instance_id}],
            StartTime=start,
            EndTime=end,
            Period=3600 * 6,
            Statistics=["Average"],
        )
        dps = resp.get("Datapoints", [])
        if not dps:
            return None
        return sum(dp["Average"] for dp in dps) / len(dps)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        print(f"WARN: RDS CloudWatch CPU failed for {db_instance_id} in {region}: {code}")
        return None
    except Exception as e:
        print(f"WARN: RDS CloudWatch CPU failed for {db_instance_id}: {e}")
        return None


def _rds_recommendation(avg_cpu: Optional[float], monthly_cost: float) -> tuple[str, float]:
    """Rule-based RDS recommendation and potential_savings_usd."""
    if avg_cpu is not None and avg_cpu < RDS_LOW_CPU_THRESHOLD and monthly_cost > 0:
        return (
            "Low CPU utilization — consider right-sizing or reserved instance.",
            0.0,
        )
    if monthly_cost > 50:
        return ("Review reserved instance eligibility for committed use savings.", 0.0)
    return ("OK — review periodically.", 0.0)


def _dynamodb_recommendation(billing_mode: str, monthly_cost: float) -> tuple[str, float]:
    """Simple DynamoDB recommendation."""
    if billing_mode == "On-Demand" and monthly_cost > 100:
        return ("Consider provisioned capacity for steady, predictable workload.", 0.0)
    if billing_mode == "Provisioned" and monthly_cost > 50:
        return ("Review provisioned throughput vs usage; consider auto scaling.", 0.0)
    return ("OK — review periodically.", 0.0)


# ----------------------
# RDS scanner
# ----------------------
def _scan_rds(
    regions: List[str],
    aws_credentials: Optional[Dict[str, str]] = None,
    include_cloudwatch_cpu: bool = True,
) -> List[Dict[str, Any]]:
    """Scan RDS instances in the given regions. Returns list of dicts matching _REQUIRED_DB_COLS."""
    findings: List[Dict[str, Any]] = []

    for region in regions:
        try:
            rds = _aws_client("rds", region, aws_credentials)
            cw = _aws_client("cloudwatch", region, aws_credentials) if include_cloudwatch_cpu else None
        except Exception as e:
            print(f"WARN: Failed to create RDS/CloudWatch client in {region}: {e}")
            continue

        marker: Optional[str] = None
        while True:
            try:
                params: Dict[str, Any] = {"MaxRecords": 100}
                if marker:
                    params["Marker"] = marker
                resp = rds.describe_db_instances(**params)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "Unknown")
                msg = e.response.get("Error", {}).get("Message", str(e))
                print(f"ERROR: describe_db_instances failed in {region}: {code} - {msg}")
                if code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
                    # Bubble up permission errors so the UI can show a clear message
                    raise
                break
            except Exception as e:
                print(f"ERROR: describe_db_instances failed in {region}: {e}")
                raise

            for db in resp.get("DBInstances", []) or []:
                db_id = (db.get("DBInstanceIdentifier") or "").strip()
                if not db_id:
                    continue
                instance_class = (db.get("DBInstanceClass") or "").strip() or "—"
                monthly = _rds_monthly_estimate(instance_class)
                avg_cpu = None
                if cw:
                    avg_cpu = _rds_avg_cpu(cw, db_id, region)
                rec, savings = _rds_recommendation(avg_cpu, monthly)

                findings.append({
                    "resource_id": db_id,
                    "service": "RDS",
                    "instance_type": instance_class,
                    "region": region,
                    "monthly_cost_usd": monthly,
                    "recommendation": rec,
                    "potential_savings_usd": savings,
                })

            marker = resp.get("Marker")
            if not marker:
                break

    return findings


# ----------------------
# DynamoDB scanner
# ----------------------
def _scan_dynamodb(
    regions: List[str],
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Scan DynamoDB tables in the given regions. Returns list of dicts matching _REQUIRED_DB_COLS."""
    findings: List[Dict[str, Any]] = []

    for region in regions:
        try:
            ddb = _aws_client("dynamodb", region, aws_credentials)
        except Exception as e:
            print(f"WARN: Failed to create DynamoDB client in {region}: {e}")
            continue

        table_names: List[str] = []
        try:
            paginator = ddb.get_paginator("list_tables")
            for page in paginator.paginate():
                table_names.extend(page.get("TableNames", []) or [])
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "Unknown")
            msg = e.response.get("Error", {}).get("Message", str(e))
            print(f"ERROR: list_tables failed in {region}: {code} - {msg}")
            if code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "UnauthorizedException"):
                # Bubble up permission errors so the UI can show a clear message
                raise
            continue
        except Exception as e:
            print(f"ERROR: list_tables failed in {region}: {e}")
            raise

        for table_name in table_names:
            billing_mode = "On-Demand"
            try:
                desc = ddb.describe_table(TableName=table_name)
                summary = (desc.get("Table") or {}).get("BillingModeSummary") or {}
                mode = (summary.get("BillingMode") or "").strip()
                if mode == "PAY_PER_REQUEST":
                    billing_mode = "On-Demand"
                elif mode:
                    billing_mode = "Provisioned"
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                print(f"WARN: describe_table failed for {table_name} in {region}: {code}")
            except Exception as e:
                print(f"WARN: describe_table failed for {table_name}: {e}")

            monthly = 0.0  # Cost Explorer can fill later
            rec, savings = _dynamodb_recommendation(billing_mode, monthly)

            findings.append({
                "resource_id": table_name,
                "service": "DynamoDB",
                "instance_type": billing_mode,
                "region": region,
                "monthly_cost_usd": monthly,
                "recommendation": rec,
                "potential_savings_usd": savings,
            })

    return findings


# ----------------------
# Combined scanner
# ----------------------
def scan_databases(
    regions: Optional[List[str]] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
    include_rds_cpu: bool = True,
) -> List[Dict[str, Any]]:
    """
    Scan RDS and DynamoDB in the given regions and return combined rows for the Databases tab.

    Args:
        regions: List of regions to scan. If None, uses [DEFAULT_REGION].
        aws_credentials: Optional credentials dict; else uses env.
        include_rds_cpu: If True, fetch CloudWatch CPU for RDS for recommendations.

    Returns:
        List of dicts with keys: resource_id, service, instance_type, region,
        monthly_cost_usd, recommendation, potential_savings_usd.
    """
    if not regions:
        regions = [DEFAULT_REGION]

    rds_rows = _scan_rds(regions, aws_credentials, include_cloudwatch_cpu=include_rds_cpu)
    ddb_rows = _scan_dynamodb(regions, aws_credentials)
    return rds_rows + ddb_rows


# ----------------------
# Public entry points
# ----------------------
def run(
    regions: Optional[List[str]] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Scan RDS + DynamoDB and return list of dicts for the scan service."""
    return scan_databases(regions=regions, aws_credentials=aws_credentials)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cloud Waste Tracker – Databases (RDS + DynamoDB) Scanner"
    )
    parser.add_argument("--region", default=None, help="Single region")
    parser.add_argument("--regions", default=None, help="Comma-separated regions")
    args = parser.parse_args()

    reg_list = None
    if args.regions:
        reg_list = [r.strip() for r in args.regions.split(",") if r.strip()]
    elif args.region:
        reg_list = [args.region]

    findings = run(regions=reg_list)
    for row in findings:
        print(
            f"[{row['service']}] {row['resource_id']} {row['instance_type']} "
            f"region={row['region']} cost={row['monthly_cost_usd']}"
        )
    print(f"Total: {len(findings)}")
