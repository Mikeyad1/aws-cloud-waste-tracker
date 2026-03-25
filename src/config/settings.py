"""
Application configuration and settings
"""

import os
from typing import Dict, Any


class Settings:
    """Application settings with environment-based configuration"""
    
    def __init__(self):
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        # Core settings
        self.APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
        self.DEBUG = self.APP_ENV == "development"
        
        # Database settings
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        if not self.DATABASE_URL:
            if self.APP_ENV == "production":
                raise RuntimeError("DATABASE_URL is required in production")
            else:
                self.DATABASE_URL = "sqlite:///local_dev.db"
        
        # AWS settings
        self.AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Feature flags
        self.FEATURES = self._load_features()
        
        # UI settings
        self.STREAMLIT_THEME = os.getenv("STREAMLIT_THEME_BASE", "dark")
        self.STREAMLIT_HEADLESS = os.getenv("STREAMLIT_SERVER_HEADLESS", "true") == "true"
    
    def _load_features(self) -> Dict[str, bool]:
        """Load feature flags from environment variables"""
        return {
            "recent_scans_table": self._get_feature_flag("FEATURE_RECENT_SCANS", True),
            "cost_explorer": self._get_feature_flag("FEATURE_COST_EXPLORER", True),
            "advanced_filters": self._get_feature_flag("FEATURE_ADVANCED_FILTERS", False),
            "api_endpoints": self._get_feature_flag("FEATURE_API_ENDPOINTS", False),
            "webhook_notifications": self._get_feature_flag("FEATURE_WEBHOOKS", False),
            "multi_account": self._get_feature_flag("FEATURE_MULTI_ACCOUNT", False),
        }
    
    def _get_feature_flag(self, env_var: str, default: bool = False) -> bool:
        """Get feature flag from environment variable"""
        return os.getenv(env_var, str(default)).lower() in ("true", "1", "yes", "on")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.APP_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.APP_ENV == "development"
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "url": self.DATABASE_URL,
            "pool_pre_ping": True,
            "echo": self.DEBUG
        }
    
    def get_aws_config(self) -> Dict[str, str]:
        """Get AWS configuration"""
        config = {
            "region": self.AWS_DEFAULT_REGION
        }
        
        if self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY:
            config.update({
                "access_key_id": self.AWS_ACCESS_KEY_ID,
                "secret_access_key": self.AWS_SECRET_ACCESS_KEY
            })
        
        return config


# Global settings instance
settings = Settings()
