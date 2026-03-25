"""
FastAPI application for Cloud Waste Tracker API
Future endpoint for mobile apps, integrations, and webhooks
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import pandas as pd
from datetime import datetime

from config.factory import settings
from core.services.scan_service import scan_service
from db.repo import get_last_scan

# Only create FastAPI app if API endpoints are enabled
if settings.FEATURES.get("api_endpoints", False):
    
    app = FastAPI(
        title="Cloud Waste Tracker API",
        description="REST API for cloud waste scanning and reporting",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None
    )
    
    # CORS middleware for web clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://cloud-waste-tracker.onrender.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.APP_ENV,
            "features": settings.FEATURES
        }
    
    # Get last scan results
    @app.get("/api/v1/scans/latest")
    async def get_latest_scan():
        """Get the most recent scan results"""
        try:
            ec2_df, scanned_at = get_last_scan()
            
            # Convert DataFrames to JSON-serializable format
            ec2_data = ec2_df.to_dict("records") if not ec2_df.empty else []
            
            # Generate summary
            summary = scan_service.get_scan_summary(ec2_df)
            
            return {
                "scanned_at": scanned_at,
                "summary": summary,
                "ec2_findings": ec2_data
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Trigger new scan (if enabled)
    @app.post("/api/v1/scans/trigger")
    async def trigger_scan(region: str = "us-east-1"):
        """Trigger a new scan (development only)"""
        if not settings.DEBUG:
            raise HTTPException(status_code=403, detail="Scan triggering only available in development")
        
        try:
            ec2_df, scanned_at = scan_service.run_full_scan(
                region=region,
                save_to_db=True
            )
            
            summary = scan_service.get_scan_summary(ec2_df)
            
            return {
                "message": "Scan completed successfully",
                "scanned_at": scanned_at,
                "summary": summary
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Get scan history
    @app.get("/api/v1/scans/history")
    async def get_scan_history(limit: int = 10):
        """Get scan history"""
        try:
            from dashboard.recent_scans import get_recent_scans
            recent_scans_df = get_recent_scans(limit=limit)
            return {
                "scans": recent_scans_df.to_dict("records")
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

else:
    # Feature disabled - create minimal app
    app = FastAPI(title="Cloud Waste Tracker API - Disabled")
    
    @app.get("/")
    async def feature_disabled():
        return {"message": "API endpoints are currently disabled"}
