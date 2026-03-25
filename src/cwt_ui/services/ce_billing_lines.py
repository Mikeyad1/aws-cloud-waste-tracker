# Cost Explorer usage-type lines (month-to-date) for Waste recommendation cards.
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Generator, Mapping

import boto3
from botocore.exceptions import ClientError

# Logical service key → AWS Cost Explorer SERVICE dimension value(s).
# EC2 is split across two CE service names.
AWS_CE_SERVICE_NAMES: dict[str, list[str]] = {
    "EC2": [
        "Amazon Elastic Compute Cloud - Compute",
        "Amazon Elastic Compute Cloud - Other",
    ],
    "Lambda": ["AWS Lambda"],
    "Fargate": ["Amazon Elastic Container Service"],
    "S3": ["Amazon Simple Storage Service"],
    "RDS": ["Amazon Relational Database Service"],
    "DynamoDB": ["Amazon DynamoDB"],
}

CE_REGION = "us-east-1"
_MAX_LINES = 40


def service_to_ce_logical_key(service: str) -> str | None:
    """Map unified row Service label to a key in AWS_CE_SERVICE_NAMES."""
    s = (service or "").strip()
    if not s or s == "Data Transfer":
        return None
    if s == "EC2":
        return "EC2"
    if s == "Lambda":
        return "Lambda"
    if s == "Fargate":
        return "Fargate"
    if s == "S3":
        return "S3"
    su = s.upper()
    if "DYNAMO" in su:
        return "DynamoDB"
    if "RDS" in su or "AURORA" in su:
        return "RDS"
    return None


def _month_to_date_period() -> tuple[str, str]:
    """Exclusive end date per GetCostAndUsage API."""
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    end_exclusive = today + timedelta(days=1)
    return month_start.strftime("%Y-%m-%d"), end_exclusive.strftime("%Y-%m-%d")


def _filter_region_and_services(region: str, service_names: list[str]) -> dict[str, Any]:
    if len(service_names) == 1:
        svc_filter: dict[str, Any] = {"Dimensions": {"Key": "SERVICE", "Values": service_names}}
    else:
        svc_filter = {
            "Or": [{"Dimensions": {"Key": "SERVICE", "Values": [name]}} for name in service_names],
        }
    return {
        "And": [
            {"Dimensions": {"Key": "REGION", "Values": [region]}},
            svc_filter,
        ]
    }


def fetch_ce_usage_lines(ce_client: Any, logical_key: str, region: str) -> list[dict[str, Any]]:
    """
    Return billing-style rows: [{"line": str, "amount_usd": float}, ...]
    Grouped by USAGE_TYPE for the given CE service(s) and region, month to date.
    """
    service_names = AWS_CE_SERVICE_NAMES.get(logical_key)
    if not service_names or not region or region.strip() in ("", "—", "None"):
        return []

    start, end = _month_to_date_period()
    filt = _filter_region_and_services(region.strip(), service_names)
    out: list[dict[str, Any]] = []
    token: str | None = None

    while True:
        kwargs: dict[str, Any] = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": "MONTHLY",
            "Metrics": ["UnblendedCost"],
            "Filter": filt,
            "GroupBy": [{"Type": "DIMENSION", "Key": "USAGE_TYPE"}],
        }
        if token:
            kwargs["NextPageToken"] = token
        try:
            resp = ce_client.get_cost_and_usage(**kwargs)
        except ClientError:
            return []
        except Exception:
            return []

        for period in resp.get("ResultsByTime") or []:
            for group in period.get("Groups") or []:
                keys = group.get("Keys") or []
                usage_type = keys[0] if keys else "—"
                try:
                    amt_s = (group.get("Metrics") or {}).get("UnblendedCost", {}).get("Amount", "0")
                    amt = float(amt_s or 0)
                except (TypeError, ValueError):
                    amt = 0.0
                if amt <= 0:
                    continue
                out.append(
                    {
                        "line": (
                            f"Service **{logical_key}** · Region **{region}** · Usage type **{usage_type}**"
                        ),
                        "amount_usd": round(amt, 4),
                        "usage_type": usage_type,
                    }
                )

        token = resp.get("NextPageToken")
        if not token:
            break

    out.sort(key=lambda x: float(x.get("amount_usd", 0) or 0), reverse=True)
    return out[:_MAX_LINES]


@contextmanager
def ce_client_context(session_state: Mapping[str, Any]) -> Generator[Any, None, None]:
    """Use the same credential path as scans (role assume or session keys or env)."""
    from cwt_ui.services.scans import _assume_role, _temporary_env

    override = session_state.get("aws_override_enabled", False)
    if override and session_state.get("aws_auth_method") == "role" and session_state.get("aws_role_arn"):
        creds = {
            "AWS_ROLE_ARN": str(session_state.get("aws_role_arn", "") or ""),
            "AWS_EXTERNAL_ID": str(session_state.get("aws_external_id", "") or ""),
            "AWS_ROLE_SESSION_NAME": str(session_state.get("aws_role_session_name", "") or "CloudWasteTracker"),
            "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        }
        assumed = _assume_role(creds)
        if assumed:
            with _temporary_env(assumed):
                yield boto3.client("ce", region_name=CE_REGION)
            return

    if override and session_state.get("aws_auth_method") != "role":
        ak = str(session_state.get("aws_access_key_id", "") or "")
        sk = str(session_state.get("aws_secret_access_key", "") or "")
        if ak and sk:
            creds = {
                "AWS_ACCESS_KEY_ID": ak,
                "AWS_SECRET_ACCESS_KEY": sk,
                "AWS_SESSION_TOKEN": str(session_state.get("aws_session_token", "") or ""),
                "AWS_DEFAULT_REGION": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            }
            with _temporary_env(creds):
                yield boto3.client("ce", region_name=CE_REGION)
            return

    yield boto3.client("ce", region_name=CE_REGION)


def _synthetic_ce_lines(logical: str, region: str) -> list[dict[str, Any]]:
    """Demo-only: same *shape* as Cost Explorer lines (labels only — no dollar amounts)."""
    presets: dict[str, list[str]] = {
        "EC2": ["BoxUsage:t3.micro (Hrs)", "DataTransfer-Out-Bytes"],
        "Lambda": ["Lambda-GB-Second", "Request"],
        "Fargate": ["Fargate-vCPU-Hours:perCPU", "Fargate-GB-Hours"],
        "S3": ["TimedStorage-ByteHrs", "Requests-Tier1"],
        "RDS": ["InstanceUsage:db.t3.medium", "StorageUsage"],
        "DynamoDB": ["TimedStorage-ByteHrs", "ReadRequestUnits"],
    }
    usages = presets.get(logical, ["Example-Usage-Type"])
    lines: list[dict[str, Any]] = []
    for usage in usages:
        lines.append(
            {
                "line": f"Service **{logical}** · Region **{region}** · Usage type **{usage}**",
            }
        )
    return lines


def ensure_ce_billing_lines_cache(
    session_state: Any,
    unified_rows: list[dict],
    last_scan_at: str,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """
    Fetch and cache CE usage-type lines per (logical_key, region).
    Invalidates when last_scan_at changes.
    """
    if session_state.get("data_source") != "real":
        return dict(session_state.get("ce_billing_lines_cache") or {})

    cached_at = session_state.get("ce_billing_lines_cache_scan_at")
    cache: dict[tuple[str, str], list[dict[str, Any]]] | None = session_state.get("ce_billing_lines_cache")

    key_ts = str(last_scan_at or "")
    if cache is not None and cached_at == key_ts:
        return cache

    pairs: set[tuple[str, str]] = set()
    for r in unified_rows:
        logical = service_to_ce_logical_key(str(r.get("Service", "") or ""))
        region = str(r.get("region") or "").strip()
        if not logical or region in ("", "—", "None"):
            continue
        pairs.add((logical, region))

    new_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    if pairs:
        with ce_client_context(session_state) as ce:
            for logical, region in sorted(pairs):
                new_cache[(logical, region)] = fetch_ce_usage_lines(ce, logical, region)

    session_state["ce_billing_lines_cache"] = new_cache
    session_state["ce_billing_lines_cache_scan_at"] = key_ts
    return new_cache


def attach_ce_billing_lines_to_rows(
    rows: list[dict],
    *,
    cache: dict[tuple[str, str], list[dict[str, Any]]],
    data_source: str,
) -> None:
    """Attach billing_line_items + intro for non–Data Transfer rows."""
    for r in rows:
        if r.get("Service") == "Data Transfer":
            continue

        svc = str(r.get("Service", "") or "")
        logical = service_to_ce_logical_key(svc)
        region = str(r.get("region") or "").strip()
        if not logical:
            continue

        if data_source == "synthetic":
            demo_region = region if region and region not in ("—", "None") else "us-east-1"
            r["billing_line_items"] = _synthetic_ce_lines(logical, demo_region)
            r["billing_lines_source"] = "synthetic"
            r["billing_hide_amounts"] = True
            r["billing_intro"] = (
                "**Sample mode:** After you connect AWS, **billing line labels** from your account can appear here. "
                "We never show fake dollar amounts in the sample."
            )
            r["billing_period_label"] = ""
            continue

        if region in ("", "—", "None"):
            continue

        lines = list(cache.get((logical, region)) or [])
        if not lines:
            continue

        r["billing_line_items"] = lines
        r["billing_lines_source"] = "ce"
        r["billing_intro"] = f"**Month to date** billing lines for **{svc}** in **{region}** (from Cost Explorer)."
        r["billing_period_label"] = "Month to date · Cost Explorer"
