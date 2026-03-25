"""
Region selector component for scan UI.
Allows users to choose which regions to scan.
"""

import streamlit as st
from typing import List, Optional
import os


def render_region_selector(
    default_regions: Optional[List[str]] = None,
    allow_multi_region: bool = True
) -> List[str]:
    """
    Render region selector UI and return selected regions.
    
    Args:
        default_regions: Default regions to show (if None, auto-discovers)
        allow_multi_region: Allow selecting multiple regions
    
    Returns:
        List of selected region names
    """
    # Initialize session state
    if "scan_regions" not in st.session_state:
        st.session_state["scan_regions"] = default_regions or ["us-east-1"]
    
    if "scan_mode" not in st.session_state:
        st.session_state["scan_mode"] = "auto"  # auto, single, multi
    
    # Discover available regions
    try:
        from core.services.region_service import discover_enabled_regions, get_region_display_name as _get_region_name
        
        # Get current credentials for discovery
        aws_credentials = None
        aws_auth_method = st.session_state.get("aws_auth_method", "user")
        
        if st.session_state.get("aws_override_enabled", False):
            aws_credentials = {
                "AWS_ACCESS_KEY_ID": st.session_state.get("aws_access_key_id", ""),
                "AWS_SECRET_ACCESS_KEY": st.session_state.get("aws_secret_access_key", ""),
                "AWS_DEFAULT_REGION": st.session_state.get("aws_default_region", "us-east-1"),
            }
        
        available_regions = discover_enabled_regions(aws_credentials, aws_auth_method)
        
        if not available_regions:
            available_regions = ["us-east-1"]  # Fallback
    except Exception:
        available_regions = ["us-east-1"]  # Fallback
        _get_region_name = lambda r: r  # Fallback function
    
    # Region selection mode
    if allow_multi_region:
        # Get current scan mode and validate it
        valid_modes = ["auto", "single", "multi"]
        current_mode = st.session_state.get("scan_mode", "auto")
        # Ensure current_mode is valid, default to "auto" if not
        if current_mode not in valid_modes:
            current_mode = "auto"
            st.session_state["scan_mode"] = "auto"
        
        scan_mode = st.radio(
            "🔍 Scan Mode",
            options=valid_modes,
            format_func=lambda x: {
                "auto": "🌍 Auto: All enabled regions",
                "single": "📍 Single: Choose one region",
                "multi": "📍📍 Multiple: Choose specific regions"
            }.get(x, x),
            index=valid_modes.index(current_mode),
            horizontal=True,
            key="scan_mode_radio"
        )
        st.session_state["scan_mode"] = scan_mode
    else:
        scan_mode = "single"
        st.session_state["scan_mode"] = "single"
    
    # Region selection based on mode
    if scan_mode == "auto":
        st.info(f"🌍 Will scan all {len(available_regions)} enabled regions automatically")
        return None  # None signals auto-discover
    
    elif scan_mode == "single":
        # Single region selector
        current_region = st.session_state.get("scan_regions", ["us-east-1"])[0] if st.session_state.get("scan_regions") else "us-east-1"
        
        region_options = {_get_region_name(r): r for r in available_regions}
        
        selected_display = st.selectbox(
            "📍 Select Region",
            options=list(region_options.keys()),
            index=list(region_options.values()).index(current_region) if current_region in region_options.values() else 0,
            key="single_region_select"
        )
        
        selected_region = region_options[selected_display]
        st.session_state["scan_regions"] = [selected_region]
        return [selected_region]
    
    else:  # multi
        # Multi-region selector
        current_selected = st.session_state.get("scan_regions", ["us-east-1"])
        
        region_options = {_get_region_name(r): r for r in available_regions}
        
        selected_displays = st.multiselect(
            "📍📍 Select Regions (can choose multiple)",
            options=list(region_options.keys()),
            default=[_get_region_name(r) for r in current_selected if r in region_options.values()],
            key="multi_region_select"
        )
        
        selected_regions = [region_options[d] for d in selected_displays]
        
        if not selected_regions:
            st.warning("⚠️ Please select at least one region")
            selected_regions = ["us-east-1"]  # Fallback
        
        st.session_state["scan_regions"] = selected_regions
        return selected_regions


# Helper function for backward compatibility
def get_region_display_name(region: str) -> str:
    """Get human-readable name for a region."""
    try:
        from core.services.region_service import get_region_display_name as _get_name
        return _get_name(region)
    except:
        return region

