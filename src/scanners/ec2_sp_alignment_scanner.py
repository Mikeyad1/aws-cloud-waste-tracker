"""
EC2 vs Savings Plans Alignment Scanner

This module cross-references EC2 instances with Savings Plans coverage to determine
optimal SP usage and identify misalignment issues.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from boto3.session import Session
from botocore.exceptions import ClientError

LOOKBACK_DAYS = 7  # Use shorter lookback for alignment analysis


def _utc_today() -> datetime:
    return datetime.utcnow()


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _get_idle_score(cpu_util: float) -> float:
    """Calculate idle score from CPU utilization (0-100, higher = more idle)."""
    if cpu_util < 0:
        return 100.0  # No data = assume idle
    return max(0.0, min(100.0, (1.0 - (cpu_util / 100.0)) * 100.0))


def _get_alignment_flag(
    cpu_util: float, sp_coverage_hr: float, ondemand_rate_hr: float, threshold: float = 20.0
) -> str:
    """Determine alignment flag based on utilization and SP coverage."""
    if sp_coverage_hr > 0:
        if cpu_util < threshold:
            return "Low-util consuming SP"
        else:
            return "Aligned"
    else:
        if cpu_util >= 50.0:
            return "Not covered high-util"
        elif cpu_util >= threshold:
            return "Not covered medium-util"
        else:
            return "Not covered low-util"


def _get_recommendation(alignment_flag: str, cpu_util: float) -> str:
    """Generate recommendation based on alignment flag."""
    if alignment_flag == "Low-util consuming SP":
        if cpu_util < 5:
            return "Stop instance"
        else:
            return "Rightsize/Stop"
    elif alignment_flag == "Not covered high-util":
        return "Purchase SP"
    elif alignment_flag == "Not covered medium-util":
        return "Consider SP"
    elif alignment_flag == "Aligned":
        return "No action"
    else:
        return "Review instance sizing"


def _calculate_potential_savings(
    alignment_flag: str, cpu_util: float, monthly_cost: float, sp_coverage_hr: float, ondemand_rate_hr: float
) -> float:
    """Calculate potential monthly savings based on alignment."""
    if alignment_flag == "Low-util consuming SP":
        # Savings from stopping/rightsizing
        if cpu_util < 5:
            return monthly_cost  # Can stop entirely
        else:
            # Estimate rightsizing can save 50-70% for low util instances
            return monthly_cost * 0.6
    elif alignment_flag in ["Not covered high-util", "Not covered medium-util"]:
        # Potential savings from purchasing SP (typically 30-40% for compute)
        if ondemand_rate_hr > 0:
            estimated_sp_rate = ondemand_rate_hr * 0.65  # 35% savings estimate
            savings_per_hr = ondemand_rate_hr - estimated_sp_rate
            return savings_per_hr * 24 * 30
    return 0.0


def scan_ec2_sp_alignment(
    ec2_df: pd.DataFrame, sp_df: pd.DataFrame, aws_credentials: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Cross-reference EC2 instances with Savings Plans to determine alignment.
    
    Args:
        ec2_df: DataFrame with EC2 instance data (must have columns: instance_id, region, 
                avg_cpu_7d, monthly_cost_usd, state, instance_type)
        sp_df: DataFrame with Savings Plans data (from scan_savings_plans)
        aws_credentials: Optional AWS credentials dict
    
    Returns:
        DataFrame with alignment analysis including:
        - Instance ID, Region, State
        - CPU Utilization %, Idle Score
        - On-Demand Rate ($/hr)
        - SP Coverage ($/hr)
        - Alignment Flag
        - Potential Savings (Monthly)
        - Recommendation
    """
    if ec2_df.empty:
        return pd.DataFrame(
            columns=[
                "Instance ID",
                "Region",
                "State",
                "CPU Utilization %",
                "Idle Score",
                "On-Demand Rate ($/hr)",
                "SP Coverage ($/hr)",
                "Alignment Flag",
                "Potential Savings (Monthly)",
                "Recommendation",
            ]
        )
    
    if sp_df.empty:
        # No SP data - all instances are uncovered
        return _create_uncovered_alignment(ec2_df)
    
    # Normalize column names
    ec2_working = ec2_df.copy()
    
    # Ensure required columns exist
    required_cols = {
        "instance_id": ["instance_id", "InstanceId", "instance"],
        "region": ["region", "Region"],
        "avg_cpu_7d": ["avg_cpu_7d", "CPU Utilization (%)", "cpu_utilization", "avg_cpu"],
        "monthly_cost_usd": ["monthly_cost_usd", "Monthly Cost (USD)", "monthly_cost", "cost"],
        "state": ["state", "State"],
        "instance_type": ["instance_type", "InstanceType", "type"],
    }
    
    for standard_col, aliases in required_cols.items():
        if standard_col not in ec2_working.columns:
            for alias in aliases:
                if alias in ec2_working.columns:
                    ec2_working[standard_col] = ec2_working[alias]
                    break
        if standard_col not in ec2_working.columns:
            # Set defaults
            if standard_col == "avg_cpu_7d":
                ec2_working[standard_col] = 0.0
            elif standard_col == "monthly_cost_usd":
                ec2_working[standard_col] = 0.0
            elif standard_col == "state":
                ec2_working[standard_col] = "unknown"
            elif standard_col == "instance_type":
                ec2_working[standard_col] = "unknown"
            else:
                ec2_working[standard_col] = ""
    
    # Try to get SP coverage from Cost Explorer if credentials available
    sp_coverage_map = {}
    if aws_credentials or not os.getenv("AWS_ACCESS_KEY_ID"):
        try:
            sp_coverage_map = _get_sp_coverage_from_cost_explorer(
                ec2_working, sp_df, aws_credentials
            )
        except Exception:
            # Fallback to inference-based matching
            sp_coverage_map = _infer_sp_coverage(ec2_working, sp_df)
    else:
        sp_coverage_map = _infer_sp_coverage(ec2_working, sp_df)
    
    # Build alignment dataframe
    alignment_rows = []
    
    for _, instance in ec2_working.iterrows():
        instance_id = str(instance.get("instance_id", "unknown"))
        region = str(instance.get("region", "unknown"))
        state = str(instance.get("state", "unknown")).lower()
        cpu_util = float(instance.get("avg_cpu_7d", 0.0))
        monthly_cost = float(instance.get("monthly_cost_usd", 0.0))
        instance_type = str(instance.get("instance_type", "unknown"))
        
        # Calculate hourly rates
        ondemand_rate_hr = monthly_cost / (24 * 30) if monthly_cost > 0 else 0.0
        
        # Get SP coverage for this instance
        sp_coverage_hr = sp_coverage_map.get(instance_id, 0.0)
        
        # Calculate metrics
        idle_score = _get_idle_score(cpu_util)
        alignment_flag = _get_alignment_flag(cpu_util, sp_coverage_hr, ondemand_rate_hr)
        recommendation = _get_recommendation(alignment_flag, cpu_util)
        potential_savings = _calculate_potential_savings(
            alignment_flag, cpu_util, monthly_cost, sp_coverage_hr, ondemand_rate_hr
        )
        
        alignment_rows.append(
            {
                "Instance ID": instance_id,
                "Region": region,
                "State": state.title(),
                "CPU Utilization %": max(0.0, min(100.0, cpu_util)),
                "Idle Score": round(idle_score, 1),
                "On-Demand Rate ($/hr)": round(ondemand_rate_hr, 4),
                "SP Coverage ($/hr)": round(sp_coverage_hr, 4),
                "Alignment Flag": alignment_flag,
                "Potential Savings (Monthly)": round(potential_savings, 2),
                "Recommendation": recommendation,
            }
        )
    
    return pd.DataFrame(alignment_rows)


def _create_uncovered_alignment(ec2_df: pd.DataFrame) -> pd.DataFrame:
    """Create alignment dataframe when no SP data exists (all instances uncovered)."""
    alignment_rows = []
    
    for _, instance in ec2_df.iterrows():
        instance_id = str(instance.get("instance_id", instance.get("InstanceId", "unknown")))
        region = str(instance.get("region", instance.get("Region", "unknown")))
        state = str(instance.get("state", instance.get("State", "unknown"))).lower()
        
        cpu_util = float(
            instance.get("avg_cpu_7d", instance.get("CPU Utilization (%)", instance.get("avg_cpu", 0.0)))
        )
        monthly_cost = float(
            instance.get(
                "monthly_cost_usd",
                instance.get("Monthly Cost (USD)", instance.get("monthly_cost", instance.get("cost", 0.0))),
            )
        )
        
        ondemand_rate_hr = monthly_cost / (24 * 30) if monthly_cost > 0 else 0.0
        idle_score = _get_idle_score(cpu_util)
        
        alignment_flag = _get_alignment_flag(cpu_util, 0.0, ondemand_rate_hr)
        recommendation = _get_recommendation(alignment_flag, cpu_util)
        potential_savings = _calculate_potential_savings(alignment_flag, cpu_util, monthly_cost, 0.0, ondemand_rate_hr)
        
        alignment_rows.append(
            {
                "Instance ID": instance_id,
                "Region": region,
                "State": state.title(),
                "CPU Utilization %": max(0.0, min(100.0, cpu_util)),
                "Idle Score": round(idle_score, 1),
                "On-Demand Rate ($/hr)": round(ondemand_rate_hr, 4),
                "SP Coverage ($/hr)": 0.0,
                "Alignment Flag": alignment_flag,
                "Potential Savings (Monthly)": round(potential_savings, 2),
                "Recommendation": recommendation,
            }
        )
    
    return pd.DataFrame(alignment_rows)


def _get_sp_coverage_from_cost_explorer(
    ec2_df: pd.DataFrame, sp_df: pd.DataFrame, aws_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, float]:
    """
    Use Cost Explorer API to get actual SP coverage per instance.
    This is the most accurate method.
    """
    coverage_map: Dict[str, float] = {}
    
    try:
        # Set up credentials in environment if provided
        env_backup = {}
        if aws_credentials:
            for key, value in aws_credentials.items():
                env_backup[key] = os.environ.get(key)
                if value:
                    os.environ[key] = value
        
        try:
            session = Session()
            ce_client = session.client("ce", region_name="us-east-1")
            
            # Get coverage for recent period
            end_dt = _utc_today().replace(hour=0, minute=0, second=0, microsecond=0)
            start_dt = end_dt - timedelta(days=LOOKBACK_DAYS)
            
            # Query Cost Explorer grouped by ResourceId to see which instances have SP coverage
            # Note: This requires proper permissions (ce:GetCostAndUsage)
            try:
                response = ce_client.get_cost_and_usage(
                    TimePeriod={"Start": _date_str(start_dt), "End": _date_str(end_dt)},
                    Granularity="DAILY",
                    Metrics=["AmortizedCost", "UnblendedCost"],
                    GroupBy=[
                        {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
                        {"Type": "DIMENSION", "Key": "SERVICE"},
                    ],
                    Filter={
                        "And": [
                            {"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}},
                            {"Dimensions": {"Key": "USAGE_TYPE_GROUP", "Values": ["EC2: Running Hours"]}},
                        ]
                    },
                )
                
                # Process results to extract SP coverage per instance
                for result in response.get("ResultsByTime", []):
                    for group in result.get("Groups", []):
                        keys = group.get("Keys", [])
                        if len(keys) >= 1:
                            resource_id = keys[0]  # Instance ID
                            # AmortizedCost includes SP discounts, UnblendedCost is on-demand
                            amortized = float(group.get("Metrics", {}).get("AmortizedCost", {}).get("Amount", 0.0))
                            unblended = float(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0.0))
                            
                            if resource_id.startswith("i-") and amortized < unblended:
                                # SP coverage = difference between unblended and amortized
                                # Divide by hours to get hourly coverage
                                hours_in_period = 24.0
                                sp_coverage = (unblended - amortized) / hours_in_period
                                if resource_id not in coverage_map:
                                    coverage_map[resource_id] = 0.0
                                coverage_map[resource_id] += sp_coverage
            except ClientError as e:
                # If we don't have permissions or API fails, fall back to inference
                print(f"Cost Explorer API failed (will use inference): {e}")
                pass
        finally:
            # Restore environment
            if aws_credentials:
                for key, old_value in env_backup.items():
                    if old_value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old_value
    except Exception as e:
        print(f"Error getting SP coverage from Cost Explorer: {e}")
        # Will fall back to inference
    
    return coverage_map


def _infer_sp_coverage(ec2_df: pd.DataFrame, sp_df: pd.DataFrame) -> Dict[str, float]:
    """
    Infer SP coverage by matching instances to SPs based on region and instance type compatibility.
    This is a fallback when Cost Explorer API is not available.
    """
    coverage_map: Dict[str, float] = {}
    
    if sp_df.empty:
        return coverage_map
    
    # Create a mapping of SP capacity by region and type
    # For simplicity, we'll distribute SP commitment proportionally to instance costs
    total_sp_commitment_hr = sp_df["Commitment ($/hr)"].sum() if "Commitment ($/hr)" in sp_df.columns else 0.0
    total_sp_usage_hr = sp_df["Actual Usage ($/hr)"].sum() if "Actual Usage ($/hr)" in sp_df.columns else 0.0
    
    if total_sp_commitment_hr == 0:
        return coverage_map
    
    # Group instances by region
    instances_by_region = {}
    for _, instance in ec2_df.iterrows():
        region = str(instance.get("region", "unknown"))
        if region not in instances_by_region:
            instances_by_region[region] = []
        instances_by_region[region].append(instance)
    
    # For each region, distribute SP coverage based on instance costs
    for region, instances in instances_by_region.items():
        # Find SPs that cover this region (multi-region SPs or region-specific)
        region_sps = sp_df[
            (sp_df["Region"] == region) | (sp_df["Region"] == "Multi-region")
        ]
        
        if region_sps.empty:
            continue
        
        region_sp_capacity = region_sps["Commitment ($/hr)"].sum()
        region_sp_usage = region_sps["Actual Usage ($/hr)"].sum()
        
        # Calculate total hourly cost for instances in this region
        total_instance_cost_hr = 0.0
        for inst in instances:
            monthly_cost = float(inst.get("monthly_cost_usd", 0.0))
            hourly_cost = monthly_cost / (24 * 30) if monthly_cost > 0 else 0.0
            total_instance_cost_hr += hourly_cost
        
        if total_instance_cost_hr == 0:
            continue
        
        # Distribute SP coverage proportionally to instance costs
        # Cap at the instance's actual cost (can't have more SP coverage than cost)
        for inst in instances:
            instance_id = str(inst.get("instance_id", "unknown"))
            monthly_cost = float(inst.get("monthly_cost_usd", 0.0))
            hourly_cost = monthly_cost / (24 * 30) if monthly_cost > 0 else 0.0
            
            if hourly_cost > 0:
                # Proportion of total cost this instance represents
                proportion = hourly_cost / total_instance_cost_hr
                # Allocate SP coverage proportionally
                allocated_coverage = min(hourly_cost, region_sp_usage * proportion)
                coverage_map[instance_id] = allocated_coverage
    
    return coverage_map

