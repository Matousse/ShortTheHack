"""
Application configuration management module
"""
import os
import json
from pathlib import Path
from loguru import logger

class ConfigManager:
    """Configuration manager for the GentleMate application"""
    
    def __init__(self, config_file="config.json"):
        """Initialize the configuration manager"""
        self.config_file = config_file
        self.default_settings = {
            "trading_enabled": False,
            "target_account": os.getenv("TARGET_TWITTER_ACCOUNT", "DamienMATHIS4"),
            "target_coin": os.getenv("DEFAULT_COIN", "USDC"),
            "leverage": 1,
            "check_interval": int(os.getenv("CHECK_INTERVAL", 3))
        }
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from the configuration file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, "r") as f:
                    settings = json.load(f)
                logger.info(f"Settings loaded from {self.config_file}")
                return settings
            else:
                logger.info(f"Configuration file {self.config_file} not found, using default settings")
                self._save_settings(self.default_settings)
                return self.default_settings
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return self.default_settings
    
    def _save_settings(self, settings):
        """Save settings to the configuration file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(settings, f, indent=4)
            logger.info(f"Settings saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False
    
    def get_settings(self):
        """Return the current settings"""
        return self.settings
    
    def update_settings(self, new_settings):
        """Update the settings"""
        self.settings.update(new_settings)
        self._save_settings(self.settings)
        logger.info(f"Settings updated: {new_settings}")
        return self.settings
