"""
Input validation for Cloud Waste Tracker
"""

import re
from typing import Any, Dict, List, Optional
from .exceptions import ValidationError


class InputValidator:
    """Input validation utilities"""
    
    # AWS region pattern
    AWS_REGION_PATTERN = re.compile(r'^[a-z]{2}-[a-z]+-\d+$')
    
    # AWS resource ID patterns
    EC2_INSTANCE_PATTERN = re.compile(r'^i-[0-9a-f]{8,17}$')
    
    @staticmethod
    def validate_aws_region(region: str) -> str:
        """Validate AWS region format"""
        if not region:
            raise ValidationError("AWS region cannot be empty")
        
        if not isinstance(region, str):
            raise ValidationError("AWS region must be a string")
        
        region = region.strip().lower()
        
        if not InputValidator.AWS_REGION_PATTERN.match(region):
            raise ValidationError(
                f"Invalid AWS region format: {region}. "
                "Expected format: us-east-1, eu-west-1, etc."
            )
        
        return region
    
    @staticmethod
    def validate_ec2_instance_id(instance_id: str) -> str:
        """Validate EC2 instance ID format"""
        if not instance_id:
            raise ValidationError("EC2 instance ID cannot be empty")
        
        if not isinstance(instance_id, str):
            raise ValidationError("EC2 instance ID must be a string")
        
        instance_id = instance_id.strip()
        
        if not InputValidator.EC2_INSTANCE_PATTERN.match(instance_id):
            raise ValidationError(
                f"Invalid EC2 instance ID format: {instance_id}. "
                "Expected format: i-1234567890abcdef0"
            )
        
        return instance_id
    
    @staticmethod
    def validate_positive_number(value: Any, field_name: str) -> float:
        """Validate that a value is a positive number"""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a number")
        
        if num_value < 0:
            raise ValidationError(f"{field_name} must be positive")
        
        return num_value
    
    @staticmethod
    def validate_string_not_empty(value: Any, field_name: str) -> str:
        """Validate that a string is not empty"""
        if not value:
            raise ValidationError(f"{field_name} cannot be empty")
        
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        value = value.strip()
        if not value:
            raise ValidationError(f"{field_name} cannot be empty or whitespace")
        
        return value
    
    @staticmethod
    def validate_scan_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scan parameters"""
        validated = {}
        
        # Validate region
        if 'region' in params:
            validated['region'] = InputValidator.validate_aws_region(params['region'])
        
        # Validate scan type
        if 'scan_type' in params:
            scan_type = params['scan_type']
            if scan_type not in ['ec2']:
                raise ValidationError(
                    f"Invalid scan type: {scan_type}. Must be 'ec2'"
                )
            validated['scan_type'] = scan_type
        
        # Validate save_to_db
        if 'save_to_db' in params:
            save_to_db = params['save_to_db']
            if not isinstance(save_to_db, bool):
                raise ValidationError("save_to_db must be a boolean")
            validated['save_to_db'] = save_to_db
        
        return validated


class ConfigValidator:
    """Configuration validation utilities"""
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> Dict[str, str]:
        """Validate that required environment variables are present"""
        import os
        missing_vars = []
        validated_vars = {}
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            else:
                validated_vars[var] = value
        
        if missing_vars:
            raise ValidationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        return validated_vars
    
    @staticmethod
    def validate_database_url(database_url: str) -> str:
        """Validate database URL format"""
        if not database_url:
            raise ValidationError("Database URL cannot be empty")
        
        if not isinstance(database_url, str):
            raise ValidationError("Database URL must be a string")
        
        database_url = database_url.strip()
        
        # Check for valid database URL patterns
        valid_schemes = ['sqlite:///', 'postgresql://', 'mysql://']
        if not any(database_url.startswith(scheme) for scheme in valid_schemes):
            raise ValidationError(
                f"Invalid database URL scheme. Must start with: {', '.join(valid_schemes)}"
            )
        
        return database_url
    
    @staticmethod
    def validate_aws_credentials() -> Dict[str, str]:
        """Validate AWS credentials are properly configured"""
        import os
        
        # Check for role-based credentials
        role_arn = os.getenv('AWS_ROLE_ARN')
        if role_arn:
            # Role-based authentication
            required_vars = ['AWS_ROLE_ARN']
            optional_vars = ['AWS_EXTERNAL_ID', 'AWS_ROLE_SESSION_NAME']
            
            credentials = {}
            for var in required_vars:
                value = os.getenv(var)
                if not value:
                    raise ValidationError(f"Missing required AWS role variable: {var}")
                credentials[var] = value
            
            for var in optional_vars:
                value = os.getenv(var)
                if value:
                    credentials[var] = value
            
            return credentials
        
        # Check for user-based credentials
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if not access_key or not secret_key:
            raise ValidationError(
                "AWS credentials not found. Either set AWS_ROLE_ARN for role-based auth "
                "or AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY for user-based auth"
            )
        
        return {
            'AWS_ACCESS_KEY_ID': access_key,
            'AWS_SECRET_ACCESS_KEY': secret_key,
            'AWS_SESSION_TOKEN': os.getenv('AWS_SESSION_TOKEN', '')
        }
