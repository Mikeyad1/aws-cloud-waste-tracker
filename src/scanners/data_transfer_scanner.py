# src/scanners/data_transfer_scanner.py
"""
Real Data Transfer scanner using AWS Cost Explorer.
Returns rows matching the Data Transfer tab contract (data_transfer_tab._REQUIRED_DT_COLS).
Cost Explorer is global (us-east-1); no region loop.
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
CE_REGION = "us-east-1"

# Contract columns expected by data_transfer_tab (_REQUIRED_DT_COLS)
REQUIRED_DT_COLS = [
    "region",
    "transfer_type",
    "destination",
    "data_gb",
    "monthly_cost_usd",
    "recommendation",
    "potential_savings_usd",
]

# Rough $/GB for estimation (internet egress ~0.09, inter-region varies)
DEFAULT_EGRESS_USD_PER_GB = 0.09


# ----------------------
# Helpers
# ----------------------
def _ce_client(aws_credentials: Optional[Dict[str, str]] = None):
    """Cost Explorer client in us-east-1. Credentials from env if None."""
    if aws_credentials and aws_credentials.get("AWS_ACCESS_KEY_ID"):
        return boto3.client(
            "ce",
            region_name=CE_REGION,
            aws_access_key_id=aws_credentials.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_credentials.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=aws_credentials.get("AWS_SESSION_TOKEN"),
        )
    # When aws_credentials is None, rely on current process env / default session.
    # This lets _temporary_env (assumed role) control which keys are used.
    if os.getenv("APP_ENV", "development").strip().lower() != "production":
        from boto3.session import Session as _Session
        _sess = _Session()
        _creds = _sess.get_credentials()
        print("DEBUG: _ce_client() using default credential chain")
        print(f"  AWS_PROFILE: {os.getenv('AWS_PROFILE')!r}")
        print(f"  AWS_ACCESS_KEY_ID env set?: {bool(os.getenv('AWS_ACCESS_KEY_ID'))}")
        print(f"  boto3.Session credentials: {_creds.get_frozen_credentials() if _creds else None}")
    return boto3.client("ce", region_name=CE_REGION)


def _this_month_period() -> tuple[str, str]:
    """Return (Start, End) date strings for current month to date."""
    end = datetime.now(timezone.utc).date()
    start = end.replace(day=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _usage_type_to_transfer_type_dest(usage_type: str, region: str) -> tuple[str, str]:
    """
    Map CE usage type string to (transfer_type, destination).
    e.g. DataTransfer-Out-Bytes -> (Internet, egress); Regional -> (Intra-region, region).
    """
    u = (usage_type or "").upper()
    if "OUT-BYTES" in u or "OUTBYTES" in u or "EGRESS" in u:
        if "REGION" in u or "INTER-REGION" in u or "REGIONAL" in u:
            return ("Inter-region", "other region")
        return ("Internet", "egress")
    if "IN-BYTES" in u or "INBOUND" in u:
        return ("Inbound", "inbound")
    if "REGIONAL" in u or "REGION-TO-REGION" in u:
        return ("Inter-region", "other region")
    if "TRANSFER" in u:
        return ("Data Transfer", "egress")
    return ("Data Transfer", "—")


def _estimate_data_gb(cost_usd: float, usage_type: str) -> Optional[float]:
    """Rough data_gb from cost when usage type suggests egress (e.g. $0.09/GB)."""
    if cost_usd <= 0:
        return None
    u = (usage_type or "").upper()
    if "OUT" in u and ("BYTES" in u or "EGRESS" in u):
        return round(cost_usd / DEFAULT_EGRESS_USD_PER_GB, 2)
    return None


def _recommendation(transfer_type: str, monthly_cost_usd: float) -> tuple[str, float]:
    """Simple rule-based recommendation and potential_savings_usd."""
    if monthly_cost_usd < 1.0:
        return ("Low spend; no action required.", 0.0)
    if transfer_type == "Internet":
        return (
            "Review CloudFront or other CDN for static content to reduce egress.",
            0.0,
        )
    if transfer_type == "Inter-region":
        return (
            "Review inter-region traffic; consolidate resources or use VPC peering where possible.",
            0.0,
        )
    return ("Review data transfer patterns for optimization.", 0.0)


# ----------------------
# Scanner
# ----------------------
def scan_data_transfer(
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Query Cost Explorer for AWS Data Transfer costs and return rows for the Data Transfer tab.

    Uses get_cost_and_usage with Filter SERVICE = "AWS Data Transfer",
    GroupBy REGION and USAGE_TYPE. Cost Explorer is global (us-east-1).

    Returns:
        List of dicts with keys: region, transfer_type, destination, data_gb,
        monthly_cost_usd, recommendation, potential_savings_usd.
    """
    start_str, end_str = _this_month_period()
    findings: List[Dict[str, Any]] = []

    try:
        ce = _ce_client(aws_credentials)
        token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {
                "TimePeriod": {"Start": start_str, "End": end_str},
                "Granularity": "MONTHLY",
                "Metrics": ["UnblendedCost"],
                "GroupBy": [
                    {"Type": "DIMENSION", "Key": "REGION"},
                    {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
                ],
                "Filter": {
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": ["AWS Data Transfer"],
                    }
                },
            }
            if token:
                params["NextPageToken"] = token

            resp = ce.get_cost_and_usage(**params)

            for result in resp.get("ResultsByTime", []) or []:
                for group in result.get("Groups", []) or []:
                    keys = group.get("Keys", [])
                    if len(keys) < 2:
                        continue
                    region = (keys[0] or "").strip() or "—"
                    usage_type = (keys[1] or "").strip() or "—"
                    amount = 0.0
                    try:
                        amount = float(
                            group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0)
                        )
                    except (TypeError, ValueError):
                        pass
                    if amount <= 0:
                        continue

                    transfer_type, destination = _usage_type_to_transfer_type_dest(
                        usage_type, region
                    )
                    data_gb = _estimate_data_gb(amount, usage_type)
                    rec_text, savings = _recommendation(transfer_type, amount)

                    row = {
                        "region": region,
                        "usage_type": usage_type,
                        "transfer_type": transfer_type,
                        "destination": destination,
                        "data_gb": data_gb if data_gb is not None else 0.0,
                        "monthly_cost_usd": round(amount, 2),
                        "recommendation": rec_text,
                        "potential_savings_usd": round(savings, 2),
                    }
                    findings.append(row)

            token = resp.get("NextPageToken")
            if not token:
                break

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: Cost Explorer get_cost_and_usage failed: {error_code} - {error_message}")
        return []
    except Exception as e:
        print(f"ERROR: Data transfer scan failed: {e}")
        return []

    return findings


# ----------------------
# Public entry points
# ----------------------
def run(aws_credentials: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Scan data transfer costs via Cost Explorer and return list of dicts for the scan service.
    """
    return scan_data_transfer(aws_credentials=aws_credentials)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cloud Waste Tracker – Data Transfer (Cost Explorer) Scanner"
    )
    parser.parse_args()

    findings = run()
    for row in findings:
        gb = row.get("data_gb") or 0
        print(
            f"[DT] {row['region']} {row['transfer_type']} -> {row['destination']} "
            f"cost={row['monthly_cost_usd']:.2f} USD data_gb={gb}"
        )
    print(f"Total rows: {len(findings)}")
