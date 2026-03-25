# src/cwt_ui/services/enhanced_scans.py
"""
Enhanced scans service that provides clear, valuable recommendations with specific dollar amounts.
This replaces the basic scans with much more valuable data.
"""

from __future__ import annotations
from typing import Tuple, Optional, Mapping, List
import pandas as pd
import os

def run_all_scans(
    region: str | List[str] | None = None, 
    aws_credentials: Optional[Mapping[str, str]] = None, 
    aws_auth_method: str = "user"
) -> pd.DataFrame:
    """Run enhanced scans with clear cost analysis and actionable recommendations.
    
    Args:
        region: AWS region(s) to scan. Can be:
            - Single region string (e.g., "us-east-1")
            - List of regions (e.g., ["us-east-1", "us-west-2"])
            - None: auto-discover and scan all enabled regions
        aws_credentials: Optional credential overrides
        aws_auth_method: "user" or "role"
    """
    # Delegate to the main scans service which handles multi-region logic
    try:
        from cwt_ui.services.scans import run_all_scans as _run_all_scans
        ec2_df = _run_all_scans(region=region, aws_credentials=aws_credentials, aws_auth_method=aws_auth_method)
        
        # Enhance the results with better recommendations
        if not ec2_df.empty:
            ec2_df = _enhance_ec2_dataframe(ec2_df)
        
        return ec2_df
    except Exception as e:
        print(f"Enhanced scan error: {e}")
        return pd.DataFrame()


def _enhance_ec2_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Enhance EC2 DataFrame with clear recommendations."""
    if df.empty:
        return df
    return df.copy()  # Already enhanced by scanners, just pass through for now


def _enhance_ec2_data(findings: list) -> pd.DataFrame:
    """Enhance EC2 data with clear recommendations and dollar amounts."""
    if not findings:
        return pd.DataFrame()
    
    df = pd.DataFrame(findings)
    
    # Add clear, actionable recommendations
    def get_clear_recommendation(row):
        cpu = row.get('avg_cpu_7d', 0)
        cost = row.get('monthly_cost_usd', 0)
        instance_type = row.get('instance_type', '')
        name = row.get('name', 'Unnamed')
        
        if cpu < 1.0:
            return f"🛑 STOP: {name} - Save ${cost:.2f}/month (CPU only {cpu:.1f}%)"
        elif cpu < 3.0:
            return f"⚠️ STOP/DOWNSIZE: {name} - Save ${cost:.2f}/month (CPU {cpu:.1f}%)"
        elif cpu < 5.0:
            return f"🔄 DOWNSIZE: {name} - Save ${cost * 0.5:.2f}/month (CPU {cpu:.1f}%)"
        else:
            return f"✅ OK: {name} - CPU usage normal ({cpu:.1f}%)"
    
    def get_priority(row):
        cpu = row.get('avg_cpu_7d', 0)
        if cpu < 1.0:
            return "🔴 HIGH"
        elif cpu < 3.0:
            return "🔴 HIGH"
        elif cpu < 5.0:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"
    
    def get_action_steps(row):
        cpu = row.get('avg_cpu_7d', 0)
        cost = row.get('monthly_cost_usd', 0)
        instance_id = row.get('instance_id', '')
        name = row.get('name', 'Unnamed')
        
        if cpu < 5.0:
            return [
                f"1. Go to EC2 Console → Instances → {instance_id}",
                f"2. Select '{name}' and click 'Instance State' → 'Stop'",
                f"3. Confirm stop to save ${cost:.2f}/month",
                f"4. For permanent removal: 'Instance State' → 'Terminate'"
            ]
        else:
            return ["No action needed - CPU usage is normal"]
    
    # Add enhanced columns
    df['clear_recommendation'] = df.apply(get_clear_recommendation, axis=1)
    df['priority'] = df.apply(get_priority, axis=1)
    df['action_steps'] = df.apply(get_action_steps, axis=1)
    df['potential_savings_usd'] = df.apply(lambda row: 
        row.get('monthly_cost_usd', 0) if row.get('avg_cpu_7d', 0) < 5.0 else 0, axis=1)
    
    # Rename columns for clarity
    df = df.rename(columns={
        'instance_id': 'Instance ID',
        'name': 'Name',
        'instance_type': 'Instance Type',
        'region': 'Region',
        'avg_cpu_7d': 'CPU Usage (%)',
        'monthly_cost_usd': 'Monthly Cost ($)',
        'clear_recommendation': 'Recommendation',
        'potential_savings_usd': 'Potential Savings ($)'
    })
    
    return df



