"""Base configuration management for Ottotone."""

import os
import json
import logging
import appdirs

APP_NAME = "Ottotone"
APP_AUTHOR = "OttotoneDev"
CONFIG_FILE_NAME = "ottotone_config.json"

logger = logging.getLogger(__name__)

class ConfigStorageManager:
    """Manages the storage and retrieval of application settings.
    
    This class handles the low-level persistence of configuration data,
    but does not define any specific configuration fields.
    Domain-specific configuration classes should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the configuration storage manager."""
        self.config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
        self.config_file_path = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        self._settings = {}
        self._load_settings()
        logger.info(f"ConfigStorageManager initialized. Settings loaded from: {self.config_file_path}")
    
    def _load_settings(self):
        """Load settings from the configuration file."""
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    self._settings = json.load(f)
                    logger.info("Settings loaded successfully.")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading config file '{self.config_file_path}': {e}. Using empty settings.", 
                              exc_info=True)
                self._settings = {}
                self._save_settings()
        else:
            logger.info("No config file found. Using empty settings and creating one.")
            self._settings = {}
            self._save_settings()
    
    def _save_settings(self):
        """Save settings to the configuration file."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file_path, 'w') as f:
                json.dump(self._settings, f, indent=4)
            logger.info(f"Settings saved to '{self.config_file_path}'.")
        except IOError as e:
            logger.error(f"Could not save config file '{self.config_file_path}': {e}", exc_info=True)
    
    def get_setting(self, key, default=None):
        """Get a setting value by key.
        
        Args:
            key: The setting key to retrieve
            default: Default value to return if key is not found
            
        Returns:
            The setting value or default if not found
        """
        if default is not None:
            return self._settings.get(key, default)
        return self._settings.get(key)
    
    def set_setting(self, key, value):
        """Set a setting value.
        
        Args:
            key: The setting key to set
            value: The value to store
        """
        self._settings[key] = value
        logger.info(f"Setting '{key}' updated to '{value}'. Saving settings.")
        self._save_settings()
