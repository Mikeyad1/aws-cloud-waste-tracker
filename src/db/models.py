from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# בסיס לכל הטבלאות
class Base(DeclarativeBase):
    pass

# משתמשים (נשאיר לעתיד, אבל לא חובה להשתמש בזה עכשיו)
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False, default="!")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scans: Mapped[list["Scan"]] = relationship(back_populates="user")

# ריצת סריקה אחת
class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String)  # למשל "running", "done", "failed"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(back_populates="scan")

# תוצאה אחת מתוך סריקה
class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"))
    resource_id: Mapped[str] = mapped_column(String)         # instance_id / bucket
    resource_type: Mapped[str] = mapped_column(String)       # "EC2" / "S3"
    region: Mapped[str | None] = mapped_column(String)       # למשל us-east-1
    issue_type: Mapped[str] = mapped_column(String)          # idle server / unused storage
    estimated_saving_usd: Mapped[float] = mapped_column(Numeric(12, 2))
    attributes: Mapped[dict] = mapped_column(JSON, default={})  # כל העמודות הנוספות מה־CSV
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scan: Mapped["Scan"] = relationship(back_populates="findings")
