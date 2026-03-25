"""
Core module for Cloud Waste Tracker
Contains business logic, error handling, logging, and validation
"""

from .exceptions import (
    CloudWasteError,
    ScanError,
    DatabaseError,
    ConfigurationError,
    AWSCredentialsError,
    ValidationError,
    ServiceUnavailableError
)

from .logging import CloudWasteLogger, logger

from .validators import InputValidator, ConfigValidator

__all__ = [
    # Exceptions
    "CloudWasteError",
    "ScanError", 
    "DatabaseError",
    "ConfigurationError",
    "AWSCredentialsError",
    "ValidationError",
    "ServiceUnavailableError",
    
    # Logging
    "CloudWasteLogger",
    "logger",
    
    # Validators
    "InputValidator",
    "ConfigValidator"
]