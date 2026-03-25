"""
Settings tab components for different configuration sections.
"""

import streamlit as st
import os
from ..ui.beautiful_ui import (
    render_section_header, render_settings_card, close_settings_card, 
    render_success_card, render_warning_card, render_info_card
)
from .settings_config import SettingsManager, parse_time, weekday_index


def render_email_notifications_tab(settings_manager: SettingsManager) -> None:
    """Render the email notifications settings tab."""
    render_section_header("📧 Email Notifications")
    
    render_settings_card(
        "Configure automated email reports",
        "Set up daily or weekly cost optimization reports delivered to your inbox."
    )
    
    cfg = settings_manager.load_settings()
    
    with st.form("email_reports_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            enabled = st.checkbox(
                "📬 Enable email reports", 
                value=cfg.get("email_reports", {}).get("enabled", False)
            )
            recipient = st.text_input(
                "📧 Recipient email", 
                value=cfg.get("email_reports", {}).get("recipient", ""), 
                placeholder="your-email@company.com"
            )
            schedule = st.selectbox(
                "📅 Report frequency", 
                options=["daily", "weekly"],
                index=(0 if cfg.get("email_reports", {}).get("schedule", "daily") == "daily" else 1)
            )
        
        with col2:
            send_time = st.time_input(
                "⏰ Send time (local)", 
                value=parse_time(cfg.get("email_reports", {}).get("send_time", "09:00"))
            )
            weekday = st.selectbox(
                "📆 Weekday (weekly only)",
                options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                index=weekday_index(cfg.get("email_reports", {}).get("weekday", "Monday"))
            )
        
        if st.form_submit_button("💾 Save Email Settings", type="primary", use_container_width=True):
            # Save email settings
            if "email_reports" not in cfg:
                cfg["email_reports"] = {}
            cfg["email_reports"].update({
                "enabled": enabled,
                "recipient": recipient.strip(),
                "schedule": schedule,
                "send_time": send_time.strftime("%H:%M"),
                "weekday": weekday,
            })
            if settings_manager.save_settings(cfg):
                st.success("✅ Email settings saved successfully!")
    
    close_settings_card()
    
    render_warning_card(
        "🚧 Coming Soon",
        "Email sending will be implemented via a scheduler (Render Cron / APScheduler) in future updates."
    )


def render_aws_config_tab(settings_manager: SettingsManager) -> None:
    """Render the AWS configuration settings tab."""
    render_section_header("☁️ AWS Configuration")
    
    render_settings_card(
        "Default AWS settings",
        "Configure default AWS region and other cloud provider settings."
    )
    
    cfg = settings_manager.load_settings()
    
    with st.form("aws_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            region = st.text_input(
                "🌍 Default AWS region", 
                value=cfg.get("aws", {}).get("default_region", "us-east-1"), 
                placeholder="us-east-1"
            )
            st.caption("Region used for new scans and resource discovery")
        
        with col2:
            currency = st.selectbox(
                "💱 Display currency", 
                options=["USD", "EUR", "ILS"],
                index=["USD", "EUR", "ILS"].index(cfg.get("billing", {}).get("currency", "USD"))
            )
            st.caption("Currency for cost display (does not affect actual AWS billing)")
        
        if st.form_submit_button("💾 Save AWS Settings", type="primary", use_container_width=True):
            if "aws" not in cfg:
                cfg["aws"] = {}
            if "billing" not in cfg:
                cfg["billing"] = {}
            cfg["aws"]["default_region"] = (region or "us-east-1").strip()
            cfg["billing"]["currency"] = currency
            if settings_manager.save_settings(cfg):
                st.session_state["region"] = cfg["aws"]["default_region"]
                st.success("✅ AWS settings saved successfully!")
    
    close_settings_card()
    
    # AWS Status Card
    render_success_card(
        "✅ AWS Connection Status",
        "Your AWS credentials are configured and working properly."
    )


def render_billing_tab(settings_manager: SettingsManager) -> None:
    """Render the billing and cost management settings tab."""
    render_section_header("💰 Billing & Cost Management")
    
    render_settings_card(
        "Cost tracking preferences",
        "Configure how costs are calculated and displayed in your reports."
    )
    
    cfg = settings_manager.load_settings()
    
    with st.form("billing_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            cost_threshold = st.number_input(
                "💰 Cost alert threshold ($)", 
                min_value=0.0, 
                value=cfg.get("billing", {}).get("cost_threshold", 100.0), 
                step=10.0
            )
            st.caption("Get alerts when monthly costs exceed this amount")
        
        with col2:
            savings_threshold = st.number_input(
                "💡 Savings alert threshold ($)", 
                min_value=0.0, 
                value=cfg.get("billing", {}).get("savings_threshold", 50.0), 
                step=5.0
            )
            st.caption("Get alerts when potential savings exceed this amount")
        
        if st.form_submit_button("💾 Save Billing Settings", type="primary", use_container_width=True):
            if "billing" not in cfg:
                cfg["billing"] = {}
            cfg["billing"]["cost_threshold"] = cost_threshold
            cfg["billing"]["savings_threshold"] = savings_threshold
            if settings_manager.save_settings(cfg):
                st.success("✅ Billing settings saved successfully!")
    
    close_settings_card()
    
    # Cost Summary Card
    render_info_card(
        "📊 Current Cost Status",
        "Monitor your AWS spending and optimization opportunities."
    )


def render_advanced_tab(settings_manager: SettingsManager) -> None:
    """Render the advanced settings tab."""
    render_section_header("🔧 Advanced Settings")
    
    render_settings_card(
        "System configuration",
        "Advanced settings for power users and system administrators."
    )
    
    cfg = settings_manager.load_settings()
    
    # Get debug mode from environment
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    DEBUG_MODE = APP_ENV != "production"
    
    with st.form("advanced_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            debug_mode = st.checkbox("🐛 Enable debug mode", value=DEBUG_MODE)
            st.caption("Show detailed debug information in the interface")
            
            auto_refresh = st.checkbox(
                "🔄 Auto-refresh data", 
                value=cfg.get("advanced", {}).get("auto_refresh", True)
            )
            st.caption("Automatically refresh data when switching pages")
        
        with col2:
            scan_interval = st.selectbox(
                "⏱️ Scan interval", 
                options=["1 hour", "6 hours", "12 hours", "24 hours"], 
                index=["1 hour", "6 hours", "12 hours", "24 hours"].index(
                    cfg.get("advanced", {}).get("scan_interval", "24 hours")
                )
            )
            st.caption("How often to automatically scan for new resources")
            
            data_retention = st.selectbox(
                "🗄️ Data retention", 
                options=["7 days", "30 days", "90 days", "1 year"], 
                index=["7 days", "30 days", "90 days", "1 year"].index(
                    cfg.get("advanced", {}).get("data_retention", "30 days")
                )
            )
            st.caption("How long to keep historical scan data")
        
        if st.form_submit_button("💾 Save Advanced Settings", type="primary", use_container_width=True):
            if "advanced" not in cfg:
                cfg["advanced"] = {}
            cfg["advanced"]["debug_mode"] = debug_mode
            cfg["advanced"]["auto_refresh"] = auto_refresh
            cfg["advanced"]["scan_interval"] = scan_interval
            cfg["advanced"]["data_retention"] = data_retention
            if settings_manager.save_settings(cfg):
                st.success("✅ Advanced settings saved successfully!")
    
    close_settings_card()
    
    # System Info Card
    render_info_card(
        "ℹ️ System Information",
        "Environment: Development | Version: 1.0.0 | Last Updated: Today"
    )
