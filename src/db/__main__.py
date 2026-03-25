#!/usr/bin/env python3
"""
Database initialization script
Usage: python -m src.db
"""

from .db import engine
from .models import Base

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully")

if __name__ == "__main__":
    create_tables()
