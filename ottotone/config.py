"""Configuration management for Ottotone."""

import os
import json
import appdirs
import logging

APP_NAME = "Ottotone"
APP_AUTHOR = "OttotoneDev" # Can be your name or organization
CONFIG_FILE_NAME = "ottotone_config.json"

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application settings and preferences.
    
    Responsibilities:
    - Load/save configuration (hotkeys, model, silence detection, etc.)
    - Provide access to configuration values
    """
    def __init__(self):
        self.config_dir = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
        self.config_file_path = os.path.join(self.config_dir, CONFIG_FILE_NAME)
        self.settings = self._default_settings()
        self._load_settings()
        logger.info(f"ConfigManager initialized. Settings loaded from: {self.config_file_path}")

    def _default_settings(self):
        return {
            "hotkey": {"key_code": 49, "modifiers": ["cmd", "shift"]},
            "silence_threshold_db": -30.0,
            "silence_duration_seconds": 2.0,
            "selected_model": "tiny",
            "output_action": "paste_at_cursor",
            "models_path": os.path.join(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR), "models"),
            "transcription_language": "en", # Can be None for auto-detect
            "compute_type": "int8",  # Always use int8 for CPU compatibility
            "transcription_beam_size": 1,
            "transcription_vad_filter": False,
            "transcription_vad_parameters": {"min_silence_duration_ms": 250, "threshold": 0.35},
            "transcription_temperature": 0.0,
            "transcription_patience": 1.0,
            "transcription_condition_on_previous_text": False,
        }

    def _load_settings(self):
        if os.path.exists(self.config_file_path):
            try:
                with open(self.config_file_path, 'r') as f:
                    loaded_settings = json.load(f)
                    default_copy = self._default_settings()
                    default_copy.update(loaded_settings)
                    self.settings = default_copy
                    logger.info("Settings loaded successfully.")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading config file '{self.config_file_path}': {e}. Using default settings and attempting to save.", exc_info=True)
                self.settings = self._default_settings()
                self._save_settings()
        else:
            logger.info("No config file found. Using default settings and creating one.")
            self.settings = self._default_settings()
            self._save_settings()

    def _save_settings(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Settings saved to '{self.config_file_path}'.")
        except IOError as e:
            logger.error(f"Could not save config file '{self.config_file_path}': {e}", exc_info=True)

    def get_setting(self, key, default=None):
        if default is not None:
            return self.settings.get(key, default)
        return self.settings.get(key) 

    def set_setting(self, key, value):
        self.settings[key] = value
        logger.info(f"Setting '{key}' updated to '{value}'. Saving settings.")
        self._save_settings()

    def get_selected_model(self):
        return self.get_setting("selected_model")

    def get_hotkey(self):
        return self.get_setting("hotkey")

    def get_silence_threshold_db(self, default=-30.0):
        return self.get_setting("silence_threshold_db", default)

    def get_silence_duration_seconds(self, default=2.0):
        return self.get_setting("silence_duration_seconds", default)

    def get_compute_type(self, default="int8"):
        return self.get_setting("compute_type", default)

    def get_transcription_param(self, param_name, default=None):
        key = f"transcription_{param_name}"
        return self.get_setting(key, default)

    def get_models_path(self):
        return self.get_setting("models_path")

    def get_output_action(self):
        return self.get_setting("output_action", "clipboard") 

    def set_output_action(self, action):
        if action in ["clipboard", "paste_at_cursor"]:
            self.set_setting("output_action", action)
        else:
            logger.warning(f"Invalid output action '{action}'. Not saving.")