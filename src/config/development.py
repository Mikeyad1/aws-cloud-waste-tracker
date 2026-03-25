"""
Development environment configuration
"""

from .settings import Settings

class DevelopmentSettings(Settings):
    """Development-specific settings"""
    
    def __init__(self):
        super().__init__()
        
        # Override for development
        self.DEBUG = True
        
        # Development database (SQLite)
        if not self.DATABASE_URL or "sqlite" not in self.DATABASE_URL:
            self.DATABASE_URL = "sqlite:///local_dev.db"
        
        # Enable all features in development
        self.FEATURES.update({
            "recent_scans_table": True,
            "cost_explorer": True,
            "advanced_filters": True,
            "api_endpoints": True,
            "webhook_notifications": False,  # Keep disabled to avoid external calls
            "multi_account": True,
        })
        
        # Development-specific settings
        self.AUTO_SCAN_ON_START = False
        self.SCAN_TIMEOUT_SECONDS = 60
        self.MAX_SCAN_HISTORY = 100
