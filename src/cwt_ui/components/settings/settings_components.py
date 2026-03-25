"""
Reusable UI components for the Settings page.
This module contains all the beautiful UI components used across different settings tabs.
"""

import streamlit as st
from typing import Dict, Any, Optional


def render_settings_css() -> None:
    """Render the beautiful CSS styling for the Settings page."""
    st.markdown("""
    <style>
        .main .block-container {
            padding-left: 1rem;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .settings-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .settings-header h1 {
            color: white;
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }
        .settings-header p {
            color: rgba(255,255,255,0.9);
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
        }
        .settings-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
            margin-bottom: 1rem;
            transition: transform 0.2s ease;
        }
        .settings-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        }
        .section-header {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0 1rem 0;
            border-left: 4px solid #667eea;
            font-weight: 600;
            color: #495057;
        }
        .info-card {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(52,152,219,0.3);
        }
        .warning-card {
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(243,156,18,0.3);
        }
        .success-card {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(46,204,113,0.3);
        }
        .table-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            padding: 1rem;
            margin-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


def render_settings_header(title: str, subtitle: str) -> None:
    """Render the beautiful settings page header."""
    st.markdown(f"""
    <div class="settings-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_info_card(title: str, content: str, icon: str = "ℹ️") -> None:
    """Render a beautiful info card."""
    st.markdown(f"""
    <div class="info-card">
        <h4 style="margin: 0; color: white;">{icon} {title}</h4>
        <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.9);">{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_warning_card(title: str, content: str, icon: str = "⚠️") -> None:
    """Render a beautiful warning card."""
    st.markdown(f"""
    <div class="warning-card">
        <h4 style="margin: 0; color: white;">{icon} {title}</h4>
        <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.9);">{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_success_card(title: str, content: str, icon: str = "✅") -> None:
    """Render a beautiful success card."""
    st.markdown(f"""
    <div class="success-card">
        <h4 style="margin: 0; color: white;">{icon} {title}</h4>
        <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.9);">{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, icon: str = "") -> None:
    """Render a beautiful section header."""
    st.markdown(f'<div class="section-header">{icon} {title}</div>', unsafe_allow_html=True)


def render_settings_card(title: str, description: str) -> None:
    """Render a beautiful settings card container."""
    st.markdown(f"""
    <div class="settings-card">
        <h4 style="margin: 0 0 1rem 0; color: #495057;">{title}</h4>
        <p style="margin: 0 0 1.5rem 0; color: #6c757d;">{description}</p>
    """, unsafe_allow_html=True)


def close_settings_card() -> None:
    """Close the settings card container."""
    st.markdown('</div>', unsafe_allow_html=True)


def render_form_field_with_caption(field_type: str, label: str, **kwargs) -> Any:
    """Render a form field with caption in a consistent style."""
    if field_type == "text_input":
        return st.text_input(label, **kwargs)
    elif field_type == "number_input":
        return st.number_input(label, **kwargs)
    elif field_type == "selectbox":
        return st.selectbox(label, **kwargs)
    elif field_type == "checkbox":
        return st.checkbox(label, **kwargs)
    elif field_type == "time_input":
        return st.time_input(label, **kwargs)
    else:
        raise ValueError(f"Unknown field type: {field_type}")


def render_status_card(credential_type: str, is_active: bool) -> None:
    """Render the AWS credentials status card."""
    if is_active:
        render_success_card(
            "Session Credentials Active",
            f"Using session-specific AWS {credential_type} credentials for live scans."
        )
    else:
        render_info_card(
            "Using Environment Credentials",
            "Using AWS credentials from environment variables."
        )
