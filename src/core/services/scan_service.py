"""
Scan orchestration service - centralized business logic for running scans
"""

from typing import Tuple, Optional, Mapping, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import time

from ..exceptions import ScanError, DatabaseError, ValidationError
from ..logging import logger
from ..validators import InputValidator

from scanners.ec2_scanner import scan_ec2
from db.repo import save_scan_results


class ScanService:
    """Central service for orchestrating cloud waste scans"""
    
    def __init__(self):
        self.logger = logger
    
    def run_full_scan(
        self, 
        region: str = "us-east-1",
        aws_credentials: Optional[Mapping[str, str]] = None,
        aws_auth_method: str = "user",
        save_to_db: bool = True
    ) -> Tuple[pd.DataFrame, str]:
        """
        Run a complete scan (EC2) and optionally save to database.
        
        Args:
            region: AWS region to scan
            aws_credentials: Optional AWS credentials override
            aws_auth_method: "user" or "role" authentication method
            save_to_db: Whether to save results to database
            
        Returns:
            Tuple of (ec2_df, timestamp)
            
        Raises:
            ValidationError: If input parameters are invalid
            ScanError: If scan operation fails
            DatabaseError: If database save fails
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            region = InputValidator.validate_aws_region(region)
            
            if aws_auth_method not in ["user", "role"]:
                raise ValidationError(f"Invalid auth method: {aws_auth_method}. Must be 'user' or 'role'")
            
            # Log scan start
            self.logger.log_scan_start(region, "ec2")
            
            # Import the existing scan orchestrator
            from cwt_ui.services.scans import run_all_scans
            
            # Run the scans using existing logic
            ec2_df = run_all_scans(
                region=region,
                aws_credentials=aws_credentials,
                aws_auth_method=aws_auth_method
            )
            
            # Generate timestamp in Israel time
            israel_time = datetime.utcnow() + timedelta(hours=3)
            scanned_at = israel_time.replace(microsecond=0).isoformat() + " (Israel Time)"
            
            # Save to database if requested
            if save_to_db:
                try:
                    save_scan_results(ec2_df, scanned_at)
                    self.logger.log_database_operation("save_scan_results", "scans", True)
                except Exception as e:
                    self.logger.log_database_operation("save_scan_results", "scans", False, e)
                    raise DatabaseError(f"Failed to save scan results to database: {e}")
            
            # Log scan completion
            duration = time.time() - start_time
            self.logger.log_scan_complete(
                region, 
                len(ec2_df), 
                duration, 
                "ec2"
            )
            
            return ec2_df, scanned_at
            
        except ValidationError:
            raise
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_scan_error(region, e, "full")
            raise ScanError(f"Scan failed for region {region}: {e}")
    
    def run_ec2_scan(self, region: str = "us-east-1") -> pd.DataFrame:
        """Run EC2-only scan with validation and logging"""
        try:
            region = InputValidator.validate_aws_region(region)
            self.logger.log_scan_start(region, "ec2")
            
            from cwt_ui.services.scans import scan_ec2
            result = scan_ec2(region)
            
            self.logger.log_scan_complete(region, len(result), 0.0, "ec2")
            return result
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.log_scan_error(region, e, "ec2")
            raise ScanError(f"EC2 scan failed for region {region}: {e}")
    
    def get_scan_summary(self, ec2_df: pd.DataFrame) -> dict:
        """Generate scan summary statistics"""
        summary = {
            "ec2_instances": len(ec2_df),
            "total_findings": len(ec2_df),
            "estimated_monthly_waste": 0.0
        }
        
        # Calculate EC2 waste
        if not ec2_df.empty and "monthly_cost_usd" in ec2_df.columns:
            if "recommendation" in ec2_df.columns:
                waste_mask = ~ec2_df["recommendation"].astype(str).str.upper().eq("OK")
                summary["estimated_monthly_waste"] = float(
                    pd.to_numeric(ec2_df.loc[waste_mask, "monthly_cost_usd"], errors="coerce")
                    .fillna(0.0).sum()
                )
        
        return summary
    
    def validate_scan_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scan parameters using the validator"""
        return InputValidator.validate_scan_parameters(params)
    
    def get_scan_history(self, limit: int = 10) -> pd.DataFrame:
        """Get scan history from database"""
        try:
            from db.repo import get_db
            from db.models import Scan
            from sqlalchemy import select, desc
            
            with get_db() as s:
                scans = s.scalars(
                    select(Scan)
                    .order_by(desc(Scan.finished_at))
                    .limit(limit)
                ).all()
                
                scan_data = []
                for scan in scans:
                    scan_data.append({
                        "id": scan.id,
                        "started_at": scan.started_at.isoformat() if scan.started_at else None,
                        "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
                        "status": scan.status,
                        "created_at": scan.created_at.isoformat()
                    })
                
                return pd.DataFrame(scan_data)
                
        except Exception as e:
            self.logger.log_database_operation("get_scan_history", "scans", False, e)
            raise DatabaseError(f"Failed to get scan history: {e}")
    
    def clear_scan_history(self) -> None:
        """Clear all scan history from database"""
        try:
            from db.repo import clear_all_scans
            clear_all_scans()
            self.logger.log_database_operation("clear_all_scans", "scans", True)
            self.logger.log_system_event("scan_history_cleared")
        except Exception as e:
            self.logger.log_database_operation("clear_all_scans", "scans", False, e)
            raise DatabaseError(f"Failed to clear scan history: {e}")


# Global instance for easy access
scan_service = ScanService()
