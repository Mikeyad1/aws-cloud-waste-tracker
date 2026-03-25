# src/cwt_ui/components/recommendations.py
"""
Enhanced recommendations component that shows actionable steps and cost savings.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional

def render_recommendations_summary(ec2_df: pd.DataFrame, formatters) -> None:
    """Render a summary of recommendations with implementation steps."""
    
    # Collect all actionable recommendations
    recommendations = []
    
    # Process EC2 recommendations
    if ec2_df is not None and not ec2_df.empty:
        for _, row in ec2_df.iterrows():
            if row.get("recommendation", "").upper() != "OK":
                recommendations.append({
                    "type": "EC2 Instance",
                    "resource": f"{row.get('name', 'Unnamed')} ({row.get('instance_id', '')})",
                    "priority": row.get("priority", "MEDIUM"),
                    "monthly_cost": row.get("monthly_cost_usd", 0),
                    "potential_savings": row.get("potential_savings_usd", 0),
                    "action": row.get("action", row.get("recommendation", "")),
                    "implementation_steps": row.get("implementation_steps", []),
                    "details": f"CPU: {row.get('avg_cpu_7d', 0):.1f}% | Type: {row.get('instance_type', '')}"
                })
    
    if not recommendations:
        st.info("🎉 Great! No optimization recommendations found. Your AWS resources are well-optimized.")
        return
    
    # Sort by potential savings (highest first)
    recommendations.sort(key=lambda x: x["potential_savings"], reverse=True)
    
    # Display recommendations
    st.subheader("🎯 Optimization Recommendations")
    
    total_savings = sum(r["potential_savings"] for r in recommendations)
    st.success(f"**Total Potential Savings: {formatters.currency(total_savings)}/month** ({formatters.currency(total_savings * 12)}/year)")
    
    # Group by priority
    high_priority = [r for r in recommendations if r["priority"] == "HIGH"]
    medium_priority = [r for r in recommendations if r["priority"] == "MEDIUM"]
    low_priority = [r for r in recommendations if r["priority"] == "LOW"]
    
    for priority_group, title, color in [
        (high_priority, "🔴 High Priority", "error"),
        (medium_priority, "🟡 Medium Priority", "warning"),
        (low_priority, "🟢 Low Priority", "success")
    ]:
        if priority_group:
            st.markdown(f"### {title}")
            
            for i, rec in enumerate(priority_group):
                with st.expander(f"{rec['type']}: {rec['resource']} - Save {formatters.currency(rec['potential_savings'])}/month", expanded=i < 2):
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Action:** {rec['action']}")
                        st.write(f"**Details:** {rec['details']}")
                        st.write(f"**Current Cost:** {formatters.currency(rec['monthly_cost'])}/month")
                        st.write(f"**Potential Savings:** {formatters.currency(rec['potential_savings'])}/month")
                    
                    with col2:
                        if rec['potential_savings'] > 0:
                            savings_percent = (rec['potential_savings'] / rec['monthly_cost'] * 100) if rec['monthly_cost'] > 0 else 0
                            st.metric("Savings %", f"{savings_percent:.1f}%")
                    
                    # Implementation steps
                    if rec['implementation_steps']:
                        st.markdown("**Implementation Steps:**")
                        for step in rec['implementation_steps']:
                            st.write(f"• {step}")
                    else:
                        st.info("Implementation steps will be provided in the detailed view.")
                    
                    st.divider()


def render_quick_actions(ec2_df: pd.DataFrame) -> None:
    """Render quick action buttons for common optimizations."""
    
    st.subheader("⚡ Quick Actions")
    
    # Calculate quick stats
    ec2_waste = 0
    
    if ec2_df is not None and not ec2_df.empty:
        ec2_waste = ec2_df.get("potential_savings_usd", pd.Series()).sum()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if ec2_waste > 0:
            st.button(
                f"🛑 Stop Idle Instances",
                help=f"Stop instances with low CPU usage. Potential savings: ${ec2_waste:.2f}/month",
                disabled=True  # Disabled for demo - would trigger actual AWS API calls
            )
        else:
            st.button("🛑 Stop Idle Instances", disabled=True, help="No idle instances found")
    
    with col2:
        st.button(
            f"📊 Generate Cost Report",
            help="Generate detailed cost optimization report",
            disabled=True  # Disabled for demo
        )
    
    st.caption("💡 Quick actions are disabled in demo mode. In production, these would execute the optimizations automatically.")
