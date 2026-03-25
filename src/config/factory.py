"""
Configuration factory for loading environment-specific settings
"""

import os
from .settings import Settings


def get_settings() -> Settings:
    """
    Factory function to get the appropriate settings based on environment
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    
    if app_env == "production":
        from .production import ProductionSettings
        return ProductionSettings()
    elif app_env == "staging":
        # For future staging environment
        from .settings import Settings
        return Settings()
    else:
        from .development import DevelopmentSettings
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()
