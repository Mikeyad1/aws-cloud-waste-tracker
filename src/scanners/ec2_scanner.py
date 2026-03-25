# src/scanners/ec2_scanner.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple

import boto3
from botocore.exceptions import ClientError

# ----------------------
# Settings / constants
# ----------------------
DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Below this average CPU (over lookback window) an instance is considered "idle"
IDLE_CPU_THRESHOLD = 5.0
# Lookback window for CPU metric
IDLE_LOOKBACK_DAYS = 7

# Legacy pricing - now using PricingService for accurate calculations
INSTANCE_PRICES = {
    "t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416, "t3.large": 0.0832,
    "t2.micro": 0.0116, "t2.small": 0.023, "t2.medium": 0.0464,
}


# ----------------------
# Helpers
# ----------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _daterange(days: int) -> Tuple[datetime, datetime]:
    end = _utc_now()
    start = end - timedelta(days=days)
    return start, end


def _estimate_monthly_cost(instance_type: str):
    """Legacy function - use PricingService for accurate calculations."""
    hourly = INSTANCE_PRICES.get(instance_type)
    if hourly is None:
        # Return a reasonable default cost for unknown instance types
        # Most instance types cost between $10-100/month
        return 50.0  # Default monthly cost estimate
    return round(hourly * 24 * 30, 2)  # ~720h


def _aws_client(service: str, region: str):
    # Use environment variables only, no local credentials file
    return boto3.client(
        service, 
        region_name=region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN')
    )


# ----------------------
# Scanners (EC2 / EBS / EIP)
# ----------------------
def scan_ec2_idle(region: str) -> List[Dict]:
    """
    Return idle EC2 instance findings with enhanced cost analysis and recommendations.
    """
    # Import pricing service for accurate calculations
    try:
        from core.services.pricing_service import pricing_service
    except ImportError:
        # Fallback to legacy pricing if service not available
        pricing_service = None
    
    ec2 = _aws_client("ec2", region)
    cw = _aws_client("cloudwatch", region)

    reservations = ec2.describe_instances().get("Reservations", [])
    # Get ALL instances (not just running) - we need all states
    instances = [
        i
        for r in reservations
        for i in r.get("Instances", [])
    ]

    start, end = _daterange(IDLE_LOOKBACK_DAYS)
    out: List[Dict] = []

    for inst in instances:
        instance_id = inst.get("InstanceId")
        itype = inst.get("InstanceType", "?")
        name_tag = next((t["Value"] for t in inst.get("Tags", []) if t.get("Key") == "Name"), "")
        state = inst.get("State", {}).get("Name", "unknown")  # running, stopped, terminated, etc.

        # Average CPU over lookback window (only for running instances)
        avg_cpu = -1.0  # Default: unavailable
        if state == "running":
            try:
                resp = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start,
                    EndTime=end,
                    Period=3600 * 6,
                    Statistics=["Average"],
                )
                dps = resp.get("Datapoints", [])
                avg_cpu = 0.0 if not dps else sum(dp["Average"] for dp in dps) / len(dps)
            except ClientError:
                avg_cpu = -1.0  # couldn't read metrics

        # Calculate accurate monthly cost and savings
        if pricing_service:
            monthly_cost = pricing_service.get_instance_monthly_cost(itype, region)
            savings_analysis = pricing_service.calculate_instance_savings(itype, avg_cpu, "stop or downsize", region)
        else:
            # Fallback to legacy calculation
            monthly_cost = _estimate_monthly_cost(itype)
            savings_analysis = {
                "potential_savings": monthly_cost if isinstance(monthly_cost, (int, float)) else 50.0,
                "action": "Stop or downsize instance",
                "implementation_steps": ["Go to EC2 Console and stop/terminate instance"]
            }

        # Determine recommendation based on CPU usage
        if avg_cpu >= 0 and avg_cpu < IDLE_CPU_THRESHOLD:
            if avg_cpu < 1.0:
                recommendation = "Stop instance - extremely low CPU usage"
                priority = "HIGH"
                # Update savings analysis for idle instances
                savings_analysis["potential_savings"] = monthly_cost if isinstance(monthly_cost, (int, float)) else 50.0
                savings_analysis["action"] = "Stop instance - extremely low CPU usage"
            elif avg_cpu < 3.0:
                recommendation = "Stop or downsize - very low CPU usage"
                priority = "HIGH"
                # Update savings analysis for idle instances
                savings_analysis["potential_savings"] = monthly_cost if isinstance(monthly_cost, (int, float)) else 50.0
                savings_analysis["action"] = "Stop or downsize - very low CPU usage"
            else:
                recommendation = "Consider downsizing - low CPU usage"
                priority = "MEDIUM"
                # Update savings analysis for idle instances
                savings_analysis["potential_savings"] = monthly_cost if isinstance(monthly_cost, (int, float)) else 50.0
                savings_analysis["action"] = "Consider downsizing - low CPU usage"
        else:
            recommendation = "OK - CPU usage is normal"
            priority = "LOW"
            # No savings for normal usage instances
            savings_analysis["potential_savings"] = 0
            savings_analysis["action"] = "No action needed"

        finding = {
            "type": "idle_instance",
            "region": region,
            "instance_id": instance_id,
            "name": name_tag,
            "instance_type": itype,
            "state": state,  # Include state: running, stopped, terminated, etc.
            "avg_cpu_7d": round(avg_cpu, 2) if avg_cpu >= 0 else -1.0,
            "monthly_cost_usd": monthly_cost if state == "running" else 0.0,  # Only cost for running instances
            "recommendation": recommendation,
            "priority": priority,
            "potential_savings_usd": savings_analysis.get("potential_savings", 0),
            "action": savings_analysis.get("action", recommendation),
            "implementation_steps": savings_analysis.get("implementation_steps", []),
            "roi_days": savings_analysis.get("roi_days", 0),
        }
        
        out.append(finding)

    return out


def scan_ebs_available(region: str) -> List[Dict]:
    """
    Return findings for available (detached) EBS volumes with cost analysis.
    """
    # Import pricing service for accurate calculations
    try:
        from core.services.pricing_service import pricing_service
    except ImportError:
        pricing_service = None
    
    ec2 = _aws_client("ec2", region)
    vols = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}]).get("Volumes", [])
    out: List[Dict] = []
    
    for v in vols:
        vid = v.get("VolumeId")
        size = v.get("Size", 0)
        volume_type = v.get("VolumeType", "gp3")
        
        # Calculate accurate monthly cost and savings
        if pricing_service:
            monthly_cost = pricing_service.get_ebs_monthly_cost(size, volume_type)
            savings_analysis = pricing_service.calculate_ebs_savings(size, volume_type)
        else:
            # Fallback calculation
            monthly_cost = size * 0.08  # Approximate gp3 pricing
            savings_analysis = {
                "potential_savings": monthly_cost,
                "action": f"Delete unused {size}GB {volume_type} volume",
                "implementation_steps": ["Create snapshot first, then delete volume"]
            }
        
        out.append(
            {
                "type": "unused_ebs",
                "region": region,
                "volume_id": vid,
                "size_gb": size,
                "volume_type": volume_type,
                "monthly_cost_usd": monthly_cost,
                "potential_savings_usd": savings_analysis.get("potential_savings", monthly_cost),
                "recommendation": "Delete or snapshot then delete",
                "priority": "HIGH",
                "action": savings_analysis.get("action", "Delete unused volume"),
                "implementation_steps": savings_analysis.get("implementation_steps", []),
                "notes": f"Detached EBS ~{size}GB (consider snapshot+delete)",
            }
        )
    return out


def scan_eips_unassociated(region: str) -> List[Dict]:
    """
    Return findings for unassociated Elastic IPs with cost analysis.
    """
    # Import pricing service for accurate calculations
    try:
        from core.services.pricing_service import pricing_service
    except ImportError:
        pricing_service = None
    
    ec2 = _aws_client("ec2", region)
    addrs = ec2.describe_addresses().get("Addresses", [])
    out: List[Dict] = []
    
    for a in addrs:
        if not a.get("AssociationId"):
            # Calculate accurate monthly cost and savings
            if pricing_service:
                monthly_cost = pricing_service.get_eip_monthly_cost()
                savings_analysis = pricing_service.calculate_eip_savings()
            else:
                # Fallback calculation
                monthly_cost = 3.6  # Approximate monthly cost
                savings_analysis = {
                    "potential_savings": monthly_cost,
                    "action": "Release unassociated Elastic IP",
                    "implementation_steps": ["Go to EC2 Console → Elastic IPs → Release"]
                }
            
            out.append(
                {
                    "type": "unused_eip",
                    "region": region,
                    "allocation_id": a.get("AllocationId"),
                    "public_ip": a.get("PublicIp"),
                    "monthly_cost_usd": monthly_cost,
                    "potential_savings_usd": savings_analysis.get("potential_savings", monthly_cost),
                    "recommendation": "Release Elastic IP",
                    "priority": "HIGH",
                    "action": savings_analysis.get("action", "Release Elastic IP"),
                    "implementation_steps": savings_analysis.get("implementation_steps", []),
                    "notes": "EIP charges when not associated",
                }
            )
    return out


# ----------------------
# Public entry points
# ----------------------
def scan_ec2(region: str | None = None):
    """
    Primary entry point used by the UI adapter (scans.py).
    Returns a list[dict] for EC2 idle instances only (the EC2 page focuses on instances).
    Other findings (EBS/EIP) are still available via helper functions above if you want to surface them later.
    """
    region = region or DEFAULT_REGION
    return scan_ec2_idle(region)


def run(region: str | None = None):
    """
    Backward-compatible CLI entry point.
    Aggregates all EC2/EBS/EIP findings and returns them (no CSV).
    """
    region = region or DEFAULT_REGION
    findings: List[Dict] = []
    findings += scan_ec2_idle(region)
    findings += scan_ebs_available(region)
    findings += scan_eips_unassociated(region)

    # brief console output
    for r in findings:
        t = r.get("type")
        if t == "idle_instance":
            print(
                f"[EC2 idle] {r.get('instance_id')} "
                f"avg_cpu_7d={r.get('avg_cpu_7d')}% cost={r.get('monthly_cost_usd')} -> {r.get('recommendation')}"
            )
        elif t == "unused_ebs":
            print(f"[EBS free] {r.get('volume_id')} size={r.get('size_gb')}GB -> {r.get('recommendation')}")
        elif t == "unused_eip":
            print(f"[EIP] {r.get('public_ip')} -> {r.get('recommendation')}")

    return findings


if __name__ == "__main__":
    # Allow standalone testing: python -m scanners.ec2_scanner --region us-east-1
    import argparse

    p = argparse.ArgumentParser(description="Cloud Waste Tracker – EC2/EBS/EIP (live, no CSV)")
    p.add_argument("--region", default=DEFAULT_REGION)
    args = p.parse_args()

    run(region=args.region)
