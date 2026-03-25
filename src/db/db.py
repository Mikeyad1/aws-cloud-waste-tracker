import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# שליפת DATABASE_URL מהסביבה (Render מגדיר אותו)
DATABASE_URL = os.getenv("DATABASE_URL")

# אם אין DATABASE_URL, נשתמש ב-SQLite מקומי לפיתוח
if not DATABASE_URL:
    # Use local SQLite database for development
    DATABASE_URL = "sqlite:///local_dev.db"
    if os.getenv("APP_ENV", "development").strip().lower() != "production":
        print("🔍 DEBUG: Using local SQLite database for development")

# יצירת engine (Postgres או SQLite)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# factory לסשנים
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# context manager לשימוש נוח
@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
