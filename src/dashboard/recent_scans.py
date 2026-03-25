"""
Recent Scans functionality for Dashboard
"""

import pandas as pd
from datetime import timedelta
from sqlalchemy import select, desc
from db.db import get_db
from db.models import Scan


def get_recent_scans(limit: int = 3) -> pd.DataFrame:
    """
    Get the most recent scans from the database.
    
    Args:
        limit: Number of recent scans to retrieve (default: 3)
        
    Returns:
        DataFrame with columns: scan_time, status
    """
    try:
        with get_db() as s:
            # Get recent scans, prioritizing finished_at over created_at
            scans = s.scalars(
                select(Scan)
                .order_by(desc(Scan.finished_at), desc(Scan.created_at))
                .limit(limit)
            ).all()
            
            scan_data = []
            for scan in scans:
                # Use finished_at if available, otherwise created_at
                timestamp = scan.finished_at or scan.created_at
                
                if timestamp:
                    # Convert UTC to Israel time (UTC+3)
                    israel_time = timestamp + timedelta(hours=3)
                    time_str = israel_time.strftime("%H:%M:%S")
                else:
                    time_str = "—"
                
                scan_data.append({
                    "scan_time": time_str,
                    "status": scan.status or "unknown"
                })
            
            # Fill empty rows if we have fewer than the limit
            while len(scan_data) < limit:
                scan_data.append({
                    "scan_time": "—",
                    "status": "—"
                })
            
            return pd.DataFrame(scan_data)
            
    except Exception as e:
        # If database is corrupted or empty, return empty table gracefully
        import os
        if os.getenv("APP_ENV", "development").strip().lower() != "production":
            print(f"🔍 DEBUG: Database error in get_recent_scans: {e}")
        return pd.DataFrame([{"scan_time": "—", "status": "—"}] * limit)


def render_recent_scans_table(df: pd.DataFrame) -> None:
    """
    Render the recent scans table using Streamlit.
    
    Args:
        df: DataFrame from get_recent_scans()
    """
    import streamlit as st
    
    st.subheader("🕒 Recent Scans")
    
    # Rename columns for display
    display_df = df.copy()
    display_df = display_df.rename(columns={
        "scan_time": "Time",
        "status": "Status"
    })
    
    # Style the table
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "Time": st.column_config.TextColumn(
                "Time",
                help="Scan completion time (Israel time)",
                width="medium"
            ),
            "Status": st.column_config.TextColumn(
                "Status", 
                help="Scan status",
                width="medium"
            )
        }
    )
