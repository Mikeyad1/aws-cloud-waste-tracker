"""
Utility functions for calculating metrics and summaries across different pages.
"""

import pandas as pd
import streamlit as st
import os


def debug_write(message: str):
    """Debug messages disabled - no-op function"""
    pass  # Debug messages removed from UI


def compute_summary(df: pd.DataFrame) -> dict:
    """
    Compute summary metrics for a dataframe with robust column detection.
    
    Args:
        df: DataFrame containing cost and savings data
        
    Returns:
        Dictionary with total_cost, potential_savings, and waste_count
    """
    if df.empty:
        return {"total_cost": 0, "potential_savings": 0, "waste_count": 0}
    
    # Try multiple possible column names for cost and savings
    cost_columns = ['monthly_cost_usd', 'Monthly Cost ($)', 'monthly_cost', 'cost']
    savings_columns = ['potential_savings_usd', 'Potential Savings ($)', 'potential_savings', 'savings']
    
    # Find the actual cost column
    cost_col = None
    for col in cost_columns:
        if col in df.columns:
            cost_col = col
            break
    
    # Find the actual savings column  
    savings_col = None
    for col in savings_columns:
        if col in df.columns:
            savings_col = col
            break
    
    # Calculate totals
    total_cost = df[cost_col].sum() if cost_col else 0
    potential_savings = df[savings_col].sum() if savings_col else 0
    waste_count = len(df)
    
    # Debug: Show what columns were found
    debug_write(f"🔍 **Found cost column:** {cost_col}, **Found savings column:** {savings_col}")
    debug_write(f"🔍 **Cost values:** {df[cost_col].tolist() if cost_col else 'None'}")
    debug_write(f"🔍 **Savings values:** {df[savings_col].tolist() if savings_col else 'None'}")
    
    return {
        "total_cost": total_cost,
        "potential_savings": potential_savings,
        "waste_count": waste_count
    }


def render_metrics_cards(total_cost: float, potential_savings: float, waste_count: int, savings_percent: float = None) -> None:
    """
    Render the standard metrics cards used across pages.
    
    Args:
        total_cost: Total monthly cost
        potential_savings: Potential savings amount
        waste_count: Number of waste items
        savings_percent: Optional savings percentage (calculated if not provided)
    """
    if savings_percent is None:
        savings_percent = (potential_savings / total_cost * 100) if total_cost > 0 else 0
    
    # Beautiful metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="beautiful-metric">
            <div class="beautiful-metric-value">${total_cost:,.2f}</div>
            <div class="beautiful-metric-label">Total Monthly Cost</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="beautiful-metric">
            <div class="beautiful-metric-value">${potential_savings:,.2f}</div>
            <div class="beautiful-metric-label">Potential Savings</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="beautiful-metric">
            <div class="beautiful-metric-value">{waste_count}</div>
            <div class="beautiful-metric-label">Waste Items</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="beautiful-metric">
            <div class="beautiful-metric-value">{savings_percent:.1f}%</div>
            <div class="beautiful-metric-label">Savings Potential</div>
        </div>
        """, unsafe_allow_html=True)

