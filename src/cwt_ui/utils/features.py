"""
Feature flag utilities for UI components
"""

import streamlit as st
from typing import Any


def get_settings():
    """Get settings with fallback for UI context"""
    try:
        from config.factory import settings
        return settings
    except ImportError:
        # Fallback for when config is not available
        import os
        class FallbackSettings:
            FEATURES = {
                "recent_scans_table": True,
                "cost_explorer": True,
                "advanced_filters": False,
                "api_endpoints": False,
            }
            DEBUG = os.getenv("APP_ENV", "development") == "development"
        return FallbackSettings()


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled"""
    settings = get_settings()
    return settings.FEATURES.get(feature_name, False)


def feature_flag(feature_name: str, default_content: Any = None):
    """Decorator/context manager for feature-flagged content"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if is_feature_enabled(feature_name):
                return func(*args, **kwargs)
            elif default_content is not None:
                if callable(default_content):
                    return default_content(*args, **kwargs)
                else:
                    return default_content
            return None
        return wrapper
    return decorator


def show_feature_debug():
    """Show feature flag status in debug mode (development only)"""
    settings = get_settings()
    if settings.DEBUG:
        with st.expander("🚩 Feature Flags (Debug)", expanded=False):
            for feature, enabled in settings.FEATURES.items():
                status = "✅" if enabled else "❌"
                st.write(f"{status} `{feature}`: {enabled}")


@feature_flag("recent_scans_table")
def render_recent_scans():
    """Render recent scans table if feature is enabled"""
    try:
        from dashboard.recent_scans import get_recent_scans, render_recent_scans_table
        recent_scans_df = get_recent_scans()
        render_recent_scans_table(recent_scans_df)
        st.divider()
    except Exception as e:
        if get_settings().DEBUG:
            st.error(f"Recent scans failed: {e}")


@feature_flag("advanced_filters")
def render_advanced_filters():
    """Render advanced filtering options if feature is enabled"""
    with st.expander("🔍 Advanced Filters", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            cost_threshold = st.number_input("Min Monthly Cost ($)", min_value=0.0, value=0.0)
        with col2:
            resource_types = st.multiselect(
                "Resource Types", 
                ["EC2"], 
                default=["EC2"]
            )
        return {"cost_threshold": cost_threshold, "resource_types": resource_types}


@feature_flag("cost_explorer")
def render_cost_breakdown():
    """Render cost breakdown charts if feature is enabled"""
    # Placeholder for future cost visualization
    st.info("💡 Cost Explorer charts coming soon!")
