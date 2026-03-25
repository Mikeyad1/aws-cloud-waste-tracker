"""
Beautiful UI Component Library for Cloud Waste Tracker.
Professional, modern components that make Streamlit look stunning.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
import base64


def load_css_framework():
    """Load the beautiful CSS framework for the entire app."""
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Root Variables */
        :root {
            --primary-color: #667eea;
            --primary-dark: #5a67d8;
            --secondary-color: #764ba2;
            --success-color: #2ecc71;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --info-color: #3498db;
            --light-color: #f8f9fa;
            --dark-color: #2c3e50;
            --white: #ffffff;
            --gray-100: #f8f9fa;
            --gray-200: #e9ecef;
            --gray-300: #dee2e6;
            --gray-400: #ced4da;
            --gray-500: #adb5bd;
            --gray-600: #6c757d;
            --gray-700: #495057;
            --gray-800: #343a40;
            --gray-900: #212529;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
            --shadow-xl: 0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04);
            --border-radius: 12px;
            --border-radius-sm: 8px;
            --border-radius-lg: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Global Styles */
        .main .block-container {
            padding: 2rem 1rem;
            max-width: 1200px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Beautiful Headers */
        .beautiful-header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            padding: 3rem 2rem;
            border-radius: var(--border-radius-lg);
            margin-bottom: 2rem;
            color: var(--white);
            text-align: center;
            box-shadow: var(--shadow-xl);
            position: relative;
            overflow: hidden;
        }
        
        .beautiful-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="white" opacity="0.1"/><circle cx="75" cy="75" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="10" r="0.5" fill="white" opacity="0.1"/><circle cx="10" cy="60" r="0.5" fill="white" opacity="0.1"/><circle cx="90" cy="40" r="0.5" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }
        
        .beautiful-header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin: 0;
            position: relative;
            z-index: 1;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .beautiful-header p {
            font-size: 1.2rem;
            margin: 1rem 0 0 0;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        /* Beautiful Cards */
        .beautiful-card {
            background: var(--white);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-md);
            padding: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--gray-200);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }
        
        .beautiful-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }
        
        .beautiful-card-header {
            background: linear-gradient(135deg, var(--gray-100) 0%, var(--gray-200) 100%);
            padding: 1.5rem;
            margin: -2rem -2rem 2rem -2rem;
            border-bottom: 1px solid var(--gray-200);
            border-radius: var(--border-radius) var(--border-radius) 0 0;
        }
        
        .beautiful-card-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--gray-800);
            margin: 0;
        }
        
        .beautiful-card-subtitle {
            font-size: 1rem;
            color: var(--gray-600);
            margin: 0.5rem 0 0 0;
        }
        
        /* Beautiful Metrics */
        .beautiful-metric {
            background: var(--white);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            box-shadow: var(--shadow-sm);
            border-left: 4px solid var(--primary-color);
            transition: var(--transition);
        }
        
        .beautiful-metric:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .beautiful-metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin: 0;
            line-height: 1;
        }
        
        .beautiful-metric-label {
            font-size: 0.9rem;
            color: var(--gray-600);
            margin: 0.5rem 0 0 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .beautiful-metric-change {
            font-size: 0.8rem;
            margin-top: 0.5rem;
            padding: 0.25rem 0.5rem;
            border-radius: var(--border-radius-sm);
            font-weight: 500;
        }
        
        .beautiful-metric-change.positive {
            background: rgba(46, 204, 113, 0.1);
            color: var(--success-color);
        }
        
        .beautiful-metric-change.negative {
            background: rgba(231, 76, 60, 0.1);
            color: var(--danger-color);
        }
        
        /* Beautiful Buttons */
        .beautiful-button {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: var(--white);
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: var(--border-radius-sm);
            font-weight: 500;
            font-size: 0.9rem;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: var(--shadow-sm);
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        
        .beautiful-button:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
        }
        
        .beautiful-button.secondary {
            background: linear-gradient(135deg, var(--gray-600) 0%, var(--gray-700) 100%);
        }
        
        .beautiful-button.success {
            background: linear-gradient(135deg, var(--success-color) 0%, #27ae60 100%);
        }
        
        .beautiful-button.warning {
            background: linear-gradient(135deg, var(--warning-color) 0%, #e67e22 100%);
        }
        
        .beautiful-button.danger {
            background: linear-gradient(135deg, var(--danger-color) 0%, #c0392b 100%);
        }
        
        /* Beautiful Alerts */
        .beautiful-alert {
            padding: 1rem 1.5rem;
            border-radius: var(--border-radius);
            margin: 1rem 0;
            border-left: 4px solid;
            box-shadow: var(--shadow-sm);
        }
        
        .beautiful-alert.success {
            background: rgba(46, 204, 113, 0.1);
            border-left-color: var(--success-color);
            color: #155724;
        }
        
        .beautiful-alert.warning {
            background: rgba(243, 156, 18, 0.1);
            border-left-color: var(--warning-color);
            color: #856404;
        }
        
        .beautiful-alert.danger {
            background: rgba(231, 76, 60, 0.1);
            border-left-color: var(--danger-color);
            color: #721c24;
        }
        
        .beautiful-alert.info {
            background: rgba(52, 152, 219, 0.1);
            border-left-color: var(--info-color);
            color: #0c5460;
        }
        
        /* Beautiful Tables */
        .beautiful-table {
            background: var(--white);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            margin: 1rem 0;
        }
        
        .beautiful-table table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .beautiful-table th {
            background: linear-gradient(135deg, var(--gray-100) 0%, var(--gray-200) 100%);
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--gray-800);
            border-bottom: 2px solid var(--gray-200);
        }
        
        .beautiful-table td {
            padding: 1rem;
            border-bottom: 1px solid var(--gray-200);
            color: var(--gray-700);
        }
        
        .beautiful-table tr:hover {
            background: var(--gray-100);
        }
        
        /* Beautiful Tabs */
        .beautiful-tabs {
            background: var(--white);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
        }
        
        .beautiful-tab-content {
            padding: 2rem;
        }
        
        /* Beautiful Progress Bars */
        .beautiful-progress {
            background: var(--gray-200);
            border-radius: var(--border-radius-sm);
            height: 8px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        
        .beautiful-progress-bar {
            height: 100%;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            border-radius: var(--border-radius-sm);
            transition: width 0.6s ease;
        }
        
        /* Beautiful Badges */
        .beautiful-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: var(--border-radius-sm);
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .beautiful-badge.success {
            background: rgba(46, 204, 113, 0.1);
            color: var(--success-color);
        }
        
        .beautiful-badge.warning {
            background: rgba(243, 156, 18, 0.1);
            color: var(--warning-color);
        }
        
        .beautiful-badge.danger {
            background: rgba(231, 76, 60, 0.1);
            color: var(--danger-color);
        }
        
        .beautiful-badge.info {
            background: rgba(52, 152, 219, 0.1);
            color: var(--info-color);
        }
        
        /* Beautiful Loading Spinner */
        .beautiful-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid var(--gray-200);
            border-radius: 50%;
            border-top-color: var(--primary-color);
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Settings-specific styles */
        .section-header {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0 1rem 0;
            border-left: 4px solid #667eea;
            font-weight: 600;
            color: #495057;
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
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .main .block-container {
                padding: 1rem 0.5rem;
            }
            
            .beautiful-header {
                padding: 2rem 1rem;
            }
            
            .beautiful-header h1 {
                font-size: 2rem;
            }
            
            .beautiful-card {
                padding: 1.5rem;
            }
            
            .beautiful-metric-value {
                font-size: 2rem;
            }
        }
        
        /* Dark Mode Support */
        @media (prefers-color-scheme: dark) {
            :root {
                --white: #1a1a1a;
                --gray-100: #2d2d2d;
                --gray-200: #3d3d3d;
                --gray-300: #4d4d4d;
                --gray-400: #5d5d5d;
                --gray-500: #6d6d6d;
                --gray-600: #7d7d7d;
                --gray-700: #8d8d8d;
                --gray-800: #9d9d9d;
                --gray-900: #adadad;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def beautiful_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render a beautiful page header with gradient background."""
    icon_html = f"<span style='font-size: 2rem; margin-right: 1rem;'>{icon}</span>" if icon else ""
    st.markdown(f"""
    <div class="beautiful-header">
        {icon_html}
        <h1>{title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def beautiful_card(title: str, subtitle: str = "", content: str = "") -> None:
    """Render a beautiful card component."""
    st.markdown(f"""
    <div class="beautiful-card">
        <div class="beautiful-card-header">
            <h3 class="beautiful-card-title">{title}</h3>
            {f'<p class="beautiful-card-subtitle">{subtitle}</p>' if subtitle else ''}
        </div>
        {f'<div>{content}</div>' if content else ''}
    </div>
    """, unsafe_allow_html=True)


def beautiful_metric(value: str, label: str, change: str = "", change_type: str = "positive") -> None:
    """Render a beautiful metric component."""
    change_html = f'<div class="beautiful-metric-change {change_type}">{change}</div>' if change else ""
    st.markdown(f"""
    <div class="beautiful-metric">
        <div class="beautiful-metric-value">{value}</div>
        <div class="beautiful-metric-label">{label}</div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def beautiful_alert(message: str, alert_type: str = "info", icon: str = "") -> None:
    """Render a beautiful alert component."""
    icon_html = f"<span style='margin-right: 0.5rem;'>{icon}</span>" if icon else ""
    st.markdown(f"""
    <div class="beautiful-alert {alert_type}">
        {icon_html}{message}
    </div>
    """, unsafe_allow_html=True)


def beautiful_button(text: str, button_type: str = "primary", icon: str = "") -> bool:
    """Render a beautiful button component."""
    icon_html = f"<span style='margin-right: 0.5rem;'>{icon}</span>" if icon else ""
    return st.button(f"{icon_html}{text}", key=f"btn_{text}_{button_type}")


def beautiful_badge(text: str, badge_type: str = "info") -> None:
    """Render a beautiful badge component."""
    st.markdown(f'<span class="beautiful-badge {badge_type}">{text}</span>', unsafe_allow_html=True)


def beautiful_progress(percentage: float, label: str = "") -> None:
    """Render a beautiful progress bar."""
    label_html = f'<div style="margin-bottom: 0.5rem; font-weight: 500; color: var(--gray-700);">{label}</div>' if label else ""
    st.markdown(f"""
    <div>
        {label_html}
        <div class="beautiful-progress">
            <div class="beautiful-progress-bar" style="width: {percentage}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def beautiful_spinner(text: str = "Loading...") -> None:
    """Render a beautiful loading spinner."""
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: center; padding: 2rem;">
        <div class="beautiful-spinner"></div>
        <span style="margin-left: 1rem; color: var(--gray-600);">{text}</span>
    </div>
    """, unsafe_allow_html=True)


# Settings-specific components
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