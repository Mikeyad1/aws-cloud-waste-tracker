"""
Shared CSS styles for all pages.
This reduces line count while keeping the beautiful look.
"""

def load_beautiful_css():
    """Load beautiful CSS that all pages can use."""
    import streamlit as st
    
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
            padding-left: 1rem;
            padding-top: 2rem;
            padding-bottom: 2rem;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Beautiful Headers — compact so hero number and content stay in proportion */
        .beautiful-header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            padding: 1rem 1.5rem;
            border-radius: var(--border-radius);
            margin-bottom: 1rem;
            color: var(--white);
            text-align: center;
            box-shadow: var(--shadow-md);
            position: relative;
            overflow: hidden;
        }
        
        .beautiful-header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0;
            position: relative;
            z-index: 1;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .beautiful-header p {
            font-size: 0.9rem;
            margin: 0.25rem 0 0 0;
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
                padding: 0.75rem 1rem;
            }
            
            .beautiful-header h1 {
                font-size: 1.35rem;
            }
            
            .beautiful-card {
                padding: 1.5rem;
            }
            
            .beautiful-metric-value {
                font-size: 2rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)
























