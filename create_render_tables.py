#!/usr/bin/env python3
"""
Create database tables directly on Render PostgreSQL
Usage: python create_render_tables.py
"""

import os
import sys
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Use Render PostgreSQL URL from environment.
# Prefer `DATABASE_URL` to match the app configuration, but also allow
# `RENDER_DATABASE_URL` for local/legacy usage.
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("RENDER_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Missing required database connection URL. Please set `DATABASE_URL` "
        "(or `RENDER_DATABASE_URL`) in your environment before running this script."
    )

try:
    from sqlalchemy import create_engine
    from db.models import Base
    
    print("🔗 Connecting to Render PostgreSQL...")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
    print("📋 Creating database tables...")
    Base.metadata.create_all(engine)
    
    print("✅ Database tables created successfully on Render!")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📊 Created tables: {tables}")
    
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    sys.exit(1)
