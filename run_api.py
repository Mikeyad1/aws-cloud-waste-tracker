#!/usr/bin/env python3
"""
Run the FastAPI server for Cloud Waste Tracker API
Usage: python run_api.py
"""

import sys
import os
from pathlib import Path

# Load .env file first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Check if API endpoints are enabled
from config.factory import settings

if not settings.FEATURES.get("api_endpoints", False):
    print("❌ API endpoints are disabled.")
    print("   To enable: set FEATURE_API_ENDPOINTS=true in your .env file")
    sys.exit(1)

print("🚀 Starting Cloud Waste Tracker API server...")
print(f"🔧 Environment: {settings.APP_ENV}")
print(f"🔧 Debug mode: {settings.DEBUG}")

if __name__ == "__main__":
    import uvicorn
    
    # Import the FastAPI app
    from api.main import app
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
