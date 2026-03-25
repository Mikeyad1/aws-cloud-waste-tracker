"""
AWS credentials management component - Clean and simple.
Handles session-only AWS credential configuration with a streamlined UI.
"""

import streamlit as st
import os
from .settings_config import SettingsManager


def render_clean_credentials_form(settings_manager: SettingsManager) -> bool:
    """Render a clean, simple role-based credentials form.
    
    Uses environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) as base credentials
    to assume an IAM role.
    
    Returns:
        True if credentials were successfully applied, False otherwise
    """
    cfg = settings_manager.load_settings()
    
    # Check if base credentials are in environment
    base_ak = os.getenv("AWS_ACCESS_KEY_ID")
    base_sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not base_ak or not base_sk:
        st.warning("⚠️ **Base credentials not found in environment variables.**\n\nPlease set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment before using role assumption.")
        st.caption("Need help? Go to the **Setup** page for a step-by-step AWS role guide and example policies.")
    
    # Create a simple form for role assumption - GLOBAL / REGIONAL scan uses same role
    with st.form("aws_credentials_form", clear_on_submit=False):
        st.markdown("**Enter the IAM role details**")
        st.caption("Use the role you created in the AWS console. All scans will assume this role to read resources.")
        role_arn = st.text_input(
            "**Role ARN** *",
            value=st.session_state.get("aws_role_arn", ""),
            placeholder="arn:aws:iam::123456789012:role/CloudWasteTrackerFullScanRole",
            help="Full ARN of the IAM role. Example: arn:aws:iam::123456789012:role/CloudWasteTrackerFullScanRole"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            external_id = st.text_input(
                "**External ID** *",
                value=st.session_state.get("aws_external_id", ""),
                placeholder="e.g. cwt-prod-1234",
                type="password",
                help="External ID required by the role's trust policy for enhanced security"
            )
        
        with col2:
            session_name = st.text_input(
                "**Session Name** *(optional)*",
                value=st.session_state.get("aws_role_session_name", "CloudWasteTracker"),
                placeholder="CloudWasteTracker",
                help="Name for the assumed role session (default: CloudWasteTracker)"
            )
        
        # Apply / Clear as a control group
        col1, col2 = st.columns([3, 1])
        with col1:
            apply_button = st.form_submit_button(
                "Apply role",
                type="primary",
                use_container_width=True,
                help="Save these role settings for this session and test that we can assume it."
            )
        with col2:
            clear_button = st.form_submit_button(
                "Clear",
                type="secondary",
                use_container_width=True,
                help="Remove the role from this session and fall back to environment credentials."
            )
    
    # Handle form submission
    if apply_button:
        # Validate required fields
        role_arn = role_arn.strip()
        external_id = external_id.strip()
        session_name = session_name.strip() or "CloudWasteTracker"
        
        # Check base credentials first
        if not base_ak or not base_sk:
            st.error("❌ **Base credentials missing.** Please set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment variables.")
            return False
        
        if not role_arn:
            st.warning("⚠️ Please provide a Role ARN in the format `arn:aws:iam::123456789012:role/RoleName`.")
            return False
        
        if not external_id:
            st.warning("⚠️ **External ID is required.** Use the same External ID you configured on the role's trust policy.")
            return False
        
        # Validate role ARN format (basic check)
        if not role_arn.startswith("arn:aws:iam::"):
            st.warning("⚠️ Role ARN format appears incorrect. It should start with `arn:aws:iam::`.")
        
        # Store in session state (no region - global scan)
        st.session_state["aws_override_enabled"] = True
        st.session_state["aws_role_arn"] = role_arn
        st.session_state["aws_external_id"] = external_id
        st.session_state["aws_role_session_name"] = session_name
        st.session_state["aws_auth_method"] = "role"
        st.session_state["_credentials_just_applied"] = True
        
        return True  # Successfully applied
    
    if clear_button:
        # Clear credentials
        st.session_state["aws_override_enabled"] = False
        st.session_state["aws_role_arn"] = ""
        st.session_state["aws_external_id"] = ""
        st.session_state["aws_role_session_name"] = "CloudWasteTracker"
        st.session_state.pop("aws_connection_verify", None)
        st.info("ℹ️ Role cleared. Using environment variables directly.")
        return False
    
    return False  # No action taken


# Keep the old function name for backward compatibility, but make it use the clean form
def render_aws_credentials_section(settings_manager: SettingsManager) -> None:
    """Legacy function - redirects to clean form."""
    render_clean_credentials_form(settings_manager)


def render_user_credentials_form(use_override: bool) -> None:
    """Legacy function - kept for backward compatibility."""
    # This is no longer used, but kept for compatibility
    pass
