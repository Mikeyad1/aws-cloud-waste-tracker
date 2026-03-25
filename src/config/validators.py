"""
Configuration validation for Cloud Waste Tracker
"""

import os
from typing import Dict, List, Optional, Any
from ..core.exceptions import ConfigurationError, ValidationError
from ..core.validators import ConfigValidator


class AppConfigValidator:
    """Application configuration validation"""
    
    @staticmethod
    def validate_environment() -> Dict[str, Any]:
        """Validate the application environment configuration"""
        try:
            app_env = os.getenv("APP_ENV", "development").strip().lower()
            
            if app_env not in ["development", "staging", "production"]:
                raise ConfigurationError(
                    f"Invalid APP_ENV: {app_env}. Must be 'development', 'staging', or 'production'"
                )
            
            return {
                "APP_ENV": app_env,
                "DEBUG": app_env == "development"
            }
            
        except Exception as e:
            raise ConfigurationError(f"Environment validation failed: {e}")
    
    @staticmethod
    def validate_database_config() -> Dict[str, str]:
        """Validate database configuration"""
        try:
            database_url = os.getenv("DATABASE_URL")
            
            if not database_url:
                raise ConfigurationError("DATABASE_URL environment variable is required")
            
            # Validate database URL format
            validated_url = ConfigValidator.validate_database_url(database_url)
            
            return {
                "DATABASE_URL": validated_url
            }
            
        except Exception as e:
            raise ConfigurationError(f"Database configuration validation failed: {e}")
    
    @staticmethod
    def validate_aws_config() -> Dict[str, str]:
        """Validate AWS configuration"""
        try:
            # Validate AWS credentials
            aws_credentials = ConfigValidator.validate_aws_credentials()
            
            # Validate AWS region
            aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            from ..core.validators import InputValidator
            validated_region = InputValidator.validate_aws_region(aws_region)
            
            return {
                **aws_credentials,
                "AWS_DEFAULT_REGION": validated_region
            }
            
        except Exception as e:
            raise ConfigurationError(f"AWS configuration validation failed: {e}")
    
    @staticmethod
    def validate_feature_flags() -> Dict[str, bool]:
        """Validate feature flags configuration"""
        try:
            # Default feature flags
            default_flags = {
                "recent_scans_table": True,
                "advanced_filters": True,
                "api_endpoints": False,
                "debug_mode": False
            }
            
            # Override with environment variables if present
            feature_flags = {}
            for flag_name in default_flags.keys():
                env_var = f"FEATURE_{flag_name.upper()}"
                env_value = os.getenv(env_var)
                
                if env_value is not None:
                    # Convert string to boolean
                    if env_value.lower() in ["true", "1", "yes", "on"]:
                        feature_flags[flag_name] = True
                    elif env_value.lower() in ["false", "0", "no", "off"]:
                        feature_flags[flag_name] = False
                    else:
                        raise ConfigurationError(
                            f"Invalid feature flag value for {flag_name}: {env_value}. "
                            "Must be 'true' or 'false'"
                        )
                else:
                    feature_flags[flag_name] = default_flags[flag_name]
            
            return feature_flags
            
        except Exception as e:
            raise ConfigurationError(f"Feature flags validation failed: {e}")
    
    @staticmethod
    def validate_all_config() -> Dict[str, Any]:
        """Validate all application configuration"""
        try:
            config = {}
            
            # Validate each configuration section
            config.update(AppConfigValidator.validate_environment())
            config.update(AppConfigValidator.validate_database_config())
            config.update(AppConfigValidator.validate_aws_config())
            config["FEATURES"] = AppConfigValidator.validate_feature_flags()
            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    @staticmethod
    def validate_required_env_vars() -> List[str]:
        """Get list of required environment variables"""
        return [
            "DATABASE_URL",
            "AWS_ACCESS_KEY_ID",  # or AWS_ROLE_ARN for role-based auth
            "AWS_SECRET_ACCESS_KEY"  # or AWS_ROLE_ARN for role-based auth
        ]
    
    @staticmethod
    def check_optional_env_vars() -> Dict[str, Optional[str]]:
        """Check optional environment variables and return their values"""
        optional_vars = {
            "APP_ENV": "development",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ROLE_ARN": None,
            "AWS_EXTERNAL_ID": None,
            "AWS_ROLE_SESSION_NAME": "CloudWasteTracker",
            "PYTHON_VERSION": "3.11.9"
        }
        
        result = {}
        for var, default in optional_vars.items():
            result[var] = os.getenv(var, default)
        
        return result
