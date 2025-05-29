"""Application-level configuration for Ottotone."""

import logging
from src.config.base import ConfigStorageManager
from src.config.audio_config import AudioConfig
from src.config.hotkey_config import HotkeyConfig
from src.config.ui_config import UIConfig

logger = logging.getLogger(__name__)

class AppConfig:
    """Main application configuration coordinator.
    
    This class provides a unified interface to all configuration domains
    and ensures they use a single shared storage manager.
    
    Responsibilities:
    - Initialize and provide access to domain-specific configurations
    - Coordinate configuration updates that affect multiple domains
    """
    
    def __init__(self):
        """Initialize the application configuration."""
        # Create a single shared storage manager
        self.storage_manager = ConfigStorageManager()
        
        # Initialize domain-specific configurations
        self.audio = AudioConfig(self.storage_manager)
        self.hotkeys = HotkeyConfig(self.storage_manager)
        self.ui = UIConfig(self.storage_manager)
        
        logger.info("AppConfig initialized with all configuration domains")
    
    def migrate_from_legacy_config(self, legacy_config):
        """Migrate settings from a legacy ConfigManager.
        
        This is a helper method to transition from the old configuration
        system to the new modular approach.
        
        Args:
            legacy_config: An instance of the old ConfigManager class
        """
        legacy_settings = legacy_config.settings
        
        # Migrate audio settings
        if "selected_model" in legacy_settings:
            self.audio.set_selected_model(legacy_settings["selected_model"])
        
        if "silence_threshold_db" in legacy_settings:
            self.audio.set_silence_threshold_db(legacy_settings["silence_threshold_db"])
        
        if "silence_duration_seconds" in legacy_settings:
            self.audio.set_silence_duration_seconds(legacy_settings["silence_duration_seconds"])
        
        if "models_path" in legacy_settings:
            self.audio.set_models_path(legacy_settings["models_path"])
        
        if "compute_type" in legacy_settings:
            self.audio.set_compute_type(legacy_settings["compute_type"])
        
        # Migrate transcription settings
        for param in ["language", "beam_size", "vad_filter", "vad_parameters", 
                     "temperature", "patience", "condition_on_previous_text"]:
            key = f"transcription_{param}"
            if key in legacy_settings:
                method_name = f"set_{param}"
                if hasattr(self.audio, method_name):
                    getattr(self.audio, method_name)(legacy_settings[key])
        
        # Migrate hotkey settings
        if "hotkey" in legacy_settings:
            hotkey = legacy_settings["hotkey"]
            if "key_code" in hotkey and "modifiers" in hotkey:
                self.hotkeys.set_recording_toggle_hotkey(
                    hotkey["key_code"],
                    hotkey["modifiers"]
                )
        
        # Migrate UI settings
        if "output_action" in legacy_settings:
            self.ui.set_output_action(legacy_settings["output_action"])
        
        logger.info("Legacy configuration successfully migrated to new modular format")
