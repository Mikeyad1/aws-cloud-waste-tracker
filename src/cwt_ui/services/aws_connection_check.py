# Post–Apply role checks: identity, Cost Explorer, EC2 (read-only smoke test).
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from cwt_ui.services.scans import _assume_role, _temporary_env


def verify_assumed_role_access(
    *,
    role_arn: str,
    external_id: str,
    session_name: str,
    ec2_region: str,
) -> dict[str, Any]:
    """
    After AssumeRole succeeds, validate typical CloudWasteTracker needs.

    Returns keys:
      assume_ok: bool
      assume_error: optional str
      identity: { ok, arn, account, error }
      cost_explorer: { ok, error, error_code }
      ec2: { ok, error, error_code }
    """
    out: dict[str, Any] = {
        "assume_ok": False,
        "assume_error": None,
        "identity": {"ok": False, "arn": None, "account": None, "error": None},
        "cost_explorer": {"ok": False, "error": None, "error_code": None},
        "ec2": {"ok": False, "error": None, "error_code": None},
    }

    creds = {
        "AWS_ROLE_ARN": role_arn.strip(),
        "AWS_EXTERNAL_ID": external_id.strip(),
        "AWS_ROLE_SESSION_NAME": session_name.strip() or "CloudWasteTracker",
        "AWS_DEFAULT_REGION": ec2_region.strip() or "us-east-1",
    }

    assumed = _assume_role(creds)
    if not assumed:
        out["assume_error"] = "Could not assume this IAM role. Check the role ARN, external ID, and base credentials."
        return out

    out["assume_ok"] = True

    with _temporary_env(assumed):
        # 1) STS caller identity (assumed role)
        try:
            sts = boto3.client("sts", region_name=ec2_region)
            ident = sts.get_caller_identity()
            out["identity"]["ok"] = True
            out["identity"]["arn"] = ident.get("Arn")
            out["identity"]["account"] = ident.get("Account")
        except ClientError as e:
            out["identity"]["error"] = e.response.get("Error", {}).get("Message", str(e))
        except Exception as e:
            out["identity"]["error"] = str(e)

        # 2) Cost Explorer (global endpoint — us-east-1)
        try:
            ce = boto3.client("ce", region_name="us-east-1")
            today = datetime.now(timezone.utc).date()
            month_start = today.replace(day=1)
            end_exclusive = today + timedelta(days=1)
            ce.get_cost_and_usage(
                TimePeriod={
                    "Start": month_start.strftime("%Y-%m-%d"),
                    "End": end_exclusive.strftime("%Y-%m-%d"),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )
            out["cost_explorer"]["ok"] = True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "ClientError")
            out["cost_explorer"]["error"] = e.response.get("Error", {}).get("Message", str(e))
            out["cost_explorer"]["error_code"] = code
        except Exception as e:
            out["cost_explorer"]["error"] = str(e)
            out["cost_explorer"]["error_code"] = type(e).__name__

        # 3) EC2 describe (regional resource read)
        try:
            ec2 = boto3.client("ec2", region_name=ec2_region)
            ec2.describe_instances(MaxResults=5)
            out["ec2"]["ok"] = True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "ClientError")
            out["ec2"]["error"] = e.response.get("Error", {}).get("Message", str(e))
            out["ec2"]["error_code"] = code
        except Exception as e:
            out["ec2"]["error"] = str(e)
            out["ec2"]["error_code"] = type(e).__name__

    return out
