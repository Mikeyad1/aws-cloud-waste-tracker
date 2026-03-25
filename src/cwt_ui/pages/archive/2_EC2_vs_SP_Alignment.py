from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Tuple

CURRENT_DIR = Path(__file__).resolve().parent
for candidate in [CURRENT_DIR, *CURRENT_DIR.parents]:
    candidate_src = candidate / "src"
    if candidate_src.exists():
        if str(candidate_src) not in sys.path:
            sys.path.insert(0, str(candidate_src))
        break

import altair as alt
import pandas as pd
import streamlit as st

from cwt_ui.components.kpi_card import render_kpi
from cwt_ui.components.ui.header import render_page_header
from cwt_ui.utils.money import format_usd

DEFAULT_LOOKBACK_DAYS = 30


def create_mock_alignment_data() -> pd.DataFrame:
    """Create mock EC2 vs Savings Plans alignment data for development."""
    today = pd.Timestamp.utcnow().normalize()
    
    # Mock instances with different utilization levels and SP coverage
    instances = [
        {
            "Instance ID": "i-xxxxxx",
            "Region": "us-east-1",
            "State": "running",
            "CPU Utilization %": 1.0,
            "Idle Score": 95,
            "On-Demand Rate ($/hr)": 0.12,
            "SP Coverage ($/hr)": 0.12,
            "Alignment Flag": "Low-util consuming SP",
            "Potential Savings (Monthly)": 85.0,
            "Recommendation": "Rightsize/Stop",
            "Instance Type": "t3.medium",
        },
        {
            "Instance ID": "i-yyyyyy",
            "Region": "eu-west-1",
            "State": "running",
            "CPU Utilization %": 65.0,
            "Idle Score": 20,
            "On-Demand Rate ($/hr)": 0.25,
            "SP Coverage ($/hr)": 0.25,
            "Alignment Flag": "Aligned",
            "Potential Savings (Monthly)": 0.0,
            "Recommendation": "No action",
            "Instance Type": "m5.large",
        },
        {
            "Instance ID": "i-zzzzzz",
            "Region": "ap-south-1",
            "State": "running",
            "CPU Utilization %": 70.0,
            "Idle Score": 15,
            "On-Demand Rate ($/hr)": 0.30,
            "SP Coverage ($/hr)": 0.00,
            "Alignment Flag": "Not covered high-util",
            "Potential Savings (Monthly)": 180.0,
            "Recommendation": "Purchase SP",
            "Instance Type": "c5.xlarge",
        },
        {
            "Instance ID": "i-aaaaaa",
            "Region": "us-east-1",
            "State": "running",
            "CPU Utilization %": 3.5,
            "Idle Score": 92,
            "On-Demand Rate ($/hr)": 0.18,
            "SP Coverage ($/hr)": 0.18,
            "Alignment Flag": "Low-util consuming SP",
            "Potential Savings (Monthly)": 120.0,
            "Recommendation": "Rightsize/Stop",
            "Instance Type": "t3.large",
        },
        {
            "Instance ID": "i-bbbbbb",
            "Region": "us-west-2",
            "State": "running",
            "CPU Utilization %": 45.0,
            "Idle Score": 35,
            "On-Demand Rate ($/hr)": 0.22,
            "SP Coverage ($/hr)": 0.22,
            "Alignment Flag": "Aligned",
            "Potential Savings (Monthly)": 0.0,
            "Recommendation": "No action",
            "Instance Type": "m5.medium",
        },
        {
            "Instance ID": "i-cccccc",
            "Region": "us-east-1",
            "State": "running",
            "CPU Utilization %": 8.0,
            "Idle Score": 85,
            "On-Demand Rate ($/hr)": 0.15,
            "SP Coverage ($/hr)": 0.15,
            "Alignment Flag": "Low-util consuming SP",
            "Potential Savings (Monthly)": 90.0,
            "Recommendation": "Rightsize/Stop",
            "Instance Type": "t3.small",
        },
        {
            "Instance ID": "i-dddddd",
            "Region": "eu-west-1",
            "State": "running",
            "CPU Utilization %": 75.0,
            "Idle Score": 12,
            "On-Demand Rate ($/hr)": 0.28,
            "SP Coverage ($/hr)": 0.00,
            "Alignment Flag": "Not covered high-util",
            "Potential Savings (Monthly)": 190.0,
            "Recommendation": "Purchase SP",
            "Instance Type": "r5.large",
        },
        {
            "Instance ID": "i-eeeeee",
            "Region": "us-west-2",
            "State": "running",
            "CPU Utilization %": 55.0,
            "Idle Score": 28,
            "On-Demand Rate ($/hr)": 0.20,
            "SP Coverage ($/hr)": 0.20,
            "Alignment Flag": "Aligned",
            "Potential Savings (Monthly)": 0.0,
            "Recommendation": "No action",
            "Instance Type": "c5.large",
        },
    ]
    
    return pd.DataFrame(instances)


def compute_utilization_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Compute SP coverage by utilization bands."""
    if df.empty:
        return pd.DataFrame()
    
    def assign_band(cpu_util: float) -> str:
        if cpu_util < 5:
            return "0-5%"
        elif cpu_util < 10:
            return "5-10%"
        elif cpu_util < 20:
            return "10-20%"
        elif cpu_util < 50:
            return "20-50%"
        else:
            return "50%+"
    
    working = df.copy()
    working["utilization_band"] = working["CPU Utilization %"].apply(assign_band)
    
    # Only count instances with SP coverage
    sp_covered = working[working["SP Coverage ($/hr)"] > 0].copy()
    
    if sp_covered.empty:
        return pd.DataFrame(columns=["utilization_band", "sp_coverage_hr"])
    
    grouped = sp_covered.groupby("utilization_band")["SP Coverage ($/hr)"].sum().reset_index()
    grouped.columns = ["utilization_band", "sp_coverage_hr"]
    
    # Ensure all bands are present
    all_bands = ["0-5%", "5-10%", "10-20%", "20-50%", "50%+"]
    for band in all_bands:
        if band not in grouped["utilization_band"].values:
            grouped = pd.concat([grouped, pd.DataFrame([{"utilization_band": band, "sp_coverage_hr": 0.0}])], ignore_index=True)
    
    grouped = grouped.sort_values("utilization_band", key=lambda x: x.map({
        "0-5%": 0, "5-10%": 1, "10-20%": 2, "20-50%": 3, "50%+": 4
    }))
    
    return grouped


def compute_coverage_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Compute SP coverage vs on-demand spend by region."""
    if df.empty:
        return pd.DataFrame()
    
    working = df.copy()
    
    # Calculate on-demand rate (total - SP covered)
    working["ondemand_spend_hr"] = working["On-Demand Rate ($/hr)"] - working["SP Coverage ($/hr)"]
    working["ondemand_spend_hr"] = working["ondemand_spend_hr"].clip(lower=0.0)
    
    grouped = working.groupby("Region").agg({
        "SP Coverage ($/hr)": "sum",
        "ondemand_spend_hr": "sum",
        "CPU Utilization %": lambda x: (x < 20).sum()  # Count of low-util instances
    }).reset_index()
    
    grouped.columns = ["region", "sp_covered_hr", "ondemand_spend_hr", "low_util_count"]
    
    return grouped


def plot_sp_coverage_by_band(band_df: pd.DataFrame) -> alt.Chart | None:
    """Plot SP coverage by utilization band with modern styling."""
    if band_df.empty:
        return None
    
    # Add monthly value for tooltip
    band_df = band_df.copy()
    band_df["monthly_value"] = band_df["sp_coverage_hr"] * 24 * 30
    
    # Color scheme with clear utilization mapping
    color_domain = ["0-5%", "5-10%", "10-20%", "20-50%", "50%+"]
    color_range = ["#ef4444", "#f97316", "#fbbf24", "#84cc16", "#22c55e"]
    
    return (
        alt.Chart(band_df)
        .mark_bar(
            cornerRadiusEnd=8,
            cornerRadiusTopLeft=8,
            cornerRadiusTopRight=8,
            strokeWidth=0,
            opacity=0.9
        )
        .encode(
            x=alt.X(
                "utilization_band:N",
                title="Utilization Band",
                sort=color_domain,
                axis=alt.Axis(
                    labelFontSize=12,
                    labelFontWeight=500,
                    titleFontSize=13,
                    titleFontWeight=600,
                    titlePadding=10,
                    labelPadding=8
                )
            ),
            y=alt.Y(
                "sp_coverage_hr:Q",
                title="SP Coverage ($/hr)",
                axis=alt.Axis(
                    format="$.2f",
                    labelFontSize=11,
                    titleFontSize=13,
                    titleFontWeight=600,
                    titlePadding=15,
                    labelPadding=5,
                    grid=True,
                    gridOpacity=0.15
                )
            ),
            color=alt.Color(
                "utilization_band:N",
                title="CPU Utilization",
                scale=alt.Scale(domain=color_domain, range=color_range),
                legend=alt.Legend(
                    titleFontSize=13,
                    titleFontWeight=600,
                    labelFontSize=11,
                    labelLimit=200,
                    orient="right",
                    padding=10,
                    titlePadding=10,
                    columnPadding=15,
                    symbolType="square",
                    symbolSize=100,
                    offset=10
                )
            ),
            tooltip=[
                alt.Tooltip("utilization_band:N", title="Utilization Band"),
                alt.Tooltip("sp_coverage_hr:Q", title="SP Coverage ($/hr)", format="$.4f"),
                alt.Tooltip("monthly_value:Q", title="Monthly Value", format="$.2f")
            ]
        )
        .properties(
            height=320,
            padding={"left": 10, "right": 10, "top": 15, "bottom": 10}
        )
        .configure_view(
            strokeWidth=0,
            fill="#0d1117"
        )
        .configure_axis(
            domainColor="#c9d1d9",
            domainWidth=1,
            labelColor="#c9d1d9",
            titleColor="#c9d1d9",
            tickColor="#c9d1d9"
        )
    )


def plot_coverage_vs_ondemand_by_region(region_df: pd.DataFrame) -> alt.Chart | None:
    """Plot coverage vs on-demand spend by region with modern styling."""
    if region_df.empty:
        return None
    
    # Melt for grouped bar chart
    melted = region_df.melt(
        id_vars=["region"],
        value_vars=["sp_covered_hr", "ondemand_spend_hr"],
        var_name="spend_type",
        value_name="amount"
    )
    
    melted["spend_type"] = melted["spend_type"].map({
        "sp_covered_hr": "SP Covered",
        "ondemand_spend_hr": "On-Demand"
    })
    
    # Add monthly value for tooltip
    melted["monthly_amount"] = melted["amount"] * 24 * 30
    
    # Create base chart with shared encoding
    base = alt.Chart(melted).encode(
        x=alt.X(
            "region:N",
            title="Region",
            axis=alt.Axis(
                labelAngle=-35,
                labelFontSize=11,
                labelFontWeight=500,
                titleFontSize=13,
                titleFontWeight=600,
                titlePadding=10,
                labelPadding=8
            )
        ),
        y=alt.Y(
            "amount:Q",
            title="Spend ($/hr)",
            axis=alt.Axis(
                format="$.2f",
                labelFontSize=11,
                titleFontSize=13,
                titleFontWeight=600,
                titlePadding=15,
                labelPadding=5,
                grid=True,
                gridOpacity=0.15
            )
        ),
        color=alt.Color(
            "spend_type:N",
            title="Spend Type",
            scale=alt.Scale(
                domain=["SP Covered", "On-Demand"],
                range=["#3b82f6", "#ef4444"]
            ),
            legend=alt.Legend(
                titleFontSize=13,
                titleFontWeight=600,
                labelFontSize=11,
                labelLimit=200,
                orient="right",
                padding=10,
                titlePadding=10,
                columnPadding=15,
                symbolType="square",
                symbolSize=100,
                offset=10
            )
        ),
        tooltip=[
            alt.Tooltip("region:N", title="Region"),
            alt.Tooltip("spend_type:N", title="Spend Type"),
            alt.Tooltip("amount:Q", title="Hourly Spend ($/hr)", format="$.4f"),
            alt.Tooltip("monthly_amount:Q", title="Monthly Spend", format="$.2f")
        ]
    )
    
    # Create bars with rounded corners and set properties before faceting
    bars = (
        base
        .mark_bar(
            cornerRadiusEnd=8,
            cornerRadiusTopLeft=8,
            cornerRadiusTopRight=8,
            strokeWidth=0,
            opacity=0.9
        )
        .properties(
            width=alt.Step(80),
            height=320
        )
    )
    
    return (
        bars
        .facet(
            column=alt.Column(
                "spend_type:N",
                title=None,
                header=alt.Header(
                    labelFontSize=12,
                    labelFontWeight=600,
                    labelPadding=10
                )
            )
        )
        .resolve_scale(x="independent", y="shared")
        .configure_view(
            strokeWidth=0,
            fill="#0d1117"
        )
        .configure_axis(
            domainColor="#c9d1d9",
            domainWidth=1,
            labelColor="#c9d1d9",
            titleColor="#c9d1d9",
            tickColor="#c9d1d9"
        )
    )


def load_alignment_data() -> Tuple[pd.DataFrame, bool]:
    """Load EC2 vs SP alignment data from session state, compute if needed, or return mock data."""
    demo_mode = os.getenv("CWT_DEMO_MODE", "false").strip().lower() == "true"
    if demo_mode:
        return create_mock_alignment_data(), True
    
    alignment_df = st.session_state.get("EC2_SP_ALIGNMENT_DF")
    if alignment_df is None or not isinstance(alignment_df, pd.DataFrame):
        alignment_df = pd.DataFrame()
    
    # If alignment data doesn't exist but we have EC2 and SP data, compute it automatically
    if alignment_df.empty:
        ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
        sp_df = st.session_state.get("SP_DF", pd.DataFrame())
        
        # Only compute if we have EC2 data (SP can be empty - means all instances uncovered)
        if not ec2_df.empty:
            try:
                from scanners.ec2_sp_alignment_scanner import scan_ec2_sp_alignment
                # Get AWS credentials if available
                aws_credentials = None
                if st.session_state.get("aws_override_enabled", False):
                    aws_credentials = {}
                    if st.session_state.get("aws_auth_method") == "role":
                        if st.session_state.get("aws_role_arn"):
                            aws_credentials["AWS_ROLE_ARN"] = st.session_state.get("aws_role_arn", "")
                            aws_credentials["AWS_EXTERNAL_ID"] = st.session_state.get("aws_external_id", "")
                            aws_credentials["AWS_ROLE_SESSION_NAME"] = st.session_state.get("aws_role_session_name", "CloudWasteTracker")
                
                alignment_df = scan_ec2_sp_alignment(ec2_df, sp_df, aws_credentials)
                st.session_state["EC2_SP_ALIGNMENT_DF"] = alignment_df
            except Exception as e:
                # If computation fails, return empty
                print(f"Error computing alignment: {e}")
                alignment_df = pd.DataFrame()
        else:
            alignment_df = pd.DataFrame()
    
    if alignment_df is None:
        alignment_df = pd.DataFrame()
    
    return alignment_df.copy(), False


def compute_key_metrics(df: pd.DataFrame) -> dict:
    """Compute key metrics from alignment data."""
    if df.empty:
        return {
            "total_sp_commitment_hr": 0.0,
            "effective_utilization_pct": 0.0,
            "unused_commitment_hr": 0.0,
            "misalignment_waste_monthly": 0.0,
            "low_util_sp_coverage_pct": 0.0,
        }
    
    total_sp_commitment_hr = df["SP Coverage ($/hr)"].sum()
    
    # Effective utilization: % of SP used by instances above utilization threshold (e.g., 20%)
    threshold = 20.0
    high_util_instances = df[df["CPU Utilization %"] >= threshold]
    high_util_sp_used = high_util_instances["SP Coverage ($/hr)"].sum()
    effective_utilization_pct = (high_util_sp_used / total_sp_commitment_hr * 100.0) if total_sp_commitment_hr > 0 else 0.0
    
    # Unused commitment: instances with SP coverage but very low utilization
    low_util_instances = df[df["CPU Utilization %"] < threshold]
    unused_commitment_hr = low_util_instances["SP Coverage ($/hr)"].sum()
    
    # Misalignment waste: monthly cost of SP covering low-utilization resources
    misalignment_waste_monthly = unused_commitment_hr * 24 * 30
    
    # Low-util SP coverage: % of SP applied to instances below threshold
    low_util_sp_coverage_pct = (unused_commitment_hr / total_sp_commitment_hr * 100.0) if total_sp_commitment_hr > 0 else 0.0
    
    return {
        "total_sp_commitment_hr": total_sp_commitment_hr,
        "effective_utilization_pct": effective_utilization_pct,
        "unused_commitment_hr": unused_commitment_hr,
        "misalignment_waste_monthly": misalignment_waste_monthly,
        "low_util_sp_coverage_pct": low_util_sp_coverage_pct,
    }


def generate_insights(df: pd.DataFrame, metrics: dict) -> list[str]:
    """Generate insights based on alignment data."""
    insights = []
    
    if df.empty:
        return ["No alignment data available."]
    
    # False optimization detection
    low_util_sp_count = len(df[(df["CPU Utilization %"] < 20) & (df["SP Coverage ($/hr)"] > 0)])
    if low_util_sp_count > 0:
        insights.append(
            f"**False optimization detection**: {low_util_sp_count} instance(s) with low utilization (<20%) are consuming Savings Plans coverage, "
            f"wasting approximately {format_usd(metrics['misalignment_waste_monthly'])} monthly."
        )
    
    # Rightsizing opportunities
    rightsizing_candidates = df[(df["CPU Utilization %"] < 20) & (df["SP Coverage ($/hr)"] > 0)]
    if not rightsizing_candidates.empty:
        total_savings = rightsizing_candidates["Potential Savings (Monthly)"].sum()
        insights.append(
            f"**Rightsizing opportunities**: {len(rightsizing_candidates)} instance(s) could be downsized or scheduled off-hours, "
            f"potentially saving {format_usd(total_savings)} monthly."
        )
    
    # SP purchase recommendations
    high_util_uncovered = df[(df["CPU Utilization %"] >= 50) & (df["SP Coverage ($/hr)"] == 0)]
    if not high_util_uncovered.empty:
        total_potential = high_util_uncovered["Potential Savings (Monthly)"].sum()
        insights.append(
            f"**SP purchase recommendations**: {len(high_util_uncovered)} high-utilization instance(s) (≥50%) are not covered by Savings Plans. "
            f"Purchasing SP coverage could save approximately {format_usd(total_potential)} monthly."
        )
    
    if not insights:
        insights.append("No major alignment issues detected. Your EC2 instances are well-aligned with Savings Plans coverage.")
    
    return insights


# Page layout (skip when embedded in Optimization > Commitment tab)
if not os.environ.get("CWT_AS_TAB"):
    st.set_page_config(page_title="EC2 vs Savings Plans Alignment", page_icon="🔗", layout="wide")
    render_page_header(
        title="EC2 vs Savings Plans Alignment",
        subtitle="Consolidated view of how EC2 instance usage aligns with Savings Plans commitments, ensuring optimization is not just apparent but truly effective.",
        icon="🔗",
    )

alignment_df, is_demo = load_alignment_data()

if alignment_df.empty:
    secrets_env = ""
    try:
        secrets_env = st.secrets.get("env", "")
    except Exception:
        secrets_env = ""
    is_dev_env = (
        os.getenv("CWT_ENV", "").strip().lower() == "development"
        or os.getenv("APP_ENV", "").strip().lower() == "development"
        or secrets_env.strip().lower() == "dev"
    )
    
    # Check if we have EC2 or SP data that could be used for alignment
    ec2_df = st.session_state.get("ec2_df", pd.DataFrame())
    sp_df = st.session_state.get("SP_DF", pd.DataFrame())
    
    if is_dev_env:
        st.info("No EC2 vs Savings Plans alignment data detected. Click below to load demo data.")
        if st.button("Load Demo Data", type="primary"):
            mock_data = create_mock_alignment_data()
            st.session_state["EC2_SP_ALIGNMENT_DF"] = mock_data
            st.rerun()
    elif not ec2_df.empty:
        # We have EC2 data - alignment should have been computed automatically
        # If it's still empty, there was likely an error
        st.info(
            "EC2 instance data found, but alignment computation failed or is in progress. "
            "The alignment will be computed automatically when you run a scan that includes both EC2 instances and Savings Plans data."
        )
        st.info("💡 **Tip**: Run a scan from the AWS Setup page to cross-reference your EC2 instances with Savings Plans coverage.")
    else:
        st.info("Run a scan from the AWS Setup page to load EC2 instances and Savings Plans data. "
                "The alignment analysis will be computed automatically to show how your EC2 usage aligns with SP coverage.")
    st.stop()

# Compute key metrics
metrics = compute_key_metrics(alignment_df)

# Key Metrics Section with styled cards
st.markdown("## 🔑 Key Metrics")

# Add CSS for styled metric cards
st.markdown("""
<style>
    .metric-card {
        background: #121A2C;
        border: 1px solid #1E2740;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        border-color: #1E2740;
    }
    
    .metric-label {
        font-size: 12px;
        font-weight: 500;
        color: #c9d1d9;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.8;
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    
    .metric-help {
        font-size: 11px;
        color: #8b949e;
        margin-top: 8px;
        line-height: 1.4;
    }
    
    /* Ensure columns have proper spacing */
    div[data-testid="column"] {
        padding: 0 8px;
    }
    
    /* Responsive adjustments - Streamlit columns will handle wrapping */
    @media (max-width: 1200px) {
        div[data-testid="column"] {
            padding: 0 8px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Render metrics in styled cards using Streamlit columns for responsive layout
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

with kpi_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total SP hourly commitment</div>
        <div class="metric-value">{format_usd(metrics["total_sp_commitment_hr"])}</div>
        <div class="metric-help">Total hourly Savings Plans commitment covering EC2 instances.</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Effective utilization</div>
        <div class="metric-value">{metrics['effective_utilization_pct']:.1f}%</div>
        <div class="metric-help">% of SP used by instances above utilization threshold (≥20%).</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Unused commitment</div>
        <div class="metric-value">{format_usd(metrics["unused_commitment_hr"])}</div>
        <div class="metric-help">SP commitment consumed by low-utilization instances (<20%).</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Misalignment waste (monthly)</div>
        <div class="metric-value">{format_usd(metrics["misalignment_waste_monthly"])}</div>
        <div class="metric-help">Monthly cost of SP covering low-utilization resources.</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Low-util SP coverage</div>
        <div class="metric-value">{metrics['low_util_sp_coverage_pct']:.1f}%</div>
        <div class="metric-help">% of SP applied to instances below utilization threshold (<20%).</div>
    </div>
    """, unsafe_allow_html=True)

# Filters Section - Redesigned with card container
st.markdown("""
<style>
    .filters-card {
        background: #121A2C;
        border: 1px solid #1E2740;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 32px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }
    
    .filters-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;
    }
    
    .filters-title {
        font-size: 18px;
        font-weight: 600;
        color: #E6EDF7;
        margin-bottom: 4px;
    }
    
    .filters-subtitle {
        font-size: 13px;
        color: #A9B4CC;
        margin: 0;
    }
    
    .reset-filters-btn {
        background: #1E2740;
        border: 1px solid #2D3748;
        border-radius: 6px;
        padding: 6px 12px;
        color: #c9d1d9;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    .reset-filters-btn:hover {
        background: #2D3748;
        border-color: #3D4758;
    }
    
    .filters-content {
        display: flex;
        gap: 16px;
        align-items: flex-end;
        flex-wrap: wrap;
    }
    
    .filter-group {
        flex: 1;
        min-width: 200px;
    }
    
    .slider-value-badge {
        display: inline-block;
        background: #1E2740;
        border: 1px solid #2D3748;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        color: #c9d1d9;
        margin-left: 8px;
    }
    
    .filters-badge {
        display: inline-flex;
        align-items: center;
        background: #1E2740;
        border: 1px solid #2D3748;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 12px;
        color: #c9d1d9;
        margin-bottom: 16px;
        gap: 8px;
    }
    
    .filters-badge-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .filters-badge-separator {
        color: #3D4758;
    }
    
    /* Visual Analysis Section */
    .chart-section-header {
        margin-bottom: 32px;
        margin-top: 0;
    }
    
    .chart-section-title {
        font-size: 22px;
        font-weight: 700;
        color: #E6EDF7;
        margin-bottom: 6px;
    }
    
    .chart-section-subtitle {
        font-size: 14px;
        color: #A9B4CC;
        margin: 0;
        line-height: 1.5;
    }
    
    /* Chart Description Panel */
    .chart-panel {
        background: #121A2C;
        border: 1px solid #1E2740;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        max-height: 140px;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .chart-header {
        display: flex;
        align-items: flex-start;
        gap: 0;
    }
    
    .chart-icon {
        font-size: 16px;
        line-height: 1;
        margin-right: 8px;
        margin-top: 2px;
        flex-shrink: 0;
        opacity: 0.7;
    }
    
    .chart-header-content {
        flex: 1;
    }
    
    .chart-title {
        font-size: 16px;
        font-weight: 500;
        color: #E6EDF7;
        margin-bottom: 6px;
        line-height: 1.4;
    }
    
    .chart-description {
        font-size: 13px;
        color: #A9B4CC;
        margin: 0;
        line-height: 1.5;
    }
    
    .chart-divider {
        height: 1px;
        background: #1E2740;
        margin: 0 0 16px 0;
        border: none;
    }
    
    /* Unified Chart Card Container */
    .chart-card {
        background: #121A2C;
        border: 1px solid #1E2740;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        animation: fadeIn 0.3s ease-in;
    }
    
    .chart-canvas {
        width: 100%;
        min-height: 320px;
    }
    
    /* Remove any grid scaffolding */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        padding: 0 12px;
    }
    
    /* Ensure consistent margins */
    .chart-section-container {
        margin: 0;
        padding: 0;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-4px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .chart-updating {
        animation: shimmer 1.5s ease-in-out infinite;
    }
    
    @keyframes shimmer {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.7;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for filters if not exists
if "filter_regions" not in st.session_state:
    st.session_state.filter_regions = sorted(alignment_df["Region"].dropna().unique().tolist())
if "filter_flags" not in st.session_state:
    st.session_state.filter_flags = sorted(alignment_df["Alignment Flag"].dropna().unique().tolist())
if "filter_min_util" not in st.session_state:
    st.session_state.filter_min_util = 0.0

available_regions = sorted(alignment_df["Region"].dropna().unique().tolist())
available_flags = sorted(alignment_df["Alignment Flag"].dropna().unique().tolist())

# Filters Card Container
st.markdown("""
<div class="filters-card">
    <div class="filters-header">
        <div>
            <div class="filters-title">🔧 Chart Filters</div>
            <div class="filters-subtitle">Use these filters to customize the visual analysis below.</div>
        </div>
    </div>
    <div class="filters-content">
""", unsafe_allow_html=True)

# Filters in columns
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])

with filter_col1:
    selected_regions = st.multiselect(
        "Region",
        options=available_regions,
        default=st.session_state.filter_regions,
        key="filter_regions_select"
    )
    st.session_state.filter_regions = selected_regions

with filter_col2:
    selected_flags = st.multiselect(
        "Alignment Flag",
        options=available_flags,
        default=st.session_state.filter_flags,
        key="filter_flags_select"
    )
    st.session_state.filter_flags = selected_flags

with filter_col3:
    min_util = st.slider(
        "Min CPU Utilization %",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.filter_min_util),
        step=1.0,
        key="filter_min_util_slider"
    )
    st.session_state.filter_min_util = min_util

with filter_col4:
    st.markdown("<br>", unsafe_allow_html=True)  # Align button with filters
    if st.button("🔄 Reset", key="reset_filters_btn", help="Reset all filters to default values"):
        st.session_state.filter_regions = available_regions
        st.session_state.filter_flags = available_flags
        st.session_state.filter_min_util = 0.0
        st.rerun()

st.markdown("</div></div>", unsafe_allow_html=True)

# Filters Applied Badge
filter_summary_parts = []
if len(selected_regions) < len(available_regions):
    filter_summary_parts.append(f"Regions: {len(selected_regions)}")
if len(selected_flags) < len(available_flags):
    filter_summary_parts.append(f"Flags: {len(selected_flags)}")
if min_util > 0.0:
    filter_summary_parts.append(f"Min CPU: {min_util:.0f}%")

if filter_summary_parts:
    filter_badge_text = " | ".join(filter_summary_parts)
    st.markdown(f"""
    <div class="filters-badge">
        <span>📊 Filters applied:</span>
        <span class="filters-badge-item">{filter_badge_text}</span>
    </div>
    """, unsafe_allow_html=True)

# Apply filters
filtered_df = alignment_df.copy()
if selected_regions:
    filtered_df = filtered_df[filtered_df["Region"].isin(selected_regions)]
if selected_flags:
    filtered_df = filtered_df[filtered_df["Alignment Flag"].isin(selected_flags)]
filtered_df = filtered_df[filtered_df["CPU Utilization %"] >= min_util]

# Visual Analysis Section
st.markdown("""
<div class="chart-section-header">
    <div class="chart-section-title">📊 Visual Analysis</div>
    <div class="chart-section-subtitle">Explore how Savings Plans align with EC2 usage across utilization bands and regions.</div>
</div>
""", unsafe_allow_html=True)

# Chart Description Panels and Charts
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Description Panel
    st.markdown("""
    <div class="chart-panel">
        <div class="chart-header">
            <div class="chart-icon">•</div>
            <div class="chart-header-content">
                <div class="chart-title">Utilization Breakdown</div>
                <div class="chart-description">Shows how SP coverage is distributed across different CPU utilization levels. Lower utilization with SP coverage indicates waste.</div>
            </div>
        </div>
    </div>
    <hr class="chart-divider">
    """, unsafe_allow_html=True)
    
    # Chart Card
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    
    band_df = compute_utilization_bands(filtered_df)
    band_chart = plot_sp_coverage_by_band(band_df)
    if band_chart is not None:
        st.altair_chart(band_chart, use_container_width=True, theme=None)
    else:
        st.info("Not enough data to plot SP coverage by utilization band.")
    
    st.markdown("</div>", unsafe_allow_html=True)

with chart_col2:
    # Description Panel
    st.markdown("""
    <div class="chart-panel">
        <div class="chart-header">
            <div class="chart-icon">•</div>
            <div class="chart-header-content">
                <div class="chart-title">Regional Spend Comparison</div>
                <div class="chart-description">Compares SP-covered spending versus on-demand spending across regions. Identifies regions with optimization opportunities.</div>
            </div>
        </div>
    </div>
    <hr class="chart-divider">
    """, unsafe_allow_html=True)
    
    # Chart Card
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    
    region_df = compute_coverage_by_region(filtered_df)
    region_chart = plot_coverage_vs_ondemand_by_region(region_df)
    if region_chart is not None:
        st.altair_chart(region_chart, use_container_width=True, theme=None)
    else:
        st.info("Not enough data to plot coverage by region.")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Instance-Level Table
st.markdown("## 📋 Instance-Level SP Alignment Table")

table_df = filtered_df[
    [
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
].copy()

# Format columns for display
table_df["On-Demand Rate ($/hr)"] = table_df["On-Demand Rate ($/hr)"].apply(lambda x: format_usd(x, 4))
table_df["SP Coverage ($/hr)"] = table_df["SP Coverage ($/hr)"].apply(lambda x: format_usd(x, 4))
table_df["Potential Savings (Monthly)"] = table_df["Potential Savings (Monthly)"].apply(lambda x: format_usd(x, 2))
table_df["CPU Utilization %"] = table_df["CPU Utilization %"].apply(lambda x: f"{x:.1f}%")
table_df["Idle Score"] = table_df["Idle Score"].apply(lambda x: f"{x:.0f}")

st.dataframe(table_df, use_container_width=True, hide_index=True)

# Insights Section
st.markdown("## ⚡ Insights")

filtered_metrics = compute_key_metrics(filtered_df)
insights = generate_insights(filtered_df, filtered_metrics)

for insight in insights:
    st.markdown(f"- {insight}")

if is_demo:
    st.caption("Showing demo data (CWT_DEMO_MODE enabled).")





