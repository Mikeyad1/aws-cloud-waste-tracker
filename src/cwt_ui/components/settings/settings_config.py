"""
Settings configuration management.
Handles loading, saving, and validation of application settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import datetime as dt


class SettingsManager:
    """Manages application settings with proper validation and persistence."""
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]  # repo root
        self.user_cfg_dir = Path(os.path.expanduser("~")) / ".cloud_waste_tracker"
        self.settings_path = self._determine_settings_path()
        self.default_settings = self._get_default_settings()
    
    def _determine_settings_path(self) -> Path:
        """Determine the best location for settings file."""
        project_settings = self.project_root / "settings.json"
        if project_settings.exists():
            return project_settings
        
        user_settings = self.user_cfg_dir / "settings.json"
        if not user_settings.parent.exists():
            user_settings.parent.mkdir(parents=True, exist_ok=True)
        
        return user_settings
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings structure."""
        return {
            "email_reports": {
                "enabled": False,
                "recipient": "",
                "schedule": "daily",
                "send_time": "09:00",
                "weekday": "Monday",
            },
            "aws": {
                "default_region": "us-east-1",
                # standalone | org_member | org_payer — used in Setup to set Cost Explorer expectations
                "account_context": "standalone",
            },
            "billing": {
                "currency": "USD",
                "cost_threshold": 100.0,
                "savings_threshold": 50.0,
            },
            "advanced": {
                "debug_mode": False,
                "auto_refresh": True,
                "scan_interval": "24 hours",
                "data_retention": "30 days",
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file with fallback to defaults."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r") as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._merge_with_defaults(settings)
            except json.JSONDecodeError:
                print(f"Error reading settings file: {self.settings_path}. Using defaults.")
                return self.default_settings.copy()
        
        return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_path, "w") as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Failed to save settings: {e}")
            return False
    
    def _merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded settings with defaults to ensure all keys exist."""
        merged = self.default_settings.copy()
        for key, value in settings.items():
            if isinstance(value, dict) and key in merged:
                merged[key].update(value)
            else:
                merged[key] = value
        return merged
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        settings = self.load_settings()
        return settings.get(section, {}).get(key, default)
    
    def set_setting(self, section: str, key: str, value: Any) -> bool:
        """Set a specific setting value."""
        settings = self.load_settings()
        if section not in settings:
            settings[section] = {}
        settings[section][key] = value
        return self.save_settings(settings)


def parse_time(time_str: str) -> dt.time:
    """Parse time string to time object."""
    try:
        return dt.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return dt.time(9, 0)  # Default to 09:00


def weekday_index(weekday_str: str) -> int:
    """Get weekday index for selectbox."""
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    try:
        return weekdays.index(weekday_str)
    except ValueError:
        return 0  # Default to Monday


def mask_secret(secret: str, keep: int = 4) -> str:
    """Mask secret string for display."""
    if not secret:
        return ""
    if len(secret) <= keep:
        return "•" * len(secret)
    return "•" * (len(secret) - keep) + secret[-keep:]
