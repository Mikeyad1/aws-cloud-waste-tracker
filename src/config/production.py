"""
Production environment configuration
"""

from .settings import Settings

class ProductionSettings(Settings):
    """Production-specific settings"""
    
    def __init__(self):
        super().__init__()
        
        # Override for production
        self.DEBUG = False
        
        # Ensure PostgreSQL in production
        if not self.DATABASE_URL or "postgresql" not in self.DATABASE_URL:
            raise RuntimeError("PostgreSQL DATABASE_URL is required in production")
        
        # Conservative feature flags for production
        self.FEATURES.update({
            "recent_scans_table": True,
            "cost_explorer": True,
            "advanced_filters": False,  # Enable gradually
            "api_endpoints": False,     # Enable when ready
            "webhook_notifications": False,
            "multi_account": False,
        })
        
        # Production-specific settings
        self.AUTO_SCAN_ON_START = False
        self.SCAN_TIMEOUT_SECONDS = 300  # 5 minutes
        self.MAX_SCAN_HISTORY = 1000
        
        # Security settings
        self.REQUIRE_HTTPS = True
        self.SESSION_TIMEOUT_MINUTES = 60
