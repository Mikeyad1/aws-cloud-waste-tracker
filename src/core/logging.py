"""
Structured logging system for Cloud Waste Tracker
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class CloudWasteLogger:
    """Structured logger for Cloud Waste Tracker operations"""
    
    def __init__(self, name: str = "cloud_waste_tracker"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler if not already present
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _log_structured(self, level: str, message: str, **kwargs):
        """Log structured data with additional context"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        if level.upper() == "ERROR":
            self.logger.error(json.dumps(log_data))
        elif level.upper() == "WARNING":
            self.logger.warning(json.dumps(log_data))
        elif level.upper() == "INFO":
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.debug(json.dumps(log_data))
    
    def log_scan_start(self, region: str, scan_type: str = "full"):
        """Log the start of a scan operation"""
        self._log_structured(
            "INFO",
            f"Scan started for region {region}",
            operation="scan_start",
            region=region,
            scan_type=scan_type
        )
    
    def log_scan_complete(self, region: str, ec2_count: int, 
                         duration_seconds: float, scan_type: str = "ec2"):
        """Log the completion of a scan operation"""
        self._log_structured(
            "INFO",
            f"Scan completed for region {region}",
            operation="scan_complete",
            region=region,
            scan_type=scan_type,
            ec2_findings=ec2_count,
            duration_seconds=duration_seconds
        )
    
    def log_scan_error(self, region: str, error: Exception, scan_type: str = "full"):
        """Log scan errors"""
        self._log_structured(
            "ERROR",
            f"Scan failed for region {region}: {str(error)}",
            operation="scan_error",
            region=region,
            scan_type=scan_type,
            error_type=type(error).__name__,
            error_message=str(error)
        )
    
    def log_database_operation(self, operation: str, table: str, success: bool, 
                              error: Optional[Exception] = None):
        """Log database operations"""
        level = "INFO" if success else "ERROR"
        message = f"Database {operation} on {table} {'succeeded' if success else 'failed'}"
        
        log_data = {
            "operation": f"db_{operation}",
            "table": table,
            "success": success
        }
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        self._log_structured(level, message, **log_data)
    
    def log_aws_operation(self, service: str, operation: str, region: str, 
                         success: bool, error: Optional[Exception] = None):
        """Log AWS operations"""
        level = "INFO" if success else "ERROR"
        message = f"AWS {service}.{operation} in {region} {'succeeded' if success else 'failed'}"
        
        log_data = {
            "operation": f"aws_{service}_{operation}",
            "service": service,
            "aws_operation": operation,
            "region": region,
            "success": success
        }
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        self._log_structured(level, message, **log_data)
    
    def log_user_action(self, action: str, user_id: Optional[str] = None, **kwargs):
        """Log user actions"""
        self._log_structured(
            "INFO",
            f"User action: {action}",
            operation="user_action",
            action=action,
            user_id=user_id,
            **kwargs
        )
    
    def log_system_event(self, event: str, **kwargs):
        """Log system events"""
        self._log_structured(
            "INFO",
            f"System event: {event}",
            operation="system_event",
            event=event,
            **kwargs
        )


# Global logger instance
logger = CloudWasteLogger()
