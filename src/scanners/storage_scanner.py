# src/scanners/storage_scanner.py
"""
Real S3 Storage scanner. Lists buckets, gets location and versioning/lifecycle,
and returns rows matching the Storage tab contract (storage_tab._REQUIRED_STORAGE_COLS).
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# ----------------------
# Settings / constants
# ----------------------
DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Contract columns expected by storage_tab (storage_tab._REQUIRED_STORAGE_COLS)
REQUIRED_STORAGE_COLS = [
    "bucket_name",
    "region",
    "storage_class",
    "size_gb",
    "monthly_cost_usd",
    "recommendation",
    "potential_savings_usd",
]


# ----------------------
# Helpers
# ----------------------
def _aws_client(
    service: str,
    region: str,
    aws_credentials: Optional[Dict[str, str]] = None,
):
    """Create AWS client with optional credentials override.
    When aws_credentials is None, use environment variables (e.g. from _temporary_env).
    """
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


def _bucket_region(s3_client, bucket_name: str) -> Optional[str]:
    """Return bucket region; us-east-1 is returned as None by API, normalize to 'us-east-1'."""
    try:
        resp = s3_client.get_bucket_location(Bucket=bucket_name)
        loc = resp.get("LocationConstraint")
        if loc is None or loc == "":
            return "us-east-1"
        return str(loc)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        print(f"WARN: get_bucket_location failed for {bucket_name}: {code}")
        return None
    except Exception as e:
        print(f"WARN: get_bucket_location failed for {bucket_name}: {e}")
        return None


def _bucket_versioning(s3_client, bucket_name: str) -> str:
    """Return 'Enabled', 'Suspended', or 'None' (no versioning)."""
    try:
        resp = s3_client.get_bucket_versioning(Bucket=bucket_name)
        status = (resp.get("Status") or "").strip() or "None"
        return status if status else "None"
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        print(f"WARN: get_bucket_versioning failed for {bucket_name}: {code}")
        return "None"
    except Exception as e:
        print(f"WARN: get_bucket_versioning failed for {bucket_name}: {e}")
        return "None"


def _bucket_has_lifecycle(s3_client, bucket_name: str) -> bool:
    """True if bucket has at least one lifecycle rule."""
    try:
        s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchLifecycleConfiguration", "404"):
            return False
        print(f"WARN: get_bucket_lifecycle_configuration failed for {bucket_name}: {code}")
        return False
    except Exception as e:
        print(f"WARN: get_bucket_lifecycle_configuration failed for {bucket_name}: {e}")
        return False


def _recommendation(
    storage_class: str,
    has_lifecycle: bool,
    versioning: str,
) -> tuple[str, float]:
    """Rule-based recommendation and potential_savings_usd. Returns (recommendation, potential_savings_usd)."""
    if storage_class in ("GLACIER", "DEEP_ARCHIVE", "GLACIER_IR"):
        return ("OK — cold storage.", 0.0)
    if has_lifecycle:
        return ("Lifecycle configured. Review for further savings.", 0.0)
    if storage_class in ("STANDARD_IA", "INTELLIGENT_TIERING", "ONEZONE_IA"):
        return ("Consider lifecycle to Glacier for rarely accessed data.", 0.0)
    # STANDARD or unknown, no lifecycle
    return (
        "Consider S3 IA or lifecycle to Glacier for rarely accessed data.",
        0.0,
    )


# ----------------------
# Scanner
# ----------------------
def scan_storage(
    regions: Optional[List[str]] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Scan S3 buckets and return rows matching the Storage tab contract.

    ListBuckets is global; we list once then filter by bucket region.
    For each bucket we get location, versioning, and lifecycle (if any).
    Storage class is assumed STANDARD at bucket level (per-object class not enumerated).

    Args:
        regions: If provided, only include buckets in these regions. If None, include all.
        aws_credentials: Optional credentials dict; else uses env (e.g. from _temporary_env).

    Returns:
        List of dicts with keys: bucket_name, region, storage_class, size_gb,
        monthly_cost_usd, recommendation, potential_savings_usd.
    """
    # ListBuckets is global; use a single region for the client (e.g. us-east-1)
    s3_region = DEFAULT_REGION
    s3 = _aws_client("s3", s3_region, aws_credentials)
    findings: List[Dict] = []

    try:
        resp = s3.list_buckets()
        buckets = resp.get("Buckets") or []
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        print(f"ERROR: list_buckets failed: {error_code} - {error_message}")
        # Let the caller distinguish permission vs other AWS errors
        raise
    except Exception as e:
        print(f"ERROR: list_buckets failed: {e}")
        raise

    for b in buckets:
        bucket_name = b.get("Name") or ""
        if not bucket_name:
            continue
        region = _bucket_region(s3, bucket_name)
        if region is None:
            continue
        if regions is not None and region not in regions:
            continue

        versioning = _bucket_versioning(s3, bucket_name)
        has_lifecycle = _bucket_has_lifecycle(s3, bucket_name)
        storage_class = "STANDARD"  # bucket-level; per-object class not available from list API
        rec_text, savings = _recommendation(storage_class, has_lifecycle, versioning)

        row = {
            "bucket_name": bucket_name,
            "region": region,
            "storage_class": storage_class,
            "size_gb": None,  # not available without CloudWatch/CE or inventory
            "monthly_cost_usd": 0.0,  # can be filled by Cost Explorer in a later step
            "recommendation": rec_text,
            "potential_savings_usd": savings,
        }
        findings.append(row)

    return findings


def scan_storage_single_region(
    region: str,
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Scan S3 buckets in a single region. Convenience wrapper around scan_storage.
    """
    return scan_storage(regions=[region], aws_credentials=aws_credentials)


# ----------------------
# Public entry points
# ----------------------
def run(
    regions: Optional[List[str]] = None,
    aws_credentials: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """
    Scan S3 storage and return list of dicts for the scan service.
    If regions is None, all buckets (all regions) are returned.
    """
    regions = regions or None  # None means no filter
    return scan_storage(regions=regions, aws_credentials=aws_credentials)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cloud Waste Tracker – S3 Storage Scanner")
    parser.add_argument("--region", default=None, help="Single region to filter (default: all)")
    parser.add_argument("--regions", default=None, help="Comma-separated regions to filter")
    args = parser.parse_args()

    reg_list = None
    if args.regions:
        reg_list = [r.strip() for r in args.regions.split(",") if r.strip()]
    elif args.region:
        reg_list = [args.region]

    findings = run(regions=reg_list)
    for row in findings:
        rec = (row["recommendation"] or "")[:60]
        if len(row.get("recommendation") or "") > 60:
            rec += "..."
        print(f"[S3] {row['bucket_name']} region={row['region']} class={row['storage_class']} — {rec}")
    print(f"Total buckets: {len(findings)}")
