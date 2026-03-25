"""
Custom exceptions for Cloud Waste Tracker
"""


class CloudWasteError(Exception):
    """Base exception for all Cloud Waste Tracker errors"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ScanError(CloudWasteError):
    """Errors related to scanning operations"""
    pass


class DatabaseError(CloudWasteError):
    """Errors related to database operations"""
    pass


class ConfigurationError(CloudWasteError):
    """Errors related to configuration issues"""
    pass


class AWSCredentialsError(CloudWasteError):
    """Errors related to AWS credentials or permissions"""
    pass


class ValidationError(CloudWasteError):
    """Errors related to input validation"""
    pass


class ServiceUnavailableError(CloudWasteError):
    """Errors when external services are unavailable"""
    pass
