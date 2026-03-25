from datetime import datetime
from sqlalchemy import select, desc, delete
from .db import get_db
from .models import User, Scan, Finding
import pandas as pd
import json

# Import our new error handling and logging
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.exceptions import DatabaseError, ValidationError
    from core.logging import logger
    from core.validators import InputValidator
except ImportError:
    # Fallback if core modules not available
    class DatabaseError(Exception):
        pass
    class ValidationError(Exception):
        pass
    class InputValidator:
        @staticmethod
        def validate_aws_region(region):
            return region
    class logger:
        @staticmethod
        def log_database_operation(*args, **kwargs):
            pass

def ensure_user(email: str) -> User:
    """יוצר משתמש אם לא קיים ומחזיר אותו"""
    with get_db() as s:
        u = s.scalar(select(User).where(User.email == email))
        if not u:
            u = User(email=email, password_hash="!")
            s.add(u)
            s.flush()
        return u

def start_scan(user_id: int | None = None) -> Scan:
    """פותח סריקה חדשה"""
    with get_db() as s:
        scan = Scan(user_id=user_id, started_at=datetime.utcnow(), status="pending")
        s.add(scan)
        s.flush()
        return scan

def add_finding(scan_id: int, resource_id: str, resource_type: str,
                issue_type: str, estimated_saving_usd: float,
                region: str | None = None, attributes: dict | None = None) -> Finding:
    """מוסיף Finding חדש לסריקה"""
    with get_db() as s:
        f = Finding(
            scan_id=scan_id,
            resource_id=resource_id,
            resource_type=resource_type,
            issue_type=issue_type,
            estimated_saving_usd=estimated_saving_usd,
            region=region,
            attributes=attributes or {},
        )
        s.add(f)
        s.flush()
        return f

def finish_scan(scan_id: int, status: str = "success") -> None:
    """מסיים סריקה ומעדכן סטטוס"""
    with get_db() as s:
        scan = s.get(Scan, scan_id)
        if scan:
            scan.status = status
            scan.finished_at = datetime.utcnow()


def save_scan_results(ec2_df: pd.DataFrame, scanned_at: str) -> None:
    """שמירת תוצאות סריקה למסד הנתונים"""
    try:
        # Validate inputs
        if not isinstance(ec2_df, pd.DataFrame):
            raise ValidationError("ec2_df must be a pandas DataFrame")
        if not scanned_at:
            raise ValidationError("scanned_at cannot be empty")
        
        with get_db() as s:
            # Create a new scan record
            # Parse timestamp - handle both UTC and Israel time formats
            try:
                if "(Israel Time)" in scanned_at:
                    # Remove the suffix and parse as ISO format
                    timestamp_str = scanned_at.replace(" (Israel Time)", "")
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    # Handle UTC format
                    timestamp = datetime.fromisoformat(scanned_at.replace('Z', '+00:00'))
            except ValueError as e:
                raise ValidationError(f"Invalid timestamp format: {scanned_at}. Error: {e}")
            
            scan = Scan(
                user_id=None,  # No user for automated scans
                started_at=timestamp,
                finished_at=datetime.utcnow(),
                status="success"
            )
            s.add(scan)
            s.flush()
            
            # Save EC2 findings
            ec2_count = 0
            if not ec2_df.empty:
                for _, row in ec2_df.iterrows():
                    try:
                        finding = Finding(
                            scan_id=scan.id,
                            resource_id=row.get('instance_id', ''),
                            resource_type='EC2',
                            issue_type=row.get('type', 'idle_instance'),
                            estimated_saving_usd=float(row.get('monthly_cost_usd', 0)),
                            region=row.get('region', ''),
                            attributes=row.to_dict()
                        )
                        s.add(finding)
                        ec2_count += 1
                    except Exception as e:
                        logger.log_database_operation("save_ec2_finding", "findings", False, e)
                        # Continue with other findings even if one fails
            
            # Commit the transaction
            s.commit()
            
            # Log successful operation
            logger.log_database_operation("save_scan_results", "scans", True)
            logger.log_system_event("scan_results_saved", 
                                  scan_id=scan.id, 
                                  ec2_findings=ec2_count)
            
    except ValidationError:
        raise
    except Exception as e:
        logger.log_database_operation("save_scan_results", "scans", False, e)
        raise DatabaseError(f"Failed to save scan results: {e}")


def get_last_scan() -> tuple[pd.DataFrame, str]:
    """קבלת הסריקה האחרונה ממסד הנתונים"""
    try:
        with get_db() as s:
            # Get the most recent scan
            scan = s.scalar(
                select(Scan)
                .where(Scan.status == "success")
                .order_by(desc(Scan.finished_at))
                .limit(1)
            )
            
            if not scan:
                return pd.DataFrame(), ""
            
            # Get findings for this scan
            findings = s.scalars(
                select(Finding)
                .where(Finding.scan_id == scan.id)
            ).all()
            
            # Collect EC2 findings
            ec2_data = []
            
            for finding in findings:
                if finding.resource_type == 'EC2':
                    ec2_data.append(finding.attributes)
            
            # Convert to DataFrame
            ec2_df = pd.DataFrame(ec2_data) if ec2_data else pd.DataFrame()
            
            # Format timestamp - convert UTC to Israel time (UTC+3)
            if scan.finished_at:
                from datetime import timedelta
                israel_time = scan.finished_at + timedelta(hours=3)
                scanned_at = israel_time.isoformat() + " (Israel Time)"
            else:
                scanned_at = ""
            
            return ec2_df, scanned_at
            
    except Exception as e:
        # If database is corrupted or empty, return empty data gracefully
        import os
        if os.getenv("APP_ENV", "development").strip().lower() != "production":
            print(f"🔍 DEBUG: Database error in get_last_scan: {e}")
        return pd.DataFrame(), ""


def clear_all_scans() -> None:
    """Clear all scan data from the database (scans and findings)"""
    try:
        with get_db() as s:
            # Count records before deletion for logging
            from sqlalchemy import func
            findings_count = s.scalar(select(func.count(Finding.id)))
            scans_count = s.scalar(select(func.count(Scan.id)))
            
            # Delete all findings first (due to foreign key constraint)
            s.execute(delete(Finding))
            
            # Delete all scans
            s.execute(delete(Scan))
            
            # Commit the changes
            s.commit()
            
            # Log successful operation
            logger.log_database_operation("clear_all_scans", "scans", True)
            logger.log_system_event("scan_data_cleared", 
                                  deleted_scans=scans_count, 
                                  deleted_findings=findings_count)
            
            print("✅ All scan data cleared successfully")
            
    except Exception as e:
        logger.log_database_operation("clear_all_scans", "scans", False, e)
        import os
        if os.getenv("APP_ENV", "development").strip().lower() != "production":
            print(f"🔍 DEBUG: Error clearing scan data: {e}")
        raise DatabaseError(f"Failed to clear scan data: {e}")
