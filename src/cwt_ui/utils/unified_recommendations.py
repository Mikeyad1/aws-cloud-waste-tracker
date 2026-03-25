"""
Unified "Recommendations to lower it" list across EC2, Lambda, Fargate, Storage, Data Transfer, Databases.
Used by the waste home (Overview) and the full Waste page.
MVP command 23: all service DataFrames use recommendation + potential_savings_usd; we normalize on input.
"""

from __future__ import annotations

import pandas as pd

from cwt_ui.services.spend_aggregate import normalize_optimization_df
from cwt_ui.utils.money import format_usd


def _rec_col(df: pd.DataFrame):
    return next((c for c in ["recommendation", "Recommendation"] if c in df.columns), None)


def _savings_col(df: pd.DataFrame):
    return next((c for c in ["potential_savings_usd", "Potential Savings ($)", "potential_savings"] if c in df.columns), None)


def _fix_steps_ec2(row: pd.Series, rec_col: str, df: pd.DataFrame) -> str:
    """Fix steps for EC2 recommendation (action title) — elaborated."""
    rec_text = str(row.get(rec_col, "") or "").lower()
    if "stop" in rec_text:
        return "Stop this EC2 instance to eliminate the monthly cost while it’s idle or unused."
    if "rightsize" in rec_text or "right-size" in rec_text:
        instance_type_col = next((c for c in ["instance_type", "InstanceType", "Instance Type"] if c in df.columns), None)
        if instance_type_col:
            current_type = row.get(instance_type_col, "")
            return f"Right-size to a smaller instance type (currently {current_type}) to match actual CPU and memory usage and reduce cost."
        return "Right-size this instance to match usage; choose a smaller type if utilization is consistently low."
    if "schedule" in rec_text:
        return "Schedule the instance to run only during business hours so you don’t pay for nights and weekends when it’s idle."
    raw = str(row.get(rec_col, "") or "").strip()
    return raw if raw else "—"


def _fix_steps_lambda(rec_text: str, row: pd.Series) -> str:
    """Action steps for Lambda recommendation — elaborated."""
    r = rec_text.lower()
    if "right-size" in r or "rightsize" in r or "memory" in r:
        mem_col = next((c for c in ["memory_size_mb", "MemorySize"] if c in row.index), None)
        if mem_col and pd.notna(row.get(mem_col)):
            return f"Right-size function memory from {row.get(mem_col)} MB to match actual usage; lower memory reduces cost per invocation."
        return "Right-size function memory to match actual usage so you don’t overpay for unused capacity."
    if "stop" in r or "remove" in r or "delete" in r:
        return "Remove or consolidate this unused function; if it’s no longer needed, deleting it stops the cost."
    return _humanize_fix(rec_text)


def _fix_steps_fargate(rec_text: str, row: pd.Series) -> str:
    """Action steps for Fargate recommendation — elaborated."""
    r = rec_text.lower()
    if "right-size" in r or "rightsize" in r or "cpu" in r or "memory" in r:
        cpu, mem = row.get("cpu"), row.get("memory_mb")
        parts = []
        if pd.notna(cpu) and cpu:
            parts.append(f"{cpu} CPU")
        if pd.notna(mem) and mem:
            parts.append(f"{mem} MB memory")
        current = " · ".join(parts) if parts else "current size"
        return f"Right-size task CPU and memory (currently {current}) to match utilization and reduce the per-task cost."
    if "stop" in r:
        return "Stop or scale down the unused task service so you’re not paying for idle containers."
    return _humanize_fix(rec_text)


def _fix_steps_storage(rec_text: str) -> str:
    """Action steps for S3/storage recommendation — elaborated."""
    r = rec_text.lower()
    if "lifecycle" in r and "glacier" in r:
        return "Add a lifecycle policy to move old or rarely accessed objects to Glacier (or Glacier Deep Archive) to cut storage cost."
    if "lifecycle" in r and "delete" in r:
        return "Enable a lifecycle rule to delete or expire objects after a set period (e.g. 7 days) so you don’t pay for temporary data."
    if "s3 ia" in r or "glacier" in r or "move to" in r:
        return "Move objects to S3 Infrequent Access or Glacier where the access pattern allows; this reduces storage cost significantly."
    if "intelligent" in r or "tiering" in r:
        return "Switch the bucket or prefix to S3 Intelligent-Tiering so objects automatically move to cheaper tiers when access drops."
    if "cloudfront" in r:
        return "Use CloudFront (or another CDN) for infrequent access to reduce both storage and data transfer cost."
    if "snapshot" in r and ("delete" in r or "unused" in r):
        return "Delete the unused snapshot after confirming it’s not needed for restore; snapshots incur storage cost until removed."
    if "ok" in r or "already" in r:
        return "No action — already optimized"
    return _humanize_fix(rec_text)


def _fix_steps_data_transfer(rec_text: str) -> str:
    """Action steps for Data Transfer recommendation — elaborated."""
    r = rec_text.lower()
    if "cloudfront" in r or "cdn" in r:
        return "Serve static assets (images, CSS, JS, etc.) through CloudFront or another CDN so egress is cheaper and cached at the edge."
    if "consolidate" in r or "vpc" in r or "peering" in r:
        return "Consolidate workloads in fewer regions or use VPC peering / PrivateLink to reduce inter-region data transfer cost."
    if "compression" in r:
        return "Enable compression (e.g. gzip) on responses to reduce bytes transferred and lower data transfer cost."
    if "review" in r and "cdn" in r:
        return "Review CDN and cache settings so more static content is served from the edge and less from origin, lowering egress."
    return _humanize_fix(rec_text)


def _action_title_data_transfer(rec_text: str, fix: str) -> str:
    """Action title: specific finding, not generic advice."""
    r = (rec_text or "").lower()
    if "cloudfront" in r or "cdn" in r:
        return "Reduce internet egress with CloudFront"
    if "consolidate" in r or "vpc" in r or "peering" in r:
        return "Reduce inter-region data transfer"
    if "compression" in r:
        return "Reduce transfer volume with compression"
    return fix or "Optimize data transfer"


def _fix_steps_databases(rec_text: str, row: pd.Series) -> str:
    """Action steps for RDS/DynamoDB recommendation — elaborated."""
    r = rec_text.lower()
    if "reserved" in r or "savings plan" in r or "ri " in r:
        return "Review Reserved Instance or Savings Plan eligibility; a 1- or 3-year commitment can cut cost for steady workloads."
    if "aurora serverless" in r:
        return "Consider Aurora Serverless (or scale down size) when load is variable so you’re not paying for peak capacity all the time."
    if "right-size" in r or "rightsize" in r or "low cpu" in r or "utilization" in r:
        inst = row.get("instance_type", "") or ""
        if inst:
            return f"Right-size the instance (currently {inst}) to a smaller class that matches low CPU utilization and reduces cost."
        return "Right-size the instance to match actual usage; a smaller instance class will reduce the monthly bill."
    if "provisioned" in r and "dynamo" in r:
        return "Consider switching to provisioned capacity for steady DynamoDB read/write; it can be cheaper than on-demand at consistent rates."
    if "ok" in r or "variable" in r:
        return "No action — usage pattern is variable or already optimized"
    return _humanize_fix(rec_text)


def _humanize_fix(rec_text: str) -> str:
    """Turn raw recommendation into a single action-oriented sentence."""
    t = str(rec_text or "").strip()
    if not t or t == "—":
        return "—"
    # Already sentence-like (starts with verb or noun)
    if t[0].isupper() and len(t) > 10:
        return t
    # Short or technical: capitalize and return
    return t[0].upper() + t[1:] if t else "—"


def action_type_from_fix_steps(fix_steps: str) -> str:
    """
    Classify recommendation for All Waste navigation: Stop or remove, Right-size, or Move or change tier.
    Used for filtering and "By action" tabs.
    """
    f = (fix_steps or "").lower()
    if "stop" in f or "remove" in f or "delete" in f or "scale down" in f:
        return "Stop or remove"
    if "right-size" in f or "rightsize" in f or "downsize" in f:
        return "Right-size"
    return "Move or change tier"


def _severity(fix_steps: str, rec_text: str, waste_usd: float) -> str:
    """
    Derive Critical / Moderate / Low from recommendation type and savings amount.
    Stop = Critical, Right-size/downsize = Moderate, else Low; high savings can bump to Critical/Moderate.
    """
    rec_lower = (fix_steps + " " + rec_text).lower()
    if "stop" in rec_lower:
        return "Critical"
    if "rightsize" in rec_lower or "right-size" in rec_lower or "downsize" in rec_lower:
        return "Moderate"
    # By savings amount when recommendation is generic
    if waste_usd >= 500:
        return "Critical"
    if waste_usd >= 100:
        return "Moderate"
    return "Low"


def _reason_ec2(row: pd.Series, rec_text: str, df: pd.DataFrame) -> str:
    """Human-readable reason for EC2 recommendation (e.g. CPU < 1% for 7 days)."""
    cpu_col = next((c for c in ["avg_cpu_7d", "CPU Utilization (%)"] if c in df.columns), None)
    cpu = float(pd.to_numeric(row.get(cpu_col), errors="coerce")) if cpu_col and pd.notna(row.get(cpu_col)) else None
    rec_lower = (rec_text or "").lower()
    if "extremely low" in rec_lower or ("stop instance" in rec_lower and cpu is not None and cpu < 1):
        return "CPU utilization < 1% for 7 days"
    if "very low" in rec_lower and cpu is not None and cpu < 3:
        return "CPU utilization < 3% for 7 days"
    if "downsiz" in rec_lower or "low cpu" in rec_lower:
        if cpu is not None:
            return f"CPU utilization {cpu:.1f}% for 7 days (below 5% threshold)"
        return "Low CPU utilization for 7 days"
    if "schedule" in rec_lower:
        return "Instance runs 24/7; usage pattern suggests scheduling could reduce cost"
    if "rightsize" in rec_lower or "right-size" in rec_lower:
        return "Instance size exceeds current usage; a smaller instance type may match demand and reduce cost."
    return rec_text.strip() if rec_text else "Instance usage pattern suggests an optimization opportunity."


def _reason_lambda(rec_text: str, row: pd.Series) -> str:
    """Reason for Lambda recommendation."""
    rec_lower = (rec_text or "").lower()
    if "right-size" in rec_lower or "rightsize" in rec_lower or "memory" in rec_lower:
        mem_col = next((c for c in ["memory_size_mb", "MemorySize"] if c in row.index), None)
        if mem_col and pd.notna(row.get(mem_col)):
            return f"Memory allocation {row.get(mem_col)} MB exceeds typical usage; right-sizing can reduce cost."
        return "Memory allocation is higher than observed usage; reducing it can lower the bill."
    if "stop" in rec_lower or "remove" in rec_lower:
        return "No or minimal invocations detected; the function appears unused and can be removed or consolidated."
    return rec_text.strip() if rec_text else "Function configuration or usage suggests an optimization opportunity."


def _reason_fargate(rec_text: str, row: pd.Series) -> str:
    """Reason for Fargate recommendation."""
    rec_lower = (rec_text or "").lower()
    if "right-size" in rec_lower or "rightsize" in rec_lower or "cpu" in rec_lower or "memory" in rec_lower:
        return "Task CPU or memory allocation is higher than utilization; right-sizing can reduce cost."
    if "stop" in rec_lower:
        return "Task or service appears underused or idle; stopping or scaling down can reduce cost."
    return rec_text.strip() if rec_text else "Task utilization suggests a right-sizing opportunity."


def _reason_storage(rec_text: str) -> str:
    """Observation that triggered the recommendation (what we detected), not the action."""
    r = (rec_text or "").lower()
    if "lifecycle" in r and "glacier" in r:
        return "Old or rarely accessed objects are in standard storage class; moving them to a cheaper tier can reduce cost."
    if "lifecycle" in r and "delete" in r:
        return "Objects with no expiration or lifecycle rule detected; removing or archiving them can reduce storage cost."
    if "s3 ia" in r or "glacier" in r or "move to" in r:
        return "Storage class cost is higher than the access pattern requires; a lower-cost class may fit better."
    if "intelligent" in r or "tiering" in r:
        return "Variable access pattern detected; current class may be suboptimal and Intelligent-Tiering could save cost."
    if "cloudfront" in r:
        return "Infrequent access pattern detected; combining with a CDN or different class can reduce cost."
    return (rec_text or "").strip() or "Storage usage pattern suggests optimization opportunity."


def _reason_data_transfer(rec_text: str, fix: str) -> str:
    """Observation that triggered the recommendation (what we detected), not the action."""
    r = (rec_text or "").lower()
    if "cloudfront" in r or "cdn" in r:
        return "High internet egress detected; serving static or public content without a CDN is driving transfer cost."
    if "consolidate" in r or "vpc" in r or "peering" in r:
        return "Inter-region or cross-region transfer volume detected; consolidating or using VPC peering can reduce cost."
    if "compression" in r:
        return "Data transfer volume is significant; enabling compression could reduce bytes transferred and cost."
    if "review" in r and "cdn" in r:
        return "Egress and cache pattern detected; a CDN or better caching could lower transfer cost."
    return (rec_text or "").strip() or "Transfer pattern suggests optimization opportunity."


def _reason_databases(rec_text: str, row: pd.Series) -> str:
    """Observation that triggered the recommendation (what we detected)."""
    r = (rec_text or "").lower()
    if "low cpu" in r or "utilization" in r or "right-size" in r or "rightsize" in r:
        return "Low CPU utilization detected over the lookback period; right-sizing the instance may reduce cost."
    if "reserved" in r or "savings plan" in r:
        return "Steady usage pattern detected; a Reserved Instance or Savings Plan could reduce cost."
    if "provisioned" in r and "dynamo" in r:
        return "Steady read/write pattern detected; provisioned capacity may be cheaper than on-demand at this usage."
    return (rec_text or "").strip() or "Usage or commitment pattern suggests optimization opportunity."


def _where_this_comes_from(
    *,
    resource: str,
    monthly_cost_line: str,
    why: str,
    savings_monthly: float,
    sources: str | None = None,
) -> str:
    """Plain-language breakdown for the “Where this number comes from” expander (no internal jargon)."""
    out = (
        f"**Resource** — {resource}\n\n"
        f"**Monthly cost (estimate)** — {monthly_cost_line}\n\n"
    )
    if sources:
        out += f"{sources}\n\n"
    out += (
        f"**Reason for this recommendation** — {why}\n\n"
        f"**Potential savings** — {format_usd(savings_monthly)} per month if you apply the fix above"
    )
    return out


def _monthly_cost_line_ec2(row: pd.Series) -> str:
    for c in ["monthly_cost_usd", "Monthly Cost ($)", "monthly_cost"]:
        if c in row.index and pd.notna(row.get(c)):
            mc = float(pd.to_numeric(row.get(c), errors="coerce") or 0)
            if mc > 0:
                return (
                    f"{format_usd(mc)} per month. "
                    "Based on the current AWS on-demand price for this instance type."
                )
            return f"{format_usd(mc)} per month (instance not accruing full run cost in this view)."
    return "Estimated from instance type and public pricing; your bill may differ slightly."


def _calculation_note_ec2(row: pd.Series, ec2_df: pd.DataFrame, w: float, resource: str, why: str) -> str:
    mc_line = _monthly_cost_line_ec2(row)
    cpu = None
    for c in ["avg_cpu_7d", "CPU Utilization (%)"]:
        if c in row.index and pd.notna(row.get(c)):
            v = float(pd.to_numeric(row.get(c), errors="coerce"))
            if v >= -0.5:
                cpu = v
            break
    if cpu is not None and cpu >= 0 and "cpu" not in (why or "").lower():
        why_full = f"{why} Average CPU over the last week was about **{cpu:.1f}%**."
    else:
        why_full = why
    src_parts: list[str] = [
        "**Source** — AWS public pricing (current on-demand rate for this instance type, used for the monthly cost estimate)",
    ]
    if cpu is not None and cpu >= 0:
        src_parts.insert(
            0,
            "**Source** — AWS CloudWatch metrics (CPU usage over the last 7 days)",
        )
    return _where_this_comes_from(
        resource=resource,
        monthly_cost_line=mc_line,
        why=why_full,
        savings_monthly=w,
        sources="\n\n".join(src_parts),
    )


def _calculation_note_lambda(row: pd.Series, w: float, resource: str, why: str) -> str:
    mc_line = "Not itemized for this function."
    has_cost = False
    for c in ["monthly_cost_usd", "Monthly Cost ($)", "monthly_cost"]:
        if c in row.index and pd.notna(row.get(c)):
            mc = float(pd.to_numeric(row.get(c), errors="coerce") or 0)
            if mc > 0:
                mc_line = f"About {format_usd(mc)} per month at current memory and usage assumptions."
                has_cost = True
            break
    src = "**Source** — AWS Lambda (function configuration in your account)"
    if has_cost:
        src += "\n\n**Source** — AWS public pricing (Lambda rates, used for the dollar estimate)"
    return _where_this_comes_from(
        resource=resource,
        monthly_cost_line=mc_line,
        why=why,
        savings_monthly=w,
        sources=src,
    )


def _calculation_note_fargate(row: pd.Series, w: float, resource: str, why: str) -> str:
    mc_line = "Not itemized for this task."
    has_cost = False
    for c in ["monthly_cost_usd", "Monthly Cost ($)", "monthly_cost"]:
        if c in row.index and pd.notna(row.get(c)):
            mc = float(pd.to_numeric(row.get(c), errors="coerce") or 0)
            if mc > 0:
                mc_line = f"About {format_usd(mc)} per month at the CPU and memory shown for this task."
                has_cost = True
            break
    cpu, mem = row.get("cpu"), row.get("memory_mb")
    extra = []
    if pd.notna(cpu) and str(cpu).strip():
        extra.append(f"CPU units {cpu}")
    if pd.notna(mem) and mem:
        extra.append(f"memory {mem} MB")
    if extra:
        mc_line = f"{mc_line.rstrip('.')} — {'; '.join(extra)}."
    src = "**Source** — Amazon ECS (task and cluster details from your account)"
    if has_cost:
        src += "\n\n**Source** — AWS public pricing (Fargate vCPU and memory rates, used for the dollar estimate)"
    return _where_this_comes_from(
        resource=resource,
        monthly_cost_line=mc_line,
        why=why,
        savings_monthly=w,
        sources=src,
    )


def _calculation_note_storage(w: float, resource: str, why: str) -> str:
    mc_line = (
        "Bucket-level review only; exact monthly storage dollars are not always shown here. "
        "Check AWS Billing for the precise charge for this bucket."
    )
    return _where_this_comes_from(
        resource=resource,
        monthly_cost_line=mc_line,
        why=why,
        savings_monthly=w,
        sources=(
            "**Source** — Amazon S3 (bucket settings in your account)\n\n"
            "**Source** — AWS Cost Explorer / billing data (to confirm monthly storage cost on your bill)"
        ),
    )


def _calculation_note_data_transfer(w: float, row: pd.Series, why: str) -> str:
    region = row.get("region", "—")
    ut = row.get("transfer_type", "—")
    mc = None
    for c in ["monthly_cost_usd", "Monthly Cost ($)", "monthly_cost"]:
        if c in row.index and pd.notna(row.get(c)):
            mc = float(pd.to_numeric(row.get(c), errors="coerce") or 0)
            break
    if mc is not None and mc > 0:
        mc_line = (
            f"About {format_usd(mc)} in **data transfer** charges this month (so far) for **{region}**, "
            f"type “{ut}”—taken from your billing view for this line item."
        )
    else:
        mc_line = (
            f"This row reflects transfer activity in **{region}** (“{ut}”). "
            "The dollar amount ties to what billing shows for that pattern."
        )
    return _where_this_comes_from(
        resource=f"{region} · {ut}",
        monthly_cost_line=mc_line,
        why=why,
        savings_monthly=w,
        sources="**Source** — AWS Cost Explorer / billing data (data transfer charges for this region and usage type)",
    )


def _calculation_note_databases(service_label: str, row: pd.Series, w: float, resource: str, why: str) -> str:
    inst = str(row.get("instance_type", "") or "").strip()
    r = (service_label or "").upper()
    mc_line = "Estimated from typical pricing for this size or mode; your invoice is the source of truth."
    for c in ["monthly_cost_usd", "Monthly Cost ($)", "monthly_cost"]:
        if c in row.index and pd.notna(row.get(c)):
            mc = float(pd.to_numeric(row.get(c), errors="coerce") or 0)
            if mc > 0:
                mc_line = f"About {format_usd(mc)} per month for this database at current settings."
            elif "DYNAMO" in r and inst:
                mc_line = f"Billing mode: **{inst}**. Exact monthly dollars may show in Billing once linked."
            break
    if inst and "DYNAMO" not in r:
        mc_line = f"{mc_line} Instance class: **{inst}**."
    if "DYNAMO" in r:
        src = (
            "**Source** — Amazon DynamoDB (table settings in your account)\n\n"
            "**Source** — AWS Cost Explorer / billing data (to confirm monthly table cost on your bill)"
        )
    else:
        src = (
            "**Source** — Amazon RDS (instance details in your account)\n\n"
            "**Source** — AWS CloudWatch metrics (CPU utilization for this database, when available)\n\n"
            "**Source** — AWS public pricing and reference rates (used when we show a monthly cost estimate)"
        )
    return _where_this_comes_from(
        resource=resource,
        monthly_cost_line=mc_line,
        why=why,
        savings_monthly=w,
        sources=src,
    )


_BILLING_INTRO_DT = "**Month to date** data transfer charges from Cost Explorer."

# Short billing verification — same for every service (no implementation details).
BILLING_VERIFY_CE = "**Verify in AWS:** Open **Billing → Cost Explorer** and filter by **service** and **region**."


def _dt_billing_line_from_row(row: pd.Series) -> dict[str, float | str]:
    """One human-readable billing line + amount from a data-transfer scan row."""
    cost = float(pd.to_numeric(row.get("monthly_cost_usd", 0), errors="coerce") or 0)
    region = str(row.get("region", "—")).strip() or "—"
    ut = str(row.get("usage_type", "") or "").strip()
    if not ut:
        ut = str(row.get("transfer_type", "—"))
    dest = str(row.get("destination", "") or "").strip()
    parts = [
        f"Service **AWS Data Transfer**",
        f"Region **{region}**",
        f"Usage type **{ut}**",
    ]
    if dest and dest not in ("—", ""):
        parts.append(f"Category **{dest}**")
    data_gb = row.get("data_gb")
    try:
        if pd.notna(data_gb) and float(data_gb or 0) > 0:
            parts.append(f"Approx. volume **{float(data_gb):,.1f} GB** (rough estimate from cost)")
    except (TypeError, ValueError):
        pass
    line = " · ".join(parts)
    return {"line": line, "amount_usd": round(cost, 2)}


def _s3_billing_verification_note(_bucket: str) -> str:
    return BILLING_VERIFY_CE


def _dynamodb_billing_verification_note(_table: str) -> str:
    return BILLING_VERIFY_CE


def _rds_billing_verification_note(_db_id: str, _region: str) -> str:
    return BILLING_VERIFY_CE


def _ec2_billing_verification_note(_instance_id: str, _region: str) -> str:
    return BILLING_VERIFY_CE


def _lambda_billing_verification_note(_function_name: str, _region: str) -> str:
    return BILLING_VERIFY_CE


def _fargate_billing_verification_note(_resource_label: str, _region: str) -> str:
    return BILLING_VERIFY_CE


def build_unified_what_to_turn_off(
    ec2_df: pd.DataFrame | None,
    lambda_df: pd.DataFrame | None,
    fargate_df: pd.DataFrame | None,
    storage_df: pd.DataFrame | None,
    data_transfer_df: pd.DataFrame | None,
    databases_df: pd.DataFrame | None,
) -> list[dict]:
    """
    Build a single list of rows: Resource, Waste ($/mo), Fix steps, Service, Severity.
    Only rows with positive savings. Sorted by Waste descending.
    Expects or normalizes to recommendation + potential_savings_usd per service DataFrame.
    """
    rows: list[dict] = []

    if ec2_df is not None and not ec2_df.empty:
        ec2_df = normalize_optimization_df(ec2_df)
        sav = _savings_col(ec2_df)
        rec = _rec_col(ec2_df)
        id_col = next((c for c in ["instance_id", "InstanceId", "Instance ID"] if c in ec2_df.columns), None)
        if sav and id_col and rec:
            for _, row in ec2_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                fix = _fix_steps_ec2(row, rec, ec2_df)
                rec_t = str(row.get(rec, "") or "")
                rec_lower = rec_t.lower()
                idle_for = "7 days" if ("stop" in rec_lower or "downsize" in rec_lower or "very low" in rec_lower or "extremely low" in rec_lower) else None
                res_id = str(row.get(id_col, "—"))
                why_ec2 = _reason_ec2(row, rec_t, ec2_df)
                ec2_region = str(row.get("region", "—") or "—")
                rows.append({
                    "Resource": res_id,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": fix,
                    "Service": "EC2",
                    "region": ec2_region,
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": why_ec2,
                    "Idle for": idle_for,
                    "Calculation": _calculation_note_ec2(row, ec2_df, w, res_id, why_ec2),
                    "billing_verification_note": _ec2_billing_verification_note(res_id, ec2_region),
                })

    if lambda_df is not None and not lambda_df.empty:
        lambda_df = normalize_optimization_df(lambda_df)
        sav = _savings_col(lambda_df)
        rec = _rec_col(lambda_df)
        id_col = next((c for c in ["function_name", "FunctionName"] if c in lambda_df.columns), None)
        if sav and id_col:
            for _, row in lambda_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                rec_t = str(row.get(rec, "") or "") if rec else ""
                fix = _fix_steps_lambda(rec_t, row)
                fn = str(row.get(id_col, "—"))
                why_lm = _reason_lambda(rec_t, row)
                lm_region = str(row.get("region", "—") or "—")
                rows.append({
                    "Resource": fn,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": fix,
                    "Service": "Lambda",
                    "region": lm_region,
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": why_lm,
                    "Idle for": None,
                    "Calculation": _calculation_note_lambda(row, w, fn, why_lm),
                    "billing_verification_note": _lambda_billing_verification_note(fn, lm_region),
                })

    if fargate_df is not None and not fargate_df.empty:
        fargate_df = normalize_optimization_df(fargate_df)
        sav = _savings_col(fargate_df)
        rec = _rec_col(fargate_df)
        svc_col = next((c for c in ["service_name"] if c in fargate_df.columns), None)
        cluster_col = next((c for c in ["cluster_name"] if c in fargate_df.columns), None)
        if sav and (svc_col or cluster_col):
            for _, row in fargate_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                rec_t = str(row.get(rec, "") or "") if rec else ""
                fix = _fix_steps_fargate(rec_t, row)
                resource = str(row.get(svc_col, "") or row.get(cluster_col, "—") or "—")
                if cluster_col and resource and str(row.get(cluster_col, "")):
                    resource = f"{resource} ({row.get(cluster_col, '')})"
                why_fg = _reason_fargate(rec_t, row)
                fg_region = str(row.get("region", "—") or "—")
                rows.append({
                    "Resource": resource,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": fix,
                    "Service": "Fargate",
                    "region": fg_region,
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": why_fg,
                    "Idle for": None,
                    "Calculation": _calculation_note_fargate(row, w, resource, why_fg),
                    "billing_verification_note": _fargate_billing_verification_note(resource, fg_region),
                })

    if storage_df is not None and not storage_df.empty:
        storage_df = normalize_optimization_df(storage_df)
        sav = _savings_col(storage_df)
        rec = _rec_col(storage_df)
        id_col = next((c for c in ["bucket_name", "BucketName"] if c in storage_df.columns), None)
        if sav and id_col:
            for _, row in storage_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                rec_t = str(row.get(rec, "") or "") if rec else ""
                fix = _fix_steps_storage(rec_t)
                bkt = str(row.get(id_col, "—"))
                why_s3 = _reason_storage(rec_t)
                s3_region = str(row.get("region", "—") or "—")
                rows.append({
                    "Resource": bkt,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": fix,
                    "Service": "S3",
                    "region": s3_region,
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": why_s3,
                    "Idle for": None,
                    "Calculation": _calculation_note_storage(w, bkt, why_s3),
                    "billing_verification_note": _s3_billing_verification_note(bkt),
                })

    if data_transfer_df is not None and not data_transfer_df.empty:
        data_transfer_df = normalize_optimization_df(data_transfer_df)
        sav = _savings_col(data_transfer_df)
        rec = _rec_col(data_transfer_df)
        if sav:
            for _, row in data_transfer_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                region = row.get("region", "—")
                ttype = row.get("transfer_type", "—")
                dest = row.get("destination", "—")
                resource = f"{region} · {ttype} → {dest}"
                rec_t = str(row.get(rec, "") or "") if rec else ""
                fix = _fix_steps_data_transfer(rec_t)
                action_title = _action_title_data_transfer(rec_t, fix)
                reason = _reason_data_transfer(rec_t, fix)
                rows.append({
                    "Resource": resource,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": action_title,
                    "Service": "Data Transfer",
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": reason,
                    "Idle for": None,
                    "Calculation": _calculation_note_data_transfer(w, row, reason),
                    "billing_line_items": [_dt_billing_line_from_row(row)],
                    "billing_period_label": "Month to date · Cost Explorer",
                    "billing_intro": _BILLING_INTRO_DT,
                })

    if databases_df is not None and not databases_df.empty:
        databases_df = normalize_optimization_df(databases_df)
        sav = _savings_col(databases_df)
        rec = _rec_col(databases_df)
        id_col = next((c for c in ["resource_id", "ResourceId"] if c in databases_df.columns), None)
        svc_col = next((c for c in ["service", "Service"] if c in databases_df.columns), None)
        if sav and id_col:
            for _, row in databases_df.iterrows():
                w = float(pd.to_numeric(row.get(sav, 0), errors="coerce") or 0)
                if w <= 0:
                    continue
                rec_t = str(row.get(rec, "") or "") if rec else ""
                fix = _fix_steps_databases(rec_t, row)
                service_label = str(row.get(svc_col, "Databases")) if svc_col else "Databases"
                rid = str(row.get(id_col, "—"))
                why_db = _reason_databases(rec_t, row)
                db_region = str(row.get("region", "—") or "—")
                sl_up = service_label.upper()
                if "DYNAMO" in sl_up:
                    bill_note = _dynamodb_billing_verification_note(rid)
                else:
                    bill_note = _rds_billing_verification_note(rid, db_region)
                rows.append({
                    "Resource": rid,
                    "Waste ($/mo)": w,
                    "Severity": _severity(fix, rec_t, w),
                    "Fix steps": fix,
                    "Action title": fix,
                    "Service": service_label,
                    "region": db_region,
                    "Action": action_type_from_fix_steps(fix),
                    "Reason": why_db,
                    "Idle for": None,
                    "Calculation": _calculation_note_databases(service_label, row, w, rid, why_db),
                    "billing_verification_note": bill_note,
                })

    # Aggregate duplicate-looking recommendations (e.g. multiple internet egress lines → one)
    rows = _aggregate_data_transfer_rows(rows)

    rows.sort(key=lambda r: r["Waste ($/mo)"], reverse=True)
    return rows


def _aggregate_data_transfer_rows(rows: list[dict]) -> list[dict]:
    """
    Group Data Transfer rows that share the same Action title (e.g. same egress fix)
    into a single recommendation with summed waste, to avoid duplicate-looking cards.
    """
    dt_rows = [r for r in rows if r.get("Service") == "Data Transfer"]
    other_rows = [r for r in rows if r.get("Service") != "Data Transfer"]
    if not dt_rows:
        return rows
    # Group by Action title
    by_title: dict[str, list[dict]] = {}
    for r in dt_rows:
        key = r.get("Action title") or r.get("Fix steps") or "Data Transfer"
        by_title.setdefault(key, []).append(r)
    aggregated: list[dict] = []
    for action_title, group in by_title.items():
        if len(group) == 1:
            aggregated.append(group[0])
            continue
        total_waste = sum(float(x.get("Waste ($/mo)", 0) or 0) for x in group)
        # Use first row as template; sum waste; combine resource description
        first = group[0].copy()
        first["Waste ($/mo)"] = total_waste
        first["Resource"] = "Multiple sources"
        first["Reason"] = first.get("Reason") or "High internet egress detected"
        merged_billing: list[dict[str, float | str]] = []
        for x in group:
            merged_billing.extend(x.get("billing_line_items") or [])
        first["billing_line_items"] = merged_billing
        first["billing_period_label"] = group[0].get("billing_period_label", "Month to date · Cost Explorer")
        total_billed = sum(float(m.get("amount_usd", 0) or 0) for m in merged_billing)
        first["billing_intro"] = (
            f"**{len(group)}** similar items combined · **{len(merged_billing)}** billing lines (month to date)."
        )
        first["Calculation"] = _where_this_comes_from(
            resource="Multiple data transfer line items (same kind of fix)",
            monthly_cost_line=(
                f"About **{format_usd(total_billed)}** in combined data-transfer charges month to date across these lines "
                f"(**{len(merged_billing)}** Cost Explorer lines). "
                f"Estimated savings shown for this card: **{format_usd(total_waste)}** per month."
            ),
            why=first.get("Reason") or "Several regions or usage types point to the same kind of savings opportunity.",
            savings_monthly=total_waste,
            sources="**Source** — AWS Cost Explorer / billing data (data transfer charges; we summed matching lines for readability)",
        )
        # Severity from highest in group (Critical > Moderate > Low)
        severity_order = {"Critical": 3, "Moderate": 2, "Low": 1}
        first["Severity"] = max(
            (x.get("Severity") for x in group if x.get("Severity")),
            key=lambda s: severity_order.get(s, 0),
            default=first.get("Severity", "Moderate"),
        )
        aggregated.append(first)
    return other_rows + aggregated
