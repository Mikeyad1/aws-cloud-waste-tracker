#!/usr/bin/env python3
"""
Simple database table creation script for Render deployment
Usage: python create_tables.py
Creates database tables locally (your computer)
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

try:
    from db.db import engine
    from db.models import Base
    from sqlalchemy import text
    
    def create_tables():
        """Create all database tables with clear separators"""
        print("Creating database tables...")
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully")
        
        # Add clear separators in the database for manual editing
        with engine.connect() as conn:
            # Add a comment table to mark safe deletion zones
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS deletion_zones (
                    id INTEGER PRIMARY KEY,
                    zone_name TEXT NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert zone markers
            conn.execute(text("""
                INSERT OR REPLACE INTO deletion_zones (id, zone_name, description) VALUES 
                (1, 'SCAN_DATA_ZONE', 'SAFE TO DELETE: All scan results and findings data'),
                (2, 'TABLE_STRUCTURE_ZONE', 'DO NOT DELETE: Database table definitions')
            """))
            
            conn.commit()
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")
        print("✅ Added deletion zone markers for safe manual cleanup")
    
    if __name__ == "__main__":
        create_tables()
        
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    sys.exit(1)